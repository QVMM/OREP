package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DocketScoreStatsTest {

    @Test
    void rerunsOfSameTapeCountAsOneAndAverageLatestOnly() {
        DocketScoreStats.Summary summary = DocketScoreStats.summarize(List.of(
                row(55L, 47L, "docket-a", 48.3),
                row(54L, 46L, "docket-a", 48.3),
                row(53L, 45L, "docket-a", 40.9),
                row(46L, 37L, "", 37.6)
        ));
        assertEquals(2, summary.count());
        assertEquals(48.3, summary.latest(), 0.001);
        assertEquals(43.0, summary.average(), 0.001);
    }

    @Test
    void emptyRowsStayEmpty() {
        DocketScoreStats.Summary summary = DocketScoreStats.summarize(List.of());
        assertEquals(0, summary.count());
        assertNull(summary.average());
        assertNull(summary.latest());
    }

    @Test
    void identitySqlDoesNotUseMeetingId() {
        String sql = DocketScoreStats.identitySql("s");
        assertTrue(sql.contains("docket_id"));
        assertTrue(sql.contains("s.id"));
        assertTrue(!sql.contains("meeting"));
        String latest = DocketScoreStats.latestReportOnlySql("r", "s");
        assertTrue(latest.contains("LIMIT 1"));
        assertTrue(latest.contains("docket_id"));
        assertTrue(!latest.contains("meeting"));
    }

    private static Map<String, Object> row(Long reportId, Long sessionId, String docketId, double score) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("reportId", reportId);
        row.put("sessionId", sessionId);
        row.put("docketId", docketId);
        row.put("score", score);
        return row;
    }
}
