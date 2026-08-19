package com.orep.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import java.util.LinkedHashMap;
import java.util.Map;

@Component
public class CollaborationNotificationListener {
    private static final Logger log = LoggerFactory.getLogger(CollaborationNotificationListener.class);

    private final NotificationService notificationService;

    public CollaborationNotificationListener(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT, fallbackExecution = true)
    public void onCollaborationEvent(CollaborationEvent event) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("requestId", event.requestId());
        payload.put("teamId", event.teamId());
        if (event.taskId() != null) payload.put("taskId", event.taskId());
        payload.put("message", message(event));
        try {
            notificationService.createNotification(
                    event.tenantId(),
                    event.actorUserId(),
                    event.recipientUserId(),
                    event.eventType(),
                    "COLLABORATION_REQUEST",
                    payload
            );
        } catch (RuntimeException error) {
            log.error(
                    "协作通知发送失败，requestId={}, eventType={}, recipientId={}",
                    event.requestId(),
                    event.eventType(),
                    event.recipientUserId(),
                    error
            );
        }
    }

    private String message(CollaborationEvent event) {
        String title = event.title() == null || event.title().isBlank() ? "协作任务" : event.title();
        return switch (event.eventType()) {
            case "COLLABORATION_REQUESTED" -> "你收到一项协作申请：" + title;
            case "COLLABORATION_ACCEPTED" -> "对方已接受协作申请：" + title;
            case "COLLABORATION_DECLINED" -> "对方暂未接受协作申请：" + title
                    + suffix(event.reason());
            case "COLLABORATION_WITHDRAWN" -> "协作申请已撤回：" + title;
            default -> title + "有新的状态变化";
        };
    }

    private String suffix(String reason) {
        return reason == null || reason.isBlank() ? "" : "（" + reason + "）";
    }
}
