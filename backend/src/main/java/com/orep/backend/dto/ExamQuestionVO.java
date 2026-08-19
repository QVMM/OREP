package com.orep.backend.dto;

import lombok.Data;

@Data
public class ExamQuestionVO {
    private Long id;
    private String questionType;
    private String stem;
    private String optionsJson;
    private String answerJson;
    private String analysis;
    private String category;
    private String difficulty;
    private Integer score;
    private String status;
    private Boolean favorite;
}
