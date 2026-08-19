package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.AdminChapterRequest;
import com.orep.backend.dto.AdminCourseRequest;
import com.orep.backend.dto.AdminLessonRequest;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.CourseDetailVO;
import com.orep.backend.entity.Course;
import com.orep.backend.entity.CourseAttachment;
import com.orep.backend.entity.CourseChapter;
import com.orep.backend.entity.CourseLesson;
import com.orep.backend.service.CourseService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/admin/courses")
public class AdminCourseController {
    private final CourseService courseService;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    public AdminCourseController(CourseService courseService) {
        this.courseService = courseService;
    }

    @GetMapping
    public Result<List<Course>> listCourses(HttpServletRequest request) {
        return Result.success(courseService.listAdminCourses(userId(request), role(request)));
    }

    @GetMapping("/{id}")
    public Result<CourseDetailVO> getCourse(@PathVariable Long id, HttpServletRequest request) {
        CourseDetailVO detail = courseService.getAdminCourseDetail(id, userId(request), role(request));
        if (detail == null) return Result.error(404, "课程不存在");
        return Result.success(detail);
    }

    @PostMapping
    public Result<Course> createCourse(@RequestBody AdminCourseRequest body, HttpServletRequest request) {
        return Result.success(courseService.createCourse(body, userId(request)));
    }

    @PutMapping("/{id}")
    public Result<Course> updateCourse(@PathVariable Long id, @RequestBody AdminCourseRequest body, HttpServletRequest request) {
        Course course = courseService.updateCourse(id, body, userId(request), role(request));
        if (course == null) return Result.error(404, "课程不存在");
        return Result.success(course);
    }

    @DeleteMapping("/{id}")
    public Result<Void> deleteCourse(@PathVariable Long id, HttpServletRequest request) {
        if (!courseService.deleteCourse(id, userId(request), role(request))) return Result.error(404, "课程不存在");
        return Result.success();
    }

    @PostMapping("/{id}/cover")
    public Result<?> uploadCourseCover(
            @PathVariable Long id,
            @RequestParam("file") MultipartFile file,
            HttpServletRequest request
    ) throws IOException {
        if (file == null || file.isEmpty()) return Result.error(400, "封面图片为空");
        String originalName = file.getOriginalFilename() == null ? "course-cover.jpg" : file.getOriginalFilename();
        String ext = getExt(originalName);
        if (!List.of("jpg", "jpeg", "png", "webp").contains(ext)) {
            return Result.error(400, "仅支持 jpg、jpeg、png、webp 图片");
        }
        if (file.getSize() > 5L * 1024 * 1024) {
            return Result.error(400, "封面图片不能超过 5MB");
        }

        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        Path base = Path.of(uploadDir).toAbsolutePath().normalize();
        Path dir = base.resolve("course-covers").resolve(String.valueOf(id)).resolve(datePath).normalize();
        Files.createDirectories(dir);
        String fileName = UUID.randomUUID().toString().replace("-", "") + "." + ext;
        Path target = dir.resolve(fileName).normalize();
        if (!target.startsWith(base)) return Result.error(400, "文件路径不合法");
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        String outputExt = optimizeVideoForWebPlayback(target, ext);
        if (!outputExt.equals(ext)) {
            target = target.resolveSibling(target.getFileName().toString().replaceFirst("\\.[^.]+$", "." + outputExt));
            ext = outputExt;
        }

        String relativePath = base.relativize(target).toString().replace("\\", "/");
        Course course = courseService.updateCourseCover(
                id,
                "/uploads/" + relativePath,
                userId(request),
                role(request)
        );
        if (course == null) return Result.error(404, "课程不存在");
        return Result.success(Map.of(
                "courseId", course.getId(),
                "coverUrl", course.getCoverUrl()
        ));
    }

    @PostMapping("/batch-delete")
    public Result<BatchDeleteResult> batchDeleteCourses(@RequestBody BatchDeleteRequest body, HttpServletRequest request) {
        return Result.success(courseService.deleteCourses(body.getIds(), userId(request), role(request)));
    }

    @PostMapping("/{id}/chapters")
    public Result<CourseChapter> createChapter(@PathVariable Long id, @RequestBody AdminChapterRequest body, HttpServletRequest request) {
        CourseChapter chapter = courseService.createChapter(id, body, userId(request), role(request));
        if (chapter == null) return Result.error(404, "课程不存在");
        return Result.success(chapter);
    }

    @PutMapping("/{id}/chapters/{chapterId}")
    public Result<CourseChapter> updateChapter(
            @PathVariable Long id,
            @PathVariable Long chapterId,
            @RequestBody AdminChapterRequest body,
            HttpServletRequest request
    ) {
        CourseChapter chapter = courseService.updateChapter(id, chapterId, body, userId(request), role(request));
        if (chapter == null) return Result.error(404, "章节不存在");
        return Result.success(chapter);
    }

    @DeleteMapping("/{id}/chapters/{chapterId}")
    public Result<Void> deleteChapter(@PathVariable Long id, @PathVariable Long chapterId, HttpServletRequest request) {
        if (!courseService.deleteChapter(id, chapterId, userId(request), role(request))) return Result.error(404, "章节不存在");
        return Result.success();
    }

    @PostMapping("/{id}/lessons")
    public Result<CourseLesson> createLesson(@PathVariable Long id, @RequestBody AdminLessonRequest body, HttpServletRequest request) {
        CourseLesson lesson = courseService.createLesson(id, body, userId(request), role(request));
        if (lesson == null) return Result.error(404, "课程或章节不存在");
        return Result.success(lesson);
    }

    @PutMapping("/{id}/lessons/{lessonId}")
    public Result<CourseLesson> updateLesson(
            @PathVariable Long id,
            @PathVariable Long lessonId,
            @RequestBody AdminLessonRequest body,
            HttpServletRequest request
    ) {
        CourseLesson lesson = courseService.updateLesson(id, lessonId, body, userId(request), role(request));
        if (lesson == null) return Result.error(404, "课程、章节或课时不存在");
        return Result.success(lesson);
    }

    @DeleteMapping("/{id}/lessons/{lessonId}")
    public Result<Void> deleteLesson(@PathVariable Long id, @PathVariable Long lessonId, HttpServletRequest request) {
        if (!courseService.deleteLesson(id, lessonId, userId(request), role(request))) return Result.error(404, "课时不存在");
        return Result.success();
    }

    @PostMapping("/lessons/{lessonId}/video")
    public Result<?> uploadLessonVideo(
            @PathVariable Long lessonId,
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "durationSeconds", required = false) Integer durationSeconds,
            HttpServletRequest request
    ) throws IOException {
        if (file == null || file.isEmpty()) return Result.error(400, "视频文件为空");
        String originalName = file.getOriginalFilename() == null ? "lesson-video.mp4" : file.getOriginalFilename();
        String ext = getExt(originalName);
        if (!List.of("mp4", "webm", "mov", "m4v").contains(ext)) {
            return Result.error(400, "仅支持 mp4、webm、mov、m4v 视频");
        }

        CourseLesson lesson = courseService.getLesson(lessonId);
        if (lesson == null) return Result.error(404, "课时不存在");

        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        Path base = Path.of(uploadDir).toAbsolutePath().normalize();
        Path dir = base.resolve("course-videos").resolve(String.valueOf(lesson.getCourseId())).resolve(datePath).normalize();
        Files.createDirectories(dir);
        String fileName = UUID.randomUUID().toString().replace("-", "") + "." + ext;
        Path target = dir.resolve(fileName).normalize();
        if (!target.startsWith(base)) return Result.error(400, "文件路径不合法");
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

        String relativePath = base.relativize(target).toString().replace("\\", "/");
        CourseLesson updated = courseService.attachLessonVideo(
                lessonId,
                relativePath,
                detectVideoMime(null, ext),
                Files.size(target),
                durationSeconds,
                userId(request),
                role(request)
        );
        if (updated == null) return Result.error(404, "课时不存在");
        return Result.success(Map.of(
                "lessonId", updated.getId(),
                "resourceUrl", updated.getResourceUrl(),
                "videoSizeBytes", updated.getVideoSizeBytes(),
                "videoMimeType", updated.getVideoMimeType()
        ));
    }

    @PostMapping("/{id}/attachments")
    public Result<?> uploadAttachment(
            @PathVariable Long id,
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "sortOrder", required = false) Integer sortOrder,
            HttpServletRequest request
    ) throws IOException {
        if (file == null || file.isEmpty()) return Result.error(400, "附件文件为空");
        String originalName = file.getOriginalFilename() == null ? "课程附件" : file.getOriginalFilename();
        String ext = getExt(originalName);
        if (!List.of("pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip", "rar", "png", "jpg", "jpeg").contains(ext)) {
            return Result.error(400, "仅支持 PDF、Office、压缩包和图片附件");
        }
        if (file.getSize() > 100L * 1024 * 1024) {
            return Result.error(400, "附件不能超过 100MB");
        }

        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        Path base = Path.of(uploadDir).toAbsolutePath().normalize();
        Path dir = base.resolve("course-attachments").resolve(String.valueOf(id)).resolve(datePath).normalize();
        Files.createDirectories(dir);
        String fileName = UUID.randomUUID().toString().replace("-", "") + "." + ext;
        Path target = dir.resolve(fileName).normalize();
        if (!target.startsWith(base)) return Result.error(400, "文件路径不合法");
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

        String relativePath = base.relativize(target).toString().replace("\\", "/");
        CourseAttachment attachment = courseService.createAttachment(
                id,
                originalName,
                "/uploads/" + relativePath,
                ext,
                formatSize(Files.size(target)),
                sortOrder,
                userId(request),
                role(request)
        );
        if (attachment == null) return Result.error(404, "课程不存在");
        return Result.success(attachment);
    }

    @DeleteMapping("/{courseId}/attachments/{attachmentId}")
    public Result<Void> deleteAttachment(@PathVariable Long courseId, @PathVariable Long attachmentId, HttpServletRequest request) {
        if (!courseService.deleteAttachment(courseId, attachmentId, userId(request), role(request))) return Result.error(404, "附件不存在");
        return Result.success();
    }

    @PostMapping("/{courseId}/attachments/batch-delete")
    public Result<BatchDeleteResult> batchDeleteAttachments(
            @PathVariable Long courseId,
            @RequestBody BatchDeleteRequest body,
            HttpServletRequest request
    ) {
        return Result.success(courseService.deleteAttachments(courseId, body.getIds(), userId(request), role(request)));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }

    private String getExt(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "";
    }

    private String detectVideoMime(String contentType, String ext) {
        if (contentType != null && contentType.startsWith("video/")) return contentType;
        if ("webm".equals(ext)) return "video/webm";
        if ("mov".equals(ext)) return "video/quicktime";
        return "video/mp4";
    }

    private String optimizeVideoForWebPlayback(Path target, String ext) {
        if (!List.of("mp4", "mov", "m4v").contains(ext)) return ext;
        boolean transcode = shouldTranscodeForWebPlayback(target, ext);
        String outputExt = transcode ? "mp4" : ext;
        Path temp = target.resolveSibling(target.getFileName().toString() + ".web." + outputExt);
        try {
            ProcessBuilder builder = transcode
                    ? new ProcessBuilder(
                            "ffmpeg",
                            "-y",
                            "-i", target.toString(),
                            "-c:v", "libx264",
                            "-preset", "veryfast",
                            "-crf", "23",
                            "-c:a", "aac",
                            "-b:a", "128k",
                            "-movflags", "+faststart",
                            temp.toString()
                    )
                    : new ProcessBuilder(
                            "ffmpeg",
                            "-y",
                            "-i", target.toString(),
                            "-c", "copy",
                            "-movflags", "+faststart",
                            temp.toString()
                    );
            Process process = builder.redirectErrorStream(true).start();
            if (process.waitFor() == 0 && Files.exists(temp) && Files.size(temp) > 0) {
                Path finalTarget = outputExt.equals(ext)
                        ? target
                        : target.resolveSibling(target.getFileName().toString().replaceFirst("\\.[^.]+$", "." + outputExt));
                Files.move(temp, finalTarget, StandardCopyOption.REPLACE_EXISTING);
                if (!finalTarget.equals(target)) Files.deleteIfExists(target);
                return outputExt;
            } else {
                Files.deleteIfExists(temp);
            }
        } catch (Exception ignored) {
            try {
                Files.deleteIfExists(temp);
            } catch (IOException ignoredDelete) {
                // Keep the original uploaded video if local ffmpeg is unavailable.
            }
        }
        return ext;
    }

    boolean shouldTranscodeForWebPlayback(Path target, String ext) {
        if (!"mp4".equals(ext)) return true;
        try {
            Process process = new ProcessBuilder(
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    target.toString()
            ).redirectErrorStream(true).start();
            String videoCodec = new String(process.getInputStream().readAllBytes()).trim();
            if (process.waitFor() != 0 || !"h264".equals(videoCodec)) return true;

            Process audioProcess = new ProcessBuilder(
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=codec_name",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    target.toString()
            ).redirectErrorStream(true).start();
            String audioCodec = new String(audioProcess.getInputStream().readAllBytes()).trim();
            return audioProcess.waitFor() != 0 || !"aac".equals(audioCodec);
        } catch (Exception ignored) {
            return false;
        }
    }

    private String formatSize(long bytes) {
        if (bytes >= 1024 * 1024) return String.format("%.1f MB", bytes / 1024.0 / 1024.0);
        if (bytes >= 1024) return String.format("%.1f KB", bytes / 1024.0);
        return bytes + " B";
    }
}
