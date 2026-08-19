package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** 聚合首页备赛脉搏所需的真实数据库事实。 */
@Service
public class CompetitionReadinessService {
    private final JdbcTemplate jdbc;
    private final CompetitionReadinessAnalyzer analyzer;
    private final ObjectMapper objectMapper;

    public CompetitionReadinessService(
            JdbcTemplate jdbc,
            CompetitionReadinessAnalyzer analyzer,
            ObjectMapper objectMapper
    ) {
        this.jdbc = jdbc;
        this.analyzer = analyzer;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> build(Long teamId) {
        List<CompetitionReadinessAnalyzer.MaterialFact> materialFacts = materialFacts(teamId);
        List<CompetitionReadinessAnalyzer.IssueFact> issueFacts = issueFacts(teamId);
        List<String> trackRequirements = activeTrackRequirements(teamId);
        int rehearsalCount = count("SELECT COUNT(*) FROM project_roadshow_binding WHERE team_id = ?", teamId);
        boolean roadshowCompleted = count("""
                SELECT COUNT(*)
                FROM project_roadshow_binding b
                JOIN ai_score_report r ON r.meeting_id = b.meeting_id
                WHERE b.team_id = ? AND LOWER(r.status) = 'completed'
                """, teamId) > 0;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("generatedAt", LocalDateTime.now());
        result.put("deadline", deadline(teamId));
        result.put("activity", activity(teamId));
        result.put("recentUpdates", recentUpdates(teamId));
        result.put("gaps", analyzer.analyze(new CompetitionReadinessAnalyzer.Snapshot(
                materialFacts,
                trackRequirements,
                issueFacts,
                rehearsalCount,
                roadshowCompleted
        )));
        result.put("basis", Map.of(
                "approvedMaterialCount", materialFacts.stream().filter(this::approved).count(),
                "rehearsalCount", rehearsalCount,
                "trackRequirementCount", trackRequirements.size(),
                "openHighRiskCount", issueFacts.stream().filter(this::openHighRisk).count()
        ));
        return result;
    }

    private List<CompetitionReadinessAnalyzer.MaterialFact> materialFacts(Long teamId) {
        return jdbc.queryForList("""
                SELECT material_type materialType, name, description, review_status reviewStatus
                FROM project_material WHERE team_id = ?
                """, teamId).stream().map(row -> new CompetitionReadinessAnalyzer.MaterialFact(
                text(row.get("materialType")), text(row.get("name")),
                text(row.get("description")), text(row.get("reviewStatus"))
        )).toList();
    }

    private List<CompetitionReadinessAnalyzer.IssueFact> issueFacts(Long teamId) {
        return jdbc.queryForList("""
                SELECT title, description, severity, status
                FROM project_review_issue
                WHERE team_id = ?
                ORDER BY FIELD(status, 'OPEN', 'IN_PROGRESS', 'DONE'),
                         FIELD(severity, 'HIGH', 'MEDIUM', 'LOW'), updated_at DESC
                """, teamId).stream().map(row -> new CompetitionReadinessAnalyzer.IssueFact(
                text(row.get("title")), text(row.get("description")),
                text(row.get("severity")), text(row.get("status"))
        )).toList();
    }

    private List<String> activeTrackRequirements(Long teamId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT es.material_types_json materialTypesJson
                FROM ai_scoring_session s
                LEFT JOIN track_evidence_schema es
                  ON es.id = s.evidence_schema_id
                  OR (es.track_id = s.track_id AND es.status = 'active' AND es.active_slot = 'ACTIVE')
                WHERE s.team_id = ?
                ORDER BY s.created_at DESC, es.id DESC
                LIMIT 1
                """, teamId);
        if (rows.isEmpty()) return List.of();
        Object raw = rows.get(0).get("materialTypesJson");
        if (raw == null) return List.of();
        try {
            return objectMapper.readValue(String.valueOf(raw), new TypeReference<List<String>>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Map<String, Object> deadline(Long teamId) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT end_date endDate FROM project_team WHERE id = ?", teamId);
        if (rows.isEmpty() || rows.get(0).get("endDate") == null) {
            return Map.of("configured", false, "label", "比赛日期待设置");
        }
        LocalDate date = toDate(rows.get(0).get("endDate"));
        if (date == null) return Map.of("configured", false, "label", "比赛日期待设置");
        long days = ChronoUnit.DAYS.between(LocalDate.now(), date);
        String label = days > 0 ? "距比赛 " + days + " 天" : days == 0 ? "今天比赛" : "比赛已过 " + Math.abs(days) + " 天";
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("configured", true);
        value.put("date", date);
        value.put("daysRemaining", days);
        value.put("label", label);
        value.put("tone", days < 0 ? "late" : days <= 7 ? "warning" : "normal");
        return value;
    }

    private Map<String, Object> activity(Long teamId) {
        LocalDate start = LocalDate.now().minusDays(6);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT DATE(eventAt) activityDate, COUNT(*) activityCount
                FROM (
                  SELECT updated_at eventAt FROM project_task WHERE team_id = ? AND updated_at >= ?
                  UNION ALL
                  SELECT created_at FROM project_task_submission WHERE team_id = ? AND created_at >= ?
                  UNION ALL
                  SELECT updated_at FROM project_material WHERE team_id = ? AND updated_at >= ?
                  UNION ALL
                  SELECT created_at FROM project_roadshow_binding WHERE team_id = ? AND created_at >= ?
                  UNION ALL
                  SELECT updated_at FROM project_review_issue WHERE team_id = ? AND updated_at >= ?
                ) events
                GROUP BY DATE(eventAt)
                """, teamId, start.atStartOfDay(), teamId, start.atStartOfDay(), teamId, start.atStartOfDay(),
                teamId, start.atStartOfDay(), teamId, start.atStartOfDay());
        Map<LocalDate, Integer> counts = new LinkedHashMap<>();
        for (Map<String, Object> row : rows) {
            LocalDate date = toDate(row.get("activityDate"));
            if (date != null) counts.put(date, number(row.get("activityCount")));
        }
        List<Map<String, Object>> points = new ArrayList<>();
        int total = 0;
        for (int i = 0; i < 7; i++) {
            LocalDate date = start.plusDays(i);
            int count = counts.getOrDefault(date, 0);
            total += count;
            points.add(Map.of("date", date, "label", (date.getMonthValue()) + "/" + date.getDayOfMonth(), "count", count));
        }
        return Map.of("days", points, "total", total, "label", "近 7 天 " + total + " 次更新");
    }

    private List<Map<String, Object>> recentUpdates(Long teamId) {
        return jdbc.queryForList("""
                SELECT kind, title, eventAt
                FROM (
                  SELECT 'task' kind, CONCAT('任务更新：', title) title, updated_at eventAt
                  FROM project_task WHERE team_id = ?
                  UNION ALL
                  SELECT 'submission', CONCAT('成果提交：', t.title), s.created_at
                  FROM project_task_submission s JOIN project_task t ON t.id = s.task_id WHERE s.team_id = ?
                  UNION ALL
                  SELECT 'material', CONCAT('材料更新：', name), updated_at
                  FROM project_material WHERE team_id = ?
                  UNION ALL
                  SELECT 'roadshow', CONCAT('路演记录：', COALESCE(m.title, '未命名会议')), b.created_at
                  FROM project_roadshow_binding b JOIN meeting m ON m.id = b.meeting_id WHERE b.team_id = ?
                  UNION ALL
                  SELECT 'review', CONCAT('复盘更新：', title), updated_at
                  FROM project_review_issue WHERE team_id = ?
                ) events
                ORDER BY eventAt DESC
                LIMIT 3
                """, teamId, teamId, teamId, teamId, teamId);
    }

    private int count(String sql, Long teamId) {
        Integer value = jdbc.queryForObject(sql, Integer.class, teamId);
        return value == null ? 0 : value;
    }

    private boolean approved(CompetitionReadinessAnalyzer.MaterialFact fact) {
        String status = text(fact.reviewStatus()).toUpperCase(Locale.ROOT);
        return status.equals("APPROVED") || status.equals("DONE") || status.equals("ACCEPTED");
    }

    private boolean openHighRisk(CompetitionReadinessAnalyzer.IssueFact fact) {
        String status = text(fact.status()).toUpperCase(Locale.ROOT);
        return "HIGH".equalsIgnoreCase(fact.severity())
                && !List.of("DONE", "CLOSED", "RESOLVED").contains(status);
    }

    private int number(Object value) {
        if (value instanceof Number number) return number.intValue();
        try { return Integer.parseInt(String.valueOf(value)); } catch (Exception ignored) { return 0; }
    }

    private LocalDate toDate(Object value) {
        if (value instanceof LocalDate date) return date;
        if (value instanceof java.sql.Date date) return date.toLocalDate();
        if (value == null) return null;
        try { return LocalDate.parse(String.valueOf(value).substring(0, 10)); } catch (Exception ignored) { return null; }
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
