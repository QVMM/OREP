package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

@Data
@TableName("exam_attempt_answer")
public class ExamAttemptAnswer {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long attemptId;
    private Long questionId;
    private String answerJson;
    private Boolean correct;
    private Integer score;
}
