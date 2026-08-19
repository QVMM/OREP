package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DailyReportDatePolicyTest {

    private static final LocalDate TODAY = LocalDate.of(2026, 8, 13);

    @Test
    void yesterdayIsWritable() {
        assertEquals(LocalDate.of(2026, 8, 12),
                DailyReportDatePolicy.resolveWritableDate(TODAY, LocalDate.of(2026, 8, 12)));
    }

    @Test
    void futureDateClampsToToday() {
        assertEquals(TODAY, DailyReportDatePolicy.resolveWritableDate(TODAY, LocalDate.of(2026, 8, 20)));
    }

    @Test
    void olderThan14DaysIsRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> DailyReportDatePolicy.resolveWritableDate(TODAY, LocalDate.of(2026, 7, 1)));
        assertFalse(DailyReportDatePolicy.isBackfillAllowed(TODAY, LocalDate.of(2026, 7, 1)));
        assertTrue(DailyReportDatePolicy.isBackfillAllowed(TODAY, LocalDate.of(2026, 8, 12)));
    }
}
