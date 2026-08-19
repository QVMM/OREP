package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.NotificationService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {
    private final NotificationService service;

    public NotificationController(NotificationService service) {
        this.service = service;
    }

    @GetMapping
    public Result<Map<String, Object>> list(HttpServletRequest request) {
        return Result.success(service.notifications(
                (Long) request.getAttribute("tenantId"),
                (Long) request.getAttribute("userId")
        ));
    }

    @PatchMapping("/{id}/read")
    public Result<Map<String, Object>> markRead(@PathVariable Long id, HttpServletRequest request) {
        return Result.success(service.markRead(
                (Long) request.getAttribute("tenantId"),
                (Long) request.getAttribute("userId"),
                id
        ));
    }

    @PatchMapping("/read-all")
    public Result<Map<String, Object>> markAllRead(HttpServletRequest request) {
        return Result.success(service.markAllRead(
                (Long) request.getAttribute("tenantId"),
                (Long) request.getAttribute("userId")
        ));
    }
}
