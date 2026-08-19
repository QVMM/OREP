package com.orep.backend.service;

import com.orep.backend.dto.AiScoreStructuredResultRequest;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class AiScoreStructuredResultValidator {
    private static final Set<String> EVIDENCE_LEVELS = Set.of(
            "none",
            "claim",
            "weak",
            "medium",
            "strong",
            "E0",
            "E1",
            "E2",
            "E3",
            "E4",
            "E5"
    );
    private static final Set<String> VALIDITY_STATUSES = Set.of("valid", "weak_evidence", "contradicted", "unverifiable");
    private static final Set<String> DEDUCTION_STATUSES = Set.of("new", "repeated", "improved", "recovered", "invalid");
    private static final Set<String> RECOVERY_STATUSES = Set.of(
            "not_fixed",
            "partially_fixed",
            "fixed",
            "invalid_fix",
            "not_enough_evidence",
            "verified",
            "recovered",
            "pending",
            "rejected"
    );
    private static final Set<String> ACCEPTED_RECOVERY_STATUSES = Set.of("fixed", "verified", "recovered");
    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private static final BigDecimal ONE = BigDecimal.ONE;
    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100");

    public void validate(AiScoreStructuredResultRequest request) {
        if (request == null) {
            throw invalid("request", "must not be null");
        }
        if (request.getSessionId() == null || request.getSessionId() <= 0) {
            throw invalid("sessionId", "must be a positive number");
        }
        requireText(request.getRuleEngineVersion(), "ruleEngineVersion");
        if (request.getObservations() == null || request.getObservations().isEmpty()) {
            throw invalid("observations", "must not be empty");
        }

        Set<String> observationCodes = validateObservations(request.getObservations());
        validateDeductions(request.getDeductions(), observationCodes);
        validateRecoveryClaims(request.getRecoveryClaims());
    }

    private Set<String> validateObservations(List<AiScoreStructuredResultRequest.ObservationInput> observations) {
        Set<String> observationCodes = new HashSet<>();
        for (int i = 0; i < observations.size(); i++) {
            String path = "observations[" + i + "]";
            AiScoreStructuredResultRequest.ObservationInput observation = observations.get(i);
            if (observation == null) {
                throw invalid(path, "must not be null");
            }

            requireText(observation.getObservationCode(), path + ".observationCode");
            requireText(observation.getDimensionCode(), path + ".dimensionCode");
            requireText(observation.getDimensionName(), path + ".dimensionName");
            requireOptionalRange(observation.getMaxScore(), ZERO, ONE_HUNDRED, path + ".maxScore");
            requireRange(observation.getRawScore(), ZERO, ONE_HUNDRED, path + ".rawScore");
            requireRange(observation.getScoreCap(), ZERO, ONE_HUNDRED, path + ".scoreCap");
            requireEnum(observation.getEvidenceLevel(), EVIDENCE_LEVELS, path + ".evidenceLevel");
            requireRange(observation.getConfidence(), ZERO, ONE, path + ".confidence");
            requireEnum(observation.getValidityStatus(), VALIDITY_STATUSES, path + ".validityStatus");
            requireAnchorIdsUnlessE0(observation.getEvidenceLevel(), observation.getEvidenceAnchorIds(), path + ".evidenceAnchorIds");

            observationCodes.add(observation.getObservationCode());
        }
        return observationCodes;
    }

    private void validateDeductions(
            List<AiScoreStructuredResultRequest.DeductionInput> deductions,
            Set<String> observationCodes
    ) {
        if (deductions == null) {
            return;
        }

        for (int i = 0; i < deductions.size(); i++) {
            String path = "deductions[" + i + "]";
            AiScoreStructuredResultRequest.DeductionInput deduction = deductions.get(i);
            if (deduction == null) {
                throw invalid(path, "must not be null");
            }

            requireText(deduction.getDeductionId(), path + ".deductionId");
            requireText(deduction.getObservationCode(), path + ".observationCode");
            requireText(deduction.getDimensionCode(), path + ".dimensionCode");
            if (!observationCodes.contains(deduction.getObservationCode())) {
                throw invalid(path + ".observationCode", "must reference an existing observation");
            }
            requireRange(deduction.getDeductedPoints(), ZERO, ONE_HUNDRED, path + ".deductedPoints");
            requireRange(deduction.getMaxRecoverablePoints(), ZERO, ONE_HUNDRED, path + ".maxRecoverablePoints");
            if (deduction.getMaxRecoverablePoints().compareTo(deduction.getDeductedPoints()) > 0) {
                throw invalid(path + ".maxRecoverablePoints", "must not exceed deductedPoints");
            }
            requireText(deduction.getReason(), path + ".reason");
            requireText(deduction.getRequiredFix(), path + ".requiredFix");
            requireText(deduction.getAcceptanceCriteria(), path + ".acceptanceCriteria");
            requireEnum(deduction.getEvidenceLevel(), EVIDENCE_LEVELS, path + ".evidenceLevel");
            requireRange(deduction.getConfidence(), ZERO, ONE, path + ".confidence");
            requireEnum(deduction.getStatus(), DEDUCTION_STATUSES, path + ".status");
            requireAnchorIdsUnlessE0(deduction.getEvidenceLevel(), deduction.getEvidenceAnchorIds(), path + ".evidenceAnchorIds");
        }
    }

    private void validateRecoveryClaims(List<AiScoreStructuredResultRequest.RecoveryClaimInput> recoveryClaims) {
        if (recoveryClaims == null) {
            return;
        }

        for (int i = 0; i < recoveryClaims.size(); i++) {
            String path = "recoveryClaims[" + i + "]";
            AiScoreStructuredResultRequest.RecoveryClaimInput recoveryClaim = recoveryClaims.get(i);
            if (recoveryClaim == null) {
                throw invalid(path, "must not be null");
            }

            requireText(recoveryClaim.getSourceDeductionId(), path + ".sourceDeductionId");
            requireEnum(recoveryClaim.getRecoveryStatus(), RECOVERY_STATUSES, path + ".recoveryStatus");
            requireRange(recoveryClaim.getRequestedRecoverPoints(), ZERO, ONE_HUNDRED, path + ".requestedRecoverPoints");
            if (ACCEPTED_RECOVERY_STATUSES.contains(recoveryClaim.getRecoveryStatus())) {
                requireText(recoveryClaim.getAcceptanceEvidence(), path + ".acceptanceEvidence");
                requireAnchorIds(recoveryClaim.getEvidenceAnchorIds(), path + ".evidenceAnchorIds");
            } else {
                validateAnchorIds(recoveryClaim.getEvidenceAnchorIds(), path + ".evidenceAnchorIds");
            }
        }
    }

    private void requireText(String value, String fieldPath) {
        if (value == null || value.isBlank()) {
            throw invalid(fieldPath, "must not be blank");
        }
    }

    private void requireRange(BigDecimal value, BigDecimal min, BigDecimal max, String fieldPath) {
        if (value == null || value.compareTo(min) < 0 || value.compareTo(max) > 0) {
            throw invalid(fieldPath, "must be between " + min + " and " + max);
        }
    }

    private void requireOptionalRange(BigDecimal value, BigDecimal min, BigDecimal max, String fieldPath) {
        if (value != null) {
            requireRange(value, min, max, fieldPath);
        }
    }

    private void requireEnum(String value, Set<String> allowedValues, String fieldPath) {
        if (value == null || !allowedValues.contains(value)) {
            throw invalid(fieldPath, "must be a supported value");
        }
    }

    private void validateAnchorIds(List<Long> anchorIds, String fieldPath) {
        if (anchorIds == null) {
            return;
        }
        for (int i = 0; i < anchorIds.size(); i++) {
            Long anchorId = anchorIds.get(i);
            if (anchorId == null || anchorId < 0) {
                throw invalid(fieldPath + "[" + i + "]", "must not be negative");
            }
        }
    }

    private void requireAnchorIds(List<Long> anchorIds, String fieldPath) {
        if (anchorIds == null || anchorIds.isEmpty()) {
            throw invalid(fieldPath, "must not be empty");
        }
        validateAnchorIds(anchorIds, fieldPath);
    }

    private void requireAnchorIdsUnlessE0(String evidenceLevel, List<Long> anchorIds, String fieldPath) {
        if ("E0".equals(evidenceLevel)) {
            validateAnchorIds(anchorIds, fieldPath);
            return;
        }
        requireAnchorIds(anchorIds, fieldPath);
    }

    private IllegalArgumentException invalid(String fieldPath, String message) {
        return new IllegalArgumentException(fieldPath + " " + message);
    }
}
