package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.AiScoreUploadAccessService;
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

@WebMvcTest(controllers = AiScoreUploadDownloadController.class)
@Import({AiScoreUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-ai-score-upload-download")
class AiScoreUploadDownloadWebMvcTest {
    private static final Path FILE = Path.of("target/test-ai-score-upload-download/ai-score/47/demo.mp4");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private AiScoreUploadAccessService aiScoreUploadAccessService;

    @BeforeAll
    static void createFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "score-secret");
    }

    @Test
    void anonymousAiScoreUploadIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/ai-score/47/demo.mp4"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void participantCanDownloadAfterSessionAccess() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(10L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("李林峰");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(aiScoreUploadAccessService.authorize(eq("/uploads/ai-score/47/demo.mp4"), eq(3L), eq(10L), eq("STUDENT")))
                .thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/ai-score/47/demo.mp4")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("score-secret"));
    }

    @Test
    void foreignSessionIsForbidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(aiScoreUploadAccessService.authorize(eq("/uploads/ai-score/9/demo.mp4"), eq(3L), eq(11L), eq("STUDENT")))
                .thenThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"));

        mvc.perform(get("/uploads/ai-score/9/demo.mp4")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isForbidden());
    }
}
