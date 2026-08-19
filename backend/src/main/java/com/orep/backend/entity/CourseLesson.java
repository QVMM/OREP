package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("course_lesson")
public class CourseLesson {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long courseId;
    private Long chapterId;
    private String title;
    private String lessonType;
    private Integer durationSeconds;
    private String resourceUrl;
    private String videoFilePath;
    private String videoMimeType;
    private Long videoSizeBytes;
    private Integer sortOrder;
    private LocalDateTime createdAt;
}
