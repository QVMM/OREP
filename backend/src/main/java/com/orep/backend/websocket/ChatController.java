package com.orep.backend.websocket;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

import java.util.Map;

@Controller
public class ChatController {

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    /**
     * 发送聊天消息到会议室
     */
    @MessageMapping("/chat")
    public void sendMessage(@Payload Map<String, Object> message) {
        String meetingId = String.valueOf(message.get("meetingId"));
        messagingTemplate.convertAndSend("/topic/meeting/" + meetingId, message);
    }

    /**
     * 评分结果推送
     */
    public void pushScoreResult(Long meetingId, Object scoreResult) {
        messagingTemplate.convertAndSend("/topic/meeting/" + meetingId + "/score", scoreResult);
    }

    /**
     * 会议状态变更通知
     */
    public void pushMeetingStatus(Long meetingId, String status) {
        messagingTemplate.convertAndSend("/topic/meeting/" + meetingId + "/status",
                Map.of("status", status, "meetingId", meetingId));
    }
}
