package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.AdminCreateUserRequest;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.entity.User;
import com.orep.backend.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/list")
    public Result<List<Map<String, Object>>> list(HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(userService.listUsers(tenantId, operatorUserId, role));
    }

    @GetMapping("/{id}")
    public Result<User> getById(@PathVariable Long id, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(userService.getUserById(id, operatorUserId, role, tenantId));
    }

    @PostMapping
    public Result<Void> create(@Valid @RequestBody AdminCreateUserRequest request, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        userService.createUser(request, operatorUserId, tenantId, role);
        return Result.success();
    }

    @PostMapping("/{id}/role")
    public Result<Void> updateRole(@PathVariable Long id, @RequestBody Map<String, String> params, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        userService.updateUserRole(id, params.get("role"), operatorUserId, role, tenantId);
        return Result.success();
    }

    /** 管理端修改登录用户名 */
    @PostMapping("/{id}/username")
    public Result<Void> updateUsername(@PathVariable Long id, @RequestBody Map<String, String> params, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        userService.updateUserUsername(id, params.get("username"), operatorUserId, role, tenantId);
        return Result.success();
    }

    @PostMapping("/{id}/organization")
    public Result<Void> updateOrganization(@PathVariable Long id, @RequestBody Map<String, Object> params, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        userService.updateUserOrganization(id, tenantId, params, operatorUserId, role);
        return Result.success();
    }

    @GetMapping("/organization/options")
    public Result<Map<String, Object>> organizationOptions(HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long operatorUserId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(userService.organizationOptions(tenantId, operatorUserId, role));
    }

    @PostMapping("/organization/units")
    public Result<Map<String, Object>> createOrganizationUnit(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(userService.createOrganizationUnit(tenantId, body));
    }

    @PutMapping("/organization/units/{id}")
    public Result<Map<String, Object>> updateOrganizationUnit(@PathVariable Long id, @RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(userService.updateOrganizationUnit(tenantId, id, body));
    }

    @DeleteMapping("/organization/units/{id}")
    public Result<Void> deleteOrganizationUnit(@PathVariable Long id, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        userService.deleteOrganizationUnit(tenantId, id);
        return Result.success();
    }

    @PostMapping("/organization/groups")
    public Result<Map<String, Object>> createUserGroup(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(userService.createUserGroup(tenantId, body));
    }

    @PutMapping("/organization/groups/{id}")
    public Result<Map<String, Object>> updateUserGroup(@PathVariable Long id, @RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(userService.updateUserGroup(tenantId, id, body));
    }

    @DeleteMapping("/organization/groups/{id}")
    public Result<Void> deleteUserGroup(@PathVariable Long id, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        userService.deleteUserGroup(tenantId, id);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id, HttpServletRequest req) {
        Long operatorUserId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        String role = (String) req.getAttribute("role");
        userService.deleteUser(id, operatorUserId, role, tenantId);
        return Result.success();
    }

    @PostMapping("/batch-delete")
    public Result<BatchDeleteResult> batchDelete(@RequestBody BatchDeleteRequest request, HttpServletRequest req) {
        Long operatorUserId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        String role = (String) req.getAttribute("role");
        return Result.success(userService.deleteUsers(request.getIds(), operatorUserId, role, tenantId));
    }
}
