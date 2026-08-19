package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.ProjectPreparationService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/project-prep")
public class ProjectPreparationController {
    private final ProjectPreparationService projectPreparationService;

    public ProjectPreparationController(ProjectPreparationService projectPreparationService) {
        this.projectPreparationService = projectPreparationService;
    }

    @GetMapping("/bootstrap")
    public Result<Map<String, Object>> bootstrap(
            @RequestParam(required = false) Long teamId,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.bootstrap(teamId, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/teams/{teamId}")
    public Result<Map<String, Object>> teamWorkspace(@PathVariable Long teamId, HttpServletRequest request) {
        return Result.success(projectPreparationService.teamWorkspace(teamId, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/sessions/{sessionId}")
    public Result<Map<String, Object>> session(@PathVariable Long sessionId, HttpServletRequest request) {
        return Result.success(projectPreparationService.session(sessionId, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/sessions/{sessionId}/messages")
    public Result<Map<String, Object>> sendMessage(
            @PathVariable Long sessionId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.sendMessage(sessionId, body, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/sessions/{sessionId}/directions/{directionId}/select")
    public Result<Map<String, Object>> selectDirection(
            @PathVariable Long sessionId,
            @PathVariable Long directionId,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.selectDirection(sessionId, directionId, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/sessions/{sessionId}/directions/{directionId}/tasks")
    public Result<Map<String, Object>> createTasks(
            @PathVariable Long sessionId,
            @PathVariable Long directionId,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.createTasksFromDirection(sessionId, directionId, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/sessions/{sessionId}/document")
    public Result<Map<String, Object>> createDocument(
            @PathVariable Long sessionId,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.createDocument(
                sessionId, body == null ? Map.of() : body, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/sessions/{sessionId}/documents/{documentId}")
    public Result<Map<String, Object>> documentDetail(
            @PathVariable Long sessionId,
            @PathVariable Long documentId,
            HttpServletRequest request
    ) {
        return Result.success(projectPreparationService.documentDetail(
                sessionId, documentId, tenantId(request), userId(request), role(request)));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }
}
