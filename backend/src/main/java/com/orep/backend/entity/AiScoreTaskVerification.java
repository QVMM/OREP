package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_task_verification")
public class AiScoreTaskVerification {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long taskId;
    private Long sourceSessionId;
    private Long verificationSessionId;
    private Long reportId;
    private String status;
    private Boolean minimumPassed;
    private Boolean fullScorePassed;
    private String evidenceAnchorIdsJson;
    private String previousStateJson;
    private String currentStateJson;
    private String reason;
    private Boolean ruleComparable;
    private LocalDateTime verifiedAt;
    private LocalDateTime createdAt;
}
