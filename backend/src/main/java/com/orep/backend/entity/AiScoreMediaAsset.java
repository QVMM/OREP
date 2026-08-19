package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_media_asset")
public class AiScoreMediaAsset {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String assetType;
    private String sourceType;
    private String filePath;
    private String originalName;
    private String mimeType;
    private String fileHash;
    private Long sizeBytes;
    private Double durationSeconds;
    private Boolean hasAudio;
    private Boolean hasVideo;
    private String status;
    private Long createdBy;
    private LocalDateTime createdAt;
}
