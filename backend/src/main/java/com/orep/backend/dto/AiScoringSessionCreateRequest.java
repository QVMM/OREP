package com.orep.backend.dto;

import lombok.Data;

@Data
public class AiScoringSessionCreateRequest {
    private String sourceType;
    private Long sourceId;
    private Long projectId;
    private Long teamId;
    private Long meetingId;
    private Long recordingId;
    private String trackId;
    private String trackName;
    private Boolean useHistoryMemory;
    private Boolean juryEnabled;
    /** 仅排障/计费：为 true 时才允许命中已完成 fingerprint 短路。默认必须新开场。 */
    private Boolean reuseCompleted;
    private Long historyMemorySnapshotId;
    private String modelVersion;
    private String promptVersion;
    private String scoringConfigHash;
}
