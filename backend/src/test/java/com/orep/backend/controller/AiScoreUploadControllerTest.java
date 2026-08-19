package com.orep.backend.controller;

import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.PipelineStartResponse;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreUploadControllerTest {

    @Test
    void meetingRecordingUploadsIntoTheSameAuthoritativePipeline() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        AiScoringPipelineClient pipelineClient = mock(AiScoringPipelineClient.class);
        AiScoringSession dispatch = dispatchSession();
        dispatch.setSessionNo("SC-20260623180000001");
        dispatch.setSourceType("meeting_recording");
        dispatch.setMeetingId(88L);
        dispatch.setTeamId(9L);
        dispatch.setProjectId(3L);
        when(sessionService.requireSessionForAccess(123L)).thenReturn(dispatch);
        when(sessionService.markUploaded(123L)).thenReturn(session("created", "uploaded", 0));
        when(sessionService.markPipelineQueued(123L)).thenReturn(session("scoring", "queued", 5));
        when(assetService.storeMeetingVideo(eq(123L), any(), eq(7L))).thenReturn(asset("video"));
        when(assetService.getVideoAssetBySession(123L)).thenReturn(asset("video"));
        when(assetService.getMaterialAssetsBySession(123L)).thenReturn(java.util.List.of());
        PipelineStartResponse accepted = new PipelineStartResponse();
        accepted.setAccepted(true);
        when(pipelineClient.startSessionPipeline(anyLong(), anyString(), any(), any(),
                anyString(), anyString(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyList(), anyBoolean(), any(), anyBoolean(), anyString()))
                .thenReturn(accepted);

        MockMvc mvc = standaloneSetup(new AiScoreUploadController(
                sessionService, assetService, mock(AiScoreAccessControlService.class),
                pipelineClient, "./uploads"
        )).build();
        MockMultipartFile recording = new MockMultipartFile(
                "audio", "meeting.webm", "video/webm", "audio-video".getBytes()
        );

        mvc.perform(multipart("/api/ai-score/sessions/123/meeting-media")
                        .file(recording)
                        .requestAttr("userId", 7L)
                        .requestAttr("tenantId", 3L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.status").value("scoring"))
                .andExpect(jsonPath("$.data.currentStage").value("queued"));

        verify(assetService).storeMeetingVideo(eq(123L), any(), eq(7L));
        verify(pipelineClient).startSessionPipeline(
                eq(123L), anyString(), eq(9L), eq(3L),
                eq("track-it"), eq("新一代信息技术赛道"), eq("v1.2"), eq("sha256:test"),
                eq("meeting_recording"), contains("test-video.mp4"), eq("test.mp4"), anyList(), anyBoolean(),
                any(), anyBoolean(),
                contains("/api/ai-score/sessions/123/pipeline-callback")
        );
    }

    @Test
    void uploadsVideoCreatesSessionAndReturnsRedactedResponse() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L))).thenReturn(session("created"));
        when(sessionService.markUploaded(123L)).thenReturn(session("created"));
        when(sessionService.markPipelineQueued(123L)).thenReturn(session("scoring", "queued", 5));
        when(sessionService.requireSessionForAccess(123L)).thenReturn(dispatchSession());
        when(assetService.storeVideo(eq(123L), any(), eq(7L))).thenReturn(asset("video"));
        when(assetService.storeMaterial(eq(123L), any(), eq(7L))).thenReturn(asset("material"));
        when(assetService.getVideoAssetBySession(123L)).thenReturn(asset("video"));
        when(assetService.getMaterialAssetsBySession(123L)).thenReturn(java.util.List.of());
        AiScoringPipelineClient pipelineClient = mock(AiScoringPipelineClient.class);
        PipelineStartResponse pipelineResponse = new PipelineStartResponse();
        pipelineResponse.setAccepted(true);
        pipelineResponse.setMessage("accepted");
        pipelineResponse.setTaskId("task-123");
        when(pipelineClient.startSessionPipeline(anyLong(), anyString(), any(), any(),
                anyString(), anyString(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyList(), anyBoolean(), any(), anyBoolean(), anyString()))
                .thenReturn(pipelineResponse);
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, assetService, mock(AiScoreAccessControlService.class), pipelineClient, "./uploads")).build();

        MockMultipartFile video = new MockMultipartFile("video", "roadshow.mp4", "video/mp4", "video".getBytes());
        MockMultipartFile material = new MockMultipartFile("materials", "bp.pdf", "application/pdf", "pdf".getBytes());

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .file(material)
                        .requestAttr("userId", 7L)
                        .requestAttr("tenantId", 3L)
                        .requestAttr("role", "STUDENT")
                        .param("projectId", "3")
                        .param("teamId", "9")
                        .param("trackId", "track-it")
                        .param("trackName", "新一代信息技术赛道")
                        .param("useHistoryMemory", "true")
                        .param("juryEnabled", "false"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(123))
                .andExpect(jsonPath("$.data.status").value("scoring"))
                .andExpect(jsonPath("$.data.currentStage").value("queued"))
                .andExpect(jsonPath("$.data.progressPercent").value(5))
                .andExpect(jsonPath("$.data.sourceType").value("uploaded_video"))
                .andExpect(jsonPath("$.data.rubric_hash").doesNotExist())
                .andExpect(jsonPath("$.data.rubricPath").doesNotExist())
                .andExpect(jsonPath("$.data.internalVersion").doesNotExist())
                .andExpect(jsonPath("$.data.prompt").doesNotExist())
                .andExpect(jsonPath("$.data.weight").doesNotExist());

        verify(assetService).storeVideo(eq(123L), any(), eq(7L));
        verify(assetService).storeMaterial(eq(123L), any(), eq(7L));
        verify(pipelineClient).startSessionPipeline(
                eq(123L), anyString(), eq(9L), eq(3L),
                eq("track-it"), eq("新一代信息技术赛道"), eq("v1.2"), eq("sha256:test"),
                eq("uploaded_video"), contains("test-video.mp4"), eq("test.mp4"), anyList(), anyBoolean(),
                any(), anyBoolean(),
                contains("/api/ai-score/sessions/123/pipeline-callback")
        );
    }

    @Test
    void uploadReturnsFailedSessionWhenPipelineDispatchFails() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        AiScoringPipelineClient pipelineClient = mock(AiScoringPipelineClient.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L))).thenReturn(session("created"));
        when(sessionService.markUploaded(123L)).thenReturn(session("created", "uploaded", 0));
        when(sessionService.markPipelineQueued(123L)).thenReturn(session("scoring", "queued", 5));
        when(sessionService.requireSessionForAccess(123L)).thenReturn(dispatchSession());
        when(sessionService.markFailed(eq(123L), contains("AI分析未启动"), eq("pipeline_dispatch_failed")))
                .thenReturn(session("failed", "pipeline_dispatch_failed", 5));
        when(assetService.storeVideo(eq(123L), any(), eq(7L))).thenReturn(asset("video"));
        when(assetService.getVideoAssetBySession(123L)).thenReturn(asset("video"));
        when(assetService.getMaterialAssetsBySession(123L)).thenReturn(java.util.List.of());
        PipelineStartResponse pipelineResponse = new PipelineStartResponse();
        pipelineResponse.setAccepted(false);
        pipelineResponse.setMessage("AI 服务调用失败: Connection refused");
        when(pipelineClient.startSessionPipeline(anyLong(), anyString(), any(), any(),
                anyString(), anyString(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyList(), anyBoolean(), any(), anyBoolean(), anyString()))
                .thenReturn(pipelineResponse);
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, assetService, mock(AiScoreAccessControlService.class), pipelineClient, "./uploads")).build();

        MockMultipartFile video = new MockMultipartFile("video", "roadshow.mp4", "video/mp4", "video".getBytes());

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .requestAttr("userId", 7L)
                        .requestAttr("tenantId", 3L)
                        .requestAttr("role", "STUDENT")
                        .param("teamId", "9")
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.status").value("failed"))
                .andExpect(jsonPath("$.data.currentStage").value("pipeline_dispatch_failed"))
                .andExpect(jsonPath("$.data.message").value("AI分析未启动：AI 服务连接失败（AI 服务调用失败: Connection refused）"));
    }

    @Test
    void uploadReportsIncompleteBindingWithoutClaimingServiceDisconnected() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        AiScoringPipelineClient pipelineClient = mock(AiScoringPipelineClient.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L))).thenReturn(session("created"));
        when(sessionService.markUploaded(123L)).thenReturn(session("created", "uploaded", 0));
        when(sessionService.markPipelineQueued(123L)).thenReturn(session("scoring", "queued", 5));
        when(sessionService.requireSessionForAccess(123L)).thenReturn(dispatchSession());
        when(sessionService.markFailed(eq(123L), contains("评分绑定信息不完整"), eq("pipeline_dispatch_failed")))
                .thenReturn(session("failed", "pipeline_dispatch_failed", 5));
        when(assetService.storeVideo(eq(123L), any(), eq(7L))).thenReturn(asset("video"));
        when(assetService.getVideoAssetBySession(123L)).thenReturn(asset("video"));
        when(assetService.getMaterialAssetsBySession(123L)).thenReturn(java.util.List.of());
        PipelineStartResponse pipelineResponse = new PipelineStartResponse();
        pipelineResponse.setAccepted(false);
        pipelineResponse.setMessage("track_confirmation_required");
        when(pipelineClient.startSessionPipeline(anyLong(), anyString(), any(), any(),
                anyString(), anyString(), anyString(), anyString(),
                anyString(), anyString(), anyString(), anyList(), anyBoolean(), any(), anyBoolean(), anyString()))
                .thenReturn(pipelineResponse);
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(
                sessionService,
                assetService,
                mock(AiScoreAccessControlService.class),
                pipelineClient,
                "./uploads"
        )).build();

        MockMultipartFile video = new MockMultipartFile("video", "roadshow.mp4", "video/mp4", "video".getBytes());

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .requestAttr("userId", 7L)
                        .requestAttr("tenantId", 3L)
                        .requestAttr("role", "STUDENT")
                        .param("teamId", "9")
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.message").value("AI分析未启动：评分绑定信息不完整（track_confirmation_required）"))
                .andExpect(jsonPath("$.data.message").value(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("本地 ai-scoring 服务未连接"))));
    }

    @Test
    void rejectsRequestWithoutVideo() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, mock(AiScoreMediaAssetService.class), mock(AiScoreAccessControlService.class), mock(AiScoringPipelineClient.class), "./uploads")).build();

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .requestAttr("userId", 7L)
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400));

        verify(sessionService, never()).createSession(any(), any());
    }

    @Test
    void marksSessionFailedWhenAssetStoreFails() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L))).thenReturn(session("created"));
        when(sessionService.requireSessionForAccess(123L)).thenReturn(dispatchSession());
        when(assetService.storeVideo(eq(123L), any(), eq(7L))).thenThrow(new IllegalArgumentException("视频格式不支持"));
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, assetService, mock(AiScoreAccessControlService.class), mock(AiScoringPipelineClient.class), "./uploads")).build();
        MockMultipartFile video = new MockMultipartFile("video", "bad.exe", "application/octet-stream", "x".getBytes());

        mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .requestAttr("userId", 7L)
                        .requestAttr("tenantId", 3L)
                        .requestAttr("role", "STUDENT")
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("视频格式不支持"));

        verify(sessionService).markFailed(123L, "视频格式不支持");
    }

    private AiScoringSessionUserResponse session(String status) {
        return session(status, "uploaded", 0);
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
        return response;
    }

    private AiScoringSession dispatchSession() {
        AiScoringSession session = new AiScoringSession();
        session.setId(123L);
        session.setCreatedBy(7L);
        session.setTrackId("track-it");
        session.setTrackName("新一代信息技术赛道");
        session.setRubricInternalVersion("v1.2");
        session.setRubricHash("sha256:test");
        return session;
    }

    private AiScoreMediaAsset asset(String type) {
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(1L);
        asset.setSessionId(123L);
        asset.setAssetType(type);
        asset.setSourceType("uploaded_video");
        asset.setStatus("uploaded");
        asset.setFilePath("ai-score/123/test-" + type + "." + ("video".equals(type) ? "mp4" : "pdf"));
        asset.setOriginalName("test." + ("video".equals(type) ? "mp4" : "pdf"));
        return asset;
    }
}
