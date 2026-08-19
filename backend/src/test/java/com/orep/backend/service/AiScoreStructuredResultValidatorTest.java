package com.orep.backend.service;

import com.orep.backend.dto.AiScoreStructuredResultRequest;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AiScoreStructuredResultValidatorTest {

    private final AiScoreStructuredResultValidator validator = new AiScoreStructuredResultValidator();

    @Test
    void validatesCompleteStructuredResult() {
        assertDoesNotThrow(() -> validator.validate(validRequest()));
    }

    @Test
    void rejectsMissingObservations() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setObservations(List.of());

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("observations"));
    }

    @Test
    void rejectsInvalidScoreRange() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getObservations().getFirst().setRawScore(new BigDecimal("101"));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("observations[0].rawScore"));
    }

    @Test
    void rejectsInvalidEvidenceLevel() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getObservations().getFirst().setEvidenceLevel("unsupported");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("observations[0].evidenceLevel"));
    }

    @Test
    void rejectsDeductionReferenceToMissingObservation() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setObservationCode("missing_observation");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].observationCode"));
    }

    @Test
    void rejectsDeductionMissingReason() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setReason(" ");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].reason"));
    }

    @Test
    void rejectsDeductionMissingDeductionId() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setDeductionId(" ");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].deductionId"));
    }

    @Test
    void rejectsNegativeEvidenceAnchorId() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getObservations().getFirst().setEvidenceAnchorIds(List.of(10L, -1L));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("observations[0].evidenceAnchorIds[1]"));
    }

    @Test
    void rejectsEmptyEvidenceAnchorIds() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setEvidenceAnchorIds(List.of());

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].evidenceAnchorIds"));
    }

    @Test
    void rejectsDeductionMissingConfidence() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setConfidence(null);

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].confidence"));
    }

    @Test
    void rejectsDeductionScoreOverOneHundred() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setDeductedPoints(new BigDecimal("101"));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].deductedPoints"));
    }

    @Test
    void rejectsMaxRecoverableGreaterThanDeductedPoints() {
        AiScoreStructuredResultRequest request = validRequest();
        request.getDeductions().getFirst().setDeductedPoints(new BigDecimal("2"));
        request.getDeductions().getFirst().setMaxRecoverablePoints(new BigDecimal("3"));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("deductions[0].maxRecoverablePoints"));
    }

    @Test
    void validatesCompleteRecoveryClaim() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));

        assertDoesNotThrow(() -> validator.validate(request));
    }

    @Test
    void rejectsRecoveryClaimMissingSourceDeductionId() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setSourceDeductionId(" ");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("recoveryClaims[0].sourceDeductionId"));
    }

    @Test
    void rejectsAcceptedRecoveryClaimMissingAcceptanceEvidence() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setAcceptanceEvidence(" ");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("recoveryClaims[0].acceptanceEvidence"));
    }

    @Test
    void rejectsRecoveryClaimNegativeRequestedRecoverPoints() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setRequestedRecoverPoints(new BigDecimal("-0.1"));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("recoveryClaims[0].requestedRecoverPoints"));
    }

    @Test
    void rejectsAcceptedRecoveryClaimEmptyEvidenceAnchorIds() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setEvidenceAnchorIds(List.of());

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("recoveryClaims[0].evidenceAnchorIds"));
    }

    @Test
    void allowsPendingRecoveryClaimWithoutEvidenceAnchorIds() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setRecoveryStatus("pending");
        request.getRecoveryClaims().getFirst().setAcceptanceEvidence(null);
        request.getRecoveryClaims().getFirst().setEvidenceAnchorIds(null);

        assertDoesNotThrow(() -> validator.validate(request));
    }

    @Test
    void rejectsNegativeOptionalRecoveryClaimEvidenceAnchorId() {
        AiScoreStructuredResultRequest request = validRequest();
        request.setRecoveryClaims(List.of(recoveryClaim()));
        request.getRecoveryClaims().getFirst().setRecoveryStatus("pending");
        request.getRecoveryClaims().getFirst().setEvidenceAnchorIds(List.of(10L, -1L));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> validator.validate(request)
        );

        assertTrue(exception.getMessage().contains("recoveryClaims[0].evidenceAnchorIds[1]"));
    }

    private AiScoreStructuredResultRequest validRequest() {
        AiScoreStructuredResultRequest request = new AiScoreStructuredResultRequest();
        request.setSessionId(123L);
        request.setRuleEngineVersion("p8-b-test");
        request.setScoreSummary(scoreSummary());
        request.setObservations(List.of(observation()));
        request.setDeductions(List.of(deduction()));
        return request;
    }

    private AiScoreStructuredResultRequest.ScoreSummary scoreSummary() {
        AiScoreStructuredResultRequest.ScoreSummary summary = new AiScoreStructuredResultRequest.ScoreSummary();
        summary.setRawTotalScore(new BigDecimal("88.5"));
        summary.setFinalScore(new BigDecimal("86"));
        summary.setScoreCap(new BigDecimal("100"));
        return summary;
    }

    private AiScoreStructuredResultRequest.ObservationInput observation() {
        AiScoreStructuredResultRequest.ObservationInput observation = new AiScoreStructuredResultRequest.ObservationInput();
        observation.setObservationCode("market_need");
        observation.setDimensionCode("market");
        observation.setDimensionName("市场需求");
        observation.setRawScore(new BigDecimal("88.5"));
        observation.setScoreCap(new BigDecimal("100"));
        observation.setEvidenceLevel("strong");
        observation.setConfidence(new BigDecimal("0.92"));
        observation.setValidityStatus("valid");
        observation.setEvidenceAnchorIds(List.of(10L, 11L));
        return observation;
    }

    private AiScoreStructuredResultRequest.DeductionInput deduction() {
        AiScoreStructuredResultRequest.DeductionInput deduction = new AiScoreStructuredResultRequest.DeductionInput();
        deduction.setObservationCode("market_need");
        deduction.setDeductionId("missing_customer_interview");
        deduction.setDimensionCode("market");
        deduction.setDeductedPoints(new BigDecimal("2.5"));
        deduction.setMaxRecoverablePoints(new BigDecimal("2.5"));
        deduction.setReason("缺少足够客户访谈证据");
        deduction.setRequiredFix("补充至少 3 个目标客户访谈");
        deduction.setAcceptanceCriteria("访谈记录能证明目标客户痛点真实存在");
        deduction.setEvidenceLevel("medium");
        deduction.setConfidence(new BigDecimal("0.81"));
        deduction.setStatus("new");
        deduction.setEvidenceAnchorIds(List.of(10L));
        return deduction;
    }

    private AiScoreStructuredResultRequest.RecoveryClaimInput recoveryClaim() {
        AiScoreStructuredResultRequest.RecoveryClaimInput claim = new AiScoreStructuredResultRequest.RecoveryClaimInput();
        claim.setSourceDeductionId("missing_customer_interview");
        claim.setRecoveryStatus("fixed");
        claim.setRequestedRecoverPoints(new BigDecimal("2.5"));
        claim.setAcceptanceEvidence("已补充 3 个目标客户访谈记录");
        claim.setEvidenceAnchorIds(List.of(12L));
        return claim;
    }
}
