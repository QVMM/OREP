package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CourseMaterialUploadAccessServiceTest {

    @TempDir
    Path uploadRoot;

    private final CourseService courseService = mock(CourseService.class);
    private CourseMaterialUploadAccessService service;

    @BeforeEach
    void setUp() {
        service = new CourseMaterialUploadAccessService(courseService, uploadRoot.toString());
    }

    @Test
    void detectsProtectedFolders() {
        assertTrue(service.isProtectedCourseMaterial("/uploads/course-videos/7/a.mp4"));
        assertTrue(service.isProtectedCourseMaterial("/uploads/course-attachments/7/a.pdf"));
        assertTrue(service.isProtectedCourseMaterial("/uploads/course-covers/7/a.png"));
        assertEquals(7L, CourseMaterialUploadAccessService.courseIdFromPath("/uploads/course-videos/7/a.mp4"));
        assertEquals(7L, CourseMaterialUploadAccessService.courseIdFromPath("/uploads/course-attachments/7/notes.pdf"));
        assertEquals(7L, CourseMaterialUploadAccessService.courseIdFromPath("/uploads/course-covers/7/a.png"));
    }

    @Test
    void requiresLogin() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/course-videos/7/a.mp4", null, "STUDENT"));
        assertEquals(HttpStatus.UNAUTHORIZED, error.getStatusCode());
    }

    @Test
    void publishedCourseAllowsLoggedInUser() throws Exception {
        Path file = uploadRoot.resolve("course-videos/7/a.mp4");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "video");
        when(courseService.canViewCourseMedia(7L, 10L, "STUDENT")).thenReturn(true);

        Path authorized = service.authorize("/uploads/course-videos/7/a.mp4", 10L, "STUDENT");
        assertEquals(file.toAbsolutePath().normalize(), authorized);
    }

    @Test
    void unpublishedCourseHidesNonViewer() throws Exception {
        Path file = uploadRoot.resolve("course-attachments/8/secret.pdf");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "secret");
        when(courseService.canViewCourseMedia(8L, 11L, "STUDENT")).thenReturn(false);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/course-attachments/8/secret.pdf", 11L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void unpublishedCoverHidesNonViewer() throws Exception {
        Path file = uploadRoot.resolve("course-covers/8/secret.png");
        Files.createDirectories(file.getParent());
        Files.writeString(file, "cover");
        when(courseService.canViewCourseMedia(8L, 11L, "STUDENT")).thenReturn(false);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/course-covers/8/secret.png", 11L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }

    @Test
    void missingFileIsNotFoundEvenWhenCourseIsReadable() {
        when(courseService.canViewCourseMedia(7L, 10L, "STUDENT")).thenReturn(true);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.authorize("/uploads/course-videos/7/missing.mp4", 10L, "STUDENT"));
        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
    }
}
