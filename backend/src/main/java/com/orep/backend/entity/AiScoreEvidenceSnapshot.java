package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_evidence_snapshot")
public class AiScoreEvidenceSnapshot {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String mediaAssetHash;
    private String asrSnapshotHash;
    private String frameSnapshotHash;
    private String ocrSnapshotHash;
    private String materialSnapshotHash;
    private Long historyMemorySnapshotId;
    private String snapshotStatus;
    private LocalDateTime createdAt;
}
