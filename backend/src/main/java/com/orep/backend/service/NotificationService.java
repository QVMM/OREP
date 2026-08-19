package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class NotificationService {
    private static final String REMINDER_EVENT = "REMINDER_SENT";
    private static final String TRAINING_PATH = "/training/today";
    private static final Set<String> USER_NOTIFICATION_EVENTS = Set.of(
            REMINDER_EVENT,
            "COLLABORATION_REQUESTED",
            "COLLABORATION_ACCEPTED",
            "COLLABORATION_DECLINED",
            "COLLABORATION_WITHDRAWN",
            "COLLABORATION_SUBMITTED",
            "COLLABORATION_REVIEWED",
            "TEACHER_TASK_ASSIGNED"
    );
    private static final String USER_NOTIFICATION_EVENT_SQL = """
        ('REMINDER_SENT','COLLABORATION_REQUESTED','COLLABORATION_ACCEPTED',
         'COLLABORATION_DECLINED','COLLABORATION_WITHDRAWN','COLLABORATION_SUBMITTED',
         'COLLABORATION_REVIEWED','TEACHER_TASK_ASSIGNED')
        """;
    private static final Map<String, String> EVENT_TITLES = Map.ofEntries(
            Map.entry("COLLABORATION_REQUESTED", "新的协作申请"),
            Map.entry("COLLABORATION_ACCEPTED", "协作申请已接受"),
            Map.entry("COLLABORATION_DECLINED", "协作申请未接受"),
            Map.entry("COLLABORATION_WITHDRAWN", "协作申请已撤回"),
            Map.entry("COLLABORATION_SUBMITTED", "协作成果待确认"),
            Map.entry("COLLABORATION_REVIEWED", "协作成果已审核"),
            Map.entry("TEACHER_TASK_ASSIGNED", "新的团队任务")
    );

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final SimpMessagingTemplate messagingTemplate;

    public NotificationService(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            SimpMessagingTemplate messagingTemplate
    ) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.messagingTemplate = messagingTemplate;
    }

    public Map<String, Object> notifications(Long tenantId, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id,event_type eventType,target_type targetType,payload_json payloadJson,
                   created_at createdAt,read_at readAt
            FROM teacher_portal_event
            WHERE tenant_id=? AND target_id=? AND event_type IN %s
            ORDER BY created_at DESC,id DESC LIMIT 20
            """.formatted(USER_NOTIFICATION_EVENT_SQL), tenantId, userId);
        List<Map<String, Object>> items = rows.stream().map(this::notificationView).toList();
        Integer unread = jdbc.queryForObject("""
            SELECT COUNT(*) FROM teacher_portal_event
            WHERE tenant_id=? AND target_id=? AND event_type IN %s AND read_at IS NULL
            """.formatted(USER_NOTIFICATION_EVENT_SQL), Integer.class, tenantId, userId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("items", items);
        result.put("unreadCount", unread == null ? 0 : unread);
        return result;
    }

    public Map<String, Object> markRead(Long tenantId, Long userId, Long notificationId) {
        int updated = jdbc.update("""
            UPDATE teacher_portal_event SET read_at=COALESCE(read_at,CURRENT_TIMESTAMP)
            WHERE id=? AND tenant_id=? AND target_id=? AND event_type IN %s
            """.formatted(USER_NOTIFICATION_EVENT_SQL), notificationId, tenantId, userId);
        if (updated == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "通知不存在");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", notificationId);
        result.put("isRead", true);
        result.put("readAt", LocalDateTime.now());
        return result;
    }

    public Map<String, Object> markAllRead(Long tenantId, Long userId) {
        int updated = jdbc.update("""
            UPDATE teacher_portal_event SET read_at=CURRENT_TIMESTAMP
            WHERE tenant_id=? AND target_id=? AND event_type IN %s AND read_at IS NULL
            """.formatted(USER_NOTIFICATION_EVENT_SQL), tenantId, userId);
        return Map.of("unreadCount", 0, "updatedCount", updated);
    }

    public Map<String, Object> createReminder(
            Long tenantId,
            Long actorUserId,
            Long recipientUserId,
            String targetType,
            Map<String, Object> payload
    ) {
        return createNotification(
                tenantId,
                actorUserId,
                recipientUserId,
                REMINDER_EVENT,
                targetType,
                payload
        );
    }

    public Map<String, Object> createNotification(
            Long tenantId,
            Long actorUserId,
            Long recipientUserId,
            String eventType,
            String targetType,
            Map<String, Object> payload
    ) {
        String normalizedEventType = text(eventType);
        if (!USER_NOTIFICATION_EVENTS.contains(normalizedEventType)) {
            throw new IllegalArgumentException("不支持的通知事件类型");
        }
        if (tenantId == null || recipientUserId == null) {
            throw new IllegalArgumentException("通知缺少租户或接收人");
        }
        LocalDateTime createdAt = LocalDateTime.now();
        String payloadJson;
        try {
            payloadJson = objectMapper.writeValueAsString(payload == null ? Map.of() : payload);
        } catch (Exception error) {
            throw new IllegalArgumentException("通知内容无法保存", error);
        }

        KeyHolder keyHolder = new GeneratedKeyHolder();
        int inserted = jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement("""
                INSERT INTO teacher_portal_event(
                  tenant_id,actor_user_id,event_type,target_type,target_id,payload_json,created_at
                ) VALUES (?,?,?,?,?,?,?)
                """, Statement.RETURN_GENERATED_KEYS);
            statement.setObject(1, tenantId);
            statement.setObject(2, actorUserId);
            statement.setString(3, normalizedEventType);
            statement.setString(4, targetType);
            statement.setObject(5, recipientUserId);
            statement.setString(6, payloadJson);
            statement.setObject(7, createdAt);
            return statement;
        }, keyHolder);
        Number generatedId = keyHolder.getKey();
        if (inserted != 1 || generatedId == null) {
            throw new IllegalStateException("通知保存失败");
        }

        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", generatedId.longValue());
        row.put("eventType", normalizedEventType);
        row.put("targetType", targetType);
        row.put("payloadJson", payloadJson);
        row.put("createdAt", createdAt);
        row.put("readAt", null);
        Map<String, Object> notification = notificationView(row);
        messagingTemplate.convertAndSendToUser(
                String.valueOf(recipientUserId),
                "/queue/notifications",
                notification
        );
        return notification;
    }

    private Map<String, Object> notificationView(Map<String, Object> row) {
        Map<String, Object> payload = parsePayload(row.get("payloadJson"));
        String eventType = defaultText(row.get("eventType"), REMINDER_EVENT);
        String targetType = text(row.get("targetType"));
        Object readAt = row.get("readAt");
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", row.get("id"));
        view.put("eventType", eventType);
        view.put("targetType", targetType);
        view.put("title", notificationTitle(eventType, targetType, payload));
        view.put("message", defaultText(payload.get("message"), defaultMessage(eventType)));
        view.put("deadline", defaultText(payload.get("deadline"), ""));
        view.put("createdAt", row.get("createdAt"));
        view.put("readAt", readAt);
        view.put("isRead", readAt != null);
        view.put("targetPath", targetPath(eventType, payload));
        copyIdentifier(payload, view, "requestId");
        copyIdentifier(payload, view, "taskId");
        copyIdentifier(payload, view, "submissionId");
        copyIdentifier(payload, view, "teamId");
        return view;
    }

    private String notificationTitle(String eventType, String targetType, Map<String, Object> payload) {
        String explicit = text(payload.get("title"));
        if (explicit != null) return explicit;
        if (REMINDER_EVENT.equals(eventType)) {
            return "TRAINING_CAMP".equals(targetType) ? "集训任务提醒" : "训练提交提醒";
        }
        return EVENT_TITLES.getOrDefault(eventType, "平台通知");
    }

    private String defaultMessage(String eventType) {
        if (REMINDER_EVENT.equals(eventType)) return "老师提醒你及时完成当前训练任务";
        return switch (eventType) {
            case "COLLABORATION_REQUESTED" -> "有团队成员邀请你共同完成一项任务";
            case "COLLABORATION_ACCEPTED" -> "对方已接受你的协作申请";
            case "COLLABORATION_DECLINED" -> "对方暂未接受你的协作申请";
            case "COLLABORATION_WITHDRAWN" -> "发起人已撤回这项协作申请";
            case "COLLABORATION_SUBMITTED" -> "协作成果已提交，请及时确认";
            case "COLLABORATION_REVIEWED" -> "你的协作成果已有新的审核结果";
            case "TEACHER_TASK_ASSIGNED" -> "老师发布了一项新的团队任务";
            default -> "你有一条新的平台通知";
        };
    }

    private String targetPath(String eventType, Map<String, Object> payload) {
        if (REMINDER_EVENT.equals(eventType)) return TRAINING_PATH;
        String explicit = text(payload.get("targetPath"));
        if (explicit != null && explicit.startsWith("/") && !explicit.startsWith("//")) {
            return explicit;
        }
        Object requestId = payload.get("requestId");
        if (requestId != null) return "/project-team?collaborationRequestId=" + requestId;
        return "/project-team";
    }

    private void copyIdentifier(Map<String, Object> payload, Map<String, Object> view, String key) {
        if (payload.containsKey(key) && payload.get(key) != null) view.put(key, payload.get(key));
    }

    private Map<String, Object> parsePayload(Object value) {
        if (value == null) return Map.of();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() { });
        } catch (Exception ignored) {
            return Map.of();
        }
    }

    private String defaultText(Object value, String fallback) {
        String result = text(value);
        return result == null ? fallback : result;
    }

    private String text(Object value) {
        if (value == null) return null;
        String result = String.valueOf(value).trim();
        return result.isEmpty() ? null : result;
    }
}
