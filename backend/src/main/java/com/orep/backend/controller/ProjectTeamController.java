package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.ProjectTeamService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/project-teams")
public class ProjectTeamController {
    private final ProjectTeamService projectTeamService;

    public ProjectTeamController(ProjectTeamService projectTeamService) {
        this.projectTeamService = projectTeamService;
    }

    @GetMapping("/my")
    public Result<List<Map<String, Object>>> myTeams(HttpServletRequest request) {
        return Result.success(projectTeamService.myTeams(tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/{teamId}/dashboard")
    public Result<Map<String, Object>> dashboard(@PathVariable Long teamId, HttpServletRequest request) {
        return Result.success(projectTeamService.dashboard(teamId, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/{teamId}/tasks/{taskId}")
    public Result<Map<String, Object>> taskDetail(
            @PathVariable Long teamId,
            @PathVariable Long taskId,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.taskDetail(
                teamId, taskId, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/{teamId}/roadshow-memory")
    public Result<Map<String, Object>> roadshowMemory(@PathVariable Long teamId, HttpServletRequest request) {
        return Result.success(projectTeamService.roadshowMemory(teamId, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/{teamId}/evidence-excerpt")
    public Result<Map<String, Object>> evidenceExcerpt(
            @PathVariable Long teamId,
            @RequestParam Long aiReportId,
            @RequestParam String sourceRef,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.evidenceExcerpt(
                teamId, aiReportId, sourceRef, tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/candidate-members")
    public Result<List<Map<String, Object>>> candidateMembers(HttpServletRequest request) {
        return Result.success(projectTeamService.candidateMembers(tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/position-roles")
    public Result<List<Map<String, Object>>> positionRoles(HttpServletRequest request) {
        return Result.success(projectTeamService.positionRoles(tenantId(request)));
    }

    @GetMapping("/tracks")
    public Result<List<Map<String, Object>>> tracks(HttpServletRequest request) {
        return Result.success(projectTeamService.availableTracks(role(request)));
    }

    @PostMapping("/position-roles")
    public Result<Map<String, Object>> createPositionRole(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.createPositionRole(tenantId(request), userId(request), role(request), body));
    }

    @PostMapping
    public Result<Map<String, Object>> createTeam(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.createTeam(tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/{teamId}/tasks")
    public Result<Map<String, Object>> createTask(
            @PathVariable Long teamId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.createTask(teamId, tenantId(request), userId(request), role(request), body));
    }

    @PatchMapping("/tasks/{taskId}")
    public Result<Map<String, Object>> updateTask(
            @PathVariable Long taskId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.updateTask(taskId, tenantId(request), userId(request), role(request), body));
    }

    @PatchMapping("/{teamId}/members/{memberUserId}/position")
    public Result<Map<String, Object>> updateMemberPosition(
            @PathVariable Long teamId,
            @PathVariable Long memberUserId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.updateMemberPosition(
                teamId, memberUserId, tenantId(request), userId(request), role(request), body
        ));
    }

    @PostMapping("/{teamId}/members")
    public Result<Map<String, Object>> addMember(@PathVariable Long teamId,@RequestBody Map<String,Object> body,HttpServletRequest request) {
        return Result.success(projectTeamService.addMember(teamId,tenantId(request),userId(request),role(request),body));
    }

    @DeleteMapping("/{teamId}/members/{memberUserId}")
    public Result<Map<String, Object>> removeMember(@PathVariable Long teamId,@PathVariable Long memberUserId,HttpServletRequest request) {
        return Result.success(projectTeamService.removeMember(teamId,memberUserId,tenantId(request),userId(request),role(request)));
    }

    @PostMapping("/tasks/{taskId}/submissions")
    public Result<Map<String, Object>> submitTask(
            @PathVariable Long taskId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.submitTask(taskId, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/submissions/{submissionId}/review")
    public Result<Map<String, Object>> reviewSubmission(
            @PathVariable Long submissionId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.reviewSubmission(submissionId, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/{teamId}/materials")
    public Result<Map<String, Object>> createMaterial(
            @PathVariable Long teamId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.createMaterial(teamId, tenantId(request), userId(request), role(request), body));
    }

    /** 团队共享资源：实际上传文件并创建材料记录 */
    @PostMapping(value = "/{teamId}/materials/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> uploadMaterial(
            @PathVariable Long teamId,
            @RequestPart("file") MultipartFile file,
            @RequestParam(value = "name", required = false) String name,
            @RequestParam(value = "materialType", required = false) String materialType,
            @RequestParam(value = "description", required = false) String description,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.uploadMaterial(
                teamId,
                tenantId(request),
                userId(request),
                role(request),
                file,
                name,
                materialType,
                description
        ));
    }

    @PostMapping("/materials/{materialId}/review")
    public Result<Map<String, Object>> reviewMaterial(
            @PathVariable Long materialId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.reviewMaterial(materialId, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/{teamId}/roadshows/bind")
    public Result<Map<String, Object>> bindRoadshow(
            @PathVariable Long teamId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.bindRoadshow(teamId, tenantId(request), userId(request), role(request), body));
    }

    @GetMapping("/roadshow-roster/{meetingId}")
    public Result<List<Map<String, Object>>> roadshowRoster(@PathVariable Long meetingId,
                                                            HttpServletRequest request) {
        return Result.success(projectTeamService.roadshowTeamRoster(
                meetingId, tenantId(request), userId(request), role(request)));
    }

    @PatchMapping("/{teamId}/stages/{stageKey}")
    public Result<Map<String, Object>> updateStageSchedule(
            @PathVariable Long teamId,
            @PathVariable String stageKey,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.updateStageSchedule(
                teamId, stageKey, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/roadshow-speakers/{speakerId}/resolve")
    public Result<Map<String, Object>> resolveRoadshowSpeaker(
            @PathVariable Long speakerId,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(projectTeamService.resolveRoadshowSpeaker(
                speakerId, tenantId(request), userId(request), role(request), body == null ? Map.of() : body));
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
