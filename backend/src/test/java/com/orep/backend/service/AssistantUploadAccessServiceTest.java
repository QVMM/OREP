package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AssistantUploadAccessServiceTest {

    private static final String OWNER_SQL = """
                SELECT COUNT(1)
                FROM ai_assistant_session
                WHERE id = ? AND tenant_id = ? AND user_id = ? AND status <> 'deleted'
                """;

    @TempDir
    Path uploadRoot;

    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private AssistantUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new AssistantUploadAccessService(jdbc, uploadRoot.toString());
    }

    @Test
    void detectsAssistantFolderAndParsesIds() {
        assertTrue(service.isProtectedAssistantUpload("/uploads/assistant/1/6/note.md"));
        assertFalse(service.isProtectedAssistantUpload("/uploads/ai-score/47/a.mp4"));
        assertEquals(1L, AssistantUploadAccessService.idsFromPath("/uploads/assistant/1/6/note.md").tenantId());
        assertEquals(6L, AssistantUploadAccessService.idsFromPath("/uploads/assistant/1/6/note.md").sessionId());
        assertNull(AssistantUploadAccessService.idsFromPath("/uploads/assistant/x/6/note.md"));
    }

    @Test
    void authorizeRequiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/assistant/1/6/note.md", 1L, null));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void authorizeHidesOtherUsersSession() throws Exception {
        Path file = uploadRoot.resolve("assistant/1/6/note.md");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "secret plan");
        when(jdbc.queryForObject(OWNER_SQL, Integer.class, 6L, 1L, 11L)).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/assistant/1/6/note.md", 1L, 11L));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void authorizeAllowsSessionOwner() throws Exception {
        Path file = uploadRoot.resolve("assistant/1/6/note.md");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "ok");
        when(jdbc.queryForObject(OWNER_SQL, Integer.class, 6L, 1L, 6L)).thenReturn(1);

        Path authorized = service.authorize("/uploads/assistant/1/6/note.md?t=token", 1L, 6L);
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }
}
