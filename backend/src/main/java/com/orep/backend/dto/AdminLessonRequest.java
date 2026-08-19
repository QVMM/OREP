package com.orep.backend.dto;

import lombok.Data;

@Data
public class AdminLessonRequest {
    private Long chapterId;
    private String title;
    private String lessonType;
    private Integer durationSeconds;
    private Integer sortOrder;
}
