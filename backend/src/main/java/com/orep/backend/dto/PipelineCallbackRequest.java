package com.orep.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class PipelineCallbackRequest {
    private Long sessionId;
    private String status;          // scoring, completed, failed
    private String currentStage;    // queued, audio_extracting, asr_processing, etc.
    private Integer progressPercent;
    private String message;
    private String errorMessage;
    private PipelineFinalResult finalResult;

    @Data
    public static class PipelineFinalResult {
        private String transcript;
        private List<Map<String, Object>> asrSegments;
        private List<SpeakerEvidenceInput> speakerEvidence;
        private BigDecimal overallScore;
        private BigDecimal rawOverallScore;
        private String scoreAuthority;
        private String dimensionsJson;
        private String highlightsJson;
        private String criticalIssuesJson;
        private String improvementPrioritiesJson;
        private String actionPlanJson;
        private String lossLedgerJson;
        private String coverageSummaryJson;
        private String scoreProjectionJson;
        private String contractVersion;
        private String todoPortfolioStatus;
        private Boolean publishCompleteTodoPortfolio;
        private String speechQualityJson;
        private String scoreCalibrationJson;
        private String model;
        private BigDecimal llmRawScore;
        private BigDecimal ruleEngineScore;
        private BigDecimal modelReviewScore;
        private Boolean tapeGrounded;
        private BigDecimal scoreDiff;
        private List<String> diffReasons;
        private String scoringFingerprint;
        private List<ObservationInput> observations;
        private List<DeductionInput> deductions;
        private List<EvidenceAnchorInput> evidenceAnchors;
        private String ruleEngineVersion;
        private SpeakerAttributionInput speakerAttribution;
    }

    @Data
    public static class SpeakerAttributionInput {
        private String contractVersion;
        private Integer revision;
        private String status;
        private Map<String, Object> clock;
        private List<AttributionPersonInput> people;
        private List<AttributionTurnInput> turns;
        private List<AttributionSegmentInput> segments;
    }

    @Data
    public static class AttributionPersonInput {
        private String personId;
        private String personType;
        private Integer contestantSlot;
        private String displayName;
        private String roleName;
        private String state;
        private BigDecimal confidence;
        private Long firstSeenMs;
        private Long lastSeenMs;
        private List<String> faceTrackIds;
        private List<String> bodyTrackIds;
        private List<String> voiceClusterIds;
        private Integer modelRevision;
    }

    @Data
    public static class AttributionTurnInput {
        private String turnId;
        private Long startMs;
        private Long endMs;
        private String personId;
        private String speakerState;
        private BigDecimal confidence;
        private List<String> candidatePersonIds;
        private String sourceClusterId;
        private String sourceVisualIdentityId;
        private String speakerVerification;
    }

    @Data
    public static class AttributionSegmentInput {
        private String segmentId;
        private Integer revision;
        private Long startMs;
        private Long endMs;
        private String text;
        private String personId;
        private String rawSpeakerId;
        private String sourceClusterId;
        private String speakerState;
        private BigDecimal speakerConfidence;
        private List<String> candidatePersonIds;
        private Boolean isFinal;
        private String source;
        private BigDecimal asrConfidence;

        @JsonProperty("isFinal")
        public Boolean getFinal() {
            return isFinal;
        }

        @JsonProperty("isFinal")
        public void setFinal(Boolean value) {
            isFinal = value;
        }
    }

    @Data
    public static class SpeakerEvidenceInput {
        private String rawSpeakerId;
        private String displayName;
        private String roleName;
        private String matchedName;
        private String status;
        private String source;
        private BigDecimal confidence;
        private BigDecimal durationSec;
        private List<String> evidenceQuotes;
        private List<Map<String, Object>> segments;
    }

    @Data
    public static class ObservationInput {
        private String observationCode;
        private String observationName;
        private String dimensionCode;
        private String dimensionName;
        private BigDecimal maxScore;
        private BigDecimal baseScore;
        private BigDecimal rawScore;
        private BigDecimal scoreCap;
        private BigDecimal finalScore;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String validityStatus;
        private String modelReason;
        private List<Long> evidenceAnchorIds;
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
    }

    @Data
    public static class EvidenceAnchorInput {
        private Long id;
        private String anchorType;
        private String anchorTitle;
        private String evidenceText;
        private String sourceRef;
        private Long startMs;
        private Long endMs;
        private BigDecimal confidence;
        private String validityStatus;
    }
}
