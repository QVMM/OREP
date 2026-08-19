package com.orep.backend.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class IssueView {
    private Long id;
    private Long tenantId;
    private Long meetingId;
    private String meetingTitle;
    private Long teamId;
    private String teamName;
    private Long mentorId;
    private String mentorName;
    private Long scoreDetailId;
    private String category;
    private String title;
    private String description;
    private Long sourceUserId;
    private String reporterName;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime resolvedAt;
    private Long resolvedMeetingId;
}
