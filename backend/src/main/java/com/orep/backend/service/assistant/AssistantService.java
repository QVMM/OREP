package com.orep.backend.service.assistant;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.service.ProjectTeamService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

@Service
public class AssistantService {
    private static final Logger log = LoggerFactory.getLogger(AssistantService.class);
    private static final int MEMORY_LIMIT = 50;
    private static final int MEMORY_INJECT_TOP_K = 8;
    private static final Pattern SCORE_LIKE = Pattern.compile("\\d+(?:\\.\\d+)?\\s*分");
    private static final Set<String> ALLOWED_EXT = Set.of(
            "pdf", "doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx",
            "png", "jpg", "jpeg", "gif", "webp", "txt", "md", "java", "py", "js", "ts", "vue", "json"
    );
    private static final Set<String> ADMIN_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN", "SUPER_ADMIN");

    private final JdbcTemplate jdbc;
    private final ProjectTeamService projectTeamService;
    private final ObjectMapper objectMapper;
    private final ExecutorService streamExecutor = Executors.newCachedThreadPool();
    /** 仅用户主动停止 / 系统取消时为 true；浏览器刷新不断开生成 */
    private final ConcurrentHashMap<Long, Boolean> cancelFlags = new ConcurrentHashMap<>();
    /** 进行中的 run 直播状态（可多订阅者重连） */
    private final ConcurrentHashMap<Long, LiveRun> liveRuns = new ConcurrentHashMap<>();

    /**
     * 单次生成的内存态：后台持续跑 AI，SSE 只是订阅者。
     * 刷新浏览器不会停任务；回来可 subscribe 继续收实时事件。
     */
    private static final class LiveRun {
        final long runId;
        final long sessionId;
        final long assistantMsgId;
        final long userMsgId;
        final AtomicBoolean finished = new AtomicBoolean(false);
        final CopyOnWriteArrayList<SseEmitter> subscribers = new CopyOnWriteArrayList<>();
        final StringBuilder contentBuf = new StringBuilder();
        final StringBuilder thinkingBuf = new StringBuilder();
        final List<Map<String, Object>> citationAcc = new CopyOnWriteArrayList<>();
        final List<Map<String, Object>> fileAcc = new CopyOnWriteArrayList<>();
        final List<Map<String, Object>> stepSnap = new CopyOnWriteArrayList<>();
        volatile Map<String, Object> intent;
        volatile String status = "running";
        volatile long lastPersistAt = 0L;
        volatile int lastPersistedContentLen = 0;
        volatile int lastPersistedThinkingLen = 0;

        LiveRun(long runId, long sessionId, long assistantMsgId, long userMsgId) {
            this.runId = runId;
            this.sessionId = sessionId;
            this.assistantMsgId = assistantMsgId;
            this.userMsgId = userMsgId;
        }
    }

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Value("${ai-scoring.base-url:http://127.0.0.1:8090}")
    private String aiBaseUrl;

    @Value("${orep.assistant.internal-token:OREP_ASSISTANT_INTERNAL_DEV_TOKEN}")
    private String internalToken;

    public AssistantService(JdbcTemplate jdbc, ProjectTeamService projectTeamService, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.projectTeamService = projectTeamService;
        this.objectMapper = objectMapper;
    }

    // ── Sessions ──────────────────────────────────────────────

    public List<Map<String, Object>> listSessions(Long tenantId, Long userId, String keyword, int page, int size) {
        int limit = Math.min(Math.max(size, 1), 100);
        int offset = Math.max(page, 0) * limit;
        String like = keyword == null || keyword.isBlank() ? null : "%" + keyword.trim() + "%";
        if (like == null) {
            return jdbc.queryForList("""
                    SELECT id, title, team_id AS teamId, project_id AS projectId, folder_id AS folderId, status, pin,
                           message_count AS messageCount, last_message_at AS lastMessageAt,
                           created_at AS createdAt, updated_at AS updatedAt
                    FROM ai_assistant_session
                    WHERE tenant_id = ? AND user_id = ? AND status <> 'deleted'
                    ORDER BY pin DESC, updated_at DESC
                    LIMIT ? OFFSET ?
                    """, tenantId, userId, limit, offset);
        }
        // 标题 + 消息正文联合搜索
        return jdbc.queryForList("""
                SELECT DISTINCT s.id, s.title, s.team_id AS teamId, s.project_id AS projectId, s.folder_id AS folderId, s.status, s.pin,
                       s.message_count AS messageCount, s.last_message_at AS lastMessageAt,
                       s.created_at AS createdAt, s.updated_at AS updatedAt
                FROM ai_assistant_session s
                LEFT JOIN ai_assistant_message m
                  ON m.session_id = s.id AND m.user_id = s.user_id
                WHERE s.tenant_id = ? AND s.user_id = ? AND s.status <> 'deleted'
                  AND (
                    s.title LIKE ?
                    OR m.content_text LIKE ?
                  )
                ORDER BY s.pin DESC, s.updated_at DESC
                LIMIT ? OFFSET ?
                """, tenantId, userId, like, like, limit, offset);
    }

    @Transactional
    public Map<String, Object> createSession(Long tenantId, Long userId, String role, Map<String, Object> body) {
        Long teamId = longVal(body.get("teamId"));
        Long projectId = longVal(body.get("projectId"));
        if (teamId != null) {
            assertTeamAccess(teamId, tenantId, userId, role);
        }
        String title = str(body.get("title"));
        if (title == null || title.isBlank()) {
            title = "新对话";
        }
        String titleSource = body.get("title") == null ? "default" : "user";
        Long folderId = resolveFolderId(tenantId, userId, body);
        KeyHolder kh = new GeneratedKeyHolder();
        String finalTitle = title;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_session
                      (tenant_id, user_id, team_id, project_id, folder_id, title, title_source, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', NOW(), NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            if (teamId == null) ps.setObject(3, null);
            else ps.setLong(3, teamId);
            if (projectId == null) ps.setObject(4, null);
            else ps.setLong(4, projectId);
            if (folderId == null) ps.setObject(5, null);
            else ps.setLong(5, folderId);
            ps.setString(6, finalTitle);
            ps.setString(7, titleSource);
            return ps;
        }, kh);
        long id = kh.getKey().longValue();
        Object ctxRaw = body.get("contextJson") != null ? body.get("contextJson") : body.get("context");
        if (ctxRaw instanceof Map<?, ?> ctxMap && !ctxMap.isEmpty()) {
            jdbc.update(
                    "UPDATE ai_assistant_session SET context_json = ?, updated_at = NOW() WHERE id = ?",
                    toJson(ctxMap), id);
        }
        return getSession(id, tenantId, userId);
    }

    public Map<String, Object> getSession(Long sessionId, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, tenant_id AS tenantId, user_id AS userId, team_id AS teamId, project_id AS projectId,
                       folder_id AS folderId,
                       title, title_source AS titleSource, status, model, pin,
                       message_count AS messageCount, last_message_at AS lastMessageAt,
                       context_json AS contextJson,
                       created_at AS createdAt, updated_at AS updatedAt
                FROM ai_assistant_session
                WHERE id = ? AND tenant_id = ? AND user_id = ? AND status <> 'deleted'
                """, sessionId, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        Map<String, Object> row = rows.get(0);
        row.put("contextJson", parseJsonObject(row.get("contextJson")));
        return row;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseJsonObject(Object raw) {
        if (raw == null) return null;
        if (raw instanceof Map<?, ?> m) {
            return new LinkedHashMap<>((Map<String, Object>) m);
        }
        String s = String.valueOf(raw).trim();
        if (s.isEmpty() || "null".equalsIgnoreCase(s)) return null;
        try {
            return objectMapper.readValue(s, Map.class);
        } catch (Exception e) {
            return null;
        }
    }

    private void mergeSessionSlots(Long sessionId, Map<String, Object> intentData) {
        if (intentData == null || sessionId == null) return;
        Object slotsObj = intentData.get("slots");
        if (!(slotsObj instanceof Map<?, ?>)) return;
        try {
            Map<String, Object> incoming = new LinkedHashMap<>((Map<String, Object>) slotsObj);
            // 去掉调试字段
            incoming.remove("updated_keys");
            incoming.remove("updatedKeys");
            Map<String, Object> existing = null;
            try {
                List<Map<String, Object>> rows = jdbc.queryForList(
                        "SELECT context_json AS contextJson FROM ai_assistant_session WHERE id = ?",
                        sessionId);
                if (!rows.isEmpty()) {
                    existing = parseJsonObject(rows.get(0).get("contextJson"));
                }
            } catch (Exception ignore) {
                existing = null;
            }
            Map<String, Object> merged = existing == null ? new LinkedHashMap<>() : new LinkedHashMap<>(existing);
            for (Map.Entry<String, Object> e : incoming.entrySet()) {
                Object v = e.getValue();
                if (v == null) continue;
                if (v instanceof String str && str.isBlank()) continue;
                if (v instanceof List<?> list && list.isEmpty()) continue;
                if (v instanceof Boolean b && !b && merged.containsKey(e.getKey())) {
                    // prefer_scores: true 可写，false 不覆盖已有 true
                    if ("prefer_scores".equals(e.getKey()) || "preferScores".equals(e.getKey())) {
                        continue;
                    }
                }
                merged.put(e.getKey(), v);
            }
            jdbc.update(
                    "UPDATE ai_assistant_session SET context_json = ?, updated_at = NOW() WHERE id = ?",
                    toJson(merged), sessionId);
        } catch (Exception e) {
            log.warn("mergeSessionSlots failed: {}", e.getMessage());
        }
    }

    @Transactional
    public Map<String, Object> patchSession(
            Long sessionId, Long tenantId, Long userId, String role, Map<String, Object> body
    ) {
        getSession(sessionId, tenantId, userId);
        if (body.containsKey("title")) {
            String title = str(body.get("title"));
            if (title != null && !title.isBlank()) {
                jdbc.update("UPDATE ai_assistant_session SET title = ?, title_source = 'user', updated_at = NOW() WHERE id = ?",
                        title.trim(), sessionId);
            }
        }
        if (body.containsKey("status")) {
            String status = str(body.get("status"));
            if (status != null && Set.of("active", "archived", "deleted").contains(status)) {
                jdbc.update("UPDATE ai_assistant_session SET status = ?, updated_at = NOW() WHERE id = ?", status, sessionId);
            }
        }
        if (body.containsKey("pin")) {
            int pin = Boolean.TRUE.equals(body.get("pin")) || "1".equals(String.valueOf(body.get("pin"))) ? 1 : 0;
            jdbc.update("UPDATE ai_assistant_session SET pin = ?, updated_at = NOW() WHERE id = ?", pin, sessionId);
        }
        if (body.containsKey("folderId") || body.containsKey("folderSlug")) {
            Long folderId = resolveFolderId(tenantId, userId, body);
            jdbc.update("UPDATE ai_assistant_session SET folder_id = ?, updated_at = NOW() WHERE id = ?", folderId, sessionId);
        }
        if (body.containsKey("teamId")) {
            Long teamId = longVal(body.get("teamId"));
            if (teamId != null) {
                assertTeamAccess(teamId, tenantId, userId, role);
            }
            jdbc.update("UPDATE ai_assistant_session SET team_id = ?, updated_at = NOW() WHERE id = ?", teamId, sessionId);
        }
        if (body.containsKey("contextJson") || body.containsKey("context")) {
            Object ctxRaw = body.get("contextJson") != null ? body.get("contextJson") : body.get("context");
            if (ctxRaw instanceof Map<?, ?> ctxMap) {
                jdbc.update(
                        "UPDATE ai_assistant_session SET context_json = ?, updated_at = NOW() WHERE id = ?",
                        toJson(ctxMap), sessionId);
            }
        }
        return getSession(sessionId, tenantId, userId);
    }

    public List<Map<String, Object>> myTeams(Long tenantId, Long userId, String role) {
        try {
            return projectTeamService.myTeams(tenantId, userId, role);
        } catch (Exception e) {
            log.warn("myTeams failed: {}", e.getMessage());
            return List.of();
        }
    }

    /**
     * 小启 slash 技能列表（与 ai-scoring skills/catalog 对齐；不依赖 Python 进程）。
     */
    public List<Map<String, Object>> listSkills(String audience) {
        String aud = audience == null ? "student" : audience.trim().toLowerCase(Locale.ROOT);
        List<Map<String, Object>> all = List.of(
                skillRow("opening", "开场", "30 秒路演开场词（赛场匿名：禁止真名真校）", "student", 20),
                skillRow("score-review", "复盘", "根据 AI 评分报告做复盘：扣分、优先改什么、怎么练", "student", 25),
                skillRow("daily-agenda", "今日", "今日安排 / 下一步优先：结合训练营、任务、协同", "student", 30),
                skillRow("rewrite-script", "改稿", "润色/改写讲稿、开场、路演词（赛场匿名）", "student", 18),
                skillRow("teacher-desk", "工作台", "教师工作台：待批改、未交、进度、今日带队重点", "teacher", 30)
        );
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> s : all) {
            String a = String.valueOf(s.get("audience"));
            if ("any".equals(aud) || "any".equals(a) || aud.equals(a)) {
                out.add(s);
            }
        }
        out.sort((x, y) -> Integer.compare(
                ((Number) y.getOrDefault("priority", 0)).intValue(),
                ((Number) x.getOrDefault("priority", 0)).intValue()
        ));
        return out;
    }

    private static Map<String, Object> skillRow(String name, String slash, String description, String audience, int priority) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("name", name);
        m.put("slash", slash);
        m.put("description", description);
        m.put("audience", audience);
        m.put("priority", priority);
        return m;
    }

    public Map<String, Object> resourcePicker(Long teamId, Long tenantId, Long userId, String role) {
        assertTeamAccess(teamId, tenantId, userId, role);
        List<Map<String, Object>> files = jdbc.queryForList("""
                SELECT id, name, ext, file_size AS fileSize, category AS folderKey,
                       created_at AS createdAt, team_id AS teamId,
                       extract_method AS extractMethod, extract_chars AS extractChars,
                       extract_at AS extractAt
                FROM resource
                WHERE team_id = ?
                ORDER BY created_at DESC
                LIMIT 200
                """, teamId);
        List<Map<String, Object>> publicFiles = jdbc.queryForList("""
                SELECT id, name, ext, file_size AS fileSize, category AS folderKey,
                       created_at AS createdAt, team_id AS teamId,
                       extract_method AS extractMethod, extract_chars AS extractChars,
                       extract_at AS extractAt
                FROM resource
                WHERE team_id IS NULL OR category = 'public'
                ORDER BY id DESC
                LIMIT 50
                """);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teamId", teamId);
        result.put("teamFiles", files);
        result.put("publicFiles", publicFiles);
        return result;
    }

    @Transactional
    public Map<String, Object> saveFileToResource(
            Long fileId, Long tenantId, Long userId, String role, Map<String, Object> body
    ) throws IOException {
        Map<String, Object> file = getFile(fileId, tenantId, userId);
        Long teamId = longVal(body.get("teamId"));
        if (teamId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择团队");
        }
        assertTeamAccess(teamId, tenantId, userId, role);
        String key = str(file.get("storageKey"));
        if (key == null || key.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该文件无可保存内容");
        }
        Path path = resolveFilePath(fileId, tenantId, userId);
        String name = str(file.get("name"));
        String ext = extension(name);
        if (ext.isEmpty()) ext = "bin";
        Integer resourceId = insertTeamResource(
                teamId, userId, name, ext, key, Files.size(path), str(body.get("folderKey")));
        if (resourceId == null) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "保存到资源中心失败");
        }
        jdbc.update("UPDATE ai_assistant_file SET resource_id = ?, visibility = 'team_resource' WHERE id = ?",
                resourceId, fileId);
        Map<String, Object> result = new LinkedHashMap<>(getFile(fileId, tenantId, userId));
        result.put("resourceId", resourceId);
        result.put("teamId", teamId);
        return result;
    }

    @Transactional
    public Map<String, Object> saveReplyAsMarkdown(
            Long sessionId, Long tenantId, Long userId, String role, Map<String, Object> body
    ) throws IOException {
        getSession(sessionId, tenantId, userId);
        String content = str(body.get("content"));
        if (content == null || content.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "内容为空");
        }
        String format = str(body.get("format"));
        if (format == null) format = "md";
        format = format.toLowerCase();

        String fileName = str(body.get("fileName"));
        Map<String, Object> file;
        if ("docx".equals(format) || "word".equals(format)) {
            if (fileName == null || fileName.isBlank()) {
                fileName = "助手产出-" + System.currentTimeMillis() + ".docx";
            }
            if (!fileName.toLowerCase().endsWith(".docx")) fileName = fileName + ".docx";
            byte[] bytes = renderDocxViaAi(content, str(body.get("title")));
            file = persistGeneratedBytes(
                    sessionId, tenantId, userId, 0L, fileName,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    bytes);
        } else if ("pdf".equals(format)) {
            if (fileName == null || fileName.isBlank()) {
                fileName = "助手产出-" + System.currentTimeMillis() + ".pdf";
            }
            if (!fileName.toLowerCase().endsWith(".pdf")) fileName = fileName + ".pdf";
            byte[] bytes = renderPdfViaAi(Map.of(
                    "title", str(body.get("title")) == null ? "竞赛助手文稿" : str(body.get("title")),
                    "content", content
            ));
            file = persistGeneratedBytes(
                    sessionId, tenantId, userId, 0L, fileName,
                    "application/pdf", bytes);
        } else if ("pptx".equals(format) || "ppt".equals(format)) {
            if (fileName == null || fileName.isBlank()) {
                fileName = "助手提纲-" + System.currentTimeMillis() + ".pptx";
            }
            if (!fileName.toLowerCase().endsWith(".pptx")) fileName = fileName + ".pptx";
            byte[] bytes = postAiBinary("/api/assistant/v1/render-pptx", Map.of(
                    "content", content,
                    "title", str(body.get("title")) == null ? "竞赛助手提纲" : str(body.get("title"))
            ), "PPT");
            file = persistGeneratedBytes(
                    sessionId, tenantId, userId, 0L, fileName,
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    bytes);
        } else {
            if (fileName == null || fileName.isBlank()) {
                fileName = "助手产出-" + System.currentTimeMillis() + ".md";
            }
            if (!fileName.contains(".")) fileName = fileName + ".md";
            file = persistGeneratedBytes(
                    sessionId, tenantId, userId, 0L, fileName,
                    "text/markdown", content.getBytes(StandardCharsets.UTF_8));
        }

        if (Boolean.TRUE.equals(body.get("saveToTeam"))) {
            Long teamId = longVal(body.get("teamId"));
            if (teamId != null) {
                Map<String, Object> saved = saveFileToResource(
                        longVal(file.get("id")), tenantId, userId, role,
                        Map.of("teamId", teamId, "folderKey", body.getOrDefault("folderKey", "content")));
                file.putAll(saved);
            }
        }
        return file;
    }

    @SuppressWarnings("unchecked")
    private byte[] renderDocxViaAi(String content, String title) {
        Map<String, Object> req = new LinkedHashMap<>();
        req.put("content", content);
        req.put("title", title == null || title.isBlank() ? "竞赛助手文稿" : title);
        return postAiBinary("/api/assistant/v1/render-docx", req, "Word");
    }

    @SuppressWarnings("unchecked")
    private byte[] renderPdfViaAi(Map<String, Object> req) {
        return postAiBinary("/api/assistant/v1/render-pdf", req, "PDF");
    }

    @SuppressWarnings("unchecked")
    private byte[] postAiBinary(String path, Map<String, Object> req, String label) {
        try {
            HttpURLConnection conn = (HttpURLConnection) URI.create(aiBaseUrl + path).toURL().openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(5_000);
            conn.setReadTimeout(45_000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            try (OutputStream os = conn.getOutputStream()) {
                os.write(objectMapper.writeValueAsBytes(req));
            }
            int code = conn.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
            if (stream == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, label + " 渲染无响应");
            }
            String body = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            if (code < 200 || code >= 300) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, label + " 渲染失败: " + truncate(body, 200));
            }
            Map<String, Object> parsed = objectMapper.readValue(body, Map.class);
            String b64 = str(parsed.get("contentBase64"));
            if (b64 == null || b64.isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, label + " 渲染结果为空");
            }
            return Base64.getDecoder().decode(b64);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, label + " 渲染失败: " + e.getMessage());
        }
    }

    /**
     * 导出整段对话为 PDF，写入会话文件。
     */
    @Transactional
    public Map<String, Object> exportSessionPdf(Long sessionId, Long tenantId, Long userId, String role) throws IOException {
        Map<String, Object> session = getSession(sessionId, tenantId, userId);
        List<Map<String, Object>> msgs = listMessages(sessionId, tenantId, userId, null, 200);
        List<Map<String, Object>> payloadMsgs = new ArrayList<>();
        for (Map<String, Object> m : msgs) {
            String roleName = str(m.get("role"));
            if (!"user".equals(roleName) && !"assistant".equals(roleName)) continue;
            String content = str(m.get("contentText"));
            if (content == null || content.isBlank()) continue;
            payloadMsgs.add(Map.of("role", roleName, "content", content));
        }
        String title = str(session.get("title"));
        if (title == null || title.isBlank()) title = "竞赛助手对话";
        byte[] bytes = renderPdfViaAi(Map.of(
                "title", title,
                "subtitle", "导出时间：" + LocalDateTime.now(),
                "messages", payloadMsgs
        ));
        String fileName = "对话导出-" + title.replaceAll("[\\\\/:*?\"<>|]+", "_") + "-" + System.currentTimeMillis() + ".pdf";
        return persistGeneratedBytes(
                sessionId, tenantId, userId, 0L, fileName, "application/pdf", bytes);
    }

    @Transactional
    public void deleteSession(Long sessionId, Long tenantId, Long userId) {
        getSession(sessionId, tenantId, userId);
        jdbc.update("UPDATE ai_assistant_session SET status = 'deleted', updated_at = NOW() WHERE id = ?", sessionId);
    }

    public List<Map<String, Object>> listFolders(Long tenantId, Long userId) {
        ensureDefaultFolders(tenantId, userId);
        classifyUnfiledSessions(tenantId, userId);
        return jdbc.queryForList("""
                SELECT f.id, f.name, f.slug, f.builtin, f.sort_order AS sortOrder,
                       (SELECT COUNT(*) FROM ai_assistant_session s
                         WHERE s.folder_id = f.id AND s.user_id = f.user_id AND s.status <> 'deleted') AS sessionCount
                FROM ai_assistant_folder f
                WHERE f.tenant_id = ? AND f.user_id = ?
                ORDER BY f.sort_order ASC, f.id ASC
                """, tenantId, userId);
    }

    @Transactional
    public Map<String, Object> createFolder(Long tenantId, Long userId, Map<String, Object> body) {
        ensureDefaultFolders(tenantId, userId);
        String name = str(body.get("name"));
        if (name == null || name.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请填写文件夹名称");
        }
        name = name.trim();
        if (name.length() > 80) name = name.substring(0, 80);
        Integer max = jdbc.queryForObject(
                "SELECT COALESCE(MAX(sort_order), 10) FROM ai_assistant_folder WHERE tenant_id = ? AND user_id = ?",
                Integer.class, tenantId, userId);
        String slug = "custom-" + System.currentTimeMillis();
        KeyHolder kh = new GeneratedKeyHolder();
        String finalName = name;
        int order = (max == null ? 10 : max) + 1;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_folder (tenant_id, user_id, name, slug, builtin, sort_order, created_at)
                    VALUES (?, ?, ?, ?, 0, ?, NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setString(3, finalName);
            ps.setString(4, slug);
            ps.setInt(5, order);
            return ps;
        }, kh);
        return getFolder(kh.getKey().longValue(), tenantId, userId);
    }

    @Transactional
    public Map<String, Object> patchFolder(Long folderId, Long tenantId, Long userId, Map<String, Object> body) {
        Map<String, Object> folder = getFolder(folderId, tenantId, userId);
        if (isBuiltinFolder(folder)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "系统文件夹不能改名");
        }
        if (body.containsKey("name")) {
            String name = str(body.get("name"));
            if (name == null || name.isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请填写文件夹名称");
            }
            jdbc.update("UPDATE ai_assistant_folder SET name = ? WHERE id = ?", name.trim(), folderId);
        }
        return getFolder(folderId, tenantId, userId);
    }

    @Transactional
    public void deleteFolder(Long folderId, Long tenantId, Long userId) {
        Map<String, Object> folder = getFolder(folderId, tenantId, userId);
        if (isBuiltinFolder(folder)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "系统文件夹不能删除");
        }
        jdbc.update("UPDATE ai_assistant_session SET folder_id = NULL WHERE folder_id = ? AND user_id = ?", folderId, userId);
        jdbc.update("DELETE FROM ai_assistant_folder WHERE id = ?", folderId);
    }

    private Map<String, Object> getFolder(Long folderId, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, name, slug, builtin, sort_order AS sortOrder
                FROM ai_assistant_folder
                WHERE id = ? AND tenant_id = ? AND user_id = ?
                """, folderId, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件夹不存在");
        }
        return rows.get(0);
    }

    private void ensureDefaultFolders(Long tenantId, Long userId) {
        insertDefaultFolder(tenantId, userId, "讲稿", "script", 1);
        insertDefaultFolder(tenantId, userId, "路演", "roadshow", 2);
    }

    private void insertDefaultFolder(Long tenantId, Long userId, String name, String slug, int order) {
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM ai_assistant_folder WHERE tenant_id = ? AND user_id = ? AND slug = ?",
                Integer.class, tenantId, userId, slug);
        if (exists != null && exists > 0) return;
        jdbc.update("""
                INSERT INTO ai_assistant_folder (tenant_id, user_id, name, slug, builtin, sort_order, created_at)
                VALUES (?, ?, ?, ?, 1, ?, NOW())
                """, tenantId, userId, name, slug, order);
    }

    private void classifyUnfiledSessions(Long tenantId, Long userId) {
        Long scriptId = folderIdBySlug(tenantId, userId, "script");
        Long roadshowId = folderIdBySlug(tenantId, userId, "roadshow");
        if (scriptId != null) {
            jdbc.update("""
                    UPDATE ai_assistant_session
                    SET folder_id = ?
                    WHERE tenant_id = ? AND user_id = ? AND folder_id IS NULL AND status <> 'deleted'
                      AND (title LIKE '改稿%' OR title LIKE '%讲稿%')
                    """, scriptId, tenantId, userId);
        }
        if (roadshowId != null) {
            jdbc.update("""
                    UPDATE ai_assistant_session
                    SET folder_id = ?
                    WHERE tenant_id = ? AND user_id = ? AND folder_id IS NULL AND status <> 'deleted'
                      AND (title LIKE '%路演%' OR title LIKE '%评分%')
                    """, roadshowId, tenantId, userId);
        }
    }

    private boolean isBuiltinFolder(Map<String, Object> folder) {
        Object raw = folder == null ? null : folder.get("builtin");
        return Boolean.TRUE.equals(raw) || "1".equals(String.valueOf(raw));
    }

    private Long folderIdBySlug(Long tenantId, Long userId, String slug) {
        List<Long> ids = jdbc.query(
                "SELECT id FROM ai_assistant_folder WHERE tenant_id = ? AND user_id = ? AND slug = ? LIMIT 1",
                (rs, i) -> rs.getLong(1), tenantId, userId, slug);
        return ids.isEmpty() ? null : ids.get(0);
    }

    private Long resolveFolderId(Long tenantId, Long userId, Map<String, Object> body) {
        if (body == null) return null;
        if (body.containsKey("folderId") && body.get("folderId") == null) return null;
        Long folderId = longVal(body.get("folderId"));
        if (folderId != null) {
            getFolder(folderId, tenantId, userId);
            return folderId;
        }
        String slug = str(body.get("folderSlug"));
        if (slug == null || slug.isBlank()) return null;
        ensureDefaultFolders(tenantId, userId);
        Long id = folderIdBySlug(tenantId, userId, slug.trim());
        if (id == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件夹不存在");
        }
        return id;
    }

    // ── Messages ──────────────────────────────────────────────

    public List<Map<String, Object>> listMessages(Long sessionId, Long tenantId, Long userId, Long beforeId, int limit) {
        getSession(sessionId, tenantId, userId);
        int lim = Math.min(Math.max(limit, 1), 100);
        List<Map<String, Object>> rows;
        if (beforeId == null) {
            rows = jdbc.queryForList("""
                    SELECT id, session_id AS sessionId, role, content_text AS contentText, content_json AS contentJson,
                           thinking_text AS thinkingText, status, model, run_id AS runId,
                           error_code AS errorCode, error_message AS errorMessage,
                           created_at AS createdAt, updated_at AS updatedAt
                    FROM ai_assistant_message
                    WHERE session_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    """, sessionId, lim);
        } else {
            rows = jdbc.queryForList("""
                    SELECT id, session_id AS sessionId, role, content_text AS contentText, content_json AS contentJson,
                           thinking_text AS thinkingText, status, model, run_id AS runId,
                           error_code AS errorCode, error_message AS errorMessage,
                           created_at AS createdAt, updated_at AS updatedAt
                    FROM ai_assistant_message
                    WHERE session_id = ? AND id < ?
                    ORDER BY id DESC
                    LIMIT ?
                    """, sessionId, beforeId, lim);
        }
        // 进行中的消息：合并内存实时态 + DB steps，便于刷新后立刻看到进度
        for (Map<String, Object> m : rows) {
            Long runId = longVal(m.get("runId"));
            if (runId == null) continue;
            String st = String.valueOf(m.get("status"));
            if ("streaming".equals(st) || "pending".equals(st)) {
                LiveRun live = liveRuns.get(runId);
                if (live != null && !live.finished.get()) {
                    m.put("contentText", live.contentBuf.toString());
                    m.put("thinkingText", live.thinkingBuf.toString());
                    m.put("status", "streaming");
                    m.put("steps", new ArrayList<>(live.stepSnap));
                    m.put("live", true);
                } else {
                    m.put("steps", jdbc.queryForList("""
                            SELECT step_no AS stepNo, step_key AS stepKey, title, status,
                                   output_summary AS outputSummary
                            FROM ai_assistant_run_step WHERE run_id = ? ORDER BY step_no
                            """, runId));
                    m.put("live", false);
                }
            }
        }
        return rows;
    }

    public Map<String, Object> getRun(Long runId, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, session_id AS sessionId, status, intent_json AS intentJson, trace_id AS traceId,
                       user_message_id AS userMessageId, assistant_message_id AS assistantMessageId,
                       error_code AS errorCode, error_message AS errorMessage,
                       started_at AS startedAt, finished_at AS finishedAt, created_at AS createdAt
                FROM ai_assistant_run
                WHERE id = ? AND tenant_id = ? AND user_id = ?
                """, runId, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "运行不存在");
        }
        Map<String, Object> run = rows.get(0);
        run.put("steps", jdbc.queryForList("""
                SELECT step_no AS stepNo, step_key AS stepKey, title, status,
                       input_summary AS inputSummary, output_summary AS outputSummary,
                       started_at AS startedAt, finished_at AS finishedAt
                FROM ai_assistant_run_step WHERE run_id = ? ORDER BY step_no
                """, runId));
        return run;
    }

    @Transactional
    public void cancelRun(Long runId, Long tenantId, Long userId) {
        Map<String, Object> run = getRun(runId, tenantId, userId);
        String status = String.valueOf(run.get("status"));
        if (!"running".equals(status) && !"queued".equals(status)) {
            return;
        }
        cancelFlags.put(runId, true);
        jdbc.update("""
                UPDATE ai_assistant_run SET status = 'cancelled', finished_at = NOW(),
                  error_code = 'CANCELLED', error_message = '用户停止生成'
                WHERE id = ?
                """, runId);
        Long assistantMessageId = longVal(run.get("assistantMessageId"));
        if (assistantMessageId != null) {
            jdbc.update("""
                    UPDATE ai_assistant_message SET status = 'cancelled', updated_at = NOW()
                    WHERE id = ? AND status IN ('pending', 'streaming')
                    """, assistantMessageId);
        }
    }

    public SseEmitter streamMessage(
            Long sessionId,
            Long tenantId,
            Long userId,
            String role,
            Map<String, Object> body
    ) {
        Map<String, Object> session = getSession(sessionId, tenantId, userId);
        String content = str(body.get("content"));
        if (content == null || content.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "消息内容不能为空");
        }
        String clientMessageId = str(body.get("clientMessageId"));
        if (clientMessageId != null && !clientMessageId.isBlank()) {
            List<Map<String, Object>> existing = jdbc.queryForList("""
                    SELECT run_id AS runId FROM ai_assistant_message
                    WHERE session_id = ? AND client_message_id = ? AND role = 'user' LIMIT 1
                    """, sessionId, clientMessageId);
            if (!existing.isEmpty() && existing.get(0).get("runId") != null) {
                // 幂等：已存在则返回已有 run 的状态流（简化：直接 409 提示前端拉历史）
                Long existingRunId = longVal(existing.get(0).get("runId"));
                SseEmitter emitter = new SseEmitter(30_000L);
                streamExecutor.execute(() -> {
                    try {
                        emitter.send(SseEmitter.event().name("error").data(Map.of(
                                "code", "DUPLICATE",
                                "message", "重复请求",
                                "runId", existingRunId,
                                "retryable", false
                        )));
                        emitter.complete();
                    } catch (Exception e) {
                        emitter.completeWithError(e);
                    }
                });
                return emitter;
            }
        }

        @SuppressWarnings("unchecked")
        List<Number> attachmentFileIds = body.get("attachmentFileIds") instanceof List
                ? (List<Number>) body.get("attachmentFileIds") : List.of();
        @SuppressWarnings("unchecked")
        List<Number> resourceIds = body.get("resourceIds") instanceof List
                ? (List<Number>) body.get("resourceIds") : List.of();

        long userMsgId = insertMessage(sessionId, tenantId, userId, "user", content.trim(), null, "completed", null, clientMessageId);
        long assistantMsgId = insertMessage(sessionId, tenantId, userId, "assistant", "", null, "pending", null, null);
        String traceId = UUID.randomUUID().toString().replace("-", "");
        long runId = insertRun(sessionId, tenantId, userId, userMsgId, assistantMsgId, traceId, body);
        jdbc.update("UPDATE ai_assistant_message SET run_id = ? WHERE id IN (?, ?)", runId, userMsgId, assistantMsgId);
        jdbc.update("""
                UPDATE ai_assistant_session
                SET message_count = message_count + 2, last_message_at = NOW(), updated_at = NOW()
                WHERE id = ?
                """, sessionId);

        if (session.get("titleSource") != null && "default".equals(String.valueOf(session.get("titleSource")))) {
            String autoTitle = content.trim();
            if (autoTitle.length() > 36) autoTitle = autoTitle.substring(0, 36) + "…";
            jdbc.update("UPDATE ai_assistant_session SET title = ?, title_source = 'auto' WHERE id = ? AND title_source = 'default'",
                    autoTitle, sessionId);
        }

        // 关联本轮引用的资源到会话文件区
        for (Number rid : resourceIds) {
            try {
                attachResourceRef(sessionId, tenantId, userId, rid.longValue());
            } catch (Exception e) {
                log.warn("attach resource ref failed: {}", e.getMessage());
            }
        }

        List<Map<String, Object>> history = loadHistoryForModel(sessionId, 20);
        List<String> memories = loadMemoriesForInject(tenantId, userId);
        Long teamId = longVal(session.get("teamId"));
        if (teamId == null) {
            teamId = longVal(body.get("teamId"));
        }
        List<Map<String, Object>> resourceContexts = buildResourceContexts(
                resourceIds, tenantId, userId, role);
        List<Map<String, Object>> attachmentContexts = buildAttachmentContexts(
                attachmentFileIds, tenantId, userId);

        Map<String, Object> aiRequest = new LinkedHashMap<>();
        aiRequest.put("traceId", traceId);
        aiRequest.put("tenantId", tenantId);
        aiRequest.put("userId", userId);
        aiRequest.put("role", role);
        aiRequest.put("teamId", teamId);
        aiRequest.put("sessionId", sessionId);
        aiRequest.put("runId", runId);
        aiRequest.put("userMessageId", userMsgId);
        aiRequest.put("assistantMessageId", assistantMsgId);
        aiRequest.put("messages", history);
        aiRequest.put("memories", memories);
        aiRequest.put("attachmentFileIds", attachmentFileIds);
        aiRequest.put("resourceIds", resourceIds);
        aiRequest.put("resourceContexts", resourceContexts);
        aiRequest.put("attachmentContexts", attachmentContexts);
        Map<String, Object> options = new LinkedHashMap<>();
        if (body.get("options") instanceof Map<?, ?> optRaw) {
            for (Map.Entry<?, ?> e : optRaw.entrySet()) {
                if (e.getKey() != null) options.put(String.valueOf(e.getKey()), e.getValue());
            }
        }
        String mode = str(body.get("mode"));
        if (mode == null || mode.isBlank()) mode = str(options.get("mode"));
        if (mode == null || mode.isBlank()) mode = "fast";
        mode = mode.trim().toLowerCase(Locale.ROOT);
        if (!Set.of("fast", "think", "deep_search").contains(mode)) mode = "fast";
        options.put("mode", mode);

        // 首页 clientContext：ephemeral，不污染持久化 user content
        Map<String, Object> clientContext = extractMap(body.get("clientContext"));
        if (clientContext == null) {
            clientContext = extractMap(options.get("clientContext"));
        }
        if (clientContext != null && !clientContext.isEmpty()) {
            aiRequest.put("clientContext", clientContext);
            String source = str(clientContext.get("source"));
            if (source != null && "home".equalsIgnoreCase(source.trim())) {
                // P0：学生首页半栏强制学生备赛人设，覆盖 JWT 教师/管理员角色
                options.put("audience", "student");
                options.put("forceStudent", true);
                String homeBrief = buildHomeContextBrief(clientContext);
                if (homeBrief != null && !homeBrief.isBlank()) {
                    aiRequest.put("homeContextBrief", homeBrief);
                }
            }
        }
        // 允许前端显式 audience
        String audience = str(body.get("audience"));
        if (audience == null || audience.isBlank()) audience = str(options.get("audience"));
        if (audience != null && !audience.isBlank()) {
            options.put("audience", audience.trim().toLowerCase(Locale.ROOT));
            if ("student".equalsIgnoreCase(audience)) {
                options.put("forceStudent", true);
            }
        }

        aiRequest.put("mode", mode);
        aiRequest.put("options", options);
        aiRequest.put("workspaceSlug", teamId == null ? null : "t" + tenantId + "-team" + teamId);
        // 会话级 Slot 记忆（项目名/报告/产物偏好）
        Object ctx = session.get("contextJson");
        if (ctx instanceof Map<?, ?>) {
            aiRequest.put("sessionSlots", ctx);
        }
        // AI 在独立容器内调用：必须用 Docker 服务名，不能用 127.0.0.1
        aiRequest.put("backendBaseUrl", resolveBackendInternalUrl());
        aiRequest.put("internalToken", internalToken);

        LiveRun live = new LiveRun(runId, sessionId, assistantMsgId, userMsgId);
        liveRuns.put(runId, live);
        cancelFlags.put(runId, false);

        SseEmitter emitter = new SseEmitter(0L); // 0 = 不因订阅超时掐掉任务
        attachSubscriber(live, emitter);

        Long finalTeamId = teamId;
        streamExecutor.execute(() -> runAssistantJob(live, tenantId, userId, finalTeamId, aiRequest));
        return emitter;
    }

    /**
     * 重连订阅：用户刷新后带着 runId 回来，继续收实时进度。
     * 若任务已结束则推快照后关闭；若 JVM 重启丢内存则轮询 DB。
     */
    public SseEmitter subscribeRun(Long runId, Long tenantId, Long userId) {
        Map<String, Object> run = getRun(runId, tenantId, userId);
        SseEmitter emitter = new SseEmitter(0L);
        LiveRun live = liveRuns.get(runId);
        String status = String.valueOf(run.get("status"));

        if (live != null && !live.finished.get()) {
            // 先推快照再挂直播
            try {
                emitter.send(SseEmitter.event().name("snapshot").data(buildLiveSnapshot(live, run)));
            } catch (Exception e) {
                finishEmitterQuietly(emitter);
                return emitter;
            }
            attachSubscriber(live, emitter);
            return emitter;
        }

        // 无内存态：已完成 / 或服务重启后仍 running → 快照 + 可选轮询
        streamExecutor.execute(() -> {
            try {
                Map<String, Object> snap = buildDbSnapshot(runId, run);
                emitter.send(SseEmitter.event().name("snapshot").data(snap));
                if ("running".equals(status) || "queued".equals(status)) {
                    // 服务重启后后台任务已丢：标记失败提示重试；若其它节点扩展可在此恢复
                    // 同进程：短暂轮询等待 live 注册或 DB 结束
                    for (int i = 0; i < 120; i++) {
                        if (Boolean.TRUE.equals(cancelFlags.get(runId))) break;
                        LiveRun again = liveRuns.get(runId);
                        if (again != null && !again.finished.get()) {
                            attachSubscriber(again, emitter);
                            return;
                        }
                        Map<String, Object> r2 = getRun(runId, tenantId, userId);
                        String st = String.valueOf(r2.get("status"));
                        if (!"running".equals(st) && !"queued".equals(st)) {
                            emitter.send(SseEmitter.event().name("snapshot").data(buildDbSnapshot(runId, r2)));
                            emitter.send(SseEmitter.event().name("run_completed").data(Map.of(
                                    "runId", runId, "status", st
                            )));
                            break;
                        }
                        // 心跳，保持连接
                        try {
                            emitter.send(SseEmitter.event().name("heartbeat").data(Map.of("ts", System.currentTimeMillis())));
                        } catch (Exception gone) {
                            return;
                        }
                        Thread.sleep(1500);
                    }
                } else {
                    emitter.send(SseEmitter.event().name("run_completed").data(Map.of(
                            "runId", runId, "status", status
                    )));
                }
            } catch (Exception e) {
                log.info("subscribeRun end runId={}: {}", runId, rootMessage(e));
            } finally {
                finishEmitterQuietly(emitter);
            }
        });
        return emitter;
    }

    private void attachSubscriber(LiveRun live, SseEmitter emitter) {
        live.subscribers.add(emitter);
        emitter.onCompletion(() -> live.subscribers.remove(emitter));
        emitter.onTimeout(() -> {
            live.subscribers.remove(emitter);
            finishEmitterQuietly(emitter);
            log.info("Assistant SSE subscriber timeout runId={} (task keeps running)", live.runId);
        });
        emitter.onError(ex -> {
            live.subscribers.remove(emitter);
            if (isClientAbort(ex)) {
                log.info("Assistant SSE subscriber abort runId={} (task keeps running): {}",
                        live.runId, rootMessage(ex));
            } else {
                log.warn("Assistant SSE subscriber error runId={}: {}", live.runId, rootMessage(ex));
            }
        });
    }

    private Map<String, Object> buildLiveSnapshot(LiveRun live, Map<String, Object> runRow) {
        Map<String, Object> snap = new LinkedHashMap<>();
        snap.put("runId", live.runId);
        snap.put("sessionId", live.sessionId);
        snap.put("status", live.status);
        snap.put("userMessageId", live.userMsgId);
        snap.put("assistantMessageId", live.assistantMsgId);
        snap.put("contentText", live.contentBuf.toString());
        snap.put("thinkingText", live.thinkingBuf.toString());
        snap.put("citations", new ArrayList<>(live.citationAcc));
        snap.put("files", new ArrayList<>(live.fileAcc));
        snap.put("steps", new ArrayList<>(live.stepSnap));
        snap.put("intent", live.intent);
        if (runRow != null) {
            snap.put("traceId", runRow.get("traceId"));
        }
        return snap;
    }

    private Map<String, Object> buildDbSnapshot(long runId, Map<String, Object> run) {
        Map<String, Object> snap = new LinkedHashMap<>(run);
        Long assistantMsgId = longVal(run.get("assistantMessageId"));
        if (assistantMsgId != null) {
            List<Map<String, Object>> msgs = jdbc.queryForList("""
                    SELECT id, content_text AS contentText, thinking_text AS thinkingText,
                           content_json AS contentJson, status
                    FROM ai_assistant_message WHERE id = ?
                    """, assistantMsgId);
            if (!msgs.isEmpty()) {
                snap.put("contentText", msgs.get(0).get("contentText"));
                snap.put("thinkingText", msgs.get(0).get("thinkingText"));
                snap.put("messageStatus", msgs.get(0).get("status"));
                snap.put("contentJson", parseJsonObject(msgs.get(0).get("contentJson")));
            }
        }
        snap.put("steps", run.get("steps"));
        return snap;
    }

    private static String rootMessage(Throwable e) {
        Throwable t = e;
        while (t.getCause() != null && t.getCause() != t) {
            t = t.getCause();
        }
        String m = t.getMessage();
        return m == null || m.isBlank() ? t.getClass().getSimpleName() : m;
    }

    private static boolean isClientAbort(Throwable e) {
        Throwable t = e;
        while (t != null) {
            String name = t.getClass().getName();
            String msg = t.getMessage() == null ? "" : t.getMessage();
            if (name.contains("ClientAbortException")
                    || name.contains("AsyncRequestNotUsableException")
                    || msg.contains("Broken pipe")
                    || msg.contains("Connection reset")
                    || msg.contains("连接重置")
                    || msg.contains("你的主机中的软件中止了一个已建立的连接")
                    || msg.contains("An established connection was aborted")) {
                return true;
            }
            t = t.getCause();
        }
        return false;
    }

    /** 向所有订阅者广播；某个客户端断开不影响任务与其它订阅者 */
    private void publish(long runId, String eventName, Object data) {
        LiveRun live = liveRuns.get(runId);
        if (live == null) return;
        // 维护 step 快照便于重连
        if ("step_start".equals(eventName) || "step_end".equals(eventName)) {
            syncStepSnap(live, eventName, data);
        }
        if ("intent".equals(eventName) && data instanceof Map<?, ?> m) {
            live.intent = new LinkedHashMap<>((Map<String, Object>) m);
        }
        List<SseEmitter> dead = new ArrayList<>();
        for (SseEmitter emitter : live.subscribers) {
            try {
                emitter.send(SseEmitter.event().name(eventName).data(data));
            } catch (Exception e) {
                dead.add(emitter);
            }
        }
        if (!dead.isEmpty()) {
            live.subscribers.removeAll(dead);
            for (SseEmitter e : dead) {
                finishEmitterQuietly(e);
            }
        }
    }

    @SuppressWarnings("unchecked")
    private void syncStepSnap(LiveRun live, String eventName, Object data) {
        if (!(data instanceof Map<?, ?> raw)) return;
        Map<String, Object> d = (Map<String, Object>) raw;
        Object stepNo = d.get("stepNo");
        if (stepNo == null) return;
        Map<String, Object> found = null;
        for (Map<String, Object> s : live.stepSnap) {
            if (String.valueOf(stepNo).equals(String.valueOf(s.get("stepNo")))) {
                found = s;
                break;
            }
        }
        if (found == null) {
            found = new LinkedHashMap<>();
            found.put("stepNo", stepNo);
            live.stepSnap.add(found);
        }
        if (d.get("stepKey") != null) found.put("stepKey", d.get("stepKey"));
        if (d.get("title") != null) found.put("title", d.get("title"));
        if ("step_start".equals(eventName)) {
            found.put("status", "running");
        } else {
            found.put("status", d.get("status") == null ? "completed" : d.get("status"));
            if (d.get("outputSummary") != null) found.put("outputSummary", d.get("outputSummary"));
        }
    }

    private void finishEmitterQuietly(SseEmitter emitter) {
        try {
            emitter.complete();
        } catch (Exception ignore) {
            try {
                emitter.completeWithError(ignore);
            } catch (Exception ignore2) {
                /* swallow */
            }
        }
    }

    private void finishAllSubscribers(LiveRun live) {
        for (SseEmitter e : live.subscribers) {
            finishEmitterQuietly(e);
        }
        live.subscribers.clear();
    }

    /** 增量落库：至少 800ms 一次，或内容增长 >= 200 字 */
    private void maybePersistLive(LiveRun live) {
        long now = System.currentTimeMillis();
        int clen = live.contentBuf.length();
        int tlen = live.thinkingBuf.length();
        boolean due = now - live.lastPersistAt >= 800
                || clen - live.lastPersistedContentLen >= 200
                || tlen - live.lastPersistedThinkingLen >= 200;
        if (!due && live.lastPersistAt != 0) return;
        try {
            jdbc.update("""
                    UPDATE ai_assistant_message
                    SET content_text = ?, thinking_text = ?, status = 'streaming', updated_at = NOW()
                    WHERE id = ? AND status IN ('pending','streaming')
                    """, live.contentBuf.toString(), emptyToNull(live.thinkingBuf.toString()), live.assistantMsgId);
            live.lastPersistAt = now;
            live.lastPersistedContentLen = clen;
            live.lastPersistedThinkingLen = tlen;
        } catch (Exception e) {
            log.warn("incremental persist failed runId={}: {}", live.runId, e.getMessage());
        }
    }

    private void runAssistantJob(
            LiveRun live,
            long tenantId,
            long userId,
            Long teamId,
            Map<String, Object> aiRequest
    ) {
        long runId = live.runId;
        long assistantMsgId = live.assistantMsgId;
        long sessionId = live.sessionId;
        HttpURLConnection conn = null;
        try {
            jdbc.update("UPDATE ai_assistant_run SET status = 'running', started_at = NOW() WHERE id = ?", runId);
            jdbc.update("UPDATE ai_assistant_message SET status = 'streaming', updated_at = NOW() WHERE id = ?", assistantMsgId);
            live.status = "running";

            publish(runId, "run_started", Map.of(
                    "runId", runId,
                    "sessionId", sessionId,
                    "traceId", aiRequest.get("traceId"),
                    "userMessageId", aiRequest.get("userMessageId"),
                    "assistantMessageId", assistantMsgId
            ));

            // 立刻发出协作抬头（所有 mode 含 fast），避免前端黑盒
            long processStartedAt = System.currentTimeMillis();
            publishAgentKickoff(runId, str(aiRequest.get("mode")));

            // 先解析资料（含 OCR 进度），再进入模型生成
            resolveContextsWithProgress(runId, aiRequest);

            // 模式编排：可见协作步骤 + 站内/公网检索
            enrichWithModeResearch(live, tenantId, userId, teamId, str(aiRequest.get("role")), aiRequest);

            // 过程摘要：驱动前端折叠行「已完成 · Ns · 站内X · 网络Y」
            publishProcessDone(runId, processStartedAt, live);

            conn = (HttpURLConnection) URI.create(aiBaseUrl + "/api/assistant/v1/runs").toURL().openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(10_000);
            conn.setReadTimeout(300_000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            conn.setRequestProperty("Accept", "text/event-stream");
            byte[] payload = objectMapper.writeValueAsBytes(aiRequest);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(payload);
            }

            int code = conn.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
            if (stream == null) {
                throw new IOException("AI 服务无响应 body, HTTP " + code);
            }
            if (code < 200 || code >= 300) {
                String err = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
                throw new IOException("AI 服务错误 HTTP " + code + ": " + err);
            }

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String eventName = "message";
                StringBuilder data = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    if (Boolean.TRUE.equals(cancelFlags.get(runId))) {
                        break;
                    }
                    if (line.isEmpty()) {
                        if (data.length() > 0) {
                            handleSseEvent(live, tenantId, userId, teamId,
                                    eventName, data.toString());
                            data.setLength(0);
                            eventName = "message";
                        }
                        continue;
                    }
                    if (line.startsWith("event:")) {
                        eventName = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        if (data.length() > 0) data.append('\n');
                        data.append(line.substring(5).trim());
                    }
                }
                if (data.length() > 0 && !Boolean.TRUE.equals(cancelFlags.get(runId))) {
                    handleSseEvent(live, tenantId, userId, teamId, eventName, data.toString());
                }
            }

            boolean cancelled = Boolean.TRUE.equals(cancelFlags.get(runId));
            String finalStatus = cancelled ? "cancelled" : "completed";
            // 用户取消时若已有正文，仍保留 completed 便于查看
            if (cancelled && live.contentBuf.length() > 0) {
                finalStatus = "completed";
            }
            live.status = finalStatus;
            String contentJson = buildContentJson(
                    live.contentBuf.toString(),
                    new ArrayList<>(live.citationAcc),
                    new ArrayList<>(live.fileAcc));
            jdbc.update("""
                    UPDATE ai_assistant_message
                    SET content_text = ?, thinking_text = ?, content_json = ?, status = ?, updated_at = NOW()
                    WHERE id = ?
                    """, live.contentBuf.toString(), emptyToNull(live.thinkingBuf.toString()),
                    contentJson, finalStatus, assistantMsgId);
            jdbc.update("""
                    UPDATE ai_assistant_run SET status = ?, finished_at = NOW()
                    WHERE id = ? AND status IN ('running','queued','cancelled')
                    """, cancelled && live.contentBuf.length() == 0 ? "cancelled" : finalStatus, runId);

            Map<String, Object> completed = new LinkedHashMap<>();
            completed.put("messageId", assistantMsgId);
            completed.put("contentText", live.contentBuf.toString());
            completed.put("citations", new ArrayList<>(live.citationAcc));
            completed.put("files", new ArrayList<>(live.fileAcc));
            if (!cancelled || live.contentBuf.length() > 0) {
                publish(runId, "message_completed", completed);
            }
            publish(runId, "run_completed", Map.of(
                    "runId", runId,
                    "status", cancelled && live.contentBuf.length() == 0 ? "cancelled" : finalStatus
            ));
            live.finished.set(true);
            finishAllSubscribers(live);
        } catch (Exception e) {
            log.error("Assistant job failed runId={}: {}", runId, e.getMessage(), e);
            try {
                live.status = "failed";
                String raw = e.getMessage() == null ? "" : e.getMessage();
                String friendly = friendlyStreamError(raw);
                jdbc.update("""
                        UPDATE ai_assistant_message
                        SET content_text = ?, thinking_text = ?, status = 'failed',
                            error_code = 'STREAM_ERROR', error_message = ?, updated_at = NOW()
                        WHERE id = ?
                        """, live.contentBuf.toString(), emptyToNull(live.thinkingBuf.toString()),
                        truncate(friendly, 480), assistantMsgId);
                jdbc.update("""
                        UPDATE ai_assistant_run SET status = 'failed', finished_at = NOW(),
                          error_code = 'STREAM_ERROR', error_message = ? WHERE id = ?
                        """, truncate(friendly, 480), runId);
                publish(runId, "error", Map.of(
                        "code", "STREAM_ERROR",
                        "message", friendly,
                        "retryable", true
                ));
                publish(runId, "run_completed", Map.of(
                        "runId", runId,
                        "status", "failed",
                        "message", friendly
                ));
            } catch (Exception ex) {
                log.warn("fail finalize runId={}: {}", runId, ex.getMessage());
            }
            live.finished.set(true);
            finishAllSubscribers(live);
        } finally {
            if (conn != null) {
                try {
                    conn.disconnect();
                } catch (Exception ignore) {
                    /* ignore */
                }
            }
            cancelFlags.remove(runId);
            // 保留 live 片刻便于最后一刻 subscribe 拿到 finished 态
            streamExecutor.execute(() -> {
                try {
                    Thread.sleep(30_000);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
                liveRuns.remove(runId, live);
            });
        }
    }

    @SuppressWarnings("unchecked")
    private void handleSseEvent(
            LiveRun live,
            long tenantId,
            long userId,
            Long teamId,
            String eventName,
            String dataJson
    ) {
        long runId = live.runId;
        long assistantMsgId = live.assistantMsgId;
        long sessionId = live.sessionId;
        Map<String, Object> data;
        try {
            data = objectMapper.readValue(dataJson, Map.class);
        } catch (Exception e) {
            data = new LinkedHashMap<>(Map.of("raw", dataJson));
        }
        if (!(data instanceof LinkedHashMap)) {
            data = new LinkedHashMap<>(data);
        }

        switch (eventName) {
            case "thinking_delta" -> {
                Object t = data.get("text");
                if (t != null) {
                    live.thinkingBuf.append(t);
                    maybePersistLive(live);
                }
            }
            case "content_delta" -> {
                Object t = data.get("text");
                if (t != null) {
                    live.contentBuf.append(t);
                    maybePersistLive(live);
                }
            }
            case "content_replace" -> {
                Object t = data.get("text");
                if (t != null) {
                    live.contentBuf.setLength(0);
                    live.contentBuf.append(String.valueOf(t));
                    maybePersistLive(live);
                }
            }
            case "step_start" -> upsertStep(runId, data, "running");
            case "step_end" -> upsertStep(runId, data, str(data.get("status")) == null ? "completed" : str(data.get("status")));
            case "intent" -> {
                jdbc.update("UPDATE ai_assistant_run SET intent_json = ? WHERE id = ?", toJson(data), runId);
                mergeSessionSlots(sessionId, data);
            }
            case "citation" -> {
                Map<String, Object> c = new LinkedHashMap<>();
                int idx = live.citationAcc.size() + 1;
                if (data.get("index") instanceof Number n) idx = n.intValue();
                c.put("index", idx);
                c.put("resourceId", data.get("resourceId"));
                c.put("fileId", data.get("fileId"));
                c.put("reportId", data.get("reportId"));
                c.put("sessionId", data.get("sessionId"));
                c.put("title", data.get("title"));
                c.put("snippet", data.get("snippet"));
                c.put("url", data.get("url"));
                c.put("sourceType", data.getOrDefault("sourceType",
                        data.get("url") != null ? "web" : (data.get("resourceId") != null ? "resource" : "unknown")));
                c.put("ocr", data.get("ocr"));
                c.put("method", data.get("method"));
                c.put("fromCache", data.get("fromCache"));
                live.citationAcc.add(c);
            }
            case "artifact", "file" -> {
                try {
                    String name = str(data.get("name"));
                    String b64 = str(data.get("contentBase64"));
                    String textContent = str(data.get("textContent"));
                    Map<String, Object> saved = null;
                    if (b64 != null && !b64.isBlank()) {
                        if (name == null || name.isBlank()) {
                            name = "助手产出-" + System.currentTimeMillis() + ".bin";
                        }
                        String mime = str(data.get("mime"));
                        if (mime == null || mime.isBlank()) mime = "application/octet-stream";
                        byte[] bytes = Base64.getDecoder().decode(b64);
                        saved = persistGeneratedBytes(
                                sessionId, tenantId, userId, assistantMsgId, name, mime, bytes);
                    } else if (textContent != null && !textContent.isBlank()) {
                        if (name == null || name.isBlank()) {
                            name = "助手产出-" + System.currentTimeMillis() + ".md";
                        }
                        saved = persistGeneratedText(
                                sessionId, tenantId, userId, assistantMsgId, name, textContent);
                    }
                    if (saved != null) {
                        data.put("fileId", saved.get("id"));
                        data.put("name", saved.get("name"));
                        data.put("size", saved.get("sizeBytes"));
                        data.put("source", "generated");
                        data.put("mime", saved.get("mimeType"));
                        data.remove("contentBase64");
                        data.remove("textContent");
                        Map<String, Object> f = new LinkedHashMap<>();
                        f.put("fileId", saved.get("id"));
                        f.put("id", saved.get("id"));
                        f.put("name", saved.get("name"));
                        f.put("mime", saved.get("mimeType"));
                        f.put("size", saved.get("sizeBytes"));
                        f.put("source", "generated");
                        live.fileAcc.add(f);
                    }
                } catch (Exception e) {
                    log.warn("persist artifact failed: {}", e.getMessage());
                }
            }
            case "heartbeat" -> { /* pass-through */ }
            default -> { /* pass-through */ }
        }
        if (data.containsKey("contentBase64")) {
            data.remove("contentBase64");
        }
        if (data.containsKey("textContent") && "file".equals(eventName)) {
            Object tc = data.get("textContent");
            if (tc instanceof String s && s.length() > 4000) {
                data.remove("textContent");
                data.put("textTruncated", true);
            }
        }
        publish(runId, eventName, data);
    }

    private String buildContentJson(
            String contentText,
            List<Map<String, Object>> citations,
            List<Map<String, Object>> files
    ) {
        Map<String, Object> root = new LinkedHashMap<>();
        List<Map<String, Object>> blocks = new ArrayList<>();
        if (contentText != null && !contentText.isBlank()) {
            blocks.add(Map.of("type", "text", "text", contentText));
        }
        if (citations != null) {
            for (Map<String, Object> c : citations) {
                Map<String, Object> b = new LinkedHashMap<>(c);
                b.put("type", "citation");
                blocks.add(b);
            }
        }
        if (files != null) {
            for (Map<String, Object> f : files) {
                Map<String, Object> b = new LinkedHashMap<>(f);
                b.put("type", "file");
                blocks.add(b);
            }
        }
        root.put("blocks", blocks);
        root.put("citations", citations == null ? List.of() : citations);
        root.put("files", files == null ? List.of() : files);
        return toJson(root);
    }

    private Map<String, Object> persistGeneratedText(
            long sessionId, long tenantId, long userId, long messageId, String fileName, String content
    ) throws IOException {
        if (!fileName.contains(".")) fileName = fileName + ".md";
        return persistGeneratedBytes(
                sessionId, tenantId, userId, messageId, fileName,
                "text/markdown", content.getBytes(StandardCharsets.UTF_8));
    }

    private Map<String, Object> persistGeneratedBytes(
            long sessionId, long tenantId, long userId, long messageId,
            String fileName, String mimeType, byte[] bytes
    ) throws IOException {
        Path dir = Path.of(uploadDir, "assistant", String.valueOf(tenantId), String.valueOf(sessionId));
        Files.createDirectories(dir);
        String stored = UUID.randomUUID().toString().replace("-", "") + "_" + fileName.replaceAll("[\\\\/:*?\"<>|]+", "_");
        Path target = dir.resolve(stored);
        Files.write(target, bytes);
        String storageKey = "assistant/" + tenantId + "/" + sessionId + "/" + stored;
        KeyHolder kh = new GeneratedKeyHolder();
        String finalName = fileName;
        String finalMime = mimeType == null ? "application/octet-stream" : mimeType;
        long size = bytes == null ? 0 : bytes.length;
        final long msgId = messageId;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_file
                      (tenant_id, user_id, session_id, message_id, source, visibility, name, mime_type, size_bytes, storage_key, index_status, created_at)
                    VALUES (?, ?, ?, ?, 'generated', 'private', ?, ?, ?, ?, 'none', NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setLong(3, sessionId);
            if (msgId <= 0) ps.setObject(4, null);
            else ps.setLong(4, msgId);
            ps.setString(5, finalName);
            ps.setString(6, finalMime);
            ps.setLong(7, size);
            ps.setString(8, storageKey);
            return ps;
        }, kh);
        return getFile(kh.getKey().longValue(), tenantId, userId);
    }

    private void attachResourceRef(long sessionId, long tenantId, long userId, long resourceId) {
        Integer exists = jdbc.queryForObject("""
                SELECT COUNT(*) FROM ai_assistant_file
                WHERE session_id = ? AND resource_id = ? AND source = 'resource_ref'
                """, Integer.class, sessionId, resourceId);
        if (exists != null && exists > 0) return;
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, name, ext, file_size FROM resource WHERE id = ? LIMIT 1", resourceId);
        if (rows.isEmpty()) return;
        Map<String, Object> r = rows.get(0);
        jdbc.update("""
                INSERT INTO ai_assistant_file
                  (tenant_id, user_id, session_id, source, visibility, name, mime_type, size_bytes, resource_id, index_status, created_at)
                VALUES (?, ?, ?, 'resource_ref', 'private', ?, ?, ?, ?, 'none', NOW())
                """, tenantId, userId, sessionId, r.get("name"), null, r.get("file_size"), resourceId);
    }

    /**
     * 构建资源上下文：优先命中资源表抽取缓存；未命中则标记 pending，由流式阶段解析并回写缓存。
     */
    private List<Map<String, Object>> buildResourceContexts(
            List<Number> resourceIds, long tenantId, long userId, String role
    ) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (resourceIds == null) return out;
        for (Number rid : resourceIds) {
            if (rid == null) continue;
            try {
                List<Map<String, Object>> rows = jdbc.queryForList("""
                        SELECT id, name, ext, file_path, team_id, file_size,
                               extract_text, extract_method, extract_hash, extract_chars, extract_at
                        FROM resource WHERE id = ? LIMIT 1
                        """, rid.longValue());
                if (rows.isEmpty()) continue;
                Map<String, Object> r = rows.get(0);
                Long teamId = longVal(r.get("team_id"));
                if (teamId != null) {
                    assertTeamAccess(teamId, tenantId, userId, role);
                }
                Map<String, Object> ctx = new LinkedHashMap<>();
                ctx.put("resourceId", r.get("id"));
                ctx.put("title", r.get("name"));
                ctx.put("ext", r.get("ext"));
                String name = str(r.get("name"));
                String ext = str(r.get("ext"));
                if (ext == null || ext.isBlank()) ext = extension(name == null ? "" : name);
                Path disk = resolveResourceDiskPath(str(r.get("file_path")));
                if (disk == null) {
                    ctx.put("snippet", "【文件】" + name + "（源文件不存在或路径不可解析）");
                    out.add(ctx);
                    continue;
                }
                String fileHash = sha256File(disk);
                String cachedHash = str(r.get("extract_hash"));
                String cachedText = str(r.get("extract_text"));
                if (fileHash != null && fileHash.equals(cachedHash) && cachedText != null && !cachedText.isBlank()) {
                    ctx.put("snippet", truncate(cachedText, 14000));
                    ctx.put("fromCache", true);
                    ctx.put("extractMethod", r.get("extract_method"));
                    ctx.put("ocr", "ocr".equals(String.valueOf(r.get("extract_method"))));
                    out.add(ctx);
                    continue;
                }
                if (isTextExt(ext)) {
                    try {
                        String text = truncate(Files.readString(disk, StandardCharsets.UTF_8), 14000);
                        ctx.put("snippet", text);
                        saveResourceExtractCache(longVal(r.get("id")), text, "text", fileHash, null);
                    } catch (Exception e) {
                        ctx.put("snippet", "【文件】" + name + "（文本读取失败）");
                    }
                    out.add(ctx);
                    continue;
                }
                // 待流式抽取（可能 OCR）
                Map<String, Object> job = new LinkedHashMap<>();
                job.put("path", disk.toAbsolutePath().toString());
                job.put("ext", ext);
                job.put("title", name);
                job.put("resourceId", r.get("id"));
                job.put("maxChars", 14000);
                job.put("fileHash", fileHash);
                ctx.put("_extractJob", job);
                ctx.put("snippet", "");
                out.add(ctx);
            } catch (Exception e) {
                log.warn("resource context {}: {}", rid, e.getMessage());
            }
        }
        return out;
    }

    private List<Map<String, Object>> buildAttachmentContexts(
            List<Number> fileIds, long tenantId, long userId
    ) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (fileIds == null) return out;
        for (Number fid : fileIds) {
            if (fid == null) continue;
            try {
                Map<String, Object> f = getFile(fid.longValue(), tenantId, userId);
                Map<String, Object> ctx = new LinkedHashMap<>();
                ctx.put("fileId", f.get("id"));
                ctx.put("title", f.get("name"));
                ctx.put("mime", f.get("mimeType"));
                String name = str(f.get("name"));
                String ext = extension(name == null ? "" : name);
                Path path = resolveFilePath(fid.longValue(), tenantId, userId);
                if (isTextExt(ext)) {
                    String text = Files.readString(path, StandardCharsets.UTF_8);
                    ctx.put("snippet", truncate(text, 12000));
                    out.add(ctx);
                } else {
                    Map<String, Object> job = new LinkedHashMap<>();
                    job.put("path", path.toAbsolutePath().toString());
                    job.put("ext", ext);
                    job.put("title", name);
                    job.put("fileId", f.get("id"));
                    job.put("maxChars", 12000);
                    ctx.put("_extractJob", job);
                    ctx.put("snippet", "");
                    out.add(ctx);
                }
            } catch (Exception e) {
                log.warn("attachment context {}: {}", fid, e.getMessage());
            }
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private void resolveContextsWithProgress(long runId, Map<String, Object> aiRequest) {
        List<Map<String, Object>> resourceContexts = castMapList(aiRequest.get("resourceContexts"));
        List<Map<String, Object>> attachmentContexts = castMapList(aiRequest.get("attachmentContexts"));
        if (resourceContexts.isEmpty() && attachmentContexts.isEmpty()) {
            return;
        }

        List<Map<String, Object>> jobs = new ArrayList<>();
        int cacheHits = 0;
        int readyHits = 0;
        for (Map<String, Object> ctx : resourceContexts) {
            if (Boolean.TRUE.equals(ctx.get("fromCache"))) cacheHits++;
            else if (ctx.get("_extractJob") == null && ctx.get("snippet") != null
                    && !String.valueOf(ctx.get("snippet")).isBlank()) readyHits++;
            Object job = ctx.get("_extractJob");
            if (job instanceof Map<?, ?> m) {
                jobs.add(new LinkedHashMap<>((Map<String, Object>) m));
            }
        }
        for (Map<String, Object> ctx : attachmentContexts) {
            Object job = ctx.get("_extractJob");
            if (job instanceof Map<?, ?> m) {
                jobs.add(new LinkedHashMap<>((Map<String, Object>) m));
            } else if (ctx.get("snippet") != null && !String.valueOf(ctx.get("snippet")).isBlank()) {
                readyHits++;
            }
        }

        publish(runId, "step_start", Map.of(
                "stepNo", 0,
                "stepKey", "extract",
                "title", "正在加载参考资料…"
        ));
        upsertStep(runId, Map.of(
                "stepNo", 0,
                "stepKey", "extract",
                "title", "正在加载参考资料…"
        ), "running");

        if (cacheHits > 0) {
            publish(runId, "ocr_progress", Map.of(
                    "phase", "cache",
                    "label", "命中资料缓存 " + cacheHits + " 份（跳过重复 OCR/解析）",
                    "page", 0,
                    "total", 0
            ));
        }
        if (readyHits > 0 && jobs.isEmpty()) {
            publish(runId, "ocr_progress", Map.of(
                    "phase", "text_layer",
                    "label", "文字层/文本已就绪 " + readyHits + " 份（无需 OCR）",
                    "page", 0,
                    "total", 0
            ));
        }

        Map<String, Map<String, Object>> extracted = Map.of();
        if (!jobs.isEmpty()) {
            extracted = callAiExtractStream(runId, jobs);
        }

        for (Map<String, Object> ctx : resourceContexts) {
            Object rid = ctx.get("resourceId");
            if (rid == null) continue;
            Map<String, Object> item = extracted.get("resource:" + rid);
            ctx.remove("_extractJob");
            if (item != null) {
                String text = str(item.get("text"));
                ctx.put("snippet", text == null || text.isBlank()
                        ? "【文件】" + ctx.get("title") + "（未能解析全文）"
                        : text);
                ctx.put("extractMethod", item.get("method"));
                ctx.put("fromCache", false);
                ctx.put("ocr", Boolean.TRUE.equals(item.get("ocr")));
                String hash = null;
                for (Map<String, Object> j : jobs) {
                    if (rid.toString().equals(String.valueOf(j.get("resourceId")))) {
                        hash = str(j.get("fileHash"));
                        break;
                    }
                }
                if (longVal(rid) != null) {
                    saveResourceExtractCache(
                            longVal(rid),
                            text,
                            str(item.get("method")),
                            hash,
                            item.get("ok") != null && Boolean.FALSE.equals(item.get("ok")) ? str(item.get("error")) : null
                    );
                }
                String method = str(item.get("method"));
                String tip;
                if ("ocr".equals(method)) {
                    tip = "OCR 识别完成 · " + ctx.get("title") + "（" + (item.get("chars") == null ? "?" : item.get("chars")) + " 字）";
                } else if ("text_layer".equals(method)) {
                    tip = "文字层解析完成（非扫描件，无需 OCR）· " + ctx.get("title");
                } else {
                    tip = "解析完成 · " + ctx.get("title") + "（" + method + "）";
                }
                publish(runId, "ocr_progress", Map.of(
                        "phase", method == null ? "done" : method,
                        "label", tip,
                        "title", String.valueOf(ctx.get("title")),
                        "resourceId", rid,
                        "page", 0,
                        "total", 0
                ));
            } else if (ctx.get("snippet") == null || String.valueOf(ctx.get("snippet")).isBlank()) {
                ctx.put("snippet", "【文件】" + ctx.get("title") + "（解析未完成）");
            }
        }
        for (Map<String, Object> ctx : attachmentContexts) {
            Object fid = ctx.get("fileId");
            if (fid == null) continue;
            Map<String, Object> item = extracted.get("file:" + fid);
            ctx.remove("_extractJob");
            if (item != null) {
                String text = str(item.get("text"));
                ctx.put("snippet", text == null || text.isBlank() ? "（附件未能解析全文）" : text);
                ctx.put("extractMethod", item.get("method"));
                ctx.put("ocr", Boolean.TRUE.equals(item.get("ocr")));
            }
        }
        aiRequest.put("resourceContexts", resourceContexts);
        aiRequest.put("attachmentContexts", attachmentContexts);

        String summary;
        if (!jobs.isEmpty()) {
            long ocrCount = extracted.values().stream().filter(m -> Boolean.TRUE.equals(m.get("ocr"))).count();
            summary = "资料解析完成（新解析 " + jobs.size() + " 份"
                    + (ocrCount > 0 ? "，其中 OCR " + ocrCount + " 份" : "，文字层/格式解析")
                    + (cacheHits > 0 ? "，缓存 " + cacheHits + " 份" : "")
                    + "）";
        } else if (cacheHits > 0) {
            summary = "资料已就绪（全部命中缓存 " + cacheHits + " 份，跳过重复识别）";
        } else {
            summary = "资料已就绪（文字层/文本，无需 OCR）";
        }
        publish(runId, "step_end", Map.of(
                "stepNo", 0,
                "status", "completed",
                "outputSummary", summary
        ));
        upsertStep(runId, Map.of(
                "stepNo", 0,
                "stepKey", "extract",
                "title", "解析参考资料",
                "status", "completed",
                "outputSummary", summary
        ), "completed");
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> castMapList(Object raw) {
        if (!(raw instanceof List<?> list)) return new ArrayList<>();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object o : list) {
            if (o instanceof Map<?, ?> m) {
                out.add(new LinkedHashMap<>((Map<String, Object>) m));
            }
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Map<String, Object>> callAiExtractStream(long runId, List<Map<String, Object>> items) {
        Map<String, Map<String, Object>> result = new LinkedHashMap<>();
        if (items == null || items.isEmpty()) return result;
        try {
            HttpURLConnection conn = (HttpURLConnection) URI.create(aiBaseUrl + "/api/assistant/v1/extract-stream").toURL().openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(5_000);
            conn.setReadTimeout(600_000);
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            conn.setRequestProperty("Accept", "text/event-stream");
            try (OutputStream os = conn.getOutputStream()) {
                os.write(objectMapper.writeValueAsBytes(Map.of("items", items)));
            }
            int code = conn.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
            if (stream == null) return result;
            if (code < 200 || code >= 300) {
                String err = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
                log.warn("extract-stream HTTP {}: {}", code, truncate(err, 300));
                return result;
            }
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String eventName = "message";
                StringBuilder data = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    if (Boolean.TRUE.equals(cancelFlags.get(runId))) {
                        break;
                    }
                    if (line.isEmpty()) {
                        if (data.length() > 0) {
                            handleExtractStreamEvent(runId, eventName, data.toString(), result);
                            data.setLength(0);
                            eventName = "message";
                        }
                        continue;
                    }
                    if (line.startsWith("event:")) {
                        eventName = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        if (data.length() > 0) data.append('\n');
                        data.append(line.substring(5).trim());
                    }
                }
                if (data.length() > 0 && !Boolean.TRUE.equals(cancelFlags.get(runId))) {
                    handleExtractStreamEvent(runId, eventName, data.toString(), result);
                }
            }
        } catch (Exception e) {
            log.warn("ai extract-stream failed: {}", e.getMessage());
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private void handleExtractStreamEvent(
            long runId,
            String eventName,
            String dataJson,
            Map<String, Map<String, Object>> result
    ) {
        Map<String, Object> data;
        try {
            data = objectMapper.readValue(dataJson, Map.class);
        } catch (Exception e) {
            return;
        }
        if ("progress".equals(eventName)) {
            String title = str(data.get("title"));
            String phase = str(data.get("phase"));
            Object page = data.get("page");
            Object total = data.get("total");
            String label;
            if ("ocr".equals(phase) && page != null && total != null
                    && !"0".equals(String.valueOf(page)) && !"0".equals(String.valueOf(total))) {
                label = "正在 OCR 第 " + page + "/" + total + " 页"
                        + (title == null ? "" : " · " + title);
            } else if ("text_layer".equals(phase)) {
                label = "检测到 PDF 文字层，直接提取（无需 OCR）"
                        + (title == null ? "" : " · " + title);
            } else if ("start".equals(phase)) {
                label = "开始解析" + (title == null ? "" : " · " + title);
            } else {
                label = "解析资料中" + (title == null ? "" : " · " + title);
            }
            Map<String, Object> payload = new LinkedHashMap<>(data);
            payload.put("label", label);
            publish(runId, "ocr_progress", payload);
        } else if ("item".equals(eventName) || "done".equals(eventName)) {
            if ("item".equals(eventName)) {
                putExtractItem(result, data);
            } else if (data.get("items") instanceof List<?> list) {
                for (Object o : list) {
                    if (o instanceof Map<?, ?> m) {
                        putExtractItem(result, (Map<String, Object>) m);
                    }
                }
            }
        }
    }

    private void putExtractItem(Map<String, Map<String, Object>> result, Map<String, Object> data) {
        if (data.get("resourceId") != null) {
            result.put("resource:" + data.get("resourceId"), data);
        }
        if (data.get("fileId") != null) {
            result.put("file:" + data.get("fileId"), data);
        }
    }

    private void saveResourceExtractCache(Long resourceId, String text, String method, String hash, String error) {
        if (resourceId == null) return;
        try {
            jdbc.update("""
                    UPDATE resource
                    SET extract_text = ?, extract_method = ?, extract_hash = ?,
                        extract_chars = ?, extract_at = NOW(), extract_error = ?
                    WHERE id = ?
                    """,
                    text,
                    method,
                    hash,
                    text == null ? 0 : text.length(),
                    error,
                    resourceId
            );
        } catch (Exception e) {
            // 迁移未执行时不阻断主流程
            log.warn("save extract cache failed (resource {}): {}", resourceId, e.getMessage());
        }
    }

    private String sha256File(Path path) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] bytes = Files.readAllBytes(path);
            return HexFormat.of().formatHex(md.digest(bytes));
        } catch (Exception e) {
            log.warn("hash file failed: {}", e.getMessage());
            return null;
        }
    }

    private Path resolveResourceDiskPath(String filePath) {
        if (filePath == null || filePath.isBlank()) return null;
        Path uploadBase = Path.of(uploadDir).toAbsolutePath().normalize();
        List<Path> candidates = new ArrayList<>();
        if (filePath.startsWith("uploads/")) {
            candidates.add(uploadBase.resolve(filePath.substring("uploads/".length())).normalize());
            candidates.add(uploadBase.getParent() == null
                    ? null
                    : uploadBase.getParent().resolve(filePath).normalize());
        }
        candidates.add(uploadBase.resolve(filePath).normalize());
        candidates.add(Path.of(filePath).toAbsolutePath().normalize());
        // 兼容 static/ppt-templates 等相对仓库根路径
        Path cwd = Path.of("").toAbsolutePath().normalize();
        candidates.add(cwd.resolve(filePath).normalize());
        if (cwd.getParent() != null) {
            candidates.add(cwd.getParent().resolve(filePath).normalize());
            if (cwd.getFileName() != null && "backend".equals(cwd.getFileName().toString()) && cwd.getParent() != null) {
                candidates.add(cwd.getParent().resolve(filePath).normalize());
            }
        }
        for (Path p : candidates) {
            if (p != null && Files.exists(p) && Files.isRegularFile(p)) {
                return p;
            }
        }
        return null;
    }

    private static boolean isTextExt(String ext) {
        if (ext == null) return false;
        return Set.of(
                "txt", "md", "markdown", "csv", "json", "xml", "html", "htm",
                "java", "py", "js", "ts", "vue", "css", "scss", "sql", "yml", "yaml", "log"
        ).contains(ext.toLowerCase());
    }

    /**
     * 对某条用户消息重新生成助手回答（不新增用户消息）。
     */
    public SseEmitter regenerate(
            Long sessionId,
            Long userMessageId,
            Long tenantId,
            Long userId,
            String role
    ) {
        Map<String, Object> session = getSession(sessionId, tenantId, userId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, role, content_text AS contentText
                FROM ai_assistant_message
                WHERE id = ? AND session_id = ? AND role = 'user'
                LIMIT 1
                """, userMessageId, sessionId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "用户消息不存在");
        }
        String content = str(rows.get(0).get("contentText"));
        if (content == null || content.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "原消息内容为空");
        }

        // 收集该用户消息附近引用的资源/附件（会话内）
        List<Number> resourceIds = new ArrayList<>();
        List<Number> attachmentFileIds = new ArrayList<>();
        List<Map<String, Object>> files = jdbc.queryForList("""
                SELECT id, source, resource_id AS resourceId
                FROM ai_assistant_file WHERE session_id = ? ORDER BY id DESC LIMIT 30
                """, sessionId);
        for (Map<String, Object> f : files) {
            if ("resource_ref".equals(String.valueOf(f.get("source"))) && f.get("resourceId") != null) {
                resourceIds.add(((Number) f.get("resourceId")));
            } else if ("upload".equals(String.valueOf(f.get("source")))) {
                attachmentFileIds.add((Number) f.get("id"));
            }
        }

        long assistantMsgId = insertMessage(sessionId, tenantId, userId, "assistant", "", null, "pending", null, null);
        String traceId = UUID.randomUUID().toString().replace("-", "");
        long runId = insertRun(sessionId, tenantId, userId, userMessageId, assistantMsgId, traceId, Map.of(
                "regenerate", true,
                "userMessageId", userMessageId
        ));
        jdbc.update("UPDATE ai_assistant_message SET run_id = ? WHERE id = ?", runId, assistantMsgId);
        jdbc.update("""
                UPDATE ai_assistant_session
                SET message_count = message_count + 1, last_message_at = NOW(), updated_at = NOW()
                WHERE id = ?
                """, sessionId);

        List<Map<String, Object>> history = loadHistoryForModel(sessionId, 20);
        // 去掉未完成的空助手消息，避免污染
        history = history.stream()
                .filter(m -> !( "assistant".equals(String.valueOf(m.get("role")))
                        && (m.get("content") == null || String.valueOf(m.get("content")).isBlank())))
                .toList();
        // 保证以该 user 消息为最后一轮
        if (history.isEmpty() || !"user".equals(String.valueOf(history.get(history.size() - 1).get("role")))) {
            history = new ArrayList<>(history);
            history.add(Map.of("role", "user", "content", content));
        }

        Long teamId = longVal(session.get("teamId"));
        List<Map<String, Object>> resourceContexts = buildResourceContexts(resourceIds, tenantId, userId, role);
        List<Map<String, Object>> attachmentContexts = buildAttachmentContexts(attachmentFileIds, tenantId, userId);

        Map<String, Object> aiRequest = new LinkedHashMap<>();
        aiRequest.put("traceId", traceId);
        aiRequest.put("tenantId", tenantId);
        aiRequest.put("userId", userId);
        aiRequest.put("role", role);
        aiRequest.put("teamId", teamId);
        aiRequest.put("sessionId", sessionId);
        aiRequest.put("runId", runId);
        aiRequest.put("userMessageId", userMessageId);
        aiRequest.put("assistantMessageId", assistantMsgId);
        aiRequest.put("messages", history);
        aiRequest.put("memories", loadMemoriesForInject(tenantId, userId));
        aiRequest.put("attachmentFileIds", attachmentFileIds);
        aiRequest.put("resourceIds", resourceIds);
        aiRequest.put("resourceContexts", resourceContexts);
        aiRequest.put("attachmentContexts", attachmentContexts);
        aiRequest.put("options", Map.of());
        Object ctx = session.get("contextJson");
        if (ctx instanceof Map<?, ?>) {
            aiRequest.put("sessionSlots", ctx);
        }
        aiRequest.put("backendBaseUrl", resolveBackendInternalUrl());
        aiRequest.put("internalToken", internalToken);

        LiveRun live = new LiveRun(runId, sessionId, assistantMsgId, userMessageId);
        liveRuns.put(runId, live);
        cancelFlags.put(runId, false);
        SseEmitter emitter = new SseEmitter(0L);
        attachSubscriber(live, emitter);
        streamExecutor.execute(() -> runAssistantJob(live, tenantId, userId, teamId, aiRequest));
        return emitter;
    }

    private void upsertStep(long runId, Map<String, Object> data, String status) {
        Integer stepNo = data.get("stepNo") instanceof Number n ? n.intValue() : null;
        if (stepNo == null) return;
        String stepKey = str(data.get("stepKey")) == null ? "step" : str(data.get("stepKey"));
        String title = str(data.get("title")) == null ? stepKey : str(data.get("title"));
        String outputSummary = str(data.get("outputSummary"));
        Long sessionId = jdbc.queryForObject("SELECT session_id FROM ai_assistant_run WHERE id = ?", Long.class, runId);
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM ai_assistant_run_step WHERE run_id = ? AND step_no = ?",
                Integer.class, runId, stepNo);
        if (exists != null && exists > 0) {
            jdbc.update("""
                    UPDATE ai_assistant_run_step
                    SET status = ?, output_summary = COALESCE(?, output_summary),
                        finished_at = CASE WHEN ? IN ('completed','failed','skipped') THEN NOW() ELSE finished_at END
                    WHERE run_id = ? AND step_no = ?
                    """, status, outputSummary, status, runId, stepNo);
        } else {
            jdbc.update("""
                    INSERT INTO ai_assistant_run_step
                      (run_id, session_id, step_no, step_key, title, status, output_summary, started_at, finished_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NOW(), ?)
                    """, runId, sessionId, stepNo, stepKey, title, status, outputSummary,
                    Set.of("completed", "failed", "skipped").contains(status) ? Timestamp.valueOf(LocalDateTime.now()) : null);
        }
    }

    // ── Files ─────────────────────────────────────────────────

    @Transactional
    public Map<String, Object> uploadFile(Long sessionId, Long tenantId, Long userId, MultipartFile file) throws IOException {
        getSession(sessionId, tenantId, userId);
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件为空");
        }
        String original = file.getOriginalFilename() == null ? "file" : file.getOriginalFilename();
        String ext = extension(original);
        if (!ALLOWED_EXT.contains(ext)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的文件类型: " + ext);
        }
        if (file.getSize() > 20L * 1024 * 1024) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "单文件不能超过 20MB");
        }
        Path dir = Path.of(uploadDir, "assistant", String.valueOf(tenantId), String.valueOf(sessionId));
        Files.createDirectories(dir);
        String stored = UUID.randomUUID().toString().replace("-", "") + (ext.isEmpty() ? "" : "." + ext);
        Path target = dir.resolve(stored);
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        String storageKey = "assistant/" + tenantId + "/" + sessionId + "/" + stored;
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_file
                      (tenant_id, user_id, session_id, source, visibility, name, mime_type, size_bytes, storage_key, index_status, created_at)
                    VALUES (?, ?, ?, 'upload', 'private', ?, ?, ?, ?, 'skipped', NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setLong(3, sessionId);
            ps.setString(4, original);
            ps.setString(5, file.getContentType());
            ps.setLong(6, file.getSize());
            ps.setString(7, storageKey);
            return ps;
        }, kh);
        return getFile(kh.getKey().longValue(), tenantId, userId);
    }

    public List<Map<String, Object>> listFiles(Long sessionId, Long tenantId, Long userId) {
        getSession(sessionId, tenantId, userId);
        return jdbc.queryForList("""
                SELECT id, session_id AS sessionId, source, visibility, name, mime_type AS mimeType,
                       size_bytes AS sizeBytes, resource_id AS resourceId, index_status AS indexStatus,
                       created_at AS createdAt
                FROM ai_assistant_file WHERE session_id = ? ORDER BY id DESC
                """, sessionId);
    }

    public Map<String, Object> getFile(Long fileId, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, tenant_id AS tenantId, user_id AS userId, session_id AS sessionId, message_id AS messageId,
                       source, visibility, name, mime_type AS mimeType, size_bytes AS sizeBytes,
                       storage_key AS storageKey, resource_id AS resourceId, index_status AS indexStatus,
                       created_at AS createdAt
                FROM ai_assistant_file WHERE id = ? AND tenant_id = ? AND user_id = ?
                """, fileId, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return rows.get(0);
    }

    public Path resolveFilePath(Long fileId, Long tenantId, Long userId) {
        Map<String, Object> file = getFile(fileId, tenantId, userId);
        String key = str(file.get("storageKey"));
        if (key == null || key.isBlank()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件无存储路径");
        }
        Path path = Path.of(uploadDir).resolve(key).normalize();
        if (!path.startsWith(Path.of(uploadDir).toAbsolutePath().normalize()) && !path.isAbsolute()) {
            path = Path.of(uploadDir, key).normalize();
        }
        if (!Files.exists(path)) {
            // try relative to cwd
            Path alt = Path.of(uploadDir).toAbsolutePath().resolve(key).normalize();
            if (Files.exists(alt)) return alt;
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件内容不存在");
        }
        return path;
    }

    @Transactional
    public void deleteFile(Long fileId, Long tenantId, Long userId) throws IOException {
        Map<String, Object> file = getFile(fileId, tenantId, userId);
        if (!"upload".equals(String.valueOf(file.get("source"))) && !"generated".equals(String.valueOf(file.get("source")))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该文件类型不可删除");
        }
        String key = str(file.get("storageKey"));
        jdbc.update("DELETE FROM ai_assistant_file WHERE id = ?", fileId);
        if (key != null) {
            Path path = Path.of(uploadDir).toAbsolutePath().resolve(key).normalize();
            Files.deleteIfExists(path);
        }
    }

    @Transactional
    public Map<String, Object> saveCodeAsFile(Long tenantId, Long userId, Map<String, Object> body) throws IOException {
        Long sessionId = longVal(body.get("sessionId"));
        getSession(sessionId, tenantId, userId);
        String code = str(body.get("code"));
        String fileName = str(body.get("fileName"));
        if (code == null || code.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "代码为空");
        }
        if (fileName == null || fileName.isBlank()) {
            String lang = str(body.get("language"));
            fileName = "snippet." + (lang == null || lang.isBlank() ? "txt" : lang);
        }
        Path dir = Path.of(uploadDir, "assistant", String.valueOf(tenantId), String.valueOf(sessionId));
        Files.createDirectories(dir);
        String stored = UUID.randomUUID().toString().replace("-", "") + "_" + fileName.replaceAll("[\\\\/]+", "_");
        Path target = dir.resolve(stored);
        Files.writeString(target, code, StandardCharsets.UTF_8);
        String storageKey = "assistant/" + tenantId + "/" + sessionId + "/" + stored;
        KeyHolder kh = new GeneratedKeyHolder();
        String finalName = fileName;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_file
                      (tenant_id, user_id, session_id, source, visibility, name, mime_type, size_bytes, storage_key, index_status, created_at)
                    VALUES (?, ?, ?, 'generated', 'private', ?, 'text/plain', ?, ?, 'none', NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setLong(3, sessionId);
            ps.setString(4, finalName);
            ps.setLong(5, code.getBytes(StandardCharsets.UTF_8).length);
            ps.setString(6, storageKey);
            return ps;
        }, kh);
        return getFile(kh.getKey().longValue(), tenantId, userId);
    }

    // ── Memory ────────────────────────────────────────────────

    public List<Map<String, Object>> listMemories(Long tenantId, Long userId) {
        return jdbc.queryForList("""
                SELECT id, team_id AS teamId, memory_type AS memoryType, content, importance, source,
                       source_session_id AS sourceSessionId, status, created_at AS createdAt, updated_at AS updatedAt
                FROM ai_assistant_memory
                WHERE tenant_id = ? AND user_id = ? AND status = 'active'
                ORDER BY importance DESC, updated_at DESC
                """, tenantId, userId);
    }

    @Transactional
    public Map<String, Object> createMemory(Long tenantId, Long userId, Map<String, Object> body) {
        String content = str(body.get("content"));
        if (content == null || content.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "记忆内容不能为空");
        }
        content = content.trim();
        if (content.length() > 500) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "记忆不能超过 500 字");
        }
        if (SCORE_LIKE.matcher(content).find()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "记忆中请勿写入具体分数，分数请在对话中按需读取");
        }
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*) FROM ai_assistant_memory
                WHERE tenant_id = ? AND user_id = ? AND status = 'active'
                """, Integer.class, tenantId, userId);
        if (count != null && count >= MEMORY_LIMIT) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "个人记忆已达上限 " + MEMORY_LIMIT + " 条，请先删除旧记忆");
        }
        String type = str(body.get("memoryType"));
        if (type == null || type.isBlank()) type = "manual";
        Long teamId = longVal(body.get("teamId"));
        int importance = body.get("importance") instanceof Number n ? Math.min(5, Math.max(1, n.intValue())) : 3;
        KeyHolder kh = new GeneratedKeyHolder();
        String finalType = type;
        String finalContent = content;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_memory
                      (tenant_id, user_id, team_id, memory_type, content, importance, source, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'manual', 'active', NOW(), NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            if (teamId == null) ps.setObject(3, null);
            else ps.setLong(3, teamId);
            ps.setString(4, finalType);
            ps.setString(5, finalContent);
            ps.setInt(6, importance);
            return ps;
        }, kh);
        return getMemory(kh.getKey().longValue(), tenantId, userId);
    }

    public Map<String, Object> getMemory(Long id, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, team_id AS teamId, memory_type AS memoryType, content, importance, source,
                       status, created_at AS createdAt, updated_at AS updatedAt
                FROM ai_assistant_memory
                WHERE id = ? AND tenant_id = ? AND user_id = ? AND status = 'active'
                """, id, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "记忆不存在");
        }
        return rows.get(0);
    }

    @Transactional
    public Map<String, Object> patchMemory(Long id, Long tenantId, Long userId, Map<String, Object> body) {
        getMemory(id, tenantId, userId);
        if (body.containsKey("content")) {
            String content = str(body.get("content"));
            if (content == null || content.isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "记忆内容不能为空");
            }
            if (SCORE_LIKE.matcher(content).find()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "记忆中请勿写入具体分数");
            }
            jdbc.update("UPDATE ai_assistant_memory SET content = ?, updated_at = NOW() WHERE id = ?", content.trim(), id);
        }
        if (body.containsKey("importance") && body.get("importance") instanceof Number n) {
            jdbc.update("UPDATE ai_assistant_memory SET importance = ?, updated_at = NOW() WHERE id = ?",
                    Math.min(5, Math.max(1, n.intValue())), id);
        }
        if (body.containsKey("memoryType") && str(body.get("memoryType")) != null) {
            jdbc.update("UPDATE ai_assistant_memory SET memory_type = ?, updated_at = NOW() WHERE id = ?",
                    str(body.get("memoryType")), id);
        }
        return getMemory(id, tenantId, userId);
    }

    @Transactional
    public void deleteMemory(Long id, Long tenantId, Long userId) {
        getMemory(id, tenantId, userId);
        jdbc.update("UPDATE ai_assistant_memory SET status = 'deleted', updated_at = NOW() WHERE id = ?", id);
    }

    // ── Share ─────────────────────────────────────────────────

    @Transactional
    public Map<String, Object> shareSession(Long sessionId, Long tenantId, Long userId, String role, Map<String, Object> body) throws IOException {
        Map<String, Object> session = getSession(sessionId, tenantId, userId);
        Long teamId = longVal(body.get("teamId"));
        if (teamId == null) {
            teamId = longVal(session.get("teamId"));
        }
        if (teamId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请指定要分享到的团队");
        }
        assertTeamAccess(teamId, tenantId, userId, role);
        String mode = str(body.get("shareMode"));
        if (mode == null || mode.isBlank()) mode = "summary";
        if (!Set.of("summary", "full_text", "artifacts_only").contains(mode)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的分享模式");
        }
        boolean includeThinking = Boolean.TRUE.equals(body.get("includeThinking"));
        List<Map<String, Object>> messages = listMessages(sessionId, tenantId, userId, null, 200);
        String markdown = buildShareMarkdown(session, messages, mode, includeThinking);
        String fileName = "对话分享-" + session.get("title") + "-" + System.currentTimeMillis() + ".md";
        fileName = fileName.replaceAll("[\\\\/:*?\"<>|]", "_");

        Path dir = Path.of(uploadDir, "assistant", String.valueOf(tenantId), String.valueOf(sessionId), "exports");
        Files.createDirectories(dir);
        String stored = UUID.randomUUID().toString().replace("-", "") + ".md";
        Path target = dir.resolve(stored);
        Files.writeString(target, markdown, StandardCharsets.UTF_8);
        String storageKey = "assistant/" + tenantId + "/" + sessionId + "/exports/" + stored;

        KeyHolder fileKh = new GeneratedKeyHolder();
        String finalFileName = fileName;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_file
                      (tenant_id, user_id, session_id, source, visibility, name, mime_type, size_bytes, storage_key, index_status, created_at)
                    VALUES (?, ?, ?, 'export', 'private', ?, 'text/markdown', ?, ?, 'none', NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setLong(3, sessionId);
            ps.setString(4, finalFileName);
            ps.setLong(5, markdown.getBytes(StandardCharsets.UTF_8).length);
            ps.setString(6, storageKey);
            return ps;
        }, fileKh);
        long fileId = fileKh.getKey().longValue();

        // 写入资源中心（团队可见文件）
        Integer resourceId = insertTeamResource(teamId, userId, finalFileName, "md", storageKey, markdown.getBytes(StandardCharsets.UTF_8).length, str(body.get("folderKey")));

        boolean makeSearchable = Boolean.TRUE.equals(body.get("makeSearchable"));
        if (makeSearchable && resourceId != null) {
            try {
                jdbc.update("UPDATE resource SET knowledge_status = 'pending' WHERE id = ?", resourceId);
                jdbc.update("""
                        INSERT INTO ai_knowledge_index_job (tenant_id, team_id, resource_id, action, status, created_at, updated_at)
                        VALUES (?, ?, ?, 'upsert', 'pending', NOW(), NOW())
                        """, tenantId, teamId, resourceId);
            } catch (Exception e) {
                log.warn("knowledge index enqueue failed: {}", e.getMessage());
            }
        }

        KeyHolder shareKh = new GeneratedKeyHolder();
        Long finalTeamId = teamId;
        String finalMode = mode;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_share
                      (tenant_id, user_id, session_id, team_id, share_mode, include_thinking, resource_id, file_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            ps.setLong(3, sessionId);
            ps.setLong(4, finalTeamId);
            ps.setString(5, finalMode);
            ps.setInt(6, includeThinking ? 1 : 0);
            if (resourceId == null) ps.setObject(7, null);
            else ps.setInt(7, resourceId);
            ps.setLong(8, fileId);
            return ps;
        }, shareKh);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("shareId", shareKh.getKey().longValue());
        result.put("fileId", fileId);
        result.put("resourceId", resourceId);
        result.put("teamId", teamId);
        result.put("shareMode", mode);
        result.put("fileName", finalFileName);
        return result;
    }

    public List<Map<String, Object>> listShares(Long sessionId, Long tenantId, Long userId) {
        getSession(sessionId, tenantId, userId);
        return jdbc.queryForList("""
                SELECT id, team_id AS teamId, share_mode AS shareMode, include_thinking AS includeThinking,
                       resource_id AS resourceId, file_id AS fileId, status, created_at AS createdAt
                FROM ai_assistant_share WHERE session_id = ? ORDER BY id DESC
                """, sessionId);
    }

    // ── Internal score summary ────────────────────────────────

    public Map<String, Object> scoreSummary(Long userId, Long teamId, int limit, String token) {
        assertInternalToken(token);
        int lim = Math.min(Math.max(limit, 1), 10);
        List<Map<String, Object>> sessions = List.of();
        try {
            // 1) 绑定团队时优先团队内本人完成的评分
            if (teamId != null) {
                sessions = jdbc.queryForList("""
                        SELECT s.id AS sessionId, s.meeting_id AS meetingId, s.track_name AS track,
                               s.completed_at AS scoredAt, s.created_at AS createdAt, s.status,
                               s.report_id AS reportId, s.created_by AS createdBy, s.team_id AS teamId
                        FROM ai_scoring_session s
                        WHERE s.created_by = ?
                          AND s.team_id = ?
                          AND LOWER(s.status) IN ('completed', 'success', 'done')
                        ORDER BY COALESCE(s.completed_at, s.created_at) DESC
                        LIMIT ?
                        """, userId, teamId, lim);
            }
            // 2) 团队下无结果 → 回退到本人全部完成评分（含 team_id 为空的历史数据）
            if (sessions.isEmpty()) {
                sessions = jdbc.queryForList("""
                        SELECT s.id AS sessionId, s.meeting_id AS meetingId, s.track_name AS track,
                               s.completed_at AS scoredAt, s.created_at AS createdAt, s.status,
                               s.report_id AS reportId, s.created_by AS createdBy, s.team_id AS teamId
                        FROM ai_scoring_session s
                        WHERE s.created_by = ?
                          AND LOWER(s.status) IN ('completed', 'success', 'done')
                        ORDER BY COALESCE(s.completed_at, s.created_at) DESC
                        LIMIT ?
                        """, userId, lim);
            }
            // 3) 仍无结果且绑定了团队 → 团队内其他人完成的评分（协作场景可读团队分）
            if (sessions.isEmpty() && teamId != null) {
                sessions = jdbc.queryForList("""
                        SELECT s.id AS sessionId, s.meeting_id AS meetingId, s.track_name AS track,
                               s.completed_at AS scoredAt, s.created_at AS createdAt, s.status,
                               s.report_id AS reportId, s.created_by AS createdBy, s.team_id AS teamId
                        FROM ai_scoring_session s
                        WHERE s.team_id = ?
                          AND LOWER(s.status) IN ('completed', 'success', 'done')
                        ORDER BY COALESCE(s.completed_at, s.created_at) DESC
                        LIMIT ?
                        """, teamId, lim);
            }
        } catch (Exception e) {
            log.warn("score summary query failed: {}", e.getMessage());
            return Map.of("items", List.of());
        }

        List<Map<String, Object>> items = new ArrayList<>();
        for (Map<String, Object> s : sessions) {
            items.add(enrichScoreItem(s));
        }
        return Map.of("items", items);
    }

    /** 把评分会话 + 完整报告明细打成可给模型直接输出的结构 */
    private Map<String, Object> enrichScoreItem(Map<String, Object> sessionRow) {
        Map<String, Object> item = new LinkedHashMap<>(sessionRow);
        Long reportId = longVal(sessionRow.get("reportId"));
        Long sessionId = longVal(sessionRow.get("sessionId"));
        item.put("overallScore", null);
        item.put("topDeductions", List.of());
        item.put("topSuggestions", List.of());
        item.put("reportMarkdown", null);
        item.put("hasDetail", false);

        Map<String, Object> report = null;
        try {
            List<Map<String, Object>> reports = List.of();
            if (reportId != null) {
                reports = jdbc.queryForList("""
                        SELECT id, session_id, meeting_id, overall_score, status, completed_at, created_at,
                               dimensions_json, highlights_json, critical_issues_json,
                               improvement_priorities_json, action_plan_json, loss_ledger_json,
                               coverage_summary_json, score_projection_json, structured_result_json,
                               speech_quality_json, score_calibration_json, rule_engine_version, contract_version
                        FROM ai_score_report WHERE id = ? LIMIT 1
                        """, reportId);
            }
            if (reports.isEmpty() && sessionId != null) {
                reports = jdbc.queryForList("""
                        SELECT id, session_id, meeting_id, overall_score, status, completed_at, created_at,
                               dimensions_json, highlights_json, critical_issues_json,
                               improvement_priorities_json, action_plan_json, loss_ledger_json,
                               coverage_summary_json, score_projection_json, structured_result_json,
                               speech_quality_json, score_calibration_json, rule_engine_version, contract_version
                        FROM ai_score_report WHERE session_id = ?
                        ORDER BY id DESC LIMIT 1
                        """, sessionId);
            }
            if (!reports.isEmpty()) {
                report = reports.get(0);
                Object score = report.get("overall_score");
                item.put("overallScore", score);
                if (reportId == null && report.get("id") != null) {
                    item.put("reportId", report.get("id"));
                    reportId = longVal(report.get("id"));
                }
            }
        } catch (Exception e) {
            log.warn("score report enrich failed: {}", e.getMessage());
        }

        List<Map<String, Object>> deductions = List.of();
        if (sessionId != null) {
            try {
                // 真实表字段：deducted_points / reason / required_fix（旧摘要 SQL 列名错误导致一直空）
                deductions = jdbc.queryForList("""
                        SELECT observation_code AS observationCode,
                               dimension_code AS dimensionCode,
                               deducted_points AS points,
                               reason AS title,
                               required_fix AS hint,
                               evidence_level AS evidenceLevel
                        FROM ai_score_deduction
                        WHERE session_id = ?
                        ORDER BY deducted_points DESC
                        LIMIT 12
                        """, sessionId);
                item.put("topDeductions", deductions);
                List<String> suggestions = new ArrayList<>();
                for (Map<String, Object> d : deductions) {
                    if (d.get("hint") != null && !String.valueOf(d.get("hint")).isBlank()) {
                        suggestions.add(String.valueOf(d.get("hint")));
                    }
                }
                item.put("topSuggestions", suggestions.stream().limit(8).toList());
            } catch (Exception e) {
                log.debug("score deduction enrich failed: {}", e.getMessage());
            }
        }

        if (report != null) {
            try {
                String md = buildScoreReportMarkdown(item, report, deductions);
                item.put("reportMarkdown", md);
                item.put("hasDetail", md != null && md.length() > 80);
                // 结构化字段，便于模型按节引用（控制体积）
                item.put("dimensions", parseJsonSafe(report.get("dimensions_json")));
                item.put("highlights", parseJsonSafe(report.get("highlights_json")));
                item.put("criticalIssues", parseJsonSafe(report.get("critical_issues_json")));
                item.put("improvementPriorities", parseJsonSafe(report.get("improvement_priorities_json")));
                item.put("actionPlan", parseJsonSafe(report.get("action_plan_json")));
                item.put("lossLedger", truncateJsonList(parseJsonSafe(report.get("loss_ledger_json")), 12));
            } catch (Exception e) {
                log.warn("build report markdown failed: {}", e.getMessage());
            }
        }
        return item;
    }

    private static final Map<String, String> DIMENSION_LABELS = Map.of(
            "skill_level", "技能水平",
            "professionalism", "职业素养",
            "application_value", "应用价值",
            "teamwork", "团队协作",
            "innovation", "创新能力"
    );

    private String buildScoreReportMarkdown(
            Map<String, Object> sessionItem,
            Map<String, Object> report,
            List<Map<String, Object>> deductions
    ) {
        StringBuilder md = new StringBuilder();
        Object score = sessionItem.get("overallScore");
        if (score == null) score = report.get("overall_score");
        String track = str(sessionItem.get("track"));
        Object scoredAt = sessionItem.get("scoredAt");
        if (scoredAt == null) scoredAt = report.get("completed_at");
        Object reportId = sessionItem.get("reportId");
        if (reportId == null) reportId = report.get("id");
        Object sessionId = sessionItem.get("sessionId");

        md.append("# 路演评分报告\n\n");
        md.append("## 总览\n\n");
        md.append("| 项 | 内容 |\n| --- | --- |\n");
        md.append("| **总分** | **").append(score != null ? score : "—").append("** |\n");
        if (track != null && !track.isBlank()) {
            md.append("| 赛道 | ").append(escapeMdCell(track)).append(" |\n");
        }
        if (scoredAt != null) {
            md.append("| 完成时间 | ").append(escapeMdCell(String.valueOf(scoredAt))).append(" |\n");
        }
        if (reportId != null) {
            md.append("| 报告 ID | ").append(reportId).append(" |\n");
        }
        if (sessionId != null) {
            md.append("| 评分会话 | ").append(sessionId).append(" |\n");
        }
        Object rev = report.get("rule_engine_version");
        if (rev != null) {
            md.append("| 规则版本 | ").append(escapeMdCell(String.valueOf(rev))).append(" |\n");
        }
        md.append("\n");

        // 分维度
        Object dims = parseJsonSafe(report.get("dimensions_json"));
        if (dims instanceof Map<?, ?> dimMap && !dimMap.isEmpty()) {
            md.append("## 分维度得分\n\n");
            md.append("| 维度 | 得分 | 满分 |\n| --- | ---: | ---: |\n");
            for (Map.Entry<?, ?> e : dimMap.entrySet()) {
                String key = String.valueOf(e.getKey());
                String label = DIMENSION_LABELS.getOrDefault(key, key);
                Object val = e.getValue();
                String sc = "—";
                String max = "—";
                if (val instanceof Map<?, ?> vm) {
                    Object s = firstNonNull(vm.get("score"), vm.get("overall"), vm.get("value"));
                    Object m = firstNonNull(vm.get("max_score"), vm.get("maxScore"), vm.get("full"));
                    if (s != null) sc = String.valueOf(s);
                    if (m != null) max = String.valueOf(m);
                    Object name = vm.get("name");
                    if (name != null && !String.valueOf(name).isBlank()) {
                        label = String.valueOf(name);
                    }
                } else if (val != null) {
                    sc = String.valueOf(val);
                }
                md.append("| ").append(escapeMdCell(label)).append(" | ").append(sc)
                        .append(" | ").append(max).append(" |\n");
            }
            md.append("\n");
        }

        appendMdStringList(md, "亮点", parseJsonSafe(report.get("highlights_json")), 8);
        appendMdStringList(md, "关键问题", parseJsonSafe(report.get("critical_issues_json")), 10);

        // 失分账本
        Object ledger = parseJsonSafe(report.get("loss_ledger_json"));
        if (ledger instanceof List<?> list && !list.isEmpty()) {
            md.append("## 失分明细\n\n");
            int i = 0;
            for (Object raw : list) {
                if (i >= 12) break;
                if (!(raw instanceof Map<?, ?> m)) continue;
                i++;
                String name = str(firstNonNull(m.get("observationName"), m.get("title"), m.get("observationCode")));
                Object points = firstNonNull(m.get("points"), m.get("deductedPoints"), m.get("loss"));
                String reason = str(firstNonNull(m.get("reason"), m.get("detail"), m.get("description")));
                String dim = str(firstNonNull(m.get("dimensionCode"), m.get("dimension")));
                if (dim != null && DIMENSION_LABELS.containsKey(dim)) {
                    dim = DIMENSION_LABELS.get(dim);
                }
                md.append(i).append(". **");
                if (points != null) md.append("-").append(points).append(" 分** · ");
                else md.append("失分** · ");
                if (name != null) md.append(name);
                if (dim != null && !dim.isBlank()) md.append("（").append(dim).append("）");
                md.append("\n");
                if (reason != null && !reason.isBlank()) {
                    md.append("   - ").append(reason.trim().replace("\n", " ")).append("\n");
                }
            }
            md.append("\n");
        } else if (deductions != null && !deductions.isEmpty()) {
            md.append("## 失分明细\n\n");
            int i = 0;
            for (Map<String, Object> d : deductions) {
                if (i >= 12) break;
                i++;
                md.append(i).append(". **");
                if (d.get("points") != null) md.append("-").append(d.get("points")).append(" 分** · ");
                else md.append("失分** · ");
                md.append(str(d.get("title")) != null ? str(d.get("title")) : "扣分项");
                md.append("\n");
                if (d.get("hint") != null && !String.valueOf(d.get("hint")).isBlank()) {
                    md.append("   - 改进：").append(String.valueOf(d.get("hint")).trim().replace("\n", " ")).append("\n");
                }
            }
            md.append("\n");
        }

        // 改进优先级
        Object improvs = parseJsonSafe(report.get("improvement_priorities_json"));
        if (improvs instanceof List<?> list && !list.isEmpty()) {
            md.append("## 改进优先级\n\n");
            int i = 0;
            for (Object raw : list) {
                if (i >= 8) break;
                i++;
                if (raw instanceof Map<?, ?> m) {
                    Object p = firstNonNull(m.get("priority"), i);
                    String dim = str(m.get("dimension"));
                    String issue = str(firstNonNull(m.get("issue"), m.get("problem"), m.get("title")));
                    String suggestion = str(firstNonNull(m.get("suggestion"), m.get("action"), m.get("method")));
                    md.append(i).append(". **P").append(p).append("**");
                    if (dim != null) md.append(" · ").append(dim);
                    md.append("\n");
                    if (issue != null) md.append("   - 问题：").append(issue).append("\n");
                    if (suggestion != null) md.append("   - 建议：").append(suggestion).append("\n");
                } else if (raw != null) {
                    md.append(i).append(". ").append(raw).append("\n");
                }
            }
            md.append("\n");
        }

        // 行动计划
        Object plan = parseJsonSafe(report.get("action_plan_json"));
        if (plan instanceof List<?> list && !list.isEmpty()) {
            md.append("## 行动计划\n\n");
            int i = 0;
            for (Object raw : list) {
                if (i >= 8) break;
                i++;
                if (raw instanceof Map<?, ?> m) {
                    String title = str(firstNonNull(m.get("title"), m.get("name"), "行动项 " + i));
                    String priority = str(firstNonNull(m.get("priority"), m.get("level")));
                    String problem = str(firstNonNull(m.get("problem"), m.get("issue")));
                    String method = str(firstNonNull(m.get("method"), m.get("action"), m.get("suggestion")));
                    md.append("### ").append(i).append(". ").append(title != null ? title : ("行动 " + i));
                    if (priority != null) md.append("（").append(priority).append("）");
                    md.append("\n\n");
                    if (problem != null) md.append("- **问题**：").append(problem).append("\n");
                    if (method != null) md.append("- **做法**：").append(method).append("\n");
                    md.append("\n");
                }
            }
        }

        md.append("---\n\n");
        md.append("*本报告由竞赛大脑评分系统生成，分数与扣分项以系统落库结果为准。*\n");
        return md.toString();
    }

    private void appendMdStringList(StringBuilder md, String title, Object raw, int limit) {
        if (!(raw instanceof List<?> list) || list.isEmpty()) return;
        md.append("## ").append(title).append("\n\n");
        int i = 0;
        for (Object item : list) {
            if (i >= limit) break;
            String text;
            if (item instanceof Map<?, ?> m) {
                text = str(firstNonNull(m.get("text"), m.get("content"), m.get("title"), m.get("issue"), m.toString()));
            } else {
                text = item == null ? null : String.valueOf(item);
            }
            if (text == null || text.isBlank()) continue;
            i++;
            md.append(i).append(". ").append(text.trim().replace("\n", " ")).append("\n");
        }
        md.append("\n");
    }

    private Object parseJsonSafe(Object raw) {
        if (raw == null) return null;
        if (raw instanceof Map || raw instanceof List) return raw;
        String s = String.valueOf(raw).trim();
        if (s.isEmpty() || "null".equalsIgnoreCase(s)) return null;
        try {
            return objectMapper.readValue(s, Object.class);
        } catch (Exception e) {
            return null;
        }
    }

    private Object truncateJsonList(Object raw, int max) {
        if (!(raw instanceof List<?> list)) return raw;
        if (list.size() <= max) return list;
        return list.subList(0, max);
    }

    private static Object firstNonNull(Object... vals) {
        if (vals == null) return null;
        for (Object v : vals) {
            if (v != null && !(v instanceof String s && s.isBlank())) return v;
        }
        return null;
    }

    private static String escapeMdCell(String s) {
        if (s == null) return "";
        return s.replace("|", "\\|").replace("\n", " ");
    }

    /**
     * AI 服务容器访问后端的 base URL。
     * 生产 compose 网络里必须用服务名 backend，不能用 127.0.0.1。
     */
    private String resolveBackendInternalUrl() {
        String fromEnv = System.getenv("BACKEND_INTERNAL_URL");
        if (fromEnv != null && !fromEnv.isBlank()) {
            return fromEnv.trim().replaceAll("/+$", "");
        }
        // 与 docker-compose.release.yml 中 AI 回调地址保持一致
        return "http://backend:8080";
    }

    public void assertInternalToken(String token) {
        if (token == null || !internalToken.equals(token)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "invalid internal token");
        }
    }

    // ── helpers ───────────────────────────────────────────────

    private long insertMessage(
            long sessionId, long tenantId, long userId, String role, String content,
            String thinking, String status, Long runId, String clientMessageId
    ) {
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_message
                      (session_id, tenant_id, user_id, role, content_text, thinking_text, status, run_id, client_message_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, sessionId);
            ps.setLong(2, tenantId);
            ps.setLong(3, userId);
            ps.setString(4, role);
            ps.setString(5, content);
            ps.setString(6, thinking);
            ps.setString(7, status);
            if (runId == null) ps.setObject(8, null);
            else ps.setLong(8, runId);
            ps.setString(9, clientMessageId);
            return ps;
        }, kh);
        return kh.getKey().longValue();
    }

    private long insertRun(long sessionId, long tenantId, long userId, long userMsgId, long assistantMsgId, String traceId, Map<String, Object> body) {
        KeyHolder kh = new GeneratedKeyHolder();
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_run
                      (session_id, tenant_id, user_id, user_message_id, assistant_message_id, status, request_json, trace_id, created_at)
                    VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, sessionId);
            ps.setLong(2, tenantId);
            ps.setLong(3, userId);
            ps.setLong(4, userMsgId);
            ps.setLong(5, assistantMsgId);
            ps.setString(6, toJson(body));
            ps.setString(7, traceId);
            return ps;
        }, kh);
        return kh.getKey().longValue();
    }

    private List<Map<String, Object>> loadHistoryForModel(long sessionId, int limit) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT role, content_text AS content
                FROM ai_assistant_message
                WHERE session_id = ? AND role IN ('user','assistant') AND status IN ('completed','streaming','pending','cancelled','failed')
                ORDER BY id DESC
                LIMIT ?
                """, sessionId, Math.max(limit * 2, limit));
        List<Map<String, Object>> out = new ArrayList<>();
        for (int i = rows.size() - 1; i >= 0; i--) {
            Map<String, Object> r = rows.get(i);
            String content = str(r.get("content"));
            if (content == null) content = "";
            // 跳过尚未生成的空助手消息，避免污染上下文
            if ("assistant".equals(String.valueOf(r.get("role"))) && content.isBlank()) {
                continue;
            }
            out.add(Map.of("role", r.get("role"), "content", content));
        }
        if (out.size() > limit) {
            return out.subList(out.size() - limit, out.size());
        }
        return out;
    }

    private List<String> loadMemoriesForInject(long tenantId, long userId) {
        return jdbc.queryForList("""
                SELECT content FROM ai_assistant_memory
                WHERE tenant_id = ? AND user_id = ? AND status = 'active'
                ORDER BY importance DESC, updated_at DESC
                LIMIT ?
                """, String.class, tenantId, userId, MEMORY_INJECT_TOP_K);
    }

    private String buildShareMarkdown(Map<String, Object> session, List<Map<String, Object>> messages, String mode, boolean includeThinking) {
        StringBuilder sb = new StringBuilder();
        sb.append("# 竞赛助手对话分享\n\n");
        sb.append("- 会话：").append(session.get("title")).append("\n");
        sb.append("- 导出模式：").append(mode).append("\n");
        sb.append("- 导出时间：").append(LocalDateTime.now()).append("\n\n");
        sb.append("---\n\n");
        if ("artifacts_only".equals(mode)) {
            sb.append("## 本会话文件产物\n\n");
            sb.append("（请在资源中心或助手文件区查看生成物。）\n");
            return sb.toString();
        }
        if ("summary".equals(mode)) {
            sb.append("## 对话摘要\n\n");
            int turns = 0;
            for (Map<String, Object> m : messages) {
                if (!"user".equals(String.valueOf(m.get("role")))) continue;
                turns++;
                String c = str(m.get("contentText"));
                if (c != null && !c.isBlank()) {
                    sb.append(turns).append(". 用户问：").append(truncate(c, 200)).append("\n");
                }
            }
            sb.append("\n## 完整对话（精简）\n\n");
        } else {
            sb.append("## 完整对话\n\n");
        }
        for (Map<String, Object> m : messages) {
            String role = "user".equals(String.valueOf(m.get("role"))) ? "用户" : "助手";
            sb.append("### ").append(role).append("\n\n");
            if (includeThinking && m.get("thinkingText") != null && !String.valueOf(m.get("thinkingText")).isBlank()) {
                sb.append("<details><summary>思考过程</summary>\n\n").append(m.get("thinkingText")).append("\n\n</details>\n\n");
            }
            String content = str(m.get("contentText"));
            sb.append(content == null ? "" : content).append("\n\n");
        }
        sb.append("\n> 本文件由用户主动分享。不包含个人记忆条目。\n");
        return sb.toString();
    }

    private Integer insertTeamResource(Long teamId, Long userId, String name, String ext, String storageKey, long size, String folderKey) {
        try {
            String category = folderKey == null || folderKey.isBlank() ? "content" : folderKey;
            KeyHolder kh = new GeneratedKeyHolder();
            jdbc.update(con -> {
                PreparedStatement ps = con.prepareStatement("""
                        INSERT INTO resource (name, file_size, ext, file_path, uploaded_by, team_id, category, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
                        """, Statement.RETURN_GENERATED_KEYS);
                ps.setString(1, name);
                ps.setLong(2, size);
                ps.setString(3, ext);
                ps.setString(4, storageKey);
                ps.setInt(5, userId.intValue());
                ps.setLong(6, teamId);
                ps.setString(7, category);
                return ps;
            }, kh);
            return kh.getKey().intValue();
        } catch (Exception e) {
            log.warn("insert team resource failed: {}", e.getMessage());
            return null;
        }
    }

    private void assertTeamAccess(Long teamId, Long tenantId, Long userId, String role) {
        if (role != null && ADMIN_ROLES.contains(role.toUpperCase())) {
            return;
        }
        try {
            projectTeamService.dashboard(teamId, tenantId, userId, role);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该团队");
        }
    }

    /**
     * 开跑信号：只发「思考中」抬头，不演多 Agent 分工。
     * 假中间结论（统筹拆解 / 组织协作）一律不发——那是生硬感的来源。
     */
    private void publishAgentKickoff(long runId, String modeRaw) {
        String mode = modeRaw == null || modeRaw.isBlank() ? "fast" : modeRaw.trim().toLowerCase(Locale.ROOT);
        publish(runId, "agent_kickoff", mapOf(
                "label", "思考中",
                "mode", mode,
                // 单主体，不塞 G/S/P 假阵容
                "agents", List.of(
                        Map.of("key", "xiaoqi", "letter", "启", "name", "小启")
                )
        ));
    }

    /** 过程阶段结束：前端折叠摘要用 */
    private void publishProcessDone(long runId, long processStartedAt, LiveRun live) {
        int siteCount = 0;
        int webCount = 0;
        // 从已发布 citation 累计（enrichWithModeResearch 已写入 live.citationAcc）
        if (live != null && live.citationAcc != null) {
            for (Map<String, Object> c : live.citationAcc) {
                String st = str(c.get("sourceType"));
                if (st != null && st.toLowerCase(Locale.ROOT).contains("web")) webCount++;
                else siteCount++;
            }
        }
        long durationMs = Math.max(0, System.currentTimeMillis() - processStartedAt);
        int stepCount = 0;
        try {
            Integer n = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM ai_assistant_run_step WHERE run_id = ?",
                    Integer.class, runId
            );
            stepCount = n == null ? 0 : n;
        } catch (Exception ignored) {
            stepCount = 0;
        }
        publish(runId, "process_done", mapOf(
                "durationMs", durationMs,
                "stepCount", stepCount,
                "sourceCount", siteCount + webCount,
                "siteCount", siteCount,
                "webCount", webCount
        ));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> extractMap(Object raw) {
        if (raw instanceof Map<?, ?> m) {
            Map<String, Object> out = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : m.entrySet()) {
                if (e.getKey() != null) out.put(String.valueOf(e.getKey()), e.getValue());
            }
            return out;
        }
        return null;
    }

    /**
     * 首页 clientContext → ephemeral brief 字符串（注入 AI system，不写进 user 消息）。
     */
    private String buildHomeContextBrief(Map<String, Object> clientContext) {
        if (clientContext == null || clientContext.isEmpty()) return "";
        StringBuilder sb = new StringBuilder();
        Map<String, Object> camp = extractMap(clientContext.get("camp"));
        if (camp != null && !camp.isEmpty()) {
            String name = str(camp.get("campName"));
            if (name == null || name.isBlank()) name = str(camp.get("name"));
            if (name == null || name.isBlank()) name = "训练营";
            sb.append("备赛营：").append(name);
            Object day = camp.get("currentDay");
            Object total = camp.get("totalDays");
            if (day != null || total != null) {
                sb.append("，第 ").append(day != null ? day : "—")
                        .append(" / ").append(total != null ? total : "—").append(" 天");
            }
            Object remain = camp.get("remainingDays");
            if (remain != null) sb.append("，剩余 ").append(remain).append(" 天");
            sb.append("。");
        }
        Map<String, Object> today = extractMap(clientContext.get("todayTraining"));
        if (today != null) {
            Object has = today.get("hasTrainingDay");
            boolean hasDay = has instanceof Boolean ? (Boolean) has : !"false".equals(String.valueOf(has));
            if (Boolean.TRUE.equals(has) || (has == null && today.get("title") != null) || hasDay && today.get("title") != null) {
                String t = str(today.get("title"));
                Map<String, Object> primary = extractMap(today.get("primaryTask"));
                String pt = primary != null ? str(primary.get("title")) : null;
                sb.append("今日训练：").append(t != null && !t.isBlank() ? t : (pt != null ? pt : "已安排")).append("。");
                if (pt != null && !pt.isBlank() && (t == null || !pt.equals(t))) {
                    sb.append("今日唯一任务：").append(pt).append("。");
                }
            } else if (Boolean.FALSE.equals(has) || "false".equals(String.valueOf(has))) {
                sb.append("今日暂无训练日安排。");
            }
        }
        Map<String, Object> score = extractMap(clientContext.get("latestScore"));
        if (score != null) {
            Object hasReport = score.get("hasReport");
            if (Boolean.TRUE.equals(hasReport) || score.get("overallScore") != null) {
                Object overall = score.get("overallScore");
                if (overall instanceof Number) {
                    sb.append("最近 AI 评分综合 ")
                            .append(String.format(Locale.ROOT, "%.1f", ((Number) overall).doubleValue()))
                            .append("/100。");
                } else {
                    sb.append("最近有 AI 评分报告。");
                }
            } else {
                sb.append("尚无最近完成的 AI 评分报告。");
            }
        }
        Object actionsRaw = clientContext.get("nextActions");
        if (actionsRaw instanceof List<?> list && !list.isEmpty()) {
            List<String> titles = new ArrayList<>();
            for (Object a : list) {
                if (titles.size() >= 3) break;
                Map<String, Object> am = extractMap(a);
                if (am == null) continue;
                String t = str(am.get("title"));
                if (t != null && !t.isBlank()) titles.add(t);
            }
            if (!titles.isEmpty()) {
                sb.append("待办提示：").append(String.join("；", titles)).append("。");
            }
        }
        String brief = str(clientContext.get("brief"));
        if (brief != null && !brief.isBlank()) sb.append(brief);
        return sb.toString().trim();
    }

    private static Map<String, Object> mapOf(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i + 1 < kv.length; i += 2) {
            m.put(String.valueOf(kv[i]), kv[i + 1]);
        }
        return m;
    }

    /**
     * 真实检索步骤（工作日志风格，不演多 Agent）。
     * - fast：静默站内检索，仅命中时露出工具行 + 真实标题
     * - think / deep_search：始终露出站内检索；deep 另加联网
     * - 绝不发「统筹 / 深度推理准备 / 综合汇总」类假步骤
     */
    private void enrichWithModeResearch(
            LiveRun live,
            long tenantId,
            long userId,
            Long teamId,
            String role,
            Map<String, Object> aiRequest
    ) {
        long runId = live.runId;
        String mode = str(aiRequest.get("mode"));
        if (mode == null || mode.isBlank()) mode = "fast";
        boolean deep = "deep_search".equals(mode);
        boolean think = "think".equals(mode);

        String query = latestUserQuery(aiRequest);
        if (query == null || query.isBlank()) query = "备赛进度与评分";
        // 用户明确「搜索/查名单/官网公示」等：即使未点「联网」也自动走公网检索
        boolean forceWeb = looksLikeWebSearchIntent(query);
        if (forceWeb && !deep) {
            deep = true;
            mode = "deep_search";
            aiRequest.put("mode", "deep_search");
            aiRequest.put("researchMode", "deep_search");
            log.info("auto-enable deep_search for web intent q={}", truncate(query, 40));
        }
        boolean showEmptySearch = deep || think; // 深度模式连 0 结果也诚实展示
        String siteQuery = query.length() > 80 ? query.substring(0, 80) + "…" : query;

        List<Map<String, Object>> siteHits = siteKnowledgeSearch(tenantId, userId, teamId, query);
        for (Map<String, Object> hit : siteHits) {
            int index = live.citationAcc.size() + 1;
            hit.put("index", index);
            live.citationAcc.add(hit);
            publish(runId, "citation", hit);
        }

        // 有命中，或深度模式需要可见检索：才发工具行
        if (!siteHits.isEmpty() || showEmptySearch) {
            publish(runId, "step_start", mapOf(
                    "stepNo", 12,
                    "stepKey", "site_search",
                    "kind", "tool",
                    "action", "检索站内资料",
                    "query", siteQuery,
                    "title", "检索站内资料"
            ));
            publish(runId, "step_end", mapOf(
                    "stepNo", 12,
                    "stepKey", "site_search",
                    "kind", "tool",
                    "action", "检索站内资料",
                    "query", siteQuery,
                    "title", "检索站内资料",
                    "status", "completed",
                    "resultCount", siteHits.size(),
                    "outputSummary", siteHits.isEmpty() ? "0 条" : (siteHits.size() + " 条")
            ));
            // 只在有真实标题时写一句日志，不写「将更多依赖通用推理」
            if (!siteHits.isEmpty()) {
                StringBuilder note = new StringBuilder("站内找到：");
                int n = 0;
                for (Map<String, Object> h : siteHits) {
                    if (n >= 3) break;
                    String t = str(h.get("title"));
                    if (t == null || t.isBlank()) continue;
                    if (n > 0) note.append("；");
                    note.append(t);
                    n++;
                }
                if (n > 0) {
                    publish(runId, "agent_note", mapOf(
                            "agent", "小启",
                            "agentKey", "xiaoqi",
                            "text", note.toString()
                    ));
                }
            }
        }

        if (deep) {
            // Grok 式：联网研究全部由 AI Research Agent（think → tool → …）完成。
            // Java 不再跑关键词流水线，避免「告诉/河南」等口语触发词典/门户噪声。
            List<String> directUrls = extractHttpUrls(query);
            publish(runId, "step_start", mapOf(
                    "stepNo", 13,
                    "stepKey", "research_agent",
                    "kind", "tool",
                    "action", "联网研究 Agent",
                    "query", directUrls.isEmpty() ? siteQuery : directUrls.get(0),
                    "title", "联网研究 Agent"
            ));
            publish(runId, "step_end", mapOf(
                    "stepNo", 13,
                    "stepKey", "research_agent",
                    "kind", "tool",
                    "action", "联网研究 Agent",
                    "query", directUrls.isEmpty() ? siteQuery : directUrls.get(0),
                    "title", "联网研究 Agent",
                    "status", "completed",
                    "resultCount", 0,
                    "outputSummary", "交由模型多跳工具循环（search/open）"
            ));
            publish(runId, "agent_note", mapOf(
                    "agent", "小启",
                    "agentKey", "xiaoqi",
                    "text", directUrls.isEmpty()
                            ? "将用「思考→搜索/打开网页→再思考」方式联网，不再用固定关键词流水线预搜"
                            : ("检测到链接，将由 Agent 直接打开：" + directUrls.get(0))
            ));
            if (!directUrls.isEmpty()) {
                aiRequest.put("userUrls", new ArrayList<>(directUrls));
            }
        }

        aiRequest.put("researchCitations", new ArrayList<>(live.citationAcc));
        aiRequest.put("researchMode", mode);
        // deep_search：Agent 主路径（Grok 同构）
        if (deep) {
            aiRequest.put("useResearchAgent", true);
            aiRequest.put("researchAgentPrimary", true);
        }
        // 写入可读检索块，供 AI system 引用（此前只放了 citation 对象，模型侧未消费）
        if (!live.citationAcc.isEmpty()) {
            StringBuilder rb = new StringBuilder();
            rb.append("## 检索结果（联网/站内，请优先引用，勿编造链接）\n");
            int i = 0;
            for (Map<String, Object> c : live.citationAcc) {
                if (i >= 8) break;
                i++;
                rb.append(i).append(". [")
                        .append(str(c.get("sourceType")) != null ? c.get("sourceType") : "web")
                        .append("] ")
                        .append(str(c.get("title")) != null ? c.get("title") : "来源");
                if (c.get("url") != null && !String.valueOf(c.get("url")).isBlank()) {
                    rb.append("\n   链接：").append(c.get("url"));
                }
                String body = str(c.get("pageText"));
                if (body == null || body.isBlank()) body = str(c.get("snippet"));
                if (body != null && !body.isBlank()) {
                    rb.append("\n   摘录：").append(truncate(body, 900));
                }
                Object atts = c.get("attachments");
                if (atts instanceof List<?> attList && !attList.isEmpty()) {
                    rb.append("\n   可下载附件（完整 URL，须用 Markdown 链接写出，禁止只说「见附件」）：\n");
                    int ai = 0;
                    for (Object ao : attList) {
                        if (ai >= 10) break;
                        if (!(ao instanceof Map<?, ?> am)) continue;
                        String aTitle = str(am.get("title"));
                        String aUrl = str(am.get("url"));
                        if (aUrl == null || aUrl.isBlank()) continue;
                        ai++;
                        rb.append("   - [")
                                .append(aTitle != null && !aTitle.isBlank() ? aTitle : "附件")
                                .append("](")
                                .append(aUrl)
                                .append(")\n");
                    }
                }
                rb.append('\n');
            }
            rb.append("\n写作要求：优先依据摘录内容回答用户问题；摘录不足时如实说明局限，禁止编造链接与名单。"
                    + "系统已执行联网检索，禁止声称「无法搜索/没有联网能力/不能实时检索」。"
                    + "若摘录含「可下载附件」或 citation 标题以「附件 ·」开头：必须在回答中用 Markdown 可点击链接列出完整 URL；"
                    + "明确说明「附件在官网，本聊天不会上传文件」——禁止写「附件内容」却不给链接，仿佛聊天里已挂载附件。\n");
            aiRequest.put("researchBlock", rb.toString());
        } else if (deep) {
            // 占位：真正 researchBlock 由 AI Research Agent 多跳完成后写入
            aiRequest.put("researchBlock", "");
        }
    }

    /** 把 Connection refused 等底层异常转成用户可读文案 */
    private static String friendlyStreamError(String raw) {
        if (raw == null || raw.isBlank()) return "生成失败，请稍后重试。";
        String s = raw.toLowerCase(Locale.ROOT);
        if (s.contains("connection refused") || s.contains("connect timed out")
                || s.contains("failed to connect") || s.contains("connection reset")) {
            return "AI 服务暂时连不上（请确认 8090 评分/助手服务已启动），请稍后重试。";
        }
        if (s.contains("401") || s.contains("api key") || s.contains("unauthorized")) {
            return "AI 模型鉴权失败，请检查密钥配置后重试。";
        }
        if (s.contains("429") || s.contains("rate limit")) {
            return "AI 请求过于频繁，请稍后再试。";
        }
        return raw.length() > 200 ? raw.substring(0, 200) + "…" : raw;
    }

    private static String modeLabel(String mode) {
        return switch (mode) {
            case "think" -> "深度思考";
            case "deep_search" -> "联网（站内+公开网页）";
            default -> "快速回答";
        };
    }

    private String latestUserQuery(Map<String, Object> aiRequest) {
        Object messages = aiRequest.get("messages");
        if (!(messages instanceof List<?> list) || list.isEmpty()) return null;
        for (int i = list.size() - 1; i >= 0; i--) {
            Object m = list.get(i);
            if (m instanceof Map<?, ?> map) {
                Object role = map.get("role");
                if (role != null && "user".equalsIgnoreCase(String.valueOf(role))) {
                    Object c = map.get("content");
                    if (c == null) c = map.get("contentText");
                    if (c != null) {
                        String s = String.valueOf(c).trim();
                        // 去掉首页上下文前缀
                        int idx = s.indexOf("【用户问题】");
                        if (idx >= 0) s = s.substring(idx + "【用户问题】".length()).trim();
                        return s.length() > 200 ? s.substring(0, 200) : s;
                    }
                }
            }
        }
        return null;
    }

    private List<Map<String, Object>> siteKnowledgeSearch(long tenantId, long userId, Long teamId, String query) {
        List<Map<String, Object>> hits = new ArrayList<>();
        String q = query == null ? "" : query.trim();
        if (q.isBlank()) return hits;
        // 站内检索用关键词片段，避免整句 LIKE 全空
        String keyword = q
                .replaceAll("[?？!！。，,、；;：:\\s]+", " ")
                .trim();
        if (keyword.length() > 24) {
            // 取前几段有意义词
            String[] parts = keyword.split("\\s+");
            StringBuilder kb = new StringBuilder();
            for (String p : parts) {
                if (p.length() < 2) continue;
                if (kb.length() > 0) kb.append('%');
                kb.append(p);
                if (kb.length() >= 18) break;
            }
            keyword = kb.length() >= 2 ? kb.toString() : keyword.substring(0, 18);
        }
        String like = "%" + keyword.replace("%", "").replace("_", "") + "%";
        String idDigits = q.replaceAll("\\D", "");
        if (idDigits.isBlank()) idDigits = "-1";

        try {
            // 评分报告（真实表无 tenant/summary；经会话 created_by 隔离）
            List<Map<String, Object>> reports = jdbc.queryForList("""
                    SELECT r.id AS reportId, r.session_id AS sessionId, r.overall_score AS overallScore,
                           LEFT(COALESCE(CAST(r.critical_issues_json AS CHAR),
                                         CAST(r.improvement_priorities_json AS CHAR),
                                         s.track_name, ''), 160) AS snippet,
                           COALESCE(r.completed_at, r.created_at) AS created_at,
                           s.track_name AS trackName
                    FROM ai_score_report r
                    LEFT JOIN ai_scoring_session s ON s.id = r.session_id
                    WHERE r.status IN ('completed', 'done', 'success')
                      AND (s.created_by = ? OR s.created_by IS NULL)
                      AND (
                        CAST(r.id AS CHAR) = ?
                        OR CAST(r.session_id AS CHAR) = ?
                        OR CAST(r.critical_issues_json AS CHAR) LIKE ?
                        OR CAST(r.improvement_priorities_json AS CHAR) LIKE ?
                        OR s.track_name LIKE ?
                      )
                    ORDER BY COALESCE(r.completed_at, r.created_at) DESC
                    LIMIT 4
                    """, userId, idDigits, idDigits, like, like, like);
            for (Map<String, Object> r : reports) {
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "score");
                c.put("reportId", r.get("reportId"));
                c.put("sessionId", r.get("sessionId"));
                Object sc = r.get("overallScore");
                String track = str(r.get("trackName"));
                c.put("title", "AI 评分 #" + r.get("reportId")
                        + (sc != null ? " · " + sc + "分" : "")
                        + (track != null && !track.isBlank() ? " · " + track : ""));
                c.put("snippet", r.get("snippet"));
                hits.add(c);
            }
        } catch (Exception e) {
            log.warn("site score search failed: {}", e.getMessage());
        }

        try {
            // 资源中心：无 tenant_id；按 team / 上传者过滤
            List<Map<String, Object>> resources;
            if (teamId != null) {
                resources = jdbc.queryForList("""
                        SELECT id AS resourceId, name AS title,
                               LEFT(COALESCE(extract_text, name), 160) AS snippet
                        FROM resource
                        WHERE team_id = ?
                          AND (name LIKE ? OR COALESCE(extract_text, '') LIKE ?)
                        ORDER BY updated_at DESC
                        LIMIT 4
                        """, teamId, like, like);
            } else {
                resources = jdbc.queryForList("""
                        SELECT id AS resourceId, name AS title,
                               LEFT(COALESCE(extract_text, name), 160) AS snippet
                        FROM resource
                        WHERE uploaded_by = ?
                          AND (name LIKE ? OR COALESCE(extract_text, '') LIKE ?)
                        ORDER BY updated_at DESC
                        LIMIT 4
                        """, userId, like, like);
            }
            for (Map<String, Object> r : resources) {
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "resource");
                c.put("resourceId", r.get("resourceId"));
                c.put("title", r.get("title"));
                c.put("snippet", r.get("snippet"));
                hits.add(c);
            }
        } catch (Exception e) {
            log.warn("site resource search failed: {}", e.getMessage());
        }

        try {
            // 项目任务（站内备赛任务）
            List<Map<String, Object>> tasks = jdbc.queryForList("""
                    SELECT id AS taskId, title,
                           LEFT(COALESCE(description, title), 160) AS snippet
                    FROM project_task
                    WHERE (title LIKE ? OR COALESCE(description, '') LIKE ?)
                      AND (created_by = ? OR owner_user_id = ?)
                    ORDER BY id DESC
                    LIMIT 3
                    """, like, like, userId, userId);
            for (Map<String, Object> t : tasks) {
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "task");
                c.put("title", "任务 · " + t.get("title"));
                c.put("snippet", t.get("snippet"));
                hits.add(c);
            }
        } catch (Exception e) {
            log.warn("site task search failed: {}", e.getMessage());
        }
        return hits;
    }

    /**
     * 公网检索流水线（通用，不写死题型）：
     * ① LLM 改写检索词 → ② 检索 + 词重叠打分 → ③ 弱相关则 LLM 补搜 → ④ LLM 重排 → ⑤ 再给模型。
     */
    private List<Map<String, Object>> webPublicSearch(String query) {
        return webPublicSearchPipeline(query, null);
    }

    /**
     * @param runId 可为 null；非空时会推 SSE 说明第几轮检索
     */
    private List<Map<String, Object>> webPublicSearchPipeline(String originalUserQuery, Long runId) {
        // 从用户原句提取「必须尽量命中」的核心实体（年份单独处理，不能只靠年份过线）
        QueryAnchors anchors = extractQueryAnchors(originalUserQuery);
        List<String> round1 = rewriteWebSearchQueries(originalUserQuery);
        // 把最长中文实体短语强制并入检索词（动态提取，非写死业务模板）
        round1 = ensureAnchorPhrasesInQueries(round1, anchors);

        Map<String, Map<String, Object>> merged = new LinkedHashMap<>();
        List<String> usedQueries = new ArrayList<>();

        mergeSearchRound(merged, round1, originalUserQuery, anchors, usedQueries);
        List<Map<String, Object>> ranked = rankHitsByScore(merged, 12);
        ranked = filterByAnchors(ranked, anchors, /*strict*/ false);

        double avgTop = avgTopScore(ranked, 3);
        boolean needRound2 = ranked.size() < 3 || avgTop < 8.0 || !hasStrongAnchorHit(ranked, anchors);
        if (needRound2) {
            List<String> titles = new ArrayList<>();
            for (Map<String, Object> h : ranked) {
                String t = str(h.get("title"));
                if (t != null && !t.isBlank()) titles.add(t);
                if (titles.size() >= 6) break;
            }
            // 告诉补搜：首轮偏了（例如只撞上年份）
            List<String> badTitles = new ArrayList<>();
            for (Map<String, Object> h : rankHitsByScore(merged, 6)) {
                if (!passesAnchorGate(h, anchors, false)) {
                    String t = str(h.get("title"));
                    if (t != null) badTitles.add(t);
                }
            }
            List<String> round2 = refineWebSearchQueriesViaLlm(originalUserQuery, usedQueries, titles, badTitles, anchors);
            round2 = ensureAnchorPhrasesInQueries(round2, anchors);
            if (!round2.isEmpty()) {
                if (runId != null) {
                    publish(runId, "agent_note", mapOf(
                            "agent", "小启",
                            "agentKey", "xiaoqi",
                            "text", "首轮相关度不足，正在补搜：" + String.join("；", round2.subList(0, Math.min(2, round2.size())))
                    ));
                }
                mergeSearchRound(merged, round2, originalUserQuery, anchors, usedQueries);
                ranked = rankHitsByScore(merged, 12);
                ranked = filterByAnchors(ranked, anchors, false);
            }
        }

        // 硬门槛：没有核心实体命中的结果一律丢掉（避免「只有2025」的经济公报混进来）
        ranked = filterByAnchors(ranked, anchors, /*strict*/ true);
        // LLM 重排
        ranked = rerankHitsViaLlm(originalUserQuery, ranked, 6);
        // 重排后再过一遍硬门槛
        ranked = filterByAnchors(ranked, anchors, true);
        for (Map<String, Object> h : ranked) {
            h.remove("_score");
        }
        int attish = 0;
        boolean govEdu = false;
        for (Map<String, Object> h : ranked) {
            String u = str(h.get("url"));
            if (u != null) {
                String ul = u.toLowerCase(Locale.ROOT);
                if (ul.contains(".pdf") || ul.contains(".xls")) attish++;
                if (ul.contains(".gov.cn") || ul.contains(".edu.cn")) govEdu = true;
            }
        }
        log.info(
                "research_metrics {\"evidenceCount\":{},\"empty\":{},\"attachmentCount\":{},\"hasGovOrEdu\":{},\"requiredCount\":{},\"queryLen\":{}}",
                ranked.size(),
                ranked.isEmpty(),
                attish,
                govEdu,
                anchors.required != null ? anchors.required.size() : 0,
                originalUserQuery != null ? originalUserQuery.length() : 0
        );
        log.info("web pipeline queries={} hits={} required={} soft={} used={}",
                usedQueries.size(), ranked.size(), anchors.required, anchors.contentPhrases, usedQueries);
        return ranked;
    }

    private void mergeSearchRound(
            Map<String, Map<String, Object>> merged,
            List<String> searchQueries,
            String originalUserQuery,
            QueryAnchors anchors,
            List<String> usedQueriesOut
    ) {
        if (searchQueries == null) return;
        for (String sq : searchQueries) {
            if (sq == null || sq.isBlank()) continue;
            if (usedQueriesOut != null && !usedQueriesOut.contains(sq)) {
                usedQueriesOut.add(sq);
            }
            // 原式 + 对最长实体加引号（提高整词命中，通用）
            List<String> variants = new ArrayList<>();
            variants.add(sq);
            String quoted = quoteLongestPhrase(sq, anchors);
            if (quoted != null && !quoted.equals(sq)) variants.add(quoted);

            for (String variant : variants) {
                // 国内生产：360 召回中文时效信息最稳；Bing 易被「年份」带偏；DDG 在国内常 Network unreachable
                List<Map<String, Object>> batch = webSearchSo360(variant);
                if (batch.isEmpty()) {
                    batch = webSearchBingCn(variant);
                }
                if (batch.isEmpty()) {
                    batch = webSearchDuckDuckGoHtml(variant);
                }
                if (batch.isEmpty()) {
                    batch = webSearchDuckDuckGo(variant);
                }
                for (Map<String, Object> hit : batch) {
                    String key = str(hit.get("url"));
                    if (key == null || key.isBlank()) key = str(hit.get("title"));
                    if (key == null || key.isBlank()) continue;
                    int score = relevanceScore(originalUserQuery, variant, hit, anchors);
                    if (score < 3) continue;
                    if (!passesAnchorGate(hit, anchors, false)) continue;
                    Map<String, Object> prev = merged.get(key);
                    if (prev == null) {
                        hit.put("_score", score);
                        merged.put(key, hit);
                    } else {
                        int old = ((Number) prev.getOrDefault("_score", 0)).intValue();
                        if (score > old) {
                            hit.put("_score", score);
                            merged.put(key, hit);
                        } else {
                            prev.put("_score", old + 1);
                        }
                    }
                }
            }
        }
    }

    /**
     * 动态实体锚点：从用户问题提取。
     * required = 行政区划形态（…省/市/自治区…）等必选实体，必须命中，防错省/全国结果糊弄。
     * 不写死任何省名表。
     */
    private static final class QueryAnchors {
        final List<String> required;       // 地理：必须全部命中
        final List<String> contentPhrases; // 主题长短语
        final List<String> contentTokens;
        final List<String> years;
        final boolean topicRequired;       // 问题含技能/大赛等主题信号

        QueryAnchors(List<String> required, List<String> phrases, List<String> tokens,
                     List<String> years, boolean topicRequired) {
            this.required = required;
            this.contentPhrases = phrases;
            this.contentTokens = tokens;
            this.years = years;
            this.topicRequired = topicRequired;
        }

        boolean isEmpty() {
            return required.isEmpty() && contentPhrases.isEmpty() && contentTokens.isEmpty();
        }
    }

    private static String stemGeoAdmin(String phrase) {
        if (phrase == null || phrase.isBlank()) return phrase;
        return phrase.replaceAll(
                "(特别行政区|壮族自治区|回族自治区|维吾尔自治区|自治区|地区|盟|州|省|市|县|区)$",
                "");
    }

    private boolean blobMatchesRequired(String blob, String req) {
        if (req == null || req.isBlank()) return true;
        if (blob == null) return false;
        if (blob.contains(req)) return true;
        String stem = stemGeoAdmin(req);
        return stem != null && stem.length() >= 2 && !stem.equals(req) && blob.contains(stem);
    }

    private boolean queryHasTopicSignal(String raw) {
        if (raw == null) return false;
        return raw.contains("技能") || raw.contains("大赛") || raw.contains("竞赛")
                || raw.contains("赛项") || raw.contains("备赛") || raw.contains("获奖")
                || raw.contains("路演") || raw.contains("职教") || raw.contains("职业院校")
                || raw.contains("实训") || raw.contains("规程") || raw.contains("报名");
    }

    private boolean blobLooksOffTopicForCompetition(String blob) {
        if (blob == null) return false;
        String[] bad = {
                "旅游", "景点", "景区", "酒店", "美食", "百科", "天气预报", "房产", "买房",
                "股票", "彩票", "娱乐", "明星", "购物", "机票", "火车票"
        };
        for (String b : bad) {
            if (blob.contains(b)) return true;
        }
        return false;
    }

    private boolean blobLooksPortalHomeWithoutTopic(String blob) {
        if (blob == null) return false;
        return blob.contains("人民政府门户") || blob.contains("政务服务网")
                || blob.contains("频道_") || blob.contains("百度百科")
                || (blob.contains("首页") && !blob.contains("大赛") && !blob.contains("技能"));
    }

    private boolean topicMatchedInBlob(String blob, QueryAnchors anchors) {
        if (anchors == null) return true;
        if ((anchors.contentPhrases == null || anchors.contentPhrases.isEmpty())
                && (anchors.contentTokens == null || anchors.contentTokens.isEmpty())) {
            return !anchors.topicRequired;
        }
        if (anchors.contentPhrases != null) {
            for (String p : anchors.contentPhrases) {
                if (p != null && p.length() >= 4 && blob.contains(p)) return true;
            }
        }
        if (blob.contains("技能") && blob.contains("大赛")) return true;
        if (blob.contains("职业院校") && (blob.contains("大赛") || blob.contains("竞赛"))) return true;
        int strong = 0;
        String[] keys = {"技能", "大赛", "竞赛", "赛项", "备赛", "职教", "获奖", "路演", "规程", "报名"};
        for (String k : keys) {
            if (blob.contains(k)) strong++;
        }
        if (strong >= 2) return true;
        int tokenHits = 0;
        if (anchors.contentTokens != null) {
            for (String tok : anchors.contentTokens) {
                if (tok != null && tok.length() >= 2 && blob.contains(tok)) tokenHits++;
            }
        }
        int need = anchors.topicRequired ? 2 : 1;
        return tokenHits >= need;
    }

    private String stripGeoPrefixFromPhrase(String phrase, List<String> required) {
        String p = phrase == null ? "" : phrase;
        if (required != null) {
            for (String g : required) {
                if (g != null && p.startsWith(g)) p = p.substring(g.length());
                String stem = stemGeoAdmin(g);
                if (stem != null && p.startsWith(stem)) p = p.substring(stem.length());
            }
        }
        return p;
    }

    private QueryAnchors extractQueryAnchors(String userQuery) {
        String raw = userQuery == null ? "" : userQuery.trim();
        List<String> years = new ArrayList<>();
        java.util.regex.Matcher ym = Pattern.compile("20\\d{2}").matcher(raw);
        while (ym.find()) {
            if (!years.contains(ym.group())) years.add(ym.group());
        }
        boolean topicRequired = queryHasTopicSignal(raw);
        // 必选：行政区划形态（不枚举地名）
        List<String> required = new ArrayList<>();
        java.util.regex.Matcher gm = Pattern.compile(
                "([\\u4e00-\\u9fff]{2,12}(?:特别行政区|自治区|地区|盟|州|省|市|县|区))"
        ).matcher(raw);
        while (gm.find()) {
            String g = gm.group(1);
            if (!required.contains(g)) required.add(g);
            if (required.size() >= 4) break;
        }
        // 剥口语 + 年份数字
        String t = raw
                .replaceAll("网上有没有|有没有|能不能|帮我|请|搜索|搜一下|查一下|查找|帮我搜|找一下|信息|相关|资料", " ")
                .replaceAll("20\\d{2}年?", " ")
                .replaceAll("[?？!！。，,、；;：:\"'“”‘’]", " ")
                .replaceAll("[的了吗呢吧啊呀]+", " ")
                .replaceAll("\\s+", " ")
                .trim();
        List<String> phrases = new ArrayList<>();
        java.util.regex.Matcher hm = Pattern.compile("[\\u4e00-\\u9fff]{4,}").matcher(t);
        while (hm.find()) {
            String p = hm.group();
            p = p.replaceAll("^[年月日号位]+", "").replaceAll("[年月日]+$", "");
            if (p.length() < 4) continue;
            if (required.contains(p)) continue;
            String topicP = stripGeoPrefixFromPhrase(p, required);
            topicP = topicP.replaceAll("^[年月日号位]+", "");
            if (topicP.length() >= 4) {
                if (!phrases.contains(topicP) && topicP.length() <= 16) phrases.add(topicP);
                if (topicP.length() > 8) {
                    String short8 = topicP.substring(0, 8);
                    if (!phrases.contains(short8)) phrases.add(short8);
                }
            } else if (!phrases.contains(p) && p.length() <= 16) {
                phrases.add(p);
            }
            if (phrases.size() >= 8) break;
        }
        if (topicRequired && phrases.isEmpty()) {
            if (raw.contains("技能") && raw.contains("大赛")) phrases.add("技能大赛");
            else if (raw.contains("职业院校")) phrases.add("职业院校");
        }
        List<String> tokens = new ArrayList<>();
        for (String tok : extractTokens(t)) {
            if (tok.matches("20\\d{2}")) continue;
            if (tok.length() < 2) continue;
            boolean geoTok = false;
            for (String g : required) {
                if (tok.equals(g) || tok.equals(stemGeoAdmin(g))) {
                    geoTok = true;
                    break;
                }
            }
            if (geoTok) continue;
            if (!tokens.contains(tok)) tokens.add(tok);
        }
        return new QueryAnchors(required, phrases, tokens, years, topicRequired);
    }

    private List<String> ensureAnchorPhrasesInQueries(List<String> queries, QueryAnchors anchors) {
        LinkedHashSet<String> out = new LinkedHashSet<>();
        if (queries != null) {
            for (String q : queries) {
                if (q == null || q.isBlank()) continue;
                String qq = q.trim();
                // 强制把 required 实体塞进每条检索式
                if (anchors != null && !anchors.required.isEmpty()) {
                    for (String r : anchors.required) {
                        if (r != null && !qq.contains(r) && !qq.contains(stemGeoAdmin(r))) {
                            qq = r + " " + qq;
                        }
                    }
                }
                out.add(truncate(qq.replaceAll("\\s+", " ").trim(), 40));
            }
        }
        if (anchors != null) {
            // 强检索：required + 年份 + 软短语
            StringBuilder strong = new StringBuilder();
            for (String r : anchors.required) {
                if (strong.length() > 0) strong.append(' ');
                strong.append(r);
            }
            if (!anchors.years.isEmpty()) {
                if (strong.length() > 0) strong.append(' ');
                strong.append(anchors.years.get(0));
            }
            if (!anchors.contentPhrases.isEmpty()) {
                if (strong.length() > 0) strong.append(' ');
                strong.append(anchors.contentPhrases.get(0));
            }
            // 多假设检索：地理 + 主题 + 年份；…省 → 教育厅+主题（主题来自用户短语，非写死赛道表）
            String topic = anchors.contentPhrases.isEmpty() ? "" : anchors.contentPhrases.get(0);
            if (topic.isBlank() && anchors.topicRequired) {
                topic = "技能大赛";
            }
            for (String r : anchors.required) {
                if (r != null && (r.endsWith("省") || r.endsWith("市") || r.endsWith("区"))) {
                    String stem = stemGeoAdmin(r);
                    String y = anchors.years.isEmpty() ? "" : anchors.years.get(0);
                    if (!topic.isBlank()) {
                        out.add(truncate((r + " " + y + " " + topic).trim(), 40));
                        out.add(truncate((stem + " 教育厅 " + y + " " + topic).trim(), 40));
                        out.add(truncate((r + " " + topic + " 通知 公示").trim(), 40));
                    } else {
                        out.add(truncate((stem + " 教育厅 " + y).trim(), 40));
                    }
                }
            }
            if (strong.length() > 0) {
                out.add(truncate(strong.toString().replaceAll("\\s+", " ").trim(), 40));
            } else if (!anchors.contentPhrases.isEmpty()) {
                String main = anchors.contentPhrases.get(0);
                StringBuilder sb = new StringBuilder(main);
                if (!anchors.years.isEmpty()) sb.insert(0, anchors.years.get(0) + " ");
                out.add(truncate(sb.toString().replaceAll("\\s+", " ").trim(), 40));
                out.add(main);
            }
        }
        List<String> list = new ArrayList<>(out);
        if (list.size() > 6) return new ArrayList<>(list.subList(0, 6));
        return list;
    }

    private String quoteLongestPhrase(String query, QueryAnchors anchors) {
        if (query == null || query.isBlank() || anchors == null || anchors.contentPhrases.isEmpty()) {
            return null;
        }
        String main = anchors.contentPhrases.get(0);
        if (main.length() < 4) return null;
        if (query.contains("\"" + main + "\"")) return query;
        if (query.contains(main)) {
            return query.replace(main, "\"" + main + "\"");
        }
        return "\"" + main + "\" " + query;
    }

    private boolean passesAnchorGate(Map<String, Object> hit, QueryAnchors anchors, boolean strict) {
        if (anchors == null || anchors.isEmpty()) return true;
        String title = str(hit.get("title"));
        String snip = str(hit.get("snippet"));
        String page = str(hit.get("pageText"));
        String blob = ((title == null ? "" : title) + " "
                + (snip == null ? "" : snip) + " "
                + (page == null ? "" : page));
        // 主题问句 + 离题页（旅游/百科等）硬否决
        if (anchors.topicRequired || (anchors.contentPhrases != null && !anchors.contentPhrases.isEmpty())) {
            if (blobLooksOffTopicForCompetition(blob)) return false;
            if (blobLooksPortalHomeWithoutTopic(blob) && !topicMatchedInBlob(blob, anchors)) return false;
        }
        // 地理 required 必须全部命中
        if (anchors.required != null) {
            for (String req : anchors.required) {
                if (!blobMatchesRequired(blob, req)) return false;
            }
        }
        boolean topicOk = topicMatchedInBlob(blob, anchors);
        int phraseHits = 0;
        for (String p : anchors.contentPhrases) {
            if (p != null && blob.contains(p)) phraseHits++;
        }
        int tokenHits = 0;
        for (String tok : anchors.contentTokens) {
            if (tok != null && tok.length() >= 2 && blob.contains(tok)) tokenHits++;
        }
        boolean yearOnly = false;
        if (!anchors.years.isEmpty()) {
            boolean hasYear = false;
            for (String y : anchors.years) {
                if (blob.contains(y)) {
                    hasYear = true;
                    break;
                }
            }
            yearOnly = hasYear && !topicOk && (anchors.required == null || anchors.required.isEmpty());
        }
        if (yearOnly) return false;

        // 双硬：有地理 + 有主题 → 两者都要过（禁止「只有河南」的旅游局/门户）
        boolean hasGeo = anchors.required != null && !anchors.required.isEmpty();
        boolean hasTopic = anchors.topicRequired
                || (anchors.contentPhrases != null && !anchors.contentPhrases.isEmpty());
        if (hasGeo && hasTopic) {
            return topicOk; // 地理已在上方检查
        }
        if (!strict) {
            if (hasTopic) return topicOk;
            if (hasGeo) return true;
            return phraseHits >= 1 || tokenHits >= 1;
        }
        if (hasTopic) return topicOk;
        if (hasGeo) {
            return topicOk || phraseHits >= 1 || tokenHits >= 1
                    || (title != null && anchors.required.stream().anyMatch(r -> blobMatchesRequired(title, r)));
        }
        return phraseHits >= 1 || tokenHits >= Math.min(2, Math.max(1, anchors.contentTokens.size() / 3));
    }

    private List<Map<String, Object>> filterByAnchors(
            List<Map<String, Object>> hits,
            QueryAnchors anchors,
            boolean strict
    ) {
        if (hits == null || hits.isEmpty()) return hits == null ? List.of() : hits;
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> h : hits) {
            if (passesAnchorGate(h, anchors, strict)) out.add(h);
        }
        return out;
    }

    private boolean hasStrongAnchorHit(List<Map<String, Object>> hits, QueryAnchors anchors) {
        if (hits == null) return false;
        for (Map<String, Object> h : hits) {
            if (passesAnchorGate(h, anchors, true)) return true;
        }
        return false;
    }

    private List<Map<String, Object>> rankHitsByScore(Map<String, Map<String, Object>> merged, int limit) {
        List<Map<String, Object>> ranked = new ArrayList<>(merged.values());
        ranked.sort((a, b) -> Integer.compare(
                ((Number) b.getOrDefault("_score", 0)).intValue(),
                ((Number) a.getOrDefault("_score", 0)).intValue()
        ));
        if (ranked.size() > limit) {
            ranked = new ArrayList<>(ranked.subList(0, limit));
        }
        return ranked;
    }

    private double avgTopScore(List<Map<String, Object>> ranked, int n) {
        if (ranked == null || ranked.isEmpty()) return 0;
        int take = Math.min(n, ranked.size());
        double s = 0;
        for (int i = 0; i < take; i++) {
            s += ((Number) ranked.get(i).getOrDefault("_score", 0)).doubleValue();
        }
        return s / take;
    }

    @SuppressWarnings("unchecked")
    private List<String> refineWebSearchQueriesViaLlm(
            String userQuery,
            List<String> priorQueries,
            List<String> hitTitles,
            List<String> badTitles,
            QueryAnchors anchors
    ) {
        try {
            Map<String, Object> req = new LinkedHashMap<>();
            req.put("query", userQuery == null ? "" : userQuery);
            req.put("priorQueries", priorQueries == null ? List.of() : priorQueries);
            req.put("hitTitles", hitTitles == null ? List.of() : hitTitles);
            req.put("badTitles", badTitles == null ? List.of() : badTitles);
            List<String> must = new ArrayList<>();
            if (anchors != null) {
                if (anchors.required != null) must.addAll(anchors.required);
                if (anchors.contentPhrases != null) {
                    for (String p : anchors.contentPhrases) {
                        if (!must.contains(p)) must.add(p);
                    }
                }
            }
            if (!must.isEmpty()) {
                req.put("mustKeepPhrases", must);
            }
            req.put("maxQueries", 3);
            Map<String, Object> resp = postAiJson("/api/assistant/v1/refine-search", req, 15_000);
            if (resp == null) return List.of();
            Object qs = resp.get("queries");
            if (!(qs instanceof List<?> list) || list.isEmpty()) return List.of();
            List<String> out = new ArrayList<>();
            for (Object o : list) {
                String s = str(o);
                if (s == null || s.isBlank()) continue;
                s = s.replaceAll("\\s+", " ").trim();
                if (s.length() < 2) continue;
                if (s.length() > 40) s = s.substring(0, 40);
                if (!out.contains(s)) out.add(s);
                if (out.size() >= 3) break;
            }
            return out;
        } catch (Exception e) {
            log.warn("refine-search failed: {}", e.getMessage());
            return List.of();
        }
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> rerankHitsViaLlm(
            String userQuery,
            List<Map<String, Object>> hits,
            int topK
    ) {
        if (hits == null || hits.size() <= 2) return hits == null ? List.of() : hits;
        try {
            // 送轻量字段
            List<Map<String, Object>> slim = new ArrayList<>();
            for (Map<String, Object> h : hits) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("title", h.get("title"));
                String snip = str(h.get("snippet"));
                if (snip != null && snip.length() > 160) snip = snip.substring(0, 160);
                row.put("snippet", snip);
                slim.add(row);
            }
            Map<String, Object> req = new LinkedHashMap<>();
            req.put("query", userQuery == null ? "" : userQuery);
            req.put("hits", slim);
            req.put("topK", topK);
            Map<String, Object> resp = postAiJson("/api/assistant/v1/rerank-hits", req, 12_000);
            if (resp == null) return hits.size() > topK ? new ArrayList<>(hits.subList(0, topK)) : hits;
            Object orderObj = resp.get("order");
            if (!(orderObj instanceof List<?> order) || order.isEmpty()) {
                return hits.size() > topK ? new ArrayList<>(hits.subList(0, topK)) : hits;
            }
            List<Map<String, Object>> out = new ArrayList<>();
            Set<Integer> seen = new java.util.HashSet<>();
            for (Object o : order) {
                int idx;
                try {
                    idx = Integer.parseInt(String.valueOf(o));
                } catch (Exception e) {
                    continue;
                }
                if (idx < 0 || idx >= hits.size() || !seen.add(idx)) continue;
                out.add(hits.get(idx));
                if (out.size() >= topK) break;
            }
            for (int i = 0; i < hits.size() && out.size() < topK; i++) {
                if (seen.add(i)) out.add(hits.get(i));
            }
            return out;
        } catch (Exception e) {
            log.warn("rerank-hits failed: {}", e.getMessage());
            return hits.size() > topK ? new ArrayList<>(hits.subList(0, topK)) : hits;
        }
    }

    /** 兼容旧调用：多 query 单轮 */
    private List<Map<String, Object>> webPublicSearchMulti(List<String> searchQueries, String originalUserQuery) {
        Map<String, Map<String, Object>> merged = new LinkedHashMap<>();
        QueryAnchors anchors = extractQueryAnchors(originalUserQuery);
        mergeSearchRound(merged, searchQueries, originalUserQuery, anchors, null);
        List<Map<String, Object>> ranked = filterByAnchors(rankHitsByScore(merged, 6), anchors, true);
        for (Map<String, Object> h : ranked) {
            h.remove("_score");
        }
        return ranked;
    }

    /**
     * 检索词改写：优先轻量 LLM（ai-scoring），失败回落规则版。
     */
    private List<String> rewriteWebSearchQueries(String userQuery) {
        List<String> llm = rewriteWebSearchQueriesViaLlm(userQuery);
        if (llm != null && !llm.isEmpty()) {
            log.info("web query rewrite source=llm n={} q0={}", llm.size(), truncate(llm.get(0), 40));
            return llm;
        }
        List<String> rules = rewriteWebSearchQueriesRules(userQuery);
        log.info("web query rewrite source=rules n={} q0={}",
                rules.size(), rules.isEmpty() ? "" : truncate(rules.get(0), 40));
        return rules;
    }

    @SuppressWarnings("unchecked")
    private List<String> rewriteWebSearchQueriesViaLlm(String userQuery) {
        if (userQuery == null || userQuery.isBlank()) return List.of();
        try {
            Map<String, Object> req = new LinkedHashMap<>();
            req.put("query", userQuery.length() > 400 ? userQuery.substring(0, 400) : userQuery);
            req.put("maxQueries", 3);
            Map<String, Object> resp = postAiJson("/api/assistant/v1/rewrite-search", req, 12_000);
            if (resp == null) return List.of();
            Object qs = resp.get("queries");
            if (!(qs instanceof List<?> list) || list.isEmpty()) return List.of();
            List<String> out = new ArrayList<>();
            for (Object o : list) {
                String s = str(o);
                if (s == null || s.isBlank()) continue;
                s = s.replaceAll("\\s+", " ").trim();
                if (s.length() < 2) continue;
                if (s.length() > 40) s = s.substring(0, 40);
                if (!out.contains(s)) out.add(s);
                if (out.size() >= 3) break;
            }
            return out;
        } catch (Exception e) {
            log.warn("LLM rewrite-search failed, fallback rules: {}", e.getMessage());
            return List.of();
        }
    }

    /**
     * 通用规则兜底（LLM 失败时）：只剥口语壳、保留用户原句里的实体/时间/意图词。
     * <b>不写死</b>任何赛道/题型模板（开场词、名单等由 LLM 按当前问题动态生成）。
     */
    private List<String> rewriteWebSearchQueriesRules(String userQuery) {
        String raw = userQuery == null ? "" : userQuery.trim();
        if (raw.isBlank()) return List.of();

        String t = raw
                .replaceAll("[?？!！。，,、；;：:\"'“”‘’（）()\\[\\]【】]", " ")
                .replaceAll("网上有没有|有没有|能不能|可不可以|帮我找|请给我|请问|谢谢|真实参加|真实", " ")
                .replaceAll("比较好|优秀|经典|范文|例子|示例|样例|搜索|搜一下|查一下|帮我|一下", " ")
                .replaceAll("\\s+", " ")
                .trim();

        for (String stop : List.of(
                "网上", "一个", "一些", "什么", "怎么", "如何", "可以", "需要",
                "给我", "找找", "看看", "推荐", "相关", "内容", "资料", "的", "了", "吗", "呢",
                "啊", "吧", "是", "在", "和", "与", "或", "就", "都", "很", "太", "更", "最", "好的"
        )) {
            t = t.replace(stop, " ");
        }
        t = t.replaceAll("\\s+", " ").trim();

        LinkedHashSet<String> out = new LinkedHashSet<>();
        if (t.length() >= 2 && t.length() <= 40) {
            out.add(t);
        } else if (t.length() > 40) {
            String[] parts = t.split("\\s+");
            StringBuilder a = new StringBuilder();
            StringBuilder b = new StringBuilder();
            int n = 0;
            for (String p : parts) {
                if (p.length() < 2) continue;
                if (n < 4) {
                    if (a.length() > 0) a.append(' ');
                    a.append(p);
                } else if (n < 8) {
                    if (b.length() > 0) b.append(' ');
                    b.append(p);
                }
                n++;
            }
            if (a.length() >= 2) out.add(truncate(a.toString(), 36));
            if (b.length() >= 2) out.add(truncate(b.toString(), 36));
        }
        // 抽出年份作为另一检索角度（通用）
        java.util.regex.Matcher ym = Pattern.compile("20\\d{2}").matcher(raw);
        if (ym.find() && !out.isEmpty()) {
            String first = out.iterator().next();
            out.add(truncate(ym.group() + " " + first, 36));
        }
        if (out.isEmpty()) {
            String cleaned = raw.replaceAll("[?？!！]", " ").replaceAll("\\s+", " ").trim();
            if (cleaned.length() > 40) cleaned = cleaned.substring(0, 40);
            if (!cleaned.isBlank()) out.add(cleaned);
        }
        List<String> list = new ArrayList<>(out);
        if (list.size() > 3) return new ArrayList<>(list.subList(0, 3));
        return list;
    }

    /**
     * 对 top hits 抓取正文，加长 snippet / pageText。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> enrichHitsWithPageBodies(List<Map<String, Object>> hits) {
        if (hits == null || hits.isEmpty()) return hits == null ? List.of() : hits;
        try {
            Map<String, Object> req = new LinkedHashMap<>();
            req.put("hits", hits);
            req.put("maxPages", Math.min(5, Math.max(1, hits.size())));
            req.put("maxChars", 2400);
            Map<String, Object> resp = postAiJson("/api/assistant/v1/enrich-hits", req, 30_000);
            if (resp == null) return hits;
            Object enriched = resp.get("hits");
            if (!(enriched instanceof List<?> list) || list.isEmpty()) return hits;
            List<Map<String, Object>> out = new ArrayList<>();
            for (Object o : list) {
                if (o instanceof Map<?, ?> m) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (Map.Entry<?, ?> e : m.entrySet()) {
                        if (e.getKey() != null) row.put(String.valueOf(e.getKey()), e.getValue());
                    }
                    out.add(row);
                }
            }
            int n = 0;
            for (Map<String, Object> h : out) {
                if (Boolean.TRUE.equals(h.get("fetched"))) n++;
            }
            log.info("enrich-hits fetched={} / {}", n, out.size());
            return out.isEmpty() ? hits : out;
        } catch (Exception e) {
            log.warn("enrich-hits failed: {}", e.getMessage());
            return hits;
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> postAiJson(String path, Map<String, Object> req, int readTimeoutMs) {
        try {
            HttpURLConnection conn = (HttpURLConnection) URI.create(aiBaseUrl + path).toURL().openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(4_000);
            conn.setReadTimeout(Math.max(3_000, readTimeoutMs));
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            conn.setRequestProperty("Accept", "application/json");
            try (OutputStream os = conn.getOutputStream()) {
                os.write(objectMapper.writeValueAsBytes(req));
            }
            int code = conn.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
            if (stream == null) {
                log.warn("postAiJson {} no body HTTP {}", path, code);
                return null;
            }
            String body = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            if (code < 200 || code >= 300) {
                log.warn("postAiJson {} HTTP {} {}", path, code, truncate(body, 160));
                return null;
            }
            return objectMapper.readValue(body, Map.class);
        } catch (Exception e) {
            log.warn("postAiJson {} failed: {}", path, e.getMessage());
            return null;
        }
    }

    private static boolean containsAny(String text, String... keys) {
        if (text == null) return false;
        for (String k : keys) {
            if (k != null && !k.isBlank() && text.contains(k)) return true;
        }
        return false;
    }

    /** 是否像「要上网查」的意图（名单/搜索/官网/贴链接等） */
    private static boolean looksLikeWebSearchIntent(String query) {
        if (query == null || query.isBlank()) return false;
        String q = query.trim();
        if (!extractHttpUrls(q).isEmpty()) return true;
        return containsAny(q,
                "搜索", "搜一下", "查一下", "网上", "百度", "谷歌", "必应",
                "获奖名单", "获奖名单", "公示", "官网", "最新名单", "国赛名单",
                "查查", "帮我搜", "找一下", "有没有公开",
                "这个网站", "这个链接", "网页内容", "打开链接"
        ) || (containsAny(q, "名单", "获奖") && containsAny(q, "2024", "2025", "2026", "国赛", "省赛", "大赛"));
    }

    /** 从文本抽取 http(s) URL（去掉尾部中文标点） */
    private static List<String> extractHttpUrls(String text) {
        List<String> out = new ArrayList<>();
        if (text == null || text.isBlank()) return out;
        java.util.regex.Matcher m = Pattern.compile("https?://[^\\s\\[\\]（）()<>\"'“”‘’]+", Pattern.CASE_INSENSITIVE)
                .matcher(text);
        while (m.find()) {
            String u = m.group().replaceAll("[。．，,、；;：:!！?？》>】\\]]+$", "");
            if (u.startsWith("http") && !out.contains(u)) out.add(u);
            if (out.size() >= 5) break;
        }
        return out;
    }

    /** 用户像在要求阅读某链接内容（而非泛搜） */
    private static boolean looksLikeUrlReadIntent(String query) {
        List<String> urls = extractHttpUrls(query);
        if (urls.isEmpty()) return false;
        // 含 URL 即优先直抓，避免「告诉」触发词典检索
        return true;
    }

    /**
     * 结果相关度：通用。
     * - 核心实体短语 / 非年份 token 才是主分
     * - 年份只能加分，不能单独过线
     */
    private int relevanceScore(String userQuery, String searchQuery, Map<String, Object> hit, QueryAnchors anchors) {
        String title = str(hit.get("title"));
        String snip = str(hit.get("snippet"));
        String url = str(hit.get("url"));
        String blob = ((title == null ? "" : title) + " " + (snip == null ? "" : snip));
        String blobLower = blob.toLowerCase(Locale.ROOT);
        int score = 0;

        // 实体短语命中（动态，来自用户问题）
        if (anchors != null) {
            // required 未命中 → 0 分（与 gate 一致，禁止错省/全国进候选）
            if (anchors.required != null) {
                for (String req : anchors.required) {
                    if (!blobMatchesRequired(blob, req)) return 0;
                    score += 12;
                    if (title != null && blobMatchesRequired(title, req)) score += 6;
                }
            }
            // 主题问句但结果无主题 → 0 分（禁止河南旅游局等）
            if ((anchors.topicRequired || (anchors.contentPhrases != null && !anchors.contentPhrases.isEmpty()))
                    && !topicMatchedInBlob(blob, anchors)) {
                return 0;
            }
            if (blobLooksOffTopicForCompetition(blob) && anchors.topicRequired) {
                return 0;
            }
            for (String p : anchors.contentPhrases) {
                if (p != null && blob.contains(p)) {
                    score += 8;
                    if (title != null && title.contains(p)) score += 4;
                }
            }
            int tokenHits = 0;
            for (String tok : anchors.contentTokens) {
                if (tok.length() < 2) continue;
                String t = tok.toLowerCase(Locale.ROOT);
                if (blobLower.contains(t)) {
                    tokenHits++;
                    if (title != null && title.toLowerCase(Locale.ROOT).contains(t)) score += 3;
                    else score += 2;
                }
            }
            boolean yearHit = false;
            for (String y : anchors.years) {
                if (blob.contains(y)) {
                    yearHit = true;
                    break;
                }
            }
            boolean contentHit = tokenHits > 0
                    || anchors.contentPhrases.stream().anyMatch(p -> p != null && blob.contains(p))
                    || (anchors.required != null && !anchors.required.isEmpty());
            if (yearHit && !contentHit) return 0;
            if (yearHit && contentHit) score += 2;
            if (!contentHit) return 0;
        } else {
            // 无 anchors 时退回 token 重叠
            for (String tok : extractTokens(userQuery)) {
                if (tok.matches("20\\d{2}")) continue;
                if (tok.length() >= 2 && blobLower.contains(tok.toLowerCase(Locale.ROOT))) score += 2;
            }
        }

        // 检索词额外命中
        if (searchQuery != null) {
            for (String tok : extractTokens(searchQuery)) {
                if (tok.matches("20\\d{2}")) continue;
                if (tok.length() >= 2 && blobLower.contains(tok.toLowerCase(Locale.ROOT))) score += 1;
            }
        }

        // 轻量噪声降权
        String[] negative = {
                "网上银行", "电子银行", "网上办税", "办税", "人社厅", "就业服务云",
                "学信网", "个人所得税", "公积金", "网上营业厅", "国民经济", "统计公报",
                "居民收入", "消费支出", "经济半年报"
        };
        for (String n : negative) {
            if (blobLower.contains(n.toLowerCase(Locale.ROOT))) score -= 8;
        }
        if (url != null) {
            String ul = url.toLowerCase(Locale.ROOT);
            // soft 权威偏好（形态，不写死省站名表）
            if (ul.contains(".gov.cn")) score += 10;
            if (ul.contains(".edu.cn")) score += 8;
            if (ul.contains("moe.gov")) score += 3;
            if (ul.contains("bank") || ul.contains("boc.cn") || ul.contains("icbc") || ul.contains("stats.gov")) {
                score -= 6;
            }
            if (ul.contains("baike.baidu") || ul.contains("sohu.com") || ul.contains("zhihu.com")) {
                score -= 4;
            }
        }
        return Math.max(0, score);
    }

    /** 通用分词：空白切分 + 连续中文的二元组（无 jieba 依赖） */
    private List<String> extractTokens(String text) {
        List<String> out = new ArrayList<>();
        if (text == null || text.isBlank()) return out;
        String t = text.replaceAll("[?？!！。，,、；;：:\"'“”‘’（）()\\[\\]【】/\\\\|]", " ");
        for (String part : t.split("\\s+")) {
            if (part.isBlank()) continue;
            if (part.matches("[A-Za-z0-9_\\-\\.]{2,}")) {
                out.add(part);
                continue;
            }
            // 中文连续串 → 二元组 + 三元（若够长）
            StringBuilder han = new StringBuilder();
            for (int i = 0; i < part.length(); ) {
                int cp = part.codePointAt(i);
                i += Character.charCount(cp);
                if (Character.UnicodeScript.of(cp) == Character.UnicodeScript.HAN) {
                    han.appendCodePoint(cp);
                } else {
                    flushHan(han, out);
                    if (Character.isLetterOrDigit(cp)) {
                        // skip single
                    }
                }
            }
            flushHan(han, out);
        }
        return out;
    }

    private void flushHan(StringBuilder han, List<String> out) {
        if (han.length() == 0) return;
        String s = han.toString();
        han.setLength(0);
        if (s.length() == 1) {
            out.add(s);
            return;
        }
        for (int i = 0; i + 1 < s.length(); i++) {
            out.add(s.substring(i, i + 2));
        }
        if (s.length() >= 3) {
            for (int i = 0; i + 2 < s.length(); i++) {
                out.add(s.substring(i, i + 3));
            }
        }
    }

    private List<Map<String, Object>> webSearchBingCn(String query) {
        List<Map<String, Object>> hits = new ArrayList<>();
        if (query == null || query.isBlank()) return hits;
        try {
            String q = java.net.URLEncoder.encode(query, StandardCharsets.UTF_8);
            // 国内服务器用 cn.bing.com + 浏览器 UA 才能拿到 b_algo（机器 UA 常被踢回首页）
            URI uri = URI.create("https://cn.bing.com/search?q=" + q + "&setlang=zh-CN&ensearch=0");
            HttpURLConnection conn = (HttpURLConnection) uri.toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(8_000);
            conn.setReadTimeout(10_000);
            conn.setInstanceFollowRedirects(true);
            conn.setRequestProperty("User-Agent",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            + "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");
            conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            conn.setRequestProperty("Accept", "text/html,application/xhtml+xml");
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) {
                log.warn("webSearchBingCn HTTP {}", code);
                return hits;
            }
            String body = new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            // 被跳到首页则无结果
            if (!body.contains("b_algo") && body.contains("og:title") && body.length() < 25000) {
                log.warn("webSearchBingCn got homepage shell for q={}", truncate(query, 40));
                return hits;
            }
            Pattern blockPat = Pattern.compile(
                    "<li class=\"b_algo\"[^>]*>([\\s\\S]*?)</li>",
                    Pattern.CASE_INSENSITIVE);
            Pattern linkPat = Pattern.compile(
                    "<h2[^>]*>\\s*<a[^>]+href=\"([^\"]+)\"[^>]*>([\\s\\S]*?)</a>",
                    Pattern.CASE_INSENSITIVE);
            Pattern capPat = Pattern.compile(
                    "<p[^>]*>([\\s\\S]*?)</p>",
                    Pattern.CASE_INSENSITIVE);
            java.util.regex.Matcher bm = blockPat.matcher(body);
            while (bm.find() && hits.size() < 8) {
                String block = bm.group(1);
                java.util.regex.Matcher lm = linkPat.matcher(block);
                if (!lm.find()) continue;
                String href = lm.group(1);
                String title = stripHtml(lm.group(2));
                if (title.isBlank()) continue;
                String snippet = "";
                java.util.regex.Matcher cm = capPat.matcher(block);
                if (cm.find()) snippet = stripHtml(cm.group(1));
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "web");
                c.put("title", title.length() > 80 ? title.substring(0, 80) + "…" : title);
                c.put("snippet", snippet.length() > 200 ? snippet.substring(0, 200) + "…" : snippet);
                c.put("url", href);
                hits.add(c);
            }
            if (hits.isEmpty()) {
                log.warn("webSearchBingCn parsed 0 results for q={}", truncate(query, 40));
            } else {
                log.info("webSearchBingCn hits={} q={}", hits.size(), truncate(query, 40));
            }
        } catch (Exception e) {
            log.warn("webSearchBingCn failed: {}", e.getMessage());
        }
        return hits;
    }

    /**
     * 360 搜索（so.com）：国内服务器可达，中文时效查询（名单/通知）召回明显优于 Bing。
     * 结果链优先取 data-mdurl 真链，避免 so.com/link 跳转壳。
     */
    private List<Map<String, Object>> webSearchSo360(String query) {
        List<Map<String, Object>> hits = new ArrayList<>();
        if (query == null || query.isBlank()) return hits;
        try {
            String q = java.net.URLEncoder.encode(query, StandardCharsets.UTF_8);
            URI uri = URI.create("https://www.so.com/s?q=" + q);
            HttpURLConnection conn = (HttpURLConnection) uri.toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(8_000);
            conn.setReadTimeout(12_000);
            conn.setInstanceFollowRedirects(true);
            conn.setRequestProperty("User-Agent",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            + "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");
            conn.setRequestProperty("Accept", "text/html,application/xhtml+xml");
            conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) {
                log.warn("webSearchSo360 HTTP {}", code);
                return hits;
            }
            String body = new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            Pattern blockPat = Pattern.compile(
                    "<li class=\"res-list\"[^>]*>([\\s\\S]*?)</li>",
                    Pattern.CASE_INSENSITIVE);
            Pattern titlePat = Pattern.compile(
                    "class=\"res-title\"[^>]*>\\s*<a[^>]+>([\\s\\S]*?)</a>",
                    Pattern.CASE_INSENSITIVE);
            Pattern mdurlPat = Pattern.compile(
                    "data-mdurl=\"([^\"]+)\"",
                    Pattern.CASE_INSENSITIVE);
            Pattern hrefPat = Pattern.compile(
                    "href=\"(https?://[^\"]+)\"",
                    Pattern.CASE_INSENSITIVE);
            Pattern sumPat = Pattern.compile(
                    "class=\"res-list-summary\"[^>]*>([\\s\\S]*?)</span>",
                    Pattern.CASE_INSENSITIVE);
            java.util.regex.Matcher bm = blockPat.matcher(body);
            while (bm.find() && hits.size() < 8) {
                String block = bm.group(1);
                java.util.regex.Matcher tm = titlePat.matcher(block);
                if (!tm.find()) continue;
                String title = stripHtml(tm.group(1));
                if (title.isBlank() || title.length() < 4) continue;
                String href = null;
                java.util.regex.Matcher mm = mdurlPat.matcher(block);
                if (mm.find()) href = mm.group(1);
                if (href == null || href.isBlank() || href.contains("hao.360.com")) {
                    java.util.regex.Matcher hm = hrefPat.matcher(block);
                    while (hm.find()) {
                        String cand = hm.group(1);
                        if (cand.contains("so.com/link") || cand.contains("hao.360.com")) continue;
                        href = cand;
                        break;
                    }
                }
                if (href == null || href.isBlank()) continue;
                if (href.startsWith("http://")) {
                    // 多数官网支持 https
                    href = "https://" + href.substring("http://".length());
                }
                String snippet = "";
                java.util.regex.Matcher sm = sumPat.matcher(block);
                if (sm.find()) snippet = stripHtml(sm.group(1));
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "web");
                c.put("title", title.length() > 80 ? title.substring(0, 80) + "…" : title);
                c.put("snippet", snippet.length() > 200 ? snippet.substring(0, 200) + "…" : snippet);
                c.put("url", href);
                hits.add(c);
            }
            if (hits.isEmpty()) {
                log.warn("webSearchSo360 parsed 0 results for q={}", truncate(query, 40));
            } else {
                log.info("webSearchSo360 hits={} q={}", hits.size(), truncate(query, 40));
            }
        } catch (Exception e) {
            log.warn("webSearchSo360 failed: {}", e.getMessage());
        }
        return hits;
    }

    /**
     * DuckDuckGo HTML 版网页检索（非 Instant Answer API）。
     * 海外网络可用；国内服务器常 Network unreachable，仅作兜底。
     */
    private List<Map<String, Object>> webSearchDuckDuckGoHtml(String query) {
        List<Map<String, Object>> hits = new ArrayList<>();
        if (query == null || query.isBlank()) return hits;
        try {
            String q = java.net.URLEncoder.encode(query, StandardCharsets.UTF_8);
            URI uri = URI.create("https://html.duckduckgo.com/html/?q=" + q);
            HttpURLConnection conn = (HttpURLConnection) uri.toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(8_000);
            conn.setReadTimeout(12_000);
            conn.setInstanceFollowRedirects(true);
            conn.setRequestProperty("User-Agent",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            + "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36");
            conn.setRequestProperty("Accept", "text/html,application/xhtml+xml");
            conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) {
                log.warn("webSearchDuckDuckGoHtml HTTP {}", code);
                return hits;
            }
            String body = new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            Pattern linkPat = Pattern.compile(
                    "class=\"result__a\"[^>]*href=\"([^\"]+)\"[^>]*>([\\s\\S]*?)</a>",
                    Pattern.CASE_INSENSITIVE);
            Pattern snipPat = Pattern.compile(
                    "class=\"result__snippet\"[^>]*>([\\s\\S]*?)</(?:a|td|div)>",
                    Pattern.CASE_INSENSITIVE);
            List<String> snips = new ArrayList<>();
            java.util.regex.Matcher sm = snipPat.matcher(body);
            while (sm.find() && snips.size() < 12) {
                snips.add(stripHtml(sm.group(1)));
            }
            java.util.regex.Matcher lm = linkPat.matcher(body);
            int idx = 0;
            while (lm.find() && hits.size() < 8) {
                String href = decodeDuckDuckGoUrl(lm.group(1));
                String title = stripHtml(lm.group(2));
                if (title.isBlank()) {
                    idx++;
                    continue;
                }
                String snippet = idx < snips.size() ? snips.get(idx) : "";
                idx++;
                if (href == null || href.isBlank()) continue;
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "web");
                c.put("title", title.length() > 80 ? title.substring(0, 80) + "…" : title);
                c.put("snippet", snippet.length() > 200 ? snippet.substring(0, 200) + "…" : snippet);
                c.put("url", href);
                hits.add(c);
            }
            if (hits.isEmpty()) {
                log.warn("webSearchDuckDuckGoHtml parsed 0 results for q={}", truncate(query, 40));
            } else {
                log.info("webSearchDuckDuckGoHtml hits={} q={}", hits.size(), truncate(query, 40));
            }
        } catch (Exception e) {
            log.warn("webSearchDuckDuckGoHtml failed: {}", e.getMessage());
        }
        return hits;
    }

    /** 解析 DDG 跳转链 //duckduckgo.com/l/?uddg=https%3A%2F%2F... */
    private static String decodeDuckDuckGoUrl(String href) {
        if (href == null || href.isBlank()) return href;
        try {
            String h = href.trim();
            if (h.startsWith("//")) h = "https:" + h;
            int i = h.indexOf("uddg=");
            if (i >= 0) {
                String rest = h.substring(i + 5);
                int amp = rest.indexOf('&');
                if (amp >= 0) rest = rest.substring(0, amp);
                return java.net.URLDecoder.decode(rest, StandardCharsets.UTF_8);
            }
            return h;
        } catch (Exception e) {
            return href;
        }
    }

    /** Instant Answer API（英文实体尚可，中文全网检索弱；仅作兜底） */
    private List<Map<String, Object>> webSearchDuckDuckGo(String query) {
        List<Map<String, Object>> hits = new ArrayList<>();
        if (query == null || query.isBlank()) return hits;
        try {
            String q = java.net.URLEncoder.encode(query, StandardCharsets.UTF_8);
            URI uri = URI.create("https://api.duckduckgo.com/?q=" + q + "&format=json&no_html=1&skip_disambig=1");
            HttpURLConnection conn = (HttpURLConnection) uri.toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(4_000);
            conn.setReadTimeout(5_000);
            conn.setRequestProperty("User-Agent", "OREP-Assistant/1.0");
            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) return hits;
            String body = new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            @SuppressWarnings("unchecked")
            Map<String, Object> json = objectMapper.readValue(body, Map.class);
            String abstractText = str(json.get("AbstractText"));
            String abstractUrl = str(json.get("AbstractURL"));
            String heading = str(json.get("Heading"));
            if (abstractText != null && !abstractText.isBlank()) {
                Map<String, Object> c = new LinkedHashMap<>();
                c.put("sourceType", "web");
                c.put("title", heading != null && !heading.isBlank() ? heading : "联网摘要");
                c.put("snippet", abstractText.length() > 220 ? abstractText.substring(0, 220) + "…" : abstractText);
                c.put("url", abstractUrl);
                hits.add(c);
            }
            Object related = json.get("RelatedTopics");
            if (related instanceof List<?> list) {
                for (Object item : list) {
                    if (hits.size() >= 5) break;
                    if (!(item instanceof Map<?, ?> m)) continue;
                    String text = str(m.get("Text"));
                    String firstUrl = str(m.get("FirstURL"));
                    if (text == null || text.isBlank()) continue;
                    Map<String, Object> c = new LinkedHashMap<>();
                    c.put("sourceType", "web");
                    c.put("title", text.length() > 48 ? text.substring(0, 48) + "…" : text);
                    c.put("snippet", text.length() > 180 ? text.substring(0, 180) + "…" : text);
                    c.put("url", firstUrl);
                    hits.add(c);
                }
            }
        } catch (Exception e) {
            log.debug("webSearchDuckDuckGo failed (often blocked in CN): {}", e.getMessage());
        }
        return hits;
    }

    private static String stripHtml(String raw) {
        if (raw == null) return "";
        String s = raw
                .replaceAll("(?is)<script[\\s\\S]*?</script>", " ")
                .replaceAll("(?is)<style[\\s\\S]*?</style>", " ")
                .replaceAll("<[^>]+>", " ")
                .replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", "\"")
                .replace("&#39;", "'");
        s = s.replaceAll("\\s+", " ").trim();
        return s;
    }

    private static Long longVal(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.valueOf(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }

    private static String str(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private static String extension(String name) {
        int i = name.lastIndexOf('.');
        if (i < 0) return "";
        return name.substring(i + 1).toLowerCase();
    }

    private static String truncate(String s, int max) {
        if (s == null) return null;
        return s.length() <= max ? s : s.substring(0, max);
    }

    private static String emptyToNull(String s) {
        return s == null || s.isBlank() ? null : s;
    }

    private String toJson(Object o) {
        try {
            return objectMapper.writeValueAsString(o);
        } catch (JsonProcessingException e) {
            return "{}";
        }
    }
}
