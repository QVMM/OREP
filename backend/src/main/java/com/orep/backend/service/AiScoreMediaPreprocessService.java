package com.orep.backend.service;

import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoreMediaPreprocessJob;
import com.orep.backend.mapper.AiScoreMediaPreprocessJobMapper;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Service
public class AiScoreMediaPreprocessService implements DisposableBean {
    private static final long MAX_SOURCE_VIDEO_BYTES = 5L * 1024 * 1024 * 1024;
    private static final long MAX_TARGET_VIDEO_BYTES = 5L * 1024 * 1024 * 1024;
    private static final int COPY_BUFFER_BYTES = 1024 * 1024;

    private final AiScoreMediaPreprocessJobMapper jobMapper;
    private final AiScoringSessionService scoringSessionService;
    private final AiScoreMediaAssetService mediaAssetService;
    private final Path uploadRoot;
    private final String ffmpegBin;
    private final ExecutorService executor = Executors.newFixedThreadPool(2);

    public AiScoreMediaPreprocessService(AiScoreMediaPreprocessJobMapper jobMapper,
                                         AiScoringSessionService scoringSessionService,
                                         AiScoreMediaAssetService mediaAssetService,
                                         @Value("${file.upload-dir:./uploads}") String uploadDir,
                                         @Value("${ai-score.preprocess.ffmpeg-bin:ffmpeg}") String ffmpegBin) {
        this.jobMapper = jobMapper;
        this.scoringSessionService = scoringSessionService;
        this.mediaAssetService = mediaAssetService;
        this.uploadRoot = Path.of(uploadDir).toAbsolutePath().normalize();
        this.ffmpegBin = ffmpegBin;
    }

    public Map<String, Object> createJob(MultipartFile video,
                                         Long projectId,
                                         Long teamId,
                                         String trackId,
                                         String trackName,
                                         Boolean useHistoryMemory,
                                         Boolean juryEnabled,
                                         Long userId) {
        if (video == null || video.isEmpty()) {
            throw new IllegalArgumentException("视频文件不能为空");
        }
        if (video.getSize() > MAX_SOURCE_VIDEO_BYTES) {
            throw new IllegalArgumentException("源视频超过 5GB，请压缩后上传");
        }
        String originalName = safeOriginalName(video.getOriginalFilename());
        String ext = extensionOf(originalName);
        if (!("mp4".equals(ext) || "webm".equals(ext) || "mov".equals(ext))) {
            throw new IllegalArgumentException("视频格式不支持");
        }

        String jobNo = nextJobNo();
        Path jobDir = uploadRoot.resolve("ai-score-preprocess").resolve(jobNo).normalize();
        ensureInsideRoot(jobDir);
        Path sourcePath = jobDir.resolve("source-" + originalName).normalize();
        ensureInsideRoot(sourcePath);
        try {
            Files.createDirectories(jobDir);
            copy(video, sourcePath);
        } catch (IOException e) {
            throw new IllegalStateException("源视频保存失败", e);
        }

        LocalDateTime now = LocalDateTime.now();
        AiScoreMediaPreprocessJob job = new AiScoreMediaPreprocessJob();
        job.setJobNo(jobNo);
        job.setProjectId(projectId);
        job.setTeamId(teamId);
        job.setTrackId(trackId);
        job.setTrackName(trackName);
        job.setSourceFilePath(uploadRoot.relativize(sourcePath).toString().replace('\\', '/'));
        job.setSourceFileSize(video.getSize());
        job.setSourceMimeType(video.getContentType());
        job.setStatus("queued");
        job.setProgressPercent(5);
        job.setUseHistoryMemory(useHistoryMemory == null || useHistoryMemory);
        job.setJuryEnabled(false);
        job.setCreatedBy(userId);
        job.setCreatedAt(now);
        job.setUpdatedAt(now);
        jobMapper.insert(job);

        executor.submit(() -> runJob(job.getId(), originalName, userId));
        return toResponse(jobMapper.selectById(job.getId()));
    }

    public Map<String, Object> status(Long jobId) {
        return status(jobId, null);
    }

    public Map<String, Object> status(Long jobId, Long userId) {
        AiScoreMediaPreprocessJob job = requireJob(jobId);
        if (userId == null || !userId.equals(job.getCreatedBy())) {
            throw new IllegalStateException("预处理任务不存在");
        }
        return toResponse(job);
    }

    private void runJob(Long jobId, String originalName, Long userId) {
        AiScoreMediaPreprocessJob job = requireJob(jobId);
        try {
            update(job, "probing", 10, null);
            Path source = uploadRoot.resolve(job.getSourceFilePath()).normalize();
            ensureInsideRoot(source);
            if (!Files.exists(source)) {
                throw new IllegalStateException("源视频不存在");
            }

            update(job, "compressing", 30, null);
            Path target = source.getParent().resolve("standard-" + UUID.randomUUID() + ".mp4").normalize();
            ensureInsideRoot(target);
            runFfmpeg(source, target);
            long targetSize = Files.size(target);
            if (targetSize > MAX_TARGET_VIDEO_BYTES) {
                Files.deleteIfExists(target);
                throw new IllegalStateException("压缩后视频仍超过 5GB，请降低清晰度或拆分后再上传");
            }

            update(job, "registering", 85, null);
            AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
            request.setProjectId(job.getProjectId());
            request.setTeamId(job.getTeamId());
            request.setTrackId(job.getTrackId());
            request.setTrackName(job.getTrackName());
            request.setSourceType("uploaded_video");
            request.setUseHistoryMemory(job.getUseHistoryMemory());
            request.setJuryEnabled(job.getJuryEnabled());
            AiScoringSessionUserResponse session = scoringSessionService.createSession(request, userId);
            AiScoreMediaAsset asset = mediaAssetService.registerPreprocessedVideoAsset(
                    session.getSessionId(),
                    target,
                    originalName,
                    "video/mp4",
                    userId
            );
            scoringSessionService.markUploaded(session.getSessionId());

            job = requireJob(jobId);
            job.setSessionId(session.getSessionId());
            job.setMediaAssetId(asset.getId());
            job.setTargetFilePath(uploadRoot.relativize(target).toString().replace('\\', '/'));
            job.setTargetFileSize(targetSize);
            job.setStatus("completed");
            job.setProgressPercent(100);
            job.setErrorMessage(null);
            job.setCompletedAt(LocalDateTime.now());
            job.setUpdatedAt(LocalDateTime.now());
            jobMapper.updateById(job);
        } catch (Exception e) {
            AiScoreMediaPreprocessJob failed = requireJob(jobId);
            failed.setStatus("failed");
            failed.setProgressPercent(Math.max(1, failed.getProgressPercent() == null ? 1 : failed.getProgressPercent()));
            failed.setErrorMessage(e.getMessage());
            failed.setUpdatedAt(LocalDateTime.now());
            failed.setCompletedAt(LocalDateTime.now());
            jobMapper.updateById(failed);
        }
    }

    private void runFfmpeg(Path source, Path target) throws IOException, InterruptedException {
        Process process = new ProcessBuilder(
                ffmpegBin,
                "-y",
                "-i", source.toString(),
                "-vf", "scale=1920:-2:force_original_aspect_ratio=decrease",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "28",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                target.toString()
        ).redirectErrorStream(true)
                .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                .start();
        int exit = process.waitFor();
        if (exit != 0 || !Files.exists(target) || Files.size(target) == 0) {
            throw new IllegalStateException("ffmpeg 压缩失败，请确认视频可播放且 ffmpeg 可用");
        }
    }

    private void update(AiScoreMediaPreprocessJob job, String status, int progress, String error) {
        job.setStatus(status);
        job.setProgressPercent(progress);
        job.setErrorMessage(error);
        job.setUpdatedAt(LocalDateTime.now());
        jobMapper.updateById(job);
    }

    private void copy(MultipartFile file, Path target) throws IOException {
        byte[] buffer = new byte[COPY_BUFFER_BYTES];
        try (InputStream input = file.getInputStream();
             OutputStream output = Files.newOutputStream(target)) {
            int read;
            while ((read = input.read(buffer)) != -1) {
                output.write(buffer, 0, read);
            }
        }
    }

    private AiScoreMediaPreprocessJob requireJob(Long jobId) {
        AiScoreMediaPreprocessJob job = jobMapper.selectById(jobId);
        if (job == null) {
            throw new IllegalArgumentException("预处理任务不存在");
        }
        return job;
    }

    private Map<String, Object> toResponse(AiScoreMediaPreprocessJob job) {
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("jobId", job.getId());
        response.put("jobNo", job.getJobNo());
        response.put("sessionId", job.getSessionId());
        response.put("mediaAssetId", job.getMediaAssetId());
        response.put("status", job.getStatus());
        response.put("progressPercent", job.getProgressPercent());
        response.put("errorMessage", job.getErrorMessage());
        response.put("sourceFileSize", job.getSourceFileSize());
        response.put("targetFileSize", job.getTargetFileSize());
        response.put("trackName", job.getTrackName());
        return response;
    }

    private String nextJobNo() {
        return "PP-" + DateTimeFormatter.ofPattern("yyyyMMddHHmmss").format(LocalDateTime.now())
                + "-" + UUID.randomUUID().toString().substring(0, 8);
    }

    private String safeOriginalName(String originalFilename) {
        String name = originalFilename == null || originalFilename.isBlank() ? "upload.mp4" : originalFilename;
        name = name.replace('\\', '/');
        int slash = name.lastIndexOf('/');
        if (slash >= 0) {
            name = name.substring(slash + 1);
        }
        return name.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private String extensionOf(String name) {
        int dot = name.lastIndexOf('.');
        if (dot < 0 || dot == name.length() - 1) {
            return "";
        }
        return name.substring(dot + 1).toLowerCase();
    }

    private void ensureInsideRoot(Path path) {
        if (!path.toAbsolutePath().normalize().startsWith(uploadRoot)) {
            throw new IllegalArgumentException("文件路径非法");
        }
    }

    @Override
    public void destroy() {
        executor.shutdownNow();
    }
}
