package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("exam_attempt")
public class ExamAttempt {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long paperId;
    private Long userId;
    private String status;
    private LocalDateTime startedAt;
    private LocalDateTime submittedAt;
    private LocalDateTime deadlineAt;
    private Integer score;
    private Integer totalScore;
    private Integer correctCount;
    private Integer questionCount;
    private Integer screenLeaveCount;
}
