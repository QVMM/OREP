package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("course_learning_progress")
public class CourseLearningProgress {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long userId;
    private Long courseId;
    private Long lessonId;
    private Integer learnedSeconds;
    private Integer progressPercent;
    private Integer completedLessons;
    private String status;
    private LocalDateTime lastLearnedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
