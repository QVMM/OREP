package com.orep.backend.service;

import org.springframework.context.ApplicationEventPublisher;
import org.springframework.dao.DuplicateKeyException;
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
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
public class CollaborationService {
    private static final Set<String> PRIORITIES = Set.of("LOW", "MEDIUM", "HIGH", "URGENT");
    private static final Set<String> TERMINAL_STATUSES = Set.of("DECLINED", "WITHDRAWN", "COMPLETED");

    private final JdbcTemplate jdbc;
    private final ProjectTeamService projectTeamService;
    private final ApplicationEventPublisher eventPublisher;

    public CollaborationService(
            JdbcTemplate jdbc,
            ProjectTeamService projectTeamService,
            ApplicationEventPublisher eventPublisher
    ) {
        this.jdbc = jdbc;
        this.projectTeamService = projectTeamService;
        this.eventPublisher = eventPublisher;
    }

    public Map<String, Object> summary(Long tenantId, Long userId, String role) {
        List<Map<String, Object>> rows = visibleRows(tenantId, userId, role, null, null, 200);
        int actionRequired = 0;
        int inProgress = 0;
        int createdByMe = 0;
        int completed = 0;
        for (Map<String, Object> row : rows) {
            if (requiresAction(row, userId)) actionRequired++;
            if (isInProgress(row)) inProgress++;
            if (Objects.equals(longValue(row.get("requesterId")), userId)) createdByMe++;
            if ("COMPLETED".equals(text(row.get("status")))) completed++;
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("actionRequired", actionRequired);
        result.put("inProgress", inProgress);
        result.put("createdByMe", createdByMe);
        result.put("completed", completed);
        result.put("total", rows.size());
        return result;
    }

    public Map<String, Object> items(
            Long tenantId,
            Long userId,
            String role,
            String view,
            Long teamId,
            Long cursor,
            Integer requestedLimit
    ) {
        int limit = Math.max(1, Math.min(requestedLimit == null ? 30 : requestedLimit, 50));
        String normalizedView = text(view) == null ? "ACTION_REQUIRED" : text(view).toUpperCase(Locale.ROOT);
        List<Map<String, Object>> rows = visibleRows(tenantId, userId, role, teamId, cursor, 200);
        List<Map<String, Object>> filtered = rows.stream()
                .filter(row -> matchesView(row, userId, normalizedView))
                .limit(limit + 1L)
                .toList();
        boolean hasMore = filtered.size() > limit;
        List<Map<String, Object>> page = new ArrayList<>(
                hasMore ? filtered.subList(0, limit) : filtered
        );
        page.forEach(row -> decorate(row, userId));
        Long nextCursor = hasMore && !page.isEmpty()
                ? longValue(page.get(page.size() - 1).get("id"))
                : null;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("items", page);
        result.put("nextCursor", nextCursor);
        result.put("hasMore", hasMore);
        result.put("view", normalizedView);
        return result;
    }

    @Transactional
    public Map<String, Object> createRequest(
            Long tenantId,
            Long requesterId,
            String role,
            String headerIdempotencyKey,
            Map<String, Object> body
    ) {
        Long teamId = requiredLong(body.get("teamId"), "请选择协作团队");
        Long recipientId = requiredLong(body.get("recipientUserId"), "请选择协作成员");
        if (Objects.equals(requesterId, recipientId)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不能向自己发起协作");
        }
        assertActiveMember(tenantId, teamId, requesterId);
        assertActiveMember(tenantId, teamId, recipientId);
        String title = requiredText(body.get("title"), "请填写协作任务标题", 160);
        String description = optionalText(body.get("description"), 1000);
        String priority = normalizePriority(body.get("priority"));
        LocalDateTime dueAt = parseDateTime(body.get("dueAt"));
        String idempotencyKey = optionalText(
                firstNonBlank(headerIdempotencyKey, body.get("idempotencyKey")),
                120
        );
        if (idempotencyKey == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少幂等请求标识");
        }

        Long requestId;
        try {
            requestId = insert("""
                INSERT INTO collaboration_request(
                  tenant_id,team_id,requester_id,recipient_id,title,description,
                  priority,status,due_at,idempotency_key
                ) VALUES (?,?,?,?,?,?,?,'PENDING',?,?)
                """,
                    tenantId, teamId, requesterId, recipientId, title, description,
                    priority, dueAt, idempotencyKey
            );
        } catch (DuplicateKeyException duplicate) {
            List<Long> existing = jdbc.queryForList("""
                SELECT id FROM collaboration_request
                WHERE tenant_id=? AND requester_id=? AND idempotency_key=?
                """, Long.class, tenantId, requesterId, idempotencyKey);
            if (existing.isEmpty()) throw duplicate;
            return request(existing.get(0), tenantId, requesterId, role);
        }

        eventPublisher.publishEvent(new CollaborationEvent(
                tenantId,
                requesterId,
                recipientId,
                "COLLABORATION_REQUESTED",
                requestId,
                teamId,
                null,
                title,
                null
        ));
        return request(requestId, tenantId, requesterId, role);
    }

    @Transactional
    public Map<String, Object> createRequests(
            Long tenantId,
            Long requesterId,
            String role,
            String headerIdempotencyKey,
            Map<String, Object> body
    ) {
        Long teamId = requiredLong(body.get("teamId"), "请选择协作团队");
        List<Long> recipientIds = recipientIds(body.get("recipientUserIds"));
        String title = requiredText(body.get("title"), "请填写协作任务标题", 160);
        String description = optionalText(body.get("description"), 1000);
        String priority = normalizePriority(body.get("priority"));
        LocalDateTime dueAt = parseDateTime(body.get("dueAt"));
        String batchKey = optionalText(headerIdempotencyKey, 120);
        if (batchKey == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少幂等请求标识");
        }

        assertActiveMember(tenantId, teamId, requesterId);
        for (Long recipientId : recipientIds) {
            if (Objects.equals(requesterId, recipientId)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不能向自己发起协作");
            }
            assertActiveMember(tenantId, teamId, recipientId);
        }

        List<String> derivedKeys = recipientIds.stream()
                .map(recipientId -> batchIdempotencyKey(batchKey, recipientId))
                .toList();
        List<Map<String, Object>> existingRows = new ArrayList<>();
        for (String derivedKey : derivedKeys) {
            existingRows.addAll(batchRows(tenantId, requesterId, derivedKey));
        }
        if (!existingRows.isEmpty()) {
            if (existingRows.size() != recipientIds.size()) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "本次批量协作申请状态不完整，请重新发起"
                );
            }
            List<Map<String, Object>> items = new ArrayList<>();
            for (int index = 0; index < recipientIds.size(); index++) {
                Map<String, Object> existing = existingRows.get(index);
                assertSameBatchRequest(
                        existing,
                        teamId,
                        recipientIds.get(index),
                        title,
                        description,
                        priority,
                        dueAt
                );
                items.add(request(longValue(existing.get("id")), tenantId, requesterId, role));
            }
            return batchResult(items);
        }

        List<Long> requestIds = new ArrayList<>();
        try {
            for (int index = 0; index < recipientIds.size(); index++) {
                Long recipientId = recipientIds.get(index);
                Long requestId = insert("""
                    INSERT INTO collaboration_request(
                      tenant_id,team_id,requester_id,recipient_id,title,description,
                      priority,status,due_at,idempotency_key
                    ) VALUES (?,?,?,?,?,?,?,'PENDING',?,?)
                    """,
                        tenantId,
                        teamId,
                        requesterId,
                        recipientId,
                        title,
                        description,
                        priority,
                        dueAt,
                        derivedKeys.get(index)
                );
                requestIds.add(requestId);
            }
        } catch (DuplicateKeyException duplicate) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "协作申请正在处理中，请稍后重试",
                    duplicate
            );
        }

        for (int index = 0; index < requestIds.size(); index++) {
            eventPublisher.publishEvent(new CollaborationEvent(
                    tenantId,
                    requesterId,
                    recipientIds.get(index),
                    "COLLABORATION_REQUESTED",
                    requestIds.get(index),
                    teamId,
                    null,
                    title,
                    null
            ));
        }
        List<Map<String, Object>> items = requestIds.stream()
                .map(requestId -> request(requestId, tenantId, requesterId, role))
                .toList();
        return batchResult(items);
    }

    public Map<String, Object> request(Long requestId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = requestRow(requestId, tenantId, false);
        assertVisible(row, userId, role);
        decorate(row, userId);
        return row;
    }

    @Transactional
    public Map<String, Object> accept(Long requestId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = requestRow(requestId, tenantId, true);
        assertRecipient(row, userId);
        String status = text(row.get("status"));
        if ("ACCEPTED".equals(status)) {
            decorate(row, userId);
            return row;
        }
        if (!"PENDING".equals(status)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该协作申请已无法接受");
        }
        Long teamId = longValue(row.get("teamId"));
        Long requesterId = longValue(row.get("requesterId"));
        assertActiveMember(tenantId, teamId, requesterId);
        assertActiveMember(tenantId, teamId, userId);

        Map<String, Object> task = projectTeamService.createAcceptedCollaborationTask(
                teamId,
                requesterId,
                userId,
                String.valueOf(row.get("title")),
                optionalText(row.get("description"), 1000),
                text(row.get("priority")),
                row.get("dueAt")
        );
        Long taskId = longValue(task.get("id"));
        int updated = jdbc.update("""
            UPDATE collaboration_request
            SET status='ACCEPTED',linked_task_id=?,responded_at=CURRENT_TIMESTAMP
            WHERE id=? AND tenant_id=? AND status='PENDING'
            """, taskId, requestId, tenantId);
        if (updated != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "协作申请状态已变化，请刷新后重试");
        }
        eventPublisher.publishEvent(new CollaborationEvent(
                tenantId,
                userId,
                requesterId,
                "COLLABORATION_ACCEPTED",
                requestId,
                teamId,
                taskId,
                String.valueOf(row.get("title")),
                null
        ));
        return request(requestId, tenantId, userId, role);
    }

    @Transactional
    public Map<String, Object> decline(
            Long requestId,
            Long tenantId,
            Long userId,
            String role,
            Map<String, Object> body
    ) {
        Map<String, Object> row = requestRow(requestId, tenantId, true);
        assertRecipient(row, userId);
        if (!"PENDING".equals(text(row.get("status")))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该协作申请已处理");
        }
        String reason = optionalText(body == null ? null : body.get("reason"), 500);
        int updated = jdbc.update("""
            UPDATE collaboration_request
            SET status='DECLINED',response_reason=?,responded_at=CURRENT_TIMESTAMP
            WHERE id=? AND tenant_id=? AND status='PENDING'
            """, reason, requestId, tenantId);
        if (updated != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "协作申请状态已变化，请刷新后重试");
        }
        Long requesterId = longValue(row.get("requesterId"));
        eventPublisher.publishEvent(new CollaborationEvent(
                tenantId,
                userId,
                requesterId,
                "COLLABORATION_DECLINED",
                requestId,
                longValue(row.get("teamId")),
                null,
                String.valueOf(row.get("title")),
                reason
        ));
        return request(requestId, tenantId, userId, role);
    }

    @Transactional
    public Map<String, Object> withdraw(Long requestId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = requestRow(requestId, tenantId, true);
        if (!Objects.equals(longValue(row.get("requesterId")), userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有发起人可以撤回协作申请");
        }
        if (!"PENDING".equals(text(row.get("status")))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该协作申请已无法撤回");
        }
        int updated = jdbc.update("""
            UPDATE collaboration_request
            SET status='WITHDRAWN',withdrawn_at=CURRENT_TIMESTAMP
            WHERE id=? AND tenant_id=? AND status='PENDING'
            """, requestId, tenantId);
        if (updated != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "协作申请状态已变化，请刷新后重试");
        }
        eventPublisher.publishEvent(new CollaborationEvent(
                tenantId,
                userId,
                longValue(row.get("recipientId")),
                "COLLABORATION_WITHDRAWN",
                requestId,
                longValue(row.get("teamId")),
                null,
                String.valueOf(row.get("title")),
                null
        ));
        return request(requestId, tenantId, userId, role);
    }

    private List<Map<String, Object>> visibleRows(
            Long tenantId,
            Long userId,
            String role,
            Long teamId,
            Long cursor,
            int limit
    ) {
        String normalizedRole = role == null ? "" : role.toUpperCase(Locale.ROOT);
        List<Object> args = new ArrayList<>();
        StringBuilder where = new StringBuilder(" WHERE request.tenant_id=? ");
        args.add(tenantId);
        if (teamId != null) {
            where.append(" AND request.team_id=? ");
            args.add(teamId);
        }
        if (cursor != null) {
            where.append(" AND request.id<? ");
            args.add(cursor);
        }
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole)) {
            // tenant scope above is sufficient
        } else if ("TEACHER".equals(normalizedRole)) {
            where.append("""
                AND (
                  request.requester_id=? OR request.recipient_id=?
                  OR EXISTS (
                    SELECT 1 FROM project_team teacher_team
                    WHERE teacher_team.id=request.team_id
                      AND (teacher_team.mentor_id=? OR EXISTS (
                        SELECT 1 FROM project_team_member mentor
                        WHERE mentor.team_id=teacher_team.id
                          AND mentor.user_id=?
                          AND mentor.role_in_team='MENTOR'
                      ))
                  )
                )
                """);
            args.add(userId);
            args.add(userId);
            args.add(userId);
            args.add(userId);
        } else {
            where.append(" AND (request.requester_id=? OR request.recipient_id=?) ");
            args.add(userId);
            args.add(userId);
        }
        args.add(limit);
        return jdbc.queryForList(
                        requestSql(where + " ORDER BY request.created_at DESC,request.id DESC LIMIT ?"),
                        args.toArray()
                ).stream()
                .map(this::canonicalRow)
                .toList();
    }

    private Map<String, Object> requestRow(Long requestId, Long tenantId, boolean forUpdate) {
        String lock = forUpdate ? " FOR UPDATE" : "";
        List<Map<String, Object>> rows = jdbc.queryForList(
                requestSql(" WHERE request.id=? AND request.tenant_id=?" + lock),
                requestId,
                tenantId
        );
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "协作申请不存在");
        }
        return canonicalRow(rows.get(0));
    }

    private String requestSql(String suffix) {
        return """
            SELECT request.id,request.tenant_id tenantId,request.team_id teamId,
                   team.name teamName,request.requester_id requesterId,
                   requester.username requesterName,request.recipient_id recipientId,
                   recipient.username recipientName,request.title,request.description,
                   request.priority,request.status,request.due_at dueAt,
                   request.response_reason responseReason,request.linked_task_id linkedTaskId,
                   request.created_at createdAt,request.responded_at respondedAt,
                   request.withdrawn_at withdrawnAt,task.status linkedTaskStatus,
                   task.reviewer_user_id reviewerUserId,
                   (SELECT latest.id FROM project_task_submission latest
                    WHERE latest.task_id=request.linked_task_id
                    ORDER BY latest.version_no DESC,latest.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT latest.status FROM project_task_submission latest
                    WHERE latest.task_id=request.linked_task_id
                    ORDER BY latest.version_no DESC,latest.id DESC LIMIT 1) latestSubmissionStatus
            FROM collaboration_request request
            JOIN project_team team ON team.id=request.team_id
            JOIN users requester ON requester.id=request.requester_id
            JOIN users recipient ON recipient.id=request.recipient_id
            LEFT JOIN project_task task ON task.id=request.linked_task_id
            """ + suffix;
    }

    private Map<String, Object> canonicalRow(Map<String, Object> source) {
        Map<String, Object> row = new LinkedHashMap<>();
        source.forEach((key, value) -> row.put(canonicalKey(key), value));
        return row;
    }

    private String canonicalKey(String key) {
        return switch (key.toLowerCase(Locale.ROOT)) {
            case "tenantid" -> "tenantId";
            case "teamid" -> "teamId";
            case "teamname" -> "teamName";
            case "requesterid" -> "requesterId";
            case "requestername" -> "requesterName";
            case "recipientid" -> "recipientId";
            case "recipientname" -> "recipientName";
            case "dueat" -> "dueAt";
            case "responsereason" -> "responseReason";
            case "linkedtaskid" -> "linkedTaskId";
            case "createdat" -> "createdAt";
            case "respondedat" -> "respondedAt";
            case "withdrawnat" -> "withdrawnAt";
            case "linkedtaskstatus" -> "linkedTaskStatus";
            case "revieweruserid" -> "reviewerUserId";
            case "latestsubmissionid" -> "latestSubmissionId";
            case "latestsubmissionstatus" -> "latestSubmissionStatus";
            default -> key.toLowerCase(Locale.ROOT);
        };
    }

    private boolean matchesView(Map<String, Object> row, Long userId, String view) {
        return switch (view) {
            case "ACTION_REQUIRED" -> requiresAction(row, userId);
            case "IN_PROGRESS" -> isInProgress(row);
            case "CREATED_BY_ME" -> Objects.equals(longValue(row.get("requesterId")), userId);
            case "COMPLETED" -> TERMINAL_STATUSES.contains(text(row.get("status")))
                    || "DONE".equals(text(row.get("linkedTaskStatus")));
            case "ALL" -> true;
            default -> requiresAction(row, userId);
        };
    }

    private boolean requiresAction(Map<String, Object> row, Long userId) {
        if ("PENDING".equals(text(row.get("status")))
                && Objects.equals(longValue(row.get("recipientId")), userId)) {
            return true;
        }
        return Objects.equals(longValue(row.get("reviewerUserId")), userId)
                && Set.of("PENDING_REVIEW", "REVIEWING")
                .contains(text(row.get("latestSubmissionStatus")));
    }

    private boolean isInProgress(Map<String, Object> row) {
        String status = text(row.get("status"));
        String taskStatus = text(row.get("linkedTaskStatus"));
        return "ACCEPTED".equals(status) && !Set.of("DONE", "CANCELLED").contains(taskStatus);
    }

    private void decorate(Map<String, Object> row, Long userId) {
        row.put("actionRequired", requiresAction(row, userId));
        row.put("requesterIsCurrentUser", Objects.equals(longValue(row.get("requesterId")), userId));
        row.put("recipientIsCurrentUser", Objects.equals(longValue(row.get("recipientId")), userId));
        row.put("canAccept", "PENDING".equals(text(row.get("status")))
                && Objects.equals(longValue(row.get("recipientId")), userId));
        row.put("canDecline", row.get("canAccept"));
        row.put("canWithdraw", "PENDING".equals(text(row.get("status")))
                && Objects.equals(longValue(row.get("requesterId")), userId));
        row.put("kind", row.get("linkedTaskId") == null ? "REQUEST" : "TASK");
    }

    private void assertVisible(Map<String, Object> row, Long userId, String role) {
        if (Objects.equals(longValue(row.get("requesterId")), userId)
                || Objects.equals(longValue(row.get("recipientId")), userId)) {
            return;
        }
        String normalizedRole = role == null ? "" : role.toUpperCase(Locale.ROOT);
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole)) return;
        if ("TEACHER".equals(normalizedRole) && isMentor(longValue(row.get("teamId")), userId)) return;
        throw new ResponseStatusException(HttpStatus.NOT_FOUND, "协作申请不存在");
    }

    private void assertRecipient(Map<String, Object> row, Long userId) {
        if (!Objects.equals(longValue(row.get("recipientId")), userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有接收人可以处理协作申请");
        }
    }

    private void assertActiveMember(Long tenantId, Long teamId, Long userId) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*)
            FROM project_team team
            JOIN project_team_member member ON member.team_id=team.id
            WHERE team.id=? AND team.tenant_id=? AND team.status='ACTIVE' AND member.user_id=?
            """, Integer.class, teamId, tenantId, userId);
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "协作双方必须是同一有效团队成员");
        }
    }

    private boolean isMentor(Long teamId, Long userId) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*) FROM project_team team
            WHERE team.id=? AND (
              team.mentor_id=? OR EXISTS (
                SELECT 1 FROM project_team_member member
                WHERE member.team_id=team.id AND member.user_id=? AND member.role_in_team='MENTOR'
              )
            )
            """, Integer.class, teamId, userId, userId);
        return count != null && count > 0;
    }

    private List<Long> recipientIds(Object value) {
        if (!(value instanceof List<?> values)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择协作成员");
        }
        LinkedHashSet<Long> recipients = new LinkedHashSet<>();
        for (Object candidate : values) {
            Long recipientId = longValue(candidate);
            if (recipientId == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "协作成员信息不正确");
            }
            recipients.add(recipientId);
        }
        if (recipients.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择协作成员");
        }
        if (recipients.size() > 50) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "一次最多邀请 50 名成员");
        }
        return List.copyOf(recipients);
    }

    private String batchIdempotencyKey(String batchKey, Long recipientId) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(
                    (batchKey + ":" + recipientId).getBytes(StandardCharsets.UTF_8)
            );
            return "batch:" + HexFormat.of().formatHex(hash);
        } catch (RuntimeException | java.security.NoSuchAlgorithmException error) {
            throw new IllegalStateException("无法生成协作请求标识", error);
        }
    }

    private List<Map<String, Object>> batchRows(
            Long tenantId,
            Long requesterId,
            String idempotencyKey
    ) {
        return jdbc.queryForList("""
            SELECT id,team_id teamId,recipient_id recipientId,title,description,
                   priority,due_at dueAt
            FROM collaboration_request
            WHERE tenant_id=? AND requester_id=? AND idempotency_key=?
            """, tenantId, requesterId, idempotencyKey).stream()
                .map(this::canonicalRow)
                .toList();
    }

    private void assertSameBatchRequest(
            Map<String, Object> existing,
            Long teamId,
            Long recipientId,
            String title,
            String description,
            String priority,
            LocalDateTime dueAt
    ) {
        boolean same = Objects.equals(longValue(existing.get("teamId")), teamId)
                && Objects.equals(longValue(existing.get("recipientId")), recipientId)
                && Objects.equals(text(existing.get("title")), title)
                && Objects.equals(text(existing.get("description")), description)
                && Objects.equals(text(existing.get("priority")), priority)
                && Objects.equals(localDateTime(existing.get("dueAt")), dueAt);
        if (!same) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT,
                    "本次提交内容已发生变化，请重新发送"
            );
        }
    }

    private LocalDateTime localDateTime(Object value) {
        if (value == null) return null;
        if (value instanceof LocalDateTime localDateTime) return localDateTime;
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime();
        return parseDateTime(value);
    }

    private Map<String, Object> batchResult(List<Map<String, Object>> items) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("count", items.size());
        result.put("items", items);
        return result;
    }

    private Long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        int inserted = jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int index = 0; index < args.length; index++) {
                statement.setObject(index + 1, args[index]);
            }
            return statement;
        }, keyHolder);
        Number key = generatedKey(keyHolder);
        if (inserted != 1 || key == null) {
            throw new IllegalStateException("协作数据保存失败");
        }
        return key.longValue();
    }

    private Number generatedKey(KeyHolder keyHolder) {
        if (keyHolder.getKeyList().isEmpty()) return null;
        Map<String, Object> keys = keyHolder.getKeyList().get(0);
        for (String candidate : List.of("GENERATED_KEY", "id", "ID")) {
            Object value = keys.get(candidate);
            if (value instanceof Number number) return number;
        }
        return keys.values().stream()
                .filter(Number.class::isInstance)
                .map(Number.class::cast)
                .findFirst()
                .orElse(null);
    }

    private String normalizePriority(Object value) {
        String priority = text(value);
        if (priority == null) return "MEDIUM";
        priority = priority.toUpperCase(Locale.ROOT);
        if (!PRIORITIES.contains(priority)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "不支持的任务优先级");
        }
        return priority;
    }

    private LocalDateTime parseDateTime(Object value) {
        String text = text(value);
        if (text == null) return null;
        try {
            return LocalDateTime.parse(text.replace(" ", "T"));
        } catch (RuntimeException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "截止时间格式不正确");
        }
    }

    private Long requiredLong(Object value, String message) {
        Long result = longValue(value);
        if (result == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
        return result;
    }

    private String requiredText(Object value, String message, int maxLength) {
        String result = optionalText(value, maxLength);
        if (result == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
        return result;
    }

    private String optionalText(Object value, int maxLength) {
        String result = text(value);
        if (result == null) return null;
        if (result.length() > maxLength) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "输入内容过长");
        }
        return result;
    }

    private Object firstNonBlank(Object first, Object second) {
        return text(first) == null ? second : first;
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String text(Object value) {
        if (value == null) return null;
        String result = String.valueOf(value).trim();
        return result.isEmpty() ? null : result;
    }
}
