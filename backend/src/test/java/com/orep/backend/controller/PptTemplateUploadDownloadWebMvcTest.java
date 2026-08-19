package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.MonitorService;
import com.orep.backend.service.PptTemplateUploadAccessService;
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

@WebMvcTest(controllers = PptTemplateUploadDownloadController.class)
@Import({PptTemplateUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-ppt-template-upload")
class PptTemplateUploadDownloadWebMvcTest {
    private static final Path FILE = Path.of("target/test-ppt-template-upload/ppt-templates/demo.pdf");

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private PptTemplateUploadAccessService accessService;

    @BeforeAll
    static void createFile() throws Exception {
        Files.createDirectories(FILE.getParent());
        Files.writeString(FILE, "ppt-secret");
    }

    @Test
    void anonymousPptTemplateIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/ppt-templates/demo.pdf"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void loggedInUserCanDownload() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(10L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("李林峰");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(accessService.authorize(eq("/uploads/ppt-templates/demo.pdf"), eq(10L)))
                .thenReturn(FILE.toAbsolutePath().normalize());

        mvc.perform(get("/uploads/ppt-templates/demo.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isOk())
                .andExpect(content().string("ppt-secret"));
    }

    @Test
    void missingTemplateIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(accessService.authorize(eq("/uploads/ppt-templates/missing.pdf"), eq(11L)))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/ppt-templates/missing.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
