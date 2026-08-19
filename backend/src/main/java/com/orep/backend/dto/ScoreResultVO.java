package com.orep.backend.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
public class ScoreResultVO {
    private Long meetingId;
    private String meetingTitle;
    private List<ScoreRecordVO> records;

    @Data
    public static class ScoreRecordVO {
        private Long userId;
        private String username;
        private String role;
        private BigDecimal totalScore;
        private LocalDateTime submittedAt;
        private List<ScoreDetailVO> details;
    }

    @Data
    public static class ScoreDetailVO {
        private String category;
        private String itemName;
        private BigDecimal maxScore;
        private BigDecimal score;
        private String comment;
    }
}
