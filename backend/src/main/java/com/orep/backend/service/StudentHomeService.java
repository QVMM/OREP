package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.DeliberationState;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class StudentHomeService {
    private static final ZoneId CHINA_ZONE = ZoneId.of("Asia/Shanghai");

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final StudentTrainingService studentTrainingService;
    private final StudentLearningAnalyticsService learningAnalytics;

    public StudentHomeService(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            StudentTrainingService studentTrainingService,
            StudentLearningAnalyticsService learningAnalytics
    ) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.studentTrainingService = studentTrainingService;
        this.learningAnalytics = learningAnalytics;
    }

    public Map<String, Object> home(Long tenantId, Long userId) {
        Map<String, Object> camp = studentTrainingService.currentCamp(tenantId, userId);
        Map<String, Object> profile = userProfile(tenantId, userId);
        Map<String, Object> today = studentTrainingService.today(tenantId, userId);
        Map<String, Object> plan = studentTrainingService.plan(tenantId, userId);
        Long teamId = longValue(camp.get("teamId"));
        if (teamId == null) {
            teamId = longValue(profile.get("teamId"));
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("serverTime", LocalDateTime.now(CHINA_ZONE));
        data.put("profile", profile);
        data.put("camp", camp.isEmpty() ? Map.of("hasCamp", false) : camp);
        data.put("team", teamSummary(teamId));
        data.put("todayTraining", today);
        data.put("planSummary", planSummary(plan));
        data.put("weeklyLearning", learningAnalytics.weekly(userId));
        Map<String, Object> latestScore = latestScore(teamId);
        data.put("roadshow", roadshow(teamId, latestScore));
        data.put("latestScore", latestScore);
        data.put("nextActions", nextActions(tenantId, userId, teamId, today, latestScore));
        return data;
    }

    private Map<String, Object> userProfile(Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT u.id userId, u.username, u.role, u.school_name schoolName,
                   u.college_name collegeName, u.class_name className,
                   pt.id teamId, pt.name teamName, pt.description projectDescription,
                   tm.role_in_team roleInTeam, tm.position_name positionName
            FROM users u
            LEFT JOIN project_team_member tm ON tm.user_id = u.id
            LEFT JOIN project_team pt ON pt.id = tm.team_id AND pt.tenant_id = u.tenant_id AND pt.status = 'ACTIVE'
            WHERE u.id = ? AND u.tenant_id = ?
            ORDER BY pt.updated_at DESC, pt.id DESC
            LIMIT 1
            """, userId, tenantId);
        return rows.isEmpty() ? Map.of("userId", userId) : rows.get(0);
    }

    private Map<String, Object> teamSummary(Long teamId) {
        if (teamId == null) {
            return Map.of("hasTeam", false, "memberCount", 0, "members", List.of());
        }
        List<Map<String, Object>> members = safeQuery("""
            SELECT u.id userId, u.username, tm.role_in_team roleInTeam,
                   tm.position_name positionName
            FROM project_team_member tm
            JOIN users u ON u.id = tm.user_id
            WHERE tm.team_id = ?
            ORDER BY
              CASE tm.role_in_team WHEN 'CAPTAIN' THEN 0 WHEN 'MEMBER' THEN 1 ELSE 2 END,
              tm.joined_at ASC, tm.id ASC
            """, teamId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasTeam", true);
        result.put("teamId", teamId);
        result.put("memberCount", members.size());
        result.put("members", members);
        return result;
    }

    private Map<String, Object> planSummary(Map<String, Object> plan) {
        if (!Boolean.TRUE.equals(plan.get("hasCamp"))) {
            return Map.of(
                    "hasCamp", false,
                    "completedDays", 0,
                    "totalDays", 0,
                    "weeks", List.of()
            );
        }
        return Map.of(
                "hasCamp", true,
                "completedDays", plan.getOrDefault("completedDays", 0),
                "totalDays", plan.getOrDefault("totalDays", 0),
                "weeks", plan.getOrDefault("weeks", List.of())
        );
    }

    /**
     * Home "下场路演" card payload.
     * state drives UI next-action, not a static onboarding checklist:
     * NO_TEAM | NEVER_PRACTICED | LIVE | RECORDED_NO_SCORE | HAS_SCORE
     */
    private Map<String, Object> roadshow(Long teamId, Map<String, Object> latestScore) {
        if (teamId == null) {
            return Map.of(
                    "hasTeam", false,
                    "hasRoadshow", false,
                    "hasScoreReport", false,
                    "state", "NO_TEAM",
                    "practiceCount", 0,
                    "weekPracticeCount", 0
            );
        }

        Integer practiceCount = queryInt("""
            SELECT COUNT(*) FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            WHERE b.team_id = ?
            """, teamId);
        Integer weekPracticeCount = queryInt("""
            SELECT COUNT(*) FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            WHERE b.team_id = ?
              AND m.start_time >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)
            """, teamId);

        List<Map<String, Object>> live = safeQuery("""
            SELECT m.id meetingId, m.title, m.status, m.start_time startTime, m.end_time endTime,
                   m.duration_minutes durationMinutes, b.roadshow_type roadshowType,
                   CASE WHEN r.id IS NULL THEN 0 ELSE 1 END hasScoreReport,
                   r.session_id scoreSessionId
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            LEFT JOIN ai_score_report r ON r.meeting_id = m.id AND r.status = 'completed'
            WHERE b.team_id = ? AND m.status = 'RUNNING'
            ORDER BY m.start_time DESC, m.id DESC
            LIMIT 1
            """, teamId);

        List<Map<String, Object>> latest = safeQuery("""
            SELECT m.id meetingId, m.title, m.status, m.start_time startTime, m.end_time endTime,
                   m.duration_minutes durationMinutes, b.roadshow_type roadshowType,
                   CASE WHEN r.id IS NULL THEN 0 ELSE 1 END hasScoreReport,
                   r.session_id scoreSessionId
            FROM project_roadshow_binding b
            JOIN meeting m ON m.id = b.meeting_id
            LEFT JOIN ai_score_report r ON r.meeting_id = m.id AND r.status = 'completed'
            WHERE b.team_id = ?
            ORDER BY
              CASE WHEN m.status = 'RUNNING' THEN 0 WHEN m.start_time >= NOW() THEN 1 ELSE 2 END,
              m.start_time DESC, m.id DESC
            LIMIT 1
            """, teamId);

        boolean hasRoadshow = practiceCount > 0 && !latest.isEmpty();
        boolean teamHasScore = Boolean.TRUE.equals(latestScore.get("hasReport"));
        Map<String, Object> focus = !live.isEmpty() ? live.get(0)
                : (latest.isEmpty() ? null : latest.get(0));
        boolean latestHasScore = focus != null && toBool(focus.get("hasScoreReport"));

        String state;
        if (!live.isEmpty()) {
            state = "LIVE";
        } else if (teamHasScore) {
            state = "HAS_SCORE";
        } else if (hasRoadshow) {
            state = "RECORDED_NO_SCORE";
        } else {
            state = "NEVER_PRACTICED";
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hasTeam", true);
        result.put("hasRoadshow", hasRoadshow);
        result.put("hasScoreReport", teamHasScore || latestHasScore);
        result.put("state", state);
        result.put("practiceCount", practiceCount);
        result.put("weekPracticeCount", weekPracticeCount);
        if (focus != null) {
            result.put("meetingId", focus.get("meetingId"));
            result.put("title", focus.get("title"));
            result.put("status", focus.get("status"));
            result.put("startTime", focus.get("startTime"));
            result.put("endTime", focus.get("endTime"));
            result.put("durationMinutes", focus.get("durationMinutes"));
            result.put("roadshowType", focus.get("roadshowType"));
            result.put("scoreSessionId", focus.get("scoreSessionId"));
            result.put("latest", focus);
        }
        return result;
    }

    private Integer queryInt(String sql, Object... args) {
        try {
            Integer value = jdbc.queryForObject(sql, Integer.class, args);
            return value == null ? 0 : value;
        } catch (Exception ignored) {
            return 0;
        }
    }

    private boolean toBool(Object value) {
        if (value instanceof Boolean b) return b;
        if (value instanceof Number n) return n.intValue() != 0;
        return value != null && List.of("1", "true", "TRUE", "yes").contains(String.valueOf(value));
    }

    private Map<String, Object> latestScore(Long teamId) {
        if (teamId == null) return Map.of("hasReport", false);
        List<Map<String, Object>> rows = safeQuery("""
            SELECT r.id AS `reportId`, r.session_id AS `sessionId`, r.meeting_id AS `meetingId`,
                    r.overall_score AS `overallScore`, r.dimensions_json AS `dimensionsJson`,
                    r.improvement_priorities_json AS `improvementPrioritiesJson`,
                    r.completed_at AS `completedAt`, m.title AS `meetingTitle`
            FROM ai_score_report r
            JOIN ai_scoring_session s ON s.id = r.session_id AND s.status = 'completed'
            LEFT JOIN meeting m ON m.id = r.meeting_id
            WHERE r.status = 'completed'
              AND (
                s.team_id = ?
                OR EXISTS (
                  SELECT 1
                  FROM project_roadshow_binding b
                  WHERE b.team_id = ? AND b.meeting_id = r.meeting_id
                )
              )
            ORDER BY r.completed_at DESC, r.id DESC
            LIMIT 1
            """, teamId, teamId);
        if (rows.isEmpty()) return Map.of("hasReport", false);
        Map<String, Object> report = new LinkedHashMap<>(followLatestDocketRun(rows.get(0)));
        report.put("hasReport", true);
        report.put("dimensions", jsonObject(report.remove("dimensionsJson")));
        report.put("improvementPriorities", jsonList(report.remove("improvementPrioritiesJson")));
        return report;
    }

    private Map<String, Object> followLatestDocketRun(Map<String, Object> report) {
        Long sessionId = longValue(valueIgnoreCase(report, "sessionId"));
        if (sessionId == null) {
            return report;
        }
        List<Map<String, Object>> latest = safeQuery("""
                SELECT r.session_id AS sessionId, r.report_id AS reportId
                FROM ai_scoring_session s
                JOIN ai_score_docket_run r ON r.docket_id = s.docket_id AND r.status = 'completed'
                WHERE s.id = ? AND s.docket_id IS NOT NULL AND s.docket_id <> ''
                ORDER BY r.run_index DESC
                LIMIT 1
                """, sessionId);
        if (latest.isEmpty()) {
            return report;
        }
        Long newerSessionId = longValue(valueIgnoreCase(latest.get(0), "sessionId"));
        Long newerReportId = longValue(valueIgnoreCase(latest.get(0), "reportId"));
        if (newerSessionId == null || sessionId.equals(newerSessionId) || newerReportId == null) {
            return report;
        }
        List<Map<String, Object>> newer = safeQuery("""
                SELECT r.id AS `reportId`, r.session_id AS `sessionId`, r.meeting_id AS `meetingId`,
                        r.overall_score AS `overallScore`, r.dimensions_json AS `dimensionsJson`,
                        r.improvement_priorities_json AS `improvementPrioritiesJson`,
                        r.completed_at AS `completedAt`, m.title AS `meetingTitle`
                FROM ai_score_report r
                LEFT JOIN meeting m ON m.id = r.meeting_id
                WHERE r.id = ? AND r.status = 'completed'
                LIMIT 1
                """, newerReportId);
        return newer.isEmpty() ? report : newer.get(0);
    }

    private List<Map<String, Object>> nextActions(
            Long tenantId,
            Long userId,
            Long teamId,
            Map<String, Object> today,
            Map<String, Object> latestScore
    ) {
        List<Map<String, Object>> actions = new ArrayList<>();
        Map<String, Object> taskBookAction = publishedTaskBookAction(latestScore);
        if (taskBookAction != null) {
            actions.add(taskBookAction);
        }
        Long primaryTaskId = null;
        if (Boolean.TRUE.equals(today.get("hasTrainingDay"))) {
            @SuppressWarnings("unchecked")
            Map<String, Object> primaryTask = (Map<String, Object>) today.getOrDefault("primaryTask", Map.of());
            if (!primaryTask.isEmpty()) {
                primaryTaskId = longValue(primaryTask.get("taskId"));
                Map<String, Object> action = new LinkedHashMap<>();
                action.put("type", "TRAINING");
                action.put("title", primaryTask.get("title"));
                action.put("meta", primaryTask.get("latestSubmissionId") == null ? "今日集训" : "已提交，等待反馈");
                action.put("path", primaryTask.get("latestSubmissionId") == null
                        ? "/training/today"
                        : "/training/submissions/" + primaryTask.get("latestSubmissionId"));
                action.put("priority", "PRIMARY");
                actions.add(action);
            }
        }

        if (teamId != null && actions.size() < 4) {
            List<Map<String, Object>> taskRows = safeQuery("""
                SELECT t.id taskId, t.title,
                       CASE
                         WHEN t.due_at IS NULL THEN '未设置截止日期'
                         WHEN t.due_at < NOW() THEN CONCAT('已过期 · ', DATE_FORMAT(t.due_at, '%m月%d日 %H:%i'))
                         ELSE CONCAT('截止 ', DATE_FORMAT(t.due_at, '%m月%d日 %H:%i'))
                       END meta,
                       CASE WHEN t.due_at < NOW() THEN 'EXPIRED' ELSE 'NORMAL' END priority
                FROM project_task t
                LEFT JOIN project_task_assignee a ON a.task_id = t.id AND a.user_id = ?
                JOIN project_team pt ON pt.id = t.team_id AND pt.tenant_id = ?
                WHERE t.team_id = ? AND (t.owner_user_id = ? OR a.user_id = ?)
                  AND t.status NOT IN ('DONE', 'APPROVED')
                  AND (? IS NULL OR t.id <> ?)
                ORDER BY (t.due_at IS NOT NULL AND t.due_at < NOW()) ASC,
                         t.due_at IS NULL, t.due_at ASC, t.id DESC
                LIMIT ?
                """, userId, tenantId, teamId, userId, userId,
                    primaryTaskId, primaryTaskId, 4 - actions.size());
            for (Map<String, Object> row : taskRows) {
                Map<String, Object> action = new LinkedHashMap<>(row);
                action.put("type", "TASK");
                action.put("path", "/project-team");
                actions.add(action);
            }
        }
        return actions.stream().limit(4).toList();
    }

    private Map<String, Object> publishedTaskBookAction(Map<String, Object> latestScore) {
        if (latestScore == null || !Boolean.TRUE.equals(latestScore.get("hasReport"))) {
            return null;
        }
        Long sessionId = longValue(valueIgnoreCase(latestScore, "sessionId"));
        if (sessionId == null) {
            return null;
        }
        List<Map<String, Object>> rows = safeQuery("""
                SELECT s.teacher_confirmed teacherConfirmed,
                       s.deliberation_stage deliberationStage,
                       r.task_book_published reportPublished,
                       r.task_book_json reportJson,
                       d.task_book_published docketPublished,
                       d.task_book_json docketJson
                FROM ai_scoring_session s
                LEFT JOIN ai_score_report r ON r.id = s.report_id OR r.session_id = s.id
                LEFT JOIN ai_score_docket d ON d.docket_id = s.docket_id
                WHERE s.id = ?
                LIMIT 1
                """, sessionId);
        if (rows.isEmpty()) {
            return null;
        }
        Map<String, Object> row = rows.get(0);
        boolean confirmed = toBool(row.get("teacherConfirmed"))
                || DeliberationStageMachine.FROZEN.equalsIgnoreCase(text(row.get("deliberationStage")));
        boolean published = DocketTaskBook.flag(row.get("reportPublished"), row.get("docketPublished"));
        DeliberationState state = new DeliberationState();
        state.setFinalized(confirmed);
        if (!DeliberationStageMachine.studentSeesTodos(state, published)) {
            return null;
        }
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(
                toBool(row.get("reportPublished")),
                text(row.get("reportJson")),
                toBool(row.get("docketPublished")),
                text(row.get("docketJson"))
        );
        String title = firstTaskTitle(snapshot.json());
        if (title == null || title.isBlank()) {
            title = "查看本场任务书";
        }
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("type", "TASK_BOOK");
        action.put("title", title);
        TaskBookHang.Progress progress = hungProgress(snapshot.json());
        action.put("meta", progress.hung() > 0 ? progress.display() : "本场任务书");
        action.put("hungCount", progress.hung());
        action.put("hungTotal", progress.total());
        action.put("path", "/ai-score/report/" + sessionId + "/todos");
        action.put("priority", "SCORE");
        action.put("sessionId", sessionId);
        return action;
    }

    private TaskBookHang.Progress hungProgress(String json) {
        if (json == null || json.isBlank()) {
            return new TaskBookHang.Progress(0, 0);
        }
        try {
            return TaskBookHang.progress(objectMapper.readValue(json, com.orep.backend.dto.TaskBook.class));
        } catch (Exception ignored) {
            return new TaskBookHang.Progress(0, 0);
        }
    }

    private String firstTaskTitle(String json) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            Map<String, Object> book = objectMapper.readValue(json, new TypeReference<>() {
            });
            Object items = book.get("items");
            if (items instanceof List<?> list && !list.isEmpty() && list.getFirst() instanceof Map<?, ?> item) {
                Object title = item.get("title");
                return title == null ? null : String.valueOf(title).trim();
            }
        } catch (Exception ignored) {
            return null;
        }
        return null;
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private List<Map<String, Object>> safeQuery(String sql, Object... args) {
        try {
            return jdbc.queryForList(sql, args);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Map<String, Object> jsonObject(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return Map.of();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
        } catch (Exception ignored) {
            return Map.of();
        }
    }

    private List<Object> jsonList(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return List.of();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private static Object valueIgnoreCase(Map<String, Object> row, String key) {
        if (row == null || key == null) {
            return null;
        }
        if (row.containsKey(key)) {
            return row.get(key);
        }
        return row.entrySet().stream()
                .filter(entry -> entry.getKey() != null && entry.getKey().equalsIgnoreCase(key))
                .map(Map.Entry::getValue)
                .findFirst()
                .orElse(null);
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
}
