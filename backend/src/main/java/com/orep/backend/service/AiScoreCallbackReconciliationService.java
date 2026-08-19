package com.orep.backend.service;

import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.dto.PipelineCallbackRequest;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.HashSet;
import java.util.Set;

@Service
public class AiScoreCallbackReconciliationService {
    private static final String AUTHORITATIVE = "structured_rule_engine";
    private static final BigDecimal TOLERANCE = new BigDecimal("0.005");

    private final AiScoreRuleEngine ruleEngine;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiScoreCallbackReconciliationService(AiScoreRuleEngine ruleEngine) {
        this.ruleEngine = ruleEngine;
    }

    public AiScoreRuleEngineResult reconcile(PipelineCallbackRequest.PipelineFinalResult result) {
        if (result == null) {
            throw new IllegalArgumentException("finalResult cannot be null");
        }
        if (!AUTHORITATIVE.equals(result.getScoreAuthority())) {
            AiScoreRuleEngineResult legacy = new AiScoreRuleEngineResult();
            legacy.setFinalScore(result.getOverallScore());
            return legacy;
        }
        if (result.getObservations() == null || result.getObservations().isEmpty()) {
            throw new IllegalArgumentException("authoritative score requires canonical observations");
        }

        AiScoreStructuredResultRequest request = new AiScoreStructuredResultRequest();
        request.setRuleEngineVersion(result.getRuleEngineVersion());
        request.setObservations(result.getObservations().stream().map(this::toObservation).toList());
        request.setDeductions(emptyIfNull(result.getDeductions()).stream().map(this::toDeduction).toList());

        AiScoreRuleEngineResult recomputed = ruleEngine.score(request, List.of());
        BigDecimal reported = result.getOverallScore();
        if (reported == null || reported.subtract(recomputed.getFinalScore()).abs().compareTo(TOLERANCE) > 0) {
            throw new IllegalArgumentException("Python authoritative score " + decimalText(reported)
                    + " does not match Java recomputed score " + decimalText(recomputed.getFinalScore()));
        }
        if ("ai-score-report-v3".equals(result.getContractVersion())) {
            reconcileV3Portfolio(result);
        }
        return recomputed;
    }

    private void reconcileV3Portfolio(PipelineCallbackRequest.PipelineFinalResult result) {
        JsonNode ledger = readJson(result.getLossLedgerJson(), true, "lossLedgerJson");
        JsonNode tasks = readJson(result.getActionPlanJson(), true, "actionPlanJson");
        JsonNode coverage = readJson(result.getCoverageSummaryJson(), false, "coverageSummaryJson");
        Set<String> lossIds = new HashSet<>();
        Set<String> budgetKeys = new HashSet<>();
        BigDecimal ledgerPoints = BigDecimal.ZERO;
        for (JsonNode loss : ledger) {
            String lossId = text(loss, "lossId");
            if (lossId.isBlank() || !lossIds.add(lossId)) {
                throw new IllegalArgumentException("loss ledger contains blank or duplicate lossId " + lossId);
            }
            String budgetKey = text(loss, "scoreBudgetKey");
            if (budgetKey.isBlank() || !budgetKeys.add(budgetKey)) {
                throw new IllegalArgumentException("loss ledger contains blank or duplicate scoreBudgetKey " + budgetKey);
            }
            JsonNode points = loss.get("points");
            if (points == null || !points.isNumber() || points.decimalValue().compareTo(BigDecimal.ZERO) <= 0) {
                throw new IllegalArgumentException("loss ledger points must be positive");
            }
            ledgerPoints = ledgerPoints.add(points.decimalValue());
        }
        BigDecimal fullGap = new BigDecimal("100").subtract(result.getOverallScore());
        if (fullGap.subtract(ledgerPoints).abs().compareTo(new BigDecimal("0.1")) > 0) {
            throw new IllegalArgumentException("loss ledger does not reconcile with official score");
        }

        Set<String> coveredLossIds = new HashSet<>();
        for (JsonNode task : tasks) {
            String taskId = text(task, "taskId");
            if (taskId.isBlank()) {
                throw new IllegalArgumentException("remediation task requires taskId");
            }
            JsonNode covered = task.path("coveredLossIds");
            if (!covered.isArray()) {
                throw new IllegalArgumentException("remediation task requires coveredLossIds array");
            }
            for (JsonNode lossIdNode : covered) {
                String lossId = lossIdNode.asText("");
                if (!lossIds.contains(lossId)) {
                    throw new IllegalArgumentException("remediation task references unknown lossId " + lossId);
                }
                coveredLossIds.add(lossId);
            }
        }

        boolean claimsComplete = "complete".equals(result.getTodoPortfolioStatus())
                || "complete".equals(coverage.path("status").asText());
        if (claimsComplete) {
            if (coverage.path("coverageRate").decimalValue().compareTo(BigDecimal.ONE) != 0
                    || coveredLossIds.size() != lossIds.size()
                    || coverage.path("uncoveredLossIds").size() != 0) {
                throw new IllegalArgumentException("complete remediation portfolio does not cover every loss");
            }
        }
    }

    private JsonNode readJson(String value, boolean array, String field) {
        try {
            JsonNode node = objectMapper.readTree(value == null ? "" : value);
            if (node == null || (array && !node.isArray()) || (!array && !node.isObject())) {
                throw new IllegalArgumentException(field + " has invalid JSON shape");
            }
            return node;
        } catch (IllegalArgumentException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalArgumentException(field + " is not valid JSON");
        }
    }

    private String text(JsonNode node, String field) {
        return node.path(field).asText("").trim();
    }

    private AiScoreStructuredResultRequest.ObservationInput toObservation(
            PipelineCallbackRequest.ObservationInput source
    ) {
        AiScoreStructuredResultRequest.ObservationInput target = new AiScoreStructuredResultRequest.ObservationInput();
        target.setObservationCode(source.getObservationCode());
        target.setObservationName(source.getObservationName());
        target.setDimensionCode(source.getDimensionCode());
        target.setDimensionName(source.getDimensionName());
        target.setMaxScore(source.getMaxScore());
        target.setRawScore(source.getBaseScore() == null ? source.getRawScore() : source.getBaseScore());
        target.setScoreCap(source.getScoreCap());
        target.setEvidenceLevel(source.getEvidenceLevel());
        target.setConfidence(source.getConfidence());
        target.setValidityStatus(source.getValidityStatus());
        target.setModelReason(source.getModelReason());
        target.setEvidenceAnchorIds(source.getEvidenceAnchorIds());
        return target;
    }

    private AiScoreStructuredResultRequest.DeductionInput toDeduction(
            PipelineCallbackRequest.DeductionInput source
    ) {
        AiScoreStructuredResultRequest.DeductionInput target = new AiScoreStructuredResultRequest.DeductionInput();
        target.setDeductionId(source.getDeductionId());
        target.setObservationCode(source.getObservationCode());
        target.setDimensionCode(source.getDimensionCode());
        target.setDeductedPoints(source.getDeductedPoints());
        target.setMaxRecoverablePoints(source.getMaxRecoverablePoints());
        target.setReason(source.getReason());
        target.setRequiredFix(source.getRequiredFix());
        target.setAcceptanceCriteria(source.getAcceptanceCriteria());
        target.setEvidenceLevel(source.getEvidenceLevel());
        target.setConfidence(source.getConfidence());
        target.setStatus(source.getStatus());
        target.setEvidenceAnchorIds(source.getEvidenceAnchorIds());
        return target;
    }

    private String decimalText(BigDecimal value) {
        if (value == null) {
            return "null";
        }
        return value.setScale(2, RoundingMode.HALF_UP).toPlainString();
    }

    private <T> List<T> emptyIfNull(List<T> values) {
        return values == null ? List.of() : values;
    }
}
