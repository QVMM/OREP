package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("course_attachment")
public class CourseAttachment {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long courseId;
    private String name;
    private String fileUrl;
    private String fileType;
    private String fileSize;
    private Integer sortOrder;
    private LocalDateTime createdAt;
}
