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
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 训练日说明图与附件：/uploads/task/instructions/{dayId}/**。
 * 匿名不可读。教师按营期只读门；学生须为本营期队员且当天已开放。
 */
@Service
public class TaskInstructionUploadAccessService {

    private final JdbcTemplate jdbc;
    private final TrainingDayAvailabilityService availabilityService;
    private final Path uploadRoot;

    public TaskInstructionUploadAccessService(
            JdbcTemplate jdbc,
            TrainingDayAvailabilityService availabilityService,
            @Value("${file.upload-dir:./uploads}") String uploadDir
    ) {
        this.jdbc = jdbc;
        this.availabilityService = availabilityService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedTaskInstruction(String rawUrl) {
        return canonicalUploadPath(rawUrl).startsWith("/uploads/task/instructions/");
    }

    public Path authorize(String rawUrl, Long tenantId, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        Long dayId = dayIdFromPath(path);
        if (dayId == null || !canView(tenantId, userId, role, dayId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Path file = resolveFile(path);
        if (!Files.isRegularFile(file)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return file;
    }

    boolean canView(Long tenantId, Long userId, String role, Long dayId) {
        if (tenantId == null || userId == null || dayId == null) {
            return false;
        }
        List<Map<String, Object>> days = jdbc.queryForList("""
                SELECT d.status, d.training_date trainingDate, d.early_unlocked_at earlyUnlockedAt
                FROM training_day d
                JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
                WHERE d.id = ?
                """, tenantId, dayId);
        if (days.isEmpty()) {
            return false;
        }
        String normalized = role == null ? "" : role.toUpperCase(Locale.ROOT);
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalized)) {
            return true;
        }
        if ("TEACHER".equals(normalized)) {
            Integer count = jdbc.queryForObject("""
                    SELECT COUNT(DISTINCT pt.id)
                    FROM training_day d
                    JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
                    JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.status = 'ACTIVE'
                    JOIN project_team pt ON pt.id = ct.team_id AND pt.tenant_id = c.tenant_id
                    WHERE d.id = ? AND (pt.mentor_id = ? OR EXISTS (
                      SELECT 1 FROM project_team_member tm
                      WHERE tm.team_id = pt.id AND tm.user_id = ? AND tm.role_in_team = 'MENTOR'
                    ))
                    """, Integer.class, tenantId, dayId, userId, userId);
            return count != null && count > 0;
        }
        Integer member = jdbc.queryForObject("""
                SELECT COUNT(1)
                FROM training_day d
                JOIN training_camp c ON c.id = d.camp_id AND c.tenant_id = ?
                JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.status = 'ACTIVE'
                JOIN project_team pt ON pt.id = ct.team_id AND pt.tenant_id = c.tenant_id
                JOIN project_team_member tm ON tm.team_id = pt.id AND tm.user_id = ?
                WHERE d.id = ?
                """, Integer.class, tenantId, userId, dayId);
        if (member == null || member == 0) {
            return false;
        }
        return !Boolean.TRUE.equals(availabilityService.availability(days.get(0)).get("locked"));
    }

    static Long dayIdFromPath(String path) {
        String prefix = "/uploads/task/instructions/";
        if (path == null || !path.startsWith(prefix)) {
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
