package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
public class AiScoreReportUserResponse {
    private Long reportId;
    private Long sessionId;
    private String sessionNo;
    private Long meetingId;
    private String trackName;
    private String sourceType;
    private BigDecimal overallScore;
    private String dimensionsJson;
    private String highlightsJson;
    private String criticalIssuesJson;
    private String improvementPrioritiesJson;
    private String actionPlanJson;
    private List<Map<String, Object>> actionPlan;
    private String lossLedgerJson;
    private List<Map<String, Object>> lossLedger;
    private String coverageSummaryJson;
    private Map<String, Object> coverageSummary;
    private String scoreProjectionJson;
    private Map<String, Object> scoreProjection;
    private List<Map<String, Object>> remediationTasks;
    private List<Map<String, Object>> taskVerifications;
    private String todoPortfolioStatus;
    private String contractVersion;
    private String transcript;
    private String speechQualityJson;
    private String scoreCalibrationJson;
    private String model;
    private String status;
    private LocalDateTime completedAt;
    private String scoringConsistencyNo;
    private List<StructuredObservation> structuredObservations;
    private List<StructuredDeduction> structuredDeductions;
    private List<EvidenceAnchor> evidenceAnchors;
    private ScoreRecoverySummary scoreRecoverySummary;
    private List<TrainingTask> trainingTasks;
    private RuleEngineShadow ruleEngineShadow;
    private MediaPlayback mediaPlayback;
    private String speakerAttributionStatus;
    private Integer speakerAttributionRevision;
    private List<StablePerson> stablePeople;
    private List<TranscriptSegment> finalSpeakerSegments;
    private List<TranscriptSegment> asrSegments;
    private List<SpeakerMapping> speakerMappings;
    private Stability stability;
    private List<SubstanceClaim> verifyClaims;
    private TaskBook taskBook;
    private ScoreGap scoreGap;
    private DeliberationState deliberation;
    private Boolean teacherConfirmed;
    private ChallengeSet challenges;

    @Data
    public static class Stability {
        private String band;
        private int runCount;
        private String headline;
        private String identityBand;
        private int identityRunCount;
        private String identityHeadline;
        private Integer thisRunIndex;
        private Long newerSessionId;
        private Integer newerRunIndex;
        private List<StabilityRun> runs;
    }

    @Data
    public static class StabilityRun {
        private Integer runIndex;
        private BigDecimal officialScore;
        private BigDecimal scoreDeltaAbs;
        private BigDecimal transcriptCoverage;
        private BigDecimal seekableAnchorRate;
        private Boolean tapeGrounded;
    }

    @Data
    public static class TranscriptSegment {
        private Long id;
        private String segmentId;
        private Integer segmentNo;
        private Integer attributionRevision;
        private Long startMs;
        private Long endMs;
        private String text;
        private String rawSpeaker;
        private String personId;
        private String personType;
        private Integer contestantSlot;
        private String speakerState;
        private Boolean finalSegment;
        private String speakerName;
        private String roleName;
        private BigDecimal confidence;
    }

    @Data
    public static class StablePerson {
        private String personId;
        private String personType;
        private String personTypeLabel;
        private Integer contestantSlot;
        private String displayName;
        private String roleName;
        private String personState;
        private BigDecimal confidence;
        private Long firstSeenMs;
        private Long lastSeenMs;
    }

    @Data
    public static class SpeakerMapping {
        private String rawSpeaker;
        private String displayName;
        private String roleName;
        private String status;
        private BigDecimal confidence;
        private Integer revision;
    }

    @Data
    public static class MediaPlayback {
        private Long assetId;
        private String contentType;
        private Long sizeBytes;
        private Double durationSeconds;
        private String streamUrl;
    }

    @Data
    public static class StructuredObservation {
        private Long id;
        private String dimensionName;
        private BigDecimal rawScore;
        private BigDecimal scoreCap;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String validityStatus;
        private String modelReason;
        private List<Long> evidenceAnchorIds;
    }

    @Data
    public static class StructuredDeduction {
        private Long id;
        private String dimensionName;
        private BigDecimal deductedPoints;
        private BigDecimal recoveredPoints;
        private String reason;
        private String requiredFix;
        private String acceptanceCriteria;
        private BigDecimal maxRecoverablePoints;
        private String evidenceLevel;
        private BigDecimal confidence;
        private List<Long> evidenceAnchorIds;
        private String status;
        private Boolean recovery;
    }

    @Data
    public static class EvidenceAnchor {
        private Long id;
        private String anchorType;
        private String anchorTitle;
        private String evidenceText;
        private String sourceRef;
        private Long transcriptSegmentId;
        private Long frameId;
        private Long mediaAssetId;
        private Long startMs;
        private Long endMs;
        private BigDecimal confidence;
        private String validityStatus;
    }

    @Data
    public static class ScoreRecoverySummary {
        private Integer recoveredCount;
        private BigDecimal recoveredPoints;
        private BigDecimal currentDeductedPoints;
        private BigDecimal recoverableScore;
        private Integer newIssueCount;
        private List<String> notPerfectReasons;
    }

    @Data
    public static class TrainingTask {
        private String taskId;
        private String title;
        private String correspondingDeduction;
        private String trainingAction;
        private String ownerRole;
        private String timeSuggestion;
        private String acceptanceCriteria;
        private BigDecimal expectedRecoverPoints;
        private List<Long> evidenceAnchorIds;
        private String priority;
        private String observationCode;
        private String sourceIssueKey;
    }

    @Data
    public static class RuleEngineShadow {
        private BigDecimal llmRawScore;
        private BigDecimal ruleEngineScore;
        private BigDecimal modelReviewScore;
        private Boolean tapeGrounded;
        private BigDecimal scoreDiff;
        private List<String> diffReasons;
        private String scoringFingerprint;
    }
}
