package com.orep.backend.controller;

import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.WebConfig;
import com.orep.backend.service.DocumentStoreUploadAccessService;
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
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = DocumentStoreUploadDownloadController.class)
@Import({DocumentStoreUploadDownloadController.class, WebConfig.class, AuthInterceptor.class})
@TestPropertySource(properties = "file.upload-dir=target/test-document-store-upload")
class DocumentStoreUploadDownloadWebMvcTest {
    @Autowired
    private MockMvc mvc;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @MockBean
    private DocumentStoreUploadAccessService accessService;

    @BeforeAll
    static void createFiles() throws Exception {
        Files.createDirectories(Path.of("target/test-document-store-upload/resource-center/3"));
        Files.writeString(Path.of("target/test-document-store-upload/resource-center/3/a.pdf"), "rc");
        Files.createDirectories(Path.of("target/test-document-store-upload/office/versions/9"));
        Files.writeString(Path.of("target/test-document-store-upload/office/versions/9/v1.pptx"), "off");
    }

    @Test
    void anonymousResourceCenterIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/resource-center/3/a.pdf"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void anonymousOfficeVersionIsUnauthorized() throws Exception {
        mvc.perform(get("/uploads/office/versions/9/v1.pptx"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void foreignResourceCenterIsHidden() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(11L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("刘旭");
        when(jwtUtil.getRole("valid-token")).thenReturn("STUDENT");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(3L);
        when(accessService.authorizeResourceCenter(eq("/uploads/resource-center/2/a.pdf"), eq(3L), eq(11L), eq("STUDENT")))
                .thenThrow(new ResponseStatusException(HttpStatus.NOT_FOUND, "文件不存在"));

        mvc.perform(get("/uploads/resource-center/2/a.pdf")
                        .header("Authorization", "Bearer valid-token"))
                .andExpect(status().isNotFound());
    }
}
