package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_speaker_identity")
public class AiScoreSpeakerIdentity {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String rawSpeakerLabel;
    private String personId;
    private String personType;
    private Integer contestantSlot;
    private String displayName;
    private String roleName;
    private String status;
    private String source;
    private BigDecimal confidence;
    private Integer revision;
    private String personState;
    private Long firstSeenMs;
    private Long lastSeenMs;
    private String voiceClusterIdsJson;
    private Long updatedBy;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
