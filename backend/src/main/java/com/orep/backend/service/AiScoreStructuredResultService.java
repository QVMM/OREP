package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

@Service
@RequiredArgsConstructor
public class AiScoreStructuredResultService {
    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private final AiScoringSessionMapper sessionMapper;
    private final AiScoreEvidenceAnchorMapper evidenceAnchorMapper;
    private final AiScoreReportMapper reportMapper;
    private final AiScoreObservationMapper observationMapper;
    private final AiScoreDeductionMapper deductionMapper;
    private final AiScoreStructuredResultValidator validator;
    private final AiScoreRuleEngine ruleEngine;
    private final AiScoreRecoveryMemoryService recoveryMemoryService;
    private final ObjectMapper objectMapper;

    @Transactional
    public AiScoreRuleEngineResult applyStructuredResult(
            Long sessionId,
            AiScoreStructuredResultRequest request,
            List<AiScoreRecoveryInput> recoveries
    ) {
        if (request == null) {
            throw new IllegalArgumentException("request must not be null");
        }
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("sessionId must be a positive number");
        }
        if (request.getSessionId() == null) {
            request.setSessionId(sessionId);
        } else if (!sessionId.equals(request.getSessionId())) {
            throw new IllegalArgumentException("sessionId mismatch: path sessionId=" + sessionId
                    + ", request sessionId=" + request.getSessionId());
        }

        AiScoringSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new IllegalStateException("评分会话不存在");
        }

        validator.validate(request);

        Set<Long> validAnchorIds = evidenceAnchorMapper.selectList(
                        new LambdaQueryWrapper<AiScoreEvidenceAnchor>()
                                .eq(AiScoreEvidenceAnchor::getSessionId, sessionId)
                ).stream()
                .map(AiScoreEvidenceAnchor::getId)
                .collect(Collectors.toSet());
        validateReferencedAnchors(request, validAnchorIds);
        List<AiScoreRecoveryInput> trustedRecoveries = recoveryMemoryService.resolveTrustedRecoveries(
                session,
                request.getRecoveryClaims(),
                validAnchorIds
        );
        if (emptyIfNull(request.getRecoveryClaims()).isEmpty()
                && emptyIfNull(trustedRecoveries).isEmpty()
                && !emptyIfNull(recoveries).isEmpty()) {
            trustedRecoveries = recoveries;
        }
        AiScoreRuleEngineResult result = ruleEngine.score(request, trustedRecoveries);

        LocalDateTime now = LocalDateTime.now();
        AiScoreReport report = findOrCreateReport(session, sessionId);
        boolean newReport = report.getId() == null;
        report.setSessionId(sessionId);
        report.setMeetingId(session.getMeetingId());
        report.setOverallScore(result.getFinalScore());
        report.setScoreCalibrationJson(result.getCalibrationJson());
        report.setStructuredResultJson(writeJson(structuredResultSummary(request, result)));
        report.setRuleEngineVersion(result.getRuleEngineVersion());
        report.setCurrentScoreCap(result.getCurrentScoreCap());
        report.setRecoveredScore(result.getRecoveredScore());
        report.setStatus("completed");
        if (report.getStartedAt() == null) {
            report.setStartedAt(session.getStartedAt() == null ? now : session.getStartedAt());
        }
        report.setCompletedAt(now);
        report.setUpdatedAt(now);
        if (newReport) {
            report.setCreatedAt(now);
            reportMapper.insert(report);
        } else {
            reportMapper.updateById(report);
        }

        Long reportId = report.getId();
        deleteExistingStructuredRows(sessionId);
        insertObservations(sessionId, reportId, request.getObservations(), now);
        insertDeductions(sessionId, reportId, request.getDeductions(), now);
        insertRecoveryRows(sessionId, reportId, result.getRecoveries(), request.getRecoveryClaims(), now);

        session.setReportId(reportId);
        session.setStatus("completed");
        session.setCurrentStage("rule_engine_completed");
        session.setProgressPercent(100);
        session.setCompletedAt(now);
        session.setUpdatedAt(now);
        sessionMapper.updateById(session);

        return result;
    }

    private void deleteExistingStructuredRows(Long sessionId) {
        observationMapper.delete(new LambdaQueryWrapper<AiScoreObservation>()
                .eq(AiScoreObservation::getSessionId, sessionId));
        deductionMapper.delete(new LambdaQueryWrapper<AiScoreDeduction>()
                .eq(AiScoreDeduction::getSessionId, sessionId));
    }

    private AiScoreReport findOrCreateReport(AiScoringSession session, Long sessionId) {
        if (session.getReportId() != null) {
            AiScoreReport report = reportMapper.selectById(session.getReportId());
            if (report != null) {
                return report;
            }
        }
        AiScoreReport sessionReport = reportMapper.selectOne(
                new LambdaQueryWrapper<AiScoreReport>()
                        .eq(AiScoreReport::getSessionId, sessionId)
                        .last("LIMIT 1")
        );
        if (sessionReport != null) {
            return sessionReport;
        }
        if (session.getMeetingId() != null) {
            AiScoreReport report = reportMapper.selectOne(
                    new LambdaQueryWrapper<AiScoreReport>()
                            .eq(AiScoreReport::getMeetingId, session.getMeetingId())
            );
            if (report != null) {
                return report;
            }
        }
        AiScoreReport legacyUploadedReport = reportMapper.selectOne(
                new LambdaQueryWrapper<AiScoreReport>()
                        .eq(AiScoreReport::getMeetingId, -sessionId)
                        .last("LIMIT 1")
        );
        if (legacyUploadedReport != null) {
            return legacyUploadedReport;
        }

        AiScoreReport report = new AiScoreReport();
        report.setSessionId(sessionId);
        report.setMeetingId(session.getMeetingId());
        return report;
    }

    private void validateReferencedAnchors(
            AiScoreStructuredResultRequest request,
            Set<Long> validAnchorIds
    ) {
        referencedAnchorIds(request)
                .filter(anchorId -> !validAnchorIds.contains(anchorId))
                .findFirst()
                .ifPresent(anchorId -> {
                    throw new IllegalArgumentException("evidenceAnchorId " + anchorId
                            + " does not belong to session " + request.getSessionId());
                });
    }

    private Stream<Long> referencedAnchorIds(AiScoreStructuredResultRequest request) {
        Stream<Long> observationAnchorIds = emptyIfNull(request.getObservations()).stream()
                .flatMap(observation -> emptyIfNull(observation.getEvidenceAnchorIds()).stream());
        Stream<Long> deductionAnchorIds = emptyIfNull(request.getDeductions()).stream()
                .flatMap(deduction -> emptyIfNull(deduction.getEvidenceAnchorIds()).stream());
        Stream<Long> recoveryClaimAnchorIds = emptyIfNull(request.getRecoveryClaims()).stream()
                .flatMap(claim -> emptyIfNull(claim.getEvidenceAnchorIds()).stream());
        return Stream.concat(Stream.concat(observationAnchorIds, deductionAnchorIds), recoveryClaimAnchorIds);
    }

    private void insertObservations(
            Long sessionId,
            Long reportId,
            List<AiScoreStructuredResultRequest.ObservationInput> inputs,
            LocalDateTime now
    ) {
        for (AiScoreStructuredResultRequest.ObservationInput input : emptyIfNull(inputs)) {
            AiScoreObservation observation = new AiScoreObservation();
            observation.setSessionId(sessionId);
            observation.setReportId(reportId);
            observation.setObservationCode(input.getObservationCode());
            observation.setDimensionCode(input.getDimensionCode());
            observation.setDimensionName(input.getDimensionName());
            observation.setRawScore(input.getRawScore());
            observation.setScoreCap(input.getScoreCap());
            observation.setEvidenceLevel(input.getEvidenceLevel());
            observation.setConfidence(input.getConfidence());
            observation.setEvidenceAnchorIdsJson(writeJson(emptyIfNull(input.getEvidenceAnchorIds())));
            observation.setValidityStatus(input.getValidityStatus());
            observation.setModelReason(input.getModelReason());
            observation.setCreatedAt(now);
            observationMapper.insert(observation);
        }
    }

    private void insertDeductions(
            Long sessionId,
            Long reportId,
            List<AiScoreStructuredResultRequest.DeductionInput> inputs,
            LocalDateTime now
    ) {
        for (AiScoreStructuredResultRequest.DeductionInput input : emptyIfNull(inputs)) {
            AiScoreDeduction deduction = new AiScoreDeduction();
            deduction.setSessionId(sessionId);
            deduction.setReportId(reportId);
            deduction.setDeductionId(input.getDeductionId());
            deduction.setObservationCode(input.getObservationCode());
            deduction.setDimensionCode(input.getDimensionCode());
            deduction.setDeductedPoints(input.getDeductedPoints());
            deduction.setRecoveredPoints(ZERO);
            deduction.setReason(input.getReason());
            deduction.setRequiredFix(input.getRequiredFix());
            deduction.setAcceptanceCriteria(input.getAcceptanceCriteria());
            deduction.setMaxRecoverablePoints(input.getMaxRecoverablePoints());
            deduction.setEvidenceLevel(input.getEvidenceLevel());
            deduction.setConfidence(input.getConfidence());
            deduction.setEvidenceAnchorIdsJson(writeJson(emptyIfNull(input.getEvidenceAnchorIds())));
            deduction.setStatus(input.getStatus());
            deduction.setCreatedAt(now);
            deductionMapper.insert(deduction);
        }
    }

    private void insertRecoveryRows(
            Long sessionId,
            Long reportId,
            List<AiScoreRecoveryInput> acceptedRecoveries,
            List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims,
            LocalDateTime now
    ) {
        for (AiScoreDeduction recoveryRow : emptyIfNull(recoveryMemoryService.buildRecoveryRows(
                sessionId,
                reportId,
                acceptedRecoveries,
                claims,
                now
        ))) {
            deductionMapper.insert(recoveryRow);
        }
    }

    private Map<String, Object> structuredResultSummary(
            AiScoreStructuredResultRequest request,
            AiScoreRuleEngineResult result
    ) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("sessionId", request.getSessionId());
        summary.put("scoreSummary", request.getScoreSummary());
        summary.put("finalScore", result.getFinalScore());
        summary.put("currentScoreCap", result.getCurrentScoreCap());
        summary.put("recoveredScore", result.getRecoveredScore());
        summary.put("observationCount", emptyIfNull(request.getObservations()).size());
        summary.put("deductionCount", emptyIfNull(request.getDeductions()).size());
        summary.put("recoveryCount", emptyIfNull(result.getRecoveries()).size());
        return summary;
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException("结构化评分结果序列化失败", exception);
        }
    }

    private <T> List<T> emptyIfNull(List<T> values) {
        return values == null ? List.of() : values;
    }
}
