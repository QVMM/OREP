package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class WorkbenchLatestScoresTest {

    @Test
    void sameDocketKeepsLatestAndUsesRunCountAsAttempt() {
        List<Map<String, Object>> assembled = WorkbenchLatestScores.assemble(List.of(
                row(55L, 47L, "docket-a", 3L, 48.3, "2026-08-17 13:00"),
                row(54L, 46L, "docket-a", 3L, 48.3, "2026-08-17 12:00"),
                row(53L, 45L, "docket-a", 3L, 48.3, "2026-08-17 11:00"),
                row(46L, 37L, "", 3L, 37.6, "2026-08-16 10:00")
        ), 5);
        assertEquals(2, assembled.size());
        assertEquals(55L, assembled.get(0).get("reportId"));
        assertEquals(47L, assembled.get(0).get("sessionId"));
        assertEquals(3, assembled.get(0).get("attemptNo"));
        assertEquals(48.3, (Double) assembled.get(0).get("score"), 0.001);
        assertEquals(46L, assembled.get(1).get("reportId"));
        assertEquals(1, assembled.get(1).get("attemptNo"));
        assertNull(assembled.get(1).get("runCount"));
    }

    @Test
    void durationSkipZeroDoesNotOccupyASlot() {
        List<Map<String, Object>> assembled = WorkbenchLatestScores.assemble(List.of(
                skipRow(57L, 49L, "docket-skip", 3L, 0.0, "2026-08-18 12:00"),
                row(60L, 52L, "docket-green", 3L, 43.2, "2026-08-18 11:00")
        ), 5);
        assertEquals(1, assembled.size());
        assertEquals(52L, assembled.get(0).get("sessionId"));
        assertEquals(43.2, (Double) assembled.get(0).get("score"), 0.001);
    }

    @Test
    void keepsHungDisplayOnLatestRow() {
        Map<String, Object> latest = row(60L, 52L, "docket-green", 3L, 43.2, "2026-08-18 11:00");
        latest.put("hungDisplay", "已回挂 2/2");
        List<Map<String, Object>> assembled = WorkbenchLatestScores.assemble(List.of(latest), 5);
        assertEquals("已回挂 2/2", assembled.get(0).get("hungDisplay"));
    }

    @Test
    void respectsLimitAfterCollapse() {
        List<Map<String, Object>> assembled = WorkbenchLatestScores.assemble(List.of(
                row(55L, 47L, "docket-a", 3L, 48.3, "2026-08-17"),
                row(54L, 46L, "docket-a", 3L, 48.3, "2026-08-16"),
                row(46L, 37L, "", 3L, 37.6, "2026-08-15")
        ), 1);
        assertEquals(1, assembled.size());
        assertEquals(55L, assembled.get(0).get("reportId"));
    }

    private static Map<String, Object> row(
            Long reportId,
            Long sessionId,
            String docketId,
            Long teamId,
            double score,
            String scoredAt
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("reportId", reportId);
        row.put("sessionId", sessionId);
        row.put("docketId", docketId);
        row.put("teamId", teamId);
        row.put("teamName", "应用攻坚队");
        row.put("score", score);
        row.put("scoredAt", scoredAt);
        row.put("title", "SC-" + sessionId);
        return row;
    }

    private static Map<String, Object> skipRow(
            Long reportId,
            Long sessionId,
            String docketId,
            Long teamId,
            double score,
            String scoredAt
    ) {
        Map<String, Object> row = row(reportId, sessionId, docketId, teamId, score, scoredAt);
        row.put("criticalIssuesJson", "[\"路演实际时长 120 秒，远低于比赛要求的 3600 秒\"]");
        return row;
    }
}
