package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Data
public class Challenge {
    private String challengeId;
    private String type;
    private String targetDimension;
    private String lossId;
    private List<Long> anchorIds = new ArrayList<>();
    private String statement;
    private boolean seekable;
    private Long startMs;
    private String status;
    private BigDecimal proposedRestorePoints;
    private String teacherReason;
    private Long resolvedBy;
    private String resolvedAt;
}
