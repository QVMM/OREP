package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDocketRun;

import java.util.List;

/**
 * Points from the session you are reading to a newer completed run on the same docket.
 * Never swaps this session's official score.
 */
public final class DocketRunPointer {
    private DocketRunPointer() {
    }

    public static Pointer from(List<AiScoreDocketRun> runs, Long sessionId) {
        if (runs == null || runs.isEmpty() || sessionId == null) {
            return Pointer.none();
        }
        AiScoreDocketRun current = null;
        AiScoreDocketRun latest = null;
        for (AiScoreDocketRun run : runs) {
            if (run == null || run.getRunIndex() == null) {
                continue;
            }
            if (sessionId.equals(run.getSessionId())) {
                current = run;
            }
            if (latest == null || run.getRunIndex() > latest.getRunIndex()) {
                latest = run;
            }
        }
        if (current == null || latest == null || latest.getSessionId() == null) {
            return Pointer.none(current == null ? null : current.getRunIndex());
        }
        if (latest.getRunIndex() > current.getRunIndex() && !sessionId.equals(latest.getSessionId())) {
            return new Pointer(current.getRunIndex(), latest.getSessionId(), latest.getRunIndex());
        }
        return new Pointer(current.getRunIndex(), null, null);
    }

    public static final class Pointer {
        public final Integer thisRunIndex;
        public final Long newerSessionId;
        public final Integer newerRunIndex;

        Pointer(Integer thisRunIndex, Long newerSessionId, Integer newerRunIndex) {
            this.thisRunIndex = thisRunIndex;
            this.newerSessionId = newerSessionId;
            this.newerRunIndex = newerRunIndex;
        }

        static Pointer none() {
            return new Pointer(null, null, null);
        }

        static Pointer none(Integer thisRunIndex) {
            return new Pointer(thisRunIndex, null, null);
        }
    }
}
