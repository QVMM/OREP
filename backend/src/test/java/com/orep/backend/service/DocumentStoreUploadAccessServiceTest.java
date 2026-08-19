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
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DocumentStoreUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private DocumentStoreUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new DocumentStoreUploadAccessService(jdbc, uploadRoot.toString());
    }

    @Test
    void detectsProtectedFolders() {
        assertTrue(service.isProtectedResourceCenterUpload("/uploads/resource-center/3/a.pdf"));
        assertTrue(service.isProtectedOfficeVersionUpload("/uploads/office/versions/9/v1.pptx"));
        assertEquals(3L, DocumentStoreUploadAccessService.firstNumericSegment(
                "/uploads/resource-center/3/a.pdf", "/uploads/resource-center/"));
    }

    @Test
    void resourceCenterRequiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorizeResourceCenter("/uploads/resource-center/3/a.pdf", 3L, null, "STUDENT"));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void resourceCenterHidesForeignTeam() throws Exception {
        Path file = uploadRoot.resolve("resource-center/2/a.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "secret");
        when(jdbc.queryForObject("SELECT COUNT(*) FROM project_team WHERE id = ? AND tenant_id = ?",
                Integer.class, 2L, 3L)).thenReturn(1);
        when(jdbc.queryForObject("SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?",
                Integer.class, 2L, 10L)).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorizeResourceCenter("/uploads/resource-center/2/a.pdf", 3L, 10L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void officeVersionAllowsOwner() throws Exception {
        Path file = uploadRoot.resolve("office/versions/9/v1.pptx");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "deck");
        when(jdbc.queryForList(eq("""
                SELECT owner_user_id AS ownerUserId, team_id AS teamId, scope, status
                FROM inspire_office_document
                WHERE id = ?
                """), eq(9L))).thenReturn(List.of(Map.of(
                "ownerUserId", 10L,
                "teamId", 3L,
                "scope", "personal",
                "status", "active"
        )));

        Path authorized = service.authorizeOfficeVersion("/uploads/office/versions/9/v1.pptx", 10L);
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }

    @Test
    void officeVersionHidesNonMember() throws Exception {
        Path file = uploadRoot.resolve("office/versions/9/v1.pptx");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "deck");
        when(jdbc.queryForList(eq("""
                SELECT owner_user_id AS ownerUserId, team_id AS teamId, scope, status
                FROM inspire_office_document
                WHERE id = ?
                """), eq(9L))).thenReturn(List.of(Map.of(
                "ownerUserId", 1L,
                "teamId", 1L,
                "scope", "team",
                "status", "active"
        )));
        when(jdbc.queryForObject("SELECT COUNT(*) FROM project_team_member WHERE team_id = ? AND user_id = ?",
                Integer.class, 1L, 11L)).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorizeOfficeVersion("/uploads/office/versions/9/v1.pptx", 11L));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }
}
