package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.orep.backend.entity.InspireOfficeDocument;
import com.orep.backend.entity.User;
import com.orep.backend.mapper.InspireOfficeDocumentMapper;
import com.orep.backend.mapper.UserMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class InspireOfficeService {

    private static final Logger log = LoggerFactory.getLogger(InspireOfficeService.class);
    private static final Set<String> ALLOWED_EXTS = Set.of(
            "docx", "doc", "odt", "rtf", "txt",
            "xlsx", "xls", "ods", "csv",
            "pptx", "ppt", "odp"
    );
    private static final Set<String> BLANK_EXTS = Set.of("docx", "xlsx", "pptx", "sdoc");
    static final String DEFAULT_SDOC_JSON = "{\"type\":\"doc\",\"content\":[{\"type\":\"paragraph\"}]}";
    private static final Set<String> SCOPES = Set.of("personal", "project", "team");

    private final InspireOfficeDocumentMapper documentMapper;
    private final UserMapper userMapper;
    private final JdbcTemplate jdbc;
    private final OfficeBlankDocumentFactory blankFactory;
    private final WopiAccessTokenService wopiTokens;
    private final ResourceCenterService resourceCenterService;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    private final Map<String, String> discoveryUrlsrcCache = new ConcurrentHashMap<>();
    private volatile long discoveryCachedAt = 0L;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Value("${orep.inspire-office.enabled:true}")
    private boolean enabled;

    /**
     * 后端拉 discovery / 探活地址（容器内或本机）。
     * 由环境变量 OREP_COLLABORA_URL 覆盖，勿在代码里写死云端域名。
     * 本地默认带 service_root：http://127.0.0.1:9980/collabora
     * 云端示例：http://collabora:9980/collabora
     */
    @Value("${orep.inspire-office.collabora-url:http://127.0.0.1:9980/collabora}")
    private String collaboraUrl;

    /**
     * 浏览器 iframe 使用的 Collabora 公网基址（环境变量 OREP_COLLABORA_PUBLIC_URL）。
     * 本地：http://127.0.0.1:5174（经 Vite 代理 /collabora）
     * 云端：https://www.jingsaidanao.com/collabora
     * coolwsd service_root=/collabora 时 discovery path 已含 /collabora，rewrite 只换 origin，不重复拼接。
     */
    @Value("${orep.inspire-office.collabora-public-url:http://127.0.0.1:5174}")
    private String collaboraPublicUrl;

    /**
     * Collabora 容器回调 WOPI 的基址（环境变量 OREP_WOPI_PUBLIC_BASE_URL）。
     * 本地 Docker：http://host.docker.internal:8080
     * 云端：https://www.jingsaidanao.com（或内网后端地址）
     */
    @Value("${orep.inspire-office.wopi-public-base-url:http://host.docker.internal:8080}")
    private String wopiPublicBaseUrl;

    /** 自动保存时若内容 hash 与上一版相同则跳过快照，避免刷屏 */
    @Value("${orep.inspire-office.snapshot-dedupe:true}")
    private boolean snapshotDedupe;

    public InspireOfficeService(
            InspireOfficeDocumentMapper documentMapper,
            UserMapper userMapper,
            JdbcTemplate jdbc,
            OfficeBlankDocumentFactory blankFactory,
            WopiAccessTokenService wopiTokens,
            ResourceCenterService resourceCenterService
    ) {
        this.documentMapper = documentMapper;
        this.userMapper = userMapper;
        this.jdbc = jdbc;
        this.blankFactory = blankFactory;
        this.wopiTokens = wopiTokens;
        this.resourceCenterService = resourceCenterService;
    }

    public Map<String, Object> status() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("enabled", enabled);
        m.put("engine", "collabora");
        m.put("collaboraConfigured", collaboraUrl != null && !collaboraUrl.isBlank());
        m.put("wopiBaseConfigured", wopiPublicBaseUrl != null && !wopiPublicBaseUrl.isBlank());
        m.put("collaboraReachable", probeCollabora());
        return m;
    }

    public List<Map<String, Object>> listDocuments(Long userId, String scope, Long teamId, String q) {
        if (userId == null) {
            return List.of();
        }
        List<Long> memberTeamIds = listMemberTeamIds(userId);
        // 用 apply 拼 OR，避免嵌套 lambda 在部分 MP 版本下异常
        StringBuilder visibility = new StringBuilder(
                "(owner_user_id = {0} AND scope = 'personal')"
        );
        List<Object> args = new ArrayList<>();
        args.add(userId);
        if (!memberTeamIds.isEmpty()) {
            visibility.append(" OR (team_id IN (");
            for (int i = 0; i < memberTeamIds.size(); i++) {
                if (i > 0) visibility.append(',');
                visibility.append('{').append(args.size()).append('}');
                args.add(memberTeamIds.get(i));
            }
            visibility.append(") AND scope IN ('project','team'))");
        }
        visibility.append(" OR (owner_user_id = {").append(args.size()).append("} AND scope IN ('project','team'))");
        args.add(userId);

        LambdaQueryWrapper<InspireOfficeDocument> qw = new LambdaQueryWrapper<>();
        // 必须把 visibility 整体括号起来：AND 优先于 OR，否则
        // status=active 只约束 personal 分支，已删除的 team/project 文档仍会进列表
        qw.eq(InspireOfficeDocument::getStatus, "active");
        qw.apply("(" + visibility + ")", args.toArray());
        if (scope != null && !scope.isBlank() && !"all".equalsIgnoreCase(scope)) {
            String s = scope.trim().toLowerCase();
            if (SCOPES.contains(s)) {
                qw.eq(InspireOfficeDocument::getScope, s);
            }
        }
        if (teamId != null) {
            qw.eq(InspireOfficeDocument::getTeamId, teamId);
        }
        if (q != null && !q.isBlank()) {
            qw.like(InspireOfficeDocument::getTitle, q.trim());
        }
        qw.orderByDesc(InspireOfficeDocument::getUpdatedAt);

        List<InspireOfficeDocument> docs = documentMapper.selectList(qw);
        if (docs == null || docs.isEmpty()) {
            return List.of();
        }
        Set<Long> teamIds = docs.stream()
                .map(InspireOfficeDocument::getTeamId)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());
        Map<Long, String> teamNames = loadTeamNames(teamIds);
        List<Map<String, Object>> result = new ArrayList<>(docs.size());
        for (InspireOfficeDocument d : docs) {
            if (d == null) continue;
            Long tid = d.getTeamId();
            result.add(toView(d, tid == null ? null : teamNames.get(tid)));
        }
        return result;
    }

    public Map<String, Object> getDocumentView(Long id, Long userId) {
        InspireOfficeDocument doc = requireAccessible(id, userId);
        String teamName = doc.getTeamId() != null ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
        return toView(doc, teamName);
    }

    /**
     * 启发 Office 在线/编辑时长心跳。
     * <ul>
     *   <li>onlineSeconds（写入 duration_seconds）：页可见且近期有活跃（打开编辑器、收到 Collabora 消息等）</li>
     *   <li>editSeconds（metadata）：近期有编辑信号（修改状态 / 保存等）</li>
     * </ul>
     * 与任务书驻留同一套间隔累计规则，计入学生总学习时长与教师档案「启发 Office」专项。
     */
    @Transactional
    public Map<String, Object> recordPresence(
            Long tenantId,
            Long userId,
            Long documentId,
            String sessionId,
            boolean visible,
            boolean active,
            boolean editing,
            boolean reset
    ) {
        InspireOfficeDocument doc = requireAccessible(documentId, userId);
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw new IllegalArgumentException("学习会话无效");
        }
        LocalDateTime now = LocalDateTime.now();
        Long teamId = doc.getTeamId();
        String title = doc.getTitle() != null ? doc.getTitle() : "未命名文档";
        String ext = doc.getExt() != null ? doc.getExt() : "";
        String kind = documentKindOf(ext);

        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, duration_seconds durationSeconds, metadata_json metadataJson,
                   started_at startedAt, ended_at endedAt
            FROM student_learning_session
            WHERE user_id = ? AND source_type = 'INSPIRE_DOCUMENT' AND source_id = ?
              AND activity_type = 'INSPIRE_OFFICE'
            FOR UPDATE
            """, userId, documentId);

        if (rows.isEmpty()) {
            String meta = buildPresenceMeta(sessionId, now, 0, title, ext, kind);
            jdbc.update("""
                INSERT INTO student_learning_session
                (tenant_id, user_id, team_id, activity_type, source_type, source_id,
                 started_at, ended_at, duration_seconds, metadata_json)
                VALUES (?, ?, ?, 'INSPIRE_OFFICE', 'INSPIRE_DOCUMENT', ?, ?, ?, 0, ?)
                """,
                    tenantId, userId, teamId, documentId, now, now, meta);
            return presenceResult(documentId, 0, 0, sessionId, title, kind);
        }

        Map<String, Object> current = rows.get(0);
        int onlineSeconds = Math.max(0, intVal(current.get("durationSeconds"), 0));
        String metaRaw = String.valueOf(current.getOrDefault("metadataJson", "{}"));
        int editSeconds = Math.max(0, extractJsonInt(metaRaw, "editSeconds"));
        String previousSession = extractJsonString(metaRaw, "sessionId");
        LocalDateTime previousHeartbeat = parseIsoDateTime(extractJsonString(metaRaw, "lastHeartbeatAt"));
        if (previousHeartbeat == null) {
            previousHeartbeat = asLocalDateTime(current.get("endedAt"));
        }
        boolean sameSession = sessionId.equals(previousSession);

        if (!reset && sameSession && previousHeartbeat != null) {
            double elapsedSeconds = Duration.between(previousHeartbeat, now).toMillis() / 1000.0;
            if (elapsedSeconds >= 0.5 && elapsedSeconds <= 25) {
                int delta = Math.max(1, Math.min(20, (int) Math.round(elapsedSeconds)));
                if (visible && active) {
                    onlineSeconds += delta;
                }
                // 编辑时长是在线时长的子集：仅在编辑信号活跃时累计
                if (visible && editing) {
                    editSeconds += delta;
                }
            }
        }
        // 编辑不超过在线
        editSeconds = Math.min(editSeconds, onlineSeconds);

        String nextMeta = buildPresenceMeta(sessionId, now, editSeconds, title, ext, kind);
        jdbc.update("""
            UPDATE student_learning_session
            SET duration_seconds = ?, ended_at = ?, metadata_json = ?, updated_at = CURRENT_TIMESTAMP,
                team_id = COALESCE(?, team_id),
                tenant_id = COALESCE(tenant_id, ?)
            WHERE id = ?
            """, onlineSeconds, now, nextMeta, teamId, tenantId, current.get("id"));

        return presenceResult(documentId, onlineSeconds, editSeconds, sessionId, title, kind);
    }

    private static String buildPresenceMeta(
            String sessionId, LocalDateTime now, int editSeconds,
            String title, String ext, String kind
    ) {
        String safeTitle = title == null ? "" : title
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", " ")
                .replace("\r", " ");
        if (safeTitle.length() > 120) safeTitle = safeTitle.substring(0, 120);
        String safeExt = ext == null ? "" : ext.replaceAll("[^A-Za-z0-9.]", "");
        String safeKind = kind == null ? "doc" : kind.replaceAll("[^A-Za-z0-9_]", "");
        return """
            {"sessionId":"%s","lastHeartbeatAt":"%s","editSeconds":%d,"title":"%s","ext":"%s","documentKind":"%s"}
            """.formatted(sessionId, now, editSeconds, safeTitle, safeExt, safeKind).trim();
    }

    private static Map<String, Object> presenceResult(
            Long documentId, int onlineSeconds, int editSeconds,
            String sessionId, String title, String kind
    ) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("documentId", documentId);
        m.put("onlineSeconds", onlineSeconds);
        m.put("editSeconds", editSeconds);
        m.put("durationSeconds", onlineSeconds);
        m.put("sessionId", sessionId);
        m.put("title", title);
        m.put("documentKind", kind);
        return m;
    }

    public Map<String, Object> getSmartDoc(Long id, Long userId) {
        ensureSmartDocTable();
        InspireOfficeDocument doc = requireAccessible(id, userId);
        if (!isSdoc(doc)) {
            throw new IllegalArgumentException("该文件不是智能文档");
        }
        String role = roleOf(userId);
        boolean canProtect = SmartDocProtect.canEditProtected(role);
        String json = loadSmartDocJson(doc.getId());
        if (!canProtect) {
            json = SmartDocProtect.redact(json, role);
        }
        Map<String, Object> view = toView(doc, doc.getTeamId() != null
                ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null);
        view.put("content", json);
        view.put("contentUpdatedAt", formatDt(doc.getUpdatedAt()));
        view.put("canEditProtected", canProtect);
        view.put("viewerRole", role);
        return view;
    }

    @Transactional
    public Map<String, Object> saveSmartDoc(Long id, Long userId, String contentJson, String clientUpdatedAt) {
        ensureSmartDocTable();
        InspireOfficeDocument doc = requireAccessible(id, userId);
        if (!isSdoc(doc)) {
            throw new IllegalArgumentException("该文件不是智能文档");
        }
        if (contentJson == null || contentJson.isBlank()) {
            throw new IllegalArgumentException("文档内容不能为空");
        }
        String role = roleOf(userId);
        if (!SmartDocProtect.canEditProtected(role)) {
            contentJson = SmartDocProtect.mergeSealed(loadSmartDocJson(doc.getId()), contentJson, role);
        }
        if (clientUpdatedAt != null && !clientUpdatedAt.isBlank() && doc.getUpdatedAt() != null) {
            try {
                LocalDateTime clientTime = LocalDateTime.parse(clientUpdatedAt.replace(" ", "T"));
                if (doc.getUpdatedAt().isAfter(clientTime.plusSeconds(1))) {
                    throw new IllegalStateException("文档已在其他处更新，请重新加载");
                }
            } catch (IllegalStateException e) {
                throw e;
            } catch (Exception ignored) {
                // 客户端时间格式不对时仍允许保存
            }
        }
        LocalDateTime now = LocalDateTime.now();
        jdbc.update("""
                INSERT INTO inspire_smart_doc(document_id, content_json, schema_version, updated_at)
                VALUES (?,?,1,?)
                ON DUPLICATE KEY UPDATE content_json=VALUES(content_json), updated_at=VALUES(updated_at)
                """, doc.getId(), contentJson, now);
        doc.setUpdatedAt(now);
        doc.setSizeBytes((long) contentJson.getBytes(StandardCharsets.UTF_8).length);
        documentMapper.updateById(doc);
        writeSdocFile(doc, contentJson);
        Map<String, Object> view = toView(doc, doc.getTeamId() != null
                ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null);
        view.put("content", SmartDocProtect.canEditProtected(role)
                ? contentJson
                : SmartDocProtect.redact(contentJson, role));
        view.put("contentUpdatedAt", formatDt(now));
        view.put("canEditProtected", SmartDocProtect.canEditProtected(role));
        return view;
    }

    private void insertSmartDocRow(Long documentId, String json) {
        if (documentId == null) return;
        ensureSmartDocTable();
        jdbc.update("""
                INSERT INTO inspire_smart_doc(document_id, content_json, schema_version, updated_at)
                VALUES (?,?,1,NOW())
                ON DUPLICATE KEY UPDATE document_id=document_id
                """, documentId, json);
    }

    private static boolean isSdoc(InspireOfficeDocument doc) {
        return doc != null && "sdoc".equalsIgnoreCase(OfficeBlankDocumentFactory.normalizeExt(doc.getExt()));
    }

    private String roleOf(Long userId) {
        if (userId == null) return "STUDENT";
        User user = userMapper.selectById(userId);
        if (user == null || user.getRole() == null || user.getRole().isBlank()) return "STUDENT";
        return user.getRole();
    }

    private byte[] readSnapshotBytes(InspireOfficeDocument doc) throws IOException {
        if (isSdoc(doc)) {
            String json = loadSmartDocJson(doc.getId());
            return json.getBytes(StandardCharsets.UTF_8);
        }
        Path current = resolveAbsolutePath(doc.getStoragePath());
        if (!Files.isRegularFile(current)) throw new IllegalStateException("当前文件不存在，无法存档");
        return Files.readAllBytes(current);
    }

    private void writeSdocFile(InspireOfficeDocument doc, String json) {
        if (doc == null || doc.getStoragePath() == null || json == null) return;
        try {
            Path target = resolveAbsolutePath(doc.getStoragePath());
            Files.createDirectories(target.getParent());
            Files.writeString(target, json, StandardCharsets.UTF_8);
        } catch (Exception e) {
            log.warn("sync sdoc file failed id={}: {}", doc.getId(), e.getMessage());
        }
    }

    private void upsertSmartDocJson(Long documentId, String json) {
        if (documentId == null) return;
        String safe = (json == null || json.isBlank()) ? DEFAULT_SDOC_JSON : json;
        ensureSmartDocTable();
        jdbc.update("""
                INSERT INTO inspire_smart_doc(document_id, content_json, schema_version, updated_at)
                VALUES (?,?,1,NOW())
                ON DUPLICATE KEY UPDATE content_json=VALUES(content_json), updated_at=VALUES(updated_at)
                """, documentId, safe);
    }

    private void writeAuditRecord(
            Long documentId,
            String action,
            Long actorUserId,
            String actorName,
            Integer versionNo,
            String detail,
            String metaJson
    ) {
        if (documentId == null || action == null || action.isBlank()) return;
        try {
            jdbc.update("""
                    INSERT INTO inspire_office_audit
                      (document_id, action, actor_user_id, actor_name, version_no, detail, meta_json, created_at)
                    VALUES (?,?,?,?,?,?,?,NOW())
                    """,
                    documentId, action, actorUserId, actorName, versionNo, detail, metaJson);
        } catch (Exception e) {
            log.warn("write sdoc audit failed doc={}: {}", documentId, e.getMessage());
        }
    }

    public Long latestSmartDocId(Long userId) {
        if (userId == null) return null;
        List<Long> ids = jdbc.query(
                """
                SELECT id FROM inspire_office_document
                WHERE owner_user_id = ? AND status = 'active' AND ext = 'sdoc'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (rs, i) -> rs.getLong(1),
                userId
        );
        return ids.isEmpty() ? null : ids.get(0);
    }

    public String readSmartDocContent(Long documentId) {
        ensureSmartDocTable();
        return loadSmartDocJson(documentId);
    }

    @Transactional
    public String replaceSmartDocContent(Long id, Long userId, String contentJson) {
        ensureSmartDocTable();
        InspireOfficeDocument doc = requireAccessible(id, userId);
        if (!isSdoc(doc)) throw new IllegalArgumentException("该文件不是智能文档");
        if (contentJson == null || contentJson.isBlank()) {
            throw new IllegalArgumentException("文档内容不能为空");
        }
        String role = roleOf(userId);
        if (!SmartDocProtect.canEditProtected(role)) {
            contentJson = SmartDocProtect.mergeSealed(loadSmartDocJson(doc.getId()), contentJson, role);
        }
        LocalDateTime now = LocalDateTime.now();
        jdbc.update("""
                INSERT INTO inspire_smart_doc(document_id, content_json, schema_version, updated_at)
                VALUES (?,?,1,?)
                ON DUPLICATE KEY UPDATE content_json=VALUES(content_json), updated_at=VALUES(updated_at)
                """, doc.getId(), contentJson, now);
        doc.setUpdatedAt(now);
        doc.setSizeBytes((long) contentJson.getBytes(StandardCharsets.UTF_8).length);
        documentMapper.updateById(doc);
        writeSdocFile(doc, contentJson);
        return formatDt(now);
    }

    private String loadSmartDocJson(Long documentId) {
        List<String> rows = jdbc.query(
                "SELECT content_json FROM inspire_smart_doc WHERE document_id=?",
                (rs, i) -> rs.getString(1),
                documentId
        );
        if (rows.isEmpty() || rows.get(0) == null || rows.get(0).isBlank()) {
            insertSmartDocRow(documentId, DEFAULT_SDOC_JSON);
            return DEFAULT_SDOC_JSON;
        }
        return rows.get(0);
    }

    private void ensureSmartDocTable() {
        jdbc.execute("""
                CREATE TABLE IF NOT EXISTS inspire_smart_doc (
                    document_id BIGINT PRIMARY KEY,
                    content_json MEDIUMTEXT NOT NULL,
                    schema_version INT NOT NULL DEFAULT 1,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """);
    }

    private static String documentKindOf(String ext) {
        String e = ext == null ? "" : ext.replace(".", "").toLowerCase();
        if (Set.of("pptx", "ppt", "odp", "ppsx", "potx").contains(e)) return "slide";
        if (Set.of("xlsx", "xls", "ods", "csv").contains(e)) return "sheet";
        if ("sdoc".equals(e)) return "sdoc";
        return "word";
    }

    private static String extractJsonString(String json, String key) {
        if (json == null || key == null) return null;
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
                "\"" + key + "\"\\s*:\\s*\"([^\"]*)\""
        ).matcher(json);
        return m.find() ? m.group(1) : null;
    }

    private static int extractJsonInt(String json, String key) {
        if (json == null || key == null) return 0;
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
                "\"" + key + "\"\\s*:\\s*(-?\\d+)"
        ).matcher(json);
        if (!m.find()) return 0;
        try {
            return Integer.parseInt(m.group(1));
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private static LocalDateTime parseIsoDateTime(String raw) {
        if (raw == null || raw.isBlank()) return null;
        try {
            return LocalDateTime.parse(raw.replace(' ', 'T').replaceAll("\\.\\d+$", ""));
        } catch (Exception ignored) {
            return null;
        }
    }

    private static LocalDateTime asLocalDateTime(Object value) {
        if (value == null) return null;
        if (value instanceof LocalDateTime ldt) return ldt;
        if (value instanceof java.sql.Timestamp ts) return ts.toLocalDateTime();
        return parseIsoDateTime(String.valueOf(value));
    }

    private static int intVal(Object value, int defaultValue) {
        if (value == null) return defaultValue;
        if (value instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return defaultValue;
        }
    }

    @Transactional
    public Map<String, Object> createBlank(
            Long userId, Long tenantId, String role, String title, String ext, String scope, Long teamId
    ) throws IOException {
        String normalizedExt = OfficeBlankDocumentFactory.normalizeExt(ext);
        if (!BLANK_EXTS.contains(normalizedExt)) {
            throw new IllegalArgumentException("仅支持新建智能文档 / Word / 表格 / 演示");
        }
        ScopeBinding binding = resolveScope(userId, scope, teamId);
        String safeTitle = sanitizeTitle(title, defaultTitle(normalizedExt));
        byte[] bytes = "sdoc".equals(normalizedExt)
                ? DEFAULT_SDOC_JSON.getBytes(StandardCharsets.UTF_8)
                : blankFactory.createBlank(normalizedExt);
        Map<String, Object> view = persistNew(
                userId, tenantId, role, safeTitle, normalizedExt, bytes, binding, "create"
        );
        if ("sdoc".equals(normalizedExt) && view.get("id") instanceof Number n) {
            insertSmartDocRow(n.longValue(), DEFAULT_SDOC_JSON);
        }
        return view;
    }

    @Transactional
    public Map<String, Object> upload(
            Long userId, Long tenantId, String role, MultipartFile file, String title, String scope, Long teamId
    ) throws IOException {
        if (file == null || file.isEmpty()) throw new IllegalArgumentException("文件为空");
        String original = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document.docx";
        String ext = extractExt(original);
        if (!ALLOWED_EXTS.contains(ext)) throw new IllegalArgumentException("不支持的文件类型: " + ext);
        ScopeBinding binding = resolveScope(userId, scope, teamId);
        String safeTitle = sanitizeTitle(
                title != null && !title.isBlank() ? title : stripExt(original),
                stripExt(original)
        );
        return persistNew(userId, tenantId, role, safeTitle, ext, file.getBytes(), binding, "upload");
    }

    @Transactional
    public Map<String, Object> rename(Long id, Long userId, String title) {
        InspireOfficeDocument doc = requireOwner(id, userId);
        String oldTitle = doc.getTitle();
        doc.setTitle(sanitizeTitle(title, doc.getTitle()));
        doc.setUpdatedAt(LocalDateTime.now());
        documentMapper.updateById(doc);
        writeAudit(doc.getId(), "rename", userId, displayName(userId), doc.getVersion(),
                "「" + oldTitle + "」→「" + doc.getTitle() + "」", null);
        String teamName = doc.getTeamId() != null ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
        return toView(doc, teamName);
    }

    /**
     * 迁移归属：个人 / 项目 / 团队（可换团队）。
     * - 迁入项目/团队：同步（或重新同步）资源中心
     * - 迁出到个人：解除 resource 关联（资源中心已有副本保留，不删除）
     * - 更换团队：向新团队再登记一份资源
     */
    @Transactional
    public Map<String, Object> moveLocation(
            Long id, Long userId, Long tenantId, String role, String scope, Long teamId, boolean syncResource
    ) throws IOException {
        InspireOfficeDocument doc = requireOwner(id, userId);
        String oldScope = doc.getScope();
        Long oldTeamId = doc.getTeamId();
        ScopeBinding binding = resolveScope(userId, scope, teamId);

        boolean same = Objects.equals(oldScope, binding.scope())
                && Objects.equals(oldTeamId, binding.teamId());
        if (same && !syncResource) {
            String teamName = doc.getTeamId() != null
                    ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
            return toView(doc, teamName);
        }

        doc.setScope(binding.scope());
        doc.setTeamId(binding.teamId());
        doc.setUpdatedAt(LocalDateTime.now());

        if ("personal".equals(binding.scope())) {
            doc.setResourceId(null);
            documentMapper.updateById(doc);
            writeAudit(doc.getId(), "move", userId, displayName(userId), doc.getVersion(),
                    describeMove(oldScope, oldTeamId, binding.scope(), binding.teamId()), null);
        } else {
            documentMapper.updateById(doc);
            writeAudit(doc.getId(), "move", userId, displayName(userId), doc.getVersion(),
                    describeMove(oldScope, oldTeamId, binding.scope(), binding.teamId()), null);
            // 迁入或更换团队时同步资源中心
            boolean teamChanged = !Objects.equals(oldTeamId, binding.teamId());
            boolean wasPersonal = "personal".equals(oldScope) || oldTeamId == null;
            if (syncResource || teamChanged || wasPersonal || doc.getResourceId() == null) {
                syncDocToResourceCenter(doc, userId, tenantId, role, true);
            }
        }

        String teamName = doc.getTeamId() != null
                ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
        return toView(doc, teamName);
    }

    /** 手动把当前文件内容同步到资源中心（仅项目/团队）。 */
    @Transactional
    public Map<String, Object> syncToResourceCenter(Long id, Long userId, Long tenantId, String role)
            throws IOException {
        InspireOfficeDocument doc = requireOwner(id, userId);
        if (doc.getTeamId() == null
                || (!"project".equals(doc.getScope()) && !"team".equals(doc.getScope()))) {
            throw new IllegalArgumentException("仅项目/团队文档可同步到资源中心");
        }
        syncDocToResourceCenter(doc, userId, tenantId, role, true);
        String teamName = loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId());
        return toView(doc, teamName);
    }

    /** 复制一份文档（默认归个人，也可指定归属）。 */
    @Transactional
    public Map<String, Object> duplicate(
            Long id, Long userId, Long tenantId, String role, String title, String scope, Long teamId
    ) throws IOException {
        InspireOfficeDocument src = requireAccessible(id, userId);
        ScopeBinding binding = resolveScope(
                userId,
                scope != null && !scope.isBlank() ? scope : "personal",
                teamId
        );
        Path path = resolveAbsolutePath(src.getStoragePath());
        if (!Files.isRegularFile(path)) throw new IllegalStateException("源文件不存在");
        byte[] bytes = Files.readAllBytes(path);
        String safeTitle = sanitizeTitle(
                title != null && !title.isBlank() ? title : (src.getTitle() + " 副本"),
                src.getTitle() + " 副本"
        );
        return persistNew(userId, tenantId, role, safeTitle, src.getExt(), bytes, binding, "duplicate");
    }

    /** 下载当前文件内容。 */
    public DownloadFile prepareDownload(Long id, Long userId) {
        InspireOfficeDocument doc = requireAccessible(id, userId);
        Path path = resolveAbsolutePath(doc.getStoragePath());
        if (!Files.isRegularFile(path)) throw new NoSuchElementException("文件不存在");
        writeAudit(doc.getId(), "download", userId, displayName(userId), doc.getVersion(), "下载文档", null);
        return new DownloadFile(doc, path);
    }

    public record DownloadFile(InspireOfficeDocument document, Path path) {}

    /**
     * 删除文档：元数据标为 deleted，并清理磁盘主文件与版本快照（真正不可再打开/下载）。
     * 资源中心中已同步的独立副本不自动删除。
     * <p>已删除的文档再次删除视为成功（幂等），并尽量补清残留文件。
     */
    @Transactional
    public boolean softDelete(Long id, Long userId) {
        InspireOfficeDocument doc = documentMapper.selectById(id);
        if (doc == null) throw new NoSuchElementException("文档不存在");
        if (!Objects.equals(doc.getOwnerUserId(), userId)) {
            throw new SecurityException("仅所有者可操作");
        }
        if ("deleted".equals(doc.getStatus())) {
            purgeDocumentFiles(doc);
            return true;
        }
        // 先改状态，避免删除文件过程中 WOPI/列表仍可见
        int updated = documentMapper.update(
                null,
                new LambdaUpdateWrapper<InspireOfficeDocument>()
                        .eq(InspireOfficeDocument::getId, doc.getId())
                        .ne(InspireOfficeDocument::getStatus, "deleted")
                        .set(InspireOfficeDocument::getStatus, "deleted")
                        .set(InspireOfficeDocument::getUpdatedAt, LocalDateTime.now())
        );
        if (updated == 0 && !"deleted".equals(doc.getStatus())) {
            // 并发下可能已被删
            InspireOfficeDocument again = documentMapper.selectById(id);
            if (again == null || "deleted".equals(again.getStatus())) {
                if (again != null) purgeDocumentFiles(again);
                return true;
            }
            throw new NoSuchElementException("文档不存在或已删除");
        }
        doc.setStatus("deleted");
        purgeDocumentFiles(doc);
        writeAudit(doc.getId(), "delete", userId, displayName(userId), doc.getVersion(),
                "删除文档并清理存储", null);
        log.info("inspire-office deleted id={} owner={} path={}", doc.getId(), userId, doc.getStoragePath());
        return true;
    }

    /** 删除主文件、版本快照文件与版本表记录；失败仅记日志，不回滚元数据删除。 */
    private void purgeDocumentFiles(InspireOfficeDocument doc) {
        if (doc == null || doc.getId() == null) return;
        Long docId = doc.getId();
        List<String> versionPaths = Collections.emptyList();
        try {
            versionPaths = jdbc.query(
                    "SELECT storage_path FROM inspire_office_version WHERE document_id = ?",
                    (rs, i) -> rs.getString(1),
                    docId
            );
        } catch (Exception e) {
            log.warn("list version paths failed for doc {}: {}", docId, e.getMessage());
        }
        try {
            jdbc.update("DELETE FROM inspire_office_version WHERE document_id = ?", docId);
        } catch (Exception e) {
            log.warn("delete version rows failed for doc {}: {}", docId, e.getMessage());
        }

        if (doc.getStoragePath() != null && !doc.getStoragePath().isBlank()) {
            deleteStorageQuietly(doc.getStoragePath());
        }
        if (versionPaths != null) {
            for (String rel : versionPaths) {
                if (rel != null && !rel.isBlank()) deleteStorageQuietly(rel);
            }
        }
        // 清理 versions/{id}/ 目录（含未入库的残留文件）
        try {
            Path verDir = resolveAbsolutePath("versions/" + docId);
            if (Files.isDirectory(verDir)) {
                try (var stream = Files.list(verDir)) {
                    stream.forEach(p -> {
                        try {
                            Files.deleteIfExists(p);
                        } catch (IOException ex) {
                            log.warn("delete version file {} failed: {}", p, ex.getMessage());
                        }
                    });
                }
                Files.deleteIfExists(verDir);
            }
        } catch (Exception e) {
            log.warn("cleanup version dir for doc {} failed: {}", docId, e.getMessage());
        }
    }

    private void deleteStorageQuietly(String relativeStoragePath) {
        try {
            Path path = resolveAbsolutePath(relativeStoragePath);
            if (Files.deleteIfExists(path)) {
                log.info("purged office file {}", path);
            }
        } catch (Exception e) {
            log.warn("purge office file {} failed: {}", relativeStoragePath, e.getMessage());
        }
    }

    /**
     * 返回前端 iframe 打开 Collabora 所需 URL 与 access_token。
     */
    @Transactional
    public Map<String, Object> buildEditorSession(Long id, Long userId, String mode) {
        if (!enabled) throw new IllegalStateException("启发 Office 未启用");
        if (collaboraUrl == null || collaboraUrl.isBlank()) {
            throw new IllegalStateException("Collabora 地址未配置（orep.inspire-office.collabora-url）");
        }
        if (wopiPublicBaseUrl == null || wopiPublicBaseUrl.isBlank()) {
            throw new IllegalStateException("WOPI 公网基址未配置（orep.inspire-office.wopi-public-base-url）");
        }

        InspireOfficeDocument doc = requireAccessible(id, userId);
        doc.setLastOpenedAt(LocalDateTime.now());
        documentMapper.updateById(doc);

        User user = userMapper.selectById(userId);
        String username = user != null && user.getUsername() != null ? user.getUsername() : ("用户" + userId);
        boolean canWrite = !"view".equalsIgnoreCase(mode);

        writeAudit(doc.getId(), "open", userId, username, doc.getVersion(),
                canWrite ? "打开编辑" : "打开只读", null);

        String accessToken = wopiTokens.issue(doc.getId(), userId, username, canWrite);
        String wopiSrc = trimSlash(wopiPublicBaseUrl) + "/api/wopi/files/" + doc.getId();
        String urlsrc = resolveEditorUrlsrc(doc.getExt());
        String editorUrl = urlsrc
                + "WOPISrc=" + URLEncoder.encode(wopiSrc, StandardCharsets.UTF_8)
                + "&access_token=" + URLEncoder.encode(accessToken, StandardCharsets.UTF_8)
                + "&lang=zh-CN";
        // 仅传本版 CODE 识别的 UIMode（SavedUIState 会报 unknown UI default's component）
        // ShowToolbar / 工具行展开由 deploy/collabora/branding.js 在 iframe 内强制处理
        String kind = mapDocumentType(doc.getExt());
        editorUrl += "&ui_defaults=" + URLEncoder.encode(
                "UIMode=notebookbar",
                StandardCharsets.UTF_8
        );

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("documentId", doc.getId());
        result.put("title", doc.getTitle());
        result.put("ext", doc.getExt());
        result.put("scope", doc.getScope());
        result.put("teamId", doc.getTeamId());
        if (doc.getTeamId() != null) {
            String teamName = loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId());
            if (teamName != null) result.put("teamName", teamName);
        }
        result.put("version", doc.getVersion());
        result.put("engine", "collabora");
        result.put("editorUrl", editorUrl);
        result.put("wopiSrc", wopiSrc);
        result.put("canWrite", canWrite);
        result.put("documentKind", kind);
        result.put("supportsTrackChanges", "word".equals(kind));
        return result;
    }

    // --- 版本存档 / 溯源 ---

    public List<Map<String, Object>> listVersions(Long documentId, Long userId) {
        requireAccessible(documentId, userId);
        return jdbc.query(
                """
                SELECT id, document_id, version_no, source, label, storage_path, size_bytes,
                       content_sha256, created_by, created_at
                FROM inspire_office_version
                WHERE document_id = ?
                ORDER BY version_no DESC
                """,
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("documentId", rs.getLong("document_id"));
                    m.put("versionNo", rs.getInt("version_no"));
                    m.put("source", rs.getString("source"));
                    m.put("label", rs.getString("label"));
                    m.put("sizeBytes", rs.getLong("size_bytes"));
                    m.put("contentSha256", rs.getString("content_sha256"));
                    m.put("createdBy", rs.getObject("created_by") != null ? rs.getLong("created_by") : null);
                    m.put("createdAt", formatDt(rs.getTimestamp("created_at") != null
                            ? rs.getTimestamp("created_at").toLocalDateTime() : null));
                    m.put("sourceLabel", sourceLabel(rs.getString("source")));
                    return m;
                },
                documentId
        );
    }

    public List<Map<String, Object>> listAudits(Long documentId, Long userId, Integer limit) {
        requireAccessible(documentId, userId);
        int lim = limit == null || limit < 1 ? 100 : Math.min(limit, 500);
        return jdbc.query(
                """
                SELECT id, document_id, action, actor_user_id, actor_name, version_no, detail, meta_json, created_at
                FROM inspire_office_audit
                WHERE document_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (rs, i) -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", rs.getLong("id"));
                    m.put("documentId", rs.getLong("document_id"));
                    m.put("action", rs.getString("action"));
                    m.put("actionLabel", actionLabel(rs.getString("action")));
                    m.put("actorUserId", rs.getObject("actor_user_id") != null ? rs.getLong("actor_user_id") : null);
                    m.put("actorName", rs.getString("actor_name"));
                    m.put("versionNo", rs.getObject("version_no") != null ? rs.getInt("version_no") : null);
                    m.put("detail", rs.getString("detail"));
                    m.put("metaJson", rs.getString("meta_json"));
                    m.put("createdAt", formatDt(rs.getTimestamp("created_at") != null
                            ? rs.getTimestamp("created_at").toLocalDateTime() : null));
                    return m;
                },
                documentId,
                lim
        );
    }

    @Transactional
    public Map<String, Object> createManualSnapshot(Long documentId, Long userId, String label) throws IOException {
        InspireOfficeDocument doc = requireAccessible(documentId, userId);
        if (!canAccess(doc, userId)) throw new SecurityException("无权存档");
        byte[] bytes = readSnapshotBytes(doc);
        int nextNo = nextVersionNo(doc.getId());
        doc.setVersion(nextNo);
        doc.setSizeBytes((long) bytes.length);
        doc.setUpdatedAt(LocalDateTime.now());
        documentMapper.updateById(doc);
        Map<String, Object> snap = saveVersionSnapshot(doc, userId, "manual",
                sanitizeTitle(label, "手动存档"), bytes, false);
        writeAuditRecord(doc.getId(), "manual_snapshot", userId, displayName(userId), nextNo,
                label != null && !label.isBlank() ? label : "手动存档", null);
        return snap;
    }

    @Transactional
    public Map<String, Object> restoreVersion(Long documentId, Long userId, int versionNo) throws IOException {
        InspireOfficeDocument doc = requireAccessible(documentId, userId);
        Map<String, Object> ver = jdbc.query(
                """
                SELECT storage_path, size_bytes, content_sha256 FROM inspire_office_version
                WHERE document_id = ? AND version_no = ? LIMIT 1
                """,
                rs -> {
                    if (!rs.next()) return null;
                    Map<String, Object> m = new HashMap<>();
                    m.put("storagePath", rs.getString("storage_path"));
                    m.put("sizeBytes", rs.getLong("size_bytes"));
                    m.put("sha", rs.getString("content_sha256"));
                    return m;
                },
                documentId,
                versionNo
        );
        if (ver == null) throw new NoSuchElementException("版本不存在: v" + versionNo);

        Path snapPath = resolveAbsolutePath(String.valueOf(ver.get("storagePath")));
        if (!Files.isRegularFile(snapPath)) throw new IllegalStateException("版本文件缺失: v" + versionNo);
        byte[] bytes = Files.readAllBytes(snapPath);

        Path target = resolveAbsolutePath(doc.getStoragePath());
        Files.createDirectories(target.getParent());
        Path tmp = target.resolveSibling(target.getFileName() + ".restore-" + UUID.randomUUID());
        Files.write(tmp, bytes);
        try {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING);
        }

        if (isSdoc(doc)) {
            upsertSmartDocJson(doc.getId(), new String(bytes, StandardCharsets.UTF_8));
        }

        int nextNo = nextVersionNo(doc.getId());
        doc.setVersion(nextNo);
        doc.setSizeBytes((long) bytes.length);
        doc.setUpdatedAt(LocalDateTime.now());
        documentMapper.updateById(doc);

        saveVersionSnapshot(doc, userId, "restore", "从 v" + versionNo + " 恢复", bytes, false);
        writeAuditRecord(doc.getId(), "restore", userId, displayName(userId), nextNo,
                "恢复自 v" + versionNo, "{\"fromVersion\":" + versionNo + "}");

        String teamName = doc.getTeamId() != null ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
        return toView(doc, teamName);
    }

    // --- WOPI ---

    public Map<String, Object> wopiCheckFileInfo(String fileId, String accessToken) {
        WopiAccessTokenService.WopiPrincipal p = wopiTokens.parse(accessToken);
        long id = Long.parseLong(fileId);
        if (p.documentId() != id) throw new SecurityException("token document mismatch");
        InspireOfficeDocument doc = getActive(id);
        if (doc == null) throw new NoSuchElementException("file not found");
        if (!canAccess(doc, p.userId())) throw new SecurityException("forbidden");

        Path path = resolveAbsolutePath(doc.getStoragePath());
        long size = 0L;
        try {
            if (Files.isRegularFile(path)) size = Files.size(path);
        } catch (IOException ignored) {
        }

        String baseName = ensureExtInTitle(doc.getTitle(), doc.getExt());
        User user = userMapper.selectById(p.userId());
        String friendly = resolveUserDisplayName(user, p.userId(), p.username());
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("BaseFileName", baseName);
        info.put("Size", size);
        info.put("OwnerId", String.valueOf(doc.getOwnerUserId()));
        info.put("UserId", String.valueOf(p.userId()));
        // 修订痕迹作者名：Collabora/LibreOffice 用 UserFriendlyName 作为修订作者
        info.put("UserFriendlyName", friendly);
        info.put("UserCanWrite", p.canWrite());
        info.put("Version", String.valueOf(doc.getVersion() == null ? 1 : doc.getVersion()));
        info.put("UserCanNotWriteRelative", true);
        info.put("SupportsUpdate", true);
        info.put("SupportsLocks", false);
        info.put("SupportsGetLock", false);
        info.put("SupportsExtendedLockLength", false);
        info.put("SupportsDeleteFile", false);
        info.put("SupportsRename", false);
        info.put("DisablePrint", false);
        info.put("DisableExport", false);
        info.put("DisableCopy", false);
        info.put("EnableOwnerTermination", true);
        info.put("LastModifiedTime", (doc.getUpdatedAt() != null ? doc.getUpdatedAt() : LocalDateTime.now()).toString());
        info.put("PostMessageOrigin", "*");
        // Collabora 扩展：协同头像（与系统侧栏一致：橙底 + 用户名首字）
        info.put("UserExtraInfo", buildUserExtraInfo(p.userId(), user));
        return info;
    }

    /**
     * Collabora CheckFileInfo.UserExtraInfo.avatar。
     * 浏览器（非 Collabora 容器）加载该 URL，故用公网/Vite 源，而非 host.docker.internal。
     */
    private Map<String, Object> buildUserExtraInfo(long userId, User user) {
        Map<String, Object> extra = new LinkedHashMap<>();
        // ?v= 便于样式迭代后绕过 Collabora/浏览器缓存
        extra.put("avatar", trimSlash(browserPublicOrigin()) + "/api/wopi/avatars/" + userId + "?v=4");
        if (user != null && user.getEmail() != null && !user.getEmail().isBlank()) {
            extra.put("mail", user.getEmail());
        }
        return extra;
    }

    /**
     * 浏览器可达的 API 源（去路径）。collabora-public-url 云端常带 /collabora 后缀，只取 origin。
     */
    private String browserPublicOrigin() {
        String base = collaboraPublicUrl;
        if (base == null || base.isBlank()) {
            base = wopiPublicBaseUrl;
        }
        if (base == null || base.isBlank()) {
            return "http://127.0.0.1:8080";
        }
        try {
            URI u = URI.create(base.trim());
            String scheme = u.getScheme() != null ? u.getScheme() : "http";
            String host = u.getHost() != null ? u.getHost() : "127.0.0.1";
            int port = u.getPort();
            if (port > 0) {
                return scheme + "://" + host + ":" + port;
            }
            return scheme + "://" + host;
        } catch (Exception e) {
            return trimSlash(base);
        }
    }

    /**
     * 圆形首字头像（SVG），供 Collabora 协同列表显示。
     * 圆面尽量贴满画布（Collabora 会给 &lt;img&gt; 再加外描边）；底色偏浅避免发闷。
     */
    public String buildUserAvatarSvg(long userId) {
        User user = userMapper.selectById(userId);
        String name = resolveUserDisplayName(user, userId, null);
        String letter = avatarLetter(name);
        // 与侧栏头像 --ds-orange 同色
        String bg = "#e84a1c";
        return """
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" role="img" aria-label="%s">
                  <circle cx="32" cy="32" r="31" fill="%s"/>
                  <text x="32" y="32" dy="0.36em" text-anchor="middle"
                        font-family="system-ui,-apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif"
                        font-size="26" font-weight="700" fill="#ffffff">%s</text>
                </svg>
                """.formatted(escapeXml(name), bg, escapeXml(letter));
    }

    private static String resolveUserDisplayName(User user, long userId, String fallback) {
        if (user != null && user.getUsername() != null && !user.getUsername().isBlank()) {
            return user.getUsername().trim();
        }
        if (fallback != null && !fallback.isBlank()) {
            return fallback.trim();
        }
        return "用户" + userId;
    }

    private static String avatarLetter(String name) {
        if (name == null || name.isBlank()) return "?";
        int cp = name.trim().codePointAt(0);
        return new String(Character.toChars(cp));
    }

    private static String escapeXml(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    public Path wopiGetFilePath(String fileId, String accessToken) {
        WopiAccessTokenService.WopiPrincipal p = wopiTokens.parse(accessToken);
        long id = Long.parseLong(fileId);
        if (p.documentId() != id) throw new SecurityException("token document mismatch");
        InspireOfficeDocument doc = getActive(id);
        if (doc == null) throw new NoSuchElementException("file not found");
        if (!canAccess(doc, p.userId())) throw new SecurityException("forbidden");
        Path path = resolveAbsolutePath(doc.getStoragePath());
        // Word：打开时确保开启修订记录，便于文件内标记作者
        if ("docx".equalsIgnoreCase(doc.getExt())) {
            try {
                ensureDocxTrackRevisions(path);
            } catch (Exception e) {
                log.warn("ensureDocxTrackRevisions failed id={}: {}", id, e.getMessage());
            }
        }
        return path;
    }

    /**
     * 若 docx 未开启 trackRevisions，则写入 settings.xml（就地改包）。
     */
    private void ensureDocxTrackRevisions(Path docxPath) throws IOException {
        if (docxPath == null || !Files.isRegularFile(docxPath)) return;
        byte[] original = Files.readAllBytes(docxPath);
        if (original.length < 4 || original[0] != 'P' || original[1] != 'K') return;

        boolean hasSettings = false;
        boolean alreadyOn = false;
        String contentTypes = null;
        String docRels = null;
        Map<String, byte[]> entries = new LinkedHashMap<>();

        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(original))) {
            ZipEntry e;
            while ((e = zis.getNextEntry()) != null) {
                byte[] data = zis.readAllBytes();
                String name = e.getName();
                entries.put(name, data);
                if ("word/settings.xml".equals(name)) {
                    hasSettings = true;
                    String xml = new String(data, StandardCharsets.UTF_8);
                    if (xml.contains("trackRevisions")) alreadyOn = true;
                }
                if ("[Content_Types].xml".equals(name)) contentTypes = new String(data, StandardCharsets.UTF_8);
                if ("word/_rels/document.xml.rels".equals(name)) docRels = new String(data, StandardCharsets.UTF_8);
            }
        }
        if (alreadyOn) return;

        String settingsXml = """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:trackRevisions/>
                </w:settings>
                """;
        entries.put("word/settings.xml", settingsXml.getBytes(StandardCharsets.UTF_8));

        if (contentTypes != null && !contentTypes.contains("word/settings.xml")) {
            contentTypes = contentTypes.replace(
                    "</Types>",
                    "  <Override PartName=\"/word/settings.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml\"/>\n</Types>"
            );
            entries.put("[Content_Types].xml", contentTypes.getBytes(StandardCharsets.UTF_8));
        }
        if (docRels != null && !docRels.contains("relationships/settings")) {
            if (docRels.contains("</Relationships>")) {
                docRels = docRels.replace(
                        "</Relationships>",
                        "  <Relationship Id=\"rIdTrackSettings\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings\" Target=\"settings.xml\"/>\n</Relationships>"
                );
            } else {
                docRels = """
                        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                          <Relationship Id="rIdTrackSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
                        </Relationships>
                        """;
            }
            entries.put("word/_rels/document.xml.rels", docRels.getBytes(StandardCharsets.UTF_8));
        } else if (docRels == null) {
            entries.put("word/_rels/document.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rIdTrackSettings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
                    </Relationships>
                    """.getBytes(StandardCharsets.UTF_8));
        }

        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            for (Map.Entry<String, byte[]> en : entries.entrySet()) {
                zos.putNextEntry(new ZipEntry(en.getKey()));
                zos.write(en.getValue());
                zos.closeEntry();
            }
        }
        Path tmp = docxPath.resolveSibling(docxPath.getFileName() + ".trk-" + UUID.randomUUID());
        Files.write(tmp, bos.toByteArray());
        try {
            Files.move(tmp, docxPath, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException ex) {
            Files.move(tmp, docxPath, StandardCopyOption.REPLACE_EXISTING);
        }
        log.info("enabled trackRevisions on {}", docxPath.getFileName());
    }

    @Transactional
    public void wopiPutFile(String fileId, String accessToken, byte[] body) throws IOException {
        WopiAccessTokenService.WopiPrincipal p = wopiTokens.parse(accessToken);
        long id = Long.parseLong(fileId);
        if (p.documentId() != id) throw new SecurityException("token document mismatch");
        if (!p.canWrite()) throw new SecurityException("read-only token");
        InspireOfficeDocument doc = getActive(id);
        if (doc == null) throw new NoSuchElementException("file not found");
        if (!canAccess(doc, p.userId())) throw new SecurityException("forbidden");

        byte[] data = body == null ? new byte[0] : body;
        Path target = resolveAbsolutePath(doc.getStoragePath());
        Files.createDirectories(target.getParent());
        Path tmp = target.resolveSibling(target.getFileName() + ".tmp-" + UUID.randomUUID());
        Files.write(tmp, data);
        try {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            Files.move(tmp, target, StandardCopyOption.REPLACE_EXISTING);
        }

        int nextNo = nextVersionNo(doc.getId());
        doc.setSizeBytes((long) data.length);
        doc.setVersion(nextNo);
        doc.setUpdatedAt(LocalDateTime.now());
        documentMapper.updateById(doc);

        Map<String, Object> snap = saveVersionSnapshot(doc, p.userId(), "auto_save", null, data, snapshotDedupe);
        boolean skipped = snap != null && Boolean.TRUE.equals(snap.get("skipped"));
        if (!skipped) {
            writeAudit(doc.getId(), "save", p.userId(), p.username(), nextNo,
                    "协同保存 v" + nextNo, "{\"bytes\":" + data.length + "}");
        }
        log.info("wopi PutFile id={} version={} bytes={} skippedSnap={}",
                doc.getId(), doc.getVersion(), data.length, skipped);
    }

    // --- helpers ---

    private String resolveEditorUrlsrc(String ext) {
        refreshDiscoveryIfNeeded();
        String e = OfficeBlankDocumentFactory.normalizeExt(ext);
        // discovery key: extension lowercase
        String urlsrc = discoveryUrlsrcCache.get(e);
        if (urlsrc == null) {
            // fallback common path for CODE
            String base = trimSlash(browserCollaboraBase());
            urlsrc = base + "/browser/dist/cool.html?";
            log.warn("discovery miss for ext={}, fallback {}", e, urlsrc);
        } else {
            urlsrc = rewriteToPublicCollabora(urlsrc);
        }
        // urlsrc from discovery already ends with ? or &
        if (!urlsrc.endsWith("?") && !urlsrc.endsWith("&")) {
            urlsrc = urlsrc + (urlsrc.contains("?") ? "&" : "?");
        }
        return urlsrc;
    }

    private String browserCollaboraBase() {
        if (collaboraPublicUrl != null && !collaboraPublicUrl.isBlank()) {
            return trimSlash(collaboraPublicUrl);
        }
        return trimSlash(collaboraUrl);
    }

    /**
     * 把 discovery 返回的内网地址改写成浏览器可访问的公网地址。
     * <p>
     * discovery 在 service_root=/collabora 时 path 已是 {@code /collabora/browser/.../cool.html}。
     * 公网基址若也是 {@code https://host/collabora}，只能替换 origin，不能再拼一次 path 前缀，
     * 否则会变成 {@code /collabora/collabora/browser/...} 导致 iframe 空白。
     */
    private String rewriteToPublicCollabora(String urlsrc) {
        if (urlsrc == null || urlsrc.isBlank()) return urlsrc;
        String pub = browserCollaboraBase();
        if (pub.isBlank()) return urlsrc;
        try {
            URI src = URI.create(urlsrc);
            URI pubUri = URI.create(trimSlash(pub));
            String path = src.getRawPath() != null ? src.getRawPath() : "";
            String query = src.getRawQuery();
            String origin = pubUri.getScheme() + "://" + pubUri.getAuthority();
            String serviceRoot = pubUri.getRawPath() != null ? pubUri.getRawPath() : "";

            // discovery 未带 service_root 时补上（例如旧版 coolwsd）
            if (!serviceRoot.isBlank() && !path.startsWith(serviceRoot + "/") && !path.equals(serviceRoot)) {
                path = serviceRoot + (path.startsWith("/") ? path : "/" + path);
            }

            StringBuilder out = new StringBuilder(origin).append(path);
            if (query != null && !query.isBlank()) {
                out.append('?').append(query);
            } else if (urlsrc.endsWith("?")) {
                // discovery 常以 ? 结尾，供后续拼 WOPISrc
                out.append('?');
            }
            return out.toString();
        } catch (Exception e) {
            return urlsrc;
        }
    }

    private void refreshDiscoveryIfNeeded() {
        long now = System.currentTimeMillis();
        if (now - discoveryCachedAt < 60_000 && !discoveryUrlsrcCache.isEmpty()) return;
        try {
            byte[] body = fetchDiscoveryBody();
            if (body == null || body.length == 0) {
                log.warn("collabora discovery empty (tried bases under {})", collaboraUrl);
                return;
            }
            DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
            dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            Document xml = dbf.newDocumentBuilder().parse(new ByteArrayInputStream(body));
            NodeList actions = xml.getElementsByTagName("action");
            Map<String, String> map = new HashMap<>();
            for (int i = 0; i < actions.getLength(); i++) {
                Element el = (Element) actions.item(i);
                String name = el.getAttribute("name");
                String ext = el.getAttribute("ext");
                String urlsrc = el.getAttribute("urlsrc");
                if (("edit".equals(name) || "view".equals(name)) && ext != null && !ext.isBlank() && urlsrc != null) {
                    // prefer edit
                    if ("edit".equals(name) || !map.containsKey(ext.toLowerCase(Locale.ROOT))) {
                        map.put(ext.toLowerCase(Locale.ROOT), urlsrc);
                    }
                }
            }
            if (!map.isEmpty()) {
                discoveryUrlsrcCache.clear();
                discoveryUrlsrcCache.putAll(map);
                discoveryCachedAt = now;
                log.info("collabora discovery loaded {} extensions", map.size());
            }
        } catch (Exception e) {
            log.warn("collabora discovery failed: {}", e.getMessage());
        }
    }

    private boolean probeCollabora() {
        return fetchDiscoveryBody() != null;
    }

    /**
     * 拉取 WOPI discovery XML。
     * coolwsd 可能带 service_root=/collabora（生产与本地 coolwsd.xml 默认），
     * discovery 在 {@code {base}/collabora/hosting/discovery}；也兼容无前缀的 CODE。
     */
    private byte[] fetchDiscoveryBody() {
        for (String base : collaboraDiscoveryBases()) {
            String url = trimSlash(base) + "/hosting/discovery";
            try {
                HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                        .timeout(Duration.ofSeconds(4))
                        .GET()
                        .build();
                HttpResponse<byte[]> res = httpClient.send(req, HttpResponse.BodyHandlers.ofByteArray());
                if (res.statusCode() >= 200 && res.statusCode() < 300
                        && res.body() != null && res.body().length > 0) {
                    // 缓存成功的 base，避免每次都试错
                    if (!trimSlash(base).equals(trimSlash(collaboraUrl))) {
                        log.info("collabora discovery OK via {}", url);
                    }
                    return res.body();
                }
            } catch (Exception e) {
                log.debug("collabora discovery try {} failed: {}", url, e.getMessage());
            }
        }
        return null;
    }

    private List<String> collaboraDiscoveryBases() {
        String raw = collaboraUrl == null ? "" : collaboraUrl.trim();
        LinkedHashSet<String> bases = new LinkedHashSet<>();
        if (!raw.isBlank()) bases.add(trimSlash(raw));
        // 常见：配置了 http://host:9980，实际 service_root=/collabora
        if (!raw.isBlank() && !raw.endsWith("/collabora") && !raw.contains("/collabora/")) {
            bases.add(trimSlash(raw) + "/collabora");
        }
        // 兜底：仅 host:9980
        if (raw.isBlank()) {
            bases.add("http://127.0.0.1:9980");
            bases.add("http://127.0.0.1:9980/collabora");
        }
        return new ArrayList<>(bases);
    }

    private Map<String, Object> persistNew(
            Long userId,
            Long tenantId,
            String role,
            String title,
            String ext,
            byte[] bytes,
            ScopeBinding binding,
            String source
    ) throws IOException {
        String fileKey = UUID.randomUUID().toString().replace("-", "");
        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        String relative = datePath + "/" + fileKey + "." + ext;
        Path abs = resolveAbsolutePath(relative);
        Files.createDirectories(abs.getParent());
        Files.write(abs, bytes);

        LocalDateTime now = LocalDateTime.now();
        InspireOfficeDocument doc = new InspireOfficeDocument();
        doc.setFileKey(fileKey);
        doc.setVersion(1);
        doc.setOwnerUserId(userId);
        doc.setOwnerTenantId(tenantId);
        doc.setTitle(title);
        doc.setExt(ext);
        doc.setStoragePath(relative);
        doc.setSizeBytes((long) bytes.length);
        doc.setScope(binding.scope());
        doc.setTeamId(binding.teamId());
        doc.setStatus("active");
        doc.setCreatedAt(now);
        doc.setUpdatedAt(now);
        documentMapper.insert(doc);

        String action = switch (source) {
            case "upload" -> "upload";
            case "duplicate" -> "duplicate";
            default -> "create";
        };
        String snapLabel = switch (source) {
            case "upload" -> "上传初版";
            case "duplicate" -> "复制初版";
            default -> "创建初版";
        };
        String auditSummary = switch (source) {
            case "upload" -> "上传文档";
            case "duplicate" -> "复制文档";
            default -> "新建空白文档";
        };
        saveVersionSnapshot(doc, userId, source, snapLabel, bytes, false);
        writeAudit(doc.getId(), action, userId, displayName(userId), 1, auditSummary, null);

        String teamName = doc.getTeamId() != null
                ? loadTeamNames(Set.of(doc.getTeamId())).get(doc.getTeamId()) : null;
        Map<String, Object> view = toView(doc, teamName);

        // 项目 / 团队文档：同步一份到资源中心（个人不进资源中心）
        if (doc.getTeamId() != null && ("project".equals(doc.getScope()) || "team".equals(doc.getScope()))) {
            Map<String, Object> resource = syncDocToResourceCenter(doc, userId, tenantId, role, false);
            view.put("syncedToResourceCenter", true);
            view.put("resourceId", resource != null ? resource.get("id") : doc.getResourceId());
            view.put("resourceFolderKey", resourceFolderForExt(ext));
        } else {
            view.put("syncedToResourceCenter", false);
        }
        // 重新 toView 以带上 resourceId
        return toView(doc, teamName);
    }

    /**
     * 将文档当前字节登记到资源中心，并写回 resource_id。
     * @param forceReload true 时从磁盘重读最新内容
     */
    private Map<String, Object> syncDocToResourceCenter(
            InspireOfficeDocument doc,
            Long userId,
            Long tenantId,
            String role,
            boolean forceReload
    ) throws IOException {
        if (doc.getTeamId() == null) return null;
        Path path = resolveAbsolutePath(doc.getStoragePath());
        if (!Files.isRegularFile(path)) {
            throw new IllegalStateException("文档文件不存在，无法同步资源中心");
        }
        byte[] bytes = Files.readAllBytes(path);
        String folderKey = resourceFolderForExt(doc.getExt());
        Map<String, Object> resource = resourceCenterService.registerTeamFile(
                doc.getTeamId(),
                tenantId,
                userId,
                role,
                doc.getTitle(),
                doc.getExt(),
                bytes,
                folderKey
        );
        Object rid = resource.get("id");
        if (rid instanceof Number n) {
            doc.setResourceId(n.intValue());
            doc.setUpdatedAt(LocalDateTime.now());
            documentMapper.updateById(doc);
        }
        writeAudit(doc.getId(), "resource_sync", userId, displayName(userId), doc.getVersion(),
                "同步到资源中心 #" + rid + (forceReload ? "（最新内容）" : ""), null);
        return resource;
    }

    /** 资源中心默认文件夹：演示进 content，其它进 team */
    private static String resourceFolderForExt(String ext) {
        String e = OfficeBlankDocumentFactory.normalizeExt(ext);
        return switch (e) {
            case "pptx", "ppt", "odp" -> "content";
            default -> "team";
        };
    }

    private String describeMove(String fromScope, Long fromTeam, String toScope, Long toTeam) {
        return "归属 " + scopeLabel(fromScope) + teamSuffix(fromTeam)
                + " → " + scopeLabel(toScope) + teamSuffix(toTeam);
    }

    private static String scopeLabel(String scope) {
        if ("project".equals(scope)) return "项目";
        if ("team".equals(scope)) return "团队";
        return "个人";
    }

    private String teamSuffix(Long teamId) {
        if (teamId == null) return "";
        String name = loadTeamNames(Set.of(teamId)).get(teamId);
        return name != null ? "（" + name + "）" : "（#" + teamId + "）";
    }

    private int nextVersionNo(long documentId) {
        Integer max = jdbc.queryForObject(
                "SELECT COALESCE(MAX(version_no), 0) FROM inspire_office_version WHERE document_id = ?",
                Integer.class,
                documentId
        );
        int fromSnap = max == null ? 0 : max;
        InspireOfficeDocument doc = documentMapper.selectById(documentId);
        int fromDoc = doc != null && doc.getVersion() != null ? doc.getVersion() : 0;
        return Math.max(fromSnap, fromDoc) + 1;
    }

    /**
     * @param dedupe 为 true 时，若 hash 与最近一版相同则跳过写入
     * @return 版本视图，或 skipped=true
     */
    private Map<String, Object> saveVersionSnapshot(
            InspireOfficeDocument doc,
            Long userId,
            String source,
            String label,
            byte[] bytes,
            boolean dedupe
    ) throws IOException {
        String sha = sha256Hex(bytes);
        if (dedupe) {
            String lastSha = jdbc.query(
                    """
                    SELECT content_sha256 FROM inspire_office_version
                    WHERE document_id = ? ORDER BY version_no DESC LIMIT 1
                    """,
                    rs -> rs.next() ? rs.getString(1) : null,
                    doc.getId()
            );
            if (lastSha != null && lastSha.equals(sha)) {
                Map<String, Object> skip = new LinkedHashMap<>();
                skip.put("skipped", true);
                skip.put("contentSha256", sha);
                return skip;
            }
        }

        int versionNo = doc.getVersion() == null ? 1 : doc.getVersion();
        // 若该 version_no 已存在（并发），用 next
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM inspire_office_version WHERE document_id = ? AND version_no = ?",
                Integer.class,
                doc.getId(),
                versionNo
        );
        if (exists != null && exists > 0) {
            versionNo = nextVersionNo(doc.getId());
            doc.setVersion(versionNo);
            documentMapper.updateById(doc);
        }

        String snapRel = "versions/" + doc.getId() + "/v" + versionNo + "." + doc.getExt();
        Path snapAbs = resolveAbsolutePath(snapRel);
        Files.createDirectories(snapAbs.getParent());
        Files.write(snapAbs, bytes);

        jdbc.update(
                """
                INSERT INTO inspire_office_version
                  (document_id, version_no, source, label, storage_path, size_bytes, content_sha256, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                doc.getId(),
                versionNo,
                source,
                label,
                snapRel,
                (long) bytes.length,
                sha,
                userId,
                LocalDateTime.now()
        );

        Map<String, Object> m = new LinkedHashMap<>();
        m.put("skipped", false);
        m.put("documentId", doc.getId());
        m.put("versionNo", versionNo);
        m.put("source", source);
        m.put("label", label);
        m.put("sizeBytes", (long) bytes.length);
        m.put("contentSha256", sha);
        m.put("createdBy", userId);
        return m;
    }

    /** 产品已改为「文件内修订痕迹」溯源，业务侧审计表不再写入。 */
    private void writeAudit(
            Long documentId,
            String action,
            Long actorUserId,
            String actorName,
            Integer versionNo,
            String detail,
            String metaJson
    ) {
        // no-op
    }

    private String displayName(Long userId) {
        if (userId == null) return null;
        User u = userMapper.selectById(userId);
        return u != null && u.getUsername() != null ? u.getUsername() : ("用户" + userId);
    }

    private static String sha256Hex(byte[] data) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] dig = md.digest(data == null ? new byte[0] : data);
            StringBuilder sb = new StringBuilder(dig.length * 2);
            for (byte b : dig) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return null;
        }
    }

    private static String sourceLabel(String source) {
        if (source == null) return "";
        return switch (source) {
            case "auto_save" -> "自动保存";
            case "manual" -> "手动存档";
            case "restore" -> "恢复生成";
            case "create" -> "创建";
            case "upload" -> "上传";
            default -> source;
        };
    }

    private static String actionLabel(String action) {
        if (action == null) return "";
        return switch (action) {
            case "create" -> "创建文档";
            case "upload" -> "上传文档";
            case "open" -> "打开";
            case "save" -> "保存";
            case "manual_snapshot" -> "手动存档";
            case "restore" -> "恢复版本";
            case "rename" -> "重命名";
            case "delete" -> "删除";
            case "download" -> "下载";
            case "move" -> "迁移归属";
            case "duplicate" -> "复制文档";
            case "resource_sync" -> "同步资源中心";
            default -> action;
        };
    }

    private ScopeBinding resolveScope(Long userId, String scopeRaw, Long teamId) {
        String scope = scopeRaw == null || scopeRaw.isBlank() ? "personal" : scopeRaw.trim().toLowerCase();
        if (!SCOPES.contains(scope)) throw new IllegalArgumentException("scope 须为 personal / project / team");
        if ("personal".equals(scope)) return new ScopeBinding("personal", null);
        if (teamId == null) throw new IllegalArgumentException("项目/团队文档须选择团队");
        if (!isTeamMember(teamId, userId)) throw new SecurityException("无权在该团队下创建文档");
        return new ScopeBinding(scope, teamId);
    }

    public InspireOfficeDocument requireAccessible(Long id, Long userId) {
        InspireOfficeDocument doc = getActive(id);
        if (doc == null) throw new NoSuchElementException("文档不存在");
        if (!canAccess(doc, userId)) throw new SecurityException("无权访问该文档");
        return doc;
    }

    private InspireOfficeDocument requireOwner(Long id, Long userId) {
        InspireOfficeDocument doc = getActive(id);
        if (doc == null) throw new NoSuchElementException("文档不存在");
        if (!Objects.equals(doc.getOwnerUserId(), userId)) throw new SecurityException("仅所有者可操作");
        return doc;
    }

    private InspireOfficeDocument getActive(Long id) {
        InspireOfficeDocument doc = documentMapper.selectById(id);
        if (doc == null || !"active".equals(doc.getStatus())) return null;
        return doc;
    }

    private boolean canAccess(InspireOfficeDocument doc, Long userId) {
        if (Objects.equals(doc.getOwnerUserId(), userId)) return true;
        if (doc.getTeamId() != null
                && ("project".equals(doc.getScope()) || "team".equals(doc.getScope()))) {
            return isTeamMember(doc.getTeamId(), userId);
        }
        return false;
    }

    private boolean isTeamMember(Long teamId, Long userId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?",
                Integer.class, teamId, userId
        );
        return count != null && count > 0;
    }

    private List<Long> listMemberTeamIds(Long userId) {
        return jdbc.query(
                "SELECT team_id FROM project_team_member WHERE user_id = ?",
                (rs, i) -> rs.getLong(1), userId
        );
    }

    private Map<Long, String> loadTeamNames(Set<Long> teamIds) {
        if (teamIds == null || teamIds.isEmpty()) return Map.of();
        String placeholders = teamIds.stream().map(id -> "?").collect(Collectors.joining(","));
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, name FROM project_team WHERE id IN (" + placeholders + ")",
                teamIds.toArray()
        );
        Map<Long, String> map = new HashMap<>();
        for (Map<String, Object> row : rows) {
            map.put(((Number) row.get("id")).longValue(), String.valueOf(row.get("name")));
        }
        return map;
    }

    private Path resolveAbsolutePath(String relativeStoragePath) {
        Path base = Paths.get(uploadDir).toAbsolutePath().normalize().resolve("office");
        Path target = base.resolve(relativeStoragePath).normalize();
        if (!target.startsWith(base)) throw new SecurityException("非法存储路径");
        return target;
    }

    private Map<String, Object> toView(InspireOfficeDocument doc, String teamName) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", doc.getId());
        m.put("fileKey", doc.getFileKey());
        m.put("version", doc.getVersion());
        m.put("title", doc.getTitle());
        m.put("ext", doc.getExt());
        m.put("sizeBytes", doc.getSizeBytes());
        m.put("scope", doc.getScope());
        m.put("teamId", doc.getTeamId());
        m.put("teamName", teamName);
        m.put("resourceId", doc.getResourceId());
        m.put("syncedToResourceCenter", doc.getResourceId() != null);
        m.put("ownerUserId", doc.getOwnerUserId());
        m.put("status", doc.getStatus());
        // 序列化为字符串，避免部分客户端/序列化路径对 LocalDateTime 列表处理异常
        m.put("lastOpenedAt", formatDt(doc.getLastOpenedAt()));
        m.put("createdAt", formatDt(doc.getCreatedAt()));
        m.put("updatedAt", formatDt(doc.getUpdatedAt()));
        m.put("documentType", mapDocumentType(doc.getExt()));
        m.put("downloadUrl", "/api/inspire-office/documents/" + doc.getId() + "/download");
        return m;
    }

    private static String formatDt(LocalDateTime dt) {
        return dt == null ? null : dt.toString();
    }

    private static String mapDocumentType(String ext) {
        String e = OfficeBlankDocumentFactory.normalizeExt(ext);
        return switch (e) {
            case "xlsx", "xls", "ods", "csv" -> "cell";
            case "pptx", "ppt", "odp" -> "slide";
            case "sdoc" -> "sdoc";
            default -> "word";
        };
    }

    private static String extractExt(String name) {
        int i = name.lastIndexOf('.');
        if (i < 0 || i == name.length() - 1) return "docx";
        return name.substring(i + 1).toLowerCase(Locale.ROOT);
    }

    private static String stripExt(String name) {
        int i = name.lastIndexOf('.');
        return i > 0 ? name.substring(0, i) : name;
    }

    private static String sanitizeTitle(String title, String fallback) {
        String t = title == null ? "" : title.trim();
        if (t.isEmpty()) t = fallback;
        if (t.length() > 200) t = t.substring(0, 200);
        return t;
    }

    private static String defaultTitle(String ext) {
        return switch (ext) {
            case "xlsx" -> "未命名表格";
            case "pptx" -> "未命名演示";
            case "sdoc" -> "未命名文档";
            default -> "未命名文档";
        };
    }

    private static String ensureExtInTitle(String title, String ext) {
        if (title == null) return "document." + ext;
        if (title.toLowerCase(Locale.ROOT).endsWith("." + ext.toLowerCase(Locale.ROOT))) return title;
        return title + "." + ext;
    }

    private static String trimSlash(String url) {
        if (url == null) return "";
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }

    private record ScopeBinding(String scope, Long teamId) {
    }
}
