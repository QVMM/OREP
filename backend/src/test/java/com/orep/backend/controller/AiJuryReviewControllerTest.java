package com.orep.backend.controller;

import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.service.AiJuryReviewService;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiJuryReviewControllerTest {

    @Test
    void startAndResultUseSessionIdAndDoNotExposeInternalFields() throws Exception {
        AiJuryReviewService service = mock(AiJuryReviewService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(88L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(88L)).thenReturn(accessSession);
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setSessionId(88L);
        response.setStatus("completed");
        response.setReviewMode("复核层");
        response.setOfficialScore(new BigDecimal("81.00"));
        response.setExplanation("评审团不修改基础AI评分。");
        when(service.startForSession(88L)).thenReturn(response);
        when(service.resultBySession(88L)).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiJuryReviewController(service, sessionService, access)).build();

        String startJson = mvc.perform(post("/api/ai-score/sessions/88/jury/start")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(88))
                .andExpect(jsonPath("$.data.reviewMode").value("复核层"))
                .andReturn().getResponse().getContentAsString();

        String resultJson = mvc.perform(get("/api/ai-score/sessions/88/jury/result")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(88))
                .andExpect(jsonPath("$.data.officialScore").value(81.00))
                .andReturn().getResponse().getContentAsString();

        assertThat(startJson + resultJson)
                .doesNotContain("prompt")
                .doesNotContain("rubric_hash")
                .doesNotContain("rubric_path")
                .doesNotContain("internal_version")
                .doesNotContain("weight");
    }

    @Test
    void legacyMeetingEndpointsReturnPlainJuryResponseForCompatibility() throws Exception {
        AiJuryReviewService service = mock(AiJuryReviewService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(21L);
        session.setTeamId(3L);
        when(sessionService.sessionForMeetingAccess(12L)).thenReturn(session);
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setMeetingId(12L);
        response.setStatus("completed");
        response.setReviewMode("复核层");
        when(service.startForLatestMeeting(12L)).thenReturn(response);
        when(service.resultByLatestMeeting(12L)).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiJuryReviewController(service, sessionService, access)).build();

        mvc.perform(post("/api/ai/jury/12/start")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.meetingId").value(12))
                .andExpect(jsonPath("$.reviewMode").value("复核层"));
        mvc.perform(get("/api/ai/jury/12/result")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.meetingId").value(12))
                .andExpect(jsonPath("$.status").value("completed"));
    }

    @Test
    void legacyMeetingResultRejectsCrossTeamUser() throws Exception {
        AiJuryReviewService service = mock(AiJuryReviewService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(21L);
        session.setTeamId(9L);
        when(sessionService.sessionForMeetingAccess(4L)).thenReturn(session);
        org.mockito.Mockito.doThrow(new org.springframework.web.server.ResponseStatusException(
                        org.springframework.http.HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));

        MockMvc mvc = standaloneSetup(new AiJuryReviewController(service, sessionService, access)).build();

        mvc.perform(get("/api/ai/jury/4/result")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }
}
