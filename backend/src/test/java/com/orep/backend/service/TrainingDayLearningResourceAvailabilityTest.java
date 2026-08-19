package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TrainingDayLearningResourceAvailabilityTest {
    private JdbcTemplate jdbc;
    private TrainingDayLearningResourceService service;

    @TempDir
    Path uploadRoot;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        service = new TrainingDayLearningResourceService(
                jdbc,
                new ObjectMapper(),
                uploadRoot.toString(),
                new TrainingDayAvailabilityService()
        );
    }

    @Test
    void enumeratedVideoResourceIdCannotBypassFutureDayLock() {
        stubStudentResourceAccess("PUBLISHED", LocalDate.of(2099, 1, 2), "VIDEO");

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.recordVideoHeartbeat(
                        7L, 23L, 61L, "session_12345678", 10, 120, false
                )
        );

        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, never()).queryForList(contains("resource_url resourceUrl"), any(Object[].class));
    }

    @Test
    void enumeratedDocumentResourceIdCannotBeCompletedForDraftDay() {
        stubStudentResourceAccess("DRAFT", LocalDate.of(2026, 7, 24), "DOCUMENT");

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.completeNonVideo(7L, 23L, 61L)
        );

        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, never()).update(contains("training_learning_progress"), any(Object[].class));
        verify(jdbc, never()).queryForList(contains("resource_url resourceUrl"), any(Object[].class));
    }

    @Test
    void dayResourceDetailsDoNotExposeResourceUrlWhileDayIsLocked() {
        stubStudentResourceAccess("PUBLISHED", LocalDate.of(2099, 1, 2), "DOCUMENT");

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.studentResources(7L, 23L, 51L)
        );

        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, never()).queryForList(contains("resource_url resourceUrl"), any(Object[].class));
    }

    @Test
    void controlledDownloadRejectsPathTraversalBeforeDatabaseLookup() {
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.authorizeDownload(
                        7L,
                        23L,
                        "STUDENT",
                        "/uploads/training/learning/51/document/../secret.pdf"
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        verify(jdbc, never()).queryForList(anyString(), any(Object[].class));
    }

    @Test
    void controlledDownloadMatchesExactDatabaseUrlAndStopsAfterRelock() throws Exception {
        Path file = uploadRoot.resolve("training/learning/51/document/demo.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "private");
        Map<String, Object> open = downloadableResource("PUBLISHED", LocalDate.of(2026, 7, 1));
        Map<String, Object> relocked = downloadableResource("DRAFT", LocalDate.of(2026, 7, 1));
        when(jdbc.queryForList(contains("r.resource_url = ?"), any(Object[].class)))
                .thenReturn(List.of(open), List.of(relocked));
        when(jdbc.queryForObject(contains("project_team_member"), eq(Integer.class), any(Object[].class)))
                .thenReturn(1);

        Path authorized = service.authorizeDownload(
                7L,
                23L,
                "STUDENT",
                "/uploads/training/learning/51/document/demo.pdf"
        );
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.authorizeDownload(
                        7L,
                        23L,
                        "STUDENT",
                        "/uploads/training/learning/51/document/demo.pdf"
                )
        );

        assertEquals(file.toAbsolutePath().normalize(), authorized);
        assertTrue(Files.isRegularFile(authorized));
        assertEquals(HttpStatus.LOCKED, error.getStatusCode());
        verify(jdbc, org.mockito.Mockito.times(2)).queryForList(
                contains("r.resource_url = ?"),
                eq(7L),
                eq("/uploads/training/learning/51/document/demo.pdf")
        );
    }

    @Test
    void controlledDownloadRejectsTeacherWhoDoesNotCoverEveryActiveCampTeam() throws Exception {
        Path file = uploadRoot.resolve("training/learning/51/document/demo.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "private");
        when(jdbc.queryForList(contains("r.resource_url = ?"), any(Object[].class)))
                .thenReturn(List.of(downloadableResource("PUBLISHED", LocalDate.of(2026, 7, 1))));
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            return sql.contains("FROM training_camp_team")
                    ? List.of(101L, 102L)
                    : List.of(101L);
        });

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.authorizeDownload(
                        7L,
                        88L,
                        "TEACHER",
                        "/uploads/training/learning/51/document/demo.pdf"
                )
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
    }

    @Test
    void partialTeacherCannotCreateLearningResourceForSharedCamp() {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                .thenReturn(1);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            return sql.contains("FROM training_camp_team")
                    ? List.of(101L, 102L)
                    : List.of(101L);
        });
        when(jdbc.queryForList(contains("FROM training_day d"), any(Object[].class)))
                .thenReturn(List.of(Map.of("campId", 31L)));

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.createLink(
                        7L,
                        88L,
                        "TEACHER",
                        51L,
                        Map.of("title", "共享资料", "url", "https://example.com/resource")
                )
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
    }

    @Test
    void partialTeacherCanStillReadLearningResourceMetadataForOwnTeamScope() {
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                .thenReturn(1);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            return sql.contains("FROM training_camp_team")
                    ? List.of(101L, 102L)
                    : List.of(101L);
        });
        when(jdbc.queryForList(contains("FROM training_day d"), any(Object[].class)))
                .thenReturn(List.of(Map.of("campId", 31L)));

        assertDoesNotThrow(() ->
                service.teacherResources(7L, 88L, "TEACHER", 51L)
        );
    }

    private Map<String, Object> downloadableResource(String status, LocalDate trainingDate) {
        Map<String, Object> resource = new LinkedHashMap<>();
        resource.put("id", 61L);
        resource.put("dayId", 51L);
        resource.put("campId", 31L);
        resource.put("resourceStatus", "ACTIVE");
        resource.put("resourceUrl", "/uploads/training/learning/51/document/demo.pdf");
        resource.put("trainingDate", trainingDate);
        resource.put("status", status);
        return resource;
    }

    private void stubStudentResourceAccess(String status, LocalDate trainingDate, String resourceType) {
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("training_day d")) {
                return List.of(Map.of(
                        "id", 61L,
                        "dayId", 51L,
                        "resourceType", resourceType,
                        "trainingDate", trainingDate,
                        "status", status
                ));
            }
            if (sql.contains("resource_url resourceUrl")) {
                return List.of(new java.util.LinkedHashMap<>(Map.of(
                        "id", 61L,
                        "dayId", 51L,
                        "resourceType", resourceType,
                        "resourceUrl", "/uploads/private-resource.pdf"
                )));
            }
            return List.of();
        });
    }
}
