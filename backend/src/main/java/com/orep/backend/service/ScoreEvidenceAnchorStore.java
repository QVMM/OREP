package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class ScoreEvidenceAnchorStore {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ScoreEvidenceAnchorStore(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Map<String, Object>> syncRoundAnchors(
            Long teamId,
            Map<String, Object> roadshow,
            List<Map<String, Object>> anchors
    ) {
        if (teamId == null || roadshow == null || anchors == null || anchors.isEmpty()) return anchors == null ? List.of() : anchors;
        Long meetingId = longValue(roadshow.get("meetingId"));
        Long aiReportId = longValue(roadshow.get("aiReportId"));
        if (meetingId == null) return anchors;
        try {
            Long assessmentId = assessmentId(teamId, meetingId);
            if (assessmentId == null) {
                int assessmentRound = nextAssessmentRound(teamId);
                jdbc.update("""
                    INSERT INTO project_assessment
                    (team_id, meeting_id, assessment_round, assessment_type, overall_score,
                     technical_ceiling_score, score_calibration_json, evidence_snapshot_json)
                    VALUES (?, ?, ?, 'AI_ROADSHOW', ?, ?, ?, ?)
                    """,
                        teamId,
                        meetingId,
                        assessmentRound,
                        decimalValue(roadshow.getOrDefault("score", roadshow.get("aiScore"))),
                        technicalCeilingScore(roadshow.get("scoreCalibration")),
                        text(roadshow.get("scoreCalibrationJson"), null),
                        jsonString(anchors)
                );
                assessmentId = assessmentId(teamId, meetingId);
            } else {
                jdbc.update("""
                    UPDATE project_assessment
                    SET overall_score = ?, technical_ceiling_score = ?, score_calibration_json = ?,
                        evidence_snapshot_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                        decimalValue(roadshow.getOrDefault("score", roadshow.get("aiScore"))),
                        technicalCeilingScore(roadshow.get("scoreCalibration")),
                        text(roadshow.get("scoreCalibrationJson"), null),
                        jsonString(anchors),
                        assessmentId
                );
            }
            List<Map<String, Object>> persisted = persistedAnchors(assessmentId, meetingId, aiReportId);
            Long memoryItemId = memoryItemId(assessmentId);
            if (memoryItemId == null) {
                jdbc.update("""
                    INSERT INTO score_memory_item
                    (assessment_id, team_id, memory_type, title, description, severity, status,
                     source_round, recovered_score, metadata_json)
                    VALUES (?, ?, 'ROUND_EVIDENCE', 'AI评分证据快照',
                            '该条目用于挂载本轮路演评分的转写、关键帧、OCR、录制等证据锚点。',
                            'LOW', 'SYSTEM', NULL, 0, ?)
                    """, assessmentId, teamId, jsonString(Map.of("meetingId", meetingId, "aiReportId", aiReportId)));
                memoryItemId = memoryItemId(assessmentId);
            }
            if (memoryItemId == null) return anchors;

            List<Map<String, Object>> missingAnchors = missingAnchors(anchors, persisted);
            for (Map<String, Object> anchor : anchors.stream().limit(24).toList()) {
                if (!missingAnchors.contains(anchor)) continue;
                jdbc.update("""
                    INSERT INTO score_evidence_anchor
                    (memory_item_id, assessment_id, anchor_type, evidence_text, source_ref, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        memoryItemId,
                        assessmentId,
                        text(anchor.get("type"), "evidence"),
                        text(anchor.get("summary"), "可回看该轮会议证据复核。"),
                        text(anchor.get("sourceRef"), null),
                        decimalValue(anchor.getOrDefault("confidence", "0.8500"))
                );
            }
            return persistedAnchors(assessmentId, meetingId, aiReportId);
        } catch (Exception ignored) {
            return anchors;
        }
    }

    private List<Map<String, Object>> missingAnchors(List<Map<String, Object>> anchors, List<Map<String, Object>> persisted) {
        if (persisted.isEmpty()) return anchors.stream().limit(24).toList();
        List<String> existingKeys = persisted.stream().map(this::anchorKey).toList();
        return anchors.stream()
                .limit(24)
                .filter(anchor -> !existingKeys.contains(anchorKey(anchor)))
                .toList();
    }

    private String anchorKey(Map<String, Object> anchor) {
        return text(anchor.get("type"), "evidence") + "\n" + text(anchor.get("sourceRef"), "");
    }

    private Long assessmentId(Long teamId, Long meetingId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id
            FROM project_assessment
            WHERE team_id = ? AND meeting_id = ?
            LIMIT 1
            """, teamId, meetingId);
        return rows.isEmpty() ? null : longValue(rows.get(0).get("id"));
    }

    private Long memoryItemId(Long assessmentId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id
            FROM score_memory_item
            WHERE assessment_id = ? AND memory_type = 'ROUND_EVIDENCE'
            ORDER BY id ASC
            LIMIT 1
            """, assessmentId);
        return rows.isEmpty() ? null : longValue(rows.get(0).get("id"));
    }

    private List<Map<String, Object>> persistedAnchors(Long assessmentId, Long meetingId, Long aiReportId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id evidenceAnchorId, anchor_type type, evidence_text summary,
                   source_ref sourceRef, confidence
            FROM score_evidence_anchor
            WHERE assessment_id = ?
            ORDER BY id ASC
            """, assessmentId);
        List<Map<String, Object>> anchors = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Map<String, Object> anchor = new LinkedHashMap<>(row);
            anchor.put("meetingId", meetingId == null ? "" : meetingId);
            anchor.put("aiReportId", aiReportId == null ? "" : aiReportId);
            anchors.add(anchor);
        }
        return anchors;
    }

    private int nextAssessmentRound(Long teamId) {
        Integer value = jdbc.queryForObject("SELECT COUNT(*) + 1 FROM project_assessment WHERE team_id = ?", Integer.class, teamId);
        return value == null || value <= 0 ? 1 : value;
    }

    private BigDecimal technicalCeilingScore(Object scoreCalibration) {
        if (!(scoreCalibration instanceof Map<?, ?> raw)) return null;
        Object value = raw.get("ceilingScore");
        if (value == null) value = raw.get("technicalCeilingScore");
        if (value == null) value = raw.get("calibratedScore");
        return decimalValue(value);
    }

    private BigDecimal decimalValue(Object value) {
        if (value == null) return null;
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }

    private String text(Object value, String fallback) {
        if (value == null) return fallback;
        String text = String.valueOf(value).trim();
        return text.isBlank() ? fallback : text;
    }

    private String jsonString(Object value) {
        if (value == null) return null;
        if (value instanceof String text) return text.isBlank() ? null : text;
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignored) {
            return String.valueOf(value);
        }
    }
}
