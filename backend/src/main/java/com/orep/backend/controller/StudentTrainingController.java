package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentTrainingService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class StudentTrainingController {
    private final StudentTrainingService studentTrainingService;
    private final com.orep.backend.service.TrainingDayLearningResourceService learningService;

    public StudentTrainingController(
            StudentTrainingService studentTrainingService,
            com.orep.backend.service.TrainingDayLearningResourceService learningService
    ) {
        this.studentTrainingService = studentTrainingService;
        this.learningService = learningService;
    }

    @GetMapping("/training-camps/current")
    public Result<Map<String, Object>> current(HttpServletRequest request) {
        return Result.success(studentTrainingService.current(tenantId(request), userId(request)));
    }

    @GetMapping("/training-camps/current/today")
    public Result<Map<String, Object>> today(HttpServletRequest request) {
        return Result.success(studentTrainingService.today(tenantId(request), userId(request)));
    }

    @GetMapping("/training-camps/current/today-overview")
    public Result<Map<String, Object>> todayOverview(HttpServletRequest request) {
        return Result.success(studentTrainingService.todayOverview(tenantId(request), userId(request)));
    }

    @GetMapping("/training-camps/current/plan")
    public Result<Map<String, Object>> plan(HttpServletRequest request) {
        return Result.success(studentTrainingService.plan(tenantId(request), userId(request)));
    }

    @GetMapping("/training-days/{dayId}")
    public Result<Map<String, Object>> day(@PathVariable Long dayId, HttpServletRequest request) {
        return Result.success(studentTrainingService.day(tenantId(request), userId(request), dayId));
    }

    @GetMapping("/training-days/{dayId}/overview")
    public Result<Map<String, Object>> dayOverview(@PathVariable Long dayId, HttpServletRequest request) {
        return Result.success(studentTrainingService.dayOverview(tenantId(request), userId(request), dayId));
    }

    @GetMapping("/training-submissions/{submissionId}")
    public Result<Map<String, Object>> submission(@PathVariable Long submissionId, HttpServletRequest request) {
        return Result.success(studentTrainingService.submission(tenantId(request), userId(request), submissionId));
    }

    @GetMapping("/training-submissions/{submissionId}/feedback")
    public Result<Map<String, Object>> feedback(@PathVariable Long submissionId, HttpServletRequest request) {
        return Result.success(studentTrainingService.feedback(tenantId(request), userId(request), submissionId));
    }

    @PatchMapping("/training-learning-resources/{resourceId}/progress")
    public Result<Map<String,Object>> updateLearningProgress(
            @PathVariable Long resourceId,
            @RequestBody Map<String,Object> body,
            HttpServletRequest request
    ) {
        String mode = String.valueOf(body.getOrDefault("mode", "")).trim().toUpperCase();
        if ("EMBED".equals(mode) || "EMBED_VIDEO".equals(mode)) {
            return Result.success(learningService.recordEmbedHeartbeat(
                    tenantId(request), userId(request), resourceId,
                    String.valueOf(body.getOrDefault("sessionId", "")),
                    booleanValue(body.get("visible") == null ? true : body.get("visible")),
                    booleanValue(body.get("active") == null ? true : body.get("active")),
                    booleanValue(body.get("reset"))
            ));
        }
        return Result.success(learningService.recordVideoHeartbeat(
                tenantId(request),userId(request),resourceId,
                String.valueOf(body.getOrDefault("sessionId", "")),
                intValue(body.get("positionSeconds")),
                intValue(body.get("durationSeconds")),
                booleanValue(body.get("reset"))
        ));
    }

    @PostMapping("/training-learning-resources/{resourceId}/complete")
    public Result<Map<String,Object>> completeLearningResource(@PathVariable Long resourceId,HttpServletRequest request) {
        return Result.success(learningService.completeNonVideo(tenantId(request),userId(request),resourceId));
    }

    /** 任务书页驻留心跳：教师档案「任务书驻留时长」数据源 */
    @PostMapping("/training-days/{dayId}/dwell")
    public Result<Map<String, Object>> taskBookDwell(
            @PathVariable Long dayId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(studentTrainingService.recordTaskBookDwell(
                tenantId(request),
                userId(request),
                dayId,
                String.valueOf(body.getOrDefault("sessionId", "")),
                booleanValue(body.get("visible") == null ? true : body.get("visible")),
                booleanValue(body.get("active") == null ? true : body.get("active")),
                booleanValue(body.get("reset"))
        ));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private int intValue(Object value) {
        if (value instanceof Number number) return number.intValue();
        if (value == null) return 0;
        try { return Integer.parseInt(String.valueOf(value)); }
        catch (NumberFormatException ignored) { return 0; }
    }

    private boolean booleanValue(Object value) {
        if (value instanceof Boolean bool) return bool;
        if (value instanceof Number number) return number.intValue() != 0;
        return Boolean.parseBoolean(String.valueOf(value));
    }
}
