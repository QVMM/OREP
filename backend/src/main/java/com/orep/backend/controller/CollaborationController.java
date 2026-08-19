package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.CollaborationService;
import com.orep.backend.service.CollaborationWorkItemService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

@RestController
@RequestMapping("/api/collaboration")
public class CollaborationController {
    private final CollaborationService service;
    private final CollaborationWorkItemService workItemService;
    private final boolean enabled;

    public CollaborationController(
            CollaborationService service,
            CollaborationWorkItemService workItemService,
            @Value("${orep.features.collaboration.enabled:false}") boolean enabled
    ) {
        this.service = service;
        this.workItemService = workItemService;
        this.enabled = enabled;
    }

    @GetMapping("/summary")
    public Result<Map<String, Object>> summary(HttpServletRequest request) {
        assertEnabled();
        return Result.success(workItemService.summary(
                tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/items")
    public Result<Map<String, Object>> items(
            @RequestParam(defaultValue = "ACTION_REQUIRED") String view,
            @RequestParam(required = false) Long teamId,
            @RequestParam(required = false) String cursor,
            @RequestParam(defaultValue = "30") Integer limit,
            HttpServletRequest request
    ) {
        assertEnabled();
        return Result.success(workItemService.items(
                tenantId(request),
                userId(request),
                role(request),
                view,
                teamId,
                cursor,
                limit
        ));
    }

    @PostMapping("/requests")
    public Result<Map<String, Object>> create(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        assertEnabled();
        return Result.success(service.createRequest(
                tenantId(request),
                userId(request),
                role(request),
                idempotencyKey,
                body
        ));
    }

    @PostMapping("/requests/batch")
    public Result<Map<String, Object>> createBatch(
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        assertEnabled();
        return Result.success(service.createRequests(
                tenantId(request),
                userId(request),
                role(request),
                idempotencyKey,
                body
        ));
    }

    @GetMapping("/requests/{id}")
    public Result<Map<String, Object>> detail(@PathVariable Long id, HttpServletRequest request) {
        assertEnabled();
        return Result.success(service.request(id, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/requests/{id}/accept")
    public Result<Map<String, Object>> accept(@PathVariable Long id, HttpServletRequest request) {
        assertEnabled();
        return Result.success(service.accept(id, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/requests/{id}/decline")
    public Result<Map<String, Object>> decline(
            @PathVariable Long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request
    ) {
        assertEnabled();
        return Result.success(service.decline(
                id,
                tenantId(request),
                userId(request),
                role(request),
                body == null ? Map.of() : body
        ));
    }

    @PostMapping("/requests/{id}/withdraw")
    public Result<Map<String, Object>> withdraw(@PathVariable Long id, HttpServletRequest request) {
        assertEnabled();
        return Result.success(service.withdraw(id, tenantId(request), userId(request), role(request)));
    }

    private void assertEnabled() {
        if (!enabled) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "协作功能尚未启用");
        }
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }
}
