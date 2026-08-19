package com.orep.backend.service;

import java.util.Collection;
import java.util.Map;

/**
 * Pipeline skip-LLM fingerprint: official 0 because the tape is shorter than 600s.
 * A real scored 0 must stay visible. Do not treat "score is 0" as discard.
 */
public final class DurationSkipReport {
    private DurationSkipReport() {
    }

    public static boolean matches(Map<String, Object> row) {
        if (row == null) {
            return false;
        }
        if (Boolean.TRUE.equals(row.get("durationSkip"))) {
            return true;
        }
        Object score = first(row, "overallScore", "overall_score", "score", "officialScore");
        Object issues = first(row, "criticalIssuesJson", "critical_issues_json", "issues");
        return matches(score, issues);
    }

    public static boolean matches(Object overallScore, Object issues) {
        if (!isZero(overallScore)) {
            return false;
        }
        String haystack = flatten(issues);
        if (haystack.isBlank()) {
            return false;
        }
        return haystack.contains("远低于比赛要求")
                || haystack.contains("时长严重不足")
                || haystack.contains("无法进行有效评分")
                || (haystack.contains("实际时长") && haystack.contains("秒") && haystack.contains("低于"));
    }

    /**
     * Keep rows that are not a duration-skip 0. Alias must be a simple SQL identifier.
     */
    public static String sqlNotSkipped(String reportAlias) {
        String alias = safeAlias(reportAlias);
        String issues = "CAST(" + alias + ".critical_issues_json AS CHAR)";
        return "("
                + alias + ".overall_score IS NULL OR " + alias + ".overall_score <> 0"
                + " OR ("
                + issues + " NOT LIKE '%远低于比赛要求%'"
                + " AND " + issues + " NOT LIKE '%时长严重不足%'"
                + " AND " + issues + " NOT LIKE '%无法进行有效评分%'"
                + " AND NOT ("
                + issues + " LIKE '%实际时长%' AND "
                + issues + " LIKE '%秒%' AND "
                + issues + " LIKE '%低于%'"
                + ")"
                + ")"
                + ")";
    }

    private static String safeAlias(String reportAlias) {
        if (reportAlias == null || !reportAlias.matches("[A-Za-z_][A-Za-z0-9_]*")) {
            throw new IllegalArgumentException("report alias");
        }
        return reportAlias;
    }

    private static boolean isZero(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue() == 0.0;
        }
        if (value == null) {
            return false;
        }
        try {
            return Double.parseDouble(String.valueOf(value).trim()) == 0.0;
        } catch (NumberFormatException ignored) {
            return false;
        }
    }

    private static Object first(Map<String, Object> row, String... keys) {
        for (String key : keys) {
            if (row.containsKey(key) && row.get(key) != null) {
                return row.get(key);
            }
        }
        return null;
    }

    private static String flatten(Object value) {
        if (value == null) {
            return "";
        }
        if (value instanceof Map<?, ?> map) {
            StringBuilder builder = new StringBuilder();
            for (Object item : map.values()) {
                builder.append(' ').append(flatten(item));
            }
            return builder.toString();
        }
        if (value instanceof Collection<?> collection) {
            StringBuilder builder = new StringBuilder();
            for (Object item : collection) {
                builder.append(' ').append(flatten(item));
            }
            return builder.toString();
        }
        return String.valueOf(value);
    }
}
