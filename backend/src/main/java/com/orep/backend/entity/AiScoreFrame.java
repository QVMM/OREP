package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_frame")
public class AiScoreFrame {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long mediaAssetId;
    private Integer frameNo;
    private Long timestampMs;
    private String framePath;
    private String frameHash;
    private String perceptualHash;
    private String ocrText;
    private String frameReason;
    private BigDecimal confidence;
    private LocalDateTime createdAt;
}
