package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_deduction")
public class AiScoreDeduction {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long reportId;
    private String deductionId;
    private String observationCode;
    private String dimensionCode;
    private BigDecimal deductedPoints;
    private BigDecimal recoveredPoints;
    private String reason;
    private String requiredFix;
    private String acceptanceCriteria;
    private BigDecimal maxRecoverablePoints;
    private String evidenceLevel;
    private BigDecimal confidence;
    private String evidenceAnchorIdsJson;
    private String recoverySourceDeductionId;
    private String status;
    private LocalDateTime createdAt;
}
