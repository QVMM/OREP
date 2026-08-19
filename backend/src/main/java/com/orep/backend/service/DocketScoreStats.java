package com.orep.backend.service;

import java.util.List;
import java.util.Map;

/**
 * Count and average official scores by docket, not by rerun.
 * Sessions without a docket stay as their own identity.
 */
public final class DocketScoreStats {
    private DocketScoreStats() {
    }

    public static String identitySql(String sessionAlias) {
        String alias = sessionAlias == null || sessionAlias.isBlank() ? "s" : sessionAlias;
        return "COALESCE(NULLIF(" + alias + ".docket_id, ''), CONCAT('s', " + alias + ".id))";
    }

    /**
     * Keep only the newest completed report of each docket (or of the session if no docket).
     */
    public static String latestReportOnlySql(String reportAlias, String sessionAlias) {
        String report = reportAlias == null || reportAlias.isBlank() ? "r" : reportAlias;
        String session = sessionAlias == null || sessionAlias.isBlank() ? "s" : sessionAlias;
        return report + ".id = ("
                + "SELECT r2.id FROM ai_score_report r2 "
                + "LEFT JOIN ai_scoring_session s2 ON s2.id = r2.session_id "
                + "WHERE r2.status = 'completed' "
                + "AND COALESCE(NULLIF(s2.docket_id, ''), CONCAT('s', s2.id)) = "
                + "COALESCE(NULLIF(" + session + ".docket_id, ''), CONCAT('s', " + session + ".id)) "
                + "ORDER BY COALESCE(r2.completed_at, r2.created_at) DESC, r2.id DESC LIMIT 1)";
    }

    public record Summary(int count, Double average, Double latest) {
    }

    public static Summary summarize(List<Map<String, Object>> latestFirst) {
        List<Map<String, Object>> collapsed = ReportSummaryCollapser.collapse(latestFirst);
        if (collapsed.isEmpty()) {
            return new Summary(0, null, null);
        }
        double sum = 0;
        int n = 0;
        Double latest = null;
        for (Map<String, Object> row : collapsed) {
            Double score = decimal(first(row, "score", "overallScore", "officialScore"));
            if (score == null) {
                continue;
            }
            if (latest == null) {
                latest = score;
            }
            sum += score;
            n++;
        }
        Double average = n == 0 ? null : Math.round(sum / n * 10.0) / 10.0;
        return new Summary(collapsed.size(), average, latest);
    }

    private static Object first(Map<String, Object> row, String... keys) {
        for (String key : keys) {
            if (row.containsKey(key) && row.get(key) != null) {
                return row.get(key);
            }
        }
        return null;
    }

    private static Double decimal(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value == null) {
            return null;
        }
        try {
            return Double.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }
}
