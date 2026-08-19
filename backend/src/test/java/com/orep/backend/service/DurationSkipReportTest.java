package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DurationSkipReportTest {

    @Test
    void liveTwoMinuteSkipIsDiscarded() {
        assertTrue(DurationSkipReport.matches(
                0,
                "[\"路演实际时长 120 秒，远低于比赛要求的 3600 秒\"]"));
        assertTrue(DurationSkipReport.matches(row(
                0.00,
                "[\"路演时长严重不足，无法进行有效评分\"]")));
    }

    @Test
    void realZeroWithoutDurationFingerprintStays() {
        assertFalse(DurationSkipReport.matches(
                0,
                "[\"仓库提交记录不足\", \"未展示对比测试\"]"));
        assertFalse(DurationSkipReport.matches(row(0, null)));
    }

    @Test
    void sqlKeepsRealZeroAndDropsDurationSkip() {
        String sql = DurationSkipReport.sqlNotSkipped("r");
        assertTrue(sql.contains("r.overall_score"));
        assertTrue(sql.contains("远低于比赛要求"));
        assertTrue(sql.contains("时长严重不足"));
        assertTrue(sql.contains("无法进行有效评分"));
        assertTrue(sql.contains("实际时长"));
        assertFalse(sql.contains("overall_score = 0 AND 1=1"));
    }

    @Test
    void sqlRejectsUnsafeAlias() {
        try {
            DurationSkipReport.sqlNotSkipped("r;drop");
            throw new AssertionError("expected illegal alias");
        } catch (IllegalArgumentException ignored) {
        }
    }

    @Test
    void scoredTapeIsNeverASkip() {
        assertFalse(DurationSkipReport.matches(
                43.2,
                "[\"路演实际时长 615 秒，远低于比赛要求的 3600 秒\"]"));
        assertFalse(DurationSkipReport.matches(row(48.3, "[\"O02\", \"O03\"]")));
    }

    private static Map<String, Object> row(double score, String issues) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("overallScore", score);
        row.put("criticalIssuesJson", issues);
        return row;
    }
}
