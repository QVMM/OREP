package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.IssueView;
import com.orep.backend.entity.Issue;
import com.orep.backend.entity.Meeting;
import com.orep.backend.mapper.IssueMapper;
import com.orep.backend.mapper.MeetingMapper;
import com.orep.backend.security.AdminAccess;
import com.orep.backend.security.DataScopeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;

@Service
public class IssueService {

    @Autowired
    private IssueMapper issueMapper;

    @Autowired
    private MeetingMapper meetingMapper;

    @Autowired
    private DataScopeService dataScopeService;

    @Autowired
    private JdbcTemplate jdbc;

    public Issue createIssue(Long tenantId, Long meetingId, Long scoreDetailId,
                             String category, String description, Long sourceUserId) {
        Issue issue = new Issue();
        issue.setTenantId(tenantId);
        issue.setMeetingId(meetingId);
        issue.setScoreDetailId(scoreDetailId);
        issue.setCategory(category);
        issue.setDescription(description);
        issue.setSourceUserId(sourceUserId);
        issue.setStatus(0);
        issueMapper.insert(issue);
        return issue;
    }

    public List<Issue> listIssues(Long tenantId, Long meetingId, Long userId, String role) {
        List<Long> meetingIds = accessibleIssueMeetingIds(tenantId, meetingId, userId, role);
        if (meetingIds.isEmpty()) {
            return List.of();
        }
        return issueMapper.selectList(
                new LambdaQueryWrapper<Issue>()
                        .eq(Issue::getTenantId, tenantId)
                        .in(Issue::getMeetingId, meetingIds)
                        .orderByDesc(Issue::getCreatedAt)
        );
    }

    public List<IssueView> listIssueViews(Long tenantId, Long meetingId, Integer status, Long userId, String role) {
        List<Long> meetingIds = accessibleIssueMeetingIds(tenantId, meetingId, userId, role);
        if (meetingIds.isEmpty()) {
            return List.of();
        }

        List<Object> params = new ArrayList<>();
        params.add(tenantId);
        params.addAll(meetingIds);
        String placeholders = meetingIds.stream().map(id -> "?").reduce((a, b) -> a + "," + b).orElse("?");
        StringBuilder sql = new StringBuilder("""
            SELECT i.id, i.tenant_id tenantId, i.meeting_id meetingId, m.title meetingTitle,
                   b.team_id teamId, t.name teamName, t.mentor_id mentorId, mentor.username mentorName,
                   i.score_detail_id scoreDetailId, i.category, i.description,
                   i.source_user_id sourceUserId, reporter.username reporterName,
                   i.status, i.created_at createdAt, i.resolved_at resolvedAt, i.resolved_meeting_id resolvedMeetingId
            FROM issue i
            JOIN meeting m ON m.id = i.meeting_id AND m.tenant_id = i.tenant_id
            LEFT JOIN project_roadshow_binding b ON b.meeting_id = i.meeting_id
            LEFT JOIN project_team t ON t.id = b.team_id AND t.tenant_id = i.tenant_id
            LEFT JOIN users mentor ON mentor.id = t.mentor_id
            LEFT JOIN users reporter ON reporter.id = i.source_user_id
            WHERE i.tenant_id = ?
              AND i.meeting_id IN (
            """);
        sql.append(placeholders).append(") ");
        if (status != null) {
            sql.append(" AND i.status = ? ");
            params.add(status);
        }
        sql.append(" ORDER BY i.created_at DESC ");
        return jdbc.queryForList(sql.toString(), params.toArray()).stream()
                .map(this::toIssueView)
                .toList();
    }

    private List<Long> accessibleIssueMeetingIds(Long tenantId, Long meetingId, Long userId, String role) {
        if (meetingId != null) {
            Meeting meeting = meetingMapper.selectById(meetingId);
            if (!canAccessIssueMeeting(tenantId, userId, role, meeting)) {
                throw new RuntimeException("无权访问该会议问题");
            }
            return List.of(meetingId);
        }
        return jdbc.queryForList(accessibleIssueMeetingSql(role), Long.class, accessibleIssueMeetingParams(tenantId, userId, role).toArray());
    }

    public List<Issue> listUnresolvedIssues(Long tenantId, Long userId, String role) {
        List<Long> meetingIds = accessibleIssueMeetingIds(tenantId, null, userId, role);
        if (meetingIds.isEmpty()) {
            return List.of();
        }
        return issueMapper.selectList(
                new LambdaQueryWrapper<Issue>()
                        .eq(Issue::getTenantId, tenantId)
                        .eq(Issue::getStatus, 0)
                        .in(Issue::getMeetingId, meetingIds)
                        .orderByDesc(Issue::getCreatedAt)
        );
    }

    public void resolveIssue(Long issueId, Long meetingId, Long userId, String role) {
        Issue issue = issueMapper.selectById(issueId);
        if (issue == null) {
            throw new RuntimeException("问题不存在");
        }
        Meeting meeting = meetingMapper.selectById(issue.getMeetingId());
        if (!canAccessIssueMeeting(issue.getTenantId(), userId, role, meeting)) {
            throw new RuntimeException("无权处理该会议问题");
        }
        issue.setStatus(1);
        issue.setResolvedAt(LocalDateTime.now());
        issue.setResolvedMeetingId(meetingId);
        issueMapper.updateById(issue);
    }

    public void autoResolveByFullScore(Long tenantId, Long meetingId, Long userId, String role) {
        List<Issue> unresolved = listUnresolvedIssues(tenantId, userId, role);
        for (Issue issue : unresolved) {
            resolveIssue(issue.getId(), meetingId, userId, role);
        }
    }

    public long countTotal(Long tenantId, Long userId, String role) {
        List<Long> meetingIds = accessibleIssueMeetingIds(tenantId, null, userId, role);
        if (meetingIds.isEmpty()) {
            return 0;
        }
        return issueMapper.selectCount(
                new LambdaQueryWrapper<Issue>()
                        .eq(Issue::getTenantId, tenantId)
                        .in(Issue::getMeetingId, meetingIds)
        );
    }

    public long countResolved(Long tenantId, Long userId, String role) {
        List<Long> meetingIds = accessibleIssueMeetingIds(tenantId, null, userId, role);
        if (meetingIds.isEmpty()) {
            return 0;
        }
        return issueMapper.selectCount(
                new LambdaQueryWrapper<Issue>()
                        .eq(Issue::getTenantId, tenantId)
                        .eq(Issue::getStatus, 1)
                        .in(Issue::getMeetingId, meetingIds)
        );
    }

    private boolean canAccessIssueMeeting(Long tenantId, Long userId, String role, Meeting meeting) {
        if (meeting == null || tenantId == null || !Objects.equals(meeting.getTenantId(), tenantId)) {
            return false;
        }
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM (" + accessibleIssueMeetingSql(role) + ") scoped WHERE scoped.id = ?",
                Integer.class,
                withMeetingParam(accessibleIssueMeetingParams(tenantId, userId, role), meeting.getId()).toArray()
        );
        return count != null && count > 0;
    }

    private String accessibleIssueMeetingSql(String role) {
        String normalized = AdminAccess.normalizeRole(role);
        if ("ADMIN".equals(normalized)) {
            return """
                SELECT DISTINCT m.id
                FROM meeting m
                WHERE m.tenant_id = ?
                """;
        }
        if ("SCHOOL_ADMIN".equals(normalized)) {
            return """
                SELECT DISTINCT m.id
                FROM meeting m
                WHERE m.tenant_id = ?
                """;
        }
        if ("TEACHER".equals(normalized)) {
            return """
                SELECT DISTINCT m.id
                FROM meeting m
                LEFT JOIN project_roadshow_binding b ON b.meeting_id = m.id
                LEFT JOIN project_team t ON t.id = b.team_id AND t.tenant_id = m.tenant_id
                LEFT JOIN project_team_member tm ON tm.team_id = t.id AND tm.user_id = ? AND tm.role_in_team = 'MENTOR'
                WHERE m.tenant_id = ?
                  AND (m.creator_id = ? OR t.mentor_id = ? OR tm.user_id IS NOT NULL)
                """;
        }
        if ("EXPERT".equals(normalized) || "REVIEWER".equals(normalized)) {
            return """
                SELECT DISTINCT m.id
                FROM meeting m
                JOIN project_roadshow_binding b ON b.meeting_id = m.id
                JOIN project_team t ON t.id = b.team_id AND t.tenant_id = m.tenant_id
                JOIN meeting_participant mp ON mp.meeting_id = m.id AND mp.user_id = ?
                WHERE m.tenant_id = ?
                """;
        }
        return """
            SELECT DISTINCT m.id
            FROM meeting m
            JOIN project_roadshow_binding b ON b.meeting_id = m.id
            JOIN project_team t ON t.id = b.team_id AND t.tenant_id = m.tenant_id
            WHERE 1 = 0 AND m.tenant_id = ?
            """;
    }

    private List<Object> accessibleIssueMeetingParams(Long tenantId, Long userId, String role) {
        String normalized = AdminAccess.normalizeRole(role);
        if ("TEACHER".equals(normalized)) {
            return new ArrayList<>(List.of(userId, tenantId, userId, userId));
        }
        if ("EXPERT".equals(normalized) || "REVIEWER".equals(normalized)) {
            return new ArrayList<>(List.of(userId, tenantId));
        }
        return new ArrayList<>(List.of(tenantId));
    }

    private List<Object> withMeetingParam(List<Object> params, Long meetingId) {
        params.add(meetingId);
        return params;
    }

    private IssueView toIssueView(Map<String, Object> row) {
        IssueView view = new IssueView();
        view.setId(longValue(row.get("id")));
        view.setTenantId(longValue(row.get("tenantId")));
        view.setMeetingId(longValue(row.get("meetingId")));
        view.setMeetingTitle(text(row.get("meetingTitle")));
        view.setTeamId(longValue(row.get("teamId")));
        view.setTeamName(text(row.get("teamName")));
        view.setMentorId(longValue(row.get("mentorId")));
        view.setMentorName(text(row.get("mentorName")));
        view.setScoreDetailId(longValue(row.get("scoreDetailId")));
        view.setCategory(text(row.get("category")));
        view.setDescription(text(row.get("description")));
        view.setTitle(buildTitle(view.getCategory(), view.getDescription(), view.getId()));
        view.setSourceUserId(longValue(row.get("sourceUserId")));
        view.setReporterName(text(row.get("reporterName")));
        Integer status = intValue(row.get("status"));
        view.setStatus(status != null && status == 1 ? "RESOLVED" : "OPEN");
        view.setCreatedAt(timeValue(row.get("createdAt")));
        view.setResolvedAt(timeValue(row.get("resolvedAt")));
        view.setResolvedMeetingId(longValue(row.get("resolvedMeetingId")));
        return view;
    }

    private String buildTitle(String category, String description, Long id) {
        String base = category == null || category.isBlank() ? "问题" : category;
        if (description == null || description.isBlank()) return base + " #" + id;
        String summary = description.length() > 24 ? description.substring(0, 24) + "..." : description;
        return base + " - " + summary;
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        return Long.parseLong(String.valueOf(value));
    }

    private Integer intValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.intValue();
        return Integer.parseInt(String.valueOf(value));
    }

    private LocalDateTime timeValue(Object value) {
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime();
        if (value instanceof LocalDateTime time) return time;
        return null;
    }

    private String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
