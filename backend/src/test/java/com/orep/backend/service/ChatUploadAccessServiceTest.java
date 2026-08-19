package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ChatUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private final AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
    private ChatUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new ChatUploadAccessService(jdbc, access, uploadRoot.toString());
    }

    @Test
    void detectsLegacyDateAndChatFolders() {
        assertTrue(service.isProtectedChatUpload("/uploads/2026/06/27/a.docx"));
        assertTrue(service.isProtectedChatUpload("/uploads/chat/files/2026/06/27/a.pdf"));
        assertFalse(service.isProtectedChatUpload("/uploads/task/instructions/1/a.pdf"));
        assertFalse(service.isProtectedChatUpload("/uploads/banners/home.png"));
    }

    @Test
    void authorizeRequiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/2026/06/27/a.docx", null));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void authorizeHidesForeignMeetingAttachment() throws Exception {
        Path file = uploadRoot.resolve("2026/06/27/a.docx");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "secret");
        when(jdbc.queryForList(eq("SELECT meeting_id FROM chat_message WHERE content = ? ORDER BY id DESC LIMIT 1"),
                eq(Long.class), eq("/uploads/2026/06/27/a.docx"))).thenReturn(List.of(20L));
        when(access.hasMeetingParticipantAccess(20L, 11L)).thenReturn(false);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/2026/06/27/a.docx", 11L));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void authorizeAllowsMeetingParticipant() throws Exception {
        Path file = uploadRoot.resolve("2026/06/27/a.docx");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "ok");
        when(jdbc.queryForList(eq("SELECT meeting_id FROM chat_message WHERE content = ? ORDER BY id DESC LIMIT 1"),
                eq(Long.class), eq("/uploads/2026/06/27/a.docx"))).thenReturn(List.of(20L));
        when(access.hasMeetingParticipantAccess(20L, 10L)).thenReturn(true);

        Path authorized = service.authorize("/uploads/2026/06/27/a.docx?t=token", 10L);
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }
}
