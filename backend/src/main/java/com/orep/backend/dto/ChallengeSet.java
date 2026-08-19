package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Data
public class ChallengeSet {
    private String scanVersion;
    private boolean scanned;
    private String note;
    private List<Challenge> items = new ArrayList<>();
    private BigDecimal acceptedAdjustment;
    private BigDecimal adjustedDraftScore;
}
