package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
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

/**
 * 学生端训练营任务提交断点测试。
 * 每个用例对应一条真实提交链路上的失败闸门，便于无录屏时回归。
 */
class TrainingTaskSubmitBreakpointTest {
    private JdbcTemplate jdbc;
    private ProjectTeamService service;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        service = new ProjectTeamService(
                jdbc,
                mock(RoadshowMemoryAnalyzer.class),
                mock(AiResultEvidenceAnchorExtractor.class),
                mock(RecordingEvidenceAnchorBuilder.class),
                mock(ScoreEvidenceAnchorStore.class),
                mock(CompetitionReadinessService.class),
                new TrainingDayAvailabilityService(Clock.fixed(
                        Instant.parse("2026-08-12T02:00:00Z"),
                        ZoneId.of("Asia/Shanghai")
                )),
                "./uploads"
        );
    }

    @Nested
    @DisplayName("BP1 训练日未开放 / 未发布")
    class AvailabilityGate {
        @Test
        void futurePublishedDayIsLocked() {
            stubCommonAccess();
            stubTrainingDayLink(LocalDate.of(2099, 1, 2), "PUBLISHED");

            ResponseStatusException error = assertThrows(
                    ResponseStatusException.class,
                    () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of("content", "成果"))
            );

            assertEquals(HttpStatus.LOCKED, error.getStatusCode());
            assertEquals("训练日尚未开放", error.getReason());
            verify(jdbc, never()).update(contains("INSERT INTO project_task_submission"), any(Object[].class));
        }

        @Test
        void draftDayIsLockedAsNotPublished() {
            stubCommonAccess();
            stubTrainingDayLink(LocalDate.of(2026, 8, 12), "DRAFT");

            ResponseStatusException error = assertThrows(
                    ResponseStatusException.class,
                    () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of("content", "成果"))
            );

            assertEquals(HttpStatus.LOCKED, error.getStatusCode());
            assertEquals("训练日尚未发布", error.getReason());
        }
    }

    @Nested
    @DisplayName("BP2 权限闸门")
    class PermissionGate {
        @Test
        void outsiderCannotSubmitOtherTeamTask() {
            when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
                String sql = invocation.getArgument(0);
                if (sql.equals("SELECT team_id FROM project_task WHERE id = ?")) {
                    return List.of(Map.of("team_id", 9L));
                }
                if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                    return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
                }
                if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                    return List.of();
                }
                return List.of();
            });

            ResponseStatusException error = assertThrows(
                    ResponseStatusException.class,
                    () -> service.submitTask(61L, 7L, 99L, "STUDENT", Map.of("content", "成果"))
            );

            assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        }
    }

    @Nested
    @DisplayName("BP4 必学未完成")
    class RequiredLearningGate {
        @Test
        void incompleteRequiredLearningBlocksSubmit() {
            stubCommonAccess();
            stubTrainingDayLink(LocalDate.of(2026, 8, 1), "CLOSED");
            when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                    .thenAnswer(invocation -> {
                        String sql = invocation.getArgument(0);
                        if (sql.contains("training_day_learning_resource")) return 2;
                        return 1;
                    });
            when(jdbc.queryForList(contains("FROM project_task t"), any(Object[].class)))
                    .thenReturn(List.of(new java.util.LinkedHashMap<>(Map.of(
                            "id", 61L,
                            "teamId", 9L,
                            "title", "训练任务",
                            "ownerUserId", 23L
                    ))));

            ResponseStatusException error = assertThrows(
                    ResponseStatusException.class,
                    () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of("content", "成果"))
            );

            assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
            assertTrue(error.getReason().contains("必学内容未完成"));
        }
    }

    @Nested
    @DisplayName("BP3 空成果闸门")
    class EmptyPayloadGate {
        @Test
        void openDayRejectsEmptyContentWithoutAssetsOrLinks() {
            stubCommonAccess();
            stubTrainingDayLink(LocalDate.of(2026, 8, 1), "CLOSED");
            when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                    .thenAnswer(invocation -> {
                        String sql = invocation.getArgument(0);
                        if (sql.contains("training_day_learning_resource")) return 0;
                        return 1;
                    });
            when(jdbc.queryForList(contains("FROM project_task t"), any(Object[].class)))
                    .thenReturn(List.of(new java.util.LinkedHashMap<>(Map.of(
                            "id", 61L,
                            "teamId", 9L,
                            "title", "训练任务",
                            "ownerUserId", 23L
                    ))));

            ResponseStatusException error = assertThrows(
                    ResponseStatusException.class,
                    () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of())
            );

            assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
            assertEquals("请填写提交说明、成果链接或上传成果文件", error.getReason());
        }
    }

    private void stubCommonAccess() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.equals("SELECT team_id FROM project_task WHERE id = ?")) {
                return List.of(Map.of("team_id", 9L));
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                return List.of(Map.of("role_in_team", "MEMBER"));
            }
            return List.of();
        });
    }

    private void stubTrainingDayLink(LocalDate trainingDate, String status) {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.equals("SELECT team_id FROM project_task WHERE id = ?")) {
                return List.of(Map.of("team_id", 9L));
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                return List.of(Map.of("role_in_team", "MEMBER"));
            }
            if (sql.contains("FROM training_day_task dt")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", trainingDate,
                        "status", status
                ));
            }
            return List.of();
        });
    }
}
