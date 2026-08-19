package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentTrainingService;
import com.orep.backend.service.TrainingDayLearningResourceService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentTrainingControllerTest {
    private final StudentTrainingService service = mock(StudentTrainingService.class);
    private final TrainingDayLearningResourceService learningService = mock(TrainingDayLearningResourceService.class);
    private final StudentTrainingController controller = new StudentTrainingController(
            service,
            learningService
    );

    @Test
    void currentUsesAuthenticatedTenantAndUser() {
        when(service.current(7L, 23L)).thenReturn(Map.of("hasCamp", true, "campId", 9L));
        MockHttpServletRequest request = authenticatedRequest();

        Result<Map<String, Object>> result = controller.current(request);

        assertEquals(200, result.getCode());
        assertEquals(9L, result.getData().get("campId"));
        verify(service).current(7L, 23L);
    }

    @Test
    void dayUsesPathIdAndAuthenticatedScope() {
        when(service.day(7L, 23L, 11L)).thenReturn(Map.of("dayId", 11L));
        MockHttpServletRequest request = authenticatedRequest();

        Result<Map<String, Object>> result = controller.day(11L, request);

        assertEquals(11L, result.getData().get("dayId"));
        verify(service).day(7L, 23L, 11L);
    }

    @Test
    void learningProgressUsesAuthenticatedScopeAndPayload() {
        when(learningService.recordVideoHeartbeat(7L, 23L, 41L, "session_12345678", 90, 240, false))
                .thenReturn(Map.of("id", 41L, "progressPercent", 36));
        MockHttpServletRequest request = authenticatedRequest();

        Result<Map<String, Object>> result = controller.updateLearningProgress(
                41L,
                Map.of(
                        "sessionId", "session_12345678",
                        "positionSeconds", 90,
                        "durationSeconds", 240,
                        "reset", false
                ),
                request
        );

        assertEquals(36, result.getData().get("progressPercent"));
        verify(learningService).recordVideoHeartbeat(7L, 23L, 41L, "session_12345678", 90, 240, false);
    }

    @Test
    void manualCompletionUsesAuthenticatedScope() {
        when(learningService.completeNonVideo(7L, 23L, 42L))
                .thenReturn(Map.of("id", 42L, "learningStatus", "COMPLETED"));
        MockHttpServletRequest request = authenticatedRequest();

        Result<Map<String, Object>> result = controller.completeLearningResource(42L, request);

        assertEquals("COMPLETED", result.getData().get("learningStatus"));
        verify(learningService).completeNonVideo(7L, 23L, 42L);
    }

    private MockHttpServletRequest authenticatedRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("tenantId", 7L);
        request.setAttribute("userId", 23L);
        return request;
    }
}
