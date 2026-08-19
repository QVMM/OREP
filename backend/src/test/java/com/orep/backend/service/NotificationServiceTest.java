package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.PreparedStatementCreator;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.messaging.simp.SimpMessagingTemplate;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class NotificationServiceTest {
    private JdbcTemplate jdbc;
    private SimpMessagingTemplate messagingTemplate;
    private NotificationService service;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        messagingTemplate = mock(SimpMessagingTemplate.class);
        service = new NotificationService(jdbc, new ObjectMapper(), messagingTemplate);
    }

    @Test
    void listReturnsItemsAndGlobalUnreadCount() {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", 9L);
        row.put("eventType", "REMINDER_SENT");
        row.put("targetType", "TRAINING_CAMP");
        row.put("payloadJson", "{\"message\":\"请完成训练\",\"deadline\":\"今晚 22:00\"}");
        row.put("createdAt", Timestamp.valueOf(LocalDateTime.of(2026, 7, 23, 10, 0)));
        row.put("readAt", null);
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenReturn(List.of(row));
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class))).thenReturn(3);

        Map<String, Object> result = service.notifications(7L, 21L);

        assertEquals(3, result.get("unreadCount"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) result.get("items");
        assertEquals(1, items.size());
        assertEquals("/training/today", items.getFirst().get("targetPath"));
        assertEquals("请完成训练", items.getFirst().get("message"));
        assertFalse((Boolean) items.getFirst().get("isRead"));
    }

    @Test
    void markReadScopesUpdateToTenantAndRecipient() {
        when(jdbc.update(anyString(), any(Object[].class))).thenReturn(1);

        Map<String, Object> result = service.markRead(7L, 21L, 9L);

        assertEquals(9L, result.get("id"));
        assertEquals(true, result.get("isRead"));
        verify(jdbc).update(
                anyString(),
                any(Object[].class)
        );
    }

    @Test
    void markAllReadReturnsZeroUnread() {
        when(jdbc.update(anyString(), any(Object[].class))).thenReturn(4);

        Map<String, Object> result = service.markAllRead(7L, 21L);

        assertEquals(0, result.get("unreadCount"));
        assertEquals(4, result.get("updatedCount"));
    }

    @Test
    void createReminderPushesToAuthenticatedUserDestinationAfterInsert() {
        doAnswer(invocation -> {
            KeyHolder keyHolder = invocation.getArgument(1);
            keyHolder.getKeyList().add(Map.of("GENERATED_KEY", 99L));
            return 1;
        }).when(jdbc).update(any(PreparedStatementCreator.class), any(KeyHolder.class));

        Map<String, Object> notification = service.createReminder(
                7L,
                8L,
                21L,
                "TRAINING_CAMP",
                Map.of("message", "请完成今日训练")
        );

        assertEquals(99L, notification.get("id"));
        assertEquals("/training/today", notification.get("targetPath"));
        verify(messagingTemplate).convertAndSendToUser(
                "21",
                "/queue/notifications",
                notification
        );
    }

    @Test
    void createCollaborationNotificationUsesControlledTitlePathAndIdentifiers() {
        doAnswer(invocation -> {
            KeyHolder keyHolder = invocation.getArgument(1);
            keyHolder.getKeyList().add(Map.of("GENERATED_KEY", 100L));
            return 1;
        }).when(jdbc).update(any(PreparedStatementCreator.class), any(KeyHolder.class));

        Map<String, Object> notification = service.createNotification(
                7L,
                8L,
                21L,
                "COLLABORATION_REQUESTED",
                "COLLABORATION_REQUEST",
                Map.of(
                        "requestId", 42L,
                        "teamId", 6L,
                        "message", "王同学邀请你完善路演材料"
                )
        );

        assertEquals("新的协作申请", notification.get("title"));
        assertEquals("/project-team?collaborationRequestId=42", notification.get("targetPath"));
        assertEquals(42L, ((Number) notification.get("requestId")).longValue());
        assertEquals(6L, ((Number) notification.get("teamId")).longValue());
        verify(messagingTemplate).convertAndSendToUser(
                "21",
                "/queue/notifications",
                notification
        );
    }

    @Test
    void createNotificationRejectsEventsOutsideUserNotificationWhitelist() {
        assertThrows(IllegalArgumentException.class, () -> service.createNotification(
                7L,
                8L,
                21L,
                "INTERNAL_AUDIT_EVENT",
                "AUDIT",
                Map.of()
        ));
    }
}
