package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class AiScoreStructuredResultRequest {
    private Long sessionId;
    private String ruleEngineVersion;
    private ScoreSummary scoreSummary;
    private List<ObservationInput> observations;
    private List<DeductionInput> deductions;
    private List<RecoveryClaimInput> recoveryClaims;

    @Data
    public static class ObservationInput {
        private String observationCode;
        private String observationName;
        private String dimensionCode;
        private String dimensionName;
        private BigDecimal maxScore;
        private BigDecimal rawScore;
        private BigDecimal scoreCap;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String validityStatus;
        private String modelReason;
        private List<Long> evidenceAnchorIds;
        private List<EvidenceAnchorRef> evidenceAnchors;
    }

    @Data
    public static class DeductionInput {
        private String deductionId;
        private String observationCode;
        private String dimensionCode;
        private BigDecimal deductedPoints;
        private BigDecimal maxRecoverablePoints;
        private String reason;
        private String requiredFix;
        private String acceptanceCriteria;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String status;
        private List<Long> evidenceAnchorIds;
        private List<EvidenceAnchorRef> evidenceAnchors;
    }

    @Data
    public static class RecoveryClaimInput {
        private String sourceDeductionId;
        private String recoveryStatus;
        private BigDecimal requestedRecoverPoints;
        private String acceptanceEvidence;
        private List<Long> evidenceAnchorIds;
    }

    @Data
    public static class EvidenceAnchorRef {
        private Long id;
        private String anchorType;
        private String sourceRef;
        private String evidenceText;
    }

    @Data
    public static class ScoreSummary {
        private BigDecimal rawTotalScore;
        private BigDecimal finalScore;
        private BigDecimal scoreCap;
    }
}
