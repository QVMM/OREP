package com.orep.backend.service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * One row per docket. The first row wins (caller must sort latest-first).
 * Sessions without a docket stay as their own row.
 */
public final class ReportSummaryCollapser {
    private ReportSummaryCollapser() {
    }

    public static List<Map<String, Object>> collapse(List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return List.of();
        }
        Map<String, Map<String, Object>> seen = new LinkedHashMap<>();
        for (Map<String, Object> row : rows) {
            if (row == null || DurationSkipReport.matches(row)) {
                continue;
            }
            String docketId = text(row.get("docketId"));
            String key = !docketId.isBlank()
                    ? "docket:" + docketId
                    : firstNonBlank(
                    text(row.get("sessionId")),
                    "report-" + text(row.get("reportId")),
                    "meeting-" + text(row.get("meetingId"))
            );
            if (key.isBlank()) {
                continue;
            }
            Map<String, Object> existing = seen.get(key);
            if (existing == null) {
                Map<String, Object> copy = new LinkedHashMap<>(row);
                if (!docketId.isBlank()) {
                    copy.put("runCount", 1);
                }
                seen.put(key, copy);
            } else if (!docketId.isBlank()) {
                existing.put("runCount", intValue(existing.get("runCount")) + 1);
            }
        }
        return new ArrayList<>(seen.values());
    }

    private static int intValue(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        return 1;
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value;
            }
        }
        return "";
    }
}
