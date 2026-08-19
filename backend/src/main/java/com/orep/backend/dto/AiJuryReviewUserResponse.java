package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class AiJuryReviewUserResponse {
    private Long jurySessionId;
    private Long sessionId;
    private Long meetingId;
    private String status;
    private String reviewMode;
    private String trackName;
    private BigDecimal officialScore;
    private BigDecimal juryAverageScore;
    private BigDecimal scoreDiffFromOfficial;
    private Integer judgeCount;
    private Integer successfulCount;
    private String explanation;
    private DisputeReviewContext disputeReviewContext;
    private List<MemberReview> members = new ArrayList<>();
    private AggregateReview aggregate = new AggregateReview();
    private LocalDateTime completedAt;

    @Data
    public static class MemberReview {
        private String personaCode;
        private String displayName;
        private String roleLabel;
        private String status;
        private BigDecimal referenceScore;
        private String scoreRelationToOfficial;
        private List<String> perspectiveQuestions = new ArrayList<>();
        private List<String> expressionRisks = new ArrayList<>();
        private List<String> trainingSuggestions = new ArrayList<>();
        private List<String> evidenceConcerns = new ArrayList<>();
    }

    @Data
    public static class AggregateReview {
        private List<String> consensusIssues = new ArrayList<>();
        private List<String> disagreementFocus = new ArrayList<>();
        private List<String> nextTrainingPriorities = new ArrayList<>();
    }

    @Data
    public static class DisputeReviewContext {
        private String mode = "dispute_review";
        private BigDecimal officialScore;
        private BigDecimal llmRawScore;
        private BigDecimal ruleEngineScore;
        private BigDecimal scoreDiff;
        private List<String> diffReasons = new ArrayList<>();
        private List<String> reviewTriggers = new ArrayList<>();
        private List<DisputedObservation> disputedObservations = new ArrayList<>();
        private List<DeductionReviewItem> deductionReviewItems = new ArrayList<>();
        private Boolean humanReviewSuggested;
        private String summary;
    }

    @Data
    public static class DisputedObservation {
        private String dimensionName;
        private String evidenceLevel;
        private BigDecimal rawScore;
        private BigDecimal scoreCap;
        private BigDecimal confidence;
        private Integer anchorCount;
        private List<String> reasons = new ArrayList<>();
    }

    @Data
    public static class DeductionReviewItem {
        private String dimensionName;
        private String reason;
        private BigDecimal deductedPoints;
        private BigDecimal recoveredPoints;
        private BigDecimal confidence;
        private String evidenceLevel;
        private Integer anchorCount;
        private String status;
        private String requiredFix;
    }
}
