package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_docket_run")
public class AiScoreDocketRun {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String docketId;
    private Integer runIndex;
    private Long sessionId;
    private Long reportId;
    private BigDecimal officialScore;
    private String dimensionScoresJson;
    private BigDecimal transcriptCoverage;
    private BigDecimal seekableAnchorRate;
    private BigDecimal scoreDeltaAbs;
    private String stabilityBand;
    private Boolean tapeGrounded;
    private String status;
    private LocalDateTime createdAt;
}
