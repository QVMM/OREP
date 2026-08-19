package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class StudentLearningAnalyticsServiceTest {

    @Test
    @SuppressWarnings("unchecked")
    void weeklyLearningReturnsRollingLastSevenDaysAndSumsValidSessions() {
        // Wednesday 2026-07-22 → 近一周: 2026-07-16 … 2026-07-22
        LocalDate today = LocalDate.of(2026, 7, 22);
        List<Map<String, Object>> sessions = List.of(
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 20, 9, 0), "durationSeconds", 1800),
                Map.of("activityType", "EXAM", "startedAt", LocalDateTime.of(2026, 7, 20, 14, 0), "durationSeconds", 900),
                Map.of("activityType", "ROADSHOW", "startedAt", LocalDateTime.of(2026, 7, 21, 19, 0), "durationSeconds", 3600),
                Map.of("activityType", "COLLABORATION", "startedAt", LocalDateTime.of(2026, 7, 22, 10, 0), "durationSeconds", 0),
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 22, 11, 0), "durationSeconds", -20),
                // future day relative to today — ignored
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 23, 11, 0), "durationSeconds", 600),
                // before rolling window (2026-07-15) — ignored
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 15, 11, 0), "durationSeconds", 9999),
                // inside rolling window (previous Sunday) — counted
                Map.of("activityType", "COURSE", "startedAt", LocalDateTime.of(2026, 7, 16, 11, 0), "durationSeconds", 1200)
        );

        Map<String, Object> result = StudentLearningAnalyticsService.weeklyFromSessions(sessions, today);
        List<Map<String, Object>> daily = (List<Map<String, Object>>) result.get("daily");

        assertEquals("2026-07-16", result.get("weekStart"));
        assertEquals("2026-07-22", result.get("weekEnd"));
        assertEquals("2026-07-22", result.get("serverDate"));
        // 1800+900 + 3600 + 1200 = 7500
        assertEquals(7500L, result.get("totalSeconds"));
        assertEquals(3L, result.get("activeDays"));
        assertEquals(7, daily.size());
        assertEquals("2026-07-16", daily.get(0).get("date"));
        assertEquals(1200L, daily.get(0).get("durationSeconds"));
        // index 4 = 2026-07-20
        assertEquals(2700L, daily.get(4).get("durationSeconds"));
        // index 5 = 2026-07-21
        assertEquals(3600L, daily.get(5).get("durationSeconds"));
        // index 6 = today, zero (invalid sessions only)
        assertEquals(0L, daily.get(6).get("durationSeconds"));
        assertEquals("2026-07-22", daily.get(6).get("date"));
    }
}
