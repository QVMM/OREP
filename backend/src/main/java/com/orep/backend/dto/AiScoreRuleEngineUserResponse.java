package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class AiScoreRuleEngineUserResponse {
    private BigDecimal baseScore;
    private BigDecimal rawScore;
    private BigDecimal deductedScore;
    private BigDecimal recoveredScore;
    private BigDecimal currentScoreCap;
    private BigDecimal finalScore;
    private List<String> notPerfectReasons;

    public static AiScoreRuleEngineUserResponse from(AiScoreRuleEngineResult result) {
        AiScoreRuleEngineUserResponse response = new AiScoreRuleEngineUserResponse();
        response.setBaseScore(result.getBaseScore());
        response.setRawScore(result.getRawScore());
        response.setDeductedScore(result.getDeductedScore());
        response.setRecoveredScore(result.getRecoveredScore());
        response.setCurrentScoreCap(result.getCurrentScoreCap());
        response.setFinalScore(result.getFinalScore());
        response.setNotPerfectReasons(result.getNotPerfectReasons());
        return response;
    }
}
