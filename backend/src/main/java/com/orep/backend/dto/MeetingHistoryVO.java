package com.orep.backend.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class MeetingHistoryVO {
    private Long meetingId;
    private String title;
    private String meetingCode;
    private String meetingPassword;
    private String joinCredential;
    private String status; // CREATED, RUNNING, ENDED
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private LocalDateTime meetingCreatedAt;

    // 当前用户的参与信息
    private LocalDateTime joinedAt;
    private LocalDateTime leftAt;
    private Integer durationSeconds; // 参与时长（秒）
}
