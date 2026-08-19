package com.orep.backend.controller;

import com.orep.backend.entity.AiChatMessage;
import com.orep.backend.entity.AiChatSession;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiChatMessageMapper;
import com.orep.backend.mapper.AiChatSessionMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiChatControllerTest {

    @Test
    void historyRequiresLogin() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();

        fx.mvc.perform(get("/api/ai-chat/history/4"))
                .andExpect(status().isUnauthorized());
        verify(fx.scoringSessionService, never()).sessionForMeetingAccess(any());
        verify(fx.chatSessionMapper, never()).selectList(any());
    }

    @Test
    void historyWithoutScoringSessionIsHidden() throws Exception {
        Fixtures fx = Fixtures.withoutScoringSession();
        when(fx.access.hasMeetingParticipantAccess(4L, 10L)).thenReturn(false);

        fx.mvc.perform(get("/api/ai-chat/history/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isNotFound());
        verify(fx.chatSessionMapper, never()).selectList(any());
    }

    @Test
    void historyWithoutScoringSessionAllowsMeetingParticipant() throws Exception {
        Fixtures fx = Fixtures.withoutScoringSession();
        AiChatSession chat = new AiChatSession();
        chat.setId(168L);
        chat.setMeetingId(20L);
        when(fx.scoringSessionService.sessionForMeetingAccess(20L)).thenReturn(null);
        when(fx.access.hasMeetingParticipantAccess(20L, 10L)).thenReturn(true);
        when(fx.chatSessionMapper.selectList(any())).thenReturn(List.of(chat));

        fx.mvc.perform(get("/api/ai-chat/history/20")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(168));
    }

    @Test
    void historyRejectsCrossTeamUser() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(fx.access).assertSessionAccess(eq(fx.scoring), eq(3L), eq(8L), eq("STUDENT"));

        fx.mvc.perform(get("/api/ai-chat/history/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
        verify(fx.chatSessionMapper, never()).selectList(any());
    }

    @Test
    void latestRejectsCrossTeamUser() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(fx.access).assertSessionAccess(eq(fx.scoring), eq(3L), eq(8L), eq("STUDENT"));

        fx.mvc.perform(get("/api/ai-chat/latest/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void latestAllowsTeamMemberAndReturnsEmptyWhenNoChat() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        when(fx.chatSessionMapper.selectOne(any())).thenReturn(null);

        fx.mvc.perform(get("/api/ai-chat/latest/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.session").isEmpty())
                .andExpect(jsonPath("$.data.messages").isEmpty());
    }

    @Test
    void messagesRejectsCrossTeamUser() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        AiChatSession chat = new AiChatSession();
        chat.setId(90L);
        chat.setMeetingId(4L);
        when(fx.chatSessionMapper.selectById(90L)).thenReturn(chat);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(fx.access).assertSessionAccess(eq(fx.scoring), eq(3L), eq(8L), eq("STUDENT"));

        fx.mvc.perform(get("/api/ai-chat/session/90/messages")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
        verify(fx.chatMessageMapper, never()).selectList(any());
    }

    @Test
    void messagesMissingChatSessionIsHidden() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        when(fx.chatSessionMapper.selectById(90L)).thenReturn(null);

        fx.mvc.perform(get("/api/ai-chat/session/90/messages")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isNotFound());
        verify(fx.scoringSessionService, never()).sessionForMeetingAccess(any());
    }

    @Test
    void historyAllowsTeamMember() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        AiChatSession chat = new AiChatSession();
        chat.setId(90L);
        chat.setMeetingId(4L);
        when(fx.chatSessionMapper.selectList(any())).thenReturn(List.of(chat));

        fx.mvc.perform(get("/api/ai-chat/history/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].id").value(90));
    }

    @Test
    void latestReturnsMessagesForTeamMember() throws Exception {
        Fixtures fx = Fixtures.withScoringSession();
        AiChatSession chat = new AiChatSession();
        chat.setId(90L);
        chat.setMeetingId(4L);
        AiChatMessage message = new AiChatMessage();
        message.setId(1L);
        message.setSessionId(90L);
        message.setContent("本场依据");
        when(fx.chatSessionMapper.selectOne(any())).thenReturn(chat);
        when(fx.chatMessageMapper.selectList(any())).thenReturn(List.of(message));

        fx.mvc.perform(get("/api/ai-chat/latest/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.session.id").value(90))
                .andExpect(jsonPath("$.data.messages[0].content").value("本场依据"));
    }

    private static final class Fixtures {
        final AiChatSessionMapper chatSessionMapper = mock(AiChatSessionMapper.class);
        final AiChatMessageMapper chatMessageMapper = mock(AiChatMessageMapper.class);
        final AiScoringSessionService scoringSessionService = mock(AiScoringSessionService.class);
        final AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        final AiScoringSession scoring;
        final MockMvc mvc;

        private Fixtures(AiScoringSession scoring) {
            this.scoring = scoring;
            this.mvc = standaloneSetup(new AiChatController(
                    chatSessionMapper, chatMessageMapper, scoringSessionService, access)).build();
        }

        static Fixtures withScoringSession() {
            AiScoringSession scoring = new AiScoringSession();
            scoring.setId(21L);
            scoring.setMeetingId(4L);
            scoring.setTeamId(9L);
            scoring.setCreatedBy(7L);
            Fixtures fx = new Fixtures(scoring);
            when(fx.scoringSessionService.sessionForMeetingAccess(4L)).thenReturn(scoring);
            return fx;
        }

        static Fixtures withoutScoringSession() {
            Fixtures fx = new Fixtures(null);
            when(fx.scoringSessionService.sessionForMeetingAccess(4L)).thenReturn(null);
            return fx;
        }
    }
}
