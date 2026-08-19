package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_scoring_session")
public class AiScoringSession {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String sessionNo;
    private String sourceType;
    private Long sourceId;
    private Long projectId;
    private Long teamId;
    private Long meetingId;
    private Long recordingId;
    private String trackId;
    private String trackName;
    private String rubricId;
    private String rubricInternalVersion;
    private String rubricHash;
    private Long evidenceSchemaId;
    private String evidenceSchemaVersion;
    private Integer speakerAttributionRevision;
    private String speakerAttributionStatus;
    private String speakerAttributionContractVersion;
    private String speakerAttributionClockId;
    private String speakerAttributionSnapshotHash;
    private String scoringFingerprint;
    private String docketId;
    private String deliberationStage;
    private Boolean teacherConfirmed;
    private LocalDateTime teacherConfirmedAt;
    private Long teacherConfirmedBy;
    private Boolean challengeCompleted;
    private String challengeJson;
    private String status;
    private String currentStage;
    private Integer progressPercent;
    private Boolean useHistoryMemory;
    private Boolean juryEnabled;
    private Long reportId;
    private String errorMessage;
    private Long createdBy;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
