package com.orep.backend.dto;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class UsernameLengthValidationTest {

    private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

    @Test
    void twoCharacterUsernameCanRegister() {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("李雷");
        request.setEmail("lilei@example.com");
        request.setCode("123456");
        request.setPassword("123456");

        assertTrue(validator.validate(request).isEmpty());
    }

    @Test
    void twoCharacterUsernameCanBeCreatedByAdmin() {
        AdminCreateUserRequest request = new AdminCreateUserRequest();
        request.setUsername("韩梅");
        request.setEmail("hanmei@example.com");
        request.setPassword("123456");
        request.setRole("STUDENT");

        assertTrue(validator.validate(request).isEmpty());
    }

    @Test
    void oneCharacterUsernameIsStillRejectedWhenCreatingAccount() {
        AdminCreateUserRequest request = new AdminCreateUserRequest();
        request.setUsername("李");
        request.setEmail("li@example.com");
        request.setPassword("123456");
        request.setRole("STUDENT");

        assertFalse(validator.validate(request).isEmpty());
    }

    @Test
    void loginDoesNotRejectTwoCharacterUsername() {
        LoginRequest request = new LoginRequest();
        request.setUsername("李雷");
        request.setPassword("123456");

        assertTrue(validator.validate(request).isEmpty());
    }
}
