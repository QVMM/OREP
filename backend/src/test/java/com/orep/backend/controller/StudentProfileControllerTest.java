package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentProfileService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentProfileControllerTest {

    @Test
    void dashboardUsesAuthenticatedScope() {
        StudentProfileService service = mock(StudentProfileService.class);
        StudentProfileController controller = new StudentProfileController(service);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("tenantId", 3L);
        request.setAttribute("userId", 9L);
        when(service.dashboard(3L, 9L)).thenReturn(Map.of("serverDate", "2026-07-20"));

        Result<Map<String, Object>> result = controller.dashboard(request);

        assertEquals(200, result.getCode());
        assertEquals("2026-07-20", result.getData().get("serverDate"));
        verify(service).dashboard(3L, 9L);
    }
}
