package com.orep.backend.dto;

import lombok.Data;

import java.util.List;

@Data
public class ExamPaperRequest {
    private String title;
    private String description;
    private Integer durationMinutes;
    private Integer passScore;
    private String status;
    private Boolean shuffleQuestions;
    private Boolean shuffleOptions;
    private Boolean antiCheatEnabled;
    private List<QuestionConfig> questions;

    @Data
    public static class QuestionConfig {
        private Long questionId;
        private Integer score;
        private Integer sortOrder;
    }
}
