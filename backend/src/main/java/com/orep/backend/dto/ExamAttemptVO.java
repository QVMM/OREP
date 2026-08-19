package com.orep.backend.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class ExamAttemptVO {
    private Long attemptId;
    private Long paperId;
    private String title;
    private Integer durationMinutes;
    private LocalDateTime deadlineAt;
    private Boolean antiCheatEnabled;
    private Integer screenLeaveCount;
    private List<ExamQuestionVO> questions;
}
