package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_report")
public class AiScoreReport {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long meetingId;
    private BigDecimal overallScore;
    /** 维度得分 JSON: {"技能水平":55,"职业素养":12,...} */
    private String dimensionsJson;
    /** 亮点 JSON 数组 */
    private String highlightsJson;
    /** 问题 JSON 数组 */
    private String criticalIssuesJson;
    /** 改进建议 JSON 数组 */
    private String improvementPrioritiesJson;
    /** 可执行行动计划 JSON 数组 */
    private String actionPlanJson;
    /** 不可变失分账本 JSON 数组 */
    private String lossLedgerJson;
    /** 整改覆盖摘要 JSON */
    private String coverageSummaryJson;
    /** 全部整改通过后的规则情景预测 JSON */
    private String scoreProjectionJson;
    /** 报告数据契约版本 */
    private String contractVersion;
    /** complete / incomplete */
    private String todoPortfolioStatus;
    /** 教师是否已发布本场任务书 */
    private Boolean taskBookPublished;
    /** 已发布任务书快照 JSON */
    private String taskBookJson;
    /** ASR 转录文本 */
    private String transcript;
    /** 语音质量分析 JSON */
    private String speechQualityJson;
    /** 技术/现场演示校准 JSON */
    private String scoreCalibrationJson;
    /** 规则引擎版本 */
    private String ruleEngineVersion;
    /** 规则引擎结构化结果 JSON */
    private String structuredResultJson;
    /** 本轮证据上限 */
    private BigDecimal currentScoreCap;
    /** 本轮追回分 */
    private BigDecimal recoveredScore;
    /** 使用的模型 */
    private String model;
    /** AI 服务结果 JSON 文件路径 */
    private String resultPath;
    /** 状态: processing / completed / failed */
    private String status;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
