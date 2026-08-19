package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AiScoreRecoveryInput {
    private String sourceDeductionId;
    private String recoveryStatus;
    private BigDecimal requestedRecoverPoints;
    private BigDecimal maxRecoverablePoints;
    private String acceptanceEvidence;
}
