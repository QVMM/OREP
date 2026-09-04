package com.orep.backend.service;

import com.orep.backend.dto.AdminCreateUserRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.entity.User;
import com.orep.backend.mapper.UserMapper;
import com.orep.backend.security.AdminAccess;
import com.orep.backend.security.DataScopeService;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class UserService {

    @Autowired
    private UserMapper userMapper;

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private DataScopeService dataScopeService;

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    /** 管理端一键重置后的默认密码（明文仅用于哈希，不入库） */
    static final String DEFAULT_RESET_PASSWORD = "123456";
    private static final List<String> ALLOWED_ROLES = List.of(
            "ADMIN", "SCHOOL_ADMIN", "TEACHER", "STUDENT", "REVIEWER", "EXPERT"
    );
    private static final Set<String> ORG_TYPES = Set.of("SCHOOL", "COLLEGE", "CLASS");

    @PostConstruct
    public void ensureSchema() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS organization_unit (
              id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
              tenant_id BIGINT NOT NULL,
              parent_id BIGINT DEFAULT NULL,
              type VARCHAR(30) NOT NULL,
              name VARCHAR(120) NOT NULL,
              code VARCHAR(80) DEFAULT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              KEY idx_org_tenant_type (tenant_id, type),
              KEY idx_org_parent (parent_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学校组织架构'
            """);
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS user_group (
              id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
              tenant_id BIGINT NOT NULL,
              name VARCHAR(120) NOT NULL,
              description VARCHAR(500) DEFAULT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uk_user_group_tenant_name (tenant_id, name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户组'
            """);
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS user_group_member (
              id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
              tenant_id BIGINT NOT NULL,
              group_id BIGINT NOT NULL,
              user_id BIGINT NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uk_user_group_member (group_id, user_id),
              KEY idx_user_group_member_user (tenant_id, user_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户组成员'
            """);
        addColumn("users", "school_id", "BIGINT DEFAULT NULL COMMENT '学校组织ID'");
        addColumn("users", "college_id", "BIGINT DEFAULT NULL COMMENT '学院组织ID'");
        addColumn("users", "class_id", "BIGINT DEFAULT NULL COMMENT '班级组织ID'");
        addColumn("users", "school_name", "VARCHAR(120) DEFAULT NULL COMMENT '学校'");
        addColumn("users", "college_name", "VARCHAR(120) DEFAULT NULL COMMENT '学院'");
        addColumn("users", "class_name", "VARCHAR(120) DEFAULT NULL COMMENT '班级'");
        addColumn("users", "user_group", "VARCHAR(120) DEFAULT NULL COMMENT '主用户组'");
    }

    private void addColumn(String table, String column, String ddl) {
        try {
            jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + ddl);
        } catch (Exception ignored) {
        }
    }

    public List<Map<String, Object>> listUsers(Long tenantId, Long operatorUserId, String operatorRole) {
        ensureDefaultOrganization(tenantId);
        StringBuilder sql = new StringBuilder("""
            SELECT u.id, u.tenant_id tenantId, u.username, u.email, u.role,
                   u.school_id schoolId, u.college_id collegeId, u.class_id classId,
                   COALESCE(NULLIF(u.school_name, ''), '未设置学校') schoolName,
                   COALESCE(NULLIF(u.college_name, ''), '未设置学院') collegeName,
                   COALESCE(NULLIF(u.class_name, ''), '未设置班级') className,
                   COALESCE(NULLIF(u.user_group, ''), '') userGroup,
                   u.created_at createdAt,
                   ug.groupIds,
                   ug.groupNames
            FROM users u
            LEFT JOIN (
                SELECT gm.tenant_id, gm.user_id,
                       GROUP_CONCAT(g.id ORDER BY g.name SEPARATOR ',') groupIds,
                       GROUP_CONCAT(g.name ORDER BY g.name SEPARATOR '、') groupNames
                FROM user_group_member gm
                JOIN user_group g ON g.id = gm.group_id AND g.tenant_id = gm.tenant_id AND g.status = 'ACTIVE'
                GROUP BY gm.tenant_id, gm.user_id
            ) ug ON ug.user_id = u.id AND ug.tenant_id = u.tenant_id
            WHERE u.tenant_id = ?
            """);
        List<Object> params = new ArrayList<>();
        params.add(tenantId);
        dataScopeService.appendUserOrgFilter(sql, params, operatorUserId, operatorRole);
        sql.append(" ORDER BY u.created_at DESC ");
        return jdbc.queryForList(sql.toString(), params.toArray());
    }

    public User getUserById(Long id, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        AdminAccess.assertSameTenant(operatorRole, operatorTenantId, user.getTenantId());
        dataScopeService.assertUserAccess(operatorUserId, operatorRole, user);
        return user;
    }

    @Transactional
    public void createUser(AdminCreateUserRequest request, Long operatorUserId, Long operatorTenantId, String operatorRole) {
        AdminAccess.assertCanManageUsers(operatorRole);
        String role = normalizeRole(request.getRole());
        AdminAccess.assertCanAssignRole(operatorRole, role);
        if (userMapper.findByUsername(request.getUsername()) != null) {
            throw new RuntimeException("用户名已存在");
        }
        if (userMapper.findByEmail(request.getEmail()) != null) {
            throw new RuntimeException("邮箱已注册");
        }

        Long tenantId = request.getTenantId() != null ? request.getTenantId() : operatorTenantId;
        if (!AdminAccess.isSuperAdmin(operatorRole)) {
            tenantId = operatorTenantId;
        }
        if (tenantId == null) tenantId = 1L;
        if (!AdminAccess.isSuperAdmin(operatorRole) && operatorTenantId != null && !operatorTenantId.equals(tenantId)) {
            throw new RuntimeException("无权在其他组织创建用户");
        }
        ensureDefaultOrganization(tenantId);

        Long schoolId = request.getSchoolId();
        Long collegeId = request.getCollegeId();
        Long classId = request.getClassId();
        // 教师创建账号：必须选自己管辖范围内的班级；学校/学院由班级推导，不可越权
        if ("TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            List<Map<String, Object>> scopes = dataScopeService.resolveTeachingScopes(operatorUserId);
            if (scopes.isEmpty()) {
                throw new RuntimeException("当前教师账号未配置可管辖班级，无法创建用户。请联系管理员配置教学管辖范围");
            }
            if (classId == null && scopes.size() == 1) {
                classId = longValue(scopes.get(0).get("classId"));
            }
            if (classId == null) {
                throw new RuntimeException("请选择要创建到的班级（你可管辖多个班级时必须指定）");
            }
            Map<String, Object> matched = null;
            for (Map<String, Object> scope : scopes) {
                if (classId.equals(longValue(scope.get("classId")))) {
                    matched = scope;
                    break;
                }
            }
            if (matched == null) {
                throw new RuntimeException("无权在该班级创建用户，仅可在自己管辖的班级下操作");
            }
            schoolId = longValue(matched.get("schoolId"));
            collegeId = longValue(matched.get("collegeId"));
            classId = longValue(matched.get("classId"));
        } else if (!AdminAccess.isSuperAdmin(operatorRole)) {
            User operator = dataScopeService.loadUser(operatorUserId);
            if (schoolId == null) {
                schoolId = operator.getSchoolId();
            }
            if (collegeId == null) {
                collegeId = operator.getCollegeId();
            }
            if (classId == null && operator.getClassId() != null) {
                classId = operator.getClassId();
            }
        }
        dataScopeService.assertOrgAssignment(operatorUserId, operatorRole, schoolId, collegeId, classId);

        User user = new User();
        user.setTenantId(tenantId);
        user.setUsername(request.getUsername().trim());
        user.setEmail(request.getEmail().trim());
        user.setPassword(cn.hutool.crypto.digest.BCrypt.hashpw(
                request.getPassword(),
                cn.hutool.crypto.digest.BCrypt.gensalt()
        ));
        user.setRole(role);
        // 创建时先写入组织归属，避免后续 updateUserOrganization 的 assertUserAccess
        // 因 classId/schoolId 仍为 null 而误报「无权访问该用户」（教师创建学生时必现）
        user.setSchoolId(schoolId);
        user.setCollegeId(collegeId);
        user.setClassId(classId);
        userMapper.insert(user);
        Map<String, Object> organizationBody = new HashMap<>();
        organizationBody.put("schoolId", schoolId);
        organizationBody.put("collegeId", collegeId);
        organizationBody.put("classId", classId);
        organizationBody.put("groupIds", request.getGroupIds() == null ? List.of() : request.getGroupIds());
        updateUserOrganization(user.getId(), tenantId, organizationBody, operatorUserId, operatorRole);
    }

    public void updateUserRole(Long userId, String role, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        AdminAccess.assertCanManageUsers(operatorRole);
        String normalizedRole = normalizeRole(role);
        AdminAccess.assertCanAssignRole(operatorRole, normalizedRole);
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        AdminAccess.assertSameTenant(operatorRole, operatorTenantId, user.getTenantId());
        dataScopeService.assertUserAccess(operatorUserId, operatorRole, user);
        assertTeacherCanModifyTarget(operatorRole, user.getRole());
        user.setRole(normalizedRole);
        userMapper.updateById(user);
    }

    /**
     * 管理端修改登录用户名（非展示昵称）。
     * 校验长度与唯一性，并沿用与改角色相同的数据范围权限。
     * 仅 UPDATE username 字段，避免 updateById 误伤密码等列。
     */
    @Transactional
    public void updateUserUsername(Long userId, String username, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        AdminAccess.assertCanManageUsers(operatorRole);
        if (userId == null) {
            throw new RuntimeException("用户 ID 无效");
        }
        String next = username == null ? "" : username.trim();
        if (next.length() < 2 || next.length() > 20) {
            throw new RuntimeException("用户名长度为 2-20 位");
        }
        // 与新增用户一致：允许中英文、数字、下划线；兼容历史点/短横线账号
        if (!next.matches("^[\\w\\u4e00-\\u9fa5.-]+$")) {
            throw new RuntimeException("用户名仅支持中英文、数字、下划线、点与短横线");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        AdminAccess.assertSameTenant(operatorRole, operatorTenantId, user.getTenantId());
        dataScopeService.assertUserAccess(operatorUserId, operatorRole, user);
        assertTeacherCanModifyTarget(operatorRole, user.getRole());
        if (next.equals(user.getUsername())) {
            return;
        }
        User exists = userMapper.findByUsername(next);
        if (exists != null && !exists.getId().equals(userId)) {
            throw new RuntimeException("用户名已存在，请换一个");
        }
        int updated = jdbc.update("UPDATE users SET username = ? WHERE id = ?", next, userId);
        if (updated != 1) {
            throw new RuntimeException("用户名更新失败，请刷新后重试");
        }
    }

    /**
     * 管理端一键将目标用户密码重置为默认值 {@link #DEFAULT_RESET_PASSWORD}。
     * 使用与注册/新增用户相同的 Hutool BCrypt，保证可用该明文登录。
     * 仅 UPDATE password 字段，避免 updateById 误伤其它列；不改动用户自助改密。
     */
    @Transactional
    public void resetUserPassword(Long userId, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        AdminAccess.assertCanManageUsers(operatorRole);
        if (userId == null) {
            throw new RuntimeException("用户 ID 无效");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        AdminAccess.assertSameTenant(operatorRole, operatorTenantId, user.getTenantId());
        dataScopeService.assertUserAccess(operatorUserId, operatorRole, user);
        assertTeacherCanModifyTarget(operatorRole, user.getRole());
        String hashed = cn.hutool.crypto.digest.BCrypt.hashpw(
                DEFAULT_RESET_PASSWORD,
                cn.hutool.crypto.digest.BCrypt.gensalt()
        );
        int updated = jdbc.update("UPDATE users SET password = ? WHERE id = ?", hashed, userId);
        if (updated != 1) {
            throw new RuntimeException("密码重置失败，请刷新后重试");
        }
    }

    @Transactional
    public void updateUserOrganization(Long userId, Long tenantId, Map<String, Object> body, Long operatorUserId, String operatorRole) {
        assertTenantUser(userId, tenantId);
        User target = userMapper.selectById(userId);
        if (target == null) {
            throw new RuntimeException("用户不存在");
        }
        // 尚未绑定组织的用户（含刚 insert、正准备写归属的创建路径）：
        // 不能按 class/school 做数据范围校验，否则教师创建账号会误报「无权访问该用户」。
        // 目标班级权限由下方 assertOrgAssignment / 教师管辖范围强制保证。
        boolean unassigned = target.getSchoolId() == null && target.getClassId() == null;
        if (!unassigned) {
            dataScopeService.assertUserAccess(operatorUserId, operatorRole, target);
        }
        assertTeacherCanModifyTarget(operatorRole, target.getRole());

        Long schoolId = longValue(body.get("schoolId"));
        Long collegeId = longValue(body.get("collegeId"));
        Long classId = longValue(body.get("classId"));
        if ("TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            // 教师改归属：仅允许改到自己管辖班级
            List<Map<String, Object>> scopes = dataScopeService.resolveTeachingScopes(operatorUserId);
            Long requestedClassId = classId;
            if (requestedClassId == null && scopes.size() == 1) {
                requestedClassId = longValue(scopes.get(0).get("classId"));
            }
            final Long targetClassId = requestedClassId;
            Map<String, Object> matched = null;
            for (Map<String, Object> s : scopes) {
                if (targetClassId != null && targetClassId.equals(longValue(s.get("classId")))) {
                    matched = s;
                    break;
                }
            }
            if (matched == null) {
                throw new RuntimeException("教师仅可在自己管辖的班级下分配用户");
            }
            schoolId = longValue(matched.get("schoolId"));
            collegeId = longValue(matched.get("collegeId"));
            classId = longValue(matched.get("classId"));
        }
        dataScopeService.assertOrgAssignment(operatorUserId, operatorRole, schoolId, collegeId, classId);
        Map<String, Object> school = unitOrNull(tenantId, schoolId, "SCHOOL");
        Map<String, Object> college = unitOrNull(tenantId, collegeId, "COLLEGE");
        Map<String, Object> clazz = unitOrNull(tenantId, classId, "CLASS");
        List<Long> groupIds = longList(body.get("groupIds"));
        List<Map<String, Object>> groups = groupsByIds(tenantId, groupIds);
        if (groups.size() != groupIds.size()) {
            throw new RuntimeException("用户组不属于当前租户或已停用");
        }
        String primaryGroup = groups.isEmpty() ? null : String.valueOf(groups.get(0).get("name"));
        jdbc.update("""
            UPDATE users
            SET school_id = ?, college_id = ?, class_id = ?,
                school_name = ?, college_name = ?, class_name = ?, user_group = ?
            WHERE tenant_id = ? AND id = ?
            """,
                schoolId, collegeId, classId,
                nameOrNull(school), nameOrNull(college), nameOrNull(clazz), primaryGroup,
                tenantId, userId);
        jdbc.update("DELETE FROM user_group_member WHERE tenant_id = ? AND user_id = ?", tenantId, userId);
        for (Long groupId : groupIds) {
            jdbc.update("""
                INSERT INTO user_group_member (tenant_id, group_id, user_id)
                VALUES (?, ?, ?)
                ON DUPLICATE KEY UPDATE tenant_id = VALUES(tenant_id)
                """, tenantId, groupId, userId);
        }

        // 管理员可为教师配置「一师多班」管辖范围
        if (body.containsKey("teachingClassIds")
                && !AdminAccess.normalizeRole(target.getRole()).isEmpty()
                && "TEACHER".equals(AdminAccess.normalizeRole(target.getRole()))
                && !AdminAccess.normalizeRole(operatorRole).equals("TEACHER")) {
            dataScopeService.replaceTeachingScopes(tenantId, userId, longList(body.get("teachingClassIds")));
        } else if ("TEACHER".equals(AdminAccess.normalizeRole(target.getRole()))
                && classId != null
                && !AdminAccess.normalizeRole(operatorRole).equals("TEACHER")) {
            // 仅改了主班级时，至少保证主班在管辖范围内
            Integer exists = jdbc.queryForObject(
                    "SELECT COUNT(*) FROM teacher_teaching_scope WHERE user_id = ? AND class_id = ?",
                    Integer.class, userId, classId);
            if (exists == null || exists == 0) {
                jdbc.update("""
                    INSERT INTO teacher_teaching_scope (tenant_id, user_id, school_id, college_id, class_id)
                    VALUES (?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE school_id = VALUES(school_id), college_id = VALUES(college_id)
                    """, tenantId, userId, schoolId, collegeId, classId);
            }
        }
    }

    public void deleteUser(Long userId, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        AdminAccess.assertCanManageUsers(operatorRole);
        if (userId != null && userId.equals(operatorUserId)) {
            throw new RuntimeException("不能删除当前登录账号");
        }
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        AdminAccess.assertSameTenant(operatorRole, operatorTenantId, user.getTenantId());
        dataScopeService.assertUserAccess(operatorUserId, operatorRole, user);
        assertTeacherCanModifyTarget(operatorRole, user.getRole());
        jdbc.update("DELETE FROM user_group_member WHERE user_id = ?", userId);
        userMapper.deleteById(userId);
    }

    @Transactional
    public BatchDeleteResult deleteUsers(List<Long> userIds, Long operatorUserId, String operatorRole, Long operatorTenantId) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> ids = normalizeIds(userIds);
        result.setRequested(ids.size());
        for (Long id : ids) {
            try {
                deleteUser(id, operatorUserId, operatorRole, operatorTenantId);
                result.addDeleted();
            } catch (Exception e) {
                result.addFailure(id, e.getMessage());
            }
        }
        return result;
    }

    public void changePassword(Long userId, String oldPassword, String newPassword) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            throw new RuntimeException("用户不存在");
        }
        if (!encoder.matches(oldPassword, user.getPassword())) {
            throw new RuntimeException("原密码错误");
        }
        user.setPassword(encoder.encode(newPassword));
        userMapper.updateById(user);
    }

    public Map<String, Object> organizationOptions(Long tenantId, Long operatorUserId, String operatorRole) {
        ensureDefaultOrganization(tenantId);
        List<Map<String, Object>> units = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, parent_id parentId, type, name, code, status, created_at createdAt
            FROM organization_unit
            WHERE tenant_id = ? AND status = 'ACTIVE'
            ORDER BY FIELD(type, 'SCHOOL', 'COLLEGE', 'CLASS'), parent_id, name, id
            """, tenantId);
        if (!dataScopeService.bypassOrgScope(operatorRole)) {
            units = filterUnitsForOperator(units, operatorUserId, operatorRole);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("units", units);
        result.put("groups", jdbc.queryForList("""
            SELECT id, tenant_id tenantId, name, description, status, created_at createdAt
            FROM user_group
            WHERE tenant_id = ? AND status = 'ACTIVE'
            ORDER BY name, id
            """, tenantId));
        // 供教师端创建账号：管辖范围列表（支持一师多班）
        if (operatorUserId != null) {
            try {
                User operator = dataScopeService.loadUser(operatorUserId);
                List<Map<String, Object>> teachingScopes = dataScopeService.resolveTeachingScopes(operatorUserId);
                result.put("teachingScopes", teachingScopes);
                Map<String, Object> scope = new LinkedHashMap<>();
                if (!teachingScopes.isEmpty()) {
                    Map<String, Object> first = teachingScopes.get(0);
                    scope.put("schoolId", first.get("schoolId"));
                    scope.put("collegeId", first.get("collegeId"));
                    scope.put("classId", first.get("classId"));
                    scope.put("schoolName", first.get("schoolName"));
                    scope.put("collegeName", first.get("collegeName"));
                    scope.put("className", first.get("className"));
                } else {
                    scope.put("schoolId", operator.getSchoolId());
                    scope.put("collegeId", operator.getCollegeId());
                    scope.put("classId", operator.getClassId());
                    scope.put("schoolName", operator.getSchoolName());
                    scope.put("collegeName", operator.getCollegeName());
                    scope.put("className", operator.getClassName());
                }
                scope.put("role", operator.getRole());
                scope.put("scopeCount", teachingScopes.size());
                result.put("operatorScope", scope);
            } catch (Exception ignored) {
            }
        }
        return result;
    }

    private List<Map<String, Object>> filterUnitsForOperator(List<Map<String, Object>> units, Long operatorUserId, String operatorRole) {
        if ("TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            List<Map<String, Object>> scopes = dataScopeService.resolveTeachingScopes(operatorUserId);
            if (scopes.isEmpty()) {
                return List.of();
            }
            Set<Long> schoolIdSet = scopes.stream().map(s -> longValue(s.get("schoolId"))).filter(Objects::nonNull).collect(Collectors.toSet());
            Set<Long> collegeIdSet = scopes.stream().map(s -> longValue(s.get("collegeId"))).filter(Objects::nonNull).collect(Collectors.toSet());
            Set<Long> classIdSet = scopes.stream().map(s -> longValue(s.get("classId"))).filter(Objects::nonNull).collect(Collectors.toSet());
            List<Map<String, Object>> filtered = new ArrayList<>();
            for (Map<String, Object> unit : units) {
                String type = String.valueOf(unit.get("type"));
                Long id = longValue(unit.get("id"));
                if ("SCHOOL".equals(type) && schoolIdSet.contains(id)) {
                    filtered.add(unit);
                } else if ("COLLEGE".equals(type) && collegeIdSet.contains(id)) {
                    filtered.add(unit);
                } else if ("CLASS".equals(type) && classIdSet.contains(id)) {
                    filtered.add(unit);
                }
            }
            return filtered;
        }

        List<Long> schoolIds = dataScopeService.accessibleSchoolIds(operatorUserId, operatorRole);
        if (schoolIds == null || schoolIds.isEmpty()) {
            return List.of();
        }
        Long collegeId = dataScopeService.accessibleCollegeId(operatorUserId, operatorRole);
        Set<Long> schoolIdSet = new HashSet<>(schoolIds);
        List<Map<String, Object>> schools = units.stream()
                .filter(unit -> "SCHOOL".equals(unit.get("type")) && schoolIdSet.contains(longValue(unit.get("id"))))
                .toList();
        Set<Long> allowedCollegeIds = new HashSet<>();
        for (Map<String, Object> college : units) {
            if (!"COLLEGE".equals(college.get("type"))) continue;
            Long parentId = longValue(college.get("parentId"));
            if (!schoolIdSet.contains(parentId)) continue;
            if (collegeId != null && !collegeId.equals(longValue(college.get("id")))) continue;
            allowedCollegeIds.add(longValue(college.get("id")));
        }
        List<Map<String, Object>> filtered = new ArrayList<>(schools);
        for (Map<String, Object> college : units) {
            if ("COLLEGE".equals(college.get("type")) && allowedCollegeIds.contains(longValue(college.get("id")))) {
                filtered.add(college);
            }
        }
        for (Map<String, Object> clazz : units) {
            if (!"CLASS".equals(clazz.get("type"))) continue;
            if (!allowedCollegeIds.contains(longValue(clazz.get("parentId")))) continue;
            filtered.add(clazz);
        }
        return filtered;
    }

    private void assertTeacherCanModifyTarget(String operatorRole, String targetRole) {
        if (!"TEACHER".equals(AdminAccess.normalizeRole(operatorRole))) {
            return;
        }
        String target = AdminAccess.normalizeRole(targetRole);
        if ("ADMIN".equals(target) || "SCHOOL_ADMIN".equals(target)) {
            throw new RuntimeException("教师无权修改该角色用户");
        }
    }

    private List<Long> normalizeIds(List<Long> ids) {
        if (ids == null) return List.of();
        return ids.stream()
                .filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.toList());
    }

    public Map<String, Object> createOrganizationUnit(Long tenantId, Map<String, Object> body) {
        ensureDefaultOrganization(tenantId);
        String type = requiredText(body.get("type"), "组织类型不能为空").toUpperCase(Locale.ROOT);
        if (!ORG_TYPES.contains(type)) throw new RuntimeException("不支持的组织类型: " + type);
        Long parentId = longValue(body.get("parentId"));
        if (parentId != null) assertTenantUnit(tenantId, parentId);
        jdbc.update("""
            INSERT INTO organization_unit (tenant_id, parent_id, type, name, code)
            VALUES (?, ?, ?, ?, ?)
            """, tenantId, parentId, type, requiredText(body.get("name"), "组织名称不能为空"), text(body.get("code")));
        Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return jdbc.queryForMap("SELECT id, tenant_id tenantId, parent_id parentId, type, name, code, status, created_at createdAt FROM organization_unit WHERE id = ?", id);
    }

    public Map<String, Object> updateOrganizationUnit(Long tenantId, Long id, Map<String, Object> body) {
        ensureDefaultOrganization(tenantId);
        assertTenantUnit(tenantId, id);
        String type = requiredText(body.get("type"), "组织类型不能为空").toUpperCase(Locale.ROOT);
        if (!ORG_TYPES.contains(type)) throw new RuntimeException("不支持的组织类型: " + type);
        Long parentId = longValue(body.get("parentId"));
        if (parentId != null) {
            if (parentId.equals(id)) throw new RuntimeException("上级组织不能选择自己");
            assertTenantUnit(tenantId, parentId);
        }
        jdbc.update("""
            UPDATE organization_unit
            SET parent_id = ?, type = ?, name = ?, code = ?
            WHERE tenant_id = ? AND id = ? AND status = 'ACTIVE'
            """, parentId, type, requiredText(body.get("name"), "组织名称不能为空"), text(body.get("code")), tenantId, id);
        return jdbc.queryForMap("SELECT id, tenant_id tenantId, parent_id parentId, type, name, code, status, created_at createdAt FROM organization_unit WHERE tenant_id = ? AND id = ?", tenantId, id);
    }

    public void deleteOrganizationUnit(Long tenantId, Long id) {
        ensureDefaultOrganization(tenantId);
        assertTenantUnit(tenantId, id);
        Integer childCount = jdbc.queryForObject("SELECT COUNT(*) FROM organization_unit WHERE tenant_id = ? AND parent_id = ? AND status = 'ACTIVE'", Integer.class, tenantId, id);
        if (childCount != null && childCount > 0) throw new RuntimeException("请先删除下级组织");
        jdbc.update("UPDATE organization_unit SET status = 'INACTIVE' WHERE tenant_id = ? AND id = ?", tenantId, id);
    }

    public Map<String, Object> createUserGroup(Long tenantId, Map<String, Object> body) {
        ensureDefaultOrganization(tenantId);
        jdbc.update("""
            INSERT INTO user_group (tenant_id, name, description)
            VALUES (?, ?, ?)
            """, tenantId, requiredText(body.get("name"), "用户组名称不能为空"), text(body.get("description")));
        Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return jdbc.queryForMap("SELECT id, tenant_id tenantId, name, description, status, created_at createdAt FROM user_group WHERE id = ?", id);
    }

    public Map<String, Object> updateUserGroup(Long tenantId, Long id, Map<String, Object> body) {
        ensureDefaultOrganization(tenantId);
        assertTenantGroup(tenantId, id);
        jdbc.update("""
            UPDATE user_group
            SET name = ?, description = ?
            WHERE tenant_id = ? AND id = ? AND status = 'ACTIVE'
            """, requiredText(body.get("name"), "用户组名称不能为空"), text(body.get("description")), tenantId, id);
        return jdbc.queryForMap("SELECT id, tenant_id tenantId, name, description, status, created_at createdAt FROM user_group WHERE tenant_id = ? AND id = ?", tenantId, id);
    }

    public void deleteUserGroup(Long tenantId, Long id) {
        ensureDefaultOrganization(tenantId);
        assertTenantGroup(tenantId, id);
        jdbc.update("UPDATE user_group SET status = 'INACTIVE' WHERE tenant_id = ? AND id = ?", tenantId, id);
    }

    private void ensureDefaultOrganization(Long tenantId) {
        if (tenantId == null) return;
        Integer orgCount = jdbc.queryForObject("SELECT COUNT(*) FROM organization_unit WHERE tenant_id = ?", Integer.class, tenantId);
        if (orgCount != null && orgCount == 0) {
            String tenantName = "默认学校";
            try {
                tenantName = jdbc.queryForObject("SELECT name FROM tenant WHERE id = ?", String.class, tenantId);
            } catch (Exception ignored) {
            }
            jdbc.update("INSERT INTO organization_unit (tenant_id, type, name, code) VALUES (?, 'SCHOOL', ?, ?)", tenantId, tenantName, "DEFAULT");
        }
        Integer groupCount = jdbc.queryForObject("SELECT COUNT(*) FROM user_group WHERE tenant_id = ?", Integer.class, tenantId);
        if (groupCount != null && groupCount == 0) {
            List<String> defaults = List.of("学生组", "指导教师组", "评委组", "专家组");
            for (String name : defaults) {
                jdbc.update("INSERT IGNORE INTO user_group (tenant_id, name, description) VALUES (?, ?, ?)", tenantId, name, "系统默认用户组");
            }
        }
    }

    private String normalizeRole(String role) {
        if (role == null) {
            throw new RuntimeException("角色不能为空");
        }
        String normalized = role.trim().toUpperCase();
        if (!ALLOWED_ROLES.contains(normalized)) {
            throw new RuntimeException("不支持的角色: " + role);
        }
        return normalized;
    }

    private void assertTenantUser(Long userId, Long tenantId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM users WHERE tenant_id = ? AND id = ?", Integer.class, tenantId, userId);
        if (count == null || count == 0) throw new RuntimeException("用户不属于当前租户");
    }

    private void assertTenantUnit(Long tenantId, Long unitId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM organization_unit WHERE tenant_id = ? AND id = ? AND status = 'ACTIVE'", Integer.class, tenantId, unitId);
        if (count == null || count == 0) throw new RuntimeException("组织节点不存在");
    }

    private void assertTenantGroup(Long tenantId, Long groupId) {
        Integer count = jdbc.queryForObject("SELECT COUNT(*) FROM user_group WHERE tenant_id = ? AND id = ? AND status = 'ACTIVE'", Integer.class, tenantId, groupId);
        if (count == null || count == 0) throw new RuntimeException("用户组不存在");
    }

    private Map<String, Object> unitOrNull(Long tenantId, Long unitId, String type) {
        if (unitId == null) return null;
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT id, name FROM organization_unit WHERE tenant_id = ? AND id = ? AND type = ? AND status = 'ACTIVE'", tenantId, unitId, type);
        if (rows.isEmpty()) throw new RuntimeException(type + " 组织节点不存在");
        return rows.get(0);
    }

    private List<Map<String, Object>> groupsByIds(Long tenantId, List<Long> groupIds) {
        if (groupIds.isEmpty()) return List.of();
        String placeholders = groupIds.stream().map(id -> "?").collect(Collectors.joining(","));
        List<Object> params = new ArrayList<>();
        params.add(tenantId);
        params.addAll(groupIds);
        return jdbc.queryForList("SELECT id, name FROM user_group WHERE tenant_id = ? AND status = 'ACTIVE' AND id IN (" + placeholders + ")", params.toArray());
    }

    private Long longValue(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return null;
        if (value instanceof Number n) return n.longValue();
        return Long.parseLong(String.valueOf(value));
    }

    private List<Long> longList(Object value) {
        if (!(value instanceof Collection<?> collection)) return List.of();
        return collection.stream()
                .map(this::longValue)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
    }

    private String requiredText(Object value, String message) {
        String text = text(value);
        if (text == null || text.isBlank()) throw new RuntimeException(message);
        return text;
    }

    private String text(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }

    private String nameOrNull(Map<String, Object> row) {
        return row == null ? null : String.valueOf(row.get("name"));
    }
}
