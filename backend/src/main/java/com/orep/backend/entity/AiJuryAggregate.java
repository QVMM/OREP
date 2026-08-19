package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_jury_aggregate")
public class AiJuryAggregate {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long jurySessionId;
    private Long meetingId;
    private Long scoringSessionId;
    private BigDecimal officialScore;
    private BigDecimal rawAverageScore;
    private BigDecimal trimmedAverageScore;
    private BigDecimal trimmedTotalScore;
    private Integer trimmedCount;
    private Long removedHighReportId;
    private Long removedLowReportId;
    private String scoreStatsJson;
    private String dimensionDisagreementJson;
    private String consensusIssuesJson;
    private String personaInsightsJson;
    private String optimizationSuggestionsJson;
    private String aggregateReportJson;
    private LocalDateTime createdAt;
}
