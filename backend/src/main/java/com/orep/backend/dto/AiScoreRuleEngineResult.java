package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class AiScoreRuleEngineResult {
    private String ruleEngineVersion;
    private BigDecimal baseScore;
    private BigDecimal rawScore;
    private BigDecimal deductedScore;
    private BigDecimal recoveredScore;
    private BigDecimal currentScoreCap;
    private BigDecimal finalScore;
    private List<String> notPerfectReasons;
    private String calibrationJson;
    private List<AiScoreStructuredResultRequest.ObservationInput> observations;
    private List<ObservationScoreResult> observationResults;
    private Map<String, BigDecimal> dimensionScores;
    private List<AiScoreStructuredResultRequest.DeductionInput> deductions;
    private List<AiScoreRecoveryInput> recoveries;

    @Data
    public static class ObservationScoreResult {
        private String observationCode;
        private String observationName;
        private String dimensionCode;
        private String dimensionName;
        private BigDecimal maxScore;
        private BigDecimal baseScore;
        private BigDecimal rawScore;
        private BigDecimal deductedScore;
        private BigDecimal recoveredScore;
        private BigDecimal scoreCap;
        private BigDecimal finalScore;
        private String evidenceLevel;
    }
}
