package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_task_loss_link")
public class AiScoreTaskLossLink {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long reportId;
    private Long taskId;
    private String lossId;
    private String lossKey;
    private String observationCode;
    private String scoreBudgetKey;
    private BigDecimal gapPoints;
    private LocalDateTime createdAt;
}
