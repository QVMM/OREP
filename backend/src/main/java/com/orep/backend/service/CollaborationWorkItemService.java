package com.orep.backend.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
public class CollaborationWorkItemService {
    private static final ZoneId SHANGHAI_ZONE = ZoneId.of("Asia/Shanghai");
    private static final Set<String> REQUEST_TERMINAL = Set.of("DECLINED", "WITHDRAWN", "COMPLETED");
    private static final Set<String> TASK_TERMINAL = Set.of("DONE", "CANCELLED");
    private static final Set<String> REVIEW_PENDING = Set.of("PENDING_REVIEW", "REVIEWING");

    private final JdbcTemplate jdbc;
    private final TrainingDayAvailabilityService trainingDayAvailabilityService;

    public CollaborationWorkItemService(
            JdbcTemplate jdbc,
            TrainingDayAvailabilityService trainingDayAvailabilityService
    ) {
        this.jdbc = jdbc;
        this.trainingDayAvailabilityService = trainingDayAvailabilityService;
    }

    public Map<String, Object> summary(Long tenantId, Long userId, String role) {
        List<Map<String, Object>> rows = visibleWorkItems(tenantId, userId, role, null);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("actionRequired", count(rows, item -> bool(item.get("actionRequired"))));
        result.put("inProgress", count(rows, this::isInProgress));
        result.put("createdByMe", count(rows, item -> bool(item.get("createdByCurrentUser"))));
        result.put("completed", count(rows, this::isTerminal));
        result.put("total", rows.size());
        return result;
    }

    public Map<String, Object> items(
            Long tenantId,
            Long userId,
            String role,
            String view,
            Long teamId,
            String cursor,
            Integer requestedLimit
    ) {
        String normalizedView = normalizeView(view);
        int limit = Math.max(1, Math.min(requestedLimit == null ? 30 : requestedLimit, 50));
        List<Map<String, Object>> filtered = visibleWorkItems(tenantId, userId, role, teamId).stream()
                .filter(item -> matchesView(item, normalizedView))
                .sorted(comparator(normalizedView))
                .toList();

        int start = cursorStart(filtered, cursor);
        int end = Math.min(filtered.size(), start + limit);
        List<Map<String, Object>> page = new ArrayList<>(filtered.subList(start, end));
        boolean hasMore = end < filtered.size();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("items", page);
        result.put("nextCursor", hasMore && !page.isEmpty() ? encodeCursor(page.get(page.size() - 1)) : null);
        result.put("hasMore", hasMore);
        result.put("view", normalizedView);
        return result;
    }

    private List<Map<String, Object>> visibleWorkItems(
            Long tenantId,
            Long userId,
            String role,
            Long teamId
    ) {
        List<Map<String, Object>> tasks = visibleTasks(tenantId, userId, role, teamId);
        Set<Long> linkedTaskIds = new LinkedHashSet<>();
        for (Map<String, Object> task : tasks) {
            Long taskId = longValue(task.get("id"));
            if (taskId != null) linkedTaskIds.add(taskId);
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> request : visibleRequests(tenantId, userId, role, teamId)) {
            Long linkedTaskId = longValue(request.get("linkedTaskId"));
            if (linkedTaskId != null && linkedTaskIds.contains(linkedTaskId)) continue;
            result.add(decorateRequest(request, userId));
        }
        result.addAll(tasks);
        return result;
    }

    private List<Map<String, Object>> visibleRequests(
            Long tenantId,
            Long userId,
            String role,
            Long teamId
    ) {
        String normalizedRole = normalizeRole(role);
        List<Object> args = new ArrayList<>();
        StringBuilder where = new StringBuilder(" WHERE request.tenant_id=? ");
        args.add(tenantId);
        if (teamId != null) {
            where.append(" AND request.team_id=? ");
            args.add(teamId);
        }
        if (isAdmin(normalizedRole)) {
            // Tenant scope is sufficient.
        } else if ("TEACHER".equals(normalizedRole)) {
            where.append("""
                AND (
                  request.requester_id=? OR request.recipient_id=?
                  OR team.mentor_id=?
                  OR EXISTS (
                    SELECT 1 FROM project_team_member mentor
                    WHERE mentor.team_id=team.id
                      AND mentor.user_id=?
                      AND mentor.role_in_team='MENTOR'
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

        String sql = """
            SELECT request.id,request.team_id teamId,team.name teamName,
                   request.requester_id requesterId,requester.username requesterName,
                   request.recipient_id recipientId,recipient.username recipientName,
                   request.title,request.description,request.priority,request.status,
                   request.due_at dueAt,request.linked_task_id linkedTaskId,
                   request.created_at createdAt,request.updated_at updatedAt
            FROM collaboration_request request
            JOIN project_team team ON team.id=request.team_id
            JOIN users requester ON requester.id=request.requester_id
            JOIN users recipient ON recipient.id=request.recipient_id
            """ + where;
        return canonicalRows(jdbc.queryForList(sql, args.toArray()));
    }

    private List<Map<String, Object>> visibleTasks(
            Long tenantId,
            Long userId,
            String role,
            Long teamId
    ) {
        String normalizedRole = normalizeRole(role);
        List<Object> args = new ArrayList<>();
        StringBuilder where = new StringBuilder("""
            WHERE team.tenant_id=?
              AND COALESCE(team.status,'ACTIVE')<>'ARCHIVED'
            """);
        args.add(tenantId);
        if (teamId != null) {
            where.append(" AND task.team_id=? ");
            args.add(teamId);
        }
        if (isAdmin(normalizedRole)) {
            // Tenant scope is sufficient.
        } else if ("TEACHER".equals(normalizedRole)) {
            where.append("""
                AND (
                  team.mentor_id=?
                  OR EXISTS (
                    SELECT 1 FROM project_team_member mentor
                    WHERE mentor.team_id=team.id
                      AND mentor.user_id=?
                      AND mentor.role_in_team='MENTOR'
                  )
                )
                """);
            args.add(userId);
            args.add(userId);
        } else {
            where.append("""
                AND EXISTS (
                  SELECT 1 FROM project_team_member member
                  WHERE member.team_id=team.id AND member.user_id=?
                )
                AND (
                  task.owner_user_id=?
                  OR task.created_by=?
                  OR task.reviewer_user_id=?
                  OR EXISTS (
                    SELECT 1 FROM project_task_assignee assigned
                    WHERE assigned.task_id=task.id AND assigned.user_id=?
                  )
                )
                """);
            args.add(userId);
            args.add(userId);
            args.add(userId);
            args.add(userId);
            args.add(userId);
        }

        String sql = """
            SELECT task.id,task.team_id teamId,team.name teamName,
                   task.title,task.description,task.owner_user_id ownerUserId,
                   owner.username ownerName,task.created_by createdBy,
                   creator.username creatorName,task.source_type sourceType,
                   task.reviewer_user_id reviewerUserId,task.priority,task.status,
                   task.due_at dueAt,task.created_at createdAt,task.updated_at updatedAt,
                   request_row.id collaborationRequestId,request_row.requester_id requesterId,
                   requester.username requesterName,request_row.recipient_id recipientId,
                   recipient.username recipientName,
                   (SELECT training_day_row.id
                    FROM training_day_task link
                    JOIN training_day training_day_row ON training_day_row.id=link.training_day_id
                    WHERE link.task_id=task.id
                    ORDER BY training_day_row.id DESC LIMIT 1) trainingDayId,
                   (SELECT training_day_row.day_no
                    FROM training_day_task link
                    JOIN training_day training_day_row ON training_day_row.id=link.training_day_id
                    WHERE link.task_id=task.id
                    ORDER BY training_day_row.id DESC LIMIT 1) trainingDayNo,
                   (SELECT training_day_row.status
                    FROM training_day_task link
                    JOIN training_day training_day_row ON training_day_row.id=link.training_day_id
                    WHERE link.task_id=task.id
                    ORDER BY training_day_row.id DESC LIMIT 1) trainingDayStatus,
                   (SELECT training_day_row.training_date
                    FROM training_day_task link
                    JOIN training_day training_day_row ON training_day_row.id=link.training_day_id
                    WHERE link.task_id=task.id
                    ORDER BY training_day_row.id DESC LIMIT 1) trainingDate,
                   (SELECT training_day_row.early_unlocked_at
                    FROM training_day_task link
                    JOIN training_day training_day_row ON training_day_row.id=link.training_day_id
                    WHERE link.task_id=task.id
                    ORDER BY training_day_row.id DESC LIMIT 1) earlyUnlockedAt,
                   (SELECT submission.id
                    FROM project_task_submission submission
                    WHERE submission.task_id=task.id
                    ORDER BY submission.version_no DESC,submission.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT submission.status
                    FROM project_task_submission submission
                    WHERE submission.task_id=task.id
                    ORDER BY submission.version_no DESC,submission.id DESC LIMIT 1) latestSubmissionStatus,
                   (SELECT submission.submitter_id
                    FROM project_task_submission submission
                    WHERE submission.task_id=task.id
                    ORDER BY submission.version_no DESC,submission.id DESC LIMIT 1) latestSubmitterId,
                   (SELECT submitter.username
                    FROM project_task_submission submission
                    JOIN users submitter ON submitter.id=submission.submitter_id
                    WHERE submission.task_id=task.id
                    ORDER BY submission.version_no DESC,submission.id DESC LIMIT 1) latestSubmitterName
            FROM project_task task
            JOIN project_team team ON team.id=task.team_id
            LEFT JOIN users owner ON owner.id=task.owner_user_id
            LEFT JOIN users creator ON creator.id=task.created_by
            LEFT JOIN collaboration_request request_row ON request_row.linked_task_id=task.id
            LEFT JOIN users requester ON requester.id=request_row.requester_id
            LEFT JOIN users recipient ON recipient.id=request_row.recipient_id
            """ + where;

        List<Map<String, Object>> rows = canonicalRows(jdbc.queryForList(sql, args.toArray()));
        attachAssignees(rows);
        List<Map<String, Object>> visible = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            if ("STUDENT".equals(normalizedRole) && trainingLocked(row)) continue;
            visible.add(decorateTask(row, userId, normalizedRole));
        }
        return visible;
    }

    private void attachAssignees(List<Map<String, Object>> tasks) {
        List<Long> taskIds = tasks.stream()
                .map(task -> longValue(task.get("id")))
                .filter(Objects::nonNull)
                .toList();
        if (taskIds.isEmpty()) return;
        String placeholders = String.join(",", taskIds.stream().map(ignored -> "?").toList());
        List<Map<String, Object>> rows = canonicalRows(jdbc.queryForList(("""
            SELECT assigned.task_id taskId,assigned.user_id userId,
                   assignee.username,member.role_in_team roleInTeam
            FROM project_task_assignee assigned
            JOIN users assignee ON assignee.id=assigned.user_id
            LEFT JOIN project_team_member member
              ON member.team_id=assigned.team_id AND member.user_id=assigned.user_id
            WHERE assigned.task_id IN (%s)
            ORDER BY assigned.task_id,assigned.sort_order,assigned.id
            """).formatted(placeholders), taskIds.toArray()));
        Map<Long, List<Map<String, Object>>> byTask = new HashMap<>();
        for (Map<String, Object> row : rows) {
            Long taskId = longValue(row.get("taskId"));
            byTask.computeIfAbsent(taskId, ignored -> new ArrayList<>()).add(row);
        }
        for (Map<String, Object> task : tasks) {
            task.put("assignees", byTask.getOrDefault(longValue(task.get("id")), List.of()));
        }
    }

    private boolean trainingLocked(Map<String, Object> task) {
        if (task.get("trainingDayId") == null) return false;
        Map<String, Object> availability = trainingDayAvailabilityService.availability(
                text(task.get("trainingDayStatus")),
                task.get("trainingDate"),
                task.get("earlyUnlockedAt")
        );
        return bool(availability.get("locked"));
    }

    private Map<String, Object> decorateRequest(Map<String, Object> source, Long userId) {
        Map<String, Object> item = new LinkedHashMap<>(source);
        String status = upper(source.get("status"));
        boolean requesterIsCurrent = Objects.equals(longValue(source.get("requesterId")), userId);
        boolean recipientIsCurrent = Objects.equals(longValue(source.get("recipientId")), userId);
        boolean pending = "PENDING".equals(status);

        item.put("key", "REQUEST:" + source.get("id"));
        item.put("entityType", "REQUEST");
        item.put("sourceType", "PEER_COLLABORATION");
        item.put("sourceLabel", "学生协作");
        item.put("status", status);
        item.put("statusLabel", switch (status) {
            case "PENDING" -> recipientIsCurrent ? "待接受" : "等待回应";
            case "DECLINED" -> "已婉拒";
            case "WITHDRAWN" -> "已撤回";
            case "COMPLETED" -> "已完成";
            default -> "协作申请";
        });
        item.put("requesterIsCurrentUser", requesterIsCurrent);
        item.put("recipientIsCurrentUser", recipientIsCurrent);
        item.put("canAccept", pending && recipientIsCurrent);
        item.put("canDecline", pending && recipientIsCurrent);
        item.put("canWithdraw", pending && requesterIsCurrent);
        item.put("actionRequired", pending && recipientIsCurrent);
        item.put("createdByCurrentUser", requesterIsCurrent);
        item.put("primaryAction", pending && recipientIsCurrent ? "ACCEPT" : "OPEN");
        item.put("targetPath", null);
        return item;
    }

    private Map<String, Object> decorateTask(
            Map<String, Object> source,
            Long userId,
            String role
    ) {
        Map<String, Object> item = new LinkedHashMap<>(source);
        Long taskId = longValue(source.get("id"));
        String status = upper(source.get("status"));
        String latestSubmissionStatus = upper(source.get("latestSubmissionStatus"));
        boolean assigned = isAssigned(source.get("assignees"), userId)
                || Objects.equals(longValue(source.get("ownerUserId")), userId);
        boolean designatedReviewer = Objects.equals(longValue(source.get("reviewerUserId")), userId);
        boolean teacherReviewer = "TEACHER".equals(role);
        boolean canReview = REVIEW_PENDING.contains(latestSubmissionStatus)
                && (designatedReviewer || teacherReviewer || isAdmin(role));
        boolean needsRevision = "CHANGES_REQUESTED".equals(latestSubmissionStatus)
                && (assigned || Objects.equals(longValue(source.get("latestSubmitterId")), userId));
        boolean canSubmit = assigned
                && !TASK_TERMINAL.contains(status)
                && !"REVIEWING".equals(status)
                && !REVIEW_PENDING.contains(latestSubmissionStatus);
        boolean actionRequired = canReview || needsRevision || canSubmit;
        boolean createdByCurrent = Objects.equals(longValue(source.get("createdBy")), userId);
        String sourceType = sourceType(source);
        Long trainingDayId = longValue(source.get("trainingDayId"));

        item.put("key", "TASK:" + taskId);
        item.put("entityType", "TASK");
        item.put("linkedTaskId", taskId);
        item.put("sourceType", sourceType);
        item.put("sourceLabel", sourceLabel(sourceType));
        item.put("status", status);
        item.put("statusLabel", taskStatusLabel(status, latestSubmissionStatus, canReview, needsRevision));
        item.put("actionRequired", actionRequired);
        item.put("createdByCurrentUser", createdByCurrent);
        item.put("currentUserCanSubmit", canSubmit);
        item.put("canAccept", false);
        item.put("canDecline", false);
        item.put("canWithdraw", false);
        item.put("primaryAction", canReview ? "REVIEW" : canSubmit ? "SUBMIT" : "OPEN");
        item.put("targetPath", trainingDayId == null
                ? "/project-team/details/task-" + taskId
                : "/training/tasks/" + taskId + "?dayId=" + trainingDayId);
        return item;
    }

    private String sourceType(Map<String, Object> task) {
        if (task.get("trainingDayId") != null) return "TRAINING_DAY";
        return switch (upper(task.get("sourceType"))) {
            case "TEACHER_ASSIGNMENT" -> "TEACHER_ASSIGNMENT";
            case "PEER_COLLABORATION" -> "PEER_COLLABORATION";
            default -> "TEAM_TASK";
        };
    }

    private String sourceLabel(String sourceType) {
        return switch (sourceType) {
            case "TRAINING_DAY" -> "今日训练";
            case "TEACHER_ASSIGNMENT" -> "老师任务";
            case "PEER_COLLABORATION" -> "学生协作";
            default -> "团队任务";
        };
    }

    private String taskStatusLabel(
            String status,
            String latestSubmissionStatus,
            boolean canReview,
            boolean needsRevision
    ) {
        if (canReview) return "待审核";
        if (needsRevision) return "待修改";
        if (REVIEW_PENDING.contains(latestSubmissionStatus) || "REVIEWING".equals(status)) return "待审核";
        return switch (status) {
            case "TODO" -> "待开始";
            case "IN_PROGRESS", "CHANGES_REQUESTED" -> "进行中";
            case "DONE" -> "已完成";
            case "CANCELLED" -> "已取消";
            default -> "任务";
        };
    }

    private boolean isAssigned(Object value, Long userId) {
        if (!(value instanceof Collection<?> assignees)) return false;
        return assignees.stream().anyMatch(assignee ->
                assignee instanceof Map<?, ?> row
                        && Objects.equals(longValue(row.get("userId")), userId));
    }

    private boolean matchesView(Map<String, Object> item, String view) {
        return switch (view) {
            case "ACTION_REQUIRED" -> bool(item.get("actionRequired"));
            case "IN_PROGRESS" -> isInProgress(item);
            case "CREATED_BY_ME" -> bool(item.get("createdByCurrentUser"));
            case "ALL" -> true;
            default -> false;
        };
    }

    private boolean isInProgress(Map<String, Object> item) {
        String entityType = upper(item.get("entityType"));
        String status = upper(item.get("status"));
        if ("REQUEST".equals(entityType)) return "ACCEPTED".equals(status);
        return Set.of("IN_PROGRESS", "REVIEWING", "CHANGES_REQUESTED").contains(status);
    }

    private boolean isTerminal(Map<String, Object> item) {
        String status = upper(item.get("status"));
        return "REQUEST".equals(upper(item.get("entityType")))
                ? REQUEST_TERMINAL.contains(status)
                : TASK_TERMINAL.contains(status);
    }

    private Comparator<Map<String, Object>> comparator(String view) {
        Comparator<Map<String, Object>> byKey = Comparator.comparing(item -> text(item.get("key")));
        Comparator<Map<String, Object>> updatedDesc = Comparator
                .comparing(this::updatedAt, Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparing(byKey);
        if ("ACTION_REQUIRED".equals(view)) {
            return Comparator
                    .comparing((Map<String, Object> item) -> !isOverdue(item))
                    .thenComparing(this::dueAt, Comparator.nullsLast(Comparator.naturalOrder()))
                    .thenComparing(updatedDesc);
        }
        if ("IN_PROGRESS".equals(view)) {
            return Comparator
                    .comparing(this::dueAt, Comparator.nullsLast(Comparator.naturalOrder()))
                    .thenComparing(updatedDesc);
        }
        if ("ALL".equals(view)) {
            return Comparator
                    .comparing(this::isTerminal)
                    .thenComparing(updatedDesc);
        }
        return updatedDesc;
    }

    private boolean isOverdue(Map<String, Object> item) {
        LocalDateTime dueAt = dueAt(item);
        return dueAt != null && !isTerminal(item)
                && dueAt.isBefore(LocalDateTime.now(SHANGHAI_ZONE));
    }

    private LocalDateTime dueAt(Map<String, Object> item) {
        return dateTime(item.get("dueAt"));
    }

    private LocalDateTime updatedAt(Map<String, Object> item) {
        LocalDateTime updated = dateTime(item.get("updatedAt"));
        return updated == null ? dateTime(item.get("createdAt")) : updated;
    }

    private int cursorStart(List<Map<String, Object>> items, String cursor) {
        String key = decodeCursorKey(cursor);
        if (key == null) return 0;
        for (int index = 0; index < items.size(); index++) {
            if (key.equals(text(items.get(index).get("key")))) return index + 1;
        }
        return 0;
    }

    private String encodeCursor(Map<String, Object> item) {
        String raw = text(item.get("key")) + "\n" + text(item.get("updatedAt"));
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    private String decodeCursorKey(String cursor) {
        if (cursor == null || cursor.isBlank()) return null;
        try {
            String decoded = new String(
                    Base64.getUrlDecoder().decode(cursor),
                    StandardCharsets.UTF_8
            );
            int separator = decoded.indexOf('\n');
            return separator < 0 ? decoded : decoded.substring(0, separator);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private String normalizeView(String view) {
        String normalized = upper(view);
        return Set.of("ACTION_REQUIRED", "IN_PROGRESS", "CREATED_BY_ME", "ALL")
                .contains(normalized) ? normalized : "ACTION_REQUIRED";
    }

    private String normalizeRole(String role) {
        return role == null ? "" : role.trim().toUpperCase(Locale.ROOT);
    }

    private boolean isAdmin(String role) {
        return Set.of("ADMIN", "SCHOOL_ADMIN").contains(role);
    }

    private int count(
            List<Map<String, Object>> items,
            java.util.function.Predicate<Map<String, Object>> predicate
    ) {
        return (int) items.stream().filter(predicate).count();
    }

    private List<Map<String, Object>> canonicalRows(List<Map<String, Object>> rows) {
        return rows.stream().map(this::canonicalRow).toList();
    }

    private Map<String, Object> canonicalRow(Map<String, Object> source) {
        Map<String, Object> row = new LinkedHashMap<>();
        source.forEach((key, value) -> row.put(canonicalKey(key), value));
        return row;
    }

    private String canonicalKey(String key) {
        return switch (key.toLowerCase(Locale.ROOT)) {
            case "teamid" -> "teamId";
            case "teamname" -> "teamName";
            case "requesterid" -> "requesterId";
            case "requestername" -> "requesterName";
            case "recipientid" -> "recipientId";
            case "recipientname" -> "recipientName";
            case "owneruserid" -> "ownerUserId";
            case "ownername" -> "ownerName";
            case "createdby" -> "createdBy";
            case "creatorname" -> "creatorName";
            case "sourcetype" -> "sourceType";
            case "revieweruserid" -> "reviewerUserId";
            case "dueat" -> "dueAt";
            case "createdat" -> "createdAt";
            case "updatedat" -> "updatedAt";
            case "linkedtaskid" -> "linkedTaskId";
            case "collaborationrequestid" -> "collaborationRequestId";
            case "trainingdayid" -> "trainingDayId";
            case "trainingdayno" -> "trainingDayNo";
            case "trainingdaystatus" -> "trainingDayStatus";
            case "trainingdate" -> "trainingDate";
            case "earlyunlockedat" -> "earlyUnlockedAt";
            case "latestsubmissionid" -> "latestSubmissionId";
            case "latestsubmissionstatus" -> "latestSubmissionStatus";
            case "latestsubmitterid" -> "latestSubmitterId";
            case "latestsubmittername" -> "latestSubmitterName";
            case "taskid" -> "taskId";
            case "userid" -> "userId";
            case "roleinteam" -> "roleInTeam";
            default -> key.toLowerCase(Locale.ROOT);
        };
    }

    private String upper(Object value) {
        return value == null ? "" : String.valueOf(value).trim().toUpperCase(Locale.ROOT);
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private boolean bool(Object value) {
        if (value instanceof Boolean bool) return bool;
        if (value instanceof Number number) return number.intValue() != 0;
        return value != null && Boolean.parseBoolean(String.valueOf(value));
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        if (value == null) return null;
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private LocalDateTime dateTime(Object value) {
        if (value instanceof LocalDateTime dateTime) return dateTime;
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime();
        if (value == null) return null;
        try {
            return LocalDateTime.parse(String.valueOf(value).replace(' ', 'T'));
        } catch (RuntimeException ignored) {
            return null;
        }
    }
}
