package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_speaker_turn")
public class AiScoreSpeakerTurn {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String turnUid;
    private Integer attributionRevision;
    private Long startMs;
    private Long endMs;
    private String personId;
    private String speakerState;
    private BigDecimal confidence;
    private String candidatePersonIdsJson;
    private String sourceClusterId;
    private String sourceVisualIdentityId;
    private String speakerVerification;
    private LocalDateTime createdAt;
}
