package com.orep.backend.controller.assistant;

import com.orep.backend.common.Result;
import com.orep.backend.service.assistant.AssistantActionService;
import com.orep.backend.service.assistant.AssistantService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/assistant")
public class AssistantController {
    private final AssistantService service;
    private final AssistantActionService actionService;

    public AssistantController(AssistantService service, AssistantActionService actionService) {
        this.service = service;
        this.actionService = actionService;
    }

    /**
     * 小启技能目录（slash 菜单）。与 ai-scoring skills/catalog 对齐；菜单不依赖 Python 在线。
     * {@code /v1/skills} 是历史 Python 直连路径，nginx 会打到 Java，必须同样有 handler。
     */
    @GetMapping({"/skills", "/v1/skills"})
    public Result<List<Map<String, Object>>> skills(
            @RequestParam(defaultValue = "student") String audience
    ) {
        String aud = audience != null ? audience.trim().toLowerCase() : "student";
        return Result.success(service.listSkills(aud));
    }

    @GetMapping("/folders")
    public Result<List<Map<String, Object>>> folders(HttpServletRequest request) {
        return Result.success(service.listFolders(tenantId(request), userId(request)));
    }

    @PostMapping("/folders")
    public Result<Map<String, Object>> createFolder(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return Result.success(service.createFolder(tenantId(request), userId(request), body));
    }

    @PatchMapping("/folders/{id}")
    public Result<Map<String, Object>> patchFolder(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.patchFolder(id, tenantId(request), userId(request), body));
    }

    @DeleteMapping("/folders/{id}")
    public Result<Void> deleteFolder(@PathVariable Long id, HttpServletRequest request) {
        service.deleteFolder(id, tenantId(request), userId(request));
        return Result.success();
    }

    @GetMapping("/sessions")
    public Result<List<Map<String, Object>>> sessions(
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "30") int size,
            HttpServletRequest request
    ) {
        return Result.success(service.listSessions(tenantId(request), userId(request), keyword, page, size));
    }

    @PostMapping("/sessions")
    public Result<Map<String, Object>> createSession(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return Result.success(service.createSession(tenantId(request), userId(request), role(request), body));
    }

    @GetMapping("/sessions/{id}")
    public Result<Map<String, Object>> getSession(@PathVariable Long id, HttpServletRequest request) {
        return Result.success(service.getSession(id, tenantId(request), userId(request)));
    }

    @PatchMapping("/sessions/{id}")
    public Result<Map<String, Object>> patchSession(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.patchSession(id, tenantId(request), userId(request), role(request), body));
    }

    @GetMapping("/teams")
    public Result<List<Map<String, Object>>> teams(HttpServletRequest request) {
        return Result.success(service.myTeams(tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/resource-picker")
    public Result<Map<String, Object>> resourcePicker(
            @RequestParam Long teamId,
            HttpServletRequest request
    ) {
        return Result.success(service.resourcePicker(teamId, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/files/{fileId}/save-to-resource")
    public Result<Map<String, Object>> saveToResource(
            @PathVariable Long fileId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.saveFileToResource(
                fileId, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/sessions/{id}/save-reply")
    public Result<Map<String, Object>> saveReply(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.saveReplyAsMarkdown(
                id, tenantId(request), userId(request), role(request), body));
    }

    @PostMapping("/sessions/{id}/export-pdf")
    public Result<Map<String, Object>> exportPdf(
            @PathVariable Long id,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.exportSessionPdf(
                id, tenantId(request), userId(request), role(request)));
    }

    @DeleteMapping("/sessions/{id}")
    public Result<Void> deleteSession(@PathVariable Long id, HttpServletRequest request) {
        service.deleteSession(id, tenantId(request), userId(request));
        return Result.success();
    }

    @GetMapping("/sessions/{id}/messages")
    public Result<List<Map<String, Object>>> messages(
            @PathVariable Long id,
            @RequestParam(required = false) Long beforeId,
            @RequestParam(defaultValue = "50") int limit,
            HttpServletRequest request
    ) {
        return Result.success(service.listMessages(id, tenantId(request), userId(request), beforeId, limit));
    }

    /**
     * SSE 主路径。斜杠形式避免部分代理把 {@code :stream} 编成 {@code %3Astream} 后 404。
     * 冒号形式与「去后缀」形式保留，兼容旧客户端 / 被剥掉 :stream 的请求。
     */
    @PostMapping(value = {
            "/sessions/{id}/messages/stream",
            "/sessions/{id}/messages:stream",
            "/sessions/{id}/messages"
    }, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamMessage(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return service.streamMessage(id, tenantId(request), userId(request), role(request), body);
    }

    @PostMapping(value = {
            "/sessions/{id}/messages/{userMessageId}/regenerate/stream",
            "/sessions/{id}/messages/{userMessageId}/regenerate:stream"
    }, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter regenerate(
            @PathVariable Long id,
            @PathVariable Long userMessageId,
            HttpServletRequest request
    ) {
        return service.regenerate(id, userMessageId, tenantId(request), userId(request), role(request));
    }

    @PostMapping("/runs/{runId}/cancel")
    public Result<Void> cancel(@PathVariable Long runId, HttpServletRequest request) {
        service.cancelRun(runId, tenantId(request), userId(request));
        return Result.success();
    }

    @GetMapping("/runs/{runId}")
    public Result<Map<String, Object>> getRun(@PathVariable Long runId, HttpServletRequest request) {
        return Result.success(service.getRun(runId, tenantId(request), userId(request)));
    }

    /**
     * 重连订阅：刷新浏览器后对仍在进行的 run 继续收实时进度。
     * 生成任务在服务端独立运行，与 SSE 连接解耦。
     */
    @GetMapping(value = {
            "/runs/{runId}/events/stream",
            "/runs/{runId}/events:stream"
    }, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter subscribeRun(@PathVariable Long runId, HttpServletRequest request) {
        return service.subscribeRun(runId, tenantId(request), userId(request));
    }

    @PostMapping(value = "/sessions/{id}/files", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> upload(
            @PathVariable Long id,
            @RequestPart("file") MultipartFile file,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.uploadFile(id, tenantId(request), userId(request), file));
    }

    @GetMapping("/sessions/{id}/files")
    public Result<List<Map<String, Object>>> files(@PathVariable Long id, HttpServletRequest request) {
        return Result.success(service.listFiles(id, tenantId(request), userId(request)));
    }

    @GetMapping("/files/{fileId}/preview")
    public ResponseEntity<Resource> preview(@PathVariable Long fileId, HttpServletRequest request) throws IOException {
        return fileResponse(fileId, request, true);
    }

    @GetMapping("/files/{fileId}/download")
    public ResponseEntity<Resource> download(@PathVariable Long fileId, HttpServletRequest request) throws IOException {
        return fileResponse(fileId, request, false);
    }

    @DeleteMapping("/files/{fileId}")
    public Result<Void> deleteFile(@PathVariable Long fileId, HttpServletRequest request) throws IOException {
        service.deleteFile(fileId, tenantId(request), userId(request));
        return Result.success();
    }

    @PostMapping("/code/save-as-file")
    public Result<Map<String, Object>> saveCode(@RequestBody Map<String, Object> body, HttpServletRequest request) throws IOException {
        return Result.success(service.saveCodeAsFile(tenantId(request), userId(request), body));
    }

    @GetMapping("/memories")
    public Result<List<Map<String, Object>>> memories(HttpServletRequest request) {
        return Result.success(service.listMemories(tenantId(request), userId(request)));
    }

    @PostMapping("/memories")
    public Result<Map<String, Object>> createMemory(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return Result.success(service.createMemory(tenantId(request), userId(request), body));
    }

    @PatchMapping("/memories/{id}")
    public Result<Map<String, Object>> patchMemory(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.patchMemory(id, tenantId(request), userId(request), body));
    }

    @DeleteMapping("/memories/{id}")
    public Result<Void> deleteMemory(@PathVariable Long id, HttpServletRequest request) {
        service.deleteMemory(id, tenantId(request), userId(request));
        return Result.success();
    }

    @PostMapping("/sessions/{id}/share")
    public Result<Map<String, Object>> share(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.shareSession(id, tenantId(request), userId(request), role(request), body));
    }

    @GetMapping("/sessions/{id}/shares")
    public Result<List<Map<String, Object>>> shares(@PathVariable Long id, HttpServletRequest request) {
        return Result.success(service.listShares(id, tenantId(request), userId(request)));
    }

    /** 学生端组讲稿补丁确认卡（不执行） */
    @PostMapping("/script-patch/propose")
    public Result<Map<String, Object>> proposeScriptPatch(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(actionService.proposeOwned(tenantId(request), userId(request), body));
    }

    /** 用户确认执行小启提出的写操作 */
    @PostMapping("/actions/{proposalId}/confirm")
    public Result<Map<String, Object>> confirmAction(
            @PathVariable Long proposalId,
            HttpServletRequest request
    ) {
        return Result.success(actionService.confirm(
                proposalId, tenantId(request), userId(request), role(request)));
    }

    /** 用户取消提案 */
    @PostMapping("/actions/{proposalId}/reject")
    public Result<Map<String, Object>> rejectAction(
            @PathVariable Long proposalId,
            HttpServletRequest request
    ) {
        return Result.success(actionService.reject(proposalId, tenantId(request), userId(request)));
    }

    @GetMapping("/actions/{proposalId}")
    public Result<Map<String, Object>> getAction(
            @PathVariable Long proposalId,
            HttpServletRequest request
    ) {
        return Result.success(actionService.getProposal(proposalId, tenantId(request), userId(request)));
    }

    private ResponseEntity<Resource> fileResponse(Long fileId, HttpServletRequest request, boolean inline) throws IOException {
        Map<String, Object> meta = service.getFile(fileId, tenantId(request), userId(request));
        Path path = service.resolveFilePath(fileId, tenantId(request), userId(request));
        String name = String.valueOf(meta.get("name"));
        String encoded = URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20");
        String disposition = (inline ? "inline" : "attachment") + "; filename*=UTF-8''" + encoded;
        String contentType = meta.get("mimeType") == null
                ? Files.probeContentType(path)
                : String.valueOf(meta.get("mimeType"));
        if (contentType == null) contentType = "application/octet-stream";
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition)
                .contentType(MediaType.parseMediaType(contentType))
                .contentLength(Files.size(path))
                .body(new FileSystemResource(path));
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private String role(HttpServletRequest request) {
        Object r = request.getAttribute("role");
        return r == null ? "" : String.valueOf(r);
    }
}
