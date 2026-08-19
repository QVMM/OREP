package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.TeacherGrowthService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class TeacherGrowthControllerTest {

    @Test
    void teacherCanCreateCertificateWithinAuthenticatedTenant() {
        TeacherGrowthService service = mock(TeacherGrowthService.class);
        TeacherGrowthController controller = new TeacherGrowthController(service);
        MockHttpServletRequest request = request("TEACHER");
        Map<String, Object> body = Map.of("title", "训练进步之星");
        when(service.createCertificate(1L, 7L, body)).thenReturn(Map.of("id", 12L));

        Result<Map<String, Object>> result = controller.createCertificate(body, request);

        assertEquals(200, result.getCode());
        assertEquals(12L, result.getData().get("id"));
        verify(service).createCertificate(1L, 7L, body);
    }

    @Test
    void studentCannotPublishRectification() {
        TeacherGrowthController controller = new TeacherGrowthController(mock(TeacherGrowthService.class));
        assertThrows(ResponseStatusException.class, () -> controller.createRectification(Map.of(), request("STUDENT")));
    }

    private MockHttpServletRequest request(String role) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("tenantId", 1L);
        request.setAttribute("userId", 7L);
        request.setAttribute("role", role);
        return request;
    }
}
