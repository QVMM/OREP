package com.orep.backend.dto;

import lombok.Data;

@Data
public class ExamQuestionRequest {
    private String questionType;
    private String stem;
    private String optionsJson;
    private String answerJson;
    private String analysis;
    private String category;
    private String difficulty;
    private Integer score;
    private String status;
}
