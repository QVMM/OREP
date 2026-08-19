package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.ProjectTeamService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/teacher")
public class TeacherReviewController {
    private final ProjectTeamService projectTeamService;

    public TeacherReviewController(ProjectTeamService projectTeamService) {
        this.projectTeamService = projectTeamService;
    }

    @GetMapping("/review-queue")
    public Result<List<Map<String, Object>>> reviewQueue(HttpServletRequest request) {
        return Result.success(projectTeamService.teacherReviewQueue(
                tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/submissions/{submissionId}")
    public Result<Map<String, Object>> submission(
            @PathVariable Long submissionId,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.teacherSubmissionDetail(
                submissionId, tenantId(request), userId(request), role(request)));
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
