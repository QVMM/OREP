package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class StudentTrainingServiceAvailabilityTest {
    private static final ZoneId SHANGHAI = ZoneId.of("Asia/Shanghai");
    private static final LocalDate FIXED_TODAY = LocalDate.of(2026, 7, 24);
    private JdbcTemplate jdbc;
    private TrainingDayLearningResourceService learningService;
    private StudentTrainingService service;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        learningService = mock(TrainingDayLearningResourceService.class);
        service = new StudentTrainingService(
                jdbc,
                mock(TrainingDayContentService.class),
                learningService,
                new TrainingDayAvailabilityService(
                        Clock.fixed(Instant.parse("2026-07-24T02:00:00Z"), SHANGHAI)
                ),
                mock(ProjectTeamService.class)
        );
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenReturn(List.of());
    }

    @Test
    void planIncludesDraftAsLockedPlaceholderWithoutStudentOperableContent() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "campName", "暑期集训",
                        "startDate", LocalDate.of(2026, 7, 24),
                        "endDate", LocalDate.of(2026, 7, 30),
                        "totalDays", 7,
                        "teamId", 9L
                ));
            }
            if (sql.contains("FROM training_camp_week")) {
                return List.of(Map.of(
                        "weekId", 41L,
                        "weekNo", 1,
                        "title", "第一周"
                ));
            }
            if (sql.contains("FROM training_day d") && sql.contains("submitted")) {
                if (sql.contains("status <> 'DRAFT'")) return List.of();
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "dayId", 51L,
                        "weekId", 41L,
                        "dayNo", 1,
                        "trainingDate", LocalDate.of(2026, 7, 25),
                        "title", "待发布训练日",
                        "status", "DRAFT"
                )));
            }
            if (sql.contains("JOIN training_day_task dt")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "taskId", 61L,
                        "title", "不应暴露的任务"
                ));
            }
            return List.of();
        });
        when(learningService.summaries(any(), any())).thenReturn(Map.of(
                51L, Map.of("learningResourceCount", 2)
        ));

        Map<String, Object> result = service.plan(7L, 23L);

        List<?> weeks = (List<?>) result.get("weeks");
        Map<?, ?> day = (Map<?, ?>) ((List<?>) ((Map<?, ?>) weeks.get(0)).get("days")).get(0);
        assertEquals(true, day.get("locked"));
        assertEquals(false, day.get("published"));
        assertEquals("NOT_PUBLISHED", day.get("lockReason"));
        assertFalse(day.containsKey("title"));
        assertFalse(day.containsKey("summary"));
        assertFalse(day.containsKey("dueAt"));
        assertFalse(day.containsKey("tasks"));
        assertFalse(day.containsKey("taskCount"));
        assertFalse(day.containsKey("learningResourceCount"));
    }

    @Test
    void dayReturnsLockedForFuturePublishedDayBeforeLoadingTaskContent() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "startDate", LocalDate.of(2099, 1, 1),
                        "endDate", LocalDate.of(2099, 1, 7),
                        "totalDays", 7,
                        "teamId", 9L
                ));
            }
            if (sql.contains("WHERE d.id = ?")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", "PUBLISHED",
                        "title", "未来训练日"
                ));
            }
            return List.of();
        });

        Map<String, Object> day = service.day(7L, 23L, 51L);

        assertEquals(true, day.get("locked"));
        assertEquals(List.of(), day.get("tasks"));
        assertTrue(String.valueOf(day.get("message")).contains("尚未开放"));
    }

    @Test
    void draftDayReturnsLockedInsteadOfNotFound() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "startDate", LocalDate.of(2026, 7, 1),
                        "endDate", LocalDate.of(2026, 7, 31),
                        "totalDays", 31,
                        "teamId", 9L
                ));
            }
            if (sql.contains("WHERE d.id = ?") && !sql.contains("status <> 'DRAFT'")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", LocalDate.of(2026, 7, 24),
                        "status", "DRAFT",
                        "title", "草稿训练日"
                ));
            }
            return List.of();
        });

        Map<String, Object> overview = service.dayOverview(7L, 23L, 51L);

        assertEquals(true, overview.get("locked"));
        assertTrue(String.valueOf(overview.get("message")).contains("未发布")
                || String.valueOf(overview.get("message")).contains("尚未发布"));
    }

    @Test
    void planKeepsUnassignedDaysWhenCampAlreadyHasWeeks() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "startDate", LocalDate.of(2026, 7, 24),
                        "endDate", LocalDate.of(2026, 7, 30),
                        "totalDays", 7,
                        "teamId", 9L
                ));
            }
            if (sql.contains("FROM training_camp_week")) {
                return List.of(Map.of("weekId", 41L, "weekNo", 1, "title", "第一周"));
            }
            if (sql.contains("FROM training_day d") && sql.contains("submitted")) {
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "dayId", 52L,
                        "dayNo", 2,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "title", "未分组训练日",
                        "status", "DRAFT"
                )));
            }
            return List.of();
        });
        when(learningService.summaries(any(), any())).thenReturn(Map.of());

        Map<String, Object> result = service.plan(7L, 23L);

        long returnedDays = ((List<?>) result.get("weeks")).stream()
                .mapToLong(week -> ((List<?>) ((Map<?, ?>) week).get("days")).size())
                .sum();
        assertEquals(1L, returnedDays);
    }

    @Test
    void planComputesDateProgressInJavaUsingShanghaiDate() {
        LocalDate today = FIXED_TODAY;
        java.util.concurrent.atomic.AtomicReference<String> daySql = new java.util.concurrent.atomic.AtomicReference<>();
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "startDate", today.minusDays(1),
                        "endDate", today.plusDays(1),
                        "totalDays", 3,
                        "teamId", 9L
                ));
            }
            if (sql.contains("FROM training_day d") && sql.contains("submitted")) {
                daySql.set(sql);
                return List.of(
                        mutableDay(51L, 1, today.minusDays(1)),
                        mutableDay(52L, 2, today),
                        mutableDay(53L, 3, today.plusDays(1))
                );
            }
            return List.of();
        });
        when(learningService.summaries(any(), any())).thenReturn(Map.of());

        Map<String, Object> result = service.plan(7L, 23L);

        List<?> days = (List<?>) ((Map<?, ?>) ((List<?>) result.get("weeks")).get(0)).get("days");
        assertEquals(List.of("EXPIRED", "TODAY", "UPCOMING"), days.stream()
                .map(day -> ((Map<?, ?>) day).get("progressStatus"))
                .toList());
        assertFalse(daySql.get().contains("CURRENT_DATE"));
    }

    @Test
    void currentCampSelectionUsesInjectedShanghaiDateAsSqlParameter() {
        AtomicReference<String> campSql = new AtomicReference<>();
        AtomicReference<Object[]> campArgs = new AtomicReference<>();
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM training_camp c")) {
                campSql.set(sql);
                campArgs.set(java.util.Arrays.copyOfRange(
                        invocation.getArguments(),
                        1,
                        invocation.getArguments().length
                ));
            }
            return List.of();
        });

        service.currentCamp(7L, 23L);

        assertFalse(campSql.get().contains("CURRENT_DATE"));
        assertEquals(FIXED_TODAY, campArgs.get()[campArgs.get().length - 1]);
    }

    @Test
    void planAndDayScopeTrainingTasksToTheStudentsCurrentTeam() {
        AtomicReference<String> planTaskSql = new AtomicReference<>();
        AtomicReference<Object[]> planTaskArgs = new AtomicReference<>();
        AtomicReference<String> dayTaskSql = new AtomicReference<>();
        AtomicReference<Object[]> dayTaskArgs = new AtomicReference<>();
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            Object[] args = java.util.Arrays.copyOfRange(
                    invocation.getArguments(),
                    1,
                    invocation.getArguments().length
            );
            if (sql.contains("FROM training_camp c")) {
                return List.of(Map.of(
                        "campId", 31L,
                        "startDate", LocalDate.of(2026, 7, 1),
                        "endDate", LocalDate.of(2026, 7, 31),
                        "totalDays", 31,
                        "teamId", 9L
                ));
            }
            if (sql.contains("FROM training_day d") && sql.contains("submitted")) {
                return List.of(mutableDay(51L, 1, LocalDate.of(2026, 7, 1)));
            }
            if (sql.contains("WHERE d.id = ?")) {
                return List.of(mutableDay(51L, 1, LocalDate.of(2026, 7, 1)));
            }
            if (sql.contains("JOIN training_day_task dt") && sql.contains("d.camp_id")) {
                planTaskSql.set(sql);
                planTaskArgs.set(args);
                return List.of();
            }
            if (sql.contains("FROM training_day_task dt") && sql.contains("dt.training_day_id")) {
                dayTaskSql.set(sql);
                dayTaskArgs.set(args);
                return List.of();
            }
            return List.of();
        });
        when(learningService.summaries(any(), any())).thenReturn(Map.of());
        when(learningService.studentResources(7L, 23L, 51L)).thenReturn(List.of());

        service.plan(7L, 23L);
        service.day(7L, 23L, 51L);

        assertTrue(planTaskSql.get().contains("t.team_id = ?"));
        assertEquals(9L, planTaskArgs.get()[planTaskArgs.get().length - 1]);
        assertTrue(dayTaskSql.get().contains("t.team_id = ?"));
        assertEquals(9L, dayTaskArgs.get()[dayTaskArgs.get().length - 1]);
    }

    private Map<String, Object> mutableDay(Long dayId, int dayNo, LocalDate trainingDate) {
        Map<String, Object> day = new java.util.LinkedHashMap<>();
        day.put("dayId", dayId);
        day.put("weekId", null);
        day.put("dayNo", dayNo);
        day.put("trainingDate", trainingDate);
        day.put("title", "训练日 " + dayNo);
        day.put("status", "PUBLISHED");
        return day;
    }
}
