package com.orep.backend.dto;

import lombok.Data;

import java.util.List;

@Data
public class ExamManualGradeRequest {
    private List<Item> answers;

    @Data
    public static class Item {
        private Long answerId;
        private Integer score;
    }
}
