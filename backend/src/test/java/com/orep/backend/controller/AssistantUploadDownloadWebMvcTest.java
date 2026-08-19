package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.AssistantUploadAccessService;
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

@WebMvcTest(controllers = AssistantUploadDownloadController.class)
@Import({AssistantUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-assistant-upload-download")
class AssistantUploadDownloadWebMvcTest {
    private static final Path FILE = Path.of("target/test-assistant-upload-download/assistant/1/6/note.md");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private AssistantUploadAccessService assistantUploadAccessService;

    @BeforeAll
    static void createFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "assistant-secret");
    }

    @Test
    void anonymousAssistantUploadIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/assistant/1/6/note.md"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void ownerCanDownload() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(6L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("owner");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(1L);
        when(assistantUploadAccessService.authorize(eq("/uploads/assistant/1/6/note.md"), eq(1L), eq(6L)))
                .thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/assistant/1/6/note.md")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("assistant-secret"));
    }

    @Test
    void otherUserIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(1L);
        when(assistantUploadAccessService.authorize(eq("/uploads/assistant/1/6/note.md"), eq(1L), eq(11L)))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/assistant/1/6/note.md")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
