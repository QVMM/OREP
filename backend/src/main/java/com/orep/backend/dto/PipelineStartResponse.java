package com.orep.backend.dto;

import lombok.Data;

@Data
public class PipelineStartResponse {
    private boolean accepted;
    private String message;
    private String taskId;
}
