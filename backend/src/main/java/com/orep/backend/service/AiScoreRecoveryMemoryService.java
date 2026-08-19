package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AiScoreRecoveryMemoryService {
    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private static final BigDecimal DEFAULT_CONFIDENCE = new BigDecimal("0.80");
    private static final Set<String> ACCEPTED_RECOVERY_STATUSES = Set.of("fixed", "verified", "recovered");

    private final AiScoringSessionMapper sessionMapper;
    private final AiScoreDeductionMapper deductionMapper;

    public List<AiScoreRecoveryInput> resolveTrustedRecoveries(
            AiScoringSession currentSession,
            List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims,
            Set<Long> validAnchorIds
    ) {
        if (currentSession == null
                || !Boolean.TRUE.equals(currentSession.getUseHistoryMemory())
                || !hasCompleteHistoryScope(currentSession)
                || emptyIfNull(claims).isEmpty()) {
            return List.of();
        }

        AiScoringSession previousSession = findPreviousCompletedSession(currentSession);
        if (previousSession == null) {
            return List.of();
        }

        Map<String, AiScoreDeduction> previousDeductions = deductionMapper.selectList(
                        new LambdaQueryWrapper<AiScoreDeduction>()
                                .eq(AiScoreDeduction::getSessionId, previousSession.getId())
                ).stream()
                .filter(deduction -> deduction.getDeductionId() != null)
                .collect(Collectors.toMap(
                        AiScoreDeduction::getDeductionId,
                        Function.identity(),
                        (first, ignored) -> first,
                        LinkedHashMap::new
                ));

        return emptyIfNull(claims).stream()
                .filter(this::isAcceptedClaim)
                .map(claim -> trustedRecovery(claim, previousDeductions, emptyIfNull(validAnchorIds)))
                .toList();
    }

    public List<AiScoreDeduction> buildRecoveryRows(
            Long sessionId,
            Long reportId,
            List<AiScoreRecoveryInput> acceptedRecoveries,
            List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims,
            LocalDateTime now
    ) {
        if (emptyIfNull(acceptedRecoveries).isEmpty()) {
            return List.of();
        }

        Map<String, AiScoreStructuredResultRequest.RecoveryClaimInput> claimsBySourceDeductionId =
                emptyIfNull(claims).stream()
                        .filter(claim -> claim != null && claim.getSourceDeductionId() != null)
                        .collect(Collectors.toMap(
                                AiScoreStructuredResultRequest.RecoveryClaimInput::getSourceDeductionId,
                                Function.identity(),
                                (first, ignored) -> first,
                                LinkedHashMap::new
                        ));

        return emptyIfNull(acceptedRecoveries).stream()
                .map(recovery -> recoveryRow(
                        sessionId,
                        reportId,
                        recovery,
                        claimsBySourceDeductionId.get(recovery.getSourceDeductionId()),
                        now
                ))
                .toList();
    }

    private AiScoringSession findPreviousCompletedSession(AiScoringSession currentSession) {
        List<AiScoringSession> sessions = sessionMapper.selectList(
                new LambdaQueryWrapper<AiScoringSession>()
                        .eq(AiScoringSession::getProjectId, currentSession.getProjectId())
                        .eq(AiScoringSession::getTeamId, currentSession.getTeamId())
                        .eq(AiScoringSession::getTrackId, currentSession.getTrackId())
                        .eq(AiScoringSession::getStatus, "completed")
                        .lt(AiScoringSession::getId, currentSession.getId())
                        .orderByDesc(AiScoringSession::getId)
                        .last("limit 1")
        );
        return sessions.isEmpty() ? null : sessions.getFirst();
    }

    private boolean isAcceptedClaim(AiScoreStructuredResultRequest.RecoveryClaimInput claim) {
        return claim != null
                && ACCEPTED_RECOVERY_STATUSES.contains(normalizeStatus(claim.getRecoveryStatus()));
    }

    private AiScoreRecoveryInput trustedRecovery(
            AiScoreStructuredResultRequest.RecoveryClaimInput claim,
            Map<String, AiScoreDeduction> previousDeductions,
            Set<Long> validAnchorIds
    ) {
        for (Long anchorId : emptyIfNull(claim.getEvidenceAnchorIds())) {
            if (!validAnchorIds.contains(anchorId)) {
                throw new IllegalArgumentException("evidenceAnchorId " + anchorId
                        + " does not belong to current scoring session");
            }
        }

        AiScoreDeduction sourceDeduction = previousDeductions.get(claim.getSourceDeductionId());
        if (sourceDeduction == null) {
            throw new IllegalArgumentException("sourceDeductionId " + claim.getSourceDeductionId()
                    + " does not exist in previous scoring session");
        }

        AiScoreRecoveryInput recovery = new AiScoreRecoveryInput();
        recovery.setSourceDeductionId(claim.getSourceDeductionId());
        recovery.setRecoveryStatus(normalizeStatus(claim.getRecoveryStatus()));
        recovery.setRequestedRecoverPoints(nonNegative(claim.getRequestedRecoverPoints(), "requestedRecoverPoints"));
        recovery.setMaxRecoverablePoints(nonNegative(sourceDeduction.getMaxRecoverablePoints(), "maxRecoverablePoints"));
        recovery.setAcceptanceEvidence(claim.getAcceptanceEvidence());
        return recovery;
    }

    private AiScoreDeduction recoveryRow(
            Long sessionId,
            Long reportId,
            AiScoreRecoveryInput recovery,
            AiScoreStructuredResultRequest.RecoveryClaimInput claim,
            LocalDateTime now
    ) {
        AiScoreDeduction row = new AiScoreDeduction();
        row.setSessionId(sessionId);
        row.setReportId(reportId);
        row.setDeductionId("recovery-" + recovery.getSourceDeductionId());
        row.setDeductedPoints(ZERO);
        row.setRecoveredPoints(min(
                nonNegative(recovery.getRequestedRecoverPoints(), "requestedRecoverPoints"),
                nonNegative(recovery.getMaxRecoverablePoints(), "maxRecoverablePoints")
        ));
        row.setRecoverySourceDeductionId(recovery.getSourceDeductionId());
        row.setStatus(normalizeStatus(recovery.getRecoveryStatus()));
        row.setReason("上一轮扣分项已提交恢复证据并通过本轮验收");
        row.setRequiredFix("保持已恢复项的支撑材料完整可追溯");
        row.setAcceptanceCriteria(recovery.getAcceptanceEvidence());
        row.setEvidenceLevel("medium");
        row.setConfidence(DEFAULT_CONFIDENCE);
        row.setEvidenceAnchorIdsJson(toJsonArray(claim == null ? List.of() : emptyIfNull(claim.getEvidenceAnchorIds())));
        row.setCreatedAt(now);
        return row;
    }

    private BigDecimal min(BigDecimal left, BigDecimal right) {
        return left.compareTo(right) <= 0 ? left : right;
    }

    private BigDecimal nonNull(BigDecimal value) {
        return value == null ? ZERO : value;
    }

    private BigDecimal nonNegative(BigDecimal value, String fieldName) {
        BigDecimal safeValue = nonNull(value);
        if (safeValue.compareTo(ZERO) < 0) {
            throw new IllegalArgumentException(fieldName + " must be non-negative");
        }
        return safeValue;
    }

    private boolean hasCompleteHistoryScope(AiScoringSession session) {
        return session.getId() != null
                && session.getProjectId() != null
                && session.getTeamId() != null
                && session.getTrackId() != null
                && !session.getTrackId().isBlank();
    }

    private String normalizeStatus(String status) {
        return status == null ? "" : status.trim().toLowerCase();
    }

    private String toJsonArray(List<Long> values) {
        return values.stream()
                .map(String::valueOf)
                .collect(Collectors.joining(",", "[", "]"));
    }

    private <T> List<T> emptyIfNull(List<T> values) {
        return values == null ? List.of() : values;
    }

    private <T> Set<T> emptyIfNull(Set<T> values) {
        return values == null ? Set.of() : values;
    }
}
