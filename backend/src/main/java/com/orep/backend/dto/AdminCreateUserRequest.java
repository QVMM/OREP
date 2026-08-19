package com.orep.backend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

@Data
public class AdminCreateUserRequest {
    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 20, message = "用户名长度2-20")
    private String username;

    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 30, message = "密码长度6-30")
    private String password;

    @NotBlank(message = "角色不能为空")
    private String role;

    private Long tenantId;

    private Long schoolId;

    private Long collegeId;

    private Long classId;

    private List<Long> groupIds;
}
