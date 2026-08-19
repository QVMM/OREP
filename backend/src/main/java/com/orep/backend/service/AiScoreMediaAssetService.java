package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.MeetingRecording;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import com.orep.backend.mapper.MeetingRecordingMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.io.FilterInputStream;
import java.io.OutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Service
public class AiScoreMediaAssetService {
    private static final Set<String> VIDEO_EXTENSIONS = Set.of("mp4", "webm", "mov");
    private static final Set<String> MATERIAL_EXTENSIONS = Set.of("pdf", "ppt", "pptx", "doc", "docx");
    private static final long MAX_VIDEO_BYTES = 5L * 1024 * 1024 * 1024;
    private static final long MAX_MATERIAL_BYTES = 200L * 1024 * 1024;
    private static final long MAX_TOTAL_MATERIAL_BYTES = 1L * 1024 * 1024 * 1024;
    private static final int COPY_BUFFER_BYTES = 1024 * 1024;

    private final AiScoreMediaAssetMapper mediaAssetMapper;
    private final Path uploadRoot;
    private final AiScoreDocketService docketService;
    private final MinioService minioService;
    private MeetingRecordingMapper meetingRecordingMapper;

    public AiScoreMediaAssetService(AiScoreMediaAssetMapper mediaAssetMapper, String uploadDir) {
        this(mediaAssetMapper, uploadDir, null, null);
    }

    public AiScoreMediaAssetService(AiScoreMediaAssetMapper mediaAssetMapper,
                                    String uploadDir,
                                    AiScoreDocketService docketService) {
        this(mediaAssetMapper, uploadDir, docketService, null);
    }

    @Autowired
    public AiScoreMediaAssetService(AiScoreMediaAssetMapper mediaAssetMapper,
                                    @Value("${file.upload-dir:./uploads}") String uploadDir,
                                    @Autowired(required = false) AiScoreDocketService docketService,
                                    @Autowired(required = false) MinioService minioService) {
        this.mediaAssetMapper = mediaAssetMapper;
        this.uploadRoot = Path.of(uploadDir).toAbsolutePath().normalize();
        this.docketService = docketService;
        this.minioService = minioService;
    }

    @Autowired(required = false)
    public void setMeetingRecordingMapper(MeetingRecordingMapper meetingRecordingMapper) {
        this.meetingRecordingMapper = meetingRecordingMapper;
    }

    public AiScoreMediaAsset getVideoAssetBySession(Long sessionId) {
        return mediaAssetMapper.selectOne(
            new LambdaQueryWrapper<AiScoreMediaAsset>()
                .eq(AiScoreMediaAsset::getSessionId, sessionId)
                .eq(AiScoreMediaAsset::getAssetType, "video")
                .last("LIMIT 1")
        );
    }

    public List<AiScoreMediaAsset> getMaterialAssetsBySession(Long sessionId) {
        return mediaAssetMapper.selectList(
            new LambdaQueryWrapper<AiScoreMediaAsset>()
                .eq(AiScoreMediaAsset::getSessionId, sessionId)
                .eq(AiScoreMediaAsset::getAssetType, "material")
        );
    }

    /**
     * Resolves a playable asset without exposing its absolute filesystem path to API clients.
     */
    public PlayableMedia requirePlayableVideo(Long sessionId) {
        validateSession(sessionId);
        AiScoreMediaAsset asset = getVideoAssetBySession(sessionId);
        if (asset == null || asset.getFilePath() == null || asset.getFilePath().isBlank()) {
            throw new IllegalStateException("当前评分会话未关联可播放视频");
        }
        Path path = uploadRoot.resolve(asset.getFilePath()).toAbsolutePath().normalize();
        ensureInsideRoot(path);
        if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
            throw new IllegalStateException("评分视频文件不可用");
        }
        try {
            return new PlayableMedia(asset, path, Files.size(path));
        } catch (IOException e) {
            throw new IllegalStateException("评分视频文件读取失败", e);
        }
    }

    public AiScoreMediaAsset storeVideo(Long sessionId, MultipartFile file, Long userId) {
        return store(sessionId, file, userId, "video", "uploaded_video", VIDEO_EXTENSIONS, MAX_VIDEO_BYTES, true, true);
    }

    public AiScoreMediaAsset storeMeetingVideo(Long sessionId, MultipartFile file, Long userId) {
        return store(sessionId, file, userId, "video", "meeting_recording", VIDEO_EXTENSIONS, MAX_VIDEO_BYTES, true, true);
    }

    public AiScoreMediaAsset storeMaterial(Long sessionId, MultipartFile file, Long userId) {
        return store(sessionId, file, userId, "material", "uploaded_video", MATERIAL_EXTENSIONS, MAX_MATERIAL_BYTES, false, false);
    }

    public void validateUploadBatch(MultipartFile video, List<MultipartFile> materials) {
        if (video == null || video.isEmpty()) {
            throw new IllegalArgumentException("视频文件不能为空");
        }
        if (video.getSize() > MAX_VIDEO_BYTES) {
            throw new IllegalArgumentException("视频文件超过 5GB，请压缩后上传");
        }
        long totalMaterialBytes = 0;
        if (materials == null) {
            return;
        }
        for (MultipartFile material : materials) {
            if (material == null || material.isEmpty()) {
                continue;
            }
            if (material.getSize() > MAX_MATERIAL_BYTES) {
                throw new IllegalArgumentException("单个佐证材料最大200MB：" + safeOriginalName(material.getOriginalFilename()));
            }
            try {
                totalMaterialBytes = Math.addExact(totalMaterialBytes, material.getSize());
            } catch (ArithmeticException e) {
                throw new IllegalArgumentException("佐证材料合计最大1GB，请减少文件后重试");
            }
            if (totalMaterialBytes > MAX_TOTAL_MATERIAL_BYTES) {
                throw new IllegalArgumentException("佐证材料合计最大1GB，请减少文件后重试");
            }
        }
    }

    public AiScoreMediaAsset registerPreprocessedVideoAsset(Long sessionId,
                                                            Path absoluteFile,
                                                            String originalName,
                                                            String mimeType,
                                                            Long userId) {
        validateSession(sessionId);
        Path normalized = absoluteFile.toAbsolutePath().normalize();
        ensureInsideRoot(normalized);
        if (!Files.exists(normalized)) {
            throw new IllegalArgumentException("压缩后视频不存在");
        }
        try {
            StoredFile storedFile = hashExistingFile(normalized);
            if (storedFile.sizeBytes() == 0) {
                throw new IllegalArgumentException("压缩后视频为空");
            }
            if (storedFile.sizeBytes() > MAX_VIDEO_BYTES) {
                throw new IllegalArgumentException("压缩后视频仍超过 5GB，请降低清晰度或拆分后再上传");
            }
            AiScoreMediaAsset asset = new AiScoreMediaAsset();
            asset.setSessionId(sessionId);
            asset.setAssetType("video");
            asset.setSourceType("preprocessed_video");
            asset.setFilePath(uploadRoot.relativize(normalized).toString().replace('\\', '/'));
            asset.setOriginalName(safeOriginalName(originalName));
            asset.setMimeType(mimeType == null || mimeType.isBlank() ? "video/mp4" : mimeType);
            asset.setFileHash(storedFile.sha256());
            asset.setSizeBytes(storedFile.sizeBytes());
            asset.setDurationSeconds(null);
            asset.setHasAudio(true);
            asset.setHasVideo(true);
            asset.setStatus("uploaded");
            asset.setCreatedBy(userId);
            asset.setCreatedAt(LocalDateTime.now());
            mediaAssetMapper.insert(asset);
            maybeBindDocket(sessionId, asset);
            return asset;
        } catch (IOException e) {
            throw new IllegalStateException("压缩后视频读取失败", e);
        }
    }

    public AiScoreMediaAsset registerMeetingRecordingAsset(Long sessionId,
                                                           String filePath,
                                                           String originalName,
                                                           String mimeType,
                                                           Long sizeBytes,
                                                           Long userId) {
        validateSession(sessionId);
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setSessionId(sessionId);
        asset.setAssetType("meeting_recording");
        asset.setSourceType("meeting_recording");
        asset.setFilePath(filePath);
        asset.setOriginalName(originalName);
        asset.setMimeType(mimeType);
        asset.setSizeBytes(sizeBytes);
        asset.setDurationSeconds(null);
        asset.setHasVideo(isVideoLike(originalName, mimeType));
        asset.setHasAudio(isAudioLike(originalName, mimeType) || Boolean.TRUE.equals(asset.getHasVideo()));
        asset.setStatus("uploaded");
        asset.setCreatedBy(userId);
        asset.setCreatedAt(LocalDateTime.now());
        Path readable = resolveReadableUpload(filePath);
        if (readable != null) {
            try {
                StoredFile storedFile = hashExistingFile(readable);
                asset.setFileHash(storedFile.sha256());
                if (asset.getSizeBytes() == null) {
                    asset.setSizeBytes(storedFile.sizeBytes());
                }
            } catch (IOException e) {
                throw new IllegalStateException("会议录制文件读取失败", e);
            }
        } else {
            StoredFile remote = hashObjectStore(filePath);
            if (remote != null) {
                asset.setFileHash(remote.sha256());
                if (asset.getSizeBytes() == null) {
                    asset.setSizeBytes(remote.sizeBytes());
                }
            } else {
                asset.setFileHash(null);
            }
        }
        if (asset.getFileHash() == null || asset.getFileHash().isBlank()) {
            asset.setStatus("hash_missing");
        }
        mediaAssetMapper.insert(asset);
        maybeBindDocket(sessionId, asset);
        return asset;
    }

    public AiScoreMediaAsset registerMeetingRecordingForSession(Long sessionId,
                                                               Long recordingId,
                                                               Long meetingId,
                                                               Long userId) {
        MeetingRecording recording = resolveRecording(recordingId, meetingId);
        if (recording == null) {
            return null;
        }
        String path = firstPlayablePath(recording);
        if (path == null) {
            return null;
        }
        String originalName = Path.of(path.replace('\\', '/')).getFileName() == null
                ? "meeting-recording"
                : Path.of(path.replace('\\', '/')).getFileName().toString();
        return registerMeetingRecordingAsset(
                sessionId,
                path,
                originalName,
                recording.getMimeType(),
                recording.getSizeBytes(),
                userId
        );
    }

    private MeetingRecording resolveRecording(Long recordingId, Long meetingId) {
        if (meetingRecordingMapper == null) {
            return null;
        }
        if (recordingId != null && recordingId > 0) {
            return meetingRecordingMapper.selectById(recordingId);
        }
        if (meetingId == null || meetingId <= 0) {
            return null;
        }
        List<MeetingRecording> rows = meetingRecordingMapper.selectByMeetingId(meetingId);
        if (rows == null || rows.isEmpty()) {
            return null;
        }
        for (MeetingRecording row : rows) {
            if (row != null && "READY".equalsIgnoreCase(row.getStatus()) && firstPlayablePath(row) != null) {
                return row;
            }
        }
        for (MeetingRecording row : rows) {
            if (row != null && firstPlayablePath(row) != null) {
                return row;
            }
        }
        return null;
    }

    static String firstPlayablePath(MeetingRecording recording) {
        if (recording == null) {
            return null;
        }
        String[] candidates = {
                recording.getFilePath(),
                recording.getCameraFile(),
                recording.getScreenFile()
        };
        for (String candidate : candidates) {
            if (candidate != null && !candidate.isBlank()) {
                return candidate.trim();
            }
        }
        return null;
    }

    private AiScoreMediaAsset store(Long sessionId,
                                    MultipartFile file,
                                    Long userId,
                                    String assetType,
                                    String sourceType,
                                    Set<String> allowedExtensions,
                                    long maxBytes,
                                    boolean hasVideo,
                                    boolean hasAudio) {
        validateSession(sessionId);
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("文件为空");
        }
        if (file.getSize() > maxBytes) {
            throw new IllegalArgumentException("video".equals(assetType)
                    ? "视频文件超过 5GB，请先压缩后上传"
                    : "材料文件超过 200MB，请压缩后上传");
        }

        String originalName = safeOriginalName(file.getOriginalFilename());
        String extension = extensionOf(originalName);
        if (!allowedExtensions.contains(extension)) {
            throw new IllegalArgumentException("video".equals(assetType) ? "视频格式不支持" : "材料格式不支持");
        }
        validateMime(assetType, extension, file.getContentType());

        Path sessionDir = uploadRoot.resolve("ai-score").resolve(String.valueOf(sessionId)).normalize();
        ensureInsideRoot(sessionDir);
        try {
            Files.createDirectories(sessionDir);
            Path target = sessionDir.resolve(UUID.randomUUID() + "-" + originalName).normalize();
            ensureInsideRoot(target);
            StoredFile storedFile = streamToDiskAndHash(file, target);
            if (storedFile.sizeBytes() == 0) {
                Files.deleteIfExists(target);
                throw new IllegalArgumentException("文件为空");
            }

            AiScoreMediaAsset asset = new AiScoreMediaAsset();
            asset.setSessionId(sessionId);
            asset.setAssetType(assetType);
            asset.setSourceType(sourceType);
            asset.setFilePath(uploadRoot.relativize(target).toString().replace('\\', '/'));
            asset.setOriginalName(originalName);
            asset.setMimeType(file.getContentType());
            asset.setFileHash(storedFile.sha256());
            asset.setSizeBytes(storedFile.sizeBytes());
            asset.setDurationSeconds(null);
            asset.setHasAudio(hasAudio);
            asset.setHasVideo(hasVideo);
            asset.setStatus("uploaded");
            asset.setCreatedBy(userId);
            asset.setCreatedAt(LocalDateTime.now());
            mediaAssetMapper.insert(asset);
            maybeBindDocket(sessionId, asset);
            return asset;
        } catch (IOException e) {
            throw new IllegalStateException("文件保存失败", e);
        }
    }

    private void maybeBindDocket(Long sessionId, AiScoreMediaAsset asset) {
        if (docketService == null || asset == null) {
            return;
        }
        if (!"video".equals(asset.getAssetType()) && !"meeting_recording".equals(asset.getAssetType())) {
            return;
        }
        String fileHash = asset.getFileHash();
        if (fileHash == null || fileHash.isBlank()) {
            return;
        }
        docketService.bindAfterVideoHash(sessionId, fileHash);
    }

    private StoredFile streamToDiskAndHash(MultipartFile file, Path target) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long totalBytes = 0;
            byte[] buffer = new byte[COPY_BUFFER_BYTES];
            try (InputStream input = file.getInputStream();
                 OutputStream output = Files.newOutputStream(target)) {
                int read;
                while ((read = input.read(buffer)) != -1) {
                    digest.update(buffer, 0, read);
                    output.write(buffer, 0, read);
                    totalBytes += read;
                }
            }
            return new StoredFile(hex(digest.digest()), totalBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 不可用", e);
        } catch (IOException e) {
            throw new IllegalStateException("文件保存失败", e);
        }
    }

    private StoredFile hashExistingFile(Path file) throws IOException {
        try (InputStream input = Files.newInputStream(file)) {
            return hashStream(input);
        }
    }

    private StoredFile hashObjectStore(String objectName) {
        if (minioService == null || !isObjectKey(objectName)) {
            return null;
        }
        try {
            if (!minioService.exists(objectName)) {
                return null;
            }
            try (InputStream input = minioService.download(objectName)) {
                return hashStream(input);
            }
        } catch (IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("会议对象存储文件读取失败", e);
        }
    }

    private static boolean isObjectKey(String filePath) {
        if (filePath == null || filePath.isBlank()) {
            return false;
        }
        String key = filePath.trim().replace('\\', '/');
        if (key.startsWith("/") || key.contains("..") || Path.of(filePath).isAbsolute()) {
            return false;
        }
        return key.indexOf('/') >= 0;
    }

    private StoredFile hashStream(InputStream input) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long totalBytes = 0;
            byte[] buffer = new byte[COPY_BUFFER_BYTES];
            int read;
            while ((read = input.read(buffer)) != -1) {
                digest.update(buffer, 0, read);
                totalBytes += read;
            }
            return new StoredFile(hex(digest.digest()), totalBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 不可用", e);
        }
    }

    private void validateSession(Long sessionId) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }
    }

    private void validateMime(String assetType, String extension, String mimeType) {
        if (mimeType == null || mimeType.isBlank() || "application/octet-stream".equalsIgnoreCase(mimeType)) {
            return;
        }
        String lower = mimeType.toLowerCase(Locale.ROOT);
        if ("video".equals(assetType) && lower.startsWith("video/")) {
            return;
        }
        if ("material".equals(assetType) && (lower.startsWith("application/") || lower.startsWith("text/"))) {
            return;
        }
        if ("mov".equals(extension) && lower.equals("video/quicktime")) {
            return;
        }
        throw new IllegalArgumentException("video".equals(assetType) ? "视频 MIME 类型不支持" : "材料 MIME 类型不支持");
    }

    private String hex(byte[] hashed) {
        StringBuilder builder = new StringBuilder();
        for (byte b : hashed) {
            builder.append(String.format("%02x", b));
        }
        return builder.toString();
    }

    private String safeOriginalName(String originalFilename) {
        String name = originalFilename == null || originalFilename.isBlank() ? "upload.bin" : originalFilename;
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
        return name.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private Path resolveReadableUpload(String filePath) {
        if (filePath == null || filePath.isBlank()) {
            return null;
        }
        Path raw = Path.of(filePath);
        Path candidate = raw.isAbsolute() ? raw.toAbsolutePath().normalize() : uploadRoot.resolve(raw).normalize();
        if (!candidate.startsWith(uploadRoot) || !Files.isRegularFile(candidate)) {
            return null;
        }
        return candidate;
    }

    private void ensureInsideRoot(Path path) {
        if (!path.toAbsolutePath().normalize().startsWith(uploadRoot)) {
            throw new IllegalArgumentException("文件路径非法");
        }
    }

    private boolean isVideoLike(String name, String mimeType) {
        return (mimeType != null && mimeType.toLowerCase(Locale.ROOT).startsWith("video/"))
                || VIDEO_EXTENSIONS.contains(extensionOf(safeOriginalName(name)));
    }

    private boolean isAudioLike(String name, String mimeType) {
        String lowerMime = mimeType == null ? "" : mimeType.toLowerCase(Locale.ROOT);
        String ext = extensionOf(safeOriginalName(name));
        return lowerMime.startsWith("audio/") || Set.of("mp3", "wav", "m4a", "aac", "webm").contains(ext);
    }

    private record StoredFile(String sha256, long sizeBytes) {
    }

    public record PlayableMedia(AiScoreMediaAsset asset, Path path, long sizeBytes) {
        public InputStream openRange(long start, long length) throws IOException {
            if (start < 0 || length < 0 || start > sizeBytes || length > sizeBytes - start) {
                throw new IllegalArgumentException("视频字节范围非法");
            }
            InputStream input = Files.newInputStream(path);
            try {
                input.skipNBytes(start);
                return new LimitedInputStream(input, length);
            } catch (Exception e) {
                input.close();
                throw e;
            }
        }
    }

    private static final class LimitedInputStream extends FilterInputStream {
        private long remaining;

        private LimitedInputStream(InputStream input, long remaining) {
            super(input);
            this.remaining = remaining;
        }

        @Override
        public int read() throws IOException {
            if (remaining <= 0) return -1;
            int value = super.read();
            if (value >= 0) remaining--;
            return value;
        }

        @Override
        public int read(byte[] bytes, int offset, int length) throws IOException {
            if (remaining <= 0) return -1;
            int read = super.read(bytes, offset, (int) Math.min(length, remaining));
            if (read > 0) remaining -= read;
            return read;
        }
    }
}
