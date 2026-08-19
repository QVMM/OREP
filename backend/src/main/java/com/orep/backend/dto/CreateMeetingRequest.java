package com.orep.backend.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateMeetingRequest {
    @NotBlank(message = "会议标题不能为空")
    private String title;
    private Integer durationMinutes;
}
