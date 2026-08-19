package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("course_chapter")
public class CourseChapter {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long courseId;
    private String title;
    private Integer sortOrder;
    private LocalDateTime createdAt;
}
