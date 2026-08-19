package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * transcriptCoverage = union of timed ASR segments / media duration.
 * seekableAnchorRate = anchors with a jumpable timestamp / declared anchors.
 * Empty declarations yield null so missing data does not paint the band red.
 */
public final class RunCoverageCalculator {
    private static final Pattern SOURCE_TIME = Pattern.compile("@(\\d{1,2}):(\\d{2})(?::(\\d{2}))?");
    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP);

    private RunCoverageCalculator() {
    }

    public static final class Rates {
        public final BigDecimal transcriptCoverage;
        public final BigDecimal seekableAnchorRate;

        public Rates(BigDecimal transcriptCoverage, BigDecimal seekableAnchorRate) {
            this.transcriptCoverage = transcriptCoverage;
            this.seekableAnchorRate = seekableAnchorRate;
        }
    }

    public static Rates fromCallback(PipelineCallbackRequest.PipelineFinalResult result) {
        if (result == null) {
            return new Rates(null, null);
        }
        return new Rates(
                transcriptCoverage(result.getAsrSegments()),
                seekableAnchorRate(result.getEvidenceAnchors())
        );
    }

    static BigDecimal transcriptCoverage(List<Map<String, Object>> segments) {
        if (segments == null || segments.isEmpty()) {
            return null;
        }
        List<long[]> intervals = new ArrayList<>();
        long maxEnd = 0L;
        for (Map<String, Object> segment : segments) {
            if (segment == null) {
                continue;
            }
            long start = timeMs(segment, true);
            long end = timeMs(segment, false);
            if (start < 0 || end < start) {
                continue;
            }
            intervals.add(new long[]{start, end});
            maxEnd = Math.max(maxEnd, end);
        }
        if (intervals.isEmpty() || maxEnd <= 0) {
            return ZERO;
        }
        intervals.sort(Comparator.comparingLong(item -> item[0]));
        long covered = 0;
        long cursorStart = intervals.get(0)[0];
        long cursorEnd = intervals.get(0)[1];
        for (int i = 1; i < intervals.size(); i++) {
            long[] next = intervals.get(i);
            if (next[0] <= cursorEnd) {
                cursorEnd = Math.max(cursorEnd, next[1]);
            } else {
                covered += cursorEnd - cursorStart;
                cursorStart = next[0];
                cursorEnd = next[1];
            }
        }
        covered += cursorEnd - cursorStart;
        return ratio(covered, maxEnd);
    }

    static BigDecimal seekableAnchorRate(List<PipelineCallbackRequest.EvidenceAnchorInput> anchors) {
        if (anchors == null || anchors.isEmpty()) {
            return null;
        }
        int declared = 0;
        int seekable = 0;
        for (PipelineCallbackRequest.EvidenceAnchorInput anchor : anchors) {
            if (anchor == null) {
                continue;
            }
            declared++;
            if (isSeekable(anchor)) {
                seekable++;
            }
        }
        if (declared == 0) {
            return null;
        }
        return ratio(seekable, declared);
    }

    static boolean isSeekable(PipelineCallbackRequest.EvidenceAnchorInput anchor) {
        if (anchor.getStartMs() != null && anchor.getStartMs() >= 0) {
            return true;
        }
        String sourceRef = anchor.getSourceRef();
        return sourceRef != null && SOURCE_TIME.matcher(sourceRef).find();
    }

    private static long timeMs(Map<String, Object> segment, boolean start) {
        Object millis = start ? first(segment, "startMs", "start_ms") : first(segment, "endMs", "end_ms");
        if (millis instanceof Number number) {
            return number.longValue();
        }
        Object seconds = start ? first(segment, "start", "begin") : first(segment, "end", "stop");
        if (seconds instanceof Number number) {
            return Math.round(number.doubleValue() * 1000.0);
        }
        if (seconds instanceof String text) {
            try {
                return Math.round(Double.parseDouble(text) * 1000.0);
            } catch (NumberFormatException ignored) {
                return -1L;
            }
        }
        return -1L;
    }

    private static Object first(Map<String, Object> segment, String... keys) {
        for (String key : keys) {
            if (segment.containsKey(key) && segment.get(key) != null) {
                return segment.get(key);
            }
        }
        return null;
    }

    private static BigDecimal ratio(long numerator, long denominator) {
        if (denominator <= 0) {
            return ZERO;
        }
        return BigDecimal.valueOf(numerator)
                .divide(BigDecimal.valueOf(denominator), 4, RoundingMode.HALF_UP);
    }
}
