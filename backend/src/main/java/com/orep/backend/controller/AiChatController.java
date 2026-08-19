package com.orep.backend.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.common.Result;
import com.orep.backend.entity.AiChatMessage;
import com.orep.backend.entity.AiChatSession;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiChatMessageMapper;
import com.orep.backend.mapper.AiChatSessionMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoringSessionService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/ai-chat")
public class AiChatController {

    private final AiChatSessionMapper sessionMapper;
    private final AiChatMessageMapper messageMapper;
    private final AiScoringSessionService scoringSessionService;
    private final AiScoreAccessControlService accessControlService;

    public AiChatController(AiChatSessionMapper sessionMapper,
                            AiChatMessageMapper messageMapper,
                            AiScoringSessionService scoringSessionService,
                            AiScoreAccessControlService accessControlService) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.scoringSessionService = scoringSessionService;
        this.accessControlService = accessControlService;
    }

    /**
     * Python 服务回调：保存对话消息
     * POST /api/ai-chat/callback
     */
    @PostMapping("/callback")
    public Result<Void> callback(@RequestBody Map<String, Object> body) {
        String action = (String) body.get("action"); // "session" or "message"
        String sessionKey = (String) body.get("session_key");

        if ("session".equals(action)) {
            // 创建会话记录
            AiChatSession session = new AiChatSession();
            session.setMeetingId(Long.parseLong(String.valueOf(body.get("meeting_id"))));
            session.setSessionKey(sessionKey);
            session.setProjectName((String) body.get("project_name"));
            session.setStatus("active");
            session.setCreatedAt(LocalDateTime.now());
            session.setUpdatedAt(LocalDateTime.now());
            sessionMapper.insert(session);
            return Result.success();
        }

        if ("message".equals(action)) {
            // 通过 sessionKey 查找 session
            AiChatSession session = sessionMapper.selectOne(
                new LambdaQueryWrapper<AiChatSession>()
                    .eq(AiChatSession::getSessionKey, sessionKey)
            );
            if (session == null) {
                return Result.error(404, "会话不存在: " + sessionKey);
            }

            // 插入消息
            AiChatMessage msg = new AiChatMessage();
            msg.setSessionId(session.getId());
            msg.setRole((String) body.get("role"));
            msg.setContent((String) body.get("content"));
            msg.setModel((String) body.get("model"));
            msg.setRouteType((String) body.get("route_type"));
            msg.setCreatedAt(LocalDateTime.now());
            messageMapper.insert(msg);
            return Result.success();
        }

        return Result.error(400, "未知 action: " + action);
    }

    /**
     * 查询会议的问答历史（所有会话）
     * GET /api/ai-chat/history/{meetingId}
     */
    @GetMapping("/history/{meetingId}")
    public Result<List<AiChatSession>> getHistory(@PathVariable Long meetingId,
                                                  HttpServletRequest request) {
        assertMeetingAccess(meetingId, request);
        List<AiChatSession> sessions = sessionMapper.selectList(
            new LambdaQueryWrapper<AiChatSession>()
                .eq(AiChatSession::getMeetingId, meetingId)
                .orderByDesc(AiChatSession::getCreatedAt)
        );
        return Result.success(sessions);
    }

    /**
     * 查询会话的消息列表
     * GET /api/ai-chat/session/{sessionId}/messages
     */
    @GetMapping("/session/{sessionId}/messages")
    public Result<List<AiChatMessage>> getMessages(@PathVariable Long sessionId,
                                                   HttpServletRequest request) {
        AiChatSession chatSession = sessionMapper.selectById(sessionId);
        if (chatSession == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会话不存在");
        }
        assertMeetingAccess(chatSession.getMeetingId(), request);
        List<AiChatMessage> messages = messageMapper.selectList(
            new LambdaQueryWrapper<AiChatMessage>()
                .eq(AiChatMessage::getSessionId, sessionId)
                .orderByAsc(AiChatMessage::getCreatedAt)
        );
        return Result.success(messages);
    }

    /**
     * 查询会议最近一次会话的消息（直接加载）
     * GET /api/ai-chat/latest/{meetingId}
     */
    @GetMapping("/latest/{meetingId}")
    public Result<Map<String, Object>> getLatest(@PathVariable Long meetingId,
                                                 HttpServletRequest request) {
        assertMeetingAccess(meetingId, request);
        AiChatSession session = sessionMapper.selectOne(
            new LambdaQueryWrapper<AiChatSession>()
                .eq(AiChatSession::getMeetingId, meetingId)
                .orderByDesc(AiChatSession::getCreatedAt)
                .last("LIMIT 1")
        );
        if (session == null) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("session", null);
            empty.put("messages", List.of());
            return Result.success(empty);
        }
        List<AiChatMessage> messages = messageMapper.selectList(
            new LambdaQueryWrapper<AiChatMessage>()
                .eq(AiChatMessage::getSessionId, session.getId())
                .orderByAsc(AiChatMessage::getCreatedAt)
        );
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("session", session);
        payload.put("messages", messages);
        return Result.success(payload);
    }

    private void assertMeetingAccess(Long meetingId, HttpServletRequest request) {
        Long userId = attrLong(request, "userId");
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        AiScoringSession session = scoringSessionService.sessionForMeetingAccess(meetingId);
        if (session != null) {
            accessControlService.assertSessionAccess(
                    session,
                    attrLong(request, "tenantId"),
                    userId,
                    attrString(request, "role")
            );
            return;
        }
        if (accessControlService.hasMeetingParticipantAccess(meetingId, userId)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.NOT_FOUND, "该会议暂未生成AI评分报告");
    }

    private Long attrLong(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value instanceof Number number ? number.longValue() : null;
    }

    private String attrString(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value == null ? null : String.valueOf(value);
    }
}
