package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
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
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private final AiScoringSessionService sessions = mock(AiScoringSessionService.class);
    private final AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
    private AiScoreUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new AiScoreUploadAccessService(sessions, access, uploadRoot.toString());
    }

    @Test
    void detectsAiScoreFolderAndParsesSessionId() {
        assertTrue(service.isProtectedAiScoreUpload("/uploads/ai-score/47/roadshow.mp4"));
        assertFalse(service.isProtectedAiScoreUpload("/uploads/task/instructions/1/a.pdf"));
        assertEquals(47L, AiScoreUploadAccessService.sessionIdFromPath("/uploads/ai-score/47/a.mp4"));
        assertEquals(null, AiScoreUploadAccessService.sessionIdFromPath("/uploads/ai-score/not-a-session/a.mp4"));
    }

    @Test
    void authorizeRequiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/ai-score/47/a.mp4", 3L, null, "STUDENT"));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void authorizeRejectsCrossTeamUser() throws Exception {
        Path file = uploadRoot.resolve("ai-score/9/demo.mp4");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "secret");
        AiScoringSession session = new AiScoringSession();
        session.setId(9L);
        session.setTeamId(1L);
        when(sessions.requireSessionForAccess(9L)).thenReturn(session);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertSessionAccess(eq(session), eq(3L), eq(11L), eq("STUDENT"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/ai-score/9/demo.mp4", 3L, 11L, "STUDENT"));
        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
    }

    @Test
    void authorizeAllowsTeamMember() throws Exception {
        Path file = uploadRoot.resolve("ai-score/47/demo.mp4");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "ok");
        AiScoringSession session = new AiScoringSession();
        session.setId(47L);
        session.setTeamId(3L);
        when(sessions.requireSessionForAccess(47L)).thenReturn(session);

        Path authorized = service.authorize("/uploads/ai-score/47/demo.mp4?t=token", 3L, 10L, "STUDENT");
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }
}
