package com.orep.backend.config;

import com.orep.backend.security.AdminAccess;
import com.orep.backend.service.MonitorService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private MonitorService monitorService;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        request.setAttribute("monitorStartTime", System.currentTimeMillis());
        // OPTIONS 请求放行
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        String token = request.getHeader("Authorization");
        if (token != null && token.startsWith("Bearer ")) {
            token = token.substring(7);
        } else {
            // 也支持 query 参数传 token（用于下载等浏览器直接访问的场景）
            token = request.getParameter("t");
        }

        if (token != null && jwtUtil.validateToken(token)) {
            String role = jwtUtil.getRole(token);
            request.setAttribute("userId", jwtUtil.getUserId(token));
            request.setAttribute("username", jwtUtil.getUsername(token));
            request.setAttribute("role", role);
            request.setAttribute("tenantId", jwtUtil.getTenantId(token));

            String path = request.getRequestURI();
            String method = request.getMethod();
            // 教师端 API：学生等角色禁止访问（含门户与教师专属能力）
            if (AdminAccess.isTeacherPortalPath(path) && !AdminAccess.canAccessTeacherPortal(role)) {
                deny(response, 403, "仅教师或管理员可访问教师端");
                return false;
            }
            if (AdminAccess.isAdminPanelPath(path)) {
                if (AdminAccess.isUserManagementPath(path)) {
                    if (!AdminAccess.canManageUsers(role)) {
                        deny(response, 403, "无权管理用户");
                        return false;
                    }
                } else if (!AdminAccess.canAccessAdminPanel(role)) {
                    deny(response, 403, "无权访问管理后台");
                    return false;
                }
            }
            if (AdminAccess.isSuperAdminOnlyPath(path, method) && !AdminAccess.isSuperAdmin(role)) {
                deny(response, 403, "仅平台管理员可执行该操作");
                return false;
            }
            if (AdminAccess.isTenantWritePath(path, method)) {
                if (AdminAccess.isOrgStructureWritePath(path, method) && !AdminAccess.canWriteTenantAdmin(role)) {
                    deny(response, 403, "无权修改组织架构");
                    return false;
                }
                if (AdminAccess.isUserManagementPath(path)) {
                    if (!AdminAccess.canManageUsers(role)) {
                        deny(response, 403, "无权管理用户");
                        return false;
                    }
                } else if (AdminAccess.isTeachingResourcePath(path)) {
                    if (!AdminAccess.canManageOwnedTeachingResources(role)) {
                        deny(response, 403, "无权管理教学资源");
                        return false;
                    }
                } else if (!AdminAccess.canWriteTenantAdmin(role)) {
                    deny(response, 403, "无权修改管理数据");
                    return false;
                }
            }
            return true;
        }

        deny(response, 401, "未登录或token已过期");
        return false;
    }

    private void deny(HttpServletResponse response, int status, String message) throws Exception {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        String safeMessage = message == null ? "" : message.replace("\"", "\\\"");
        response.getWriter().write("{\"code\":" + status + ",\"message\":\"" + safeMessage + "\"}");
    }

    @Override
    public void afterCompletion(
            HttpServletRequest request,
            HttpServletResponse response,
            Object handler,
            Exception ex
    ) {
        Object start = request.getAttribute("monitorStartTime");
        long durationMs = start instanceof Long ? System.currentTimeMillis() - (Long) start : 0L;
        monitorService.recordBackendAccess(request, response.getStatus(), durationMs, ex);
    }
}
