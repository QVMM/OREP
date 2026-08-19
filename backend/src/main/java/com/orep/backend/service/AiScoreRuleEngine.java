package com.orep.backend.service;

import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class AiScoreRuleEngine {
    private static final String RULE_ENGINE_VERSION = "p8-c";
    private static final Set<String> RECOVERED_STATUSES = Set.of("fixed", "verified", "recovered");
    private static final BigDecimal ZERO = BigDecimal.ZERO;
    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100");

    public AiScoreRuleEngineResult score(
            AiScoreStructuredResultRequest request,
            List<AiScoreRecoveryInput> recoveries
    ) {
        if (request == null) {
            throw new IllegalArgumentException("request must not be null");
        }

        List<AiScoreRecoveryInput> recoveryInputs = recoveries == null ? List.of() : recoveries;
        List<AiScoreStructuredResultRequest.ObservationInput> observations =
                request.getObservations() == null ? List.of() : request.getObservations();
        List<AiScoreStructuredResultRequest.DeductionInput> deductions =
                request.getDeductions() == null ? List.of() : request.getDeductions();
        Map<String, List<AiScoreStructuredResultRequest.DeductionInput>> deductionsByObservation =
                deductions.stream()
                        .filter(this::isActiveDeduction)
                        .collect(Collectors.groupingBy(
                                AiScoreStructuredResultRequest.DeductionInput::getObservationCode,
                                LinkedHashMap::new,
                                Collectors.toList()
                        ));
        AcceptedRecoveries acceptedRecoveries = acceptedRecoveries(recoveryInputs);
        Map<String, BigDecimal> recoveriesByDeduction = acceptedRecoveries.recoveries().stream()
                .collect(Collectors.toMap(
                        AiScoreRecoveryInput::getSourceDeductionId,
                        recovery -> nonNegativeRecoveryValue(
                                recovery.getRequestedRecoverPoints(),
                                "recoveries.requestedRecoverPoints"
                        ).min(nonNegativeRecoveryValue(
                                recovery.getMaxRecoverablePoints(),
                                "recoveries.maxRecoverablePoints"
                        )),
                        BigDecimal::add,
                        LinkedHashMap::new
                ));

        BigDecimal baseScore = ZERO;
        BigDecimal deductedScore = ZERO;
        BigDecimal rawScore = ZERO;
        BigDecimal recoveredScore = acceptedRecoveries.recoveredScore();
        BigDecimal currentScoreCap = ZERO;
        BigDecimal finalScore = ZERO;
        Map<String, BigDecimal> dimensionScores = new LinkedHashMap<>();
        List<AiScoreRuleEngineResult.ObservationScoreResult> observationResults = new ArrayList<>();

        for (AiScoreStructuredResultRequest.ObservationInput observation : observations) {
            ObservationCalculation calculation = scoreObservation(
                    observation,
                    deductionsByObservation.getOrDefault(observation.getObservationCode(), List.of()),
                    recoveriesByDeduction
            );
            baseScore = baseScore.add(calculation.baseScore());
            deductedScore = deductedScore.add(calculation.deductedScore());
            rawScore = rawScore.add(calculation.rawScore());
            currentScoreCap = currentScoreCap.add(calculation.scoreCap());
            finalScore = finalScore.add(calculation.finalScore());
            dimensionScores.merge(
                    observation.getDimensionCode(),
                    calculation.finalScore(),
                    BigDecimal::add
            );
            observationResults.add(toObservationResult(observation, calculation));
        }

        AiScoreRuleEngineResult result = new AiScoreRuleEngineResult();
        result.setRuleEngineVersion(RULE_ENGINE_VERSION);
        result.setBaseScore(twoDecimals(baseScore));
        result.setDeductedScore(twoDecimals(deductedScore));
        result.setRawScore(twoDecimals(rawScore));
        result.setRecoveredScore(twoDecimals(recoveredScore));
        result.setCurrentScoreCap(twoDecimals(currentScoreCap));
        result.setFinalScore(twoDecimals(finalScore));
        result.setNotPerfectReasons(notPerfectReasons(result));
        result.setCalibrationJson(calibrationJson(result));
        result.setObservations(request.getObservations());
        result.setObservationResults(observationResults);
        result.setDimensionScores(twoDecimalMap(dimensionScores));
        result.setDeductions(request.getDeductions());
        result.setRecoveries(acceptedRecoveries.recoveries());
        return result;
    }

    private ObservationCalculation scoreObservation(
            AiScoreStructuredResultRequest.ObservationInput observation,
            List<AiScoreStructuredResultRequest.DeductionInput> deductions,
            Map<String, BigDecimal> recoveriesByDeduction
    ) {
        BigDecimal maxScore = positiveOrDefault(observation.getMaxScore(), observation.getScoreCap());
        BigDecimal scoreCap = positiveOrDefault(observation.getScoreCap(), maxScore).min(maxScore);
        BigDecimal baseScore = positiveOrDefault(observation.getRawScore(), ZERO).min(maxScore);
        BigDecimal total = ZERO;
        for (AiScoreStructuredResultRequest.DeductionInput deduction : deductions) {
            if (deduction != null && deduction.getDeductedPoints() != null) {
                total = total.add(deduction.getDeductedPoints());
            }
        }
        BigDecimal deductedScore = total.max(ZERO).min(baseScore);
        BigDecimal rawScore = baseScore.subtract(deductedScore).max(ZERO);
        BigDecimal recoveredScore = ZERO;
        for (AiScoreStructuredResultRequest.DeductionInput deduction : deductions) {
            if (deduction != null && deduction.getDeductionId() != null) {
                BigDecimal recovery = recoveriesByDeduction.getOrDefault(deduction.getDeductionId(), ZERO);
                BigDecimal maxRecoverable = positiveOrDefault(deduction.getMaxRecoverablePoints(), ZERO);
                recoveredScore = recoveredScore.add(recovery.min(maxRecoverable));
            }
        }
        BigDecimal finalScore = rawScore.add(recoveredScore).min(scoreCap).max(ZERO);
        return new ObservationCalculation(
                twoDecimals(baseScore),
                twoDecimals(deductedScore),
                twoDecimals(rawScore),
                twoDecimals(recoveredScore),
                twoDecimals(scoreCap),
                twoDecimals(finalScore)
        );
    }

    private AiScoreRuleEngineResult.ObservationScoreResult toObservationResult(
            AiScoreStructuredResultRequest.ObservationInput observation,
            ObservationCalculation calculation
    ) {
        AiScoreRuleEngineResult.ObservationScoreResult result = new AiScoreRuleEngineResult.ObservationScoreResult();
        result.setObservationCode(observation.getObservationCode());
        result.setObservationName(observation.getObservationName());
        result.setDimensionCode(observation.getDimensionCode());
        result.setDimensionName(observation.getDimensionName());
        result.setMaxScore(twoDecimals(positiveOrDefault(observation.getMaxScore(), observation.getScoreCap())));
        result.setBaseScore(calculation.baseScore());
        result.setRawScore(calculation.rawScore());
        result.setDeductedScore(calculation.deductedScore());
        result.setRecoveredScore(calculation.recoveredScore());
        result.setScoreCap(calculation.scoreCap());
        result.setFinalScore(calculation.finalScore());
        result.setEvidenceLevel(observation.getEvidenceLevel());
        return result;
    }

    private boolean isActiveDeduction(AiScoreStructuredResultRequest.DeductionInput deduction) {
        if (deduction == null) {
            return false;
        }
        String status = normalizeStatus(deduction.getStatus());
        return !"invalid".equals(status) && !"recovered".equals(status);
    }

    private AcceptedRecoveries acceptedRecoveries(List<AiScoreRecoveryInput> recoveries) {
        BigDecimal total = ZERO;
        List<AiScoreRecoveryInput> accepted = new ArrayList<>();
        for (int i = 0; i < recoveries.size(); i++) {
            AiScoreRecoveryInput recovery = recoveries.get(i);
            if (recovery == null) {
                continue;
            }

            BigDecimal requested = nonNegativeRecoveryValue(
                    recovery.getRequestedRecoverPoints(),
                    "recoveries[" + i + "].requestedRecoverPoints"
            );
            BigDecimal maxRecoverable = nonNegativeRecoveryValue(
                    recovery.getMaxRecoverablePoints(),
                    "recoveries[" + i + "].maxRecoverablePoints"
            );
            if (RECOVERED_STATUSES.contains(normalizeStatus(recovery.getRecoveryStatus()))) {
                requireText(recovery.getSourceDeductionId(), "recoveries[" + i + "].sourceDeductionId");
                requireText(recovery.getAcceptanceEvidence(), "recoveries[" + i + "].acceptanceEvidence");
                total = total.add(requested.min(maxRecoverable));
                accepted.add(recovery);
            }
        }
        return new AcceptedRecoveries(total, List.copyOf(accepted));
    }

    private BigDecimal nonNegativeRecoveryValue(BigDecimal value, String fieldPath) {
        if (value == null) {
            return ZERO;
        }
        if (value.compareTo(ZERO) < 0) {
            throw new IllegalArgumentException(fieldPath + " must be non-negative");
        }
        return value;
    }

    private String normalizeStatus(String status) {
        return status == null ? "" : status.trim().toLowerCase();
    }

    private void requireText(String value, String fieldPath) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(fieldPath + " must not be blank");
        }
    }

    private BigDecimal clamp(BigDecimal value) {
        if (value == null) {
            return ZERO;
        }
        return value.max(ZERO).min(ONE_HUNDRED);
    }

    private BigDecimal positiveOrDefault(BigDecimal value, BigDecimal defaultValue) {
        if (value == null) {
            return defaultValue == null ? ZERO : defaultValue.max(ZERO);
        }
        return value.max(ZERO);
    }

    private BigDecimal twoDecimals(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    private Map<String, BigDecimal> twoDecimalMap(Map<String, BigDecimal> source) {
        Map<String, BigDecimal> result = new LinkedHashMap<>();
        source.forEach((key, value) -> result.put(key, twoDecimals(value)));
        return result;
    }

    private String calibrationJson(AiScoreRuleEngineResult result) {
        return "{"
                + "\"baseScore\":\"" + plain(result.getBaseScore()) + "\","
                + "\"rawScore\":\"" + plain(result.getRawScore()) + "\","
                + "\"deductedScore\":\"" + plain(result.getDeductedScore()) + "\","
                + "\"recoveredScore\":\"" + plain(result.getRecoveredScore()) + "\","
                + "\"currentScoreCap\":\"" + plain(result.getCurrentScoreCap()) + "\","
                + "\"finalScore\":\"" + plain(result.getFinalScore()) + "\","
                + "\"notPerfectReasons\":" + reasonsJson(result.getNotPerfectReasons())
                + "}";
    }

    private List<String> notPerfectReasons(AiScoreRuleEngineResult result) {
        List<String> reasons = new ArrayList<>();
        if (result.getCurrentScoreCap().compareTo(ONE_HUNDRED) < 0) {
            reasons.add("evidence_cap");
        }
        if (result.getDeductedScore().compareTo(ZERO) > 0) {
            reasons.add("current_deductions");
        }
        return List.copyOf(reasons);
    }

    private String reasonsJson(List<String> reasons) {
        StringBuilder builder = new StringBuilder("[");
        for (int i = 0; i < reasons.size(); i++) {
            if (i > 0) {
                builder.append(",");
            }
            builder.append("\"").append(reasons.get(i)).append("\"");
        }
        builder.append("]");
        return builder.toString();
    }

    private String plain(BigDecimal value) {
        return value.toPlainString();
    }

    private record AcceptedRecoveries(BigDecimal recoveredScore, List<AiScoreRecoveryInput> recoveries) {
    }

    private record ObservationCalculation(
            BigDecimal baseScore,
            BigDecimal deductedScore,
            BigDecimal rawScore,
            BigDecimal recoveredScore,
            BigDecimal scoreCap,
            BigDecimal finalScore
    ) {
    }
}
