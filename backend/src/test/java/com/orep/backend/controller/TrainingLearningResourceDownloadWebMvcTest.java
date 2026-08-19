package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.MonitorService;
import com.orep.backend.service.TrainingDayLearningResourceService;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@WebMvcTest(controllers = TrainingLearningResourceDownloadController.class)
@Import({TrainingLearningResourceDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-controlled-learning-download")
class TrainingLearningResourceDownloadWebMvcTest {
    private static final Path FILE = Path.of(
            "target/test-controlled-learning-download/training/learning/51/document/demo.pdf"
    );
    private static final Path ARCHIVE = Path.of(
            "target/test-controlled-learning-download/training/learning/51/document/materials.zip"
    );

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private TrainingDayLearningResourceService learningService;

    @BeforeAll
    static void createLegacyLearningFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "private learning material");
        Files.writeString(ARCHIVE, "archive");
    }

    @Test
    void unauthenticatedLegacyLearningUrlIsNotServedByStaticHandler() throws Exception {
        mvc.perform(get("/uploads/training/learning/51/document/demo.pdf"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void authenticatedDownloadUsesControlledHandlerAndReturnsTheAuthorizedFile() throws Exception {
        authenticateAs("STUDENT");
        when(learningService.authorizeDownload(
                7L,
                23L,
                "STUDENT",
                "/uploads/training/learning/51/document/demo.pdf"
        )).thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/training/learning/51/document/demo.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("private learning material"));

        verify(learningService).authorizeDownload(
                7L,
                23L,
                "STUDENT",
                "/uploads/training/learning/51/document/demo.pdf"
        );
    }

    @Test
    void oldUrlStopsWorkingImmediatelyWhenTheDayIsRelocked() throws Exception {
        authenticateAs("STUDENT");
        when(learningService.authorizeDownload(eq(7L), eq(23L), eq("STUDENT"), anyString()))
                .thenThrow(new ResponseStatusException(org.springframework.http.HttpStatus.LOCKED));

        mvc.perform(get("/uploads/training/learning/51/document/demo.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isLocked());
    }

    @Test
    void archiveLearningResourceIsForcedToDownload() throws Exception {
        authenticateAs("STUDENT");
        when(learningService.authorizeDownload(
                7L,
                23L,
                "STUDENT",
                "/uploads/training/learning/51/document/materials.zip"
        )).thenReturn(ARCHIVE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/training/learning/51/document/materials.zip")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(header().string(
                        "Content-Disposition",
                        org.hamcrest.Matchers.startsWith("attachment;")
                ));
    }

    private void authenticateAs(String role) {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getRole("valid-token")).thenReturn(role);
        when(jwtUtil.getUserId("valid-token")).thenReturn(23L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("student");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(7L);
    }
}
