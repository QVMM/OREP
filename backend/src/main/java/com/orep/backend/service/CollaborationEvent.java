package com.orep.backend.service;

public record CollaborationEvent(
        Long tenantId,
        Long actorUserId,
        Long recipientUserId,
        String eventType,
        Long requestId,
        Long teamId,
        Long taskId,
        String title,
        String reason
) {
}
