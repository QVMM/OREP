package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_evidence_anchor")
public class AiScoreEvidenceAnchor {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String anchorType;
    private String anchorTitle;
    private String evidenceText;
    private String sourceRef;
    private Long transcriptSegmentId;
    private Long frameId;
    private Long mediaAssetId;
    private Long startMs;
    private Long endMs;
    private BigDecimal confidence;
    private String validityStatus;
    private LocalDateTime createdAt;
}
