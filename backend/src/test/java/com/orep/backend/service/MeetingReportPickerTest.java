package com.orep.backend.service;

import com.orep.backend.entity.AiScoreReport;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class MeetingReportPickerTest {

    @Test
    void emptyListIsNull() {
        assertNull(MeetingReportPicker.current(List.of()));
        assertNull(MeetingReportPicker.current(null));
    }

    @Test
    void completedBeatsNewerProcessingAndUnorderedInsert() {
        AiScoreReport olderCompleted = report(11L, "completed", LocalDateTime.parse("2026-08-17T10:00:00"));
        AiScoreReport newerProcessing = report(12L, "processing", LocalDateTime.parse("2026-08-17T11:00:00"));
        assertEquals(11L, MeetingReportPicker.current(List.of(newerProcessing, olderCompleted)).getId());
    }

    @Test
    void laterCompletedWins() {
        AiScoreReport first = report(21L, "completed", LocalDateTime.parse("2026-08-17T10:00:00"));
        AiScoreReport second = report(22L, "completed", LocalDateTime.parse("2026-08-17T12:00:00"));
        assertEquals(22L, MeetingReportPicker.current(List.of(first, second)).getId());
    }

    @Test
    void missingCompletedAtFallsBackToId() {
        AiScoreReport first = report(31L, "completed", null);
        AiScoreReport second = report(32L, "completed", null);
        assertEquals(32L, MeetingReportPicker.current(List.of(first, second)).getId());
    }

    private static AiScoreReport report(Long id, String status, LocalDateTime completedAt) {
        AiScoreReport report = new AiScoreReport();
        report.setId(id);
        report.setMeetingId(9L);
        report.setStatus(status);
        report.setCompletedAt(completedAt);
        return report;
    }
}
