package com.orep.backend.service;

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
 * 课程视频、附件与封面：/uploads/course-videos|course-attachments|course-covers/{courseId}/**。
 * 匿名不可读。已发布课任意登录用户可读；未发布仅创建教师或学校管理员。
 */
@Service
public class CourseMaterialUploadAccessService {

    private final CourseService courseService;
    private final Path uploadRoot;

    public CourseMaterialUploadAccessService(CourseService courseService,
                                             @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.courseService = courseService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public boolean isProtectedCourseMaterial(String rawUrl) {
        String path = canonicalUploadPath(rawUrl);
        return path.startsWith("/uploads/course-videos/")
                || path.startsWith("/uploads/course-attachments/")
                || path.startsWith("/uploads/course-covers/");
    }

    public Path authorize(String rawUrl, Long userId, String role) {
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "未登录");
        }
        String path = canonicalUploadPath(rawUrl);
        Long courseId = courseIdFromPath(path);
        if (courseId == null || !courseService.canViewCourseMedia(courseId, userId, role)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        Path file = resolveFile(path);
        if (!Files.isRegularFile(file)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在");
        }
        return file;
    }

    static Long courseIdFromPath(String path) {
        String prefix = path.startsWith("/uploads/course-videos/")
                ? "/uploads/course-videos/"
                : path.startsWith("/uploads/course-attachments/")
                ? "/uploads/course-attachments/"
                : path.startsWith("/uploads/course-covers/")
                ? "/uploads/course-covers/"
                : null;
        if (prefix == null) {
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
