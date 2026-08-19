package com.orep.backend.dto;

import lombok.Data;

@Data
public class LoginResponse {
    private String token;
    private UserInfo user;

    @Data
    public static class UserInfo {
        private Long id;
        private String username;
        private String email;
        private String role;
        private Long tenantId;
    }
}
