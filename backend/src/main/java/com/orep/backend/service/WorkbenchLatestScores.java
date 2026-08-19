package com.orep.backend.service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Teacher workbench "latest scores": one row per docket, latest-first.
 * Reruns of the same tape do not occupy five slots.
 */
public final class WorkbenchLatestScores {
    private WorkbenchLatestScores() {
    }

    public static List<Map<String, Object>> assemble(List<Map<String, Object>> latestFirst, int limit) {
        List<Map<String, Object>> collapsed = ReportSummaryCollapser.collapse(latestFirst);
        Map<Long, Double> lastByTeam = new LinkedHashMap<>();
        Map<Object, Double> deltaByReport = new LinkedHashMap<>();
        List<Map<String, Object>> chronological = new ArrayList<>(collapsed);
        chronological.sort(Comparator.comparing(row -> String.valueOf(row.get("scoredAt"))));
        for (Map<String, Object> row : chronological) {
            Long teamId = longValue(row.get("teamId"));
            Double score = decimal(row.get("score") != null ? row.get("score") : row.get("overallScore"));
            if (teamId == null || score == null) {
                continue;
            }
            Object reportId = row.get("reportId");
            if (lastByTeam.containsKey(teamId)) {
                deltaByReport.put(reportId, score - lastByTeam.get(teamId));
            } else {
                deltaByReport.put(reportId, 0.0);
            }
            lastByTeam.put(teamId, score);
        }

        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> row : collapsed) {
            Map<String, Object> item = new LinkedHashMap<>();
            Long reportId = longValue(row.get("reportId"));
            Double score = decimal(row.get("score") != null ? row.get("score") : row.get("overallScore"));
            double safeScore = score == null ? 0.0 : score;
            item.put("reportId", reportId);
            item.put("sessionId", row.get("sessionId"));
            item.put("docketId", row.get("docketId"));
            item.put("teamId", row.get("teamId"));
            item.put("studentName", row.get("teamName") != null ? row.get("teamName") : row.get("studentName"));
            item.put("title", firstNonBlank(text(row.get("meetingTitle")), text(row.get("title"))));
            item.put("score", safeScore);
            item.put("delta", Math.round(deltaByReport.getOrDefault(row.get("reportId"), 0.0)));
            int runCount = intValue(row.get("runCount"));
            item.put("attemptNo", runCount > 0 ? runCount : 1);
            item.put("runCount", runCount > 0 ? runCount : null);
            item.put("scoredAt", row.get("scoredAt"));
            Object hungDisplay = row.get("hungDisplay");
            if (hungDisplay != null && !String.valueOf(hungDisplay).isBlank()) {
                item.put("hungDisplay", String.valueOf(hungDisplay).trim());
            }
            out.add(item);
            if (out.size() >= limit) {
                break;
            }
        }
        return out;
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        return 0;
    }

    private static Long longValue(Object value) {
        if (value instanceof Number number) {
            return number.longValue();
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

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static String firstNonBlank(String left, String right) {
        if (left != null && !left.isBlank()) {
            return left;
        }
        if (right != null && !right.isBlank()) {
            return right;
        }
        return "";
    }
}
