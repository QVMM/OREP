package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.MonitorService;
import com.orep.backend.service.TaskInstructionUploadAccessService;
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

@WebMvcTest(controllers = TaskInstructionUploadDownloadController.class)
@Import({TaskInstructionUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-task-instruction-upload")
class TaskInstructionUploadDownloadWebMvcTest {
    private static final Path FILE = Path.of("target/test-task-instruction-upload/task/instructions/23/images/a.jpg");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private TaskInstructionUploadAccessService accessService;

    @BeforeAll
    static void createFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "task-image");
    }

    @Test
    void anonymousInstructionImageIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/task/instructions/23/images/a.jpg"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void enrolledStudentCanDownload() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(10L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("李林峰");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(1L);
        when(accessService.authorize(
                eq("/uploads/task/instructions/23/images/a.jpg"), eq(1L), eq(10L), eq("STUDENT")))
                .thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/task/instructions/23/images/a.jpg")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("task-image"));
    }

    @Test
    void foreignStudentIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(1L);
        when(accessService.authorize(
                eq("/uploads/task/instructions/23/images/a.jpg"), eq(1L), eq(11L), eq("STUDENT")))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/task/instructions/23/images/a.jpg")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
