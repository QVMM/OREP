package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.CourseDetailVO;
import com.orep.backend.dto.CourseVO;
import com.orep.backend.entity.CourseLesson;
import com.orep.backend.service.CourseService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/courses")
public class CourseController {
    private static final long VIDEO_RANGE_CHUNK_SIZE = 8L * 1024L * 1024L;

    private final CourseService courseService;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    public CourseController(CourseService courseService) {
        this.courseService = courseService;
    }

    @GetMapping
    public Result<List<CourseVO>> listCourses(
            @RequestParam(required = false, defaultValue = "all") String filter,
            @RequestParam(required = false, defaultValue = "all") String category,
            HttpServletRequest request
    ) {
        Long userId = (Long) request.getAttribute("userId");
        return Result.success(courseService.listCourses(userId, filter, category));
    }

    @GetMapping("/{id}")
    public Result<CourseDetailVO> getCourse(@PathVariable Long id, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        CourseDetailVO detail = courseService.getCourseDetail(id, userId);
        if (detail == null) return Result.error(404, "课程不存在或未发布");
        return Result.success(detail);
    }

    @PostMapping("/{id}/progress")
    public Result<CourseVO> saveProgress(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        Long userId = (Long) request.getAttribute("userId");
        Long lessonId = toLong(body.get("lessonId"));
        Integer learnedSeconds = toInteger(body.get("learnedSeconds"));
        if (lessonId == null) return Result.error(400, "缺少课时ID");
        CourseVO course = courseService.saveProgress(userId, id, lessonId, learnedSeconds);
        if (course == null) return Result.error(404, "课程或课时不存在");
        return Result.success(course);
    }

    @PostMapping("/lessons/{lessonId}/complete")
    public Result<CourseVO> completeLesson(@PathVariable Long lessonId, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        CourseVO course;
        try {
            course = courseService.completeLesson(userId, lessonId);
        } catch (IllegalStateException e) {
            return Result.error(400, e.getMessage());
        }
        if (course == null) return Result.error(404, "课时不存在");
        return Result.success(course);
    }

    @GetMapping("/lessons/{lessonId}/play-url")
    public Result<Map<String, Object>> getLessonPlayUrl(@PathVariable Long lessonId,
                                                        HttpServletRequest request) {
        if (!courseService.canViewLessonMedia(lessonId, attrLong(request, "userId"), attrString(request, "role"))) {
            return Result.error(404, "视频不存在");
        }
        CourseLesson lesson = courseService.getLesson(lessonId);
        if (lesson == null || lesson.getVideoFilePath() == null || lesson.getVideoFilePath().isBlank()) {
            return Result.error(404, "视频不存在");
        }
        String normalizedPath = lesson.getVideoFilePath().replace("\\", "/");
        if (normalizedPath.startsWith("/")) normalizedPath = normalizedPath.substring(1);
        if (normalizedPath.contains("..")) return Result.error(400, "视频路径不合法");
        return Result.success(Map.of(
                "lessonId", lesson.getId(),
                "videoUrl", "/uploads/" + normalizedPath,
                "mimeType", lesson.getVideoMimeType() == null || lesson.getVideoMimeType().isBlank() ? "video/mp4" : lesson.getVideoMimeType(),
                "expiresInSeconds", 3600
        ));
    }

    @GetMapping("/lessons/{lessonId}/stream")
    public ResponseEntity<?> streamLesson(
            @PathVariable Long lessonId,
            @RequestHeader(value = HttpHeaders.RANGE, required = false) String rangeHeader,
            HttpServletRequest request
    ) throws IOException {
        if (!courseService.canViewLessonMedia(lessonId, attrLong(request, "userId"), attrString(request, "role"))) {
            return ResponseEntity.notFound().build();
        }
        CourseLesson lesson = courseService.getLesson(lessonId);
        if (lesson == null || lesson.getVideoFilePath() == null || lesson.getVideoFilePath().isBlank()) {
            return ResponseEntity.notFound().build();
        }
        Path base = Path.of(uploadDir).toAbsolutePath().normalize();
        Path videoPath = base.resolve(lesson.getVideoFilePath()).normalize();
        if (!videoPath.startsWith(base) || !Files.exists(videoPath)) {
            return ResponseEntity.notFound().build();
        }
        String contentType = lesson.getVideoMimeType() == null || lesson.getVideoMimeType().isBlank()
                ? "video/mp4"
                : lesson.getVideoMimeType();
        long fileSize = Files.size(videoPath);
        if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
            long[] range = parseRange(rangeHeader, fileSize);
            long start = range[0];
            long end = Math.min(range[1], start + VIDEO_RANGE_CHUNK_SIZE - 1);
            long length = end - start + 1;
            StreamingResponseBody body = output -> writeRange(videoPath, start, length, output);
            return ResponseEntity.status(HttpStatus.PARTIAL_CONTENT)
                    .header(HttpHeaders.ACCEPT_RANGES, "bytes")
                    .header(HttpHeaders.CONTENT_RANGE, "bytes " + start + "-" + end + "/" + fileSize)
                    .contentLength(length)
                    .contentType(MediaType.parseMediaType(contentType))
                    .body(body);
        }
        return ResponseEntity.ok()
                .header(HttpHeaders.ACCEPT_RANGES, "bytes")
                .contentLength(fileSize)
                .contentType(MediaType.parseMediaType(contentType))
                .body(new FileSystemResource(videoPath));
    }

    private void writeRange(Path videoPath, long start, long length, OutputStream output) throws IOException {
        try (InputStream input = Files.newInputStream(videoPath)) {
            long skipped = input.skip(start);
            if (skipped < start) return;
            byte[] buffer = new byte[64 * 1024];
            long remaining = length;
            while (remaining > 0) {
                int read = input.read(buffer, 0, (int) Math.min(buffer.length, remaining));
                if (read < 0) break;
                output.write(buffer, 0, read);
                remaining -= read;
            }
        }
    }

    private long[] parseRange(String rangeHeader, long fileSize) {
        String rangeValue = rangeHeader.substring("bytes=".length()).trim();
        String firstRange = rangeValue.split(",", 2)[0].trim();
        String[] parts = firstRange.split("-", 2);
        long start;
        long end;
        if (parts[0].isBlank()) {
            long suffixLength = Long.parseLong(parts[1]);
            start = Math.max(0, fileSize - suffixLength);
            end = fileSize - 1;
        } else {
            start = Long.parseLong(parts[0]);
            end = parts.length > 1 && !parts[1].isBlank() ? Long.parseLong(parts[1]) : fileSize - 1;
        }
        start = Math.max(0, Math.min(start, fileSize - 1));
        end = Math.max(start, Math.min(end, fileSize - 1));
        return new long[]{start, end};
    }

    private Long toLong(Object value) {
        if (value instanceof Number number) return number.longValue();
        if (value instanceof String text && !text.isBlank()) return Long.parseLong(text);
        return null;
    }

    private Integer toInteger(Object value) {
        if (value instanceof Number number) return number.intValue();
        if (value instanceof String text && !text.isBlank()) return Integer.parseInt(text);
        return 0;
    }

    private Long attrLong(HttpServletRequest request, String key) {
        if (request == null) return null;
        Object value = request.getAttribute(key);
        return value instanceof Number number ? number.longValue() : null;
    }

    private String attrString(HttpServletRequest request, String key) {
        if (request == null) return null;
        Object value = request.getAttribute(key);
        return value == null ? null : String.valueOf(value);
    }
}
