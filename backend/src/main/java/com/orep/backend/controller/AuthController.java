package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.LoginRequest;
import com.orep.backend.dto.LoginResponse;
import com.orep.backend.service.AuthService;
import com.orep.backend.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private UserService userService;

    @PostMapping("/send-code")
    public Result<Void> sendCode() {
        return Result.error(403, "用户端注册已关闭，请联系老师或管理员开通账号");
    }

    @PostMapping("/register")
    public Result<Void> register() {
        return Result.error(403, "用户端注册已关闭，请联系老师或管理员开通账号");
    }

    @PostMapping("/login")
    public Result<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        return Result.success(authService.login(request));
    }

    @GetMapping("/check")
    public Result<Boolean> check(HttpServletRequest request) {
        String token = request.getHeader("Authorization");
        return Result.success(authService.checkToken(token));
    }

    @PostMapping("/change-password")
    public Result<Void> changePassword(@RequestBody Map<String, String> body, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String oldPassword = body.get("oldPassword");
        String newPassword = body.get("newPassword");
        userService.changePassword(userId, oldPassword, newPassword);
        return Result.success();
    }
}
