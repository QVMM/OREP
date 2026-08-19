package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrainingDayAvailabilityServiceTest {
    private static final ZoneId SHANGHAI = ZoneId.of("Asia/Shanghai");
    private final TrainingDayAvailabilityService service = new TrainingDayAvailabilityService(
            Clock.fixed(Instant.parse("2026-07-24T02:00:00Z"), SHANGHAI)
    );

    @Test
    void draftIsAlwaysLockedEvenWhenEarlyUnlockTimestampExists() {
        LocalDateTime earlyUnlockedAt = LocalDateTime.of(2026, 7, 23, 9, 0);

        Map<String, Object> result = service.availability(
                "DRAFT",
                LocalDate.of(2026, 7, 24),
                earlyUnlockedAt
        );

        assertFalse((Boolean) result.get("published"));
        assertTrue((Boolean) result.get("locked"));
        assertEquals("NOT_PUBLISHED", result.get("lockReason"));
        assertEquals(LocalDateTime.of(2026, 7, 24, 0, 0), result.get("scheduledUnlockAt"));
        assertEquals(earlyUnlockedAt, result.get("earlyUnlockedAt"));
        assertEquals(earlyUnlockedAt, result.get("effectiveUnlockAt"));
    }

    @Test
    void futurePublishedDayUsesShanghaiMidnightAsScheduledUnlock() {
        Map<String, Object> result = service.availability(
                "PUBLISHED",
                LocalDate.of(2026, 7, 25),
                null
        );

        assertTrue((Boolean) result.get("published"));
        assertTrue((Boolean) result.get("locked"));
        assertEquals("SCHEDULED", result.get("lockReason"));
        assertEquals(LocalDateTime.of(2026, 7, 25, 0, 0), result.get("scheduledUnlockAt"));
        assertNull(result.get("earlyUnlockedAt"));
        assertEquals(LocalDateTime.of(2026, 7, 25, 0, 0), result.get("effectiveUnlockAt"));
    }

    @Test
    void publishedDayIsOpenFromShanghaiMidnight() {
        Map<String, Object> result = service.availability(
                "PUBLISHED",
                LocalDate.of(2026, 7, 24),
                null
        );

        assertFalse((Boolean) result.get("locked"));
        assertNull(result.get("lockReason"));
    }

    @Test
    void earlyUnlockImmediatelyOpensFuturePublishedDay() {
        LocalDateTime earlyUnlockedAt = LocalDateTime.of(2026, 7, 24, 9, 30);

        Map<String, Object> result = service.availability(
                "PUBLISHED",
                LocalDate.of(2026, 7, 30),
                earlyUnlockedAt
        );

        assertFalse((Boolean) result.get("locked"));
        assertNull(result.get("lockReason"));
        assertEquals(earlyUnlockedAt, result.get("effectiveUnlockAt"));
    }

    @Test
    void closedDayRemainsPublishedAndAccessibleAsHistory() {
        Map<String, Object> result = service.availability(
                "CLOSED",
                LocalDate.of(2026, 7, 23),
                null
        );

        assertTrue((Boolean) result.get("published"));
        assertFalse((Boolean) result.get("locked"));
        assertNull(result.get("lockReason"));
    }

    @Test
    void futureClosedDayRemainsLockedUntilItsSchedule() {
        Map<String, Object> result = service.availability(
                "CLOSED",
                LocalDate.of(2099, 1, 2),
                null
        );

        assertTrue((Boolean) result.get("published"));
        assertTrue((Boolean) result.get("locked"));
        assertEquals("SCHEDULED", result.get("lockReason"));
    }
}
