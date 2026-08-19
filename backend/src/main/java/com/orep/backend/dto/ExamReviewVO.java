package com.orep.backend.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ExamReviewVO {
    private Long attemptId;
    private Long paperId;
    private String paperTitle;
    private Long userId;
    private String status;
    private Integer score;
    private Integer totalScore;
    private LocalDateTime submittedAt;
    private List<AnswerItem> answers;

    @Data
    public static class AnswerItem {
        private Long answerId;
        private Long questionId;
        private String stem;
        private String referenceAnswerJson;
        private String studentAnswerJson;
        private Integer score;
        private Integer maxScore;
        private Boolean correct;
    }
}
