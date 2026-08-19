package com.orep.backend.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.common.Result;
import com.orep.backend.entity.ChatMessage;
import com.orep.backend.mapper.ChatMessageMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/chat")
public class ChatHistoryController {

    private final ChatMessageMapper chatMessageMapper;
    private final AiScoreAccessControlService accessControlService;

    public ChatHistoryController(ChatMessageMapper chatMessageMapper,
                                 AiScoreAccessControlService accessControlService) {
        this.chatMessageMapper = chatMessageMapper;
        this.accessControlService = accessControlService;
    }

    /**
     * 获取会议聊天历史
     * 登录后：会议创建人/参会人看全量；否则空列表，不泄露他人消息。
     */
    @GetMapping("/history")
    public Result<List<ChatMessage>> getHistory(@RequestParam Long meetingId,
                                                HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        if (userId == null) {
            return Result.error(401, "未登录");
        }
        if (!accessControlService.hasMeetingParticipantAccess(meetingId, userId)) {
            return Result.success(List.of());
        }
        List<ChatMessage> messages = chatMessageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getMeetingId, meetingId)
                        .orderByAsc(ChatMessage::getCreatedAt)
        );
        return Result.success(messages);
    }

    /**
     * 发送聊天消息（持久化）
     */
    @PostMapping("/send")
    public Result<ChatMessage> send(@RequestBody SendRequest req, HttpServletRequest httpReq) {
        Long userId = (Long) httpReq.getAttribute("userId");
        if (userId == null) {
            return Result.error(401, "未登录");
        }
        if (req == null || req.getMeetingId() == null) {
            return Result.error(400, "meetingId 不能为空");
        }
        if (!accessControlService.hasMeetingParticipantAccess(req.getMeetingId(), userId)) {
            return Result.error(403, "无权在此会议发言");
        }
        ChatMessage msg = new ChatMessage();
        msg.setMeetingId(req.getMeetingId());
        msg.setSenderId(userId);
        msg.setSenderName(req.getSender());
        msg.setMessageType(req.getMessageType());
        msg.setContent(req.getContent());
        msg.setFileName(req.getFileName());
        chatMessageMapper.insert(msg);
        return Result.success(msg);
    }

    public static class SendRequest {
        private Long meetingId;
        private String sender;
        private String messageType; // text / image / file
        private String content;
        private String fileName;

        public Long getMeetingId() { return meetingId; }
        public void setMeetingId(Long meetingId) { this.meetingId = meetingId; }
        public String getSender() { return sender; }
        public void setSender(String sender) { this.sender = sender; }
        public String getMessageType() { return messageType; }
        public void setMessageType(String messageType) { this.messageType = messageType; }
        public String getContent() { return content; }
        public void setContent(String content) { this.content = content; }
        public String getFileName() { return fileName; }
        public void setFileName(String fileName) { this.fileName = fileName; }
    }
}
