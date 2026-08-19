package com.orep.backend.service.assistant;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.Script;
import com.orep.backend.service.CollaborationService;
import com.orep.backend.service.ProjectTeamService;
import com.orep.backend.service.ScriptPatchApplier;
import com.orep.backend.service.ScriptService;
import com.orep.backend.service.TrainingDayLearningResourceService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 小启 AI L2 写操作：先提案，用户确认后才执行。
 */
@Service
public class AssistantActionService {
    private static final Logger log = LoggerFactory.getLogger(AssistantActionService.class);
    private static final Set<String> ALLOWED = Set.of(
            "collab_accept",
            "collab_decline",
            "collab_withdraw",
            "create_task",
            "complete_learning",
            "apply_script_patch"
    );
    private static final int TTL_MINUTES = 30;

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final CollaborationService collaborationService;
    private final ProjectTeamService projectTeamService;
    private final TrainingDayLearningResourceService learningResourceService;
    private final ScriptService scriptService;
    private final String internalToken;

    public AssistantActionService(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            CollaborationService collaborationService,
            ProjectTeamService projectTeamService,
            TrainingDayLearningResourceService learningResourceService,
            ScriptService scriptService,
            @Value("${orep.assistant.internal-token:OREP_ASSISTANT_INTERNAL_DEV_TOKEN}") String internalToken
    ) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.collaborationService = collaborationService;
        this.projectTeamService = projectTeamService;
        this.learningResourceService = learningResourceService;
        this.scriptService = scriptService;
        this.internalToken = internalToken;
    }

    /** AI 服务创建提案（internal token） */
    public Map<String, Object> propose(
            Long tenantId,
            Long userId,
            Long sessionId,
            Long runId,
            Map<String, Object> body,
            String token
    ) {
        assertInternal(token);
        if (tenantId == null || userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "tenantId/userId required");
        }
        String type = str(body.get("actionType"));
        if (type == null || !ALLOWED.contains(type)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的 actionType");
        }
        String title = str(body.get("title"));
        if (title == null || title.isBlank()) {
            title = defaultTitle(type);
        }
        String summary = str(body.get("summary"));
        @SuppressWarnings("unchecked")
        Map<String, Object> args = body.get("args") instanceof Map<?, ?> m
                ? castMap(m)
                : Map.of();
        // 校验参数齐全（不执行）
        validateArgs(type, args);

        String argsJson;
        try {
            argsJson = objectMapper.writeValueAsString(args);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "args 无效");
        }

        LocalDateTime expires = LocalDateTime.now().plusMinutes(TTL_MINUTES);
        KeyHolder kh = new GeneratedKeyHolder();
        String finalTitle = title;
        String finalSummary = summary;
        jdbc.update(con -> {
            PreparedStatement ps = con.prepareStatement("""
                    INSERT INTO ai_assistant_action_proposal
                      (tenant_id, user_id, session_id, run_id, action_type, title, summary, args_json, status, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, NOW())
                    """, Statement.RETURN_GENERATED_KEYS);
            ps.setLong(1, tenantId);
            ps.setLong(2, userId);
            if (sessionId == null) ps.setObject(3, null); else ps.setLong(3, sessionId);
            if (runId == null) ps.setObject(4, null); else ps.setLong(4, runId);
            ps.setString(5, type);
            ps.setString(6, finalTitle);
            ps.setString(7, finalSummary);
            // MySQL JSON 列可直接绑定字符串
            ps.setString(8, argsJson);
            ps.setTimestamp(9, Timestamp.valueOf(expires));
            return ps;
        }, kh);
        long id = kh.getKey() != null ? kh.getKey().longValue() : 0L;

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("proposalId", id);
        out.put("actionType", type);
        out.put("title", title);
        out.put("summary", summary);
        out.put("args", args);
        out.put("status", "pending");
        out.put("expiresAt", expires.toString());
        out.put("confirmLabel", confirmLabel(type));
        out.put("cancelLabel", "取消");
        return out;
    }

    /**
     * 学生端 JWT 提案：只允许讲稿补丁，并校验讲稿归属。
     */
    public Map<String, Object> proposeOwned(Long tenantId, Long userId, Map<String, Object> body) {
        if (tenantId == null || userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "tenantId/userId required");
        }
        if (body == null) body = new LinkedHashMap<>();
        String type = str(body.get("actionType"));
        if (type == null || type.isBlank()) {
            type = "apply_script_patch";
        }
        if (!"apply_script_patch".equals(type)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该入口只支持讲稿补丁");
        }
        Map<String, Object> owned = new LinkedHashMap<>(body);
        owned.put("actionType", type);
        @SuppressWarnings("unchecked")
        Map<String, Object> args = body.get("args") instanceof Map<?, ?> m
                ? castMap(m)
                : Map.of();
        Long scriptId = requireLong(args, "scriptId");
        if (scriptService.getById(scriptId, userId) == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        Long sessionId = longVal(owned.get("sessionId"));
        Long runId = longVal(owned.get("runId"));
        return propose(tenantId, userId, sessionId, runId, owned, internalToken);
    }

    /** 用户确认执行（JWT 会话） */
    @Transactional
    public Map<String, Object> confirm(Long proposalId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = loadOwned(proposalId, tenantId, userId);
        assertPending(row);
        String type = str(row.get("actionType"));
        Map<String, Object> args = parseArgs(row.get("argsJson"));
        Map<String, Object> result;
        try {
            result = execute(type, args, tenantId, userId, role);
            mark(proposalId, "confirmed", result, null);
        } catch (ResponseStatusException e) {
            mark(proposalId, "failed", null, e.getReason());
            throw e;
        } catch (Exception e) {
            log.warn("action confirm failed id={}: {}", proposalId, e.getMessage());
            mark(proposalId, "failed", null, e.getMessage());
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "执行失败：" + e.getMessage());
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("proposalId", proposalId);
        out.put("actionType", type);
        out.put("status", "confirmed");
        out.put("result", result);
        out.put("message", successMessage(type));
        return out;
    }

    /** 用户拒绝 */
    public Map<String, Object> reject(Long proposalId, Long tenantId, Long userId) {
        Map<String, Object> row = loadOwned(proposalId, tenantId, userId);
        assertPending(row);
        mark(proposalId, "rejected", null, null);
        return Map.of("proposalId", proposalId, "status", "rejected", "message", "已取消该操作");
    }

    public Map<String, Object> getProposal(Long proposalId, Long tenantId, Long userId) {
        return publicView(loadOwned(proposalId, tenantId, userId));
    }

    private Map<String, Object> execute(
            String type, Map<String, Object> args, Long tenantId, Long userId, String role
    ) {
        return switch (type) {
            case "collab_accept" -> collaborationService.accept(
                    requireLong(args, "requestId"), tenantId, userId, role);
            case "collab_decline" -> collaborationService.decline(
                    requireLong(args, "requestId"), tenantId, userId, role,
                    Map.of("reason", str(args.get("reason")) != null ? str(args.get("reason")) : "小启AI确认后拒绝"));
            case "collab_withdraw" -> collaborationService.withdraw(
                    requireLong(args, "requestId"), tenantId, userId, role);
            case "create_task" -> {
                Long teamId = requireLong(args, "teamId");
                Map<String, Object> body = new LinkedHashMap<>();
                body.put("title", requireText(args, "title"));
                body.put("description", str(args.get("description")) != null ? str(args.get("description")) : "");
                body.put("priority", str(args.get("priority")) != null ? str(args.get("priority")) : "MEDIUM");
                body.put("status", "TODO");
                if (args.get("dueAt") != null) body.put("dueAt", args.get("dueAt"));
                if (args.get("ownerUserId") != null) body.put("ownerUserId", args.get("ownerUserId"));
                else body.put("ownerUserId", userId);
                if (args.get("stageKey") != null) body.put("stageKey", args.get("stageKey"));
                yield projectTeamService.createTask(teamId, tenantId, userId, role, body);
            }
            case "complete_learning" -> learningResourceService.completeNonVideo(
                    tenantId, userId, requireLong(args, "resourceId"));
            case "apply_script_patch" -> {
                Long scriptId = requireLong(args, "scriptId");
                Integer expectedVersion = requireLong(args, "expectedVersion").intValue();
                List<Map<String, Object>> patches = requirePatches(args);
                Script script = scriptService.applyPatches(scriptId, userId, expectedVersion, patches);
                Map<String, Object> result = new LinkedHashMap<>();
                result.put("scriptId", script.getId());
                result.put("contentVersion", script.getContentVersion());
                result.put("title", script.getTitle());
                result.put("stepIds", patches.stream().map(p -> p.get("stepId")).toList());
                yield result;
            }
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "未知操作");
        };
    }

    private void validateArgs(String type, Map<String, Object> args) {
        switch (type) {
            case "collab_accept", "collab_decline", "collab_withdraw" -> requireLong(args, "requestId");
            case "create_task" -> {
                requireLong(args, "teamId");
                requireText(args, "title");
            }
            case "complete_learning" -> requireLong(args, "resourceId");
            case "apply_script_patch" -> {
                requireLong(args, "scriptId");
                requireLong(args, "expectedVersion");
                requirePatches(args);
            }
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "未知操作");
        }
    }

    private static List<Map<String, Object>> requirePatches(Map<String, Object> args) {
        Object raw = args.get("patches");
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少参数 patches");
        }
        List<Map<String, Object>> out = new java.util.ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> m)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "patches 格式无效");
            }
            Map<String, Object> patch = castMap(m);
            String stepId = requireText(patch, "stepId");
            String field = requireText(patch, "field");
            if (!ScriptPatchApplier.ALLOWED_FIELDS.contains(field)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不允许修改字段: " + field);
            }
            if (!patch.containsKey("before") || !patch.containsKey("after")) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "补丁缺少 before/after");
            }
            patch.put("stepId", stepId);
            patch.put("field", field);
            out.add(patch);
        }
        return out;
    }

    private Map<String, Object> loadOwned(Long id, Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, tenant_id AS tenantId, user_id AS userId, session_id AS sessionId, run_id AS runId,
                       action_type AS actionType, title, summary, args_json AS argsJson, status,
                       result_json AS resultJson, error_message AS errorMessage,
                       expires_at AS expiresAt, confirmed_at AS confirmedAt, created_at AS createdAt
                FROM ai_assistant_action_proposal
                WHERE id = ? AND tenant_id = ? AND user_id = ?
                LIMIT 1
                """, id, tenantId, userId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "操作提案不存在");
        }
        return rows.get(0);
    }

    private void assertPending(Map<String, Object> row) {
        if (!"pending".equals(str(row.get("status")))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该操作已处理或已过期");
        }
        Object exp = row.get("expiresAt");
        if (exp instanceof Timestamp ts && ts.toLocalDateTime().isBefore(LocalDateTime.now())) {
            mark(longVal(row.get("id")), "expired", null, "已过期");
            throw new ResponseStatusException(HttpStatus.CONFLICT, "确认已过期，请重新发起");
        }
        if (exp instanceof LocalDateTime ldt && ldt.isBefore(LocalDateTime.now())) {
            mark(longVal(row.get("id")), "expired", null, "已过期");
            throw new ResponseStatusException(HttpStatus.CONFLICT, "确认已过期，请重新发起");
        }
    }

    private void mark(Long id, String status, Map<String, Object> result, String error) {
        String resultJson = null;
        if (result != null) {
            try {
                resultJson = objectMapper.writeValueAsString(result);
            } catch (Exception ignored) {
            }
        }
        jdbc.update("""
                UPDATE ai_assistant_action_proposal
                SET status = ?,
                    result_json = ?,
                    error_message = ?,
                    confirmed_at = CASE WHEN ? IN ('confirmed','rejected') THEN NOW() ELSE confirmed_at END
                WHERE id = ?
                """, status, resultJson, error, status, id);
    }

    private Map<String, Object> publicView(Map<String, Object> row) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("proposalId", row.get("id"));
        out.put("actionType", row.get("actionType"));
        out.put("title", row.get("title"));
        out.put("summary", row.get("summary"));
        out.put("args", parseArgs(row.get("argsJson")));
        out.put("status", row.get("status"));
        out.put("expiresAt", row.get("expiresAt"));
        out.put("confirmLabel", confirmLabel(str(row.get("actionType"))));
        out.put("errorMessage", row.get("errorMessage"));
        return out;
    }

    private Map<String, Object> parseArgs(Object raw) {
        if (raw == null) return Map.of();
        if (raw instanceof Map<?, ?> m) return castMap(m);
        try {
            return objectMapper.readValue(String.valueOf(raw), new TypeReference<>() {});
        } catch (Exception e) {
            return Map.of();
        }
    }

    private static String defaultTitle(String type) {
        return switch (type) {
            case "collab_accept" -> "接受协作请求";
            case "collab_decline" -> "拒绝协作请求";
            case "collab_withdraw" -> "撤回协作请求";
            case "create_task" -> "创建项目任务";
            case "complete_learning" -> "标记学习完成";
            case "apply_script_patch" -> "写入讲稿修改";
            default -> "确认操作";
        };
    }

    private static String confirmLabel(String type) {
        return switch (type != null ? type : "") {
            case "collab_accept" -> "确认接受";
            case "collab_decline" -> "确认拒绝";
            case "collab_withdraw" -> "确认撤回";
            case "create_task" -> "确认创建";
            case "complete_learning" -> "确认完成";
            case "apply_script_patch" -> "确认写入讲稿";
            default -> "确认执行";
        };
    }

    private static String successMessage(String type) {
        return switch (type) {
            case "collab_accept" -> "已接受协作请求";
            case "collab_decline" -> "已拒绝协作请求";
            case "collab_withdraw" -> "已撤回协作请求";
            case "create_task" -> "任务已创建";
            case "complete_learning" -> "已标记学习完成";
            case "apply_script_patch" -> "讲稿已更新，角色未改";
            default -> "操作已完成";
        };
    }

    private void assertInternal(String token) {
        if (token == null || !internalToken.equals(token)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "invalid internal token");
        }
    }

    private static Long requireLong(Map<String, Object> args, String key) {
        Long v = longVal(args.get(key));
        if (v == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少参数 " + key);
        return v;
    }

    private static String requireText(Map<String, Object> args, String key) {
        String v = str(args.get(key));
        if (v == null || v.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少参数 " + key);
        }
        return v.trim();
    }

    private static Map<String, Object> castMap(Map<?, ?> m) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : m.entrySet()) {
            out.put(String.valueOf(e.getKey()), e.getValue());
        }
        return out;
    }

    private static String str(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private static Long longVal(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }
}
