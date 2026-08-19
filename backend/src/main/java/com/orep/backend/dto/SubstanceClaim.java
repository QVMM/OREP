package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Data
public class SubstanceClaim {
    private String claimType;
    private String verdict;
    private String claimStatus;
    private String statement;
    private List<String> evidenceRefs = new ArrayList<>();
    private List<String> sources = new ArrayList<>();
    private BigDecimal scoreCapHint;
}
