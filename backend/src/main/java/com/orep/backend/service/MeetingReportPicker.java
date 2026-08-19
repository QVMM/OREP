package com.orep.backend.service;

import com.orep.backend.entity.AiScoreReport;

import java.util.Comparator;
import java.util.List;
import java.util.Objects;

/**
 * After uk_meeting was dropped, a meeting can have many reports.
 * Current authority is the latest completed report, then the latest row.
 */
public final class MeetingReportPicker {
    private MeetingReportPicker() {
    }

    public static AiScoreReport current(List<AiScoreReport> reports) {
        if (reports == null || reports.isEmpty()) {
            return null;
        }
        return reports.stream()
                .filter(Objects::nonNull)
                .max(Comparator
                        .comparing((AiScoreReport report) -> "completed".equals(report.getStatus()) ? 1 : 0)
                        .thenComparing(AiScoreReport::getCompletedAt, Comparator.nullsFirst(Comparator.naturalOrder()))
                        .thenComparing(AiScoreReport::getId, Comparator.nullsFirst(Comparator.naturalOrder())))
                .orElse(null);
    }
}
