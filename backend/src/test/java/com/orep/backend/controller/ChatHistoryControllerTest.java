package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.ChatMessage;
import com.orep.backend.mapper.ChatMessageMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ChatHistoryControllerTest {

    private final ChatMessageMapper chatMessageMapper = mock(ChatMessageMapper.class);
    private final AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
    private ChatHistoryController controller;

    @BeforeEach
    void setUp() {
        controller = new ChatHistoryController(chatMessageMapper, access);
    }

    @Test
    void historyRequiresLogin() {
        Result<List<ChatMessage>> result = controller.getHistory(20L, new MockHttpServletRequest());

        assertEquals(401, result.getCode());
        assertNull(result.getData());
        verify(chatMessageMapper, never()).selectList(any());
    }

    @Test
    void historyHidesForeignMeetingAsEmptyList() {
        when(access.hasMeetingParticipantAccess(2L, 11L)).thenReturn(false);

        Result<List<ChatMessage>> result = controller.getHistory(2L, authenticated(11L));

        assertEquals(200, result.getCode());
        assertTrue(result.getData().isEmpty());
        verify(chatMessageMapper, never()).selectList(any());
    }

    @Test
    void historyReturnsMessagesForParticipant() {
        ChatMessage message = new ChatMessage();
        message.setId(9L);
        message.setMeetingId(20L);
        message.setContent("本场备注");
        when(access.hasMeetingParticipantAccess(20L, 10L)).thenReturn(true);
        when(chatMessageMapper.selectList(any())).thenReturn(List.of(message));

        Result<List<ChatMessage>> result = controller.getHistory(20L, authenticated(10L));

        assertEquals(200, result.getCode());
        assertEquals(1, result.getData().size());
        assertEquals("本场备注", result.getData().getFirst().getContent());
    }

    @Test
    void sendRequiresLogin() {
        ChatHistoryController.SendRequest req = new ChatHistoryController.SendRequest();
        req.setMeetingId(20L);
        req.setContent("hi");

        Result<ChatMessage> result = controller.send(req, new MockHttpServletRequest());

        assertEquals(401, result.getCode());
        verify(chatMessageMapper, never()).insert(any());
    }

    @Test
    void sendRejectsMissingMeetingId() {
        Result<ChatMessage> result = controller.send(new ChatHistoryController.SendRequest(), authenticated(10L));

        assertEquals(400, result.getCode());
        verify(chatMessageMapper, never()).insert(any());
    }

    @Test
    void sendRejectsNonParticipant() {
        ChatHistoryController.SendRequest req = new ChatHistoryController.SendRequest();
        req.setMeetingId(20L);
        req.setSender("刘旭");
        req.setContent("不该发出");
        when(access.hasMeetingParticipantAccess(20L, 11L)).thenReturn(false);

        Result<ChatMessage> result = controller.send(req, authenticated(11L));

        assertEquals(403, result.getCode());
        verify(chatMessageMapper, never()).insert(any());
    }

    @Test
    void sendUsesAuthenticatedUserId() {
        ChatHistoryController.SendRequest req = new ChatHistoryController.SendRequest();
        req.setMeetingId(20L);
        req.setSender("李林峰");
        req.setMessageType("text");
        req.setContent("本场发言");
        when(access.hasMeetingParticipantAccess(20L, 10L)).thenReturn(true);

        Result<ChatMessage> result = controller.send(req, authenticated(10L));

        assertEquals(200, result.getCode());
        verify(chatMessageMapper).insert(any(ChatMessage.class));
    }

    private static MockHttpServletRequest authenticated(Long userId) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", userId);
        request.setAttribute("tenantId", 3L);
        request.setAttribute("role", "STUDENT");
        return request;
    }
}
