package com.orep.backend.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class MeetingDetailVO {
    // 会议基本信息
    private Long meetingId;
    private String title;
    private String meetingCode;
    private String status;
    private LocalDateTime startTime;
    private LocalDateTime endTime;

    // 当前用户的参与信息
    private LocalDateTime joinedAt;
    private LocalDateTime leftAt;
    private Integer durationSeconds;

    // 聊天记录
    private List<ChatRecord> chatMessages;

    // 评分结果
    private BigDecimal totalScore;
    private List<ScoreItemRecord> scoreDetails;

    // 存在问题
    private List<IssueRecord> issues;

    @Data
    public static class ChatRecord {
        private Long id;
        private String senderName;
        private String content;
        private String messageType;
        private String fileName;
        private LocalDateTime createdAt;
    }

    @Data
    public static class ScoreItemRecord {
        private String category;
        private String itemName;
        private BigDecimal maxScore;
        private BigDecimal score;
        private String comment;
    }

    @Data
    public static class IssueRecord {
        private Long id;
        private String category;
        private String description;
        private Integer status; // 0=待解决, 1=已解决
        private LocalDateTime createdAt;
        private LocalDateTime resolvedAt;
    }
}
