package com.orep.backend.service;

import com.orep.backend.entity.Resource;
import com.orep.backend.mapper.ResourceMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.util.Date;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ResourceCenterServiceTest {
    private ResourceMapper mapper;
    private JdbcTemplate jdbc;
    private ResourceCenterService service;

    @BeforeEach
    void setUp() {
        mapper = mock(ResourceMapper.class);
        jdbc = mock(JdbcTemplate.class);
        service = new ResourceCenterService(mapper, jdbc);
    }

    @Test
    void workspaceRejectsUserOutsideTeam() {
        when(jdbc.queryForObject(
                anyString(), eq(Integer.class), eq(3L), eq(7L)
        )).thenReturn(1);
        when(jdbc.queryForObject(
                anyString(), eq(Integer.class), eq(3L), eq(21L)
        )).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.workspace(3L, 7L, 21L, "STUDENT"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        verify(mapper, never()).findByTeamId(3L);
    }

    @Test
    void workspaceSeparatesTeamFilesFromReadOnlyPublicFiles() {
        stubTeamMemberAccess();
        Resource teamFile = resource(11, 3L, "team", "项目说明.docx");
        Resource publicFile = resource(12, null, "public", "评分规则.pdf");
        when(mapper.findByTeamId(3L)).thenReturn(List.of(teamFile));
        when(mapper.findPublic()).thenReturn(List.of(publicFile));
        when(jdbc.queryForList(anyString(), eq(3L))).thenReturn(List.of());

        Map<String, Object> result = service.workspace(3L, 7L, 21L, "STUDENT");

        List<?> teamFiles = (List<?>) result.get("teamFiles");
        List<?> publicFiles = (List<?>) result.get("publicFiles");
        assertEquals(1, teamFiles.size());
        assertEquals(1, publicFiles.size());
        assertFalse(Boolean.TRUE.equals(((Map<?, ?>) teamFiles.get(0)).get("public")));
        assertTrue(Boolean.TRUE.equals(((Map<?, ?>) publicFiles.get(0)).get("public")));
        assertEquals("public", ((Map<?, ?>) publicFiles.get(0)).get("folderKey"));
    }

    @Test
    void publicResourceCannotBeDeleted() {
        stubTeamMemberAccess();
        when(mapper.findById(12)).thenReturn(resource(12, null, "public", "评分规则.pdf"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.deleteFile(12, 3L, 7L, 21L, "STUDENT"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        verify(mapper, never()).deleteByIdAndTeamId(eq(12), eq(3L));
    }

    @Test
    void teamFileCanBeDeleted() {
        stubTeamMemberAccess();
        Resource teamFile = resource(11, 3L, "root", "未归类.docx");
        teamFile.setFilePath("uploads/resource-center/3/abc.docx");
        when(mapper.findById(11)).thenReturn(teamFile);
        when(mapper.deleteByIdAndTeamId(11, 3L)).thenReturn(1);

        service.deleteFile(11, 3L, 7L, 21L, "STUDENT");

        verify(mapper).deleteByIdAndTeamId(11, 3L);
    }

    @Test
    void publicResourceCannotBeMoved() {
        stubTeamMemberAccess();
        when(mapper.findById(12)).thenReturn(resource(12, null, "public", "评分规则.pdf"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.moveFile(12, 3L, 7L, 21L, "STUDENT", "team"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        verify(mapper, never()).moveToCategory(12, 3L, "team");
    }

    @Test
    void resourceCannotMoveAcrossTeams() {
        stubTeamMemberAccess();
        when(mapper.findById(13)).thenReturn(resource(13, 8L, "root", "其他团队资料.pdf"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.moveFile(13, 3L, 7L, 21L, "STUDENT", "team"));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        verify(mapper, never()).moveToCategory(13, 3L, "team");
    }

    @Test
    void sameTeamResourceMovesIntoSystemFolder() {
        stubTeamMemberAccess();
        Resource before = resource(14, 3L, "root", "路演材料.pptx");
        Resource after = resource(14, 3L, "content", "路演材料.pptx");
        when(mapper.findById(14)).thenReturn(before, after);
        when(mapper.moveToCategory(14, 3L, "content")).thenReturn(1);

        Map<String, Object> result = service.moveFile(
                14, 3L, 7L, 21L, "STUDENT", "content");

        assertEquals("content", result.get("folderKey"));
        verify(mapper).moveToCategory(14, 3L, "content");
    }

    @Test
    void nonEmptyCustomFolderCannotBeDeleted() {
        stubTeamMemberAccess();
        when(jdbc.queryForList(
                anyString(), eq(88L), eq(3L)
        )).thenReturn(List.of(Map.of("key", "folder_demo")));
        when(jdbc.queryForObject(
                anyString(), eq(Integer.class), eq(3L), eq("folder_demo")
        )).thenReturn(2);

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.deleteFolder(88L, 3L, 7L, 21L, "STUDENT"));

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        verify(jdbc, never()).update(
                "DELETE FROM resource_category WHERE id = ? AND team_id = ?",
                88L,
                3L
        );
    }

    private void stubTeamMemberAccess() {
        when(jdbc.queryForObject(
                anyString(), eq(Integer.class), eq(3L), eq(7L)
        )).thenReturn(1);
        when(jdbc.queryForObject(
                anyString(), eq(Integer.class), eq(3L), eq(21L)
        )).thenReturn(1);
    }

    private Resource resource(int id, Long teamId, String category, String name) {
        Resource resource = new Resource();
        resource.setId(id);
        resource.setTeamId(teamId);
        resource.setCategory(category);
        resource.setName(name);
        resource.setExt(name.substring(name.lastIndexOf('.') + 1));
        resource.setFileSize(1024L);
        resource.setFilePath("uploads/resource-center/3/demo");
        resource.setCreatedAt(new Date());
        resource.setUpdatedAt(new Date());
        return resource;
    }
}
