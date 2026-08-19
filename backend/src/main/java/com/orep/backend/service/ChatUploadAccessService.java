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
 * 会中聊天上传：旧日期目录 /uploads/yyyy/** 与 /uploads/chat/**。
 * 匿名不可读。若文件已被某会议聊天引用，仅该会创建人/参会人可读。
 */
@Service
public class ChatUploadAccessService {

    private final JdbcTemplate jdbcTemplate;
    private final AiScoreAccessControlService accessControlService;
    private final Path uploadRoot;

    public ChatUploadAccessService(JdbcTemplate jdbcTemplate,
                                   AiScoreAccessControlService accessControlService,
                                   @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.jdbcTemplate = jdbcTemplate;
        this.accessControlService = accessControlService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedChatUpload(String rawUrl) {
        String path = canonicalUploadPath(rawUrl);
        return path.matches("^/uploads/\\d{4}/.*") || path.startsWith("/uploads/chat/");
    }

    public Path authorize(String rawUrl, Long userId) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        if (!isProtectedChatUpload(path)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Path file = resolveFile(path);
        if (!Files.isRegularFile(file)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Long meetingId = meetingIdForUpload(path);
        if (meetingId != null && !accessControlService.hasMeetingParticipantAccess(meetingId, userId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return file;
    }

    private Long meetingIdForUpload(String path) {
        List<Long> ids = jdbcTemplate.queryForList(
                "SELECT meeting_id FROM chat_message WHERE content = ? ORDER BY id DESC LIMIT 1",
                Long.class,
                path);
        return ids.isEmpty() ? null : ids.get(0);
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
}
