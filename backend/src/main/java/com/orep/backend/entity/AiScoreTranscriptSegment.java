package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_transcript_segment")
public class AiScoreTranscriptSegment {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long mediaAssetId;
    private Integer segmentNo;
    private String segmentUid;
    private Integer attributionRevision;
    private String speakerLabel;
    private String personId;
    private String speakerState;
    private BigDecimal speakerConfidence;
    private Boolean isFinal;
    private Long startMs;
    private Long endMs;
    private String text;
    private String sourceType;
    private BigDecimal confidence;
    private String segmentHash;
    private LocalDateTime createdAt;
}
