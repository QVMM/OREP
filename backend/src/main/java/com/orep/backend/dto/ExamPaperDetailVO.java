package com.orep.backend.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ExamPaperDetailVO {
    private Long id;
    private String title;
    private String description;
    private Integer durationMinutes;
    private Integer passScore;
    private String status;
    private Boolean shuffleQuestions;
    private Boolean shuffleOptions;
    private Boolean antiCheatEnabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private List<ExamPaperRequest.QuestionConfig> questions;
}
