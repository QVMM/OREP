package com.orep.backend.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class StudentTrainingService {
    private final JdbcTemplate jdbc;
    private final TrainingDayContentService contentService;
    private final TrainingDayLearningResourceService learningService;
    private final TrainingDayAvailabilityService availabilityService;
    private final ProjectTeamService projectTeamService;

    @Autowired
    public StudentTrainingService(
            JdbcTemplate jdbc,
            TrainingDayContentService contentService,
            TrainingDayLearningResourceService learningService,
            TrainingDayAvailabilityService availabilityService,
            ProjectTeamService projectTeamService
    ) {
        this.jdbc = jdbc;
        this.contentService = contentService;
        this.learningService = learningService;
        this.availabilityService = availabilityService;
        this.projectTeamService = projectTeamService;
    }

    public Map<String, Object> current(Long tenantId, Long userId) {
        Map<String, Object> camp = currentCamp(tenantId, userId);
        if (camp.isEmpty()) {
            return Map.of(
                    "hasCamp", false,
                    "message", "当前还没有为你的团队安排集训营"
            );
        }
        Map<String, Object> result = new LinkedHashMap<>(camp);
        result.put("hasCamp", true);
        return result;
    }

    public Map<String, Object> today(Long tenantId, Long userId) {
        Map<String, Object> camp = currentCamp(tenantId, userId);
        if (camp.isEmpty()) {
            return Map.of(
                    "hasCamp", false,
                    "hasTrainingDay", false,
                    "message", "当前还没有为你的团队安排集训营"
            );
        }
        LocalDate now = availabilityService.today();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT d.id dayId, d.day_no dayNo, d.training_date trainingDate, d.title,
                   d.summary, d.content_html contentHtml, d.due_at dueAt, d.status,
                   d.early_unlocked_at earlyUnlockedAt,
                   w.week_no weekNo, w.title weekTitle, w.start_date weekStartDate, w.end_date weekEndDate
            FROM training_day d
            LEFT JOIN training_camp_week w ON w.id = d.week_id
            WHERE d.camp_id = ? AND d.training_date = ? AND d.status <> 'DRAFT'
            LIMIT 1
            """, camp.get("campId"), now);
        if (rows.isEmpty()) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("hasCamp", true);
            result.put("hasTrainingDay", false);
            result.put("camp", camp);
            result.put("message", "今天暂未安排集训任务");
            result.put("nextDay", nextTrainingDay(camp.get("campId"), now));
            return result;
        }
        Map<String, Object> day = new LinkedHashMap<>(rows.get(0));
        day.putAll(availabilityService.availability(day));
        Map<String, Object> result = dayPayload(day, camp, tenantId, userId);
        result.put("hasCamp", true);
        result.put("hasTrainingDay", true);
        return result;
    }

    public Map<String, Object> todayOverview(Long tenantId, Long userId) {
        return overviewPayload(tenantId, userId, today(tenantId, userId));
    }

    public Map<String, Object> plan(Long tenantId, Long userId) {
        Map<String, Object> camp = currentCamp(tenantId, userId);
        if (camp.isEmpty()) {
            return Map.of(
                    "hasCamp", false,
                    "weeks", List.of(),
                    "message", "当前还没有为你的团队安排集训营"
            );
        }

        List<Map<String, Object>> weeks = jdbc.queryForList("""
            SELECT id weekId, week_no weekNo, title, start_date startDate, end_date endDate
            FROM training_camp_week
            WHERE camp_id = ?
            ORDER BY sort_order ASC, week_no ASC
            """, camp.get("campId"));

        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT d.id dayId, d.week_id weekId, d.day_no dayNo, d.training_date trainingDate,
                   d.title, d.summary, d.due_at dueAt, d.status,
                   d.early_unlocked_at earlyUnlockedAt,
                   CASE
                     WHEN EXISTS (
                       SELECT 1
                       FROM training_day_task dt
                       JOIN project_task_submission s ON s.task_id = dt.task_id
                       WHERE dt.training_day_id = d.id AND s.submitter_id = ?
                         AND s.status IN ('APPROVED', 'PENDING_REVIEW', 'REVIEWING')
                     ) THEN 1
                     ELSE 0
                   END submitted
            FROM training_day d
            WHERE d.camp_id = ?
            ORDER BY d.sort_order ASC, d.day_no ASC
            """, userId, camp.get("campId"));

        List<Map<String, Object>> tasks = jdbc.queryForList("""
            SELECT d.id dayId, t.id taskId, t.title, t.description, t.priority, t.status,
                   COALESCE(t.due_at, d.due_at) dueAt,
                   dt.is_primary isPrimary, dt.sort_order sortOrder,
                   (SELECT COUNT(*) FROM project_task_requirement r WHERE r.task_id = t.id) requirementCount,
                   (SELECT s.id FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT s.status FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmissionStatus,
                   (SELECT s.created_at FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmittedAt
            FROM training_day d
            JOIN training_day_task dt ON dt.training_day_id = d.id
            JOIN project_task t ON t.id = dt.task_id
            WHERE d.camp_id = ? AND t.team_id = ?
            ORDER BY d.sort_order ASC, d.day_no ASC, dt.is_primary DESC, dt.sort_order ASC, t.id ASC
            """, userId, userId, userId, camp.get("campId"), camp.get("teamId"));

        LocalDate today = availabilityService.today();
        for (Map<String, Object> day : days) {
            day.putAll(availabilityService.availability(day));
            boolean submitted = intValue(day.remove("submitted"), 0) > 0;
            LocalDate trainingDate = localDate(day.get("trainingDate"));
            String progressStatus = submitted
                    ? "SUBMITTED"
                    : trainingDate == null || trainingDate.isAfter(today)
                    ? "UPCOMING"
                    : trainingDate.isBefore(today)
                    ? "EXPIRED"
                    : "TODAY";
            day.put("progressStatus", progressStatus);
        }
        Map<Long, List<Map<String, Object>>> tasksByDay = new LinkedHashMap<>();
        for (Map<String, Object> task : tasks) {
            Long dayId = longValue(task.get("dayId"));
            tasksByDay.computeIfAbsent(dayId, ignored -> new ArrayList<>()).add(task);
        }
        for (Map<String, Object> day : days) {
            List<Map<String, Object>> dayTasks = Boolean.TRUE.equals(day.get("locked"))
                    ? List.of()
                    : tasksByDay.getOrDefault(longValue(day.get("dayId")), List.of());
            day.put("tasks", dayTasks);
            day.put("taskCount", dayTasks.size());
        }
        Map<Long, Map<String, Object>> learningSummaries = learningService.summaries(
                days.stream()
                        .filter(day -> !Boolean.TRUE.equals(day.get("locked")))
                        .map(day -> longValue(day.get("dayId")))
                        .filter(Objects::nonNull)
                        .toList(),
                userId
        );
        for (Map<String, Object> day : days) {
            Map<String, Object> summary = Boolean.TRUE.equals(day.get("locked"))
                    ? Map.of()
                    : learningSummaries.getOrDefault(longValue(day.get("dayId")), Map.of());
            day.put("learningResourceCount", summary.getOrDefault("learningResourceCount", 0));
            day.put("requiredLearningCount", summary.getOrDefault("requiredLearningCount", 0));
            day.put("estimatedLearningMinutes", summary.getOrDefault("estimatedLearningMinutes", 0));
            day.put("completedLearningCount", summary.getOrDefault("completedLearningCount", 0));
            day.put("videoResourceCount", summary.getOrDefault("videoResourceCount", 0));
            day.put("documentResourceCount", summary.getOrDefault("documentResourceCount", 0));
            day.put("linkResourceCount", summary.getOrDefault("linkResourceCount", 0));
            day.put("learningPreview", summary.get("learningPreview"));
            availabilityService.redactDraftPlaceholder(day);
        }

        Map<Long, List<Map<String, Object>>> daysByWeek = new LinkedHashMap<>();
        for (Map<String, Object> day : days) {
            Long weekId = longValue(day.get("weekId"));
            daysByWeek.computeIfAbsent(weekId, ignored -> new ArrayList<>()).add(day);
        }
        List<Map<String, Object>> weekPayloads = new ArrayList<>();
        for (Map<String, Object> week : weeks) {
            Map<String, Object> item = new LinkedHashMap<>(week);
            item.put("days", daysByWeek.getOrDefault(longValue(week.get("weekId")), List.of()));
            weekPayloads.add(item);
        }
        List<Map<String, Object>> ungroupedDays = daysByWeek.getOrDefault(null, List.of());
        if (weeks.isEmpty() && !days.isEmpty()) {
            Map<String, Object> fallback = new LinkedHashMap<>();
            fallback.put("weekId", null);
            fallback.put("weekNo", 1);
            fallback.put("title", "集训计划");
            fallback.put("startDate", camp.get("startDate"));
            fallback.put("endDate", camp.get("endDate"));
            fallback.put("days", days);
            weekPayloads.add(fallback);
        } else if (!ungroupedDays.isEmpty()) {
            Map<String, Object> fallback = new LinkedHashMap<>();
            fallback.put("weekId", null);
            fallback.put("weekNo", null);
            fallback.put("title", "未分组训练日");
            fallback.put("startDate", camp.get("startDate"));
            fallback.put("endDate", camp.get("endDate"));
            fallback.put("days", ungroupedDays);
            weekPayloads.add(fallback);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasCamp", true);
        result.put("camp", camp);
        result.put("weeks", weekPayloads);
        result.put("completedDays", days.stream().filter(day -> "SUBMITTED".equals(day.get("progressStatus"))).count());
        List<Map<String, Object>> accessibleTasks = days.stream()
                .flatMap(day -> ((List<Map<String, Object>>) day.getOrDefault("tasks", List.of())).stream())
                .toList();
        result.put("completedTasks", accessibleTasks.stream().filter(task -> {
            String status = String.valueOf(task.getOrDefault("latestSubmissionStatus", ""));
            return "APPROVED".equals(status) || "PENDING_REVIEW".equals(status) || "REVIEWING".equals(status);
        }).count());
        result.put("totalTasks", accessibleTasks.size());
        result.put("totalDays", camp.get("totalDays"));
        return result;
    }

    public Map<String, Object> day(Long tenantId, Long userId, Long dayId) {
        Map<String, Object> camp = currentCamp(tenantId, userId);
        if (camp.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "当前没有可访问的集训营");
        }
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT d.id dayId, d.day_no dayNo, d.training_date trainingDate, d.title,
                   d.summary, d.content_html contentHtml, d.due_at dueAt, d.status,
                   d.early_unlocked_at earlyUnlockedAt,
                   w.week_no weekNo, w.title weekTitle, w.start_date weekStartDate, w.end_date weekEndDate
            FROM training_day d
            LEFT JOIN training_camp_week w ON w.id = d.week_id
            WHERE d.id = ? AND d.camp_id = ?
            """, dayId, camp.get("campId"));
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        }
        Map<String, Object> day = new LinkedHashMap<>(rows.get(0));
        day.putAll(availabilityService.availability(day));
        if (Boolean.TRUE.equals(day.get("locked"))) {
            Map<String, Object> locked = new LinkedHashMap<>();
            locked.put("hasCamp", true);
            locked.put("hasTrainingDay", true);
            locked.put("locked", true);
            locked.put("lockReason", day.get("lockReason"));
            locked.put("scheduledUnlockAt", day.get("scheduledUnlockAt"));
            locked.put("effectiveUnlockAt", day.get("effectiveUnlockAt"));
            locked.put("trainingDate", day.get("trainingDate"));
            locked.put("dayNo", day.get("dayNo"));
            locked.put("dayId", day.get("dayId"));
            locked.put("title", day.get("title"));
            locked.put("camp", camp);
            locked.put("tasks", List.of());
            locked.put("primaryTask", Map.of());
            locked.put("learningResources", List.of());
            locked.put("attachments", List.of());
            locked.put("message", "NOT_PUBLISHED".equals(day.get("lockReason"))
                    ? "训练日尚未发布"
                    : "训练日尚未开放");
            return locked;
        }
        Map<String, Object> result = dayPayload(day, camp, tenantId, userId);
        result.put("hasCamp", true);
        result.put("hasTrainingDay", true);
        result.put("locked", false);
        return result;
    }

    public Map<String, Object> dayOverview(Long tenantId, Long userId, Long dayId) {
        return overviewPayload(tenantId, userId, day(tenantId, userId, dayId));
    }

    /**
     * 任务书页驻留心跳：可见且活跃时累计秒数，写入 student_learning_session（TASK_BOOK）。
     * 与视频心跳一致：同 session 间隔 0.5–25s 计入，单次最多 +20s。
     */
    @Transactional
    public Map<String, Object> recordTaskBookDwell(
            Long tenantId,
            Long userId,
            Long dayId,
            String sessionId,
            boolean visible,
            boolean active,
            boolean reset
    ) {
        Map<String, Object> day = day(tenantId, userId, dayId);
        if (!Boolean.TRUE.equals(day.get("hasTrainingDay"))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        }
        if (Boolean.TRUE.equals(day.get("locked"))) {
            throw new ResponseStatusException(HttpStatus.LOCKED, String.valueOf(day.getOrDefault("message", "训练日尚未开放")));
        }
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "学习会话无效");
        }
        @SuppressWarnings("unchecked")
        Map<String, Object> camp = (Map<String, Object>) day.getOrDefault("camp", Map.of());
        Long teamId = longValue(camp.get("teamId"));
        LocalDateTime now = LocalDateTime.now();

        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, duration_seconds durationSeconds, metadata_json metadataJson,
                   started_at startedAt, ended_at endedAt
            FROM student_learning_session
            WHERE user_id = ? AND source_type = 'TRAINING_DAY' AND source_id = ?
              AND activity_type = 'TASK_BOOK'
            FOR UPDATE
            """, userId, dayId);

        if (rows.isEmpty()) {
            jdbc.update("""
                INSERT INTO student_learning_session
                (tenant_id, user_id, team_id, activity_type, source_type, source_id,
                 started_at, ended_at, duration_seconds, metadata_json)
                VALUES (?, ?, ?, 'TASK_BOOK', 'TRAINING_DAY', ?, ?, ?, 0, ?)
                """,
                    tenantId, userId, teamId, dayId, now, now,
                    """
                    {"sessionId":"%s","lastHeartbeatAt":"%s"}
                    """.formatted(sessionId, now));
            return Map.of(
                    "dayId", dayId,
                    "durationSeconds", 0,
                    "sessionId", sessionId
            );
        }

        Map<String, Object> current = rows.get(0);
        int durationSeconds = intValue(current.get("durationSeconds"), 0);
        String meta = String.valueOf(current.getOrDefault("metadataJson", "{}"));
        String previousSession = extractJsonString(meta, "sessionId");
        LocalDateTime previousHeartbeat = parseIsoDateTime(extractJsonString(meta, "lastHeartbeatAt"));
        if (previousHeartbeat == null) {
            previousHeartbeat = localDateTimeValue(current.get("endedAt"));
        }
        boolean sameSession = sessionId.equals(previousSession);

        if (!reset && visible && active && sameSession && previousHeartbeat != null) {
            double elapsedSeconds = Duration.between(previousHeartbeat, now).toMillis() / 1000.0;
            if (elapsedSeconds >= 0.5 && elapsedSeconds <= 25) {
                durationSeconds += Math.max(1, Math.min(20, (int) Math.round(elapsedSeconds)));
            }
        }

        String nextMeta = """
            {"sessionId":"%s","lastHeartbeatAt":"%s"}
            """.formatted(sessionId, now).trim();
        jdbc.update("""
            UPDATE student_learning_session
            SET duration_seconds = ?, ended_at = ?, metadata_json = ?, updated_at = CURRENT_TIMESTAMP,
                team_id = COALESCE(team_id, ?)
            WHERE id = ?
            """, durationSeconds, now, nextMeta, teamId, current.get("id"));

        return Map.of(
                "dayId", dayId,
                "durationSeconds", durationSeconds,
                "sessionId", sessionId
        );
    }

    private static String extractJsonString(String json, String key) {
        if (json == null || key == null) return null;
        String pattern = "\"" + key + "\"\\s*:\\s*\"([^\"]*)\"";
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(pattern).matcher(json);
        return m.find() ? m.group(1) : null;
    }

    private static LocalDateTime parseIsoDateTime(String raw) {
        if (raw == null || raw.isBlank()) return null;
        try {
            return LocalDateTime.parse(raw.replace(' ', 'T').replaceAll("\\.\\d+$", ""));
        } catch (Exception ignored) {
            return null;
        }
    }

    private static LocalDateTime localDateTimeValue(Object value) {
        if (value == null) return null;
        if (value instanceof LocalDateTime ldt) return ldt;
        if (value instanceof java.sql.Timestamp ts) return ts.toLocalDateTime();
        try {
            return LocalDateTime.parse(String.valueOf(value).replace(' ', 'T').replaceAll("\\.\\d+$", ""));
        } catch (Exception ignored) {
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> overviewPayload(Long tenantId, Long userId, Map<String, Object> day) {
        Map<String, Object> result = new LinkedHashMap<>(day);
        if (!Boolean.TRUE.equals(day.get("hasCamp")) || !Boolean.TRUE.equals(day.get("hasTrainingDay"))) {
            return result;
        }

        Map<String, Object> trainingPlan = plan(tenantId, userId);
        Long dayId = longValue(day.get("dayId"));
        List<Map<String, Object>> weeks = (List<Map<String, Object>>) trainingPlan.getOrDefault("weeks", List.of());
        Map<String, Object> currentWeek = weeks.stream()
                .filter(week -> ((List<Map<String, Object>>) week.getOrDefault("days", List.of())).stream()
                        .anyMatch(item -> Objects.equals(longValue(item.get("dayId")), dayId)))
                .findFirst()
                .orElse(Map.of());
        result.put("currentWeek", currentWeek);

        Map<String, Object> primaryTask = (Map<String, Object>) day.getOrDefault("primaryTask", Map.of());
        Long submissionId = longValue(primaryTask.get("latestSubmissionId"));
        if (submissionId == null) {
            result.put("submission", Map.of());
            result.put("feedback", Map.of("feedbackReady", false));
        } else {
            result.put("submission", submission(tenantId, userId, submissionId));
            result.put("feedback", feedback(tenantId, userId, submissionId));
        }

        Map<String, Object> camp = (Map<String, Object>) day.getOrDefault("camp", Map.of());
        result.put("recentFeedback", recentFeedback(
                tenantId,
                userId,
                longValue(camp.get("campId")),
                submissionId
        ));
        return result;
    }

    private Map<String, Object> recentFeedback(
            Long tenantId,
            Long userId,
            Long campId,
            Long excludedSubmissionId
    ) {
        if (campId == null) return Map.of();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.id submissionId, s.status, s.review_comment reviewComment,
                   s.reviewed_at reviewedAt, s.version_no versionNo,
                   d.id dayId, d.day_no dayNo, d.title dayTitle,
                   t.title taskTitle, reviewer.username reviewerName
            FROM project_task_submission s
            JOIN project_task t ON t.id = s.task_id
            JOIN training_day_task dt ON dt.task_id = t.id
            JOIN training_day d ON d.id = dt.training_day_id AND d.camp_id = ?
            JOIN project_team pt ON pt.id = s.team_id AND pt.tenant_id = ?
            LEFT JOIN users reviewer ON reviewer.id = s.reviewer_id
            WHERE s.submitter_id = ? AND s.reviewed_at IS NOT NULL
              AND (? IS NULL OR s.id <> ?)
            ORDER BY s.reviewed_at DESC, s.id DESC
            LIMIT 1
            """, campId, tenantId, userId, excludedSubmissionId, excludedSubmissionId);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    public Map<String, Object> submission(Long tenantId, Long userId, Long submissionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.id submissionId, s.task_id taskId, s.team_id teamId, s.submitter_id submitterId,
                   s.submission_type submissionType, s.content, s.version_no versionNo, s.status,
                   s.reviewer_id reviewerId, s.review_comment reviewComment, s.reviewed_at reviewedAt,
                   s.created_at submittedAt, t.title taskTitle, t.description taskDescription,
                   pt.name teamName, reviewer.username reviewerName
            FROM project_task_submission s
            JOIN project_task t ON t.id = s.task_id
            JOIN project_team pt ON pt.id = s.team_id AND pt.tenant_id = ?
            JOIN project_team_member tm ON tm.team_id = pt.id AND tm.user_id = ?
            LEFT JOIN users reviewer ON reviewer.id = s.reviewer_id
            WHERE s.id = ?
            """, tenantId, userId, submissionId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "提交记录不存在");
        }
        Map<String, Object> result = new LinkedHashMap<>(rows.get(0));
        result.put("assets", submissionAssets(submissionId));
        result.put("links", submissionLinks(submissionId));
        result.put("requirements", taskRequirements(longValue(result.get("taskId"))));
        result.put("feedbackReady", result.get("reviewedAt") != null || result.get("reviewComment") != null);
        return result;
    }

    public Map<String, Object> feedback(Long tenantId, Long userId, Long submissionId) {
        Map<String, Object> submission = submission(tenantId, userId, submissionId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("submissionId", submissionId);
        result.put("taskId", submission.get("taskId"));
        result.put("taskTitle", submission.get("taskTitle"));
        result.put("status", submission.get("status"));
        result.put("reviewerName", submission.get("reviewerName"));
        result.put("reviewComment", submission.get("reviewComment"));
        result.put("reviewedAt", submission.get("reviewedAt"));
        result.put("submittedAt", submission.get("submittedAt"));
        result.put("versionNo", submission.get("versionNo"));
        result.put("feedbackReady", submission.get("feedbackReady"));
        return result;
    }

    public Map<String, Object> currentCamp(Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT c.id campId, c.name campName, c.subtitle, c.start_date startDate, c.end_date endDate,
                   c.total_days totalDays, c.status campStatus,
                   pt.id teamId, pt.name teamName, pt.description projectDescription,
                   pt.current_stage currentStage, tm.role_in_team roleInTeam
            FROM training_camp c
            JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.status = 'ACTIVE'
            JOIN project_team pt ON pt.id = ct.team_id AND pt.tenant_id = c.tenant_id
            JOIN project_team_member tm ON tm.team_id = pt.id AND tm.user_id = ?
            WHERE c.tenant_id = ? AND c.status IN ('PLANNED', 'ACTIVE')
            ORDER BY
              CASE WHEN ? BETWEEN c.start_date AND c.end_date THEN 0 ELSE 1 END,
              c.start_date DESC, c.id DESC
            LIMIT 1
            """, userId, tenantId, availabilityService.today());
        if (rows.isEmpty()) return Map.of();
        Map<String, Object> camp = new LinkedHashMap<>(rows.get(0));
        // 懒修复：晚加入学生补齐已发布训练日任务指派人，避免前几天任务无法提交
        try {
            Long teamId = longValue(camp.get("teamId"));
            if (teamId != null) {
                projectTeamService.ensureStudentOnPublishedTrainingDayTasks(teamId, userId);
            }
        } catch (Exception ignored) {
            // 不阻断训练计划加载
        }
        LocalDate start = localDate(camp.get("startDate"));
        LocalDate end = localDate(camp.get("endDate"));
        LocalDate today = availabilityService.today();
        long dayNo = start == null ? 0 : ChronoUnit.DAYS.between(start, today) + 1;
        long remaining = end == null ? 0 : Math.max(0, ChronoUnit.DAYS.between(today, end));
        int totalDays = intValue(camp.get("totalDays"), 21);
        camp.put("currentDay", Math.max(0, Math.min(totalDays, dayNo)));
        camp.put("remainingDays", remaining);
        return camp;
    }

    private Map<String, Object> dayPayload(Map<String, Object> day, Map<String, Object> camp, Long tenantId, Long userId) {
        Map<String, Object> result = new LinkedHashMap<>(day);
        result.put("camp", camp);
        List<Map<String, Object>> tasks = jdbc.queryForList("""
            SELECT t.id taskId, t.title, t.description, t.priority, t.status, t.due_at dueAt,
                   dt.is_primary isPrimary, dt.sort_order sortOrder,
                   (SELECT s.id FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmissionId,
                   (SELECT s.status FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmissionStatus,
                   (SELECT s.created_at FROM project_task_submission s
                    WHERE s.task_id = t.id AND s.submitter_id = ?
                    ORDER BY s.version_no DESC, s.id DESC LIMIT 1) latestSubmittedAt
            FROM training_day_task dt
            JOIN project_task t ON t.id = dt.task_id
            WHERE dt.training_day_id = ? AND t.team_id = ?
            ORDER BY dt.is_primary DESC, dt.sort_order ASC, t.id ASC
            """, userId, userId, userId, day.get("dayId"), camp.get("teamId"));
        for (Map<String, Object> task : tasks) {
            task.put("requirements", taskRequirements(longValue(task.get("taskId"))));
            task.put("assignees", taskAssignees(longValue(task.get("taskId"))));
        }
        result.put("tasks", tasks);
        result.put("attachments", contentService.studentAttachments(longValue(day.get("dayId"))));
        result.put("learningResources", learningService.studentResources(
                tenantId,
                userId,
                longValue(day.get("dayId"))
        ));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> learningResources =
                (List<Map<String, Object>>) result.getOrDefault("learningResources", List.of());
        long incompleteRequired = learningResources.stream()
                .filter(item -> {
                    boolean required = Boolean.TRUE.equals(item.get("required"))
                            || "1".equals(String.valueOf(item.get("required")));
                    boolean complete = "COMPLETED".equalsIgnoreCase(String.valueOf(item.get("learningStatus")))
                            || intValue(item.get("progressPercent"), 0) >= 100;
                    return required && !complete;
                })
                .count();
        result.put("incompleteRequiredLearningCount", incompleteRequired);
        result.put("primaryTask", tasks.stream()
                .filter(task -> intValue(task.get("isPrimary"), 0) == 1)
                .findFirst()
                .orElse(tasks.isEmpty() ? Map.of() : tasks.get(0)));
        result.put("previousDay", adjacentDay(camp.get("campId"), intValue(day.get("dayNo"), 0) - 1));
        result.put("nextDay", adjacentDay(camp.get("campId"), intValue(day.get("dayNo"), 0) + 1));
        return result;
    }

    private void assertAvailable(Map<String, Object> day) {
        if (!Boolean.TRUE.equals(day.get("locked"))) return;
        String reason = "NOT_PUBLISHED".equals(day.get("lockReason"))
                ? "训练日尚未发布"
                : "训练日尚未开放";
        throw new ResponseStatusException(HttpStatus.LOCKED, reason);
    }

    private List<Map<String, Object>> taskRequirements(Long taskId) {
        if (taskId == null) return List.of();
        return jdbc.queryForList("""
            SELECT id, title, description, required, asset_type assetType, sort_order sortOrder
            FROM project_task_requirement
            WHERE task_id = ?
            ORDER BY sort_order ASC, id ASC
            """, taskId);
    }

    private List<Map<String, Object>> taskAssignees(Long taskId) {
        if (taskId == null) return List.of();
        return jdbc.queryForList("""
            SELECT DISTINCT u.id userId, u.username
            FROM users u
            JOIN (
              SELECT owner_user_id user_id FROM project_task WHERE id = ? AND owner_user_id IS NOT NULL
              UNION
              SELECT user_id FROM project_task_assignee WHERE task_id = ?
            ) owner_ids ON owner_ids.user_id = u.id
            ORDER BY u.username
            """, taskId, taskId);
    }

    private List<Map<String, Object>> submissionAssets(Long submissionId) {
        return jdbc.queryForList("""
            SELECT id, asset_kind assetKind, file_url fileUrl, file_name fileName,
                   file_size fileSize, file_type fileType, sort_order sortOrder
            FROM project_submission_asset
            WHERE submission_id = ?
            ORDER BY sort_order ASC, id ASC
            """, submissionId);
    }

    private List<Map<String, Object>> submissionLinks(Long submissionId) {
        return jdbc.queryForList("""
            SELECT id, link_type linkType, title, url, sort_order sortOrder
            FROM project_submission_link
            WHERE submission_id = ?
            ORDER BY sort_order ASC, id ASC
            """, submissionId);
    }

    private Map<String, Object> adjacentDay(Object campId, int dayNo) {
        if (dayNo < 1) return Map.of();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id dayId, day_no dayNo, training_date trainingDate, title
            FROM training_day
            WHERE camp_id = ? AND day_no = ? AND status <> 'DRAFT'
            """, campId, dayNo);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    private Map<String, Object> nextTrainingDay(Object campId, LocalDate today) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id dayId, day_no dayNo, training_date trainingDate, title
            FROM training_day
            WHERE camp_id = ? AND training_date > ? AND status <> 'DRAFT'
            ORDER BY training_date ASC
            LIMIT 1
            """, campId, today);
        return rows.isEmpty() ? Map.of() : rows.get(0);
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

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) return number.intValue();
        if (value == null) return fallback;
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private LocalDate localDate(Object value) {
        if (value instanceof LocalDate localDate) return localDate;
        if (value instanceof java.sql.Date date) return date.toLocalDate();
        if (value == null) return null;
        try {
            return LocalDate.parse(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }
}
