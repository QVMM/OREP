package com.orep.backend.controller;

import com.orep.backend.config.JwtUtil;
import com.orep.backend.config.AuthInterceptor;
import com.orep.backend.config.WebConfig;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.PipelineStartResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreUploadTaskService;
import com.orep.backend.service.MonitorService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(AiScoreUploadController.class)
@Import({AiScoreUploadController.class, WebConfig.class, AuthInterceptor.class})
class AiScoreUploadControllerWebMvcTest {

    @Autowired
    private MockMvc mvc;

    @MockBean
    private AiScoringSessionService sessionService;

    @MockBean
    private AiScoreMediaAssetService assetService;

    @MockBean
    private AiScoreAccessControlService accessControlService;

    @MockBean
    private AiScoringPipelineClient pipelineClient;

    @MockBean
    private AiScoreUploadTaskService uploadTaskService;

    @MockBean
    private JwtUtil jwtUtil;

    @MockBean
    private MonitorService monitorService;

    @Test
    void uploadSessionUsesSpringMvcWiringAndRedactsInternalFields() throws Exception {
        when(jwtUtil.validateToken("valid-token")).thenReturn(true);
        when(jwtUtil.getUserId("valid-token")).thenReturn(7L);
        when(jwtUtil.getUsername("valid-token")).thenReturn("tester");
        when(jwtUtil.getRole("valid-token")).thenReturn("student");
        when(jwtUtil.getTenantId("valid-token")).thenReturn(1L);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L))).thenReturn(session());
        when(sessionService.markUploaded(123L)).thenReturn(session());
        when(sessionService.markPipelineQueued(123L)).thenReturn(session("scoring", "queued", 5));
        when(assetService.getVideoAssetBySession(123L)).thenReturn(videoAsset());
        when(assetService.getMaterialAssetsBySession(123L)).thenReturn(java.util.List.of());
        PipelineStartResponse pipelineResponse = new PipelineStartResponse();
        pipelineResponse.setAccepted(true);
        pipelineResponse.setTaskId("task-123");
        when(pipelineClient.startSessionPipeline(
                eq(123L), any(), eq(9L), eq(3L), eq("track-it"), eq("新一代信息技术赛道"),
                eq("internal-v1"), eq("secret-rubric-hash"), eq("uploaded_video"), any(),
                eq("roadshow.mp4"), any(), anyBoolean(), any(), anyBoolean(), any()
        )).thenReturn(pipelineResponse);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(123L);
        accessSession.setCreatedBy(7L);
        accessSession.setTrackId("track-it");
        accessSession.setTrackName("新一代信息技术赛道");
        accessSession.setRubricInternalVersion("internal-v1");
        accessSession.setRubricHash("secret-rubric-hash");
        when(sessionService.requireSessionForAccess(123L)).thenReturn(accessSession);

        MockMultipartFile video = new MockMultipartFile("video", "roadshow.mp4", "video/mp4", "video".getBytes());

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .header("Authorization", "Bearer valid-token")
                        .param("projectId", "3")
                        .param("teamId", "9")
                        .param("trackId", "track-it")
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(123))
                .andExpect(jsonPath("$.data.sourceType").value("uploaded_video"))
                .andExpect(jsonPath("$.data.rubricHash").doesNotExist())
                .andExpect(jsonPath("$.data.rubricPath").doesNotExist())
                .andExpect(jsonPath("$.data.internalVersion").doesNotExist());
    }

    private AiScoringSessionUserResponse session() {
        return session("created", "uploaded", 0);
    }

    private AiScoringSessionUserResponse session(String status, String stage, int progress) {
        AiScoringSessionUserResponse response = new AiScoringSessionUserResponse();
        response.setSessionId(123L);
        response.setSessionNo("SC-20260623180000001");
        response.setStatus(status);
        response.setCurrentStage(stage);
        response.setProgressPercent(progress);
        response.setTrackName("新一代信息技术赛道");
        response.setSourceType("uploaded_video");
        response.setUseHistoryMemory(true);
        response.setJuryEnabled(false);
        response.setCached(false);
        response.setRubricHash("secret-rubric-hash");
        response.setRubricPath("/secret/rubric.md");
        response.setInternalVersion("internal-v1");
        return response;
    }

    private com.orep.backend.entity.AiScoreMediaAsset videoAsset() {
        com.orep.backend.entity.AiScoreMediaAsset asset = new com.orep.backend.entity.AiScoreMediaAsset();
        asset.setFilePath("ai-score/123/roadshow.mp4");
        asset.setOriginalName("roadshow.mp4");
        return asset;
    }

    @SpringBootConfiguration
    @EnableAutoConfiguration
    static class TestApplication {
    }
}
