package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.Script;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ScriptScoreReviseService {

    private final ScriptService scriptService;
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    public ScriptScoreReviseService(ScriptService scriptService, JdbcTemplate jdbc, ObjectMapper mapper) {
        this.scriptService = scriptService;
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    public Map<String, Object> brief(Long scriptId, Long userId, Long tenantId) {
        Script script = scriptService.getById(scriptId, userId);
        if (script == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        Map<String, Object> score = latestScore(userId, tenantId);
        List<Map<String, Object>> items = ScriptScoreRevisePlanner.normalizeItems(
                score.get("improvementPriorities"),
                score.get("reportId") == null ? null : String.valueOf(score.get("reportId"))
        );
        List<Map<String, Object>> steps = ScriptScoreRevisePlanner.flattenSteps(script.getContent());
        List<Map<String, Object>> diagnosis = ScriptScoreRevisePlanner.plan(items, steps);
        long mapped = diagnosis.stream().filter(d -> Boolean.TRUE.equals(d.get("mapped"))).count();

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("scriptId", script.getId());
        out.put("scriptTitle", script.getTitle());
        out.put("contentVersion", ScriptService.currentVersion(script.getContentVersion()));
        out.put("pptJobId", script.getPptJobId());
        out.put("scoreReportId", score.get("reportId"));
        out.put("scoreSessionId", score.get("sessionId"));
        out.put("overallScore", score.get("overallScore"));
        out.put("meetingTitle", score.get("meetingTitle"));
        out.put("hasReport", Boolean.TRUE.equals(score.get("hasReport")));
        out.put("diagnosis", diagnosis);
        out.put("mappedCount", mapped);
        out.put("unmappedCount", diagnosis.size() - mapped);
        return out;
    }

    private Map<String, Object> latestScore(Long userId, Long tenantId) {
        Long teamId = teamIdOf(userId, tenantId);
        if (teamId == null) return Map.of("hasReport", false);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT r.id AS reportId, r.session_id AS sessionId, r.meeting_id AS meetingId,
                       r.overall_score AS overallScore, r.improvement_priorities_json AS improvementPrioritiesJson,
                       m.title AS meetingTitle
                FROM ai_score_report r
                JOIN ai_scoring_session s ON s.id = r.session_id AND s.status = 'completed'
                LEFT JOIN meeting m ON m.id = r.meeting_id
                WHERE r.status = 'completed'
                  AND (
                    s.team_id = ?
                    OR EXISTS (
                      SELECT 1 FROM project_roadshow_binding b
                      WHERE b.team_id = ? AND b.meeting_id = r.meeting_id
                    )
                  )
                ORDER BY r.completed_at DESC, r.id DESC
                LIMIT 1
                """, teamId, teamId);
        if (rows.isEmpty()) return Map.of("hasReport", false);
        Map<String, Object> report = new LinkedHashMap<>(rows.get(0));
        report.put("hasReport", true);
        report.put("improvementPriorities", parseList(report.remove("improvementPrioritiesJson")));
        return report;
    }

    private Long teamIdOf(Long userId, Long tenantId) {
        if (userId == null) return null;
        List<Long> ids = jdbc.query("""
                SELECT tm.team_id
                FROM project_team_member tm
                JOIN project_team pt ON pt.id = tm.team_id
                WHERE tm.user_id = ?
                  AND (? IS NULL OR pt.tenant_id = ?)
                ORDER BY tm.id DESC
                LIMIT 1
                """, (rs, i) -> rs.getLong(1), userId, tenantId, tenantId);
        return ids.isEmpty() ? null : ids.get(0);
    }

    private List<Map<String, Object>> parseList(Object raw) {
        if (raw == null) return List.of();
        try {
            String json = raw instanceof String s ? s : mapper.writeValueAsString(raw);
            List<Object> list = mapper.readValue(json, new TypeReference<>() {});
            return list.stream().map(el -> {
                if (el instanceof Map<?, ?> m) {
                    Map<String, Object> copy = new LinkedHashMap<>();
                    m.forEach((k, v) -> copy.put(String.valueOf(k), v));
                    return copy;
                }
                return Map.<String, Object>of("title", String.valueOf(el));
            }).toList();
        } catch (Exception e) {
            return List.of();
        }
    }
}
