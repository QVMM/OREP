package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreStructuredResultControllerTest {

    @Test
    void structuredResultReturnsUserSafeRuleEngineResult() throws Exception {
        AiScoreStructuredResultService structuredResultService = mock(AiScoreStructuredResultService.class);
        when(structuredResultService.applyStructuredResult(eq(123L), any(AiScoreStructuredResultRequest.class), eq(List.of())))
                .thenReturn(ruleEngineResult());
        MockMvc mvc = standaloneSetup(controller(structuredResultService)).build();

        String responseJson = mvc.perform(post("/api/ai-score/sessions/123/structured-result")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(validJson()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.finalScore").value(95))
                .andExpect(jsonPath("$.data.rawScore").value(100))
                .andExpect(jsonPath("$.data.currentScoreCap").value(100))
                .andExpect(jsonPath("$..rubric_hash").doesNotExist())
                .andExpect(jsonPath("$..rubric_path").doesNotExist())
                .andExpect(jsonPath("$..internal_version").doesNotExist())
                .andExpect(jsonPath("$..prompt").doesNotExist())
                .andExpect(jsonPath("$..weight").doesNotExist())
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertThat(responseJson).doesNotContain("ruleEngineVersion");

        ArgumentCaptor<AiScoreStructuredResultRequest> requestCaptor =
                ArgumentCaptor.forClass(AiScoreStructuredResultRequest.class);
        verify(structuredResultService).applyStructuredResult(eq(123L), requestCaptor.capture(), eq(List.of()));
        assertThat(requestCaptor.getValue().getSessionId()).isEqualTo(123L);
    }

    @Test
    void structuredResultReturnsBadRequestWhenServiceRejectsRequest() throws Exception {
        AiScoreStructuredResultService structuredResultService = mock(AiScoreStructuredResultService.class);
        when(structuredResultService.applyStructuredResult(eq(123L), any(AiScoreStructuredResultRequest.class), eq(List.of())))
                .thenThrow(new IllegalArgumentException("sessionId mismatch"));
        MockMvc mvc = standaloneSetup(controller(structuredResultService)).build();

        mvc.perform(post("/api/ai-score/sessions/123/structured-result")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(validJson()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("sessionId mismatch"));
    }

    @Test
    void structuredResultAcceptsRecoveryClaimsAndKeepsResponseRedacted() throws Exception {
        AiScoreStructuredResultService structuredResultService = mock(AiScoreStructuredResultService.class);
        AiScoreRuleEngineResult result = ruleEngineResult();
        result.setRecoveredScore(new BigDecimal("6"));
        result.setFinalScore(new BigDecimal("100"));
        when(structuredResultService.applyStructuredResult(eq(123L), any(AiScoreStructuredResultRequest.class), eq(List.of())))
                .thenReturn(result);
        MockMvc mvc = standaloneSetup(controller(structuredResultService)).build();

        String responseJson = mvc.perform(post("/api/ai-score/sessions/123/structured-result")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(validRecoveryJson()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.finalScore").value(100))
                .andExpect(jsonPath("$.data.recoveredScore").value(6))
                .andExpect(jsonPath("$.data.ruleEngineVersion").doesNotExist())
                .andExpect(jsonPath("$..rubric_hash").doesNotExist())
                .andExpect(jsonPath("$..rubric_path").doesNotExist())
                .andExpect(jsonPath("$..internal_version").doesNotExist())
                .andExpect(jsonPath("$..prompt").doesNotExist())
                .andExpect(jsonPath("$..weight").doesNotExist())
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertThat(responseJson)
                .doesNotContain("ruleEngineVersion")
                .doesNotContain("rubric_hash")
                .doesNotContain("rubric_path")
                .doesNotContain("internal_version")
                .doesNotContain("prompt")
                .doesNotContain("weight");

        ArgumentCaptor<AiScoreStructuredResultRequest> requestCaptor =
                ArgumentCaptor.forClass(AiScoreStructuredResultRequest.class);
        verify(structuredResultService).applyStructuredResult(eq(123L), requestCaptor.capture(), eq(List.of()));
        AiScoreStructuredResultRequest request = requestCaptor.getValue();
        assertThat(request.getRecoveryClaims()).hasSize(1);
        assertThat(request.getRecoveryClaims().getFirst().getSourceDeductionId()).isEqualTo("previous-demo-failure");
        assertThat(request.getRecoveryClaims().getFirst().getEvidenceAnchorIds()).containsExactly(10L);
    }

    private AiScoreController controller(AiScoreStructuredResultService structuredResultService) {
        return new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                mock(AiScoringSessionService.class),
                mock(AiScoreEvidenceBundleService.class),
                structuredResultService,
                mock(AiScoreAccessControlService.class)
        );
    }

    private AiScoreRuleEngineResult ruleEngineResult() {
        AiScoreRuleEngineResult result = new AiScoreRuleEngineResult();
        result.setRuleEngineVersion("p8-e-test");
        result.setBaseScore(new BigDecimal("100"));
        result.setRawScore(new BigDecimal("100"));
        result.setDeductedScore(new BigDecimal("5"));
        result.setRecoveredScore(BigDecimal.ZERO);
        result.setCurrentScoreCap(new BigDecimal("100"));
        result.setFinalScore(new BigDecimal("95"));
        result.setNotPerfectReasons(List.of("current_deductions"));
        result.setObservations(List.of());
        result.setDeductions(List.of());
        result.setRecoveries(List.of());
        return result;
    }

    private String validJson() {
        return """
                {
                  "sessionId": 123,
                  "ruleEngineVersion": "p8-e-test",
                  "scoreSummary": {
                    "rawTotalScore": 100,
                    "finalScore": 95,
                    "scoreCap": 100
                  },
                  "observations": [],
                  "deductions": []
                }
                """;
    }

    private String validRecoveryJson() {
        return """
                {
                  "sessionId": 123,
                  "ruleEngineVersion": "p9-test",
                  "scoreSummary": {
                    "rawTotalScore": 95,
                    "finalScore": 95,
                    "scoreCap": 100
                  },
                  "observations": [
                    {
                      "observationCode": "tech_demo",
                      "dimensionCode": "technology",
                      "dimensionName": "技术能力",
                      "rawScore": 100,
                      "scoreCap": 100,
                      "evidenceLevel": "strong",
                      "confidence": 0.91,
                      "validityStatus": "valid",
                      "modelReason": "现场演示证据充分",
                      "evidenceAnchorIds": [10]
                    }
                  ],
                  "deductions": [],
                  "recoveryClaims": [
                    {
                      "sourceDeductionId": "previous-demo-failure",
                      "recoveryStatus": "fixed",
                      "requestedRecoverPoints": 6,
                      "acceptanceEvidence": "本轮视频显示核心演示流程稳定跑通",
                      "evidenceAnchorIds": [10]
                    }
                  ]
                }
                """;
    }
}
