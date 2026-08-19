package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_judge_report")
public class AiJudgeReport {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long jurySessionId;
    private Long memberId;
    private Long meetingId;
    private Long scoringSessionId;
    private String personaCode;
    private BigDecimal overallScore;
    private String dimensionsJson;
    private String highlightsJson;
    private String criticalIssuesJson;
    private String improvementPrioritiesJson;
    private String evidenceSummaryJson;
    private String personaViewJson;
    private String reportJson;
    private String model;
    private String provider;
    private String tokensJson;
    private String status;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
