package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDocketRun;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class IdentityStabilityTest {

    @Test
    void mixedHistoryKeepsIdentityGreenWithoutPaintingWholeDocket() {
        List<AiScoreDocketRun> runs = List.of(
                run(1, "40.9", false),
                run(2, "49.7", false),
                run(3, "44.5", false),
                run(4, "48.3", true),
                run(5, "48.3", true),
                run(6, "48.3", true)
        );
        IdentityStability.Slice identity = IdentityStability.evaluate(runs);
        assertEquals(StabilityBandCalculator.GREEN, identity.band);
        assertEquals(3, identity.runCount);
        assertTrue(identity.headline.contains("转写钉死"));
        assertTrue(identity.headline.contains("绿档"));
        assertEquals(
                StabilityBandCalculator.RED,
                StabilityBandCalculator.band(6, new BigDecimal("7.4"))
        );
    }

    @Test
    void trailingSameOfficialIsIdentityWhenFlagsMissing() {
        List<AiScoreDocketRun> runs = List.of(
                run(1, "40.9", null),
                run(2, "49.7", null),
                run(7, "48.3", null),
                run(8, "48.3", null),
                run(9, "48.3", null)
        );
        IdentityStability.Slice identity = IdentityStability.evaluate(runs);
        assertEquals(StabilityBandCalculator.GREEN, identity.band);
        assertEquals(3, identity.runCount);
        assertTrue(identity.headline.contains("连续"));
        assertFalse(identity.headline.contains("已经很准"));
    }

    @Test
    void singleLatestScoreIsNotIdentity() {
        IdentityStability.Slice identity = IdentityStability.evaluate(List.of(
                run(1, "40.9", null),
                run(2, "48.3", null)
        ));
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, identity.band);
        assertEquals(0, identity.runCount);
    }

    private static AiScoreDocketRun run(int index, String score, Boolean tapeGrounded) {
        AiScoreDocketRun row = new AiScoreDocketRun();
        row.setRunIndex(index);
        row.setOfficialScore(new BigDecimal(score));
        row.setTapeGrounded(tapeGrounded);
        return row;
    }
}
