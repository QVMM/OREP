package com.orep.backend.dto;

import lombok.Data;

@Data
public class ScoringFingerprintInput {
    private String trackId;
    private String rubricId;
    private String rubricHash;
    private Long evidenceSchemaId;
    private String evidenceSchemaVersion;
    private String evidenceSchemaHash;
    private String sourceType;
    private Long sourceId;
    private Long meetingId;
    private Long recordingId;
    private Long projectId;
    private Long teamId;
    private Boolean useHistoryMemory;
    private Long historyMemorySnapshotId;
    private String modelVersion;
    private String promptVersion;
    private String scoringConfigHash;
}
