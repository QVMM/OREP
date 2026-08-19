package com.orep.backend.dto;

import java.time.LocalDateTime;

public record AiScoreUploadTaskResponse(
        Long sessionId,
        String sessionNo,
        String fileName,
        Long fileSize,
        Long projectId,
        Long teamId,
        String teamName,
        String trackName,
        String status,
        String currentStage,
        Integer progressPercent,
        Boolean useHistoryMemory,
        Boolean juryEnabled,
        Long reportId,
        String errorMessage,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
