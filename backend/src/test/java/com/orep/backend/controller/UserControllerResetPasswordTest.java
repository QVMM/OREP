package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.UserService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class UserControllerResetPasswordTest {

    @Test
    void resetPasswordUsesAuthenticatedOperatorAndTargetId() {
        UserService userService = mock(UserService.class);
        UserController controller = new UserController();
        ReflectionTestUtils.setField(controller, "userService", userService);

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", 99L);
        request.setAttribute("role", "ADMIN");
        request.setAttribute("tenantId", 1L);

        Result<Void> result = controller.resetPassword(11L, request);

        assertEquals(200, result.getCode());
        verify(userService).resetUserPassword(11L, 99L, "ADMIN", 1L);
    }
}
