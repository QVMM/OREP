package com.orep.backend.service;

import com.orep.backend.entity.Resource;
import com.orep.backend.mapper.ResourceMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

@Service
public class ResourceCenterService {
    public static final String ROOT_FOLDER = "root";
    private static final Set<String> ADMIN_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN");
    private static final Set<String> ALLOWED_EXTENSIONS = Set.of(
            "pdf", "doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx",
            "sdoc",
            "png", "jpg", "jpeg", "gif", "webp", "svg",
            "mp4", "webm", "mov", "mkv", "avi",
            "mp3", "wav", "m4a", "aac", "ogg",
            "txt", "md"
    );
    private static final List<Map<String, Object>> SYSTEM_FOLDERS = List.of(
            folderDefinition("competition", "赛项文件", "competition"),
            folderDefinition("team", "团队项目材料", "team"),
            folderDefinition("research", "调研资料", "research"),
            folderDefinition("proof", "成果证明", "proof"),
            folderDefinition("content", "PPT / 讲稿素材", "content")
    );

    private final ResourceMapper resourceMapper;
    private final org.springframework.jdbc.core.JdbcTemplate jdbc;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    public ResourceCenterService(
            ResourceMapper resourceMapper,
            org.springframework.jdbc.core.JdbcTemplate jdbc
    ) {
        this.resourceMapper = resourceMapper;
        this.jdbc = jdbc;
    }

    public Map<String, Object> workspace(
            Long teamId,
            Long tenantId,
            Long userId,
            String role
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        List<Map<String, Object>> teamFiles = resourceMapper.findByTeamId(teamId).stream()
                .map(resource -> fileView(resource, false))
                .toList();
        List<Map<String, Object>> publicFiles = resourceMapper.findPublic().stream()
                .map(resource -> fileView(resource, true))
                .toList();

        List<Map<String, Object>> folders = new ArrayList<>();
        for (Map<String, Object> definition : SYSTEM_FOLDERS) {
            folders.add(folderView(definition, teamFiles));
        }
        for (Map<String, Object> row : customFolders(teamId)) {
            folders.add(folderView(row, teamFiles));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teamId", teamId);
        result.put("folders", folders);
        result.put("teamFiles", teamFiles);
        result.put("publicFiles", publicFiles);
        result.put("rootFolderKey", ROOT_FOLDER);
        result.put("permissions", Map.of("canManage", true));
        return result;
    }

    @Transactional
    public Map<String, Object> createFolder(
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            String label
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        String cleanLabel = cleanFolderLabel(label);
        Integer duplicateCount = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM resource_category
                WHERE team_id = ? AND LOWER(label) = LOWER(?)
                """, Integer.class, teamId, cleanLabel);
        if (duplicateCount != null && duplicateCount > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "当前团队已存在同名文件夹");
        }
        if (SYSTEM_FOLDERS.stream().anyMatch(folder ->
                cleanLabel.equalsIgnoreCase(String.valueOf(folder.get("label"))))) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "当前团队已存在同名文件夹");
        }
        String key = "folder_" + UUID.randomUUID().toString().replace("-", "");
        jdbc.update("""
                INSERT INTO resource_category(team_id, category_key, label, created_by)
                VALUES (?, ?, ?, ?)
                """, teamId, key, cleanLabel, userId);
        Map<String, Object> row = jdbc.queryForMap("""
                SELECT id, category_key AS `key`, label, created_at AS createdAt,
                       updated_at AS updatedAt
                FROM resource_category
                WHERE team_id = ? AND category_key = ?
                """, teamId, key);
        row.put("system", false);
        row.put("tone", "custom");
        row.put("count", 0);
        row.put("covers", List.of());
        return row;
    }

    @Transactional
    public Map<String, Object> renameFolder(
            Long folderId,
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            String label
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        String cleanLabel = cleanFolderLabel(label);
        Integer duplicateCount = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM resource_category
                WHERE team_id = ? AND id <> ? AND LOWER(label) = LOWER(?)
                """, Integer.class, teamId, folderId, cleanLabel);
        if (duplicateCount != null && duplicateCount > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "当前团队已存在同名文件夹");
        }
        int affected = jdbc.update("""
                UPDATE resource_category
                SET label = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND team_id = ?
                """, cleanLabel, folderId, teamId);
        if (affected == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件夹不存在");
        }
        return Map.of("id", folderId, "label", cleanLabel);
    }

    @Transactional
    public void deleteFolder(
            Long folderId,
            Long teamId,
            Long tenantId,
            Long userId,
            String role
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT category_key AS `key`
                FROM resource_category
                WHERE id = ? AND team_id = ?
                """, folderId, teamId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件夹不存在");
        }
        String key = String.valueOf(rows.get(0).get("key"));
        Integer fileCount = jdbc.queryForObject("""
                SELECT COUNT(*) FROM resource WHERE team_id = ? AND category = ?
                """, Integer.class, teamId, key);
        if (fileCount != null && fileCount > 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "请先移出文件夹内的资料");
        }
        jdbc.update("DELETE FROM resource_category WHERE id = ? AND team_id = ?", folderId, teamId);
    }

    @Transactional
    public Map<String, Object> moveFile(
            Integer resourceId,
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            String folderKey
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        Resource resource = requireResource(resourceId);
        if (resource.getTeamId() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "公共资源为只读资料，不能移动");
        }
        if (!Objects.equals(resource.getTeamId(), teamId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "不能移动其他团队的资料");
        }
        String normalizedFolder = normalizeFolderKey(folderKey);
        assertWritableFolder(teamId, normalizedFolder);
        if (Objects.equals(normalizedFolder, normalizeFolderKey(resource.getCategory()))) {
            return fileView(resource, false);
        }
        if (resourceMapper.moveToCategory(resourceId, teamId, normalizedFolder) == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "文件状态已变化，请刷新后重试");
        }
        return fileView(requireResource(resourceId), false);
    }

    /**
     * 删除团队资料（含未归类/根目录与各文件夹内文件）。公共只读资源不可删。
     */
    @Transactional
    public void deleteFile(
            Integer resourceId,
            Long teamId,
            Long tenantId,
            Long userId,
            String role
    ) {
        assertTeamAccess(teamId, tenantId, userId, role);
        Resource resource = requireResource(resourceId);
        if (resource.getTeamId() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "公共资源为只读资料，不能删除");
        }
        if (!Objects.equals(resource.getTeamId(), teamId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "不能删除其他团队的资料");
        }
        String filePath = resource.getFilePath() == null ? "" : String.valueOf(resource.getFilePath());
        if (resourceMapper.deleteByIdAndTeamId(resourceId, teamId) == 0) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "文件状态已变化，请刷新后重试");
        }
        // 解绑启发 Office 同步引用（表不存在时忽略）
        try {
            jdbc.update("UPDATE inspire_office_document SET resource_id = NULL WHERE resource_id = ?", resourceId);
        } catch (Exception ignored) {
            /* optional schema */
        }
        deleteStoredFileQuietly(filePath);
    }

    private void deleteStoredFileQuietly(String filePath) {
        if (filePath == null || filePath.isBlank() || !filePath.startsWith("uploads/")) {
            return;
        }
        try {
            Path base = Path.of(uploadDir).toAbsolutePath().normalize();
            String relative = filePath.substring("uploads/".length());
            Path resolved = base.resolve(relative).normalize();
            if (!resolved.startsWith(base)) {
                return;
            }
            Files.deleteIfExists(resolved);
        } catch (Exception ignored) {
            /* 磁盘清理失败不影响业务删除结果 */
        }
    }

    @Transactional
    public Map<String, Object> upload(
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            String folderKey,
            MultipartFile file
    ) throws IOException {
        assertTeamAccess(teamId, tenantId, userId, role);
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择要上传的文件");
        }
        String originalName = safeDisplayName(file.getOriginalFilename());
        String ext = extension(originalName);
        if (!ALLOWED_EXTENSIONS.contains(ext)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "暂不支持该文件类型，请上传文档、表格、演示、图片、音视频或文本文件"
            );
        }
        return registerTeamFile(teamId, tenantId, userId, role, originalName, ext, file.getBytes(), folderKey);
    }

    /**
     * 将字节登记为团队资源（启发 Office 项目/团队文档同步）。
     * 复制到 resource-center 目录，与 Office 编辑文件解耦。
     */
    @Transactional
    public Map<String, Object> registerTeamFile(
            Long teamId,
            Long tenantId,
            Long userId,
            String role,
            String displayName,
            String ext,
            byte[] bytes,
            String folderKey
    ) throws IOException {
        assertTeamAccess(teamId, tenantId, userId, role);
        if (bytes == null || bytes.length == 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件内容为空");
        }
        String cleanExt = ext == null ? "" : ext.trim().toLowerCase(Locale.ROOT);
        if (cleanExt.startsWith(".")) cleanExt = cleanExt.substring(1);
        if (!ALLOWED_EXTENSIONS.contains(cleanExt)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "资源中心不支持该文件类型: " + cleanExt);
        }
        String baseName = displayName == null ? "" : displayName.trim();
        if (baseName.isEmpty()) baseName = "document." + cleanExt;
        else if (!baseName.toLowerCase(Locale.ROOT).endsWith("." + cleanExt)) {
            baseName = baseName + "." + cleanExt;
        }
        String originalName = safeDisplayName(baseName);
        String normalizedFolder = normalizeFolderKey(folderKey);
        assertWritableFolder(teamId, normalizedFolder);
        String storedName = UUID.randomUUID().toString().replace("-", "") + "." + cleanExt;
        Path base = Path.of(uploadDir).toAbsolutePath().normalize();
        Path directory = base.resolve("resource-center").resolve(String.valueOf(teamId)).normalize();
        if (!directory.startsWith(base)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "上传目录不合法");
        }
        Files.createDirectories(directory);
        Path target = directory.resolve(storedName).normalize();
        Files.write(target, bytes);

        Resource resource = new Resource();
        resource.setName(originalName);
        resource.setFileSize((long) bytes.length);
        resource.setExt(cleanExt);
        resource.setFilePath("uploads/resource-center/" + teamId + "/" + storedName);
        resource.setUploadedBy(Math.toIntExact(userId));
        resource.setTeamId(teamId);
        resource.setCategory(normalizedFolder);
        resourceMapper.insert(resource);
        return fileView(requireResource(resource.getId()), false);
    }

    public ResolvedResource resolve(
            Integer resourceId,
            Long tenantId,
            Long userId,
            String role
    ) {
        Resource resource = requireResource(resourceId);
        if (resource.getTeamId() != null) {
            assertTeamAccess(resource.getTeamId(), tenantId, userId, role);
        }
        String filePath = String.valueOf(resource.getFilePath());
        org.springframework.core.io.Resource body;
        if (filePath.startsWith("uploads/")) {
            Path base = Path.of(uploadDir).toAbsolutePath().normalize();
            String relative = filePath.substring("uploads/".length());
            Path resolved = base.resolve(relative).normalize();
            if (!resolved.startsWith(base)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件路径不合法");
            }
            body = new FileSystemResource(resolved);
        } else {
            body = new ClassPathResource(filePath);
        }
        if (!body.exists() || !body.isReadable()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "源文件不存在");
        }
        return new ResolvedResource(resource, body, contentType(resource.getExt()));
    }

    private void assertTeamAccess(Long teamId, Long tenantId, Long userId, String role) {
        if (teamId == null || tenantId == null || userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少团队上下文");
        }
        Integer teamCount = jdbc.queryForObject("""
                SELECT COUNT(*) FROM project_team WHERE id = ? AND tenant_id = ?
                """, Integer.class, teamId, tenantId);
        if (teamCount == null || teamCount == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "团队不存在");
        }
        if (ADMIN_ROLES.contains(String.valueOf(role).toUpperCase(Locale.ROOT))) return;
        Integer membership = jdbc.queryForObject("""
                SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?
                """, Integer.class, teamId, userId);
        if (membership == null || membership == 0) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该团队资源");
        }
    }

    private void assertWritableFolder(Long teamId, String folderKey) {
        if (ROOT_FOLDER.equals(folderKey)) return;
        if (SYSTEM_FOLDERS.stream().anyMatch(folder -> folderKey.equals(folder.get("key")))) return;
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*) FROM resource_category
                WHERE team_id = ? AND category_key = ?
                """, Integer.class, teamId, folderKey);
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "目标文件夹不存在");
        }
    }

    private Resource requireResource(Integer resourceId) {
        Resource resource = resourceMapper.findById(resourceId);
        if (resource == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "资源不存在");
        }
        return resource;
    }

    private List<Map<String, Object>> customFolders(Long teamId) {
        return jdbc.queryForList("""
                SELECT id, category_key AS `key`, label, created_at AS createdAt,
                       updated_at AS updatedAt, 0 AS `system`, 'custom' AS tone
                FROM resource_category
                WHERE team_id = ?
                ORDER BY updated_at DESC, id DESC
                """, teamId);
    }

    private Map<String, Object> folderView(
            Map<String, Object> folder,
            List<Map<String, Object>> files
    ) {
        String key = String.valueOf(folder.get("key"));
        List<Map<String, Object>> matches = files.stream()
                .filter(file -> key.equals(file.get("folderKey")))
                .toList();
        Map<String, Object> result = new LinkedHashMap<>(folder);
        result.put("count", matches.size());
        result.put("covers", matches.stream().limit(3).map(file -> Map.of(
                "id", file.get("id"),
                "name", file.get("name"),
                "ext", file.get("ext"),
                "previewUrl", file.get("previewUrl")
        )).toList());
        return result;
    }

    private Map<String, Object> fileView(Resource resource, boolean publicResource) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", resource.getId());
        result.put("name", resource.getName());
        result.put("ext", resource.getExt());
        result.put("fileSize", resource.getFileSize());
        result.put("size", formatSize(resource.getFileSize()));
        result.put("folderKey", publicResource ? "public" : normalizeFolderKey(resource.getCategory()));
        result.put("public", publicResource);
        result.put("uploaderName", resource.getUploaderName());
        result.put("createdAt", resource.getCreatedAt());
        result.put("updatedAt", resource.getUpdatedAt() != null ? resource.getUpdatedAt() : resource.getCreatedAt());
        result.put("previewUrl", "/api/resource-center/files/" + resource.getId() + "/preview");
        result.put("downloadUrl", "/api/resource-center/files/" + resource.getId() + "/download");
        result.put("mimeType", contentType(resource.getExt()));
        return result;
    }

    private static Map<String, Object> folderDefinition(String key, String label, String tone) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", null);
        result.put("key", key);
        result.put("label", label);
        result.put("system", true);
        result.put("tone", tone);
        return result;
    }

    private String cleanFolderLabel(String label) {
        String clean = label == null ? "" : label.trim().replaceAll("\\s+", " ");
        if (clean.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件夹名称不能为空");
        }
        if (clean.length() > 30) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件夹名称不能超过 30 个字符");
        }
        return clean;
    }

    private String normalizeFolderKey(String folderKey) {
        String clean = folderKey == null ? "" : folderKey.trim();
        if (clean.isEmpty() || "all".equals(clean)) return ROOT_FOLDER;
        if (!clean.matches("[a-zA-Z0-9_\\-]{1,64}")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件夹标识不合法");
        }
        return clean;
    }

    private String safeDisplayName(String filename) {
        String clean = filename == null ? "" : Path.of(filename).getFileName().toString().trim();
        if (clean.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件名不能为空");
        }
        return clean.length() > 255 ? clean.substring(clean.length() - 255) : clean;
    }

    private String extension(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
    }

    private String formatSize(Long bytes) {
        long value = bytes == null ? 0L : bytes;
        if (value < 1024) return value + " B";
        if (value < 1024 * 1024) return String.format(Locale.ROOT, "%.1f KB", value / 1024.0);
        if (value < 1024L * 1024 * 1024) {
            return String.format(Locale.ROOT, "%.1f MB", value / (1024.0 * 1024));
        }
        return String.format(Locale.ROOT, "%.2f GB", value / (1024.0 * 1024 * 1024));
    }

    private String contentType(String extension) {
        String ext = String.valueOf(extension).toLowerCase(Locale.ROOT);
        return switch (ext) {
            case "pdf" -> "application/pdf";
            case "doc" -> "application/msword";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xls" -> "application/vnd.ms-excel";
            case "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "csv" -> "text/csv";
            case "ppt" -> "application/vnd.ms-powerpoint";
            case "pptx" -> "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            case "png" -> "image/png";
            case "jpg", "jpeg" -> "image/jpeg";
            case "gif" -> "image/gif";
            case "webp" -> "image/webp";
            case "svg" -> "image/svg+xml";
            case "mp4" -> "video/mp4";
            case "webm" -> "video/webm";
            case "mov" -> "video/quicktime";
            case "mp3" -> "audio/mpeg";
            case "wav" -> "audio/wav";
            case "m4a" -> "audio/mp4";
            case "ogg" -> "audio/ogg";
            case "md", "txt" -> "text/plain";
            case "sdoc" -> "application/vnd.orep.sdoc+json";
            default -> "application/octet-stream";
        };
    }

    public record ResolvedResource(
            Resource metadata,
            org.springframework.core.io.Resource body,
            String contentType
    ) {
    }
}
