package com.orep.backend.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.PipelineStartResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.Iterator;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreResponseRedactionTest {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private static final String[] FORBIDDEN_FIELD_NAMES = {
            "rubricHash",
            "rubric_hash",
            "rubricPath",
            "rubric_path",
            "internalVersion",
            "internal_version",
            "rubricInternalVersion",
            "rubric_internal_version",
            "ruleEngineVersion",
            "rule_engine_version",
            "prompt",
            "weight",
            "evidenceSchemaId",
            "evidence_schema_id",
            "evidenceSchemaVersion",
            "evidence_schema_version",
            "evidenceSchemaHash",
            "evidence_schema_hash",
            "materialTypesJson",
            "frameTargetsJson",
            "demoActionsJson",
            "riskPatternsJson",
            "thirdPartyPackagingSignalsJson",
            "acceptableEvidenceLevelsJson"
    };

    private static final String[] FORBIDDEN_SECRET_VALUES = {
            "secret-rubric-hash",
            "/secret/rubric.md",
            "schema-secret-hash"
    };

    @Test
    void sessionCreateAndStatusResponsesDoNotLeakInternalRubricOrEvidenceSchemaData() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L)))
                .thenReturn(sessionWithInternalValues("created"));
        when(sessionService.getStatus(101L)).thenReturn(sessionWithInternalValues("scoring"));
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class))).build();

        String createJson = mvc.perform(post("/api/ai-score/sessions")
                        .requestAttr("userId", 7L)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"sourceType":"meeting_recording","meetingId":12,"projectId":3,"teamId":9,"trackId":"track-it","trackName":"新一代信息技术赛道"}
                                """))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        assertRedactedJson(createJson);
        AiScoreUserApiHardeningTest.assertNoForbiddenFields(createJson);

        String statusJson = mvc.perform(get("/api/ai-score/sessions/101/status")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        assertRedactedJson(statusJson);
        AiScoreUserApiHardeningTest.assertNoForbiddenFields(statusJson);
    }

    @Test
    void uploadSessionResponseDoesNotLeakInternalRubricOrEvidenceSchemaData() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreMediaAssetService assetService = mock(AiScoreMediaAssetService.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L)))
                .thenReturn(sessionWithInternalValues("created"));
        when(sessionService.markUploaded(101L)).thenReturn(sessionWithInternalValues("created"));
        when(sessionService.markPipelineQueued(101L)).thenReturn(sessionWithInternalValues("scoring"));
        com.orep.backend.entity.AiScoreMediaAsset videoAsset = new com.orep.backend.entity.AiScoreMediaAsset();
        videoAsset.setFilePath("ai-score/101/roadshow.mp4");
        videoAsset.setOriginalName("roadshow.mp4");
        when(assetService.getVideoAssetBySession(101L)).thenReturn(videoAsset);
        when(assetService.getMaterialAssetsBySession(101L)).thenReturn(java.util.List.of());
        AiScoringPipelineClient pipelineClient = mock(AiScoringPipelineClient.class);
        PipelineStartResponse pipelineResponse = new PipelineStartResponse();
        pipelineResponse.setAccepted(true);
        pipelineResponse.setTaskId("task-101");
        when(pipelineClient.startSessionPipeline(
                eq(101L), any(), eq(9L), eq(3L), eq("新一代信息技术赛道"),
                eq("uploaded_video"), any(), eq("roadshow.mp4"), any(), anyBoolean(), any()
        )).thenReturn(pipelineResponse);
        when(pipelineClient.startSessionPipeline(
                eq(101L), any(), eq(9L), eq(3L), any(), eq("新一代信息技术赛道"),
                any(), any(), eq("uploaded_video"), any(), eq("roadshow.mp4"), any(),
                anyBoolean(), any(), anyBoolean(), any()
        )).thenReturn(pipelineResponse);
        AiScoringSession uploadAccessSession = new AiScoringSession();
        uploadAccessSession.setId(101L);
        uploadAccessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(uploadAccessSession);
        MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, assetService, mock(AiScoreAccessControlService.class), pipelineClient, "./uploads")).build();
        MockMultipartFile video = new MockMultipartFile("video", "roadshow.mp4", "video/mp4", "video".getBytes());

        String responseJson = mvc.perform(multipart("/api/ai-score/upload-session")
                        .file(video)
                        .requestAttr("userId", 7L)
                        .param("projectId", "3")
                        .param("teamId", "9")
                        .param("trackId", "track-it")
                        .param("trackName", "新一代信息技术赛道"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertRedactedJson(responseJson);
        AiScoreUserApiHardeningTest.assertNoForbiddenFields(responseJson);
    }

    @Test
    void reportResponseDoesNotExposeInternalRubricOrEvidenceSchemaFieldNames() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(sessionService.reportBySession(eq(101L), any())).thenReturn(reportResponse());
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class))).build();

        String responseJson = mvc.perform(get("/api/ai-score/reports/by-session/101")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertRedactedJson(responseJson);
        AiScoreUserApiHardeningTest.assertNoForbiddenFields(responseJson);
    }

    private void assertRedactedJson(String responseJson) throws Exception {
        assertNoForbiddenFieldNames(OBJECT_MAPPER.readTree(responseJson), responseJson);
        for (String token : FORBIDDEN_SECRET_VALUES) {
            assertThat(responseJson)
                    .describedAs("user API JSON should not contain internal secret value <%s>: %s", token, responseJson)
                    .doesNotContain(token);
        }
    }

    private void assertNoForbiddenFieldNames(JsonNode node, String responseJson) {
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                for (String forbiddenFieldName : FORBIDDEN_FIELD_NAMES) {
                    assertThat(field.getKey())
                            .describedAs("user API JSON should not contain internal field name <%s>: %s", forbiddenFieldName, responseJson)
                            .isNotEqualTo(forbiddenFieldName);
                }
                assertNoForbiddenFieldNames(field.getValue(), responseJson);
            }
            return;
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                assertNoForbiddenFieldNames(child, responseJson);
            }
        }
    }

    private AiScoringSessionUserResponse sessionWithInternalValues(String status) {
        AiScoringSessionUserResponse response = new AiScoringSessionUserResponse();
        response.setSessionId(101L);
        response.setSessionNo("SC-20260623120000001");
        response.setStatus(status);
        response.setCurrentStage(status);
        response.setProgressPercent("scoring".equals(status) ? 10 : 0);
        response.setTrackName("新一代信息技术赛道");
        response.setSourceType("meeting_recording");
        response.setUseHistoryMemory(true);
        response.setJuryEnabled(false);
        response.setCached(false);
        response.setMeetingId(12L);
        response.setRubricHash("secret-rubric-hash");
        response.setRubricPath("/secret/rubric.md");
        response.setInternalVersion("internal-v1");
        return response;
    }

    private AiScoreReportUserResponse reportResponse() {
        AiScoreReportUserResponse response = new AiScoreReportUserResponse();
        response.setReportId(55L);
        response.setSessionId(101L);
        response.setSessionNo("SC-20260623120000001");
        response.setMeetingId(12L);
        response.setOverallScore(new BigDecimal("82.5"));
        response.setDimensionsJson("{\"技能水平\":82,\"商业价值\":85,\"note\":\"prompt wording and weight discussion are allowed as values\"}");
        response.setHighlightsJson("[\"结构清晰\",\"prompt 和 weight 可以作为普通报告文本出现\"]");
        response.setCriticalIssuesJson("[\"证据链仍需补强\"]");
        response.setImprovementPrioritiesJson("[\"补充用户案例\"]");
        response.setTranscript("路演转写内容");
        response.setSpeechQualityJson("{\"clarity\":80}");
        response.setScoreCalibrationJson("{\"demoCoverage\":75}");
        response.setModel("ai-score-v1");
        response.setStatus("completed");
        return response;
    }
}
