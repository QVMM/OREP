package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.Meeting;
import com.orep.backend.entity.MeetingRecording;
import com.orep.backend.mapper.MeetingMapper;
import com.orep.backend.mapper.MeetingRecordingMapper;
import com.orep.backend.service.LiveKitEgressService;
import com.orep.backend.service.MinioService;
import com.orep.backend.service.PlaybackLibraryService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.*;

/**
 * 录制控制器
 * - 代理前端请求到 Recording Bot 服务（start/stop/status）
 * - 录制文件上传到 MinIO
 * - 用户查看自己的录制
 */
@RestController
@RequestMapping("/api/recording")
public class RecordingController {

    private final MinioService minioService;
    private final LiveKitEgressService liveKitEgressService;
    private final MeetingRecordingMapper recordingMapper;
    private final MeetingMapper meetingMapper;
    private final PlaybackLibraryService playbackLibraryService;

    public RecordingController(MinioService minioService,
                               LiveKitEgressService liveKitEgressService,
                               MeetingRecordingMapper recordingMapper,
                               MeetingMapper meetingMapper,
                               PlaybackLibraryService playbackLibraryService) {
        this.minioService = minioService;
        this.liveKitEgressService = liveKitEgressService;
        this.recordingMapper = recordingMapper;
        this.meetingMapper = meetingMapper;
        this.playbackLibraryService = playbackLibraryService;
    }

    // ========== 录制控制：Egress 优先，Recording Bot 可作为本地回退 ==========
    @Value("${recording.mode:egress}")
    private String recordingMode;

    @Value("${recording.bot.url:http://127.0.0.1:8091}")
    private String botUrl;

    @Value("${recording.bot.secret:OREP_RECORDING_BOT_SECRET}")
    private String botSecret;

    @Value("${recording.callback.base-url:http://127.0.0.1:8080}")
    private String callbackBaseUrl;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    private final RestTemplate recordingControlRestTemplate = createRecordingRestTemplate(30000, 30000);
    private final RestTemplate recordingStatusRestTemplate = createRecordingRestTemplate(1000, 1000);

    private RestTemplate createRecordingRestTemplate(int connectTimeoutMs, int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        return new RestTemplate(factory);
    }

    @PostMapping("/start")
    public Result<Map<String, Object>> startRecording(@RequestBody(required = false) Map<String, Object> body,
                                                      HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        if (userId == null) return Result.error(401, "未登录");

        Long meetingId = parseMeetingId(body);
        if (meetingId == null) return Result.error(400, "meetingId 不能为空");

        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) return Result.error(404, "会议不存在");

        if (!canAccessRecording(userId, meetingId)) {
            return Result.error(403, "无权录制此会议");
        }

        MeetingRecording active = recordingMapper.selectActiveByMeetingId(meetingId);
        if (active != null) {
            return Result.error(409, "该会议已有录制任务正在进行");
        }

        String taskId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        MeetingRecording recording = new MeetingRecording();
        recording.setMeetingId(meetingId);
        recording.setUserId(userId);
        recording.setRecordingId(taskId);
        recording.setStatus("STARTING");
        recording.setMeetingTitle(meeting.getTitle());
        recording.setHasAudio(false);
        recording.setHasVideo(false);
        recording.setStartedAt(LocalDateTime.now());
        recording.setRecordedAt(LocalDateTime.now());
        recordingMapper.insert(recording);

        try {
            if (isEgressMode()) {
                String objectPath = "recordings/meeting_" + meetingId + "/egress_"
                        + recording.getId() + "_" + System.currentTimeMillis() + ".mp4";
                Map<String, Object> egress = liveKitEgressService.startRoomComposite(String.valueOf(meetingId), objectPath);
                String egressId = String.valueOf(egress.getOrDefault("egressId", egress.get("egress_id")));
                if (egressId == null || egressId.isBlank() || "null".equals(egressId)) {
                    throw new IllegalStateException("LiveKit Egress 未返回 egressId");
                }

                recording.setRecordingId(egressId);
                recording.setStatus("RECORDING");
                recording.setFilePath(objectPath);
                recording.setMimeType("video/mp4");
                recording.setHasAudio(true);
                recording.setHasVideo(true);
                recordingMapper.updateById(recording);

                Map<String, Object> data = new HashMap<>();
                data.put("recording", recording);
                data.put("egress", egress);
                data.put("status", "RECORDING");
                data.put("recordingId", recording.getId());
                data.put("taskId", egressId);
                data.put("mode", "egress");
                return Result.success(data);
            }

            Map<String, Object> botBody = new HashMap<>();
            botBody.put("meetingId", meetingId);
            botBody.put("roomName", String.valueOf(meetingId));
            botBody.put("backendRecordingId", recording.getId());
            botBody.put("recordingId", taskId);
            botBody.put("requestedBy", userId);
            botBody.put("callbackBaseUrl", callbackBaseUrl);
            botBody.put("callbackSecret", botSecret);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(botBody, headers);
            ResponseEntity<Map> response = recordingControlRestTemplate.exchange(
                    botUrl + "/api/recording/start", HttpMethod.POST, entity, Map.class);

            recording.setStatus("RECORDING");
            recordingMapper.updateById(recording);

            Map<String, Object> data = new HashMap<>();
            data.put("recording", recording);
            data.put("bot", response.getBody());
            data.put("status", "RECORDING");
            data.put("recordingId", recording.getId());
            data.put("taskId", taskId);
            data.put("mode", "bot");
            return Result.success(data);
        } catch (Exception e) {
            recording.setStatus("FAILED");
            recording.setErrorMessage("录制服务连接失败: " + friendlyRecordingError(e));
            recording.setEndedAt(LocalDateTime.now());
            recordingMapper.updateById(recording);
            return Result.error(500, "录制服务连接失败: " + friendlyRecordingError(e));
        }
    }

    @PostMapping("/stop")
    public Result<Map<String, Object>> stopRecording(@RequestBody(required = false) Map<String, Object> body,
                                                     HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        if (userId == null) return Result.error(401, "未登录");

        Long meetingId = parseMeetingId(body);
        if (meetingId == null) return Result.error(400, "meetingId 不能为空");

        MeetingRecording recording = recordingMapper.selectActiveByMeetingId(meetingId);
        if (recording == null) return Result.error(404, "没有正在进行的录制");
        if (!recording.getUserId().equals(userId) && !canAccessRecording(userId, meetingId)) {
            return Result.error(403, "无权停止此录制");
        }

        recording.setStatus("PROCESSING");
        recordingMapper.updateById(recording);

        try {
            if (isEgressMode()) {
                Map<String, Object> egress = liveKitEgressService.stop(String.valueOf(meetingId), recording.getRecordingId());
                syncEgressRecording(recording, egress);

                Map<String, Object> data = new HashMap<>();
                data.put("recording", recordingMapper.selectById(recording.getId()));
                data.put("egress", egress);
                data.put("status", recordingMapper.selectById(recording.getId()).getStatus());
                data.put("mode", "egress");
                return Result.success(data);
            }

            Map<String, Object> botBody = new HashMap<>();
            botBody.put("meetingId", meetingId);
            botBody.put("backendRecordingId", recording.getId());

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(botBody, headers);
            ResponseEntity<Map> response = recordingControlRestTemplate.exchange(
                    botUrl + "/api/recording/stop", HttpMethod.POST, entity, Map.class);

            Map<String, Object> data = new HashMap<>();
            data.put("recording", recordingMapper.selectById(recording.getId()));
            data.put("bot", response.getBody());
            data.put("status", "PROCESSING");
            data.put("mode", "bot");
            return Result.success(data);
        } catch (Exception e) {
            recording.setStatus("FAILED");
            recording.setErrorMessage("停止录制失败: " + friendlyRecordingError(e));
            recording.setEndedAt(LocalDateTime.now());
            recordingMapper.updateById(recording);
            return Result.error(500, "停止录制失败: " + friendlyRecordingError(e));
        }
    }

    @GetMapping("/status/{meetingId}")
    public Result<Map<String, Object>> getStatus(@PathVariable("meetingId") Long meetingId,
                                                 HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        if (userId == null) return Result.error(401, "未登录");
        if (!canAccessRecording(userId, meetingId)) return Result.error(403, "无权查看此录制状态");

        MeetingRecording active = recordingMapper.selectActiveByMeetingId(meetingId);
        Map<String, Object> data = new HashMap<>();
        data.put("recording", active);
        data.put("status", active == null ? "IDLE" : active.getStatus());
        data.put("mode", isEgressMode() ? "egress" : "bot");
        try {
            if (active != null && isEgressMode()) {
                Map<String, Object> egress = liveKitEgressService.listByEgressId(String.valueOf(meetingId), active.getRecordingId());
                liveKitEgressService.firstEgressItem(egress).ifPresent(info -> syncEgressRecording(active, info));
                data.put("egress", egress);
                MeetingRecording refreshed = recordingMapper.selectById(active.getId());
                data.put("recording", refreshed);
                data.put("status", refreshed == null ? "IDLE" : refreshed.getStatus());
            } else if (!isEgressMode()) {
                ResponseEntity<Map> response = recordingStatusRestTemplate.exchange(
                        botUrl + "/api/recording/status/" + meetingId, HttpMethod.GET, null, Map.class);
                data.put("bot", response.getBody());
            }
        } catch (Exception e) {
            data.put(isEgressMode() ? "egress" : "bot", Map.of("status", "unavailable", "message", e.getMessage()));
        }
        return Result.success(data);
    }

    @PostMapping(value = "/bot-complete", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> completeFromBot(
            @RequestHeader(value = "X-Recording-Secret", required = false) String secret,
            @RequestParam("recording_id") Long recordingDbId,
            @RequestParam("meeting_id") Long meetingId,
            @RequestParam("duration_seconds") Integer durationSeconds,
            @RequestParam(value = "has_audio", defaultValue = "true") Boolean hasAudio,
            @RequestParam(value = "has_video", defaultValue = "true") Boolean hasVideo,
            @RequestParam("video") MultipartFile video
    ) {
        if (!Objects.equals(secret, botSecret)) return Result.error(403, "录制回调密钥无效");
        if (video == null || video.isEmpty()) return Result.error(400, "录制视频为空");

        try {
            MeetingRecording recording = recordingMapper.selectById(recordingDbId);
            if (recording == null || !recording.getMeetingId().equals(meetingId)) {
                return Result.error(404, "录制记录不存在");
            }

            String objectName = "recordings/meeting_" + meetingId + "/recording_"
                    + recordingDbId + "_" + System.currentTimeMillis() + ".webm";
            minioService.upload(objectName, video);

            recording.setFilePath(objectName);
            recording.setMimeType(resolveVideoMimeType(video.getContentType(), objectName));
            recording.setSizeBytes(video.getSize());
            recording.setDurationSeconds(durationSeconds);
            recording.setHasAudio(Boolean.TRUE.equals(hasAudio));
            recording.setHasVideo(Boolean.TRUE.equals(hasVideo));
            recording.setStatus(Boolean.TRUE.equals(hasVideo) ? "READY" : "FAILED");
            recording.setErrorMessage(Boolean.TRUE.equals(hasVideo) ? null : "录制文件缺少视频轨");
            recording.setEndedAt(LocalDateTime.now());
            recordingMapper.updateById(recording);

            return Result.success(Map.of("recordingId", recording.getId(), "filePath", objectName));
        } catch (Exception e) {
            return Result.error(500, "保存录制视频失败: " + e.getMessage());
        }
    }

    private String resolveVideoMimeType(String contentType, String objectName) {
        if (contentType != null
                && !contentType.isBlank()
                && !MediaType.APPLICATION_OCTET_STREAM_VALUE.equalsIgnoreCase(contentType)) {
            return contentType;
        }
        if (objectName != null && objectName.toLowerCase().endsWith(".mp4")) {
            return "video/mp4";
        }
        return "video/webm";
    }

    @PostMapping("/bot-failed")
    public Result<Void> failFromBot(@RequestHeader(value = "X-Recording-Secret", required = false) String secret,
                                    @RequestBody Map<String, Object> body) {
        if (!Objects.equals(secret, botSecret)) return Result.error(403, "录制回调密钥无效");
        Long recordingDbId = body.get("recording_id") instanceof Number n ? n.longValue() : null;
        if (recordingDbId == null) return Result.error(400, "recording_id 不能为空");
        MeetingRecording recording = recordingMapper.selectById(recordingDbId);
        if (recording == null) return Result.error(404, "录制记录不存在");
        recording.setStatus("FAILED");
        recording.setErrorMessage(String.valueOf(body.getOrDefault("error", "录制失败")));
        recording.setEndedAt(LocalDateTime.now());
        recordingMapper.updateById(recording);
        return Result.success();
    }

    private boolean isEgressMode() {
        return "egress".equalsIgnoreCase(recordingMode);
    }

    private String friendlyRecordingError(Exception e) {
        String message = e.getMessage() == null ? String.valueOf(e) : e.getMessage();
        if (message.contains("no response from servers")) {
            return "LiveKit Egress 服务未启动或未连接 Redis，请先启动 livekit-egress";
        }
        return message;
    }

    private void syncEgressRecording(MeetingRecording recording, Map<String, Object> egressInfo) {
        if (recording == null || egressInfo == null || egressInfo.isEmpty()) return;

        if (liveKitEgressService.isComplete(egressInfo)) {
            Object duration = egressInfo.get("duration");
            if (duration instanceof Number n) {
                recording.setDurationSeconds((int) Math.max(1, Math.round(n.doubleValue() / 1_000_000_000D)));
            }
            Object fileResults = egressInfo.get("fileResults");
            if (fileResults instanceof List<?> list && !list.isEmpty() && list.get(0) instanceof Map<?, ?> file) {
                Object size = file.get("size");
                if (size instanceof Number n) recording.setSizeBytes(n.longValue());
                Object filename = file.get("filename");
                if (filename instanceof String s && !s.isBlank()) recording.setFilePath(s);
            }
            recording.setStatus("READY");
            recording.setHasAudio(true);
            recording.setHasVideo(true);
            recording.setErrorMessage(null);
            recording.setEndedAt(LocalDateTime.now());
            recordingMapper.updateById(recording);
        } else if (liveKitEgressService.isFailed(egressInfo)) {
            recording.setStatus("FAILED");
            recording.setErrorMessage(String.valueOf(egressInfo.getOrDefault("error", "LiveKit Egress 录制失败")));
            recording.setEndedAt(LocalDateTime.now());
            recordingMapper.updateById(recording);
        }
    }

    private Long parseMeetingId(Map<String, Object> body) {
        if (body == null) return null;
        Object val = body.get("meetingId");
        if (val == null) val = body.get("meeting_id");
        if (val instanceof Number n) return n.longValue();
        if (val instanceof String s && !s.isBlank()) {
            try { return Long.parseLong(s); } catch (NumberFormatException ignored) {}
        }
        return null;
    }

    private boolean canAccessRecording(Long userId, Long meetingId) {
        return recordingMapper.hasMeetingAccess(meetingId, userId);
    }

    @GetMapping("/health")
    public Result<Map<String, Object>> health() {
        if (isEgressMode()) {
            return Result.success(Map.of(
                    "service", "LiveKit Egress",
                    "mode", "egress",
                    "status", "configured"
            ));
        }
        try {
            ResponseEntity<Map> response = recordingStatusRestTemplate.getForEntity(
                    botUrl + "/api/recording/health", Map.class);
            return Result.success(response.getBody());
        } catch (Exception e) {
            return Result.error(500, "录制服务不可用: " + e.getMessage());
        }
    }

    // ========== 录制文件上传到 MinIO ==========

    /**
     * 上传录制文件
     * POST /api/recording/upload
     * multipart: camera (video), screen (video), audio, meeting_id
     */
    @PostMapping("/upload")
    public Result<Map<String, Object>> uploadRecording(
            @RequestParam("meeting_id") Long meetingId,
            @RequestParam(value = "camera", required = false) MultipartFile camera,
            @RequestParam(value = "screen", required = false) MultipartFile screen,
            @RequestParam("audio") MultipartFile audio,
            @RequestParam(value = "camera_preset", required = false, defaultValue = "unknown") String cameraPreset,
            @RequestParam(value = "camera_orientation", required = false, defaultValue = "unknown") String cameraOrientation,
            @RequestParam(value = "camera_raw_orientation", required = false, defaultValue = "unknown") String cameraRawOrientation,
            @RequestParam(value = "camera_rotation", required = false, defaultValue = "0") String cameraRotation,
            HttpServletRequest request
    ) {
        try {
            // 从 JWT 获取当前用户 ID
            Long userId = (Long) request.getAttribute("userId");
            if (userId == null) {
                return Result.error(401, "未登录");
            }

            String prefix = "recordings/meeting_" + meetingId + "/user_" + userId;

            // 上传到 MinIO
            String cameraPath = null;
            String screenPath = null;

            if (camera != null && !camera.isEmpty()) {
                cameraPath = prefix + "/camera_" + System.currentTimeMillis() + ".webm";
                minioService.upload(cameraPath, camera);
            }
            if (screen != null && !screen.isEmpty()) {
                screenPath = prefix + "/screen_" + System.currentTimeMillis() + ".webm";
                minioService.upload(screenPath, screen);
            }

            String metadataPath = prefix + "/camera_meta_" + System.currentTimeMillis() + ".json";
            String metadataJson = "{"
                    + "\"camera_preset\":\"" + escapeJson(cameraPreset) + "\","
                    + "\"camera_orientation\":\"" + escapeJson(cameraOrientation) + "\","
                    + "\"camera_raw_orientation\":\"" + escapeJson(cameraRawOrientation) + "\","
                    + "\"camera_rotation\":\"" + escapeJson(cameraRotation) + "\""
                    + "}";
            byte[] metadataBytes = metadataJson.getBytes(StandardCharsets.UTF_8);
            minioService.uploadStream(metadataPath, new ByteArrayInputStream(metadataBytes), metadataBytes.length, "application/json");

            String audioPath = prefix + "/audio_" + System.currentTimeMillis() + ".webm";
            minioService.upload(audioPath, audio);

            // 查询会议标题
            Meeting meeting = meetingMapper.selectById(meetingId);
            String title = meeting != null ? meeting.getTitle() : "未知会议";

            // 写入数据库
            MeetingRecording recording = new MeetingRecording();
            recording.setMeetingId(meetingId);
            recording.setUserId(userId);
            recording.setCameraFile(cameraPath);
            recording.setScreenFile(screenPath);
            recording.setAudioFile(audioPath);
            recording.setAudioSizeBytes(audio.getSize());
            recording.setStatus("READY");
            recording.setHasAudio(true);
            recording.setHasVideo(cameraPath != null || screenPath != null);
            recording.setMeetingTitle(title);
            recording.setRecordedAt(LocalDateTime.now());
            recordingMapper.insert(recording);

            Map<String, Object> data = new HashMap<>();
            data.put("recordingId", recording.getId());
            data.put("cameraPath", cameraPath);
            data.put("screenPath", screenPath);
            data.put("audioPath", audioPath);
            data.put("cameraMetadataPath", metadataPath);
            data.put("cameraPreset", cameraPreset);
            data.put("cameraOrientation", cameraOrientation);
            data.put("cameraRotation", cameraRotation);

            return Result.success(data);
        } catch (Exception e) {
            return Result.error(500, "录制文件上传失败: " + e.getMessage());
        }
    }

    private String escapeJson(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    // ========== 用户查看录制列表 ==========

    /**
     * 获取当前用户的统一回放库：会议录制 + 上传/在线评分视频（同一数据源，不重复录制）。
     * GET /api/recording/my
     */
    @GetMapping("/my")
    public Result<List<Map<String, Object>>> getMyRecordings(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        Long tenantId = (Long) request.getAttribute("tenantId");
        if (userId == null) {
            return Result.error(401, "未登录");
        }
        List<Map<String, Object>> library = playbackLibraryService.listForStudent(tenantId, userId);
        // 兼容旧前端：补充 meetingTitle 等字段
        for (Map<String, Object> item : library) {
            item.putIfAbsent("meetingTitle", item.get("title"));
            // 旧学生端用 filePath 判断可播；统一回放库用 playUrl / streamApi
            if (item.get("playUrl") != null) {
                item.putIfAbsent("filePath", item.get("playUrl"));
            }
        }
        return Result.success(library);
    }

    private void annotatePlaybackAvailability(MeetingRecording recording) {
        if (recording == null || !"READY".equals(recording.getStatus())) return;

        String objectPath = primaryPlaybackPath(recording);
        if (objectPath == null || objectPath.isBlank()) {
            markPlaybackUnavailable(recording, "MISSING", "录制文件不存在");
            return;
        }

        Path localPath = resolveLocalUploadPath(objectPath);
        if (localPath != null) {
            if (!Files.exists(localPath) || !Files.isRegularFile(localPath)) {
                markPlaybackUnavailable(recording, "MISSING", "录制文件已从本地存储中缺失");
            }
            return;
        }

        try {
            if (!minioService.exists(normalizeMinioObjectPath(objectPath))) {
                markPlaybackUnavailable(recording, "MISSING", "录制文件已从对象存储中缺失");
            }
        } catch (Exception e) {
            markPlaybackUnavailable(recording, "STORAGE_UNAVAILABLE", "录制存储服务暂不可用，请稍后重试");
        }
    }

    private String primaryPlaybackPath(MeetingRecording recording) {
        if (recording.getFilePath() != null && !recording.getFilePath().isBlank()) return recording.getFilePath();
        if (recording.getCameraFile() != null && !recording.getCameraFile().isBlank()) return recording.getCameraFile();
        if (recording.getScreenFile() != null && !recording.getScreenFile().isBlank()) return recording.getScreenFile();
        if (recording.getAudioFile() != null && !recording.getAudioFile().isBlank()) return recording.getAudioFile();
        return null;
    }

    private void markPlaybackUnavailable(MeetingRecording recording, String status, String message) {
        recording.setStatus(status);
        recording.setErrorMessage(message);
    }

    /**
     * 获取某个会议的录制列表
     * GET /api/recording/meeting/{meetingId}
     * 登录后：会议创建人/参会人看全量；否则只看自己上传的行。无权限时返回空列表，不泄露他人录像。
     */
    @GetMapping("/meeting/{meetingId}")
    public Result<List<MeetingRecording>> getMeetingRecordings(
            @PathVariable("meetingId") Long meetingId,
            HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        if (userId == null) {
            return Result.error(401, "未登录");
        }
        List<MeetingRecording> list = recordingMapper.selectByMeetingId(meetingId);
        if (list == null || list.isEmpty()) {
            return Result.success(List.of());
        }
        if (canAccessRecording(userId, meetingId)) {
            return Result.success(list);
        }
        List<MeetingRecording> owned = list.stream()
                .filter(recording -> userId.equals(recording.getUserId()))
                .toList();
        return Result.success(owned);
    }

    /**
     * 获取录制文件播放 URL
     * GET /api/recording/{id}/play?file=video|camera|screen|audio
     */
    @GetMapping("/{id}/play")
    public Result<Map<String, String>> getPlaybackUrl(
            @PathVariable("id") Long id,
            @RequestParam(value = "file", defaultValue = "video") String fileType,
            HttpServletRequest request) {
        try {
            Long userId = (Long) request.getAttribute("userId");
            if (userId == null) {
                return Result.error(401, "未登录");
            }

            MeetingRecording recording = recordingMapper.selectById(id);
            if (recording == null) {
                return Result.error(404, "录制不存在");
            }

            // 权限检查：必须是该会议的参与者
            boolean isParticipant = !recordingMapper.selectByParticipantUserId(userId).stream()
                    .filter(r -> r.getId().equals(id))
                    .toList().isEmpty();
            if (!isParticipant && !recording.getUserId().equals(userId)) {
                return Result.error(403, "无权查看此录制");
            }

            String objectPath = switch (fileType) {
                case "video", "main" -> recording.getFilePath();
                case "camera" -> recording.getCameraFile();
                case "screen" -> recording.getScreenFile();
                case "audio" -> recording.getAudioFile();
                default -> null;
            };

            if (objectPath == null) {
                return Result.error(400, "文件不存在: " + fileType);
            }

            String url = minioService.getPresignedUrl(objectPath);
            Map<String, String> data = new HashMap<>();
            data.put("url", url);
            return Result.success(data);
        } catch (Exception e) {
            return Result.error(500, "获取播放地址失败: " + e.getMessage());
        }
    }

    /**
     * 通过后端代理流式播放录制文件，避免 HTTPS 页面加载 HTTP MinIO 直链造成 Mixed Content。
     * GET /api/recording/{id}/stream?file=video|camera|screen|audio
     */
    @GetMapping("/{id}/stream")
    public ResponseEntity<org.springframework.core.io.InputStreamResource> streamRecording(
            @PathVariable("id") Long id,
            @RequestParam(value = "file", defaultValue = "video") String fileType,
            HttpServletRequest request) {
        try {
            Long userId = (Long) request.getAttribute("userId");
            if (userId == null) {
                return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
            }

            MeetingRecording recording = recordingMapper.selectById(id);
            if (recording == null) {
                return ResponseEntity.notFound().build();
            }

            boolean isParticipant = !recordingMapper.selectByParticipantUserId(userId).stream()
                    .filter(r -> r.getId().equals(id))
                    .toList().isEmpty();
            if (!isParticipant && !recording.getUserId().equals(userId)) {
                return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
            }

            String objectPath = switch (fileType) {
                case "video", "main" -> recording.getFilePath();
                case "camera" -> recording.getCameraFile();
                case "screen" -> recording.getScreenFile();
                case "audio" -> recording.getAudioFile();
                default -> null;
            };
            if (objectPath == null) {
                return ResponseEntity.notFound().build();
            }

            InputStream stream = openRecordingStream(objectPath);
            MediaType mediaType = "audio".equals(fileType)
                    ? MediaType.parseMediaType("audio/webm")
                    : MediaType.parseMediaType(recording.getMimeType() != null ? recording.getMimeType() : "video/webm");
            return ResponseEntity.ok()
                    .contentType(mediaType)
                    .header(HttpHeaders.CACHE_CONTROL, "private, max-age=3600")
                    .body(new org.springframework.core.io.InputStreamResource(stream));
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    private InputStream openRecordingStream(String objectPath) throws Exception {
        Path localPath = resolveLocalUploadPath(objectPath);
        if (localPath != null) {
            if (Files.exists(localPath) && Files.isRegularFile(localPath)) {
                return Files.newInputStream(localPath);
            }
            throw new NoSuchElementException("录制文件不存在: " + objectPath);
        }
        return minioService.download(normalizeMinioObjectPath(objectPath));
    }

    private String normalizeMinioObjectPath(String objectPath) {
        if (objectPath == null) return "";
        String normalized = objectPath.trim();
        if (normalized.startsWith("/")) normalized = normalized.substring(1);
        if (normalized.startsWith("uploads/")) normalized = normalized.substring("uploads/".length());
        return normalized;
    }

    private Path resolveLocalUploadPath(String objectPath) {
        if (objectPath == null || objectPath.isBlank()) return null;
        String relative = objectPath.trim();
        if (relative.startsWith("/uploads/")) {
            relative = relative.substring("/uploads/".length());
        } else if (relative.startsWith("uploads/")) {
            relative = relative.substring("uploads/".length());
        } else {
            return null;
        }

        Path base = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path candidate = base.resolve(relative).normalize();
        return candidate.startsWith(base) ? candidate : null;
    }

    /**
     * 删除录制
     * DELETE /api/recording/{id}
     */
    @DeleteMapping("/{id}")
    public Result<Void> deleteRecording(
            @PathVariable("id") Long id,
            HttpServletRequest request) {
        try {
            Long userId = (Long) request.getAttribute("userId");
            if (userId == null) {
                return Result.error(401, "未登录");
            }

            MeetingRecording recording = recordingMapper.selectById(id);
            if (recording == null) {
                return Result.error(404, "录制不存在");
            }
            if (!recording.getUserId().equals(userId)) {
                return Result.error(403, "只能删除自己上传的录制");
            }

            // 删除 MinIO 文件
            if (recording.getFilePath() != null) minioService.delete(recording.getFilePath());
            if (recording.getCameraFile() != null) minioService.delete(recording.getCameraFile());
            if (recording.getScreenFile() != null) minioService.delete(recording.getScreenFile());
            if (recording.getAudioFile() != null) minioService.delete(recording.getAudioFile());

            recordingMapper.deleteById(id);
            return Result.success(null);
        } catch (Exception e) {
            return Result.error(500, "删除录制失败: " + e.getMessage());
        }
    }
}
