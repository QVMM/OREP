package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_media_preprocess_job")
public class AiScoreMediaPreprocessJob {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String jobNo;
    private Long sessionId;
    private Long mediaAssetId;
    private Long projectId;
    private Long teamId;
    private String trackId;
    private String trackName;
    private String sourceFilePath;
    private Long sourceFileSize;
    private String sourceMimeType;
    private String targetFilePath;
    private Long targetFileSize;
    private String status;
    private Integer progressPercent;
    private String errorMessage;
    private Boolean useHistoryMemory;
    private Boolean juryEnabled;
    private Long createdBy;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private LocalDateTime completedAt;
}
