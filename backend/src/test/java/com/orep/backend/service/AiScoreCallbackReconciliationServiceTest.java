package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AiScoreCallbackReconciliationServiceTest {

    private final AiScoreCallbackReconciliationService service =
            new AiScoreCallbackReconciliationService(new AiScoreRuleEngine());

    @Test
    void acceptsMatchingAuthoritativeScore() {
        PipelineCallbackRequest.PipelineFinalResult result = authoritativeResult("13.00");

        assertDoesNotThrow(() -> service.reconcile(result));
        assertEquals(new BigDecimal("13.00"), service.reconcile(result).getFinalScore());
    }

    @Test
    void rejectsMismatchedAuthoritativeScore() {
        PipelineCallbackRequest.PipelineFinalResult result = authoritativeResult("15.00");

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.reconcile(result)
        );

        assertEquals("Python authoritative score 15.00 does not match Java recomputed score 13.00", error.getMessage());
    }

    @Test
    void rejectsAuthoritativeResultWithoutObservations() {
        PipelineCallbackRequest.PipelineFinalResult result = authoritativeResult("13.00");
        result.setObservations(List.of());

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.reconcile(result)
        );

        assertEquals("authoritative score requires canonical observations", error.getMessage());
    }

    @Test
    void permitsExplicitLegacyResultWithoutRecomputing() {
        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("legacy_llm");
        result.setOverallScore(new BigDecimal("68"));

        assertEquals(new BigDecimal("68"), service.reconcile(result).getFinalScore());
    }

    @Test
    void acceptsCompleteV3LossLedgerAndTaskCoverage() {
        PipelineCallbackRequest.PipelineFinalResult result = completeV3Result();

        assertDoesNotThrow(() -> service.reconcile(result));
    }

    @Test
    void rejectsV3LossLedgerThatDoesNotExplainFullGap() {
        PipelineCallbackRequest.PipelineFinalResult result = completeV3Result();
        result.setLossLedgerJson("[{\"lossId\":\"l1\",\"points\":49.0,\"scoreBudgetKey\":\"O1:performance\"}]");

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.reconcile(result)
        );

        assertEquals("loss ledger does not reconcile with official score", error.getMessage());
    }

    @Test
    void rejectsV3CompletePortfolioWithUnknownCoveredLoss() {
        PipelineCallbackRequest.PipelineFinalResult result = completeV3Result();
        result.setActionPlanJson("[{\"taskId\":\"t1\",\"coveredLossIds\":[\"missing\"]}]");

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.reconcile(result)
        );

        assertEquals("remediation task references unknown lossId missing", error.getMessage());
    }

    private PipelineCallbackRequest.PipelineFinalResult authoritativeResult(String overallScore) {
        PipelineCallbackRequest.ObservationInput observation = new PipelineCallbackRequest.ObservationInput();
        observation.setObservationCode("O1");
        observation.setDimensionCode("D1");
        observation.setMaxScore(new BigDecimal("20"));
        observation.setBaseScore(new BigDecimal("16"));
        observation.setScoreCap(new BigDecimal("14"));

        PipelineCallbackRequest.DeductionInput deduction = new PipelineCallbackRequest.DeductionInput();
        deduction.setDeductionId("O1:missing-proof");
        deduction.setObservationCode("O1");
        deduction.setDimensionCode("D1");
        deduction.setDeductedPoints(new BigDecimal("3"));
        deduction.setMaxRecoverablePoints(new BigDecimal("2"));
        deduction.setStatus("new");

        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("structured_rule_engine");
        result.setOverallScore(new BigDecimal(overallScore));
        result.setObservations(List.of(observation));
        result.setDeductions(List.of(deduction));
        return result;
    }

    private PipelineCallbackRequest.PipelineFinalResult completeV3Result() {
        PipelineCallbackRequest.ObservationInput observation = new PipelineCallbackRequest.ObservationInput();
        observation.setObservationCode("O1");
        observation.setDimensionCode("D1");
        observation.setMaxScore(new BigDecimal("100"));
        observation.setBaseScore(new BigDecimal("50"));
        observation.setScoreCap(new BigDecimal("100"));

        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setContractVersion("ai-score-report-v3");
        result.setScoreAuthority("structured_rule_engine");
        result.setOverallScore(new BigDecimal("50"));
        result.setObservations(List.of(observation));
        result.setDeductions(List.of());
        result.setLossLedgerJson("[{\"lossId\":\"l1\",\"lossKey\":\"rule:O1:performance\",\"points\":50.0,\"scoreBudgetKey\":\"O1:performance\"}]");
        result.setActionPlanJson("[{\"taskId\":\"t1\",\"coveredLossIds\":[\"l1\"]}]");
        result.setCoverageSummaryJson("{\"coverageRate\":1.0,\"status\":\"complete\",\"uncoveredLossIds\":[]}");
        result.setTodoPortfolioStatus("complete");
        return result;
    }
}
