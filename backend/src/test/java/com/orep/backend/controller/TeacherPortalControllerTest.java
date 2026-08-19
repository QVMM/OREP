package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.TeacherPortalService;
import com.orep.backend.service.TrainingDayContentService;
import com.orep.backend.service.TrainingDayLearningResourceService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TeacherPortalControllerTest {
    private final TeacherPortalService service = mock(TeacherPortalService.class);
    private final TeacherPortalController controller = new TeacherPortalController(
            service,
            mock(TrainingDayContentService.class),
            mock(TrainingDayLearningResourceService.class)
    );

    @Test
    void earlyUnlockDelegatesAuthenticatedTeacherScope() {
        when(service.earlyUnlockTrainingDay(7L, 23L, "TEACHER", 51L))
                .thenReturn(Map.of("dayId", 51L, "locked", false));

        Result<Map<String, Object>> result = controller.earlyUnlockDay(51L, authenticatedRequest());

        assertEquals(false, result.getData().get("locked"));
        verify(service).earlyUnlockTrainingDay(7L, 23L, "TEACHER", 51L);
    }

    @Test
    void automaticUnlockRestorationDelegatesAuthenticatedTeacherScope() {
        when(service.restoreAutomaticUnlock(7L, 23L, "TEACHER", 51L))
                .thenReturn(Map.of("dayId", 51L, "locked", true));

        Result<Map<String, Object>> result = controller.restoreAutomaticUnlock(51L, authenticatedRequest());

        assertEquals(true, result.getData().get("locked"));
        verify(service).restoreAutomaticUnlock(7L, 23L, "TEACHER", 51L);
    }

    @Test
    void campRescheduleDelegatesAuthenticatedTeacherScope() {
        Map<String, Object> payload = Map.of("startDate", "2026-07-27");
        when(service.rescheduleCamp(7L, 23L, "TEACHER", 31L, payload))
                .thenReturn(Map.of("campId", 31L, "startDate", "2026-07-27"));

        Result<Map<String, Object>> result = controller.rescheduleCamp(31L, payload, authenticatedRequest());

        assertEquals(31L, result.getData().get("campId"));
        verify(service).rescheduleCamp(7L, 23L, "TEACHER", 31L, payload);
    }

    @Test
    void campDeletionDelegatesAuthenticatedTeacherScope() {
        Map<String, Object> payload = Map.of("mode", "PURGE", "confirmationName", "第一阶段集训");
        when(service.deleteCamp(7L, 23L, "TEACHER", 31L, payload))
                .thenReturn(Map.of("campId", 31L, "mode", "PURGE"));

        Result<Map<String, Object>> result = controller.deleteCamp(31L, payload, authenticatedRequest());

        assertEquals("PURGE", result.getData().get("mode"));
        verify(service).deleteCamp(7L, 23L, "TEACHER", 31L, payload);
    }

    private MockHttpServletRequest authenticatedRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("tenantId", 7L);
        request.setAttribute("userId", 23L);
        request.setAttribute("role", "TEACHER");
        return request;
    }
}
