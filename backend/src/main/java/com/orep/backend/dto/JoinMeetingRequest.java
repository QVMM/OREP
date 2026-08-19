package com.orep.backend.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class JoinMeetingRequest {
    @NotBlank(message = "会议号不能为空")
    private String meetingCode;

    @NotBlank(message = "入会密码不能为空")
    private String password;
}
