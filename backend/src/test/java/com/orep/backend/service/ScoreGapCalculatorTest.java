package com.orep.backend.service;

import com.orep.backend.dto.ScoreGap;
import com.orep.backend.dto.SubstanceClaim;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ScoreGapCalculatorTest {

    @Test
    void firstFieldLeavesClosureAndDeltaNull() {
        ScoreGapCalculator.Input input = base(new BigDecimal("70.00"), new BigDecimal("100.00"));
        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        assertNull(gap.getClosureRate());
        assertNull(gap.getDeltaFromLast());
        assertEquals(0, gap.getRepairBonus().compareTo(BigDecimal.ZERO));
        assertEquals(0, gap.getOfficialScore().compareTo(new BigDecimal("70.00")));
    }

    @Test
    void checkedWithoutEvidenceCannotBeFullClosure() {
        ScoreGapCalculator.Input input = base(new BigDecimal("70.00"), new BigDecimal("100.00"));
        ScoreGapCalculator.PriorTask checked = new ScoreGapCalculator.PriorTask();
        checked.accepted = true;
        checked.evidenceAttached = false;
        input.priorTasks = List.of(checked, checked);
        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        assertEquals(0, gap.getClosureRate().compareTo(BigDecimal.ZERO));
        assertEquals(0, gap.getRepairBonus().compareTo(BigDecimal.ZERO));
    }

    @Test
    void allFixedStillNoRunningEvidenceStaysBelowCeiling() {
        ScoreGapCalculator.Input input = base(new BigDecimal("88.00"), new BigDecimal("100.00"));
        input.priorTasks = List.of(accepted("2"), accepted("3"));
        input.hasStableDemoEvidence = false;
        input.claims = List.of(fail(SubstanceClaimEvaluator.WRAPPER, "本场没有运行证据。"));
        input.previousOfficialScore = new BigDecimal("80.00");

        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        assertEquals(0, gap.getClosureRate().compareTo(BigDecimal.ONE));
        assertTrue(gap.getOfficialScore().compareTo(gap.getTrackCeiling()) < 0);
        assertTrue(gap.getOfficialScore().compareTo(new BigDecimal("100.00")) < 0);
        assertFalse(gap.getCeilingGaps().isEmpty());
        assertEquals("差异与仓库仍缺", gap.getCeilingGaps().getFirst().getTitle());
        assertNotNull(gap.getDeltaFromLast());
        assertTrue(gap.getRepairBonus().compareTo(BigDecimal.ZERO) > 0);
        assertTrue(gap.getRepairBonus().compareTo(ScoreGapCalculator.REPAIR_BONUS_CAP) <= 0);
    }

    @Test
    void closureOneCannotLiftLedgerFullScoreToCeilingWithoutDemo() {
        ScoreGapCalculator.Input input = base(new BigDecimal("100.00"), new BigDecimal("100.00"));
        input.priorTasks = List.of(accepted("4"), accepted("4"));
        input.hasStableDemoEvidence = false;
        input.claims = List.of(fail(SubstanceClaimEvaluator.ADVANCEMENT, "口头先进，没有对比测试。"));

        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        assertEquals(0, gap.getClosureRate().compareTo(BigDecimal.ONE));
        assertTrue(gap.getOfficialScore().compareTo(gap.getTrackCeiling()) < 0);
        assertTrue(gap.getCeilingGaps().size() >= 1);
    }

    @Test
    void doesNotDefaultCeilingToOneHundred() {
        ScoreGapCalculator.Input input = base(new BigDecimal("40.00"), new BigDecimal("80.00"));
        input.hasStableDemoEvidence = true;
        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        assertEquals(0, gap.getTrackCeiling().compareTo(new BigDecimal("80.00")));
        assertFalse(gap.getCeilingGaps().isEmpty());
    }

    @Test
    void firstFieldDoesNotWriteZeroDelta() {
        ScoreGapCalculator.Input input = base(new BigDecimal("37.60"), new BigDecimal("90.00"));
        input.previousOfficialScore = null;
        assertNull(ScoreGapCalculator.evaluate(input).getDeltaFromLast());
    }

    private static ScoreGapCalculator.Input base(BigDecimal ledger, BigDecimal ceiling) {
        ScoreGapCalculator.Input input = new ScoreGapCalculator.Input();
        input.ledgerScore = ledger;
        input.trackCeiling = ceiling;
        input.hasStableDemoEvidence = true;
        return input;
    }

    private static ScoreGapCalculator.PriorTask accepted(String gain) {
        ScoreGapCalculator.PriorTask task = new ScoreGapCalculator.PriorTask();
        task.accepted = true;
        task.evidenceAttached = true;
        task.expectedGainPoints = new BigDecimal(gain);
        return task;
    }

    private static SubstanceClaim fail(String type, String statement) {
        SubstanceClaim claim = new SubstanceClaim();
        claim.setClaimType(type);
        claim.setVerdict("fail");
        claim.setClaimStatus("seen_in_session");
        claim.setStatement(statement);
        return claim;
    }
}
