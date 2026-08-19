package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;


class RunCoverageCalculatorTest {

    @Test
    void emptyDeclarationsAreNullNotRedZero() {
        assertNull(RunCoverageCalculator.transcriptCoverage(null));
        assertNull(RunCoverageCalculator.transcriptCoverage(List.of()));
        assertNull(RunCoverageCalculator.seekableAnchorRate(null));
        assertNull(RunCoverageCalculator.seekableAnchorRate(List.of()));
    }

    @Test
    void transcriptCoverageUnionsOverlappingSegments() {
        List<Map<String, Object>> segments = List.of(
                Map.of("start", 0, "end", 10),
                Map.of("start", 8, "end", 20),
                Map.of("startMs", 18000L, "endMs", 20000L)
        );
        BigDecimal coverage = RunCoverageCalculator.transcriptCoverage(segments);
        assertEquals(0, coverage.compareTo(new BigDecimal("1.0000")));
    }

    @Test
    void transcriptCoverageIsPartialWhenTailMissing() {
        List<Map<String, Object>> segments = List.of(
                Map.of("start", 0, "end", 10),
                Map.of("start", 20, "end", 30)
        );
        BigDecimal coverage = RunCoverageCalculator.transcriptCoverage(segments);
        assertEquals(0, coverage.compareTo(new BigDecimal("0.6667")));
    }

    @Test
    void seekableRateCountsStartMsOrSourceRefClock() {
        PipelineCallbackRequest.EvidenceAnchorInput timed = new PipelineCallbackRequest.EvidenceAnchorInput();
        timed.setStartMs(12000L);
        PipelineCallbackRequest.EvidenceAnchorInput fromRef = new PipelineCallbackRequest.EvidenceAnchorInput();
        fromRef.setSourceRef("transcript@01:20");
        PipelineCallbackRequest.EvidenceAnchorInput missing = new PipelineCallbackRequest.EvidenceAnchorInput();
        missing.setSourceRef("ppt-page-3");
        BigDecimal rate = RunCoverageCalculator.seekableAnchorRate(List.of(timed, fromRef, missing));
        assertEquals(0, rate.compareTo(new BigDecimal("0.6667")));
    }
}
