package com.orep.backend.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

@Data
public class AiScoringSessionUserResponse {
    private Long sessionId;
    private String sessionNo;
    private String docketId;
    private String status;
    private String currentStage;
    private Integer progressPercent;
    private String trackName;
    private String sourceType;
    private Boolean useHistoryMemory;
    private Boolean juryEnabled;
    private Boolean cached;
    private Long reportId;
    private Long meetingId;
    private String message;
    private String errorMessage;

    @JsonIgnore
    private String rubricHash;
    @JsonIgnore
    private String rubricPath;
    @JsonIgnore
    private String internalVersion;
}
