package com.orep.backend.service;

import java.math.BigDecimal;

/**
 * MVP 阈值写死。改阈值必须 bump contractVersion，从而开新 docket。
 */
public final class StabilityBandCalculator {
    public static final String NOT_REVIEWED = "not_reviewed";
    public static final String GREEN = "green";
    public static final String YELLOW = "yellow";
    public static final String RED = "red";

    static final BigDecimal GREEN_MAX = new BigDecimal("2.0");
    static final BigDecimal YELLOW_MAX = new BigDecimal("3.0");
    static final BigDecimal SEEKABLE_GREEN_MIN = new BigDecimal("0.70");
    static final BigDecimal SEEKABLE_YELLOW_MIN = new BigDecimal("0.50");
    static final BigDecimal DIM_GREEN_MAX = new BigDecimal("0.08");
    static final BigDecimal DIM_YELLOW_MAX = new BigDecimal("0.12");

    private StabilityBandCalculator() {
    }

    public static String headline(String band) {
        if (RED.equals(band)) {
            return "本场不稳定，请教师复核";
        }
        if (YELLOW.equals(band)) {
            return "复评分差在黄档";
        }
        if (GREEN.equals(band)) {
            return "复评分差在绿档";
        }
        return "尚未复评";
    }

    public static String band(int completedRunCount, BigDecimal maxAbsDeltaFromFirst) {
        return band(completedRunCount, maxAbsDeltaFromFirst, null, null);
    }

    public static String band(
            int completedRunCount,
            BigDecimal maxAbsDeltaFromFirst,
            BigDecimal seekableAnchorRate,
            BigDecimal maxDimensionRatio
    ) {
        if (completedRunCount < 2) {
            return NOT_REVIEWED;
        }
        return worst(
                scoreBand(maxAbsDeltaFromFirst),
                seekableBand(seekableAnchorRate),
                dimensionBand(maxDimensionRatio)
        );
    }

    static String scoreBand(BigDecimal maxAbsDeltaFromFirst) {
        if (maxAbsDeltaFromFirst == null) {
            return NOT_REVIEWED;
        }
        if (maxAbsDeltaFromFirst.compareTo(GREEN_MAX) <= 0) {
            return GREEN;
        }
        if (maxAbsDeltaFromFirst.compareTo(YELLOW_MAX) <= 0) {
            return YELLOW;
        }
        return RED;
    }

    static String seekableBand(BigDecimal seekableAnchorRate) {
        if (seekableAnchorRate == null) {
            return null;
        }
        if (seekableAnchorRate.compareTo(SEEKABLE_GREEN_MIN) >= 0) {
            return GREEN;
        }
        if (seekableAnchorRate.compareTo(SEEKABLE_YELLOW_MIN) >= 0) {
            return YELLOW;
        }
        return RED;
    }

    static String dimensionBand(BigDecimal maxDimensionRatio) {
        if (maxDimensionRatio == null) {
            return null;
        }
        if (maxDimensionRatio.compareTo(DIM_GREEN_MAX) <= 0) {
            return GREEN;
        }
        if (maxDimensionRatio.compareTo(DIM_YELLOW_MAX) <= 0) {
            return YELLOW;
        }
        return RED;
    }

    static String worst(String... bands) {
        boolean sawScoreAxis = false;
        String worst = GREEN;
        for (String band : bands) {
            if (band == null) {
                continue;
            }
            if (NOT_REVIEWED.equals(band)) {
                return NOT_REVIEWED;
            }
            sawScoreAxis = true;
            if (rank(band) > rank(worst)) {
                worst = band;
            }
        }
        return sawScoreAxis ? worst : NOT_REVIEWED;
    }

    private static int rank(String band) {
        if (RED.equals(band)) {
            return 3;
        }
        if (YELLOW.equals(band)) {
            return 2;
        }
        if (GREEN.equals(band)) {
            return 1;
        }
        return 0;
    }
}
