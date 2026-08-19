package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreEvidenceBundleControllerTest {

    @Test
    void prepareEvidenceReturnsUserSafeBundleStatus() throws Exception {
        AiScoreEvidenceBundleService evidenceService = mock(AiScoreEvidenceBundleService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreEvidenceBundleResponse response = response();
        when(evidenceService.prepareEvidence(123L)).thenReturn(response);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(123L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(123L)).thenReturn(accessSession);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                evidenceService,
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class)
        )).build();

        mvc.perform(post("/api/ai-score/sessions/123/prepare-evidence")
                        .requestAttr("userId", 7L))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(123))
                .andExpect(jsonPath("$.data.snapshotStatus").value("ready"))
                .andExpect(jsonPath("$.data.mediaAssetCount").value(1))
                .andExpect(jsonPath("$.data.transcriptSegmentCount").value(3))
                .andExpect(jsonPath("$.data.frameCount").value(3))
                .andExpect(jsonPath("$.data.evidenceAnchorCount").value(6));

        verify(sessionService).markEvidencePreparing(123L);
        verify(sessionService).markEvidenceReady(123L);
    }

    @Test
    void latestEvidenceBundleReturnsMissingStatusBeforePreparation() throws Exception {
        AiScoreEvidenceBundleService evidenceService = mock(AiScoreEvidenceBundleService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(123L);
        response.setSnapshotStatus("missing");
        response.setMediaAssetCount(0);
        response.setTranscriptSegmentCount(0);
        response.setFrameCount(0);
        response.setEvidenceAnchorCount(0);
        when(evidenceService.latestBundle(123L)).thenReturn(response);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(123L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(123L)).thenReturn(accessSession);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                evidenceService,
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class)
        )).build();

        mvc.perform(get("/api/ai-score/sessions/123/evidence-bundle")
                        .requestAttr("userId", 7L))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(123))
                .andExpect(jsonPath("$.data.snapshotStatus").value("missing"))
                .andExpect(jsonPath("$.data.mediaAssetCount").value(0));
    }

    @Test
    void prepareEvidenceReturnsOriginalConflictWhenFailureCompensationAlsoFails() throws Exception {
        AiScoreEvidenceBundleService evidenceService = mock(AiScoreEvidenceBundleService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(evidenceService.prepareEvidence(123L)).thenThrow(new IllegalStateException("未找到可用媒体资产"));
        doThrow(new IllegalStateException("补偿失败"))
                .when(sessionService).markFailed(eq(123L), eq("未找到可用媒体资产"), eq("evidence_failed"));
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(123L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(123L)).thenReturn(accessSession);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                evidenceService,
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class)
        )).build();

        mvc.perform(post("/api/ai-score/sessions/123/prepare-evidence")
                        .requestAttr("userId", 7L))
                .andExpect(jsonPath("$.code").value(409))
                .andExpect(jsonPath("$.message").value("未找到可用媒体资产"));

        verify(sessionService).markEvidencePreparing(123L);
        verify(sessionService).markFailed(123L, "未找到可用媒体资产", "evidence_failed");
    }

    private AiScoreEvidenceBundleResponse response() {
        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(123L);
        response.setSnapshotStatus("ready");
        response.setMediaAssetCount(1);
        response.setTranscriptSegmentCount(3);
        response.setFrameCount(3);
        response.setEvidenceAnchorCount(6);
        return response;
    }
}
