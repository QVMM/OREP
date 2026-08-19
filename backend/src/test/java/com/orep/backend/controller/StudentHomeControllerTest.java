package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentHomeService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class StudentHomeControllerTest {
    @Test
    void homeUsesAuthenticatedScope() {
        StudentHomeService service = mock(StudentHomeService.class);
        StudentHomeController controller = new StudentHomeController(service);
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("tenantId", 5L);
        request.setAttribute("userId", 17L);
        when(service.home(5L, 17L)).thenReturn(Map.of("serverTime", "2026-07-20T12:00:00"));

        Result<Map<String, Object>> result = controller.home(request);

        assertEquals(200, result.getCode());
        assertEquals("2026-07-20T12:00:00", result.getData().get("serverTime"));
        verify(service).home(5L, 17L);
    }
}
