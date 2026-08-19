package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TeacherPortalServiceScopeTest {
    private static final TrainingDayAvailabilityService FIXED_AVAILABILITY =
            new TrainingDayAvailabilityService(Clock.fixed(
                    Instant.parse("2026-07-24T02:00:00Z"),
                    ZoneId.of("Asia/Shanghai")
            ));

    @Test
    void unassignedTeacherGetsEmptyWorkbenchInsteadOfTenantDefaults() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenReturn(List.of());
        TeacherPortalService service = new TeacherPortalService(
                jdbc,
                new ObjectMapper(),
                mock(TrainingDayContentService.class),
                mock(NotificationService.class),
                new TrainingDayAvailabilityService(),
                mock(PlaybackLibraryService.class),
                mock(StudentLearningAnalyticsService.class)
        );

        Map<String, Object> workbench = service.workbench(7L, 88L, "TEACHER");

        assertTrue(((Map<?, ?>) workbench.get("camp")).isEmpty());
        assertEquals(0, workbench.get("pendingReviews"));
        assertEquals(0, workbench.get("runningMeetings"));
        assertEquals(0, workbench.get("aiTodos"));
        assertEquals(List.of(), workbench.get("timeline"));
        verify(jdbc, never()).queryForObject(anyString(), eq(Integer.class), any(Object[].class));
    }

    @Test
    void assignedTeacherCanEarlyUnlockPublishedDayWithinTeamScope() {
        JdbcTemplate jdbc = scopedTeacherJdbc("PUBLISHED");
        TeacherPortalService service = service(jdbc);

        Map<String, Object> day = service.earlyUnlockTrainingDay(7L, 88L, "TEACHER", 51L);

        assertEquals(false, day.get("locked"));
        assertEquals(true, day.get("published"));
        verify(jdbc).update(
                contains("SET early_unlocked_at"),
                any(java.time.LocalDateTime.class),
                eq(51L)
        );
    }

    @Test
    void draftDayCannotBeEarlyUnlocked() {
        JdbcTemplate jdbc = scopedTeacherJdbc("DRAFT");
        TeacherPortalService service = service(jdbc);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.earlyUnlockTrainingDay(7L, 88L, "TEACHER", 51L)
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        verify(jdbc, never()).update(contains("SET early_unlocked_at"), any(Object[].class));
    }

    @Test
    void restoringAutomaticUnlockOnlyClearsEarlyUnlockTimestamp() {
        JdbcTemplate jdbc = scopedTeacherJdbc("PUBLISHED");
        TeacherPortalService service = service(jdbc);

        service.restoreAutomaticUnlock(7L, 88L, "TEACHER", 51L);

        verify(jdbc).update(contains("SET early_unlocked_at = NULL"), eq(51L));
        verify(jdbc, never()).update(contains("project_task"), any(Object[].class));
        verify(jdbc, never()).update(contains("project_task_submission"), any(Object[].class));
    }

    @ParameterizedTest
    @ValueSource(strings = {"DRAFT", "CLOSED"})
    void automaticUnlockCannotBeRestoredForUnpublishedDay(String status) {
        JdbcTemplate jdbc = scopedTeacherJdbc(status);
        TeacherPortalService service = service(jdbc);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.restoreAutomaticUnlock(7L, 88L, "TEACHER", 51L)
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        verify(jdbc, never()).update(contains("SET early_unlocked_at = NULL"), any(Object[].class));
    }

    @Test
    void teacherCannotUnlockSharedCampUnlessEveryActiveTeamIsInScope() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp_team")) return List.of(101L, 102L);
            return List.of(101L);
        });
        when(jdbc.queryForList(contains("FROM training_day d"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "dayId", 51L,
                        "campId", 31L,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", "PUBLISHED"
                )));
        TeacherPortalService service = service(jdbc);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.earlyUnlockTrainingDay(7L, 88L, "TEACHER", 51L)
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        verify(jdbc, never()).update(contains("SET early_unlocked_at"), any(Object[].class));
    }

    @Test
    void currentCampSelectionUsesInjectedShanghaiDateAsSqlParameter() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        java.util.concurrent.atomic.AtomicReference<String> campSql =
                new java.util.concurrent.atomic.AtomicReference<>();
        java.util.concurrent.atomic.AtomicReference<Object[]> campArgs =
                new java.util.concurrent.atomic.AtomicReference<>();
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class)))
                .thenReturn(List.of(101L));
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c") && sql.contains("LIMIT 1")) {
                campSql.set(sql);
                campArgs.set(java.util.Arrays.copyOfRange(
                        invocation.getArguments(),
                        1,
                        invocation.getArguments().length
                ));
            }
            return List.of();
        });

        service(jdbc).campOverview(7L, 88L, "TEACHER");

        assertFalse(campSql.get().contains("CURRENT_DATE"));
        assertEquals(
                LocalDate.of(2026, 7, 24),
                campArgs.get()[campArgs.get().length - 1]
        );
    }

    private TeacherPortalService service(JdbcTemplate jdbc) {
        return new TeacherPortalService(
                jdbc,
                new ObjectMapper(),
                mock(TrainingDayContentService.class),
                mock(NotificationService.class),
                FIXED_AVAILABILITY,
                mock(PlaybackLibraryService.class),
                mock(StudentLearningAnalyticsService.class)
        );
    }

    private JdbcTemplate scopedTeacherJdbc(String dayStatus) {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class)))
                .thenReturn(List.of(101L));
        when(jdbc.queryForList(contains("FROM training_day d"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "dayId", 51L,
                        "campId", 31L,
                        "teamId", 101L,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", dayStatus
                )));
        return jdbc;
    }
}
