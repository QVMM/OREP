package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.Objects;

@Service
public class AiScoreAccessControlService {

    private static final String ACCESS_DENIED_MESSAGE = "无权访问该评分会话";

    private final JdbcTemplate jdbcTemplate;

    public AiScoreAccessControlService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * Write access for hanging task-book evidence: creator, team member, or mentor.
     * Tenant-wide teachers cannot mutate another team's book.
     */
    public void assertSessionParticipantWrite(AiScoringSession session, Long tenantId, Long userId, String role) {
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "评分会话不存在");
        }
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        if (Objects.equals(session.getCreatedBy(), userId)) {
            return;
        }
        Long teamId = session.getTeamId();
        if (teamId == null) {
            throw forbidden();
        }
        Integer count = jdbcTemplate.queryForObject("""
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
                """, Integer.class, teamId, tenantId, userId, userId);
        if (count != null && count > 0) {
            return;
        }
        throw forbidden();
    }

    public void assertSessionAccess(AiScoringSession session, Long tenantId, Long userId, String role) {
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "评分会话不存在");
        }
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        if (Objects.equals(session.getCreatedBy(), userId)) {
            return;
        }

        Long teamId = session.getTeamId();
        if (teamId == null) {
            throw forbidden();
        }
        assertTeamAccess(teamId, tenantId, userId, role);
    }

    public void assertTeamAccess(Long teamId, Long tenantId, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        if (teamId == null) {
            return;
        }
        if (hasTeacherScope(role)) {
            Integer count = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM project_team WHERE tenant_id = ? AND id = ?",
                    Integer.class,
                    tenantId,
                    teamId);
            if (count != null && count > 0) {
                return;
            }
            throw forbidden();
        }

        Integer count = jdbcTemplate.queryForObject("""
                SELECT COUNT(*)
                FROM project_team t
                JOIN project_team_member m ON m.team_id = t.id
                WHERE t.tenant_id = ? AND t.id = ? AND m.user_id = ?
                """, Integer.class, tenantId, teamId, userId);
        if (count != null && count > 0) {
            return;
        }

        throw forbidden();
    }

    public boolean hasMeetingParticipantAccess(Long meetingId, Long userId) {
        if (meetingId == null || userId == null) {
            return false;
        }
        Integer count = jdbcTemplate.queryForObject("""
                SELECT COUNT(1)
                FROM meeting m
                LEFT JOIN meeting_participant mp
                    ON mp.meeting_id = m.id AND mp.user_id = ?
                WHERE m.id = ? AND (m.creator_id = ? OR mp.user_id = ?)
                """, Integer.class, userId, meetingId, userId, userId);
        return count != null && count > 0;
    }

    public boolean hasTeacherScope(String role) {
        if (role == null) {
            return false;
        }
        return switch (role.trim().toUpperCase()) {
            case "TEACHER", "ADMIN", "SUPER_ADMIN", "SCHOOL_ADMIN" -> true;
            default -> false;
        };
    }

    private ResponseStatusException forbidden() {
        return new ResponseStatusException(HttpStatus.FORBIDDEN, ACCESS_DENIED_MESSAGE);
    }
}
