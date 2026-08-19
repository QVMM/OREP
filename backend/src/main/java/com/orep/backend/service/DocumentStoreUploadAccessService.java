package com.orep.backend.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 资源中心与启发 Office 版本目录。匿名不可读。
 * 权限对齐正式下载口：资源中心看队伍，Office 看文档主人或本队。
 */
@Service
public class DocumentStoreUploadAccessService {

    private static final Set<String> RESOURCE_ADMIN_ROLES = Set.of("ADMIN", "SCHOOL_ADMIN");

    private final JdbcTemplate jdbcTemplate;
    private final Path uploadRoot;

    public DocumentStoreUploadAccessService(JdbcTemplate jdbcTemplate,
                                            @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.jdbcTemplate = jdbcTemplate;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedResourceCenterUpload(String rawUrl) {
        return canonicalUploadPath(rawUrl).startsWith("/uploads/resource-center/");
    }

    public boolean isProtectedOfficeVersionUpload(String rawUrl) {
        return canonicalUploadPath(rawUrl).startsWith("/uploads/office/versions/");
    }

    public Path authorizeResourceCenter(String rawUrl, Long tenantId, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        Long teamId = firstNumericSegment(path, "/uploads/resource-center/");
        if (teamId == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Integer teamCount = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM project_team WHERE id = ? AND tenant_id = ?",
                Integer.class, teamId, tenantId);
        if (teamCount == null || teamCount == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        String normalizedRole = role == null ? "" : role.trim().toUpperCase(Locale.ROOT);
        if (!RESOURCE_ADMIN_ROLES.contains(normalizedRole)) {
            Integer membership = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?",
                    Integer.class, teamId, userId);
            if (membership == null || membership == 0) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
            }
        }
        return existingFile(path);
    }

    public Path authorizeOfficeVersion(String rawUrl, Long userId) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        Long docId = firstNumericSegment(path, "/uploads/office/versions/");
        if (docId == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        var rows = jdbcTemplate.queryForList("""
                SELECT owner_user_id AS ownerUserId, team_id AS teamId, scope, status
                FROM inspire_office_document
                WHERE id = ?
                """, docId);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Map<String, Object> doc = rows.get(0);
        if (!"active".equals(String.valueOf(doc.get("status")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        if (!canAccessOffice(doc, userId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return existingFile(path);
    }

    private boolean canAccessOffice(Map<String, Object> doc, Long userId) {
        Object owner = doc.get("ownerUserId");
        if (owner instanceof Number n && userId.equals(n.longValue())) {
            return true;
        }
        String scope = doc.get("scope") == null ? "" : String.valueOf(doc.get("scope"));
        Object team = doc.get("teamId");
        if (team instanceof Number n && ("project".equals(scope) || "team".equals(scope))) {
            Integer membership = jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?",
                    Integer.class, n.longValue(), userId);
            return membership != null && membership > 0;
        }
        return false;
    }

    static Long firstNumericSegment(String path, String prefix) {
        if (!path.startsWith(prefix)) {
            return null;
        }
        String rest = path.substring(prefix.length());
        int slash = rest.indexOf('/');
        String folder = slash < 0 ? rest : rest.substring(0, slash);
        if (folder.isBlank() || !folder.chars().allMatch(Character::isDigit)) {
            return null;
        }
        try {
            return Long.parseLong(folder);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Path existingFile(String path) {
        String relative = path.substring("/uploads/".length());
        Path target = uploadRoot.resolve(relative).normalize();
        if (!target.startsWith(uploadRoot)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件路径非法");
        }
        if (!Files.isRegularFile(target)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return target;
    }

    static String canonicalUploadPath(String rawUrl) {
        if (rawUrl == null || rawUrl.isBlank()) {
            return "";
        }
        String decoded = URLDecoder.decode(rawUrl.trim(), StandardCharsets.UTF_8).replace('\\', '/');
        int q = decoded.indexOf('?');
        if (q >= 0) {
            decoded = decoded.substring(0, q);
        }
        int hash = decoded.indexOf('#');
        if (hash >= 0) {
            decoded = decoded.substring(0, hash);
        }
        int idx = decoded.indexOf("/uploads/");
        if (idx >= 0) {
            return decoded.substring(idx);
        }
        if (decoded.startsWith("uploads/")) {
            return "/" + decoded;
        }
        return decoded.startsWith("/") ? decoded : "/" + decoded;
    }
}
