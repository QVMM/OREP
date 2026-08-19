package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrainingDayLearningResourceProgressTest {

    @Test
    void mergesOverlappingRangesWithoutCountingRepeatedViewingTwice() {
        List<List<Integer>> ranges = new ArrayList<>(List.of(
                new ArrayList<>(List.of(0, 30)),
                new ArrayList<>(List.of(60, 90))
        ));

        ranges = TrainingDayLearningResourceService.mergeWatchedRanges(ranges, 20, 70);
        ranges = TrainingDayLearningResourceService.mergeWatchedRanges(ranges, 5, 25);

        assertEquals(List.of(List.of(0, 90)), ranges);
        assertEquals(90, TrainingDayLearningResourceService.watchedCoverageSeconds(ranges));
    }

    @Test
    void keepsSeparateRangesAcrossMultipleViewingSessions() {
        List<List<Integer>> ranges = TrainingDayLearningResourceService.mergeWatchedRanges(List.of(), 0, 25);
        ranges = TrainingDayLearningResourceService.mergeWatchedRanges(ranges, 80, 110);

        assertEquals(List.of(List.of(0, 25), List.of(80, 110)), ranges);
        assertEquals(55, TrainingDayLearningResourceService.watchedCoverageSeconds(ranges));
        assertEquals(110, TrainingDayLearningResourceService.furthestWatchedSecond(ranges));
    }

    @Test
    void rejectsFastForwardButAllowsContinuousPlaybackUpToDoubleSpeed() {
        assertTrue(TrainingDayLearningResourceService.isContinuousPlayback(5.0, 5));
        assertTrue(TrainingDayLearningResourceService.isContinuousPlayback(5.0, 10));
        assertFalse(TrainingDayLearningResourceService.isContinuousPlayback(1.0, 60));
        assertFalse(TrainingDayLearningResourceService.isContinuousPlayback(0.1, 1));
        assertFalse(TrainingDayLearningResourceService.isContinuousPlayback(31.0, 31));
    }
}
