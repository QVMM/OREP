package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PptTemplateUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private PptTemplateUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new PptTemplateUploadAccessService(uploadRoot.toString());
    }

    @Test
    void detectsTemplateFolder() {
        assertTrue(service.isProtectedPptTemplate("/uploads/ppt-templates/demo.pdf"));
        assertFalse(service.isProtectedPptTemplate("/uploads/course-covers/7/a.png"));
    }

    @Test
    void requiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/ppt-templates/demo.pdf", null));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void loggedInUserCanReadExistingTemplate() throws Exception {
        Path file = uploadRoot.resolve("ppt-templates/demo.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "template");

        Path authorized = service.authorize("/uploads/ppt-templates/demo.pdf", 10L);
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }

    @Test
    void missingTemplateIsNotFound() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/ppt-templates/missing.pdf", 10L));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }
}
