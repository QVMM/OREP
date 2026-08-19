package com.orep.backend.controller;

import com.orep.backend.entity.CourseLesson;
import com.orep.backend.entity.Course;
import com.orep.backend.service.CourseService;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CourseControllerTest {

    @Test
    void streamLessonHonorsRangeRequestsForHtmlVideoPlayback() throws Exception {
        Path uploadDir = Files.createTempDirectory("orep-course-video-test");
        Path video = uploadDir.resolve("course-videos/1/demo.mp4");
        Files.createDirectories(video.getParent());
        Files.write(video, "0123456789".getBytes());

        CourseLesson lesson = new CourseLesson();
        lesson.setId(12L);
        lesson.setCourseId(1L);
        lesson.setVideoFilePath("course-videos/1/demo.mp4");
        lesson.setVideoMimeType("video/mp4");

        CourseService courseService = mock(CourseService.class);
        when(courseService.getLesson(12L)).thenReturn(lesson);
        when(courseService.canViewLessonMedia(12L, 10L, "STUDENT")).thenReturn(true);

        CourseController controller = new CourseController(courseService);
        ReflectionTestUtils.setField(controller, "uploadDir", uploadDir.toString());

        ResponseEntity<?> response = controller.streamLesson(12L, "bytes=2-5", mediaRequest(10L, "STUDENT"));

        assertThat(response.getStatusCode().value()).isEqualTo(206);
        assertThat(response.getHeaders().getFirst("Content-Range")).isEqualTo("bytes 2-5/10");
        assertThat(response.getHeaders().getFirst("Accept-Ranges")).isEqualTo("bytes");
        assertThat(response.getHeaders().getContentLength()).isEqualTo(4);
    }

    @Test
    void streamLessonLimitsOpenEndedRangesToSmallChunks() throws Exception {
        Path uploadDir = Files.createTempDirectory("orep-course-video-range-test");
        Path video = uploadDir.resolve("course-videos/1/large.mp4");
        Files.createDirectories(video.getParent());
        Files.write(video, new byte[10 * 1024 * 1024]);

        CourseLesson lesson = new CourseLesson();
        lesson.setId(13L);
        lesson.setCourseId(1L);
        lesson.setVideoFilePath("course-videos/1/large.mp4");
        lesson.setVideoMimeType("video/mp4");

        CourseService courseService = mock(CourseService.class);
        when(courseService.getLesson(13L)).thenReturn(lesson);
        when(courseService.canViewLessonMedia(13L, 10L, "STUDENT")).thenReturn(true);

        CourseController controller = new CourseController(courseService);
        ReflectionTestUtils.setField(controller, "uploadDir", uploadDir.toString());

        ResponseEntity<?> response = controller.streamLesson(13L, "bytes=0-", mediaRequest(10L, "STUDENT"));

        assertThat(response.getStatusCode().value()).isEqualTo(206);
        assertThat(response.getHeaders().getFirst("Content-Range")).isEqualTo("bytes 0-8388607/10485760");
        assertThat(response.getHeaders().getContentLength()).isEqualTo(8L * 1024 * 1024);
    }

    @Test
    void lessonPlayUrlReturnsStaticUploadUrlForVideoService() {
        CourseLesson lesson = new CourseLesson();
        lesson.setId(14L);
        lesson.setCourseId(1L);
        lesson.setVideoFilePath("course-videos/1/demo.mp4");
        lesson.setVideoMimeType("video/mp4");

        CourseService courseService = mock(CourseService.class);
        when(courseService.getLesson(14L)).thenReturn(lesson);
        when(courseService.canViewLessonMedia(14L, 10L, "STUDENT")).thenReturn(true);

        CourseController controller = new CourseController(courseService);

        var response = controller.getLessonPlayUrl(14L, mediaRequest(10L, "STUDENT"));

        assertThat(response.getCode()).isEqualTo(200);
        assertThat(String.valueOf(response.getData())).contains("videoUrl=/uploads/course-videos/1/demo.mp4");
        assertThat(String.valueOf(response.getData())).contains("mimeType=video/mp4");
    }

    @Test
    void streamLessonHidesUnreadableLesson() throws Exception {
        CourseService courseService = mock(CourseService.class);
        when(courseService.canViewLessonMedia(12L, 11L, "STUDENT")).thenReturn(false);

        CourseController controller = new CourseController(courseService);
        ResponseEntity<?> response = controller.streamLesson(12L, "bytes=0-1", mediaRequest(11L, "STUDENT"));

        assertThat(response.getStatusCode().value()).isEqualTo(404);
    }

    @Test
    void lessonPlayUrlHidesUnreadableLesson() {
        CourseService courseService = mock(CourseService.class);
        when(courseService.canViewLessonMedia(14L, 11L, "STUDENT")).thenReturn(false);

        CourseController controller = new CourseController(courseService);
        var response = controller.getLessonPlayUrl(14L, mediaRequest(11L, "STUDENT"));

        assertThat(response.getCode()).isEqualTo(404);
    }

    @Test
    void uploadCourseCoverStoresImageAndReturnsPublicUrl() throws Exception {
        Path uploadDir = Files.createTempDirectory("orep-course-cover-test");
        Course updated = new Course();
        updated.setId(3L);
        updated.setCoverUrl("/uploads/course-covers/3/demo.webp");

        CourseService courseService = mock(CourseService.class);
        when(courseService.updateCourseCover(org.mockito.ArgumentMatchers.eq(3L), org.mockito.ArgumentMatchers.startsWith("/uploads/course-covers/3/"), org.mockito.ArgumentMatchers.eq(8L), org.mockito.ArgumentMatchers.eq("ADMIN"))).thenReturn(updated);

        AdminCourseController controller = new AdminCourseController(courseService);
        ReflectionTestUtils.setField(controller, "uploadDir", uploadDir.toString());
        MockMultipartFile file = new MockMultipartFile("file", "cover.webp", "image/webp", "cover".getBytes());
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", 8L);
        request.setAttribute("role", "ADMIN");

        var response = controller.uploadCourseCover(3L, file, request);

        assertThat(response.getCode()).isEqualTo(200);
        assertThat(String.valueOf(response.getData())).contains("/uploads/course-covers/3/");
        assertThat(Files.walk(uploadDir).filter(Files::isRegularFile).count()).isEqualTo(1);
    }

    @Test
    void uploadCourseCoverRejectsUnsupportedFileType() throws Exception {
        CourseService courseService = mock(CourseService.class);
        AdminCourseController controller = new AdminCourseController(courseService);
        MockMultipartFile file = new MockMultipartFile("file", "cover.gif", "image/gif", "cover".getBytes());
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", 8L);
        request.setAttribute("role", "ADMIN");

        var response = controller.uploadCourseCover(3L, file, request);

        assertThat(response.getCode()).isEqualTo(400);
        assertThat(response.getMessage()).contains("仅支持 jpg、jpeg、png、webp 图片");
    }

    @Test
    void movUploadsRequireWebPlaybackTranscode() {
        AdminCourseController controller = new AdminCourseController(mock(CourseService.class));

        boolean transcode = controller.shouldTranscodeForWebPlayback(Path.of("lesson.mov"), "mov");

        assertThat(transcode).isTrue();
    }

    private static MockHttpServletRequest mediaRequest(Long userId, String role) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", userId);
        request.setAttribute("role", role);
        return request;
    }
}
