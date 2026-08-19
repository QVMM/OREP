package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * Prior-round tasks for closureRate. Pipeline verify without hung/pipeline evidence
 * is not accepted. Hung evidence alone is also not accepted.
 */
public final class TaskBookPriorTasks {
    private TaskBookPriorTasks() {
    }

    public static List<ScoreGapCalculator.PriorTask> from(TaskBook previous, List<Map<String, Object>> verifications) {
        if (previous == null || previous.getItems() == null || previous.getItems().isEmpty()) {
            return List.of();
        }
        List<Map<String, Object>> rows = verifications == null ? List.of() : verifications;
        List<ScoreGapCalculator.PriorTask> tasks = new ArrayList<>();
        for (TaskBookItem item : previous.getItems()) {
            if (item == null) {
                continue;
            }
            ScoreGapCalculator.PriorTask task = new ScoreGapCalculator.PriorTask();
            Map<String, Object> matched = matchVerification(item, rows);
            boolean passed = matched != null && Boolean.TRUE.equals(matched.get("minimumAcceptancePassed"))
                    && "verified".equalsIgnoreCase(text(matched.get("status")));
            boolean pipelineEvidence = matched != null && Boolean.TRUE.equals(matched.get("fullScoreCriteriaPassed"));
            boolean hung = TaskBookHang.hasHungEvidence(item);
            task.evidenceAttached = hung || pipelineEvidence;
            task.accepted = passed && task.evidenceAttached;
            task.expectedGainPoints = parseExpectedGain(item.getExpectedGain());
            tasks.add(task);
        }
        return tasks;
    }

    static Map<String, Object> matchVerification(TaskBookItem item, List<Map<String, Object>> rows) {
        String title = item.getTitle() == null ? "" : item.getTitle();
        List<String> refs = item.getSourceRefs() == null ? List.of() : item.getSourceRefs();
        for (Map<String, Object> row : rows) {
            if (row == null) {
                continue;
            }
            String haystack = (text(row.get("reason")) + " " + text(row.get("taskRecordId"))).toLowerCase(Locale.ROOT);
            if (hasText(title) && haystack.contains(title.toLowerCase(Locale.ROOT))) {
                return row;
            }
            for (String ref : refs) {
                if (hasText(ref) && haystack.contains(ref.toLowerCase(Locale.ROOT))) {
                    return row;
                }
            }
        }
        return null;
    }

    private static BigDecimal parseExpectedGain(String expectedGain) {
        if (expectedGain == null || expectedGain.isBlank()) {
            return null;
        }
        String digits = expectedGain.replaceAll("[^0-9.]", " ").trim();
        if (digits.isEmpty()) {
            return null;
        }
        String first = digits.split("\\s+")[0];
        try {
            return new BigDecimal(first);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private static String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }
}
