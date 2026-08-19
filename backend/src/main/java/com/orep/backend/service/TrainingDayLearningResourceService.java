package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Service
public class TrainingDayLearningResourceService {
    private static final long MAX_VIDEO_BYTES = 500L * 1024 * 1024;
    private static final long MAX_DOCUMENT_BYTES = 50L * 1024 * 1024;
    private static final Set<String> VIDEO_EXTENSIONS = Set.of("mp4", "webm", "mov");
    private static final Set<String> AUDIO_EXTENSIONS = Set.of("mp3", "wav", "m4a");
    private static final Set<String> OFFICE_EXTENSIONS = Set.of(
            "pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx"
    );
    private static final Set<String> TEXT_EXTENSIONS = Set.of("csv", "txt", "md");
    private static final Set<String> IMAGE_EXTENSIONS = Set.of("jpg", "jpeg", "png", "gif", "webp");
    private static final Set<String> ARCHIVE_EXTENSIONS = Set.of("zip", "rar", "7z");
    private static final Set<String> DOCUMENT_EXTENSIONS = Stream.of(
                    AUDIO_EXTENSIONS,
                    OFFICE_EXTENSIONS,
                    TEXT_EXTENSIONS,
                    IMAGE_EXTENSIONS,
                    ARCHIVE_EXTENSIONS
            )
            .flatMap(Collection::stream)
            .collect(Collectors.toUnmodifiableSet());
    private static final String SUPPORTED_FILE_TYPES =
            "MP4、WebM、MOV、MP3、WAV、M4A、PDF、DOC、DOCX、PPT、PPTX、XLS、XLSX、"
                    + "CSV、TXT、MD、JPG、JPEG、PNG、GIF、WebP、ZIP、RAR、7Z";
    private static final Set<String> RESOURCE_TYPES = Set.of("VIDEO", "DOCUMENT", "LINK", "EMBED_VIDEO");
    private static final double DEFAULT_COMPLETE_RATIO = 0.80;

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final Path uploadRoot;
    private final TrainingDayAvailabilityService availabilityService;

    public TrainingDayLearningResourceService(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            @Value("${file.upload-dir:./uploads}") String uploadDir,
            TrainingDayAvailabilityService availabilityService
    ) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
        this.availabilityService = availabilityService;
    }

    @PostConstruct
    void ensureTables() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS training_day_learning_resource (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              training_day_id BIGINT NOT NULL,
              resource_type VARCHAR(20) NOT NULL,
              title VARCHAR(200) NOT NULL,
              description VARCHAR(1000) DEFAULT NULL,
              resource_url VARCHAR(1000) NOT NULL,
              file_name VARCHAR(255) DEFAULT NULL,
              file_size BIGINT NOT NULL DEFAULT 0,
              mime_type VARCHAR(120) DEFAULT NULL,
              duration_seconds INT NOT NULL DEFAULT 0,
              is_required TINYINT(1) NOT NULL DEFAULT 1,
              sort_order INT NOT NULL DEFAULT 0,
              status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
              created_by BIGINT NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              KEY idx_training_learning_day (training_day_id,status,sort_order)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """);
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS training_learning_progress (
              id BIGINT PRIMARY KEY AUTO_INCREMENT,
              user_id BIGINT NOT NULL,
              learning_resource_id BIGINT NOT NULL,
              learned_seconds INT NOT NULL DEFAULT 0,
              actual_learning_seconds INT NOT NULL DEFAULT 0,
              progress_percent INT NOT NULL DEFAULT 0,
              watched_ranges_json TEXT DEFAULT NULL,
              last_position_seconds INT NOT NULL DEFAULT 0,
              video_duration_seconds INT NOT NULL DEFAULT 0,
              heartbeat_session VARCHAR(64) DEFAULT NULL,
              heartbeat_position_seconds INT DEFAULT NULL,
              heartbeat_at DATETIME(3) DEFAULT NULL,
              status VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED',
              last_learned_at DATETIME DEFAULT NULL,
              completed_at DATETIME DEFAULT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uk_training_learning_user_resource (user_id,learning_resource_id),
              KEY idx_training_learning_progress_user (user_id,status,updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """);
        ensureColumn("training_learning_progress", "actual_learning_seconds", "INT NOT NULL DEFAULT 0");
        ensureColumn("training_learning_progress", "watched_ranges_json", "TEXT DEFAULT NULL");
        ensureColumn("training_learning_progress", "last_position_seconds", "INT NOT NULL DEFAULT 0");
        ensureColumn("training_learning_progress", "video_duration_seconds", "INT NOT NULL DEFAULT 0");
        ensureColumn("training_learning_progress", "heartbeat_session", "VARCHAR(64) DEFAULT NULL");
        ensureColumn("training_learning_progress", "heartbeat_position_seconds", "INT DEFAULT NULL");
        ensureColumn("training_learning_progress", "heartbeat_at", "DATETIME(3) DEFAULT NULL");
        // 站外内嵌视频元数据
        ensureColumn("training_day_learning_resource", "provider", "VARCHAR(32) DEFAULT NULL");
        ensureColumn("training_day_learning_resource", "provider_video_id", "VARCHAR(64) DEFAULT NULL");
        ensureColumn("training_day_learning_resource", "embed_url", "VARCHAR(1000) DEFAULT NULL");
        ensureColumn("training_day_learning_resource", "cover_url", "VARCHAR(1000) DEFAULT NULL");
        ensureColumn("training_day_learning_resource", "complete_ratio", "DECIMAL(4,2) NOT NULL DEFAULT 0.80");
    }

    private void ensureColumn(String table, String column, String definition) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema=DATABASE() AND table_name=? AND column_name=?
            """, Integer.class, table, column);
        if (count != null && count == 0) jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition);
    }

    public List<Map<String, Object>> teacherResources(
            Long tenantId,
            Long userId,
            String role,
            Long dayId
    ) {
        assertTeacherReadAccess(tenantId, userId, role, dayId);
        return resources(dayId, false, null);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> attachTeacherResources(
            Map<String, Object> payload,
            Long tenantId,
            Long userId,
            String role
    ) {
        List<Map<String, Object>> days = (List<Map<String, Object>>) payload.getOrDefault("days", List.of());
        for (Map<String, Object> day : days) {
            Long dayId = longValue(day.get("dayId"));
            if (dayId != null) day.put("learningResources", teacherResources(tenantId, userId, role, dayId));
        }
        return payload;
    }

    @Transactional
    public Map<String, Object> upload(
            Long tenantId,
            Long userId,
            String role,
            Long dayId,
            MultipartFile file,
            Map<String, Object> metadata
    ) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        if (file == null || file.isEmpty()) throw badRequest("请选择要上传的学习内容");
        String displayName = safeDisplayName(file.getOriginalFilename());
        String extension = extension(displayName);
        String resourceType = classifyResourceType(extension);
        if (resourceType == null) throw badRequest("暂不支持该文件类型。支持：" + SUPPORTED_FILE_TYPES);
        long maxBytes = "VIDEO".equals(resourceType) ? MAX_VIDEO_BYTES : MAX_DOCUMENT_BYTES;
        if (file.getSize() > maxBytes) {
            throw badRequest("VIDEO".equals(resourceType) ? "视频不能超过 500MB" : "学习资料不能超过 50MB");
        }
        validateFileSignature(file, extension);

        String storedName = UUID.randomUUID() + "." + extension;
        Path relative = Paths.get("training", "learning", String.valueOf(dayId), resourceType.toLowerCase(Locale.ROOT), storedName);
        Path target = uploadRoot.resolve(relative).normalize();
        if (!target.startsWith(uploadRoot)) throw badRequest("文件路径不合法");
        try {
            Files.createDirectories(target.getParent());
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "学习内容上传失败");
        }

        String title = text(metadata.get("title"));
        if (title == null) title = stripExtension(displayName);
        int durationSeconds = boundedInt(metadata.get("durationSeconds"), 0, 24 * 60 * 60);
        boolean required = booleanValue(metadata.get("required"), true);
        int sortOrder = nextSortOrder(dayId);
        String url = "/uploads/" + relative.toString().replace('\\', '/');
        Long resourceId = insertResource(
                dayId, resourceType, title, text(metadata.get("description")), url,
                displayName, file.getSize(), safeMime(extension),
                durationSeconds, required, sortOrder, userId
        );
        return teacherResource(resourceId, dayId);
    }

    @Transactional
    public Map<String, Object> createLink(
            Long tenantId,
            Long userId,
            String role,
            Long dayId,
            Map<String, Object> body
    ) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        String title = requiredText(body.get("title"), "请填写学习内容标题");
        String url = requiredText(body.get("url"), "请填写课程链接");
        if (!url.toLowerCase(Locale.ROOT).startsWith("https://")) throw badRequest("外部链接仅支持 HTTPS");
        Long resourceId = insertResource(
                dayId, "LINK", title, text(body.get("description")), url,
                null, 0L, "text/uri-list",
                boundedInt(body.get("durationSeconds"), 0, 24 * 60 * 60),
                booleanValue(body.get("required"), true), nextSortOrder(dayId), userId
        );
        return teacherResource(resourceId, dayId);
    }

    /** 解析站外视频链接（当前支持 bilibili） */
    public Map<String, Object> parseEmbed(String rawUrl) {
        Map<String, Object> parsed = parseExternalVideo(rawUrl);
        if (parsed == null || !Boolean.TRUE.equals(parsed.get("canEmbed"))) {
            throw badRequest("暂无法识别为可内嵌视频。请粘贴 B 站视频链接（含 BV 号），或改用「普通外链」。");
        }
        return parsed;
    }

    @Transactional
    public Map<String, Object> createEmbed(
            Long tenantId,
            Long userId,
            String role,
            Long dayId,
            Map<String, Object> body
    ) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        Map<String, Object> parsed = parseExternalVideo(text(body.get("url")));
        if (parsed == null || !Boolean.TRUE.equals(parsed.get("canEmbed"))) {
            throw badRequest("无法内嵌该链接，请检查是否为支持的站外视频地址");
        }
        String title = text(body.get("title"));
        if (title == null || title.isBlank()) {
            title = text(parsed.get("title"));
        }
        if (title == null || title.isBlank()) {
            title = "站外视频学习";
        }
        if (title.length() > 200) title = title.substring(0, 200);
        int durationSeconds = boundedInt(body.get("durationSeconds"), 0, 24 * 60 * 60);
        if (durationSeconds <= 0) {
            throw badRequest("请填写预计学习时长（分钟），用于统计完成进度");
        }
        double completeRatio = body.containsKey("completeRatio")
                ? Math.max(0.5, Math.min(1.0, doubleValue(body.get("completeRatio"), DEFAULT_COMPLETE_RATIO)))
                : DEFAULT_COMPLETE_RATIO;
        String originalUrl = String.valueOf(parsed.get("originalUrl"));
        String embedUrl = String.valueOf(parsed.get("embedUrl"));
        String provider = String.valueOf(parsed.get("provider"));
        String videoId = String.valueOf(parsed.get("providerVideoId"));
        String coverUrl = text(parsed.get("coverUrl"));
        if (body.containsKey("coverUrl") && text(body.get("coverUrl")) != null) {
            coverUrl = text(body.get("coverUrl"));
        }
        Long resourceId = insertResource(
                dayId, "EMBED_VIDEO", title, text(body.get("description")), originalUrl,
                null, 0L, "text/html",
                durationSeconds,
                booleanValue(body.get("required"), true), nextSortOrder(dayId), userId
        );
        jdbc.update("""
            UPDATE training_day_learning_resource
            SET provider=?, provider_video_id=?, embed_url=?, cover_url=?, complete_ratio=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND training_day_id=?
            """, provider, videoId, embedUrl, coverUrl, completeRatio, resourceId, dayId);
        return teacherResource(resourceId, dayId);
    }

    @Transactional
    public Map<String, Object> update(
            Long tenantId,
            Long userId,
            String role,
            Long dayId,
            Long resourceId,
            Map<String, Object> body
    ) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        Map<String, Object> current = teacherResource(resourceId, dayId);
        String title = body.containsKey("title")
                ? requiredText(body.get("title"), "学习内容标题不能为空")
                : String.valueOf(current.get("title"));
        String description = body.containsKey("description") ? text(body.get("description")) : text(current.get("description"));
        int durationSeconds = body.containsKey("durationSeconds")
                ? boundedInt(body.get("durationSeconds"), 0, 24 * 60 * 60)
                : intValue(current.get("durationSeconds"), 0);
        boolean required = body.containsKey("required")
                ? booleanValue(body.get("required"), true)
                : booleanValue(current.get("required"), true);
        String resourceUrl = String.valueOf(current.get("resourceUrl"));
        if ("LINK".equals(current.get("resourceType")) && body.containsKey("url")) {
            resourceUrl = requiredText(body.get("url"), "请填写课程链接");
            if (!resourceUrl.toLowerCase(Locale.ROOT).startsWith("https://")) throw badRequest("外部链接仅支持 HTTPS");
        }
        jdbc.update("""
            UPDATE training_day_learning_resource
            SET title=?,description=?,duration_seconds=?,is_required=?,resource_url=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND training_day_id=? AND status<>'ARCHIVED'
            """, title, description, durationSeconds, required ? 1 : 0, resourceUrl, resourceId, dayId);
        return teacherResource(resourceId, dayId);
    }

    @Transactional
    public void archive(Long tenantId, Long userId, String role, Long dayId, Long resourceId) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        teacherResource(resourceId, dayId);
        jdbc.update("""
            UPDATE training_day_learning_resource
            SET status='ARCHIVED',updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND training_day_id=?
            """, resourceId, dayId);
    }

    @Transactional
    public List<Map<String, Object>> reorder(
            Long tenantId,
            Long userId,
            String role,
            Long dayId,
            List<Long> ids
    ) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        int order = 0;
        if (ids != null) {
            for (Long id : ids) {
                if (id == null) continue;
                jdbc.update("""
                    UPDATE training_day_learning_resource SET sort_order=?,updated_at=CURRENT_TIMESTAMP
                    WHERE id=? AND training_day_id=? AND status<>'ARCHIVED'
                    """, order++, id, dayId);
            }
        }
        return resources(dayId, false, null);
    }

    @Transactional
    public void activatePending(Long dayId) {
        Integer invalid = jdbc.queryForObject("""
            SELECT COUNT(*) FROM training_day_learning_resource
            WHERE training_day_id=? AND status='PENDING'
              AND (title IS NULL OR TRIM(title)='' OR resource_url IS NULL OR TRIM(resource_url)='')
            """, Integer.class, dayId);
        if (invalid != null && invalid > 0) throw badRequest("存在未完成的学习内容，暂不能发布");
        jdbc.update("""
            UPDATE training_day_learning_resource SET status='ACTIVE',updated_at=CURRENT_TIMESTAMP
            WHERE training_day_id=? AND status='PENDING'
            """, dayId);
    }

    public List<Map<String, Object>> studentResources(Long tenantId, Long userId, Long dayId) {
        assertStudentAccess(tenantId, userId, dayId, null);
        return resources(dayId, true, userId);
    }

    public Path authorizeDownload(
            Long tenantId,
            Long userId,
            String role,
            String requestedUrl
    ) {
        String resourceUrl = normalizeControlledResourceUrl(requestedUrl);
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT r.id, r.training_day_id dayId, r.status resourceStatus,
                   r.resource_url resourceUrl, d.camp_id campId,
                   d.training_date trainingDate, d.status,
                   d.early_unlocked_at earlyUnlockedAt
            FROM training_day_learning_resource r
            JOIN training_day d ON d.id = r.training_day_id
            JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
            WHERE r.resource_url = ? AND r.status <> 'ARCHIVED'
            LIMIT 1
            """, tenantId, resourceUrl);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习文件不存在");
        }

        Map<String, Object> resource = rows.get(0);
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        if ("STUDENT".equals(normalizedRole)) {
            if (!"ACTIVE".equals(String.valueOf(resource.get("resourceStatus")))) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习文件不存在");
            }
            Integer membership = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM project_team_member tm
                JOIN project_team pt ON pt.id = tm.team_id
                  AND pt.tenant_id = ? AND pt.status = 'ACTIVE'
                JOIN training_camp_team ct ON ct.team_id = pt.id
                  AND ct.camp_id = ? AND ct.status = 'ACTIVE'
                WHERE tm.user_id = ?
                """, Integer.class, tenantId, resource.get("campId"), userId);
            if (membership == null || membership == 0) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "已失去该营期访问权限");
            }
            Map<String, Object> availability = availabilityService.availability(resource);
            if (Boolean.TRUE.equals(availability.get("locked"))) {
                throw new ResponseStatusException(HttpStatus.LOCKED, "训练日尚未开放");
            }
        } else {
            assertFullCampTeacherAccess(
                    tenantId,
                    userId,
                    normalizedRole,
                    longValue(resource.get("campId"))
            );
        }

        Path controlledRoot = uploadRoot.resolve("training").resolve("learning").normalize();
        Path target = uploadRoot.resolve(resourceUrl.substring("/uploads/".length())).normalize();
        if (!target.startsWith(controlledRoot)) {
            throw badRequest("学习文件路径不合法");
        }
        if (!Files.isRegularFile(target)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习文件不存在");
        }
        return target;
    }

    public Map<Long, Map<String, Object>> summaries(Collection<Long> dayIds, Long userId) {
        Map<Long, Map<String, Object>> result = new LinkedHashMap<>();
        if (dayIds == null || dayIds.isEmpty()) return result;
        String placeholders = String.join(",", dayIds.stream().map(ignored -> "?").toList());
        List<Object> args = new ArrayList<>(dayIds);
        args.add(userId);
        List<Map<String, Object>> rows = jdbc.queryForList(("""
            SELECT r.training_day_id dayId,
                   COUNT(*) learningResourceCount,
                   SUM(CASE WHEN r.is_required=1 THEN 1 ELSE 0 END) requiredLearningCount,
                   CEIL(SUM(r.duration_seconds)/60.0) estimatedLearningMinutes,
                   SUM(CASE WHEN p.status='COMPLETED' THEN 1 ELSE 0 END) completedLearningCount
            FROM training_day_learning_resource r
            LEFT JOIN training_learning_progress p
              ON p.learning_resource_id=r.id AND p.user_id=?
            WHERE r.training_day_id IN (%s) AND r.status='ACTIVE'
            GROUP BY r.training_day_id
            """).formatted(placeholders), rotateLastToFirst(args).toArray());
        for (Map<String, Object> row : rows) {
            result.put(longValue(row.get("dayId")), new LinkedHashMap<>(row));
        }

        List<Object> resourceArgs = new ArrayList<>(dayIds);
        resourceArgs.add(userId);
        List<Map<String, Object>> resourceRows = jdbc.queryForList(("""
            SELECT r.id,
                   r.training_day_id dayId,
                   r.resource_type resourceType,
                   r.title,
                   r.duration_seconds durationSeconds,
                   r.is_required required,
                   COALESCE(p.status,'NOT_STARTED') learningStatus,
                   COALESCE(p.progress_percent,0) progressPercent
            FROM training_day_learning_resource r
            LEFT JOIN training_learning_progress p
              ON p.learning_resource_id=r.id AND p.user_id=?
            WHERE r.training_day_id IN (%s) AND r.status='ACTIVE'
            ORDER BY r.training_day_id,r.sort_order,r.id
            """).formatted(placeholders), rotateLastToFirst(resourceArgs).toArray());
        for (Map<String, Object> resource : resourceRows) {
            Long dayId = longValue(resource.get("dayId"));
            if (dayId == null) continue;
            Map<String, Object> summary = result.computeIfAbsent(dayId, ignored -> new LinkedHashMap<>());
            String resourceType = String.valueOf(resource.getOrDefault("resourceType", "")).toUpperCase(Locale.ROOT);
            String countKey = switch (resourceType) {
                case "VIDEO", "EMBED_VIDEO" -> "videoResourceCount";
                case "DOCUMENT" -> "documentResourceCount";
                case "LINK" -> "linkResourceCount";
                default -> null;
            };
            if (countKey != null) {
                summary.put(countKey, intValue(summary.get(countKey), 0) + 1);
            }
            summary.putIfAbsent("learningPreview", new LinkedHashMap<>(resource));
        }
        return result;
    }

    /**
     * 站外内嵌视频：按「页面可见 + 会话心跳」累计 actual_learning_seconds。
     * 完成阈值默认 complete_ratio（80%）× 老师设定的 duration_seconds。
     */
    @Transactional
    public Map<String, Object> recordEmbedHeartbeat(
            Long tenantId,
            Long userId,
            Long resourceId,
            String sessionId,
            boolean visible,
            boolean active,
            boolean reset
    ) {
        Map<String, Object> resource = assertStudentAccess(tenantId, userId, null, resourceId);
        if (!"EMBED_VIDEO".equals(String.valueOf(resource.get("resourceType")))) {
            throw badRequest("仅站外内嵌视频使用此进度上报");
        }
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw badRequest("学习会话无效");
        }
        Map<String, Object> full = studentResource(resourceId, userId);
        int targetDuration = Math.max(1, intValue(full.get("durationSeconds"), 0));
        double completeRatio = doubleValue(full.get("completeRatio"), DEFAULT_COMPLETE_RATIO);
        completeRatio = Math.max(0.5, Math.min(1.0, completeRatio));
        LocalDateTime now = LocalDateTime.now();

        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id,actual_learning_seconds actualLearningSeconds,progress_percent progressPercent,
                   heartbeat_session heartbeatSession,heartbeat_at heartbeatAt,status
            FROM training_learning_progress
            WHERE user_id=? AND learning_resource_id=?
            FOR UPDATE
            """, userId, resourceId);
        if (rows.isEmpty()) {
            // 13 列对齐：last_position=0, duration=?, session=?, position=NULL, heartbeat_at=?, status 字面量
            jdbc.update("""
                INSERT INTO training_learning_progress
                (user_id, learning_resource_id, learned_seconds, actual_learning_seconds, progress_percent,
                 watched_ranges_json, last_position_seconds, video_duration_seconds,
                 heartbeat_session, heartbeat_position_seconds, heartbeat_at, status, last_learned_at)
                VALUES (?, ?, 0, 0, 0, '[]', 0, ?, ?, NULL, ?, 'NOT_STARTED', CURRENT_TIMESTAMP)
                """, userId, resourceId, targetDuration, sessionId, now);
            return studentResource(resourceId, userId);
        }

        Map<String, Object> current = rows.get(0);
        int actualSeconds = intValue(current.get("actualLearningSeconds"), 0);
        boolean alreadyCompleted = "COMPLETED".equals(String.valueOf(current.get("status")));
        boolean sameSession = sessionId.equals(String.valueOf(current.get("heartbeatSession")));
        LocalDateTime previousHeartbeat = localDateTime(current.get("heartbeatAt"));

        if (!reset && visible && active && sameSession && previousHeartbeat != null) {
            double elapsedSeconds = Duration.between(previousHeartbeat, now).toMillis() / 1000.0;
            // 单次心跳最多 +20s，间隔过长不计（切后台回来）
            if (elapsedSeconds >= 0.5 && elapsedSeconds <= 25) {
                actualSeconds += Math.max(1, Math.min(20, (int) Math.round(elapsedSeconds)));
            }
        }

        int progress = Math.min(100, (int) Math.floor(actualSeconds * 100.0 / targetDuration));
        boolean completed = alreadyCompleted || progress >= Math.ceil(completeRatio * 100);
        if (completed) progress = 100;
        String status = completed
                ? "COMPLETED"
                : actualSeconds > 0 ? "IN_PROGRESS" : "NOT_STARTED";

        jdbc.update("""
            UPDATE training_learning_progress
            SET learned_seconds=?,actual_learning_seconds=?,progress_percent=?,
                video_duration_seconds=?,
                heartbeat_session=?,heartbeat_at=?,
                status=?,last_learned_at=CURRENT_TIMESTAMP,
                completed_at=CASE WHEN ?='COMPLETED' THEN COALESCE(completed_at,CURRENT_TIMESTAMP) ELSE completed_at END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """, actualSeconds, actualSeconds, progress,
                targetDuration,
                sessionId, now,
                status, status, current.get("id"));
        return studentResource(resourceId, userId);
    }

    @Transactional
    public Map<String, Object> recordVideoHeartbeat(
            Long tenantId,
            Long userId,
            Long resourceId,
            String sessionId,
            int positionSeconds,
            int durationSeconds,
            boolean reset
    ) {
        Map<String, Object> resource = assertStudentAccess(tenantId, userId, null, resourceId);
        String type = String.valueOf(resource.get("resourceType"));
        if ("EMBED_VIDEO".equals(type)) {
            throw badRequest("站外内嵌视频请使用 embed 进度上报");
        }
        if (!"VIDEO".equals(type)) {
            throw badRequest("只有视频学习内容需要记录播放心跳");
        }
        if (sessionId == null || !sessionId.matches("[A-Za-z0-9_-]{8,64}")) {
            throw badRequest("播放会话无效");
        }
        int safeDuration = Math.max(1, Math.min(24 * 60 * 60, durationSeconds));
        int safePosition = Math.max(0, Math.min(safeDuration, positionSeconds));
        LocalDateTime now = LocalDateTime.now();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id,actual_learning_seconds actualLearningSeconds,progress_percent progressPercent,
                   watched_ranges_json watchedRangesJson,last_position_seconds lastPositionSeconds,
                   video_duration_seconds videoDurationSeconds,heartbeat_session heartbeatSession,
                   heartbeat_position_seconds heartbeatPositionSeconds,heartbeat_at heartbeatAt,status
            FROM training_learning_progress
            WHERE user_id=? AND learning_resource_id=?
            FOR UPDATE
            """, userId, resourceId);
        if (rows.isEmpty()) {
            jdbc.update("""
                INSERT INTO training_learning_progress
                (user_id,learning_resource_id,learned_seconds,actual_learning_seconds,progress_percent,
                 watched_ranges_json,last_position_seconds,video_duration_seconds,
                 heartbeat_session,heartbeat_position_seconds,heartbeat_at,status,last_learned_at)
                VALUES (?,?,0,0,0,'[]',?,?,?, ?,?,'NOT_STARTED',CURRENT_TIMESTAMP)
                """, userId, resourceId, safePosition, safeDuration, sessionId, safePosition, now);
            updateResourceDurationIfMissing(resourceId, safeDuration);
            return studentResource(resourceId, userId);
        }

        Map<String, Object> current = rows.get(0);
        int storedDuration = intValue(current.get("videoDurationSeconds"), 0);
        if (storedDuration <= 0) storedDuration = safeDuration;
        safePosition = Math.min(storedDuration, safePosition);
        List<List<Integer>> ranges = readRanges(current.get("watchedRangesJson"));
        int actualSeconds = intValue(current.get("actualLearningSeconds"), 0);
        boolean sameSession = sessionId.equals(String.valueOf(current.get("heartbeatSession")));
        Integer previousPosition = nullableInt(current.get("heartbeatPositionSeconds"));
        LocalDateTime previousHeartbeat = localDateTime(current.get("heartbeatAt"));

        if (!reset && sameSession && previousPosition != null && previousHeartbeat != null) {
            double elapsedSeconds = Duration.between(previousHeartbeat, now).toMillis() / 1000.0;
            int mediaAdvance = safePosition - previousPosition;
            boolean continuousPlayback = isContinuousPlayback(elapsedSeconds, mediaAdvance);
            if (continuousPlayback) {
                ranges = mergeWatchedRanges(ranges, previousPosition, safePosition);
                actualSeconds += Math.max(1, Math.min(30, (int) Math.round(elapsedSeconds)));
            }
        }

        int coveredSeconds = watchedCoverageSeconds(ranges);
        int progress = Math.min(100, (int) Math.floor(coveredSeconds * 100.0 / storedDuration));
        boolean completed = coveredSeconds >= Math.ceil(storedDuration * 0.9);
        boolean alreadyCompleted = "COMPLETED".equals(String.valueOf(current.get("status")));
        String status = completed || alreadyCompleted
                ? "COMPLETED"
                : coveredSeconds > 0 ? "IN_PROGRESS" : "NOT_STARTED";
        String rangesJson = writeRanges(ranges);

        jdbc.update("""
            UPDATE training_learning_progress
            SET learned_seconds=?,actual_learning_seconds=?,progress_percent=?,watched_ranges_json=?,
                last_position_seconds=?,video_duration_seconds=?,
                heartbeat_session=?,heartbeat_position_seconds=?,heartbeat_at=?,
                status=?,last_learned_at=CURRENT_TIMESTAMP,
                completed_at=CASE WHEN ?='COMPLETED' THEN COALESCE(completed_at,CURRENT_TIMESTAMP) ELSE completed_at END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """, actualSeconds, actualSeconds, progress, rangesJson,
                safePosition, storedDuration,
                sessionId, safePosition, now,
                status, status, current.get("id"));
        updateResourceDurationIfMissing(resourceId, storedDuration);
        return studentResource(resourceId, userId);
    }

    @Transactional
    public Map<String, Object> completeNonVideo(Long tenantId, Long userId, Long resourceId) {
        Map<String, Object> resource = assertStudentAccess(tenantId, userId, null, resourceId);
        String type = String.valueOf(resource.get("resourceType"));
        if ("VIDEO".equals(type)) {
            throw badRequest("视频需按实际连续播放进度完成");
        }
        if ("EMBED_VIDEO".equals(type)) {
            throw badRequest("站外视频需在平台内学习达到预计时长的完成比例后自动完成");
        }
        jdbc.update("""
            INSERT INTO training_learning_progress
            (user_id,learning_resource_id,learned_seconds,actual_learning_seconds,progress_percent,
             watched_ranges_json,last_position_seconds,video_duration_seconds,status,last_learned_at,completed_at)
            VALUES (?,?,0,0,100,'[]',0,0,'COMPLETED',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            ON DUPLICATE KEY UPDATE
              progress_percent=100,status='COMPLETED',last_learned_at=CURRENT_TIMESTAMP,
              completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP),updated_at=CURRENT_TIMESTAMP
            """, userId, resourceId);
        return studentResource(resourceId, userId);
    }

    static List<List<Integer>> mergeWatchedRanges(List<List<Integer>> current, int start, int end) {
        List<List<Integer>> ranges = new ArrayList<>();
        if (current != null) {
            for (List<Integer> range : current) {
                if (range == null || range.size() < 2) continue;
                int safeStart = Math.max(0, range.get(0));
                int safeEnd = Math.max(safeStart, range.get(1));
                if (safeEnd > safeStart) ranges.add(new ArrayList<>(List.of(safeStart, safeEnd)));
            }
        }
        if (end > start) ranges.add(new ArrayList<>(List.of(Math.max(0, start), Math.max(0, end))));
        ranges.sort(Comparator.comparingInt(range -> range.get(0)));
        List<List<Integer>> merged = new ArrayList<>();
        for (List<Integer> range : ranges) {
            if (merged.isEmpty()) {
                merged.add(range);
                continue;
            }
            List<Integer> tail = merged.get(merged.size() - 1);
            if (range.get(0) <= tail.get(1) + 1) {
                tail.set(1, Math.max(tail.get(1), range.get(1)));
            } else {
                merged.add(range);
            }
        }
        return merged;
    }

    static int watchedCoverageSeconds(List<List<Integer>> ranges) {
        if (ranges == null) return 0;
        return ranges.stream()
                .filter(range -> range != null && range.size() >= 2)
                .mapToInt(range -> Math.max(0, range.get(1) - range.get(0)))
                .sum();
    }

    static int furthestWatchedSecond(List<List<Integer>> ranges) {
        if (ranges == null) return 0;
        return ranges.stream()
                .filter(range -> range != null && range.size() >= 2)
                .mapToInt(range -> Math.max(0, range.get(1)))
                .max()
                .orElse(0);
    }

    static boolean isContinuousPlayback(double elapsedSeconds, int mediaAdvance) {
        if (elapsedSeconds < 0.25 || elapsedSeconds > 30 || mediaAdvance <= 0) return false;
        int maximumContinuousAdvance = (int) Math.ceil(elapsedSeconds * 2.05 + 1);
        return mediaAdvance <= maximumContinuousAdvance;
    }

    private List<List<Integer>> readRanges(Object value) {
        if (value == null || String.valueOf(value).isBlank()) return new ArrayList<>();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
        } catch (Exception ignored) {
            return new ArrayList<>();
        }
    }

    private String writeRanges(List<List<Integer>> ranges) {
        try {
            return objectMapper.writeValueAsString(ranges);
        } catch (Exception exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "学习进度保存失败");
        }
    }

    private void updateResourceDurationIfMissing(Long resourceId, int durationSeconds) {
        jdbc.update("""
            UPDATE training_day_learning_resource
            SET duration_seconds=CASE WHEN duration_seconds=0 THEN ? ELSE duration_seconds END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """, durationSeconds, resourceId);
    }

    private Map<String, Object> assertStudentAccess(
            Long tenantId,
            Long userId,
            Long dayId,
            Long resourceId
    ) {
        Object id = resourceId == null ? dayId : resourceId;
        String resourceSelect = resourceId == null
                ? "SELECT d.id dayId,d.training_date trainingDate,d.status,d.early_unlocked_at earlyUnlockedAt "
                    + "FROM training_day d "
                : "SELECT r.id,r.training_day_id dayId,r.resource_type resourceType,"
                    + "d.training_date trainingDate,d.status,d.early_unlocked_at earlyUnlockedAt "
                    + "FROM training_day_learning_resource r "
                    + "JOIN training_day d ON d.id=r.training_day_id ";
        String filter = resourceId == null
                ? "d.id=?"
                : "r.id=? AND r.status='ACTIVE'";
        List<Map<String, Object>> rows = jdbc.queryForList((resourceSelect + """
            JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
            JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
            JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
            JOIN project_team_member tm ON tm.team_id=pt.id AND tm.user_id=?
            WHERE %s
            LIMIT 1
            """).formatted(filter), tenantId, userId, id);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习内容不存在");
        Map<String, Object> resource = rows.get(0);
        Map<String, Object> availability = availabilityService.availability(resource);
        if (Boolean.TRUE.equals(availability.get("locked"))) {
            throw new ResponseStatusException(HttpStatus.LOCKED, String.valueOf(availability.get("lockReason")));
        }
        return resource;
    }

    private String normalizeControlledResourceUrl(String requestedUrl) {
        if (requestedUrl == null || requestedUrl.indexOf('\0') >= 0 || requestedUrl.indexOf('\\') >= 0) {
            throw badRequest("学习文件路径不合法");
        }
        String decoded;
        try {
            decoded = URLDecoder.decode(requestedUrl, StandardCharsets.UTF_8);
        } catch (IllegalArgumentException exception) {
            throw badRequest("学习文件路径不合法");
        }
        if (!decoded.matches("^/uploads/training/learning/[0-9]+/(video|document)/[A-Za-z0-9][A-Za-z0-9._-]*$")) {
            throw badRequest("学习文件路径不合法");
        }
        return decoded;
    }

    private void assertFullCampTeacherAccess(
            Long tenantId,
            Long userId,
            String role,
            Long campId
    ) {
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(role)) return;
        if (!"TEACHER".equals(role)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问学习文件");
        }
        List<Long> activeTeamIds = jdbc.queryForList("""
            SELECT ct.team_id
            FROM training_camp_team ct
            JOIN project_team pt ON pt.id = ct.team_id AND pt.tenant_id = ?
            WHERE ct.camp_id = ? AND ct.status = 'ACTIVE'
            ORDER BY ct.team_id
            """, Long.class, tenantId, campId);
        List<Long> accessibleTeamIds = jdbc.queryForList("""
            SELECT DISTINCT pt.id
            FROM project_team pt
            JOIN training_camp_team ct ON ct.team_id = pt.id
              AND ct.camp_id = ? AND ct.status = 'ACTIVE'
            LEFT JOIN project_team_member mentor ON mentor.team_id = pt.id
              AND mentor.user_id = ? AND mentor.role_in_team = 'MENTOR'
            WHERE pt.tenant_id = ? AND pt.status = 'ACTIVE'
              AND (pt.mentor_id = ? OR mentor.user_id IS NOT NULL)
            ORDER BY pt.id
            """, Long.class, campId, userId, tenantId, userId);
        if (activeTeamIds.isEmpty() || !accessibleTeamIds.containsAll(activeTeamIds)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未覆盖该营期全部团队");
        }
    }

    private void assertTeacherWriteAccess(Long tenantId, Long userId, String role, Long dayId) {
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT d.camp_id campId
            FROM training_day d
            JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
            WHERE d.id=?
            """, tenantId, dayId);
        if (days.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        }
        assertFullCampTeacherAccess(
                tenantId,
                userId,
                normalizedRole,
                longValue(days.get(0).get("campId"))
        );
    }

    private void assertTeacherReadAccess(Long tenantId, Long userId, String role, Long dayId) {
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        boolean administrator = Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole);
        Integer count = administrator
                ? jdbc.queryForObject("""
                    SELECT COUNT(DISTINCT pt.id) FROM training_day d
                    JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
                    JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                    JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
                    WHERE d.id=?
                    """, Integer.class, tenantId, dayId)
                : jdbc.queryForObject("""
                    SELECT COUNT(DISTINCT pt.id) FROM training_day d
                    JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
                    JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                    JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
                    WHERE d.id=? AND (pt.mentor_id=? OR EXISTS (
                      SELECT 1 FROM project_team_member tm
                      WHERE tm.team_id=pt.id AND tm.user_id=? AND tm.role_in_team='MENTOR'
                    ))
                    """, Integer.class, tenantId, dayId, userId, userId);
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权查看该训练日");
        }
    }

    private List<Map<String, Object>> resources(Long dayId, boolean activeOnly, Long userId) {
        String progressSelect = userId == null
                ? "'NOT_STARTED' learningStatus,0 learnedSeconds,0 actualLearningSeconds,"
                    + "0 progressPercent,0 lastPositionSeconds,0 videoDurationSeconds,"
                    + "NULL watchedRangesJson,NULL completedAt"
                : "COALESCE(p.status,'NOT_STARTED') learningStatus,COALESCE(p.learned_seconds,0) learnedSeconds,"
                    + "COALESCE(p.actual_learning_seconds,0) actualLearningSeconds,"
                    + "COALESCE(p.progress_percent,0) progressPercent,"
                    + "COALESCE(p.last_position_seconds,0) lastPositionSeconds,"
                    + "COALESCE(p.video_duration_seconds,0) videoDurationSeconds,"
                    + "p.watched_ranges_json watchedRangesJson,p.completed_at completedAt";
        String progressJoin = userId == null ? "" : " LEFT JOIN training_learning_progress p ON p.learning_resource_id=r.id AND p.user_id=" + userId;
        String status = activeOnly ? "r.status='ACTIVE'" : "r.status<>'ARCHIVED'";
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT r.id,r.training_day_id dayId,r.resource_type resourceType,r.title,r.description,
                   r.resource_url resourceUrl,r.file_name fileName,r.file_size fileSize,r.mime_type mimeType,
                   r.duration_seconds durationSeconds,r.is_required required,r.sort_order sortOrder,r.status,
                   r.provider,r.provider_video_id providerVideoId,r.embed_url embedUrl,r.cover_url coverUrl,
                   COALESCE(r.complete_ratio,0.80) completeRatio,
                   %s
            FROM training_day_learning_resource r
            %s
            WHERE r.training_day_id=? AND %s
            ORDER BY r.sort_order ASC,r.id ASC
            """.formatted(progressSelect, progressJoin, status), dayId);
        rows.forEach(this::addWatchedBoundary);
        return rows;
    }

    private Map<String, Object> teacherResource(Long resourceId, Long dayId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id,training_day_id dayId,resource_type resourceType,title,description,
                   resource_url resourceUrl,file_name fileName,file_size fileSize,mime_type mimeType,
                   duration_seconds durationSeconds,is_required required,sort_order sortOrder,status,
                   provider,provider_video_id providerVideoId,embed_url embedUrl,cover_url coverUrl,
                   COALESCE(complete_ratio,0.80) completeRatio
            FROM training_day_learning_resource
            WHERE id=? AND training_day_id=? AND status<>'ARCHIVED'
            """, resourceId, dayId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习内容不存在");
        return rows.get(0);
    }

    private Map<String, Object> studentResource(Long resourceId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT r.id,r.training_day_id dayId,r.resource_type resourceType,r.title,r.description,
                   r.resource_url resourceUrl,r.file_name fileName,r.file_size fileSize,r.mime_type mimeType,
                   r.duration_seconds durationSeconds,r.is_required required,r.sort_order sortOrder,
                   r.provider,r.provider_video_id providerVideoId,r.embed_url embedUrl,r.cover_url coverUrl,
                   COALESCE(r.complete_ratio,0.80) completeRatio,
                   COALESCE(p.status,'NOT_STARTED') learningStatus,
                   COALESCE(p.learned_seconds,0) learnedSeconds,
                   COALESCE(p.actual_learning_seconds,0) actualLearningSeconds,
                   COALESCE(p.progress_percent,0) progressPercent,
                   COALESCE(p.last_position_seconds,0) lastPositionSeconds,
                   COALESCE(p.video_duration_seconds,0) videoDurationSeconds,
                   p.watched_ranges_json watchedRangesJson,
                   p.completed_at completedAt
            FROM training_day_learning_resource r
            LEFT JOIN training_learning_progress p ON p.learning_resource_id=r.id AND p.user_id=?
            WHERE r.id=? AND r.status='ACTIVE'
            """, userId, resourceId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "学习内容不存在");
        Map<String, Object> resource = rows.get(0);
        addWatchedBoundary(resource);
        return resource;
    }

    private void addWatchedBoundary(Map<String, Object> resource) {
        Object rangesJson = resource.remove("watchedRangesJson");
        resource.put("maxWatchedPositionSeconds", furthestWatchedSecond(readRanges(rangesJson)));
    }

    private Long insertResource(
            Long dayId,
            String resourceType,
            String title,
            String description,
            String resourceUrl,
            String fileName,
            long fileSize,
            String mimeType,
            int durationSeconds,
            boolean required,
            int sortOrder,
            Long userId
    ) {
        if (!RESOURCE_TYPES.contains(resourceType)) throw badRequest("不支持的学习内容类型");
        KeyHolder keys = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement("""
                INSERT INTO training_day_learning_resource
                (training_day_id,resource_type,title,description,resource_url,file_name,file_size,mime_type,
                 duration_seconds,is_required,sort_order,status,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,'PENDING',?)
                """, Statement.RETURN_GENERATED_KEYS);
            statement.setLong(1, dayId);
            statement.setString(2, resourceType);
            statement.setString(3, title);
            statement.setString(4, description);
            statement.setString(5, resourceUrl);
            statement.setString(6, fileName);
            statement.setLong(7, fileSize);
            statement.setString(8, mimeType);
            statement.setInt(9, durationSeconds);
            statement.setInt(10, required ? 1 : 0);
            statement.setInt(11, sortOrder);
            statement.setLong(12, userId);
            return statement;
        }, keys);
        Number key = keys.getKey();
        if (key == null) throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "学习内容创建失败");
        return key.longValue();
    }

    private int nextSortOrder(Long dayId) {
        Integer value = jdbc.queryForObject("""
            SELECT COALESCE(MAX(sort_order),-1)+1 FROM training_day_learning_resource
            WHERE training_day_id=? AND status<>'ARCHIVED'
            """, Integer.class, dayId);
        return value == null ? 0 : value;
    }

    private List<Object> rotateLastToFirst(List<Object> values) {
        if (values.isEmpty()) return values;
        List<Object> result = new ArrayList<>();
        result.add(values.get(values.size() - 1));
        result.addAll(values.subList(0, values.size() - 1));
        return result;
    }

    String classifyResourceType(String extension) {
        if (VIDEO_EXTENSIONS.contains(extension)) return "VIDEO";
        if (DOCUMENT_EXTENSIONS.contains(extension)) return "DOCUMENT";
        return null;
    }

    void validateFileSignature(MultipartFile file, String extension) {
        byte[] header = new byte[8192];
        int read;
        try (InputStream input = file.getInputStream()) {
            read = input.read(header);
        } catch (IOException exception) {
            throw badRequest("文件读取失败");
        }
        boolean valid = switch (extension) {
            case "pdf" -> read >= 4 && header[0] == '%' && header[1] == 'P' && header[2] == 'D' && header[3] == 'F';
            case "docx", "pptx", "xlsx" -> isZip(header, read) && validateOoxmlPackage(file, extension);
            case "zip" -> isZip(header, read);
            case "ppt", "doc", "xls" -> isOle(header, read);
            case "mp4", "mov", "m4a" -> read >= 8 && header[4] == 'f' && header[5] == 't'
                    && header[6] == 'y' && header[7] == 'p';
            case "webm" -> read >= 4 && (header[0] & 0xff) == 0x1a && (header[1] & 0xff) == 0x45
                    && (header[2] & 0xff) == 0xdf && (header[3] & 0xff) == 0xa3;
            case "mp3" -> isMp3(header, read);
            case "wav" -> read >= 12 && ascii(header, 0, "RIFF") && ascii(header, 8, "WAVE");
            case "jpg", "jpeg" -> read >= 3 && (header[0] & 0xff) == 0xff
                    && (header[1] & 0xff) == 0xd8 && (header[2] & 0xff) == 0xff;
            case "png" -> read >= 8 && (header[0] & 0xff) == 0x89 && ascii(header, 1, "PNG")
                    && (header[4] & 0xff) == 0x0d && (header[5] & 0xff) == 0x0a
                    && (header[6] & 0xff) == 0x1a && (header[7] & 0xff) == 0x0a;
            case "gif" -> read >= 6 && (ascii(header, 0, "GIF87a") || ascii(header, 0, "GIF89a"));
            case "webp" -> read >= 12 && ascii(header, 0, "RIFF") && ascii(header, 8, "WEBP");
            case "rar" -> read >= 7 && ascii(header, 0, "Rar!")
                    && (header[4] & 0xff) == 0x1a && (header[5] & 0xff) == 0x07
                    && ((header[6] & 0xff) == 0x00 || (header[6] & 0xff) == 0x01);
            case "7z" -> read >= 6 && (header[0] & 0xff) == 0x37 && (header[1] & 0xff) == 0x7a
                    && (header[2] & 0xff) == 0xbc && (header[3] & 0xff) == 0xaf
                    && (header[4] & 0xff) == 0x27 && (header[5] & 0xff) == 0x1c;
            case "csv", "txt", "md" -> looksLikeText(header, read);
            default -> false;
        };
        if (!valid) throw badRequest("文件内容与扩展名不匹配，请检查后重新上传");
    }

    String safeMime(String extension) {
        return switch (extension) {
            case "mp4" -> "video/mp4";
            case "webm" -> "video/webm";
            case "mov" -> "video/quicktime";
            case "mp3" -> "audio/mpeg";
            case "wav" -> "audio/wav";
            case "m4a" -> "audio/mp4";
            case "pdf" -> "application/pdf";
            case "ppt" -> "application/vnd.ms-powerpoint";
            case "pptx" -> "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            case "doc" -> "application/msword";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xls" -> "application/vnd.ms-excel";
            case "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "csv" -> "text/csv";
            case "txt" -> "text/plain";
            case "md" -> "text/markdown";
            case "jpg", "jpeg" -> "image/jpeg";
            case "png" -> "image/png";
            case "gif" -> "image/gif";
            case "webp" -> "image/webp";
            case "zip" -> "application/zip";
            case "rar" -> "application/vnd.rar";
            case "7z" -> "application/x-7z-compressed";
            default -> "application/octet-stream";
        };
    }

    private boolean validateOoxmlPackage(MultipartFile file, String extension) {
        String requiredPrefix = switch (extension) {
            case "docx" -> "word/";
            case "pptx" -> "ppt/";
            case "xlsx" -> "xl/";
            default -> "";
        };
        boolean hasContentTypes = false;
        boolean hasRequiredPrefix = false;
        int entryCount = 0;
        int totalNameLength = 0;
        try (ZipInputStream zip = new ZipInputStream(file.getInputStream())) {
            ZipEntry entry;
            while ((entry = zip.getNextEntry()) != null) {
                if (++entryCount > 512) return false;
                String name = entry.getName().replace('\\', '/');
                totalNameLength += name.length();
                if (totalNameLength > 64 * 1024) return false;
                if ("[Content_Types].xml".equals(name)) hasContentTypes = true;
                if (name.startsWith(requiredPrefix)) hasRequiredPrefix = true;
                if (hasContentTypes && hasRequiredPrefix) return true;
            }
        } catch (IOException exception) {
            return false;
        }
        return false;
    }

    private boolean isZip(byte[] header, int read) {
        return read >= 4 && header[0] == 'P' && header[1] == 'K'
                && ((header[2] == 3 && header[3] == 4)
                || (header[2] == 5 && header[3] == 6)
                || (header[2] == 7 && header[3] == 8));
    }

    private boolean isOle(byte[] header, int read) {
        return read >= 8 && (header[0] & 0xff) == 0xd0 && (header[1] & 0xff) == 0xcf
                && (header[2] & 0xff) == 0x11 && (header[3] & 0xff) == 0xe0
                && (header[4] & 0xff) == 0xa1 && (header[5] & 0xff) == 0xb1
                && (header[6] & 0xff) == 0x1a && (header[7] & 0xff) == 0xe1;
    }

    private boolean isMp3(byte[] header, int read) {
        if (read >= 3 && ascii(header, 0, "ID3")) return true;
        return read >= 2 && (header[0] & 0xff) == 0xff && ((header[1] & 0xe0) == 0xe0);
    }

    private boolean looksLikeText(byte[] bytes, int read) {
        if (read <= 0) return false;
        int suspiciousControls = 0;
        for (int index = 0; index < read; index++) {
            int value = bytes[index] & 0xff;
            if (value == 0) return false;
            if (value < 0x20 && value != '\t' && value != '\n' && value != '\r' && value != '\f') {
                suspiciousControls++;
            }
        }
        return suspiciousControls * 100 <= read * 2;
    }

    private boolean ascii(byte[] bytes, int offset, String expected) {
        if (offset < 0 || offset + expected.length() > bytes.length) return false;
        for (int index = 0; index < expected.length(); index++) {
            if ((bytes[offset + index] & 0xff) != expected.charAt(index)) return false;
        }
        return true;
    }

    private String safeDisplayName(String value) {
        String name = value == null ? "学习内容" : Paths.get(value).getFileName().toString().trim();
        if (name.isBlank()) name = "学习内容";
        return name.length() > 255 ? name.substring(name.length() - 255) : name;
    }

    private String stripExtension(String value) {
        int index = value.lastIndexOf('.');
        return index <= 0 ? value : value.substring(0, index);
    }

    private String extension(String value) {
        int index = value.lastIndexOf('.');
        return index < 0 ? "" : value.substring(index + 1).toLowerCase(Locale.ROOT);
    }

    private String requiredText(Object value, String message) {
        String result = text(value);
        if (result == null) throw badRequest(message);
        return result;
    }

    private String text(Object value) {
        if (value == null) return null;
        String result = String.valueOf(value).trim();
        return result.isBlank() ? null : result;
    }

    private boolean booleanValue(Object value, boolean fallback) {
        if (value == null) return fallback;
        if (value instanceof Boolean bool) return bool;
        if (value instanceof Number number) return number.intValue() != 0;
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private int boundedInt(Object value, int min, int max) {
        int result = intValue(value, min);
        if (result < min || result > max) throw badRequest("数值超出允许范围");
        return result;
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) return number.intValue();
        if (value == null) return fallback;
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    private double doubleValue(Object value, double fallback) {
        if (value instanceof Number number) return number.doubleValue();
        if (value == null) return fallback;
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return fallback;
        }
    }

    /**
     * 解析站外视频。当前主支持 bilibili（BV/av/短链域名）。
     * 返回 null 表示无法识别。
     */
    Map<String, Object> parseExternalVideo(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String input = raw.trim();
        // 纯 BV 号
        if (input.matches("(?i)^BV[0-9A-Za-z]+$")) {
            String bvid = normalizeBvid(input);
            return bilibiliEmbed("https://www.bilibili.com/video/" + bvid, bvid);
        }
        String url = input;
        if (!url.matches("(?i)^https?://.*")) {
            return null;
        }
        String lower = url.toLowerCase(Locale.ROOT);
        if (lower.contains("bilibili.com") || lower.contains("b23.tv")) {
            String bvid = extractBilibiliBvid(url);
            if (bvid == null) return null;
            String canonical = "https://www.bilibili.com/video/" + bvid;
            return bilibiliEmbed(canonical, bvid);
        }
        return null;
    }

    private Map<String, Object> bilibiliEmbed(String originalUrl, String bvid) {
        String id = normalizeBvid(bvid);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("canEmbed", true);
        result.put("provider", "BILIBILI");
        result.put("providerLabel", "B站");
        result.put("providerVideoId", id);
        result.put("originalUrl", originalUrl);
        result.put("embedUrl", "https://player.bilibili.com/player.html?bvid=" + id
                + "&page=1&high_quality=1&danmaku=0&autoplay=0");
        result.put("coverUrl", null);
        result.put("title", "B站视频 " + id);
        return result;
    }

    private String extractBilibiliBvid(String url) {
        java.util.regex.Matcher m = java.util.regex.Pattern
                .compile("(?i)(BV[0-9A-Za-z]+)")
                .matcher(url);
        if (m.find()) return normalizeBvid(m.group(1));
        // av 号：无法稳定转 BV 时暂不支持内嵌
        return null;
    }

    private String normalizeBvid(String bvid) {
        if (bvid == null) return null;
        String s = bvid.trim();
        if (s.regionMatches(true, 0, "BV", 0, 2)) {
            return "BV" + s.substring(2);
        }
        return s;
    }

    private Integer nullableInt(Object value) {
        if (value instanceof Number number) return number.intValue();
        if (value == null) return null;
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private LocalDateTime localDateTime(Object value) {
        if (value instanceof LocalDateTime dateTime) return dateTime;
        if (value instanceof java.sql.Timestamp timestamp) return timestamp.toLocalDateTime();
        return null;
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        if (value == null) return null;
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private ResponseStatusException badRequest(String message) {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
    }
}
