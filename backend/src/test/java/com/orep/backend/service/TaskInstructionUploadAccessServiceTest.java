package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TaskInstructionUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private final JdbcTemplate jdbc = mock(JdbcTemplate.class);
    private TaskInstructionUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new TaskInstructionUploadAccessService(
                jdbc, new TrainingDayAvailabilityService(), uploadRoot.toString());
    }

    @Test
    void detectsInstructionFolder() {
        assertTrue(service.isProtectedTaskInstruction("/uploads/task/instructions/23/images/a.jpg"));
        assertFalse(service.isProtectedTaskInstruction("/uploads/training/learning/23/video/a.mp4"));
        assertEquals(23L, TaskInstructionUploadAccessService.dayIdFromPath(
                "/uploads/task/instructions/23/images/a.jpg"));
    }

    @Test
    void requiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/task/instructions/23/images/a.jpg", 1L, null, "STUDENT"));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void studentOnPublishedDayCanRead() throws Exception {
        Path file = uploadRoot.resolve("task/instructions/23/images/a.jpg");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "img");
        stubDay(23L, "PUBLISHED", LocalDate.now().minusDays(1));
        when(jdbc.queryForObject(org.mockito.ArgumentMatchers.contains("project_team_member tm"),
                org.mockito.ArgumentMatchers.eq(Integer.class),
                org.mockito.ArgumentMatchers.eq(1L),
                org.mockito.ArgumentMatchers.eq(10L),
                org.mockito.ArgumentMatchers.eq(23L))).thenReturn(1);

        Path authorized = service.authorize("/uploads/task/instructions/23/images/a.jpg", 1L, 10L, "STUDENT");
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }

    @Test
    void studentOnDraftDayIsHidden() throws Exception {
        Path file = uploadRoot.resolve("task/instructions/23/images/a.jpg");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "img");
        stubDay(23L, "DRAFT", LocalDate.now());
        when(jdbc.queryForObject(org.mockito.ArgumentMatchers.contains("project_team_member tm"),
                org.mockito.ArgumentMatchers.eq(Integer.class),
                org.mockito.ArgumentMatchers.eq(1L),
                org.mockito.ArgumentMatchers.eq(10L),
                org.mockito.ArgumentMatchers.eq(23L))).thenReturn(1);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/task/instructions/23/images/a.jpg", 1L, 10L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void foreignStudentIsHidden() throws Exception {
        Path file = uploadRoot.resolve("task/instructions/23/images/a.jpg");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "img");
        stubDay(23L, "PUBLISHED", LocalDate.now().minusDays(1));
        when(jdbc.queryForObject(org.mockito.ArgumentMatchers.contains("project_team_member tm"),
                org.mockito.ArgumentMatchers.eq(Integer.class),
                org.mockito.ArgumentMatchers.eq(1L),
                org.mockito.ArgumentMatchers.eq(11L),
                org.mockito.ArgumentMatchers.eq(23L))).thenReturn(0);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/task/instructions/23/images/a.jpg", 1L, 11L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    private void stubDay(long dayId, String status, LocalDate trainingDate) {
        when(jdbc.queryForList(org.mockito.ArgumentMatchers.contains("training_date"),
                org.mockito.ArgumentMatchers.eq(1L),
                org.mockito.ArgumentMatchers.eq(dayId)))
                .thenReturn(List.of(Map.of(
                        "status", status,
                        "trainingDate", trainingDate,
                        "earlyUnlockedAt", new Object()
                )));
    }
}
