package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.PreparedStatementCreator;
import org.springframework.jdbc.support.KeyHolder;
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

class ProjectTeamServiceMembershipTest {
    private static final LocalDate FIXED_TODAY = LocalDate.of(2026, 7, 24);
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
                        Instant.parse("2026-07-24T02:00:00Z"),
                        ZoneId.of("Asia/Shanghai")
                )),
                "./uploads"
        );
    }

    @Test
    void myTeamsDoesNotAutoAssignUnboundStudentToExistingTeam() {
        when(jdbc.queryForObject(
                "SELECT COUNT(*) FROM project_team WHERE tenant_id = ?",
                Integer.class,
                7L
        )).thenReturn(1);
        when(jdbc.queryForObject(
                contains("JOIN project_team_member"),
                eq(Integer.class),
                eq(7L),
                eq(99L)
        )).thenReturn(0);
        when(jdbc.queryForObject(
                "SELECT id FROM project_team WHERE tenant_id = ? ORDER BY id LIMIT 1",
                Long.class,
                7L
        )).thenReturn(101L);
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenReturn(List.of());

        List<?> teams = service.myTeams(7L, 99L, "STUDENT");

        assertTrue(teams.isEmpty());
        verify(jdbc, never()).update(contains("INSERT IGNORE INTO project_team_member"), any(Object[].class));
    }

    @Test
    void myTeamsOnlyReturnsTeamsActuallyMentoredByTeacher() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenReturn(List.of());

        List<?> teams = service.myTeams(7L, 88L, "TEACHER");

        assertTrue(teams.isEmpty());
        verify(jdbc).queryForList(
                contains("t.mentor_id = ?"),
                eq(88L), eq(7L), eq(88L), eq(88L)
        );
    }

    @Test
    void createTeamDoesNotSeedPlaceholderTasksOrMaterials() {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(1);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenReturn(List.of());
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM track_rubric_config")) {
                return List.of(Map.of(
                        "trackId", "track-it",
                        "trackName", "新一代信息技术赛道"
                ));
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of(
                        "id", 3L,
                        "tenantId", 7L,
                        "name", "新项目",
                        "status", "ACTIVE"
                ));
            }
            return List.of();
        });
        when(jdbc.update(any(PreparedStatementCreator.class), any(KeyHolder.class))).thenAnswer(invocation -> {
            KeyHolder keyHolder = invocation.getArgument(1);
            keyHolder.getKeyList().add(Map.of("id", 3L));
            return 1;
        });

        service.createTeam(7L, 88L, "TEACHER", Map.of(
                "name", "新项目",
                "captainUserId", 10L,
                "memberUserIds", List.of(11L, 12L),
                "trackId", "track-it",
                "startDate", "2026-07-22",
                "endDate", "2026-08-11"
        ));

        verify(jdbc, never()).update(contains("INSERT INTO project_task"), any(Object[].class));
        verify(jdbc, never()).update(contains("INSERT INTO project_material"), any(Object[].class));
    }

    @Test
    void addMemberUsesGlobalTeacherRoleAndCreatesMentorRelationship() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("TEACHER");
        when(jdbc.queryForList(contains("JOIN users u ON u.id = m.user_id"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "userId", 23L,
                        "username", "teacher02",
                        "systemRole", "TEACHER",
                        "roleInTeam", "MENTOR",
                        "positionName", "指导教师"
                )));

        Map<String, Object> member = service.addMember(
                9L, 7L, 88L, "TEACHER", Map.of("userId", 23L)
        );

        assertEquals("MENTOR", member.get("roleInTeam"));
        verify(jdbc).update(
                contains("VALUES (?, ?, 'MENTOR'"),
                eq(9L), eq(23L), eq("指导教师"), any(String.class)
        );
        verify(jdbc).update(
                contains("SET mentor_id = COALESCE(mentor_id, ?)"),
                eq(23L), eq(9L)
        );
        verify(jdbc, never()).update(
                contains("UPDATE users SET role = ?"),
                any(Object[].class)
        );
    }

    @Test
    void addMemberCanPromoteStudentToGlobalTeacherWhenExplicitlyRequested() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("STUDENT");
        when(jdbc.queryForList(contains("JOIN users u ON u.id = m.user_id"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "userId", 23L,
                        "username", "student01",
                        "systemRole", "TEACHER",
                        "roleInTeam", "MENTOR",
                        "positionName", "指导教师"
                )));

        service.addMember(
                9L, 7L, 88L, "TEACHER",
                Map.of("userId", 23L, "systemRole", "TEACHER")
        );

        verify(jdbc).update(
                "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                "TEACHER", 7L, 23L
        );
        verify(jdbc).update(
                contains("VALUES (?, ?, 'MENTOR'"),
                eq(9L), eq(23L), eq("指导教师"), any(String.class)
        );
    }

    @Test
    void addMemberUsesGlobalStudentRoleAndCreatesRegularMemberRelationship() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("STUDENT");
        when(jdbc.queryForList(contains("JOIN users u ON u.id = m.user_id"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "userId", 23L,
                        "username", "student01",
                        "systemRole", "STUDENT",
                        "roleInTeam", "MEMBER",
                        "positionName", "项目成员"
                )));

        Map<String, Object> member = service.addMember(
                9L, 7L, 88L, "TEACHER", Map.of("userId", 23L)
        );

        assertEquals("MEMBER", member.get("roleInTeam"));
        verify(jdbc).update(
                contains("VALUES (?, ?, 'MEMBER'"),
                eq(9L), eq(23L), eq("项目成员"), any(String.class)
        );
        verify(jdbc, never()).update(
                contains("SET mentor_id = COALESCE(mentor_id, ?)"),
                any(Object[].class)
        );
    }

    @Test
    void updateMemberRoleSynchronizesTeacherToStudentAndTeamMember() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("TEACHER");
        when(jdbc.queryForList(
                "SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?",
                9L,
                23L
        )).thenReturn(List.of(Map.of("role_in_team", "MENTOR")));
        when(jdbc.queryForObject(
                contains("SELECT mentor_id FROM project_team"),
                eq(Long.class),
                eq(9L)
        )).thenReturn(88L);
        when(jdbc.queryForList(contains("JOIN users u ON u.id = m.user_id"), any(Object[].class)))
                .thenReturn(List.of(Map.of(
                        "userId", 23L,
                        "username", "teacher02",
                        "systemRole", "STUDENT",
                        "roleInTeam", "MEMBER",
                        "positionName", "项目成员"
                )));

        Map<String, Object> member = service.updateMemberPosition(
                9L, 23L, 7L, 88L, "TEACHER",
                Map.of("systemRole", "STUDENT", "positionName", "项目成员")
        );

        assertEquals("STUDENT", member.get("systemRole"));
        verify(jdbc).update(
                "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                "STUDENT", 7L, 23L
        );
        verify(jdbc).update(
                contains("SET role_in_team = ?, position_name = ?, responsibility = ?"),
                eq("MEMBER"), eq("项目成员"), any(String.class), eq(9L), eq(23L)
        );
    }

    @Test
    void updateMemberRoleRejectsPromotingCaptainToTeacher() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("STUDENT");
        when(jdbc.queryForList(
                "SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?",
                9L,
                23L
        )).thenReturn(List.of(Map.of("role_in_team", "CAPTAIN")));

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.updateMemberPosition(
                        9L, 23L, 7L, 88L, "TEACHER",
                        Map.of("systemRole", "TEACHER")
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verify(jdbc, never()).update(
                "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                "TEACHER", 7L, 23L
        );
    }

    @Test
    void updateMemberRoleRejectsDemotingOnlyPrimaryMentor() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("TEACHER");
        when(jdbc.queryForList(
                "SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?",
                9L,
                23L
        )).thenReturn(List.of(Map.of("role_in_team", "MENTOR")));
        when(jdbc.queryForObject(
                contains("SELECT mentor_id FROM project_team"),
                eq(Long.class),
                eq(9L)
        )).thenReturn(23L);
        when(jdbc.queryForList(
                contains("SELECT user_id FROM project_team_member"),
                eq(Long.class),
                eq(9L),
                eq(23L)
        )).thenReturn(List.of());

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.updateMemberPosition(
                        9L, 23L, 7L, 88L, "TEACHER",
                        Map.of("systemRole", "STUDENT")
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verify(jdbc, never()).update(
                "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                "STUDENT", 7L, 23L
        );
    }

    @Test
    void addMemberRejectsUnsupportedGlobalRoleOverride() {
        stubMemberManagementScope(88L);
        when(jdbc.queryForObject(
                "SELECT role FROM users WHERE tenant_id = ? AND id = ?",
                String.class,
                7L,
                23L
        )).thenReturn("STUDENT");

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.addMember(
                        9L, 7L, 88L, "TEACHER",
                        Map.of("userId", 23L, "systemRole", "ADMIN")
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verify(jdbc, never()).update(
                "UPDATE users SET role = ? WHERE tenant_id = ? AND id = ?",
                "ADMIN", 7L, 23L
        );
    }

    private void stubMemberManagementScope(Long operatorUserId) {
        when(jdbc.queryForList(
                contains("FROM project_team WHERE id = ? AND tenant_id = ?"),
                eq(9L),
                eq(7L)
        )).thenReturn(List.of(Map.of(
                "id", 9L,
                "tenantId", 7L,
                "name", "项目团队",
                "mentorId", operatorUserId
        )));
        when(jdbc.queryForObject(
                contains("SELECT COUNT(*)"),
                eq(Integer.class),
                any(Object[].class)
        )).thenReturn(1);
    }

    @Test
    void studentCannotSubmitTaskLinkedToLockedTrainingDay() {
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
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", "PUBLISHED"
                ));
            }
            return List.of();
        });

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of("content", "成果"))
        );

        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, never()).update(contains("INSERT INTO project_task_submission"), any(Object[].class));
    }

    @Test
    void studentCannotReadTaskDetailLinkedToLockedTrainingDay() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                return List.of(Map.of("role_in_team", "MEMBER"));
            }
            if (sql.contains("FROM training_day_task dt")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", "PUBLISHED"
                ));
            }
            return List.of();
        });

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.taskDetail(9L, 61L, 7L, 23L, "STUDENT")
        );

        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, never()).queryForList(contains("FROM project_task t"), any(Object[].class));
    }

    @Test
    void studentCanReadTaskReusedByAnyAccessibleTrainingDay() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                return List.of(Map.of("role_in_team", "MEMBER"));
            }
            if (sql.contains("FROM training_day_task dt")) {
                return List.of(
                        Map.of(
                                "dayId", 51L,
                                "trainingDate", LocalDate.of(2099, 1, 2),
                                "status", "PUBLISHED"
                        ),
                        Map.of(
                                "dayId", 52L,
                                "trainingDate", LocalDate.of(2026, 7, 1),
                                "status", "CLOSED"
                        )
                );
            }
            if (sql.contains("FROM project_task t") && sql.contains("WHERE t.id = ?")) {
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "id", 61L,
                        "teamId", 9L,
                        "title", "复用训练任务",
                        "ownerUserId", 23L
                )));
            }
            return List.of();
        });

        Map<String, Object> detail = service.taskDetail(9L, 61L, 7L, 23L, "STUDENT");

        assertEquals(61L, ((Map<?, ?>) detail.get("task")).get("id"));
    }

    @Test
    void studentSubmitUsesAnyAccessibleTrainingDayRule() {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(0);
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
                return List.of(
                        Map.of(
                                "dayId", 51L,
                                "trainingDate", LocalDate.of(2099, 1, 2),
                                "status", "PUBLISHED"
                        ),
                        Map.of(
                                "dayId", 52L,
                                "trainingDate", LocalDate.of(2026, 7, 1),
                                "status", "CLOSED"
                        )
                );
            }
            if (sql.contains("FROM project_task t") && sql.contains("WHERE t.id = ?")) {
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "id", 61L,
                        "teamId", 9L,
                        "title", "复用训练任务",
                        "ownerUserId", 23L
                )));
            }
            return List.of();
        });

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.submitTask(61L, 7L, 23L, "STUDENT", Map.of())
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
    }

    @Test
    void teacherCanReadLockedTrainingTaskWithoutStudentAvailabilityGuard() {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.contains("FROM project_team_member") && sql.contains("role_in_team = 'MENTOR'")) {
                return List.of(Map.of("id", 1L));
            }
            if (sql.contains("FROM project_task t") && sql.contains("WHERE t.id = ?")) {
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "id", 61L,
                        "teamId", 9L,
                        "title", "未来训练任务"
                )));
            }
            if (sql.contains("FROM training_day_task dt")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", LocalDate.of(2099, 1, 2),
                        "status", "PUBLISHED",
                        "title", "未来训练日",
                        "isPrimary", 1
                ));
            }
            return List.of();
        });

        Map<String, Object> detail = service.taskDetail(9L, 61L, 7L, 88L, "ADMIN");

        assertEquals(61L, ((Map<?, ?>) detail.get("task")).get("id"));
    }

    @Test
    void studentsFromEachCampTeamCanSubmitOnlyTheirOwnGeneratedTask() {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                .thenAnswer(invocation -> {
                    String sql = invocation.getArgument(0);
                    if (sql.contains("project_task_assignee")) return 1;
                    return 0;
                });
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            Object[] args = java.util.Arrays.copyOfRange(
                    invocation.getArguments(),
                    1,
                    invocation.getArguments().length
            );
            if (sql.equals("SELECT team_id FROM project_task WHERE id = ?")) {
                Long taskId = ((Number) args[0]).longValue();
                return List.of(Map.of("team_id", taskId == 61L ? 101L : 102L));
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                Long teamId = ((Number) args[0]).longValue();
                return List.of(Map.of("id", teamId, "tenantId", 7L, "name", "参训团队"));
            }
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                Long teamId = ((Number) args[0]).longValue();
                Long userId = ((Number) args[1]).longValue();
                boolean ownTeam = (teamId == 101L && userId == 201L)
                        || (teamId == 102L && userId == 202L);
                return ownTeam ? List.of(Map.of("role_in_team", "MEMBER")) : List.of();
            }
            if (sql.contains("FROM training_day_task dt")) {
                return List.of(Map.of(
                        "dayId", 51L,
                        "trainingDate", LocalDate.of(2026, 7, 1),
                        "status", "CLOSED"
                ));
            }
            if (sql.contains("FROM project_task t") && sql.contains("WHERE t.id = ?")) {
                Long taskId = ((Number) args[0]).longValue();
                Long ownerId = taskId == 61L ? 201L : 202L;
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "id", taskId,
                        "teamId", taskId == 61L ? 101L : 102L,
                        "title", "团队训练任务",
                        "ownerUserId", ownerId
                )));
            }
            return List.of();
        });

        ResponseStatusException firstTeam = assertThrows(
                ResponseStatusException.class,
                () -> service.submitTask(
                        61L, 7L, 201L, "STUDENT", Map.of()
                )
        );
        ResponseStatusException secondTeam = assertThrows(
                ResponseStatusException.class,
                () -> service.submitTask(
                        62L, 7L, 202L, "STUDENT", Map.of()
                )
        );
        ResponseStatusException crossTeam = assertThrows(
                ResponseStatusException.class,
                () -> service.submitTask(
                        62L, 7L, 201L, "STUDENT", Map.of()
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, firstTeam.getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST, secondTeam.getStatusCode());
        assertEquals(HttpStatus.FORBIDDEN, crossTeam.getStatusCode());
    }

    @Test
    void dashboardIncludesAllCurrentCampDaysAndOnlyExistingTaskLinks() {
        java.util.concurrent.atomic.AtomicReference<String> scheduleLinkSql =
                new java.util.concurrent.atomic.AtomicReference<>();
        java.util.concurrent.atomic.AtomicReference<Object[]> scheduleLinkArgs =
                new java.util.concurrent.atomic.AtomicReference<>();
        java.util.concurrent.atomic.AtomicReference<String> campSelectionSql =
                new java.util.concurrent.atomic.AtomicReference<>();
        java.util.concurrent.atomic.AtomicReference<Object[]> campSelectionArgs =
                new java.util.concurrent.atomic.AtomicReference<>();
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(0);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenReturn(List.of());
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.equals("SELECT role_in_team FROM project_team_member WHERE team_id = ? AND user_id = ?")) {
                return List.of(Map.of("role_in_team", "MEMBER"));
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 9L, "tenantId", 7L, "name", "项目团队"));
            }
            if (sql.contains("FROM training_camp c") && sql.contains("LIMIT 1")) {
                campSelectionSql.set(sql);
                campSelectionArgs.set(java.util.Arrays.copyOfRange(
                        invocation.getArguments(),
                        1,
                        invocation.getArguments().length
                ));
                return List.of(Map.of("campId", 31L, "campName", "当前集训营"));
            }
            if (sql.contains("FROM training_day d") && sql.contains("WHERE d.camp_id = ?")) {
                return List.of(
                        new java.util.LinkedHashMap<>(Map.of(
                                "dayId", 51L,
                                "dayNo", 1,
                                "trainingDate", LocalDate.of(2026, 7, 24),
                                "status", "PUBLISHED"
                        )),
                        new java.util.LinkedHashMap<>(Map.of(
                                "dayId", 52L,
                                "dayNo", 2,
                                "trainingDate", LocalDate.of(2099, 1, 2),
                                "status", "DRAFT",
                                "title", "不应泄露的草稿主题",
                                "summary", "不应泄露的草稿说明",
                                "dueAt", java.time.LocalDateTime.of(2099, 1, 2, 22, 0)
                        ))
                );
            }
            if (sql.contains("FROM training_day_task") && sql.contains("WHERE training_day_id IN")) {
                scheduleLinkSql.set(sql);
                scheduleLinkArgs.set(java.util.Arrays.copyOfRange(
                        invocation.getArguments(),
                        1,
                        invocation.getArguments().length
                ));
                return List.of(
                        Map.of("dayId", 51L, "taskId", 61L),
                        Map.of("dayId", 52L, "taskId", 62L)
                );
            }
            if (sql.contains("SELECT dt.task_id taskId")) {
                return List.of(
                        Map.of(
                                "taskId", 62L,
                                "trainingDate", LocalDate.of(2099, 1, 2),
                                "status", "PUBLISHED"
                        ),
                        Map.of(
                                "taskId", 63L,
                                "trainingDate", LocalDate.of(2099, 1, 3),
                                "status", "PUBLISHED"
                        ),
                        Map.of(
                                "taskId", 63L,
                                "trainingDate", LocalDate.of(2026, 7, 1),
                                "status", "CLOSED"
                        )
                );
            }
            if (sql.contains("FROM project_task t") && sql.contains("WHERE t.team_id = ?")) {
                return List.of(
                        mutableTask(61L, "普通项目任务", "普通任务说明"),
                        mutableTask(62L, "锁定训练任务", "不可泄露"),
                        mutableTask(63L, "多日复用任务", "已有可访问训练日")
                );
            }
            return List.of();
        });

        Map<String, Object> dashboard = service.dashboard(9L, 7L, 23L, "STUDENT");

        List<?> schedule = (List<?>) dashboard.get("trainingSchedule");
        List<?> tasks = (List<?>) dashboard.get("tasks");
        assertEquals(2, schedule.size());
        assertEquals(List.of(61L), ((Map<?, ?>) schedule.get(0)).get("taskIds"));
        assertFalse(((Map<?, ?>) schedule.get(1)).containsKey("taskIds"));
        assertFalse(((Map<?, ?>) schedule.get(1)).containsKey("title"));
        assertFalse(((Map<?, ?>) schedule.get(1)).containsKey("summary"));
        assertFalse(((Map<?, ?>) schedule.get(1)).containsKey("dueAt"));
        assertEquals(true, ((Map<?, ?>) schedule.get(1)).get("locked"));
        assertEquals(List.of(61L, 63L), tasks.stream()
                .map(task -> ((Number) ((Map<?, ?>) task).get("id")).longValue())
                .toList());
        assertTrue(scheduleLinkSql.get().contains("JOIN project_task"));
        assertEquals(9L, scheduleLinkArgs.get()[scheduleLinkArgs.get().length - 1]);
        assertFalse(campSelectionSql.get().contains("CURRENT_DATE"));
        assertEquals(FIXED_TODAY, campSelectionArgs.get()[campSelectionArgs.get().length - 1]);
        verify(jdbc, never()).update(contains("INSERT INTO project_task"), any(Object[].class));
    }

    private Map<String, Object> mutableTask(Long id, String title, String description) {
        Map<String, Object> task = new java.util.LinkedHashMap<>();
        task.put("id", id);
        task.put("teamId", 9L);
        task.put("title", title);
        task.put("description", description);
        task.put("ownerUserId", 23L);
        return task;
    }
}
