package com.orep.backend.service;

import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AiScoreRuleEngineTest {

    private final AiScoreRuleEngine engine = new AiScoreRuleEngine();

    @Test
    void scoresObservationsAndAggregatesDimensionsDeterministically() {
        AiScoreStructuredResultRequest request = request(List.of(
                observation("O01", "skill_level", "技能水平", "操作规范性", "10", "8", "5", "E2"),
                observation("O02", "skill_level", "技能水平", "技能熟练度", "15", "13", "12.75", "E5"),
                observation("O06", "professionalism", "职业素养", "职业道德与行为规范", "4", "3", "0.8", "E0")
        ), List.of(
                deduction("D-O01-1", "O01", "skill_level", "2", "1"),
                deduction("D-O02-1", "O02", "skill_level", "1", "1"),
                deduction("D-O06-1", "O06", "professionalism", "1", "1")
        ));
        AiScoreRecoveryInput recovery = recovery("D-O01-1", "verified", "1", "1", "已补充过程记录");

        AiScoreRuleEngineResult first = engine.score(request, List.of(recovery));
        AiScoreRuleEngineResult second = engine.score(request, List.of(recovery));

        assertEquals(new BigDecimal("17.00"), first.getDimensionScores().get("skill_level"));
        assertEquals(new BigDecimal("0.80"), first.getDimensionScores().get("professionalism"));
        assertEquals(new BigDecimal("17.80"), first.getFinalScore());
        assertEquals(first.getFinalScore(), second.getFinalScore());
        assertEquals(new BigDecimal("5.00"), first.getObservationResults().get(0).getFinalScore());
        assertEquals(new BigDecimal("6.00"), first.getObservationResults().get(0).getRawScore());
        assertEquals(new BigDecimal("12.00"), first.getObservationResults().get(1).getFinalScore());
        assertEquals(new BigDecimal("0.80"), first.getObservationResults().get(2).getFinalScore());
    }

    @Test
    void recoveryCannotExceedCurrentEvidenceCap() {
        AiScoreStructuredResultRequest request = request(List.of(
                observation("O01", "skill_level", "技能水平", "操作规范性", "10", "8", "5", "E2")
        ), List.of(
                deduction("D-O01-1", "O01", "skill_level", "2", "2")
        ));
        AiScoreRecoveryInput recovery = recovery("D-O01-1", "verified", "2", "2", "补齐材料");

        AiScoreRuleEngineResult result = engine.score(request, List.of(recovery));

        assertEquals(new BigDecimal("5.00"), result.getFinalScore());
        assertEquals(new BigDecimal("5.00"), result.getObservationResults().get(0).getFinalScore());
        assertEquals(new BigDecimal("2.00"), result.getRecoveredScore());
    }

    private AiScoreStructuredResultRequest request(
            List<AiScoreStructuredResultRequest.ObservationInput> observations,
            List<AiScoreStructuredResultRequest.DeductionInput> deductions
    ) {
        AiScoreStructuredResultRequest request = new AiScoreStructuredResultRequest();
        request.setSessionId(1L);
        request.setRuleEngineVersion("v1.2-engine-shadow");
        request.setObservations(observations);
        request.setDeductions(deductions);
        return request;
    }

    private AiScoreStructuredResultRequest.ObservationInput observation(
            String code,
            String dimensionCode,
            String dimensionName,
            String name,
            String maxScore,
            String rawScore,
            String scoreCap,
            String evidenceLevel
    ) {
        AiScoreStructuredResultRequest.ObservationInput input = new AiScoreStructuredResultRequest.ObservationInput();
        input.setObservationCode(code);
        input.setObservationName(name);
        input.setDimensionCode(dimensionCode);
        input.setDimensionName(dimensionName);
        input.setMaxScore(new BigDecimal(maxScore));
        input.setRawScore(new BigDecimal(rawScore));
        input.setScoreCap(new BigDecimal(scoreCap));
        input.setEvidenceLevel(evidenceLevel);
        input.setConfidence(new BigDecimal("0.90"));
        input.setValidityStatus("valid");
        input.setEvidenceAnchorIds(List.of(1L));
        return input;
    }

    private AiScoreStructuredResultRequest.DeductionInput deduction(
            String id,
            String observationCode,
            String dimensionCode,
            String points,
            String recoverable
    ) {
        AiScoreStructuredResultRequest.DeductionInput input = new AiScoreStructuredResultRequest.DeductionInput();
        input.setDeductionId(id);
        input.setObservationCode(observationCode);
        input.setDimensionCode(dimensionCode);
        input.setDeductedPoints(new BigDecimal(points));
        input.setMaxRecoverablePoints(new BigDecimal(recoverable));
        input.setReason("证据不足");
        input.setRequiredFix("补齐证据");
        input.setAcceptanceCriteria("证据可定位");
        input.setEvidenceLevel("E2");
        input.setConfidence(new BigDecimal("0.80"));
        input.setStatus("new");
        input.setEvidenceAnchorIds(List.of(1L));
        return input;
    }

    private AiScoreRecoveryInput recovery(
            String sourceDeductionId,
            String status,
            String requested,
            String max,
            String evidence
    ) {
        AiScoreRecoveryInput input = new AiScoreRecoveryInput();
        input.setSourceDeductionId(sourceDeductionId);
        input.setRecoveryStatus(status);
        input.setRequestedRecoverPoints(new BigDecimal(requested));
        input.setMaxRecoverablePoints(new BigDecimal(max));
        input.setAcceptanceEvidence(evidence);
        return input;
    }
}
