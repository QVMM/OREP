package com.orep.backend.controller.assistant;

import com.orep.backend.common.Result;
import com.orep.backend.service.assistant.AssistantActionService;
import com.orep.backend.service.assistant.AssistantContextToolService;
import com.orep.backend.service.assistant.AssistantService;
import com.orep.backend.service.ProjectTeamService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/**
 * 小启 AI 内部工具面：仅 AI 服务用 X-Internal-Token 调用。
 * 所有读工具在 Service 内复用业务鉴权并裁剪结果。
 */
@RestController
@RequestMapping("/api/assistant/internal")
public class AssistantInternalController {
    private final AssistantService service;
    private final AssistantContextToolService contextTools;
    private final AssistantActionService actionService;
    private final ProjectTeamService projectTeamService;

    public AssistantInternalController(
            AssistantService service,
            AssistantContextToolService contextTools,
            AssistantActionService actionService,
            ProjectTeamService projectTeamService
    ) {
        this.service = service;
        this.contextTools = contextTools;
        this.actionService = actionService;
        this.projectTeamService = projectTeamService;
    }

    @GetMapping("/roadshow-roster")
    public Result<List<Map<String, Object>>> roadshowRoster(
            @RequestParam Long meetingId,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        service.assertInternalToken(token);
        return Result.success(projectTeamService.roadshowTeamRoster(meetingId));
    }

    @GetMapping("/score-summary")
    public Result<Map<String, Object>> scoreSummary(
            @RequestParam Long userId,
            @RequestParam(required = false) Long teamId,
            @RequestParam(defaultValue = "3") int limit,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(service.scoreSummary(userId, teamId, limit, token));
    }

    /** 教师工作台摘要（仅教师角色） */
    @GetMapping("/teacher-workbench")
    public Result<Map<String, Object>> teacherWorkbench(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) String role,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.teacherWorkbench(tenantId, userId, role, token));
    }

    /** 教师批改/今日概况（仅教师角色） */
    @GetMapping("/teacher-review-queue")
    public Result<Map<String, Object>> teacherReviewQueue(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) String role,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.teacherReviewQueue(tenantId, userId, role, token));
    }

    /** 教师训练进度（仅教师角色） */
    @GetMapping("/teacher-camp-progress")
    public Result<Map<String, Object>> teacherCampProgress(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) String role,
            @RequestParam(required = false) Long campId,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.teacherCampProgress(tenantId, userId, role, campId, token));
    }

    /** 训练营今日学习 */
    @GetMapping("/learning-today")
    public Result<Map<String, Object>> learningToday(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.learningToday(tenantId, userId, token));
    }

    /** 训练营计划摘要 */
    @GetMapping("/learning-plan")
    public Result<Map<String, Object>> learningPlan(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.learningPlan(tenantId, userId, token));
    }

    /** 我的项目任务列表（只读） */
    @GetMapping("/my-tasks")
    public Result<Map<String, Object>> myTasks(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) Long teamId,
            @RequestParam(required = false) String role,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.myTasks(tenantId, userId, teamId, role, token));
    }

    /** 任务详情（只读） */
    @GetMapping("/task-detail")
    public Result<Map<String, Object>> taskDetail(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam Long teamId,
            @RequestParam Long taskId,
            @RequestParam(required = false) String role,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.taskDetail(tenantId, userId, teamId, taskId, role, token));
    }

    /** 协同摘要 */
    @GetMapping("/collab-summary")
    public Result<Map<String, Object>> collabSummary(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) String role,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.collabSummary(tenantId, userId, role, token));
    }

    /** 协同事项列表 */
    @GetMapping("/collab-items")
    public Result<Map<String, Object>> collabItems(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestParam(required = false) Long teamId,
            @RequestParam(required = false) String role,
            @RequestParam(defaultValue = "ACTION_REQUIRED") String view,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        return Result.success(contextTools.collabItems(tenantId, userId, teamId, role, view, token));
    }

    /**
     * AI 创建待确认写操作提案（不执行）。
     * body: { actionType, title, summary, args, sessionId?, runId? }
     */
    @PostMapping("/actions/propose")
    public Result<Map<String, Object>> proposeAction(
            @RequestParam Long tenantId,
            @RequestParam Long userId,
            @RequestBody Map<String, Object> body,
            @RequestHeader(value = "X-Internal-Token", required = false) String token
    ) {
        Long sessionId = body.get("sessionId") instanceof Number n ? n.longValue() : null;
        Long runId = body.get("runId") instanceof Number n ? n.longValue() : null;
        return Result.success(actionService.propose(tenantId, userId, sessionId, runId, body, token));
    }
}
