package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_remediation_task")
public class AiScoreRemediationTask {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String projectScopeKey;
    private String taskKey;
    private String rootCauseKey;
    private String title;
    private String taskJson;
    private String status;
    private Long sourceReportId;
    private Long latestReportId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
