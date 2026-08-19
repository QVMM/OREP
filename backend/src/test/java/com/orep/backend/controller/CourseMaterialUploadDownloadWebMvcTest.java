package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.CourseMaterialUploadAccessService;
import com.orep.backend.service.MonitorService;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = CourseMaterialUploadDownloadController.class)
@Import({CourseMaterialUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-course-material-upload")
class CourseMaterialUploadDownloadWebMvcTest {
    private static final Path VIDEO = Path.of("target/test-course-material-upload/course-videos/7/a.mp4");
    private static final Path ATTACHMENT = Path.of("target/test-course-material-upload/course-attachments/7/a.pdf");
    private static final Path COVER = Path.of("target/test-course-material-upload/course-covers/7/a.png");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private CourseMaterialUploadAccessService accessService;

    @BeforeAll
    static void createFiles() throws Exception {
        Files.createDirectories(VIDEO.getParent());
        Files.writeString(VIDEO, "course-video");
        Files.createDirectories(ATTACHMENT.getParent());
        Files.writeString(ATTACHMENT, "course-pdf");
        Files.createDirectories(COVER.getParent());
        Files.writeString(COVER, "course-cover");
    }

    @Test
    void anonymousCourseVideoIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/course-videos/7/a.mp4"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void anonymousCourseAttachmentIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/course-attachments/7/a.pdf"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void loggedInViewerCanDownloadPublishedCourseVideo() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(10L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("李林峰");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(accessService.authorize(eq("/uploads/course-videos/7/a.mp4"), eq(10L), eq("STUDENT")))
                .thenReturn(VIDEO.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/course-videos/7/a.mp4")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("course-video"));
    }

    @Test
    void anonymousCourseCoverIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/course-covers/7/a.png"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void unpublishedCourseIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(accessService.authorize(eq("/uploads/course-attachments/8/secret.pdf"), eq(11L), eq("STUDENT")))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/course-attachments/8/secret.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
