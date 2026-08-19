package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_observation")
public class AiScoreObservation {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long reportId;
    private String observationCode;
    private String dimensionCode;
    private String dimensionName;
    private BigDecimal rawScore;
    private BigDecimal scoreCap;
    private String evidenceLevel;
    private BigDecimal confidence;
    private String evidenceAnchorIdsJson;
    private String validityStatus;
    private String modelReason;
    private LocalDateTime createdAt;
}
