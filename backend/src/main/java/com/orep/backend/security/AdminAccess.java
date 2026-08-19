package com.orep.backend.security;

import java.util.Locale;
import java.util.Set;

/**
 * 管理后台 RBAC：平台管理员 / 学校领导 / 教师 / 普通用户。
 */
public final class AdminAccess {

    private AdminAccess() {
    }

    public static final Set<String> ADMIN_PANEL_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN", "TEACHER");
    public static final Set<String> TENANT_WRITE_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN");
    public static final Set<String> USER_MANAGEMENT_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN", "TEACHER");
    public static final Set<String> TEACHER_ASSIGNABLE_ROLES = Set.of("STUDENT", "TEACHER", "REVIEWER", "EXPERT");
    public static final Set<String> SUPER_ADMIN_ROLES = Set.of("ADMIN");
    /** 教师端门户 / 教师小启：学生账号禁止进入 */
    public static final Set<String> TEACHER_PORTAL_ROLES = Set.of("TEACHER", "ADMIN", "SCHOOL_ADMIN");

    public static String normalizeRole(String role) {
        return role == null ? "" : role.trim().toUpperCase(Locale.ROOT);
    }

    public static boolean canAccessTeacherPortal(String role) {
        return TEACHER_PORTAL_ROLES.contains(normalizeRole(role));
    }

    public static boolean isTeacherPortalPath(String path) {
        if (path == null) return false;
        return path.startsWith("/api/teacher/")
                || path.startsWith("/api/teacher");
    }

    public static boolean canAccessAdminPanel(String role) {
        return ADMIN_PANEL_ROLES.contains(normalizeRole(role));
    }

    public static boolean canWriteTenantAdmin(String role) {
        return TENANT_WRITE_ROLES.contains(normalizeRole(role));
    }

    public static boolean canManageUsers(String role) {
        return USER_MANAGEMENT_ROLES.contains(normalizeRole(role));
    }

    public static boolean canManageOwnedTeachingResources(String role) {
        return ADMIN_PANEL_ROLES.contains(normalizeRole(role));
    }

    public static boolean isTeachingResourcePath(String path) {
        return path != null
                && (path.startsWith("/api/admin/courses")
                || path.startsWith("/api/admin/exams"));
    }

    public static boolean isUserManagementPath(String path) {
        return path != null && path.startsWith("/api/user/");
    }

    public static boolean isOrgStructureWritePath(String path, String method) {
        if (path == null || isReadMethod(method)) {
            return false;
        }
        return path.startsWith("/api/user/organization/units")
                || path.startsWith("/api/user/organization/groups");
    }

    public static boolean isReadMethod(String method) {
        return "GET".equalsIgnoreCase(method) || "HEAD".equalsIgnoreCase(method);
    }

    public static boolean isSuperAdmin(String role) {
        return SUPER_ADMIN_ROLES.contains(normalizeRole(role));
    }

    public static void assertAdminPanel(String role) {
        if (!canAccessAdminPanel(role)) {
            throw new RuntimeException("无权访问管理后台");
        }
    }

    public static void assertTenantWrite(String role) {
        if (!canWriteTenantAdmin(role)) {
            throw new RuntimeException("无权修改管理数据");
        }
    }

    public static void assertCanManageUsers(String role) {
        if (!canManageUsers(role)) {
            throw new RuntimeException("无权管理用户");
        }
    }

    public static void assertSuperAdmin(String role) {
        if (!isSuperAdmin(role)) {
            throw new RuntimeException("仅平台管理员可执行该操作");
        }
    }

    public static void assertSameTenant(String operatorRole, Long operatorTenantId, Long resourceTenantId) {
        if (isSuperAdmin(operatorRole)) {
            return;
        }
        if (operatorTenantId == null || resourceTenantId == null || !operatorTenantId.equals(resourceTenantId)) {
            throw new RuntimeException("无权访问其他组织的数据");
        }
    }

    public static void assertCanAssignRole(String operatorRole, String targetRole) {
        String normalized = normalizeRole(targetRole);
        String operator = normalizeRole(operatorRole);
        if ("ADMIN".equals(normalized)) {
            assertSuperAdmin(operatorRole);
        }
        if ("SCHOOL_ADMIN".equals(normalized) && !isSuperAdmin(operatorRole)) {
            throw new RuntimeException("仅平台管理员可分配学校管理员角色");
        }
        if ("TEACHER".equals(operator) && !TEACHER_ASSIGNABLE_ROLES.contains(normalized)) {
            throw new RuntimeException("教师仅可分配学生、教师、评委、专家角色");
        }
    }

    public static boolean isAdminPanelPath(String path) {
        if (path == null) return false;
        if (path.startsWith("/api/admin/")) return true;
        if (path.startsWith("/api/user/")) return true;
        return path.startsWith("/api/home/admin/");
    }

    public static boolean isSuperAdminOnlyPath(String path, String method) {
        if (path != null && path.startsWith("/api/admin/monitor")) {
            return true;
        }
        if (path == null || !path.startsWith("/api/admin/maintenance")) {
            return false;
        }
        return !"GET".equalsIgnoreCase(method) && !"HEAD".equalsIgnoreCase(method);
    }

    public static boolean isTenantWritePath(String path, String method) {
        if (path == null || "GET".equalsIgnoreCase(method) || "HEAD".equalsIgnoreCase(method)) {
            return false;
        }
        if (path.startsWith("/api/admin/monitor")) {
            return false;
        }
        if (path.startsWith("/api/admin/")) {
            return true;
        }
        if (path.startsWith("/api/user/")) {
            return true;
        }
        return path.startsWith("/api/home/admin/");
    }
}
