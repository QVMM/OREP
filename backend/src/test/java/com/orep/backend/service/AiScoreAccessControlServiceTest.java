package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

class AiScoreAccessControlServiceTest {

    private static final String TEACHER_TEAM_SQL = "SELECT COUNT(*) FROM project_team WHERE tenant_id = ? AND id = ?";
    private static final String MEMBER_TEAM_SQL = """
            SELECT COUNT(*)
            FROM project_team t
            JOIN project_team_member m ON m.team_id = t.id
            WHERE t.tenant_id = ? AND t.id = ? AND m.user_id = ?
            """;
    private static final String PARTICIPANT_WRITE_SQL = """
                SELECT COUNT(*)
                FROM project_team t
                WHERE t.id = ? AND t.tenant_id = ?
                  AND (
                    t.mentor_id = ?
                    OR EXISTS (
                        SELECT 1 FROM project_team_member m
                        WHERE m.team_id = t.id AND m.user_id = ?
                    )
                  )
                """;
    private static final String MEETING_ACCESS_SQL = """
                SELECT COUNT(1)
                FROM meeting m
                LEFT JOIN meeting_participant mp
                    ON mp.meeting_id = m.id AND mp.user_id = ?
                WHERE m.id = ? AND (m.creator_id = ? OR mp.user_id = ?)
                """;

    private final JdbcTemplate jdbcTemplate = mock(JdbcTemplate.class);
    private final AiScoreAccessControlService service = new AiScoreAccessControlService(jdbcTemplate);

    @Test
    void creatorCanAccessOwnSessionEvenWhenTeamIdIsNull() {
        AiScoringSession session = session(null, 7L);

        assertDoesNotThrow(() -> service.assertSessionAccess(session, 1L, 7L, "STUDENT"));

        verifyNoInteractions(jdbcTemplate);
    }

    @Test
    void teacherAdminAndSuperAdminCanAccessSessionIfTeamBelongsToSameTenant() {
        for (String role : new String[]{" teacher ", "ADMIN", "super_admin"}) {
            JdbcTemplate scopedJdbc = mock(JdbcTemplate.class);
            AiScoreAccessControlService scopedService = new AiScoreAccessControlService(scopedJdbc);
            when(scopedJdbc.queryForObject(TEACHER_TEAM_SQL, Integer.class, 3L, 9L)).thenReturn(1);

            assertDoesNotThrow(() -> scopedService.assertSessionAccess(session(9L, 7L), 3L, 8L, role));

            verify(scopedJdbc).queryForObject(TEACHER_TEAM_SQL, Integer.class, 3L, 9L);
        }
    }

    @Test
    void projectTeamMemberCanAccessOwnTeamSession() {
        AiScoringSession session = session(9L, 7L);
        when(jdbcTemplate.queryForObject(MEMBER_TEAM_SQL, Integer.class, 3L, 9L, 8L)).thenReturn(1);

        assertDoesNotThrow(() -> service.assertSessionAccess(session, 3L, 8L, "STUDENT"));

        verify(jdbcTemplate).queryForObject(MEMBER_TEAM_SQL, Integer.class, 3L, 9L, 8L);
    }

    @Test
    void crossTeamStudentIsRejected() {
        AiScoringSession session = session(9L, 7L);
        when(jdbcTemplate.queryForObject(MEMBER_TEAM_SQL, Integer.class, 3L, 9L, 8L)).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertSessionAccess(session, 3L, 8L, "STUDENT"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertTrue(error.getReason().contains("无权访问该评分会话"));
    }

    @Test
    void tenantTeacherCannotHangAnotherTeamsBook() {
        AiScoringSession session = session(9L, 7L);
        when(jdbcTemplate.queryForObject(eq(PARTICIPANT_WRITE_SQL), eq(Integer.class), eq(9L), eq(1L), eq(8L), eq(8L)))
                .thenReturn(0);
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertSessionParticipantWrite(session, 1L, 8L, "TEACHER"));
        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
    }

    @Test
    void mentorCanHangTeamBook() {
        AiScoringSession session = session(9L, 7L);
        when(jdbcTemplate.queryForObject(eq(PARTICIPANT_WRITE_SQL), eq(Integer.class), eq(9L), eq(1L), eq(16L), eq(16L)))
                .thenReturn(1);
        assertDoesNotThrow(() -> service.assertSessionParticipantWrite(session, 1L, 16L, "TEACHER"));
    }

    @Test
    void missingSessionIsNotFound() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertSessionAccess(null, 3L, 8L, "STUDENT"));

        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
        assertEquals("评分会话不存在", error.getReason());
    }

    @Test
    void missingUserIdIsUnauthorized() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertSessionAccess(session(9L, 7L), 3L, null, "STUDENT"));

        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
        assertEquals("请先登录", error.getReason());
    }

    @Test
    void nonCreatorCannotAccessTeamlessSession() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertSessionAccess(session(null, 7L), 3L, 8L, "ADMIN"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertEquals("无权访问该评分会话", error.getReason());
    }

    @Test
    void hasTeacherScopeNormalizesRole() {
        assertTrue(service.hasTeacherScope(" teacher "));
        assertTrue(service.hasTeacherScope("admin"));
        assertTrue(service.hasTeacherScope("SUPER_ADMIN"));
        assertTrue(service.hasTeacherScope("SCHOOL_ADMIN"));
        assertFalse(service.hasTeacherScope(null));
        assertFalse(service.hasTeacherScope("student"));
    }

    @Test
    void studentCannotAttachScoreToAnotherTeam() {
        when(jdbcTemplate.queryForObject(MEMBER_TEAM_SQL, Integer.class, 3L, 1L, 10L)).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.assertTeamAccess(1L, 3L, 10L, "STUDENT"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertTrue(error.getReason().contains("无权访问该评分会话"));
    }

    @Test
    void studentCanAttachScoreToOwnTeam() {
        when(jdbcTemplate.queryForObject(MEMBER_TEAM_SQL, Integer.class, 3L, 3L, 10L)).thenReturn(1);

        assertDoesNotThrow(() -> service.assertTeamAccess(3L, 3L, 10L, "STUDENT"));
    }

    @Test
    void meetingParticipantAccessRequiresCreatorOrRoster() {
        when(jdbcTemplate.queryForObject(MEETING_ACCESS_SQL, Integer.class, 10L, 20L, 10L, 10L)).thenReturn(1);
        assertTrue(service.hasMeetingParticipantAccess(20L, 10L));

        when(jdbcTemplate.queryForObject(MEETING_ACCESS_SQL, Integer.class, 8L, 1L, 8L, 8L)).thenReturn(0);
        assertFalse(service.hasMeetingParticipantAccess(1L, 8L));
        assertFalse(service.hasMeetingParticipantAccess(null, 10L));
        assertFalse(service.hasMeetingParticipantAccess(20L, null));
    }

    @Test
    void schoolAdminCanAccessSessionIfTeamBelongsToSameTenant() {
        when(jdbcTemplate.queryForObject(TEACHER_TEAM_SQL, Integer.class, 3L, 9L)).thenReturn(1);

        assertDoesNotThrow(() -> service.assertSessionAccess(session(9L, 7L), 3L, 8L, "SCHOOL_ADMIN"));

        verify(jdbcTemplate).queryForObject(TEACHER_TEAM_SQL, Integer.class, 3L, 9L);
    }

    private AiScoringSession session(Long teamId, Long createdBy) {
        AiScoringSession session = new AiScoringSession();
        session.setId(11L);
        session.setTeamId(teamId);
        session.setCreatedBy(createdBy);
        return session;
    }
}
