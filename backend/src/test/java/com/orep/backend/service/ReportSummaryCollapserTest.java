package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class ReportSummaryCollapserTest {

    @Test
    void sameDocketKeepsLatestRowAndCountsReruns() {
        List<Map<String, Object>> collapsed = ReportSummaryCollapser.collapse(List.of(
                row(47L, "docket-a", 48.3),
                row(46L, "docket-a", 48.3),
                row(45L, "docket-a", 48.3),
                row(37L, "", 37.6)
        ));
        assertEquals(2, collapsed.size());
        assertEquals(47L, collapsed.get(0).get("sessionId"));
        assertEquals(3, collapsed.get(0).get("runCount"));
        assertEquals(37L, collapsed.get(1).get("sessionId"));
        assertNull(collapsed.get(1).get("runCount"));
    }

    @Test
    void durationSkipDocketDisappearsAndRealZeroStays() {
        List<Map<String, Object>> collapsed = ReportSummaryCollapser.collapse(List.of(
                skipRow(49L, "docket-skip", 0.0),
                skipRow(48L, "docket-skip", 0.0),
                zeroRow(30L, "docket-real-zero", 0.0),
                row(52L, "docket-green", 43.2)
        ));
        assertEquals(2, collapsed.size());
        assertEquals(30L, collapsed.get(0).get("sessionId"));
        assertEquals(52L, collapsed.get(1).get("sessionId"));
    }

    @Test
    void blankRowsStayEmpty() {
        assertEquals(List.of(), ReportSummaryCollapser.collapse(List.of()));
        assertEquals(List.of(), ReportSummaryCollapser.collapse(null));
    }

    private static Map<String, Object> row(Long sessionId, String docketId, double score) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("sessionId", sessionId);
        row.put("docketId", docketId);
        row.put("overallScore", score);
        return row;
    }

    private static Map<String, Object> skipRow(Long sessionId, String docketId, double score) {
        Map<String, Object> row = row(sessionId, docketId, score);
        row.put("criticalIssuesJson", "[\"路演实际时长 120 秒，远低于比赛要求的 3600 秒\"]");
        return row;
    }

    private static Map<String, Object> zeroRow(Long sessionId, String docketId, double score) {
        Map<String, Object> row = row(sessionId, docketId, score);
        row.put("criticalIssuesJson", "[\"仓库提交记录不足\"]");
        return row;
    }
}
