package com.orep.backend.dto;

import lombok.Data;

@Data
public class CourseVO {
    private Long id;
    private String title;
    private String subtitle;
    private String description;
    private String courseType;
    private String courseTypeLabel;
    private String category;
    private String coverUrl;
    private String accentColor;
    private Integer progressPercent;
    private String learningStatus;
    private Long currentLessonId;
    private String currentLessonTitle;
    private Integer learnedSeconds;
    private Integer totalLessons;
    private Integer completedLessons;
}
