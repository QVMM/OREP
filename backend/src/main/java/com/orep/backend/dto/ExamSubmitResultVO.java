package com.orep.backend.dto;

import lombok.Data;

import java.util.List;

@Data
public class ExamSubmitResultVO {
    private Long attemptId;
    private Integer score;
    private Integer totalScore;
    private Integer correctCount;
    private Integer questionCount;
    private Boolean passed;
    private Boolean manualReviewRequired;
    private Integer manualQuestionCount;
    private List<WrongQuestion> wrongQuestions;

    @Data
    public static class WrongQuestion {
        private Long questionId;
        private String stem;
        private String analysis;
        private String answerJson;
    }
}
