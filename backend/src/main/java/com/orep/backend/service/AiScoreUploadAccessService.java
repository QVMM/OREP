package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 评分上传目录 /uploads/ai-score/{sessionId}/**。
 * 匿名不可读。按评分会话门收口，与 /sessions/{id}/media/video 同一套权限。
 */
@Service
public class AiScoreUploadAccessService {

    private final AiScoringSessionService scoringSessionService;
    private final AiScoreAccessControlService accessControlService;
    private final Path uploadRoot;

    public AiScoreUploadAccessService(AiScoringSessionService scoringSessionService,
                                      AiScoreAccessControlService accessControlService,
                                      @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.scoringSessionService = scoringSessionService;
        this.accessControlService = accessControlService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedAiScoreUpload(String rawUrl) {
        return canonicalUploadPath(rawUrl).startsWith("/uploads/ai-score/");
    }

    public Path authorize(String rawUrl, Long tenantId, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        if (!isProtectedAiScoreUpload(path)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Long sessionId = sessionIdFromPath(path);
        if (sessionId == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        AiScoringSession session;
        try {
            session = scoringSessionService.requireSessionForAccess(sessionId);
        } catch (IllegalStateException e) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        accessControlService.assertSessionAccess(session, tenantId, userId, role);
        Path file = resolveFile(path);
        if (!Files.isRegularFile(file)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return file;
    }

    static Long sessionIdFromPath(String path) {
        String prefix = "/uploads/ai-score/";
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
