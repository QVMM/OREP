package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.ChatUploadAccessService;
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

@WebMvcTest(controllers = ChatUploadDownloadController.class)
@Import({ChatUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-chat-upload-download")
class ChatUploadDownloadWebMvcTest {
    private static final Path FILE = Path.of("target/test-chat-upload-download/2026/06/27/a.docx");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private ChatUploadAccessService chatUploadAccessService;

    @BeforeAll
    static void createFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "chat-secret");
    }

    @Test
    void anonymousLegacyChatUploadIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/2026/06/27/a.docx"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void participantCanDownloadLegacyChatUpload() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(10L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("李林峰");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(chatUploadAccessService.authorize(eq("/uploads/2026/06/27/a.docx"), eq(10L)))
                .thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/2026/06/27/a.docx")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("chat-secret"));
    }

    @Test
    void foreignMeetingAttachmentIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(chatUploadAccessService.authorize(eq("/uploads/2026/06/27/a.docx"), eq(11L)))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/2026/06/27/a.docx")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
