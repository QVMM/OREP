package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Data
public class ScoreGap {
    private BigDecimal closureRate;
    private BigDecimal officialScore;
    private BigDecimal modelReviewScore;
    private Boolean tapeGrounded;
    private String identityReason;
    private BigDecimal trackCeiling;
    private BigDecimal repairBonus;
    private BigDecimal deltaFromLast;
    private List<CeilingGap> ceilingGaps = new ArrayList<>();
}
