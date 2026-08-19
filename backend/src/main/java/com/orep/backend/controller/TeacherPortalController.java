package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.TeacherPortalService;
import com.orep.backend.service.TrainingDayContentService;
import com.orep.backend.service.TrainingDayLearningResourceService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/teacher/portal")
public class TeacherPortalController {
    private final TeacherPortalService service;
    private final TrainingDayContentService contentService;
    private final TrainingDayLearningResourceService learningService;

    public TeacherPortalController(
            TeacherPortalService service,
            TrainingDayContentService contentService,
            TrainingDayLearningResourceService learningService
    ) {
        this.service = service;
        this.contentService = contentService;
        this.learningService = learningService;
    }

    @GetMapping("/workbench") public Result<Map<String,Object>> workbench(HttpServletRequest r) { return Result.success(service.workbench(tenantId(r),userId(r),role(r))); }
    @GetMapping("/camps") public Result<List<Map<String,Object>>> camps(HttpServletRequest r) { return Result.success(service.camps(tenantId(r),userId(r),role(r))); }
    @PostMapping("/camps") public Result<Map<String,Object>> createCamp(@RequestBody Map<String,Object> body,HttpServletRequest r) { return Result.success(service.createCamp(tenantId(r),userId(r),role(r),body)); }
    @PatchMapping("/camps/{campId}/schedule")
    public Result<Map<String,Object>> rescheduleCamp(
            @PathVariable Long campId,
            @RequestBody Map<String,Object> body,
            HttpServletRequest r
    ) {
        return Result.success(service.rescheduleCamp(tenantId(r),userId(r),role(r),campId,body));
    }
    @PatchMapping("/camps/{campId}/duration")
    public Result<Map<String,Object>> extendCamp(
            @PathVariable Long campId,
            @RequestBody Map<String,Object> body,
            HttpServletRequest r
    ) {
        return Result.success(service.extendCamp(tenantId(r),userId(r),role(r),campId,body));
    }
    @DeleteMapping("/camps/{campId}")
    public Result<Map<String,Object>> deleteCamp(
            @PathVariable Long campId,
            @RequestBody Map<String,Object> body,
            HttpServletRequest r
    ) {
        return Result.success(service.deleteCamp(tenantId(r),userId(r),role(r),campId,body));
    }
    @GetMapping("/camp")
    public Result<Map<String,Object>> camp(@RequestParam(required = false) Long campId,HttpServletRequest r) {
        Map<String,Object> payload = service.campOverview(tenantId(r),userId(r),role(r),campId);
        return Result.success(learningService.attachTeacherResources(payload,tenantId(r),userId(r),role(r)));
    }
    @PatchMapping("/camp/days/{dayId}")
    public Result<Map<String,Object>> updateDay(@PathVariable Long dayId,@RequestBody Map<String,Object> body,HttpServletRequest r) {
        Map<String,Object> result = service.updateTrainingDay(tenantId(r),userId(r),role(r),dayId,body);
        if ("PUBLISHED".equals(String.valueOf(body.get("status")))) learningService.activatePending(dayId);
        result.put("learningResources", learningService.teacherResources(tenantId(r),userId(r),role(r),dayId));
        return Result.success(result);
    }
    @PostMapping("/camp/days/{dayId}/early-unlock")
    public Result<Map<String,Object>> earlyUnlockDay(@PathVariable Long dayId,HttpServletRequest r) {
        return Result.success(service.earlyUnlockTrainingDay(tenantId(r),userId(r),role(r),dayId));
    }
    @DeleteMapping("/camp/days/{dayId}/early-unlock")
    public Result<Map<String,Object>> restoreAutomaticUnlock(@PathVariable Long dayId,HttpServletRequest r) {
        return Result.success(service.restoreAutomaticUnlock(tenantId(r),userId(r),role(r),dayId));
    }
    @PostMapping(value = "/camp/days/{dayId}/content-images", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String,Object>> uploadContentImage(@PathVariable Long dayId,@RequestPart("file") MultipartFile file,HttpServletRequest r) {
        return Result.success(contentService.uploadContentImage(tenantId(r),userId(r),role(r),dayId,file));
    }
    @PostMapping(value = "/camp/days/{dayId}/attachments", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String,Object>> uploadAttachment(@PathVariable Long dayId,@RequestPart("file") MultipartFile file,HttpServletRequest r) {
        return Result.success(contentService.uploadAttachment(tenantId(r),userId(r),role(r),dayId,file));
    }
    @DeleteMapping("/camp/days/{dayId}/attachments/{attachmentId}")
    public Result<Boolean> deleteAttachment(@PathVariable Long dayId,@PathVariable Long attachmentId,HttpServletRequest r) {
        contentService.deleteAttachment(tenantId(r),userId(r),role(r),dayId,attachmentId);
        return Result.success(true);
    }
    @PatchMapping("/camp/days/{dayId}/attachments/order")
    public Result<List<Map<String,Object>>> reorderAttachments(@PathVariable Long dayId,@RequestBody Map<String,List<Long>> body,HttpServletRequest r) {
        return Result.success(contentService.reorderAttachments(tenantId(r),userId(r),role(r),dayId,body.get("attachmentIds")));
    }
    @PostMapping(value = "/camp/days/{dayId}/learning-resources/files", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String,Object>> uploadLearningResource(
            @PathVariable Long dayId,
            @RequestPart("file") MultipartFile file,
            @RequestParam(required = false) String title,
            @RequestParam(required = false) String description,
            @RequestParam(defaultValue = "true") boolean required,
            @RequestParam(defaultValue = "0") int durationSeconds,
            HttpServletRequest r
    ) {
        return Result.success(learningService.upload(
                tenantId(r),userId(r),role(r),dayId,file,
                Map.of(
                        "title", title == null ? "" : title,
                        "description", description == null ? "" : description,
                        "required", required,
                        "durationSeconds", durationSeconds
                )
        ));
    }
    @PostMapping("/camp/days/{dayId}/learning-resources/links")
    public Result<Map<String,Object>> createLearningLink(@PathVariable Long dayId,@RequestBody Map<String,Object> body,HttpServletRequest r) {
        return Result.success(learningService.createLink(tenantId(r),userId(r),role(r),dayId,body));
    }

    @PostMapping("/camp/days/{dayId}/learning-resources/embed/parse")
    public Result<Map<String,Object>> parseLearningEmbed(@PathVariable Long dayId,@RequestBody Map<String,Object> body,HttpServletRequest r) {
        // dayId 用于鉴权上下文（老师需有该日写权限才解析）
        learningService.teacherResources(tenantId(r), userId(r), role(r), dayId);
        return Result.success(learningService.parseEmbed(body == null ? null : String.valueOf(body.getOrDefault("url", ""))));
    }

    @PostMapping("/camp/days/{dayId}/learning-resources/embed")
    public Result<Map<String,Object>> createLearningEmbed(@PathVariable Long dayId,@RequestBody Map<String,Object> body,HttpServletRequest r) {
        return Result.success(learningService.createEmbed(tenantId(r),userId(r),role(r),dayId,body));
    }
    @PatchMapping("/camp/days/{dayId}/learning-resources/{resourceId}")
    public Result<Map<String,Object>> updateLearningResource(@PathVariable Long dayId,@PathVariable Long resourceId,@RequestBody Map<String,Object> body,HttpServletRequest r) {
        return Result.success(learningService.update(tenantId(r),userId(r),role(r),dayId,resourceId,body));
    }
    @DeleteMapping("/camp/days/{dayId}/learning-resources/{resourceId}")
    public Result<Boolean> archiveLearningResource(@PathVariable Long dayId,@PathVariable Long resourceId,HttpServletRequest r) {
        learningService.archive(tenantId(r),userId(r),role(r),dayId,resourceId);
        return Result.success(true);
    }
    @PatchMapping("/camp/days/{dayId}/learning-resources/order")
    public Result<List<Map<String,Object>>> reorderLearningResources(@PathVariable Long dayId,@RequestBody Map<String,List<Long>> body,HttpServletRequest r) {
        return Result.success(learningService.reorder(tenantId(r),userId(r),role(r),dayId,body.get("resourceIds")));
    }
    @GetMapping("/recordings") public Result<List<Map<String,Object>>> recordings(HttpServletRequest r) { return Result.success(service.recordings(tenantId(r),userId(r),role(r))); }
    @GetMapping("/resources") public Result<List<Map<String,Object>>> resources(HttpServletRequest r) { return Result.success(service.resources(tenantId(r),userId(r),role(r))); }
    /** 学生 AI PPT 生成记录（ppt_task） */
    @GetMapping("/ai-ppt") public Result<List<Map<String,Object>>> aiPpt(HttpServletRequest r) {
        return Result.success(service.aiPptWorks(tenantId(r), userId(r), role(r)));
    }
    /** 学生 AI/编辑器讲稿（script） */
    @GetMapping("/ai-scripts") public Result<List<Map<String,Object>>> aiScripts(HttpServletRequest r) {
        return Result.success(service.aiScripts(tenantId(r), userId(r), role(r)));
    }
    @GetMapping("/exams") public Result<Map<String,Object>> exams(HttpServletRequest r) { return Result.success(service.exams(tenantId(r))); }
    @GetMapping("/ai-todos") public Result<List<Map<String,Object>>> aiTodos(HttpServletRequest r) { return Result.success(service.aiTodos(tenantId(r),userId(r),role(r))); }
    @PostMapping("/ai-todos/{todoId}/publish") public Result<Map<String,Object>> publishTodo(@PathVariable Long todoId,@RequestBody Map<String,Object> body,HttpServletRequest r) { return Result.success(service.publishAiTodo(tenantId(r),userId(r),role(r),todoId,body)); }
    @GetMapping("/analytics") public Result<Map<String,Object>> analytics(HttpServletRequest r) { return Result.success(service.analytics(tenantId(r),userId(r),role(r))); }
    @GetMapping("/students") public Result<Map<String,Object>> students(HttpServletRequest r) { return Result.success(service.studentRoster(tenantId(r),userId(r),role(r))); }
    @GetMapping("/students/{studentUserId}") public Result<Map<String,Object>> studentProfile(@PathVariable Long studentUserId, HttpServletRequest r) {
        return Result.success(service.studentProfile(tenantId(r),userId(r),role(r),studentUserId));
    }
    @PostMapping("/reminders") public Result<Map<String,Object>> remind(@RequestBody Map<String,Object> body,HttpServletRequest r) { return Result.success(service.remind(tenantId(r),userId(r),role(r),body)); }

    private Long tenantId(HttpServletRequest request) { return (Long) request.getAttribute("tenantId"); }
    private Long userId(HttpServletRequest request) { return (Long) request.getAttribute("userId"); }
    private String role(HttpServletRequest request) { return String.valueOf(request.getAttribute("role")); }
}
