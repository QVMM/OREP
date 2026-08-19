package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDocketRun;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

/**
 * Whole-docket band stays honest against the first successful run.
 * Tape-grounded (or trailing same official) is a separate slice and never
 * paints the whole docket green.
 */
public final class IdentityStability {
    private IdentityStability() {
    }

    public static Slice evaluate(List<AiScoreDocketRun> runs) {
        List<AiScoreDocketRun> safe = runs == null ? List.of() : runs;
        List<AiScoreDocketRun> flagged = new ArrayList<>();
        for (AiScoreDocketRun run : safe) {
            if (run != null && Boolean.TRUE.equals(run.getTapeGrounded())) {
                flagged.add(run);
            }
        }
        if (flagged.size() >= 2) {
            return slice(flagged, "转写钉死");
        }
        return trailing(safe);
    }

    private static Slice trailing(List<AiScoreDocketRun> runs) {
        if (runs.isEmpty()) {
            return Slice.none();
        }
        AiScoreDocketRun last = null;
        for (int i = runs.size() - 1; i >= 0; i--) {
            if (runs.get(i) != null && runs.get(i).getOfficialScore() != null) {
                last = runs.get(i);
                break;
            }
        }
        if (last == null) {
            return Slice.none();
        }
        List<AiScoreDocketRun> streak = new ArrayList<>();
        for (int i = runs.size() - 1; i >= 0; i--) {
            AiScoreDocketRun run = runs.get(i);
            if (run == null || run.getOfficialScore() == null) {
                break;
            }
            if (run.getOfficialScore().compareTo(last.getOfficialScore()) != 0) {
                break;
            }
            streak.add(0, run);
        }
        if (streak.size() < 2) {
            return Slice.none();
        }
        return slice(streak, "最近权威分连续");
    }

    private static Slice slice(List<AiScoreDocketRun> identity, String prefix) {
        BigDecimal first = identity.get(0).getOfficialScore();
        BigDecimal max = BigDecimal.ZERO;
        for (AiScoreDocketRun run : identity) {
            if (run.getOfficialScore() == null || first == null) {
                continue;
            }
            BigDecimal delta = run.getOfficialScore().subtract(first).abs();
            if (delta.compareTo(max) > 0) {
                max = delta;
            }
        }
        String band = StabilityBandCalculator.band(identity.size(), max, null, null);
        String headline = prefix + identity.size() + " 次分差在"
                + (StabilityBandCalculator.GREEN.equals(band) ? "绿档"
                : StabilityBandCalculator.YELLOW.equals(band) ? "黄档"
                : StabilityBandCalculator.RED.equals(band) ? "红档"
                : "未复评");
        if (StabilityBandCalculator.GREEN.equals(band) && prefix.startsWith("最近")) {
            headline = prefix + " " + identity.size() + " 次相同";
        }
        return new Slice(band, identity.size(), headline);
    }

    public static final class Slice {
        public final String band;
        public final int runCount;
        public final String headline;

        Slice(String band, int runCount, String headline) {
            this.band = band;
            this.runCount = runCount;
            this.headline = headline;
        }

        static Slice none() {
            return new Slice(StabilityBandCalculator.NOT_REVIEWED, 0, "");
        }
    }
}
