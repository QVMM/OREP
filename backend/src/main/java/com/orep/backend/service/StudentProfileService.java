package com.orep.backend.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class StudentProfileService {

    private final JdbcTemplate jdbc;
    private final StudentLearningAnalyticsService learningAnalytics;

    public StudentProfileService(JdbcTemplate jdbc, StudentLearningAnalyticsService learningAnalytics) {
        this.jdbc = jdbc;
        this.learningAnalytics = learningAnalytics;
    }

    public Map<String, Object> dashboard(Long tenantId, Long userId) {
        Map<String, Object> profile = profile(tenantId, userId);
        Long teamId = nullableLong(profile.get("teamId"));
        List<Map<String, Object>> sessions = learningAnalytics.learningSessions(userId);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("profile", profile);
        result.put("summary", learningAnalytics.summary(sessions));
        result.put("heatmap", learningAnalytics.heatmap(sessions));
        result.put("distribution", learningAnalytics.distribution(sessions));
        // 精准分项：站外视频 / 打字等，用于分布副文案，避免学生以为没统计
        result.put("preciseDurations", learningAnalytics.preciseDurations(tenantId, userId));
        result.put("certificates", certificates(tenantId, userId, teamId));
        result.put("rectifications", rectifications(tenantId, userId, teamId));
        result.put("roadshow", teamRoadshow(teamId));
        result.put("serverDate", LocalDate.now(ZoneId.of("Asia/Shanghai")).toString());
        return result;
    }

    /** 团队官方路演分：任意成员/老师上传，全体队员档案可见。 */
    private Map<String, Object> teamRoadshow(Long teamId) {
        Map<String, Object> empty = new LinkedHashMap<>();
        empty.put("hasReport", false);
        if (teamId == null) return empty;
        try {
            List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT r.id reportId, r.session_id sessionId, r.meeting_id meetingId,
                       r.overall_score overallScore,
                       COALESCE(r.completed_at, r.created_at) scoredAt
                FROM ai_score_report r
                JOIN ai_scoring_session s ON s.id = r.session_id
                WHERE r.status = 'completed' AND r.overall_score IS NOT NULL
                  AND (
                    s.team_id = ?
                    OR EXISTS (
                      SELECT 1 FROM project_roadshow_binding b
                      WHERE b.team_id = ? AND b.meeting_id = r.meeting_id
                    )
                  )
                ORDER BY COALESCE(r.completed_at, r.created_at) DESC, r.id DESC
                LIMIT 1
                """, teamId, teamId);
            if (rows.isEmpty()) return empty;
            Map<String, Object> out = new LinkedHashMap<>(rows.get(0));
            out.put("hasReport", true);
            return out;
        } catch (Exception ignored) {
            return empty;
        }
    }

    private Map<String, Object> profile(Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT u.id userId, u.username, u.email, u.school_name schoolName,
                   u.college_name collegeName, u.class_name className,
                   pt.id teamId, pt.name teamName,
                   ptm.role_in_team teamRole, ptm.position_name positionName
            FROM users u
            LEFT JOIN project_team_member ptm ON ptm.user_id = u.id
            LEFT JOIN project_team pt ON pt.id = ptm.team_id AND pt.tenant_id = u.tenant_id
            WHERE u.id = ? AND u.tenant_id = ?
            ORDER BY (pt.status = 'ACTIVE') DESC, ptm.joined_at DESC
            LIMIT 1
            """, userId, tenantId);
        return rows.isEmpty() ? Map.of("userId", userId) : rows.get(0);
    }

    private List<Map<String, Object>> certificates(Long tenantId, Long userId, Long teamId) {
        List<Object> args = new ArrayList<>();
        args.add(tenantId);
        args.add(userId);
        String teamClause = "";
        if (teamId != null) {
            teamClause = " OR (r.recipient_type = 'TEAM' AND r.team_id = ?)";
            args.add(teamId);
        }
        return jdbc.queryForList("""
            SELECT DISTINCT c.id, c.title, c.certificate_type certificateType,
                   c.description, c.issued_at issuedAt, c.certificate_no certificateNo,
                   c.pdf_url pdfUrl, c.award_level awardLevel, c.source_type sourceType,
                   COALESCE(NULLIF(c.issuer_name, ''), issuer.username) issuerName
            FROM student_certificate c
            JOIN student_certificate_recipient r ON r.certificate_id = c.id
            LEFT JOIN users issuer ON issuer.id = c.issuer_user_id
            WHERE c.tenant_id = ? AND c.status = 'ACTIVE'
              AND ((r.recipient_type = 'USER' AND r.user_id = ?)%s)
            ORDER BY c.issued_at DESC
            """.formatted(teamClause), args.toArray());
    }

    private List<Map<String, Object>> rectifications(Long tenantId, Long userId, Long teamId) {
        List<Object> args = new ArrayList<>();
        args.add(tenantId);
        args.add(userId);
        String teamClause = "";
        if (teamId != null) {
            teamClause = " OR (rr.recipient_type = 'TEAM' AND rr.team_id = ?)";
            args.add(teamId);
        }
        return jdbc.queryForList("""
            SELECT DISTINCT r.id, r.title, r.description, r.requirement_text requirementText,
                   r.issued_at issuedAt, r.due_at dueAt, r.status,
                   r.related_task_id relatedTaskId, r.completed_at completedAt,
                   issuer.username issuerName
            FROM student_rectification r
            JOIN student_rectification_recipient rr ON rr.rectification_id = r.id
            LEFT JOIN users issuer ON issuer.id = r.issuer_user_id
            WHERE r.tenant_id = ?
              AND ((rr.recipient_type = 'USER' AND rr.user_id = ?)%s)
            ORDER BY (r.status IN ('PENDING', 'IN_PROGRESS')) DESC, r.issued_at DESC
            """.formatted(teamClause), args.toArray());
    }

    private Long nullableLong(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

}
