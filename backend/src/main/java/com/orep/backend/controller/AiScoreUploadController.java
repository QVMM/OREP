package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.AiScoreUploadTaskResponse;
import com.orep.backend.dto.PipelineStartResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.AiScoreUploadTaskService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.InputStreamResource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.nio.file.Path;
import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/ai-score")
public class AiScoreUploadController {
    private final AiScoringSessionService scoringSessionService;
    private final AiScoreMediaAssetService mediaAssetService;
    private final AiScoreAccessControlService accessControlService;
    private final AiScoringPipelineClient pipelineClient;
    private final AiScoreUploadTaskService uploadTaskService;
    private final String uploadDir;
    /**
     * Internal base URL used by ai-scoring when posting pipeline progress/results.
     * Must be reachable from the ai-scoring container (e.g. http://backend:8080),
     * not the public site hostname (public HTTP often 301-redirects to HTTPS and is rejected).
     */
    private final String callbackBaseUrl;
    /**
     * Absolute root of upload files as seen inside the ai-scoring container.
     * When empty, uses the backend local uploadDir (same path only works if volumes are shared).
     */
    private final String aiScoringFileRoot;

    /** Test helper: local defaults for callback base and media root. */
    public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                                   AiScoreMediaAssetService mediaAssetService,
                                   AiScoreAccessControlService accessControlService,
                                   AiScoringPipelineClient pipelineClient,
                                   String uploadDir) {
        this(scoringSessionService, mediaAssetService, accessControlService, pipelineClient,
                uploadDir, null);
    }

    /** Test helper: local defaults for callback base and media root. */
    public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                                   AiScoreMediaAssetService mediaAssetService,
                                   AiScoreAccessControlService accessControlService,
                                   AiScoringPipelineClient pipelineClient,
                                   String uploadDir,
                                   AiScoreUploadTaskService uploadTaskService) {
        this(scoringSessionService, mediaAssetService, accessControlService, pipelineClient,
                uploadTaskService, uploadDir, "http://127.0.0.1:8080", "");
    }

    @Autowired
    public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                                   AiScoreMediaAssetService mediaAssetService,
                                   AiScoreAccessControlService accessControlService,
                                   AiScoringPipelineClient pipelineClient,
                                   AiScoreUploadTaskService uploadTaskService,
                                   @Value("${file.upload-dir:./uploads}") String uploadDir,
                                   @Value("${recording.callback.base-url:http://127.0.0.1:8080}") String callbackBaseUrl,
                                   @Value("${ai-scoring.file-root:}") String aiScoringFileRoot) {
        this.scoringSessionService = scoringSessionService;
        this.mediaAssetService = mediaAssetService;
        this.accessControlService = accessControlService;
        this.pipelineClient = pipelineClient;
        this.uploadTaskService = uploadTaskService;
        this.uploadDir = Path.of(uploadDir).toAbsolutePath().normalize().toString();
        this.callbackBaseUrl = callbackBaseUrl == null || callbackBaseUrl.isBlank()
                ? "http://127.0.0.1:8080"
                : callbackBaseUrl.trim().replaceAll("/+$", "");
        this.aiScoringFileRoot = aiScoringFileRoot == null ? "" : aiScoringFileRoot.trim();
    }

    @GetMapping("/upload-tasks")
    public Result<List<AiScoreUploadTaskResponse>> listUploadTasks(
            @RequestParam(value = "completedLimit", defaultValue = "10") Integer completedLimit,
            HttpServletRequest request) {
        Long userId = attrLong(request, "userId");
        if (userId == null) {
            return Result.error(401, "用户未登录");
        }
        return Result.success(uploadTaskService.listForUser(userId, completedLimit));
    }

    @PostMapping(value = "/upload-session", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<AiScoringSessionUserResponse> uploadSession(
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "teamId", required = false) Long teamId,
            @RequestParam(value = "trackId", required = false) String trackId,
            @RequestParam(value = "trackName", required = false) String trackName,
            @RequestParam(value = "useHistoryMemory", defaultValue = "true") Boolean useHistoryMemory,
            @RequestParam(value = "juryEnabled", defaultValue = "false") Boolean juryEnabled,
            @RequestParam(value = "forceRetranscribe", defaultValue = "false") Boolean forceRetranscribe,
            @RequestParam(value = "video", required = false) MultipartFile video,
            @RequestParam(value = "materials", required = false) List<MultipartFile> materials,
            HttpServletRequest request) {
        if (video == null || video.isEmpty()) {
            return Result.error(400, "视频文件不能为空");
        }

        Long userId = (Long) request.getAttribute("userId");
        AiScoringSessionUserResponse session = null;
        try {
            accessControlService.assertTeamAccess(
                    teamId,
                    attrLong(request, "tenantId"),
                    userId,
                    attrString(request, "role")
            );
            mediaAssetService.validateUploadBatch(video, materials);
            AiScoringSessionCreateRequest createRequest = new AiScoringSessionCreateRequest();
            createRequest.setProjectId(projectId);
            createRequest.setTeamId(teamId);
            createRequest.setTrackId(trackId);
            createRequest.setTrackName(trackName);
            createRequest.setSourceType("uploaded_video");
            createRequest.setUseHistoryMemory(useHistoryMemory);
            createRequest.setJuryEnabled(false);

            session = scoringSessionService.createSession(createRequest, userId);
            AiScoringSession dispatchSession = scoringSessionService.requireSessionForAccess(session.getSessionId());
            accessControlService.assertSessionAccess(
                    dispatchSession,
                    attrLong(request, "tenantId"),
                    userId,
                    attrString(request, "role")
            );
            mediaAssetService.storeVideo(session.getSessionId(), video, userId);
            if (materials != null) {
                for (MultipartFile material : materials) {
                    if (material != null && !material.isEmpty()) {
                        mediaAssetService.storeMaterial(session.getSessionId(), material, userId);
                    }
                }
            }
            session = scoringSessionService.markUploaded(session.getSessionId());
            AiScoringSessionUserResponse queuedSession = scoringSessionService.markPipelineQueued(session.getSessionId());
            String callbackUrl = buildCallbackUrl(request, session.getSessionId());
            var videoAsset = mediaAssetService.getVideoAssetBySession(session.getSessionId());
            var materialAssets = mediaAssetService.getMaterialAssetsBySession(session.getSessionId());
            List<Map<String, String>> materialList = materialAssets.stream()
                    .map(a -> Map.of(
                            "path", absoluteUploadPath(a.getFilePath()),
                            "name", valueOrEmpty(a.getOriginalName())
                    ))
                    .toList();
            PipelineStartResponse pipelineResponse = pipelineClient.startSessionPipeline(
                    session.getSessionId(),
                    session.getSessionNo(),
                    teamId,
                    projectId,
                    dispatchSession.getTrackId(),
                    dispatchSession.getTrackName(),
                    dispatchSession.getRubricInternalVersion(),
                    dispatchSession.getRubricHash(),
                    "uploaded_video",
                    absoluteUploadPath(videoAsset.getFilePath()),
                     videoAsset.getOriginalName(),
                     materialList,
                     false,
                     videoAsset.getFileHash(),
                     Boolean.TRUE.equals(forceRetranscribe),
                     callbackUrl
            );

            if (pipelineResponse == null || !pipelineResponse.isAccepted()) {
                String reason = pipelineResponse == null ? "AI 服务返回空响应" : pipelineResponse.getMessage();
                String message = dispatchFailureMessage(reason);
                AiScoringSessionUserResponse failedSession = scoringSessionService.markFailed(
                        session.getSessionId(),
                        message,
                        "pipeline_dispatch_failed"
                );
                failedSession.setMessage(message);
                return Result.success(failedSession);
            }

            queuedSession.setMessage("视频已上传，AI评分流水线已进入排队分析");
            return Result.success(queuedSession);
        } catch (IllegalArgumentException e) {
            markFailedQuietly(session, e.getMessage());
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            markFailedQuietly(session, e.getMessage());
            return Result.error(409, e.getMessage());
        } catch (Exception e) {
            markFailedQuietly(session, e.getMessage());
            return Result.error(500, "上传视频评分创建失败");
        }
    }

    /**
     * Receives the browser's combined meeting audio/video recording and dispatches
     * it through the exact same authoritative Python session pipeline as uploads.
     * The media stays on the private local deployment; no OSS/public URL is used.
     */
    @PostMapping(value = "/sessions/{sessionId}/meeting-media", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<AiScoringSessionUserResponse> uploadMeetingMedia(
            @PathVariable("sessionId") Long sessionId,
            @RequestParam(value = "audio", required = false) MultipartFile recording,
            HttpServletRequest request) {
        if (recording == null || recording.isEmpty()) {
            return Result.error(400, "会议音视频录制文件不能为空");
        }
        try {
            Long userId = attrLong(request, "userId");
            AiScoringSession dispatchSession = scoringSessionService.requireSessionForAccess(sessionId);
            accessControlService.assertSessionAccess(
                    dispatchSession,
                    attrLong(request, "tenantId"),
                    userId,
                    attrString(request, "role")
            );
            if (!"meeting_recording".equals(dispatchSession.getSourceType())) {
                return Result.error(409, "当前评分会话不是会议录制来源");
            }

            mediaAssetService.storeMeetingVideo(sessionId, recording, userId);
            scoringSessionService.markUploaded(sessionId);
            AiScoringSessionUserResponse queued = scoringSessionService.markPipelineQueued(sessionId);
            var videoAsset = mediaAssetService.getVideoAssetBySession(sessionId);
            if (videoAsset == null) {
                throw new IllegalStateException("会议录制视频未正确登记");
            }
            List<Map<String, String>> materialList = mediaAssetService.getMaterialAssetsBySession(sessionId).stream()
                    .map(a -> Map.of(
                            "path", absoluteUploadPath(a.getFilePath()),
                            "name", valueOrEmpty(a.getOriginalName())
                    ))
                    .toList();
            PipelineStartResponse response = pipelineClient.startSessionPipeline(
                    sessionId,
                    dispatchSession.getSessionNo(),
                    dispatchSession.getTeamId(),
                    dispatchSession.getProjectId(),
                    dispatchSession.getTrackId(),
                    dispatchSession.getTrackName(),
                    dispatchSession.getRubricInternalVersion(),
                    dispatchSession.getRubricHash(),
                    "meeting_recording",
                    absoluteUploadPath(videoAsset.getFilePath()),
                     videoAsset.getOriginalName(),
                     materialList,
                     false,
                     videoAsset.getFileHash(),
                     false,
                     buildCallbackUrl(request, sessionId)
            );
            if (response == null || !response.isAccepted()) {
                String reason = response == null ? "AI 服务返回空响应" : response.getMessage();
                String message = dispatchFailureMessage(reason);
                AiScoringSessionUserResponse failed = scoringSessionService.markFailed(
                        sessionId, message, "pipeline_dispatch_failed"
                );
                failed.setMessage(message);
                return Result.success(failed);
            }
            queued.setMessage("会议录制已接入统一 AI 评分流水线");
            return Result.success(queued);
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(409, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "会议录制评分任务派发失败");
        }
    }

    @RequestMapping(value = "/sessions/{sessionId}/media/video", method = {RequestMethod.GET, RequestMethod.HEAD})
    public ResponseEntity<?> streamSessionVideo(
            @PathVariable("sessionId") Long sessionId,
            @RequestHeader(value = HttpHeaders.RANGE, required = false) String rangeHeader,
            HttpServletRequest request
    ) throws IOException {
        AiScoringSession session = scoringSessionService.requireSessionForAccess(sessionId);
        accessControlService.assertSessionAccess(
                session,
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        );
        AiScoreMediaAssetService.PlayableMedia playable = mediaAssetService.requirePlayableVideo(sessionId);
        long total = playable.sizeBytes();
        ByteRange range;
        try {
            range = parseRange(rangeHeader, total);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    .header(HttpHeaders.ACCEPT_RANGES, "bytes")
                    .header(HttpHeaders.CONTENT_RANGE, "bytes */" + total)
                    .build();
        }

        HttpHeaders headers = new HttpHeaders();
        headers.set(HttpHeaders.ACCEPT_RANGES, "bytes");
        headers.setContentType(safeMediaType(playable.asset().getMimeType()));
        headers.setContentLength(range.length());
        if (range.partial()) {
            headers.set(HttpHeaders.CONTENT_RANGE,
                    "bytes " + range.start() + "-" + range.end() + "/" + total);
        }
        HttpStatus status = range.partial() ? HttpStatus.PARTIAL_CONTENT : HttpStatus.OK;
        if (RequestMethod.HEAD.name().equalsIgnoreCase(request.getMethod())) {
            return new ResponseEntity<>(headers, status);
        }
        InputStreamResource body = new InputStreamResource(
                playable.openRange(range.start(), range.length()));
        return new ResponseEntity<>(body, headers, status);
    }

    private ByteRange parseRange(String header, long total) {
        if (total <= 0) throw new IllegalArgumentException("视频为空");
        if (header == null || header.isBlank()) return new ByteRange(0, total - 1, false);
        if (!header.startsWith("bytes=") || header.indexOf(',') >= 0) {
            throw new IllegalArgumentException("仅支持单段字节范围");
        }
        String value = header.substring("bytes=".length()).trim();
        int dash = value.indexOf('-');
        if (dash < 0) throw new IllegalArgumentException("Range 格式错误");
        String startPart = value.substring(0, dash).trim();
        String endPart = value.substring(dash + 1).trim();
        try {
            if (startPart.isEmpty()) {
                long suffix = Long.parseLong(endPart);
                if (suffix <= 0) throw new IllegalArgumentException("Range 格式错误");
                long length = Math.min(suffix, total);
                return new ByteRange(total - length, total - 1, true);
            }
            long start = Long.parseLong(startPart);
            if (start < 0 || start >= total) throw new IllegalArgumentException("Range 越界");
            long end = endPart.isEmpty() ? total - 1 : Long.parseLong(endPart);
            if (end < start) throw new IllegalArgumentException("Range 格式错误");
            return new ByteRange(start, Math.min(end, total - 1), true);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Range 格式错误", e);
        }
    }

    private MediaType safeMediaType(String value) {
        try {
            return value == null || value.isBlank() ? MediaType.APPLICATION_OCTET_STREAM : MediaType.parseMediaType(value);
        } catch (IllegalArgumentException e) {
            return MediaType.APPLICATION_OCTET_STREAM;
        }
    }

    private record ByteRange(long start, long end, boolean partial) {
        long length() {
            return end - start + 1;
        }
    }

    private void markFailedQuietly(AiScoringSessionUserResponse session, String message) {
        if (session == null || session.getSessionId() == null) {
            return;
        }
        try {
            scoringSessionService.markFailed(session.getSessionId(), message);
        } catch (Exception ignored) {
        }
    }

    private Long attrLong(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value instanceof Number number ? number.longValue() : null;
    }

    private String attrString(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value == null ? null : String.valueOf(value);
    }

    private String buildCallbackUrl(HttpServletRequest request, Long sessionId) {
        // Prefer configured internal base URL so Docker ai-scoring can reach backend without
        // going through public nginx (HTTP→HTTPS 301 breaks the callback client).
        if (callbackBaseUrl != null && !callbackBaseUrl.isBlank()) {
            return callbackBaseUrl + "/api/ai-score/sessions/" + sessionId + "/pipeline-callback";
        }
        String scheme = request.getScheme();
        String host = request.getServerName();
        int port = request.getServerPort();
        return String.format("%s://%s:%d/api/ai-score/sessions/%d/pipeline-callback", scheme, host, port, sessionId);
    }

    private String absoluteUploadPath(String relativePath) {
        // Paths are consumed by ai-scoring. Prefer the root as mounted inside that container.
        String root = (aiScoringFileRoot != null && !aiScoringFileRoot.isBlank())
                ? aiScoringFileRoot
                : uploadDir;
        return Path.of(root).resolve(valueOrEmpty(relativePath)).normalize().toString();
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }

    private String dispatchFailureMessage(String reason) {
        String normalizedReason = reason == null ? "" : reason.trim();
        String base;
        if ("track_confirmation_required".equals(normalizedReason)) {
            base = "AI分析未启动：评分绑定信息不完整";
        } else if (normalizedReason.startsWith("AI 服务调用失败")) {
            base = "AI分析未启动：AI 服务连接失败";
        } else {
            base = "AI分析未启动：任务派发失败";
        }
        if (reason == null || reason.isBlank()) {
            return base;
        }
        return base + "（" + reason + "）";
    }
}
