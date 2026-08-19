package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("users")
public class User {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private String username;
    @JsonIgnore
    private String password;
    private String email;
    private String role; // ADMIN, SCHOOL_ADMIN, TEACHER, STUDENT, REVIEWER, EXPERT
    private Long schoolId;
    private Long collegeId;
    private Long classId;
    private String schoolName;
    private String collegeName;
    private String className;
    private String userGroup;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
