package com.orep.backend.security;

import com.orep.backend.entity.Meeting;
import com.orep.backend.entity.User;
import com.orep.backend.mapper.MeetingMapper;
import com.orep.backend.mapper.UserMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 租户内组织隔离。
 * 教师支持「多校/多班」管辖：{@code teacher_teaching_scope}；
 * 若无配置，则回退到 users 表上的主 school/college/class。
 */
@Service
public class DataScopeService {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private MeetingMapper meetingMapper;

    @Autowired
    private JdbcTemplate jdbc;

    @PostConstruct
    public void ensureTeachingScopeSchema() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS teacher_teaching_scope (
              id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
              tenant_id BIGINT NOT NULL,
              user_id BIGINT NOT NULL,
              school_id BIGINT DEFAULT NULL,
              college_id BIGINT DEFAULT NULL,
              class_id BIGINT NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uk_teacher_class (user_id, class_id),
              KEY idx_teacher_scope_user (tenant_id, user_id),
              KEY idx_teacher_scope_class (class_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            COMMENT='教师可管辖的班级（支持一师多校多班）'
            """);
        // 将已有主班级归属同步为一条管辖范围
        try {
            jdbc.update("""
                INSERT IGNORE INTO teacher_teaching_scope (tenant_id, user_id, school_id, college_id, class_id)
                SELECT tenant_id, id, school_id, college_id, class_id
                FROM users
                WHERE role = 'TEACHER' AND class_id IS NOT NULL
                """);
        } catch (Exception ignored) {
        }
    }

    public boolean bypassOrgScope(String role) {
        return AdminAccess.isSuperAdmin(role);
    }

    public User loadUser(Long userId) {
        if (userId == null) {
            throw new RuntimeException("用户未登录");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        return user;
    }

    /**
     * 解析教师/操作者可管辖的班级范围。优先 teaching_scope 表，否则回退主归属。
     */
    public List<Map<String, Object>> resolveTeachingScopes(Long operatorUserId) {
        User operator = loadUser(operatorUserId);
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT s.id, s.tenant_id tenantId, s.user_id userId,
                   s.school_id schoolId, s.college_id collegeId, s.class_id classId,
                   COALESCE(NULLIF(su.name, ''), NULLIF(u.school_name, ''), '未命名学校') schoolName,
                   COALESCE(NULLIF(cu.name, ''), NULLIF(u.college_name, ''), '未命名学院') collegeName,
                   COALESCE(NULLIF(cl.name, ''), NULLIF(u.class_name, ''), '未命名班级') className
            FROM teacher_teaching_scope s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN organization_unit su ON su.id = s.school_id AND su.status = 'ACTIVE'
            LEFT JOIN organization_unit cu ON cu.id = s.college_id AND cu.status = 'ACTIVE'
            LEFT JOIN organization_unit cl ON cl.id = s.class_id AND cl.status = 'ACTIVE'
            WHERE s.user_id = ?
            ORDER BY s.id
            """, operatorUserId);
        if (!rows.isEmpty()) {
            return rows;
        }
        // 回退：主账号归属
        if (operator.getClassId() != null || operator.getSchoolId() != null) {
            Map<String, Object> primary = new LinkedHashMap<>();
            primary.put("id", null);
            primary.put("tenantId", operator.getTenantId());
            primary.put("userId", operator.getId());
            primary.put("schoolId", operator.getSchoolId());
            primary.put("collegeId", operator.getCollegeId());
            primary.put("classId", operator.getClassId());
            primary.put("schoolName", operator.getSchoolName());
            primary.put("collegeName", operator.getCollegeName());
            primary.put("className", operator.getClassName());
            return List.of(primary);
        }
        return List.of();
    }

    public Set<Long> accessibleClassIds(Long operatorUserId, String operatorRole) {
        if (bypassOrgScope(operatorRole)) {
            return null;
        }
        return resolveTeachingScopes(operatorUserId).stream()
                .map(row -> longValue(row.get("classId")))
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(HashSet::new));
    }

    public Set<Long> accessibleSchoolIdSet(Long operatorUserId, String operatorRole) {
        if (bypassOrgScope(operatorRole)) {
            return null;
        }
        Set<Long> ids = resolveTeachingScopes(operatorUserId).stream()
                .map(row -> longValue(row.get("schoolId")))
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(HashSet::new));
        if (ids.isEmpty()) {
            User operator = loadUser(operatorUserId);
            if (operator.getSchoolId() != null) {
                ids.add(operator.getSchoolId());
            }
        }
        return ids;
    }

    public Set<Long> accessibleCollegeIdSet(Long operatorUserId, String operatorRole) {
        if (bypassOrgScope(operatorRole)) {
            return null;
        }
        Set<Long> ids = resolveTeachingScopes(operatorUserId).stream()
                .map(row -> longValue(row.get("collegeId")))
                .filter(Objects::nonNull)
                .collect(Collectors.toCollection(HashSet::new));
        if (ids.isEmpty()) {
            User operator = loadUser(operatorUserId);
            if (operator.getCollegeId() != null) {
                ids.add(operator.getCollegeId());
            }
        }
        return ids;
    }

    public boolean sameOrgScope(User viewer, User owner) {
        if (viewer == null || owner == null) {
            return false;
        }
        if (!Objects.equals(viewer.getTenantId(), owner.getTenantId())) {
            return false;
        }
        if (bypassOrgScope(viewer.getRole())) {
            return true;
        }
        // 教师：任一管辖班级/学校匹配即可
        if ("TEACHER".equals(AdminAccess.normalizeRole(viewer.getRole()))) {
            List<Map<String, Object>> scopes = resolveTeachingScopes(viewer.getId());
            if (scopes.isEmpty()) {
                return Objects.equals(viewer.getId(), owner.getId());
            }
            for (Map<String, Object> scope : scopes) {
                Long classId = longValue(scope.get("classId"));
                if (classId != null && classId.equals(owner.getClassId())) {
                    return true;
                }
                Long schoolId = longValue(scope.get("schoolId"));
                Long collegeId = longValue(scope.get("collegeId"));
                if (classId == null && schoolId != null && schoolId.equals(owner.getSchoolId())) {
                    if (collegeId == null || collegeId.equals(owner.getCollegeId())) {
                        return true;
                    }
                }
            }
            return Objects.equals(viewer.getId(), owner.getId());
        }

        Long viewerSchool = viewer.getSchoolId();
        if (viewerSchool == null) {
            return Objects.equals(viewer.getId(), owner.getId());
        }
        if (!viewerSchool.equals(owner.getSchoolId())) {
            return false;
        }
        Long viewerCollege = viewer.getCollegeId();
        if (viewerCollege != null && owner.getCollegeId() != null) {
            return viewerCollege.equals(owner.getCollegeId());
        }
        return true;
    }

    public boolean canAccessMeeting(User viewer, Meeting meeting) {
        if (viewer == null || meeting == null) {
            return false;
        }
        if (!Objects.equals(viewer.getTenantId(), meeting.getTenantId())) {
            return false;
        }
        if (bypassOrgScope(viewer.getRole())) {
            return true;
        }
        User creator = userMapper.selectById(meeting.getCreatorId());
        return sameOrgScope(viewer, creator);
    }

    public void assertMeetingAccess(Long userId, String role, Meeting meeting) {
        User viewer = loadUser(userId);
        if (!canAccessMeeting(viewer, meeting)) {
            throw new RuntimeException("无权访问该会议数据");
        }
    }

    public void assertMeetingAccessById(Long userId, String role, Long meetingId) {
        if (meetingId == null) {
            throw new RuntimeException("会议不存在");
        }
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        assertMeetingAccess(userId, role, meeting);
    }

    public boolean canUseOrgDashboardScope(String role) {
        String normalized = AdminAccess.normalizeRole(role);
        return "ADMIN".equals(normalized)
                || "SCHOOL_ADMIN".equals(normalized)
                || "TEACHER".equals(normalized);
    }

    public void assertUserAccess(Long operatorUserId, String operatorRole, User targetUser) {
        User operator = loadUser(operatorUserId);
        if (!sameOrgScope(operator, targetUser)) {
            throw new RuntimeException("无权访问该用户");
        }
    }

    public void assertOrgAssignment(Long operatorUserId, String operatorRole, Long schoolId, Long collegeId) {
        assertOrgAssignment(operatorUserId, operatorRole, schoolId, collegeId, null);
    }

    /**
     * 校验操作者是否可将用户落到指定学校/学院/班级。
     * 教师：classId 必须在其 teaching_scope（或主归属）内。
     */
    public void assertOrgAssignment(Long operatorUserId, String operatorRole, Long schoolId, Long collegeId, Long classId) {
        if (bypassOrgScope(operatorRole)) {
            return;
        }
        if ("TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            List<Map<String, Object>> scopes = resolveTeachingScopes(operatorUserId);
            if (scopes.isEmpty()) {
                throw new RuntimeException("当前教师账号未配置可管辖班级，无法创建或分配用户。请联系管理员配置「教学管辖范围」");
            }
            if (classId == null) {
                throw new RuntimeException("请选择要创建到的班级");
            }
            boolean allowed = scopes.stream().anyMatch(s -> classId.equals(longValue(s.get("classId"))));
            if (!allowed) {
                throw new RuntimeException("无权在该班级创建用户，仅可在自己管辖的班级下操作");
            }
            return;
        }

        User operator = loadUser(operatorUserId);
        if (operator.getSchoolId() == null) {
            throw new RuntimeException("当前账号未绑定学校，无法操作用户");
        }
        if (schoolId != null && !schoolId.equals(operator.getSchoolId())) {
            throw new RuntimeException("无权将用户分配到其他学校");
        }
        if (operator.getCollegeId() != null && collegeId != null && !collegeId.equals(operator.getCollegeId())) {
            throw new RuntimeException("无权将用户分配到其他学院");
        }
    }

    public void appendUserOrgFilter(StringBuilder sql, List<Object> params, Long operatorUserId, String operatorRole) {
        if (bypassOrgScope(operatorRole)) {
            return;
        }
        if ("TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            Set<Long> classIds = accessibleClassIds(operatorUserId, operatorRole);
            if (classIds == null || classIds.isEmpty()) {
                // 无管辖班级：仅自己
                sql.append(" AND u.id = ? ");
                params.add(operatorUserId);
                return;
            }
            sql.append(" AND u.class_id IN (");
            sql.append(classIds.stream().map(id -> "?").collect(Collectors.joining(",")));
            sql.append(") ");
            params.addAll(classIds);
            return;
        }

        User operator = loadUser(operatorUserId);
        if (operator.getSchoolId() == null) {
            sql.append(" AND u.id = ? ");
            params.add(operatorUserId);
            return;
        }
        sql.append(" AND u.school_id = ? ");
        params.add(operator.getSchoolId());
        if (operator.getCollegeId() != null) {
            sql.append(" AND u.college_id = ? ");
            params.add(operator.getCollegeId());
        }
    }

    public Long accessibleClassId(Long operatorUserId, String operatorRole) {
        Set<Long> ids = accessibleClassIds(operatorUserId, operatorRole);
        if (ids == null || ids.isEmpty()) {
            return null;
        }
        return ids.iterator().next();
    }

    public List<Long> accessibleSchoolIds(Long operatorUserId, String operatorRole) {
        Set<Long> set = accessibleSchoolIdSet(operatorUserId, operatorRole);
        if (set == null) {
            return null;
        }
        return new ArrayList<>(set);
    }

    public Long accessibleCollegeId(Long operatorUserId, String operatorRole) {
        Set<Long> set = accessibleCollegeIdSet(operatorUserId, operatorRole);
        if (set == null || set.isEmpty()) {
            return null;
        }
        // 多学院时返回 null，表示不按单学院收紧（由 filter 用集合处理）
        return set.size() == 1 ? set.iterator().next() : null;
    }

    public List<Long> accessibleMeetingIds(Long tenantId, Long userId, String role) {
        if (tenantId == null || userId == null) {
            return List.of();
        }
        if (bypassOrgScope(role)) {
            return jdbc.queryForList("SELECT id FROM meeting WHERE tenant_id = ? ORDER BY id", Long.class, tenantId);
        }
        if ("TEACHER".equals(AdminAccess.normalizeRole(role))) {
            return jdbc.queryForList("""
                SELECT DISTINCT m.id
                FROM meeting m
                LEFT JOIN meeting_participant mp ON mp.meeting_id=m.id AND mp.user_id=?
                LEFT JOIN project_roadshow_binding b ON b.meeting_id=m.id
                LEFT JOIN project_team t ON t.id=b.team_id AND t.tenant_id=m.tenant_id
                LEFT JOIN project_team_member mentor ON mentor.team_id=t.id
                  AND mentor.user_id=? AND mentor.role_in_team='MENTOR'
                WHERE m.tenant_id=?
                  AND (m.creator_id=? OR mp.user_id IS NOT NULL OR t.mentor_id=? OR mentor.user_id IS NOT NULL)
                ORDER BY m.id
                """, Long.class, userId, userId, tenantId, userId, userId);
        }
        User viewer = loadUser(userId);
        if (viewer.getSchoolId() == null) {
            return jdbc.queryForList(
                    "SELECT id FROM meeting WHERE tenant_id = ? AND creator_id = ? ORDER BY id",
                    Long.class,
                    tenantId,
                    userId
            );
        }
        if (viewer.getCollegeId() != null) {
            return jdbc.queryForList("""
                    SELECT m.id
                    FROM meeting m
                    JOIN users u ON u.id = m.creator_id
                    WHERE m.tenant_id = ?
                      AND u.school_id = ?
                      AND u.college_id = ?
                    ORDER BY m.id
                    """, Long.class, tenantId, viewer.getSchoolId(), viewer.getCollegeId());
        }
        return jdbc.queryForList("""
                SELECT m.id
                FROM meeting m
                JOIN users u ON u.id = m.creator_id
                WHERE m.tenant_id = ?
                  AND u.school_id = ?
                ORDER BY m.id
                """, Long.class, tenantId, viewer.getSchoolId());
    }

    /**
     * 替换教师管辖班级列表（管理员配置一师多班时调用）。
     */
    public void replaceTeachingScopes(Long tenantId, Long teacherUserId, List<Long> classIds) {
        jdbc.update("DELETE FROM teacher_teaching_scope WHERE user_id = ?", teacherUserId);
        if (classIds == null || classIds.isEmpty()) {
            return;
        }
        for (Long classId : classIds) {
            if (classId == null) continue;
            List<Map<String, Object>> clazzRows = jdbc.queryForList("""
                SELECT id, parent_id parentId, type, name FROM organization_unit
                WHERE id = ? AND tenant_id = ? AND type = 'CLASS' AND status = 'ACTIVE'
                """, classId, tenantId);
            if (clazzRows.isEmpty()) {
                throw new RuntimeException("班级不存在或已停用: " + classId);
            }
            Long collegeId = longValue(clazzRows.get(0).get("parentId"));
            Long schoolId = null;
            if (collegeId != null) {
                List<Map<String, Object>> collegeRows = jdbc.queryForList("""
                    SELECT id, parent_id parentId FROM organization_unit
                    WHERE id = ? AND tenant_id = ? AND status = 'ACTIVE'
                    """, collegeId, tenantId);
                if (!collegeRows.isEmpty()) {
                    schoolId = longValue(collegeRows.get(0).get("parentId"));
                }
            }
            jdbc.update("""
                INSERT INTO teacher_teaching_scope (tenant_id, user_id, school_id, college_id, class_id)
                VALUES (?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE school_id = VALUES(school_id), college_id = VALUES(college_id)
                """, tenantId, teacherUserId, schoolId, collegeId, classId);
        }
        // 同步主归属为第一条，兼容旧逻辑
        List<Map<String, Object>> scopes = resolveTeachingScopes(teacherUserId);
        if (!scopes.isEmpty()) {
            Map<String, Object> first = scopes.get(0);
            jdbc.update("""
                UPDATE users SET school_id = ?, college_id = ?, class_id = ?,
                  school_name = ?, college_name = ?, class_name = ?
                WHERE id = ?
                """,
                    first.get("schoolId"), first.get("collegeId"), first.get("classId"),
                    first.get("schoolName"), first.get("collegeName"), first.get("className"),
                    teacherUserId);
        }
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (Exception e) {
            return null;
        }
    }
}
