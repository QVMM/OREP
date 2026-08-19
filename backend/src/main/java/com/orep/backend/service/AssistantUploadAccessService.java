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
import java.util.List;

/**
 * 小启生成文件：/uploads/assistant/{tenantId}/{sessionId}/**。
 * 匿名不可读。仅该会话主人可读，与 /api/assistant/files/{id}/download 一致。
 */
@Service
public class AssistantUploadAccessService {

    private final JdbcTemplate jdbcTemplate;
    private final Path uploadRoot;

    public AssistantUploadAccessService(JdbcTemplate jdbcTemplate,
                                        @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.jdbcTemplate = jdbcTemplate;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedAssistantUpload(String rawUrl) {
        return canonicalUploadPath(rawUrl).startsWith("/uploads/assistant/");
    }

    public Path authorize(String rawUrl, Long tenantId, Long userId) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        Ids ids = idsFromPath(path);
        if (ids == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        if (tenantId == null || !tenantId.equals(ids.tenantId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Integer owned = jdbcTemplate.queryForObject("""
                SELECT COUNT(1)
                FROM ai_assistant_session
                WHERE id = ? AND tenant_id = ? AND user_id = ? AND status <> 'deleted'
                """, Integer.class, ids.sessionId, ids.tenantId, userId);
        if (owned == null || owned == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Path file = resolveFile(path);
        if (!Files.isRegularFile(file)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return file;
    }

    static Ids idsFromPath(String path) {
        String prefix = "/uploads/assistant/";
        if (!path.startsWith(prefix)) {
            return null;
        }
        String rest = path.substring(prefix.length());
        String[] parts = rest.split("/", 3);
        if (parts.length < 3 || parts[0].isBlank() || parts[1].isBlank()) {
            return null;
        }
        if (!parts[0].chars().allMatch(Character::isDigit) || !parts[1].chars().allMatch(Character::isDigit)) {
            return null;
        }
        try {
            return new Ids(Long.parseLong(parts[0]), Long.parseLong(parts[1]));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Path resolveFile(String path) {
        String relative = path.substring("/uploads/".length());
        Path target = uploadRoot.resolve(relative).normalize();
        if (!target.startsWith(uploadRoot)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件路径非法");
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

    record Ids(Long tenantId, Long sessionId) {
    }
}
