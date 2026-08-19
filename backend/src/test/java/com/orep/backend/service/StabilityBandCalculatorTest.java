package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

class StabilityBandCalculatorTest {

    @Test
    void singleRunIsNotReviewedEvenIfDeltaLooksGreen() {
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, StabilityBandCalculator.band(0, BigDecimal.ZERO));
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, StabilityBandCalculator.band(1, BigDecimal.ZERO));
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, StabilityBandCalculator.band(1, new BigDecimal("4.0")));
    }

    @Test
    void twoRunsUseDeltaThresholds() {
        assertEquals(StabilityBandCalculator.GREEN, StabilityBandCalculator.band(2, new BigDecimal("2.0")));
        assertEquals(StabilityBandCalculator.YELLOW, StabilityBandCalculator.band(3, new BigDecimal("2.01")));
        assertEquals(StabilityBandCalculator.YELLOW, StabilityBandCalculator.band(3, new BigDecimal("3.0")));
        assertEquals(StabilityBandCalculator.RED, StabilityBandCalculator.band(3, new BigDecimal("3.01")));
        assertEquals(StabilityBandCalculator.RED, StabilityBandCalculator.band(3, new BigDecimal("4.0")));
    }

    @Test
    void missingDeltaIsNotReviewed() {
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, StabilityBandCalculator.band(3, null));
    }

    @Test
    void seekableAndDimensionAxesCanTurnGreenYellowOrRed() {
        assertEquals(StabilityBandCalculator.GREEN, StabilityBandCalculator.seekableBand(new BigDecimal("0.70")));
        assertEquals(StabilityBandCalculator.YELLOW, StabilityBandCalculator.seekableBand(new BigDecimal("0.50")));
        assertEquals(StabilityBandCalculator.RED, StabilityBandCalculator.seekableBand(new BigDecimal("0.49")));
        assertEquals(StabilityBandCalculator.GREEN, StabilityBandCalculator.dimensionBand(new BigDecimal("0.08")));
        assertEquals(StabilityBandCalculator.YELLOW, StabilityBandCalculator.dimensionBand(new BigDecimal("0.12")));
        assertEquals(StabilityBandCalculator.RED, StabilityBandCalculator.dimensionBand(new BigDecimal("0.13")));
    }

    @Test
    void missingAxesDoNotPaintRedAndWorstAxisWins() {
        assertEquals(
                StabilityBandCalculator.GREEN,
                StabilityBandCalculator.band(3, new BigDecimal("1.0"), null, null)
        );
        assertEquals(
                StabilityBandCalculator.RED,
                StabilityBandCalculator.band(3, new BigDecimal("0.0"), new BigDecimal("0.40"), new BigDecimal("0.01"))
        );
        assertEquals(
                StabilityBandCalculator.YELLOW,
                StabilityBandCalculator.band(3, new BigDecimal("0.0"), new BigDecimal("0.90"), new BigDecimal("0.10"))
        );
    }

    @Test
    void headlinesNeverClaimAccuracy() {
        assertEquals("尚未复评", StabilityBandCalculator.headline(StabilityBandCalculator.NOT_REVIEWED));
        assertEquals("复评分差在绿档", StabilityBandCalculator.headline(StabilityBandCalculator.GREEN));
        assertEquals("复评分差在黄档", StabilityBandCalculator.headline(StabilityBandCalculator.YELLOW));
        assertEquals("本场不稳定，请教师复核", StabilityBandCalculator.headline(StabilityBandCalculator.RED));
        assertEquals("尚未复评", StabilityBandCalculator.headline(null));
        assertFalse(StabilityBandCalculator.headline(StabilityBandCalculator.GREEN).contains("已经很准"));
        assertFalse(StabilityBandCalculator.headline(StabilityBandCalculator.RED).contains("已经很准"));
    }
}
