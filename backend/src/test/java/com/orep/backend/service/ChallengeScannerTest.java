package com.orep.backend.service;

import com.orep.backend.dto.Challenge;
import com.orep.backend.dto.ChallengeSet;
import com.orep.backend.dto.SubstanceClaim;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class ChallengeScannerTest {

    @Test
    void failedScanStaysIncompleteAndStillAllowsDraft() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.failed = true;
        ChallengeSet set = ChallengeScanner.scan(input);
        assertFalse(set.isScanned());
        assertEquals(DeliberationStageMachine.CHALLENGE_NOTE, set.getNote());
        assertTrue(set.getItems().isEmpty());
    }

    @Test
    void emptySuccessfulScanIsNotIncomplete() {
        ChallengeSet set = ChallengeScanner.scan(new ChallengeScanner.Input());
        assertTrue(set.isScanned());
        assertEquals(ChallengeScanner.EMPTY_NOTE, set.getNote());
        assertTrue(set.getItems().isEmpty());
    }

    @Test
    void deductionWithoutSeekableAnchorIsTypeOne() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.deductions.add(deduction("loss-innov", "创新成效", "4.0", List.of()));
        ChallengeSet set = ChallengeScanner.scan(input);
        assertTrue(set.isScanned());
        assertEquals(1, set.getItems().size());
        Challenge item = set.getItems().get(0);
        assertEquals(ChallengeScanner.SCORE_WITHOUT_ANCHOR, item.getType());
        assertEquals("创新成效", item.getTargetDimension());
        assertEquals("loss-innov", item.getLossId());
        assertTrue(item.getAnchorIds().isEmpty());
        assertFalse(item.isSeekable());
        assertEquals(ChallengeScanner.STATUS_PENDING, item.getStatus());
        assertEquals(new BigDecimal("4.00"), item.getProposedRestorePoints());
        assertTrue(item.getStatement().contains("创新成效扣了 4 分"));
        assertTrue(item.getStatement().contains("没有可跳转的证据"));
        assertNull(item.getStartMs());
    }

    @Test
    void outOfRangeAnchorIsTypeTwoAndKeepsExistingTimestamp() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.durationMs = 60_000L;
        input.anchors.add(anchor(11L, 180_000L, 181_000L, "video@03:00", "仓库提交页"));
        input.deductions.add(deduction("loss-repo", "技术实现", "5.0", List.of(11L)));
        ChallengeSet set = ChallengeScanner.scan(input);
        Challenge mismatch = byType(set, ChallengeScanner.ANCHOR_MISMATCH);
        assertNotNull(mismatch);
        assertEquals("技术实现", mismatch.getTargetDimension());
        assertEquals("loss-repo", mismatch.getLossId());
        assertEquals(List.of(11L), mismatch.getAnchorIds());
        assertEquals(180_000L, mismatch.getStartMs());
        assertTrue(mismatch.isSeekable());
        assertFalse(mismatch.getStatement().contains("03:01"));
        assertTrue(mismatch.getStatement().contains("无法跳转或超出录像时长"));
    }

    @Test
    void clauseMismatchRequiresExistingAnchorAndDoesNotInventTime() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.durationMs = 120_000L;
        input.anchors.add(anchor(7L, 12_000L, 16_000L, "video@00:12", "现场只展示了登录页"));
        ChallengeScanner.Deduction deduction = deduction("loss-clause", "商业价值", "3.0", List.of(7L));
        deduction.reason = "缺少农户替代人工的对照数据";
        input.deductions.add(deduction);
        ChallengeSet set = ChallengeScanner.scan(input);
        Challenge mismatch = byType(set, ChallengeScanner.CLAUSE_MISMATCH);
        assertNotNull(mismatch);
        assertEquals(List.of(7L), mismatch.getAnchorIds());
        assertEquals(12_000L, mismatch.getStartMs());
        assertTrue(mismatch.isSeekable());
        assertTrue(mismatch.getStatement().contains("量表条款与现场证据对不上"));
    }

    @Test
    void failClaimWithoutSeekableAnchorIsAttackable() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        SubstanceClaim wrapper = new SubstanceClaim();
        wrapper.setClaimType("wrapper");
        wrapper.setVerdict("fail");
        wrapper.setStatement("本场只提到成稿改写。");
        input.claims.add(wrapper);
        ChallengeSet set = ChallengeScanner.scan(input);
        Challenge item = set.getItems().get(0);
        assertEquals(ChallengeScanner.SCORE_WITHOUT_ANCHOR, item.getType());
        assertEquals("claim:wrapper", item.getLossId());
        assertFalse(item.isSeekable());
        assertTrue(item.getStatement().contains("套壳"));
    }

    @Test
    void observationScoreWithoutAnchorCollapsesPerDimension() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.observations.add(observation("observation:1", "职业素养", "8.0"));
        input.observations.add(observation("observation:2", "职业素养", "7.0"));
        input.observations.add(observation("observation:3", "团队合作", "6.0"));
        ChallengeSet set = ChallengeScanner.scan(input);
        assertEquals(2, set.getItems().size());
        assertEquals("职业素养", set.getItems().get(0).getTargetDimension());
        assertEquals("团队合作", set.getItems().get(1).getTargetDimension());
    }

    @Test
    void capsAtFourAndNeverInventTimestamps() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        for (int i = 1; i <= 6; i++) {
            input.deductions.add(deduction("loss-" + i, "维度" + i, "2.0", List.of()));
        }
        ChallengeSet set = ChallengeScanner.scan(input);
        assertEquals(4, set.getItems().size());
        for (Challenge item : set.getItems()) {
            assertNull(item.getStartMs());
            assertFalse(item.getStatement().matches(".*\\d{1,2}:\\d{2}.*"));
        }
    }

    @Test
    void teacherAcceptDoesNotRewriteOfficialIdentity() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.deductions.add(deduction("loss-innov", "创新成效", "4.0", List.of()));
        ChallengeSet set = ChallengeScanner.scan(input);
        BigDecimal official = new BigDecimal("48.30");
        ChallengeScanner.decorate(set, official);
        assertEquals(new BigDecimal("0.00"), set.getAcceptedAdjustment());
        assertEquals(official, set.getAdjustedDraftScore());

        ChallengeSet accepted = ChallengeScanner.applyTeacherDecision(
                set, set.getItems().get(0).getChallengeId(), "accept", "锚点确实没有", 7L);
        ChallengeScanner.decorate(accepted, official);
        assertEquals(ChallengeScanner.STATUS_ACCEPTED, accepted.getItems().get(0).getStatus());
        assertEquals(new BigDecimal("4.00"), accepted.getAcceptedAdjustment());
        assertEquals(new BigDecimal("52.30"), accepted.getAdjustedDraftScore());
        assertEquals("锚点确实没有", accepted.getItems().get(0).getTeacherReason());
        assertEquals(7L, accepted.getItems().get(0).getResolvedBy());
        assertNotNull(accepted.getItems().get(0).getResolvedAt());
        assertNull(accepted.getItems().get(0).getStartMs());
    }

    @Test
    void stalePendingScanCanBeRebuiltButAcceptedScanIsKept() {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.deductions.add(deduction("loss-innov", "创新成效", "4.0", List.of()));
        ChallengeSet stale = ChallengeScanner.scan(input);
        stale.setScanVersion("challenge-scan-v1");
        assertTrue(ChallengeScanner.needsRescan(stale));
        ChallengeSet accepted = ChallengeScanner.applyTeacherDecision(
                stale, stale.getItems().get(0).getChallengeId(), "accept", "keep", 7L);
        accepted.setScanVersion("challenge-scan-v1");
        assertFalse(ChallengeScanner.needsRescan(accepted));
        assertFalse(ChallengeScanner.needsRescan(ChallengeScanner.scan(input)));
    }

    @Test
    void unknownChallengeCannotBeResolved() {
        ChallengeSet set = ChallengeScanner.scan(new ChallengeScanner.Input());
        assertThrows(IllegalArgumentException.class,
                () -> ChallengeScanner.applyTeacherDecision(set, "missing", "reject", "no", 1L));
    }

    private static Challenge byType(ChallengeSet set, String type) {
        return set.getItems().stream().filter(item -> type.equals(item.getType())).findFirst().orElse(null);
    }

    private static ChallengeScanner.Deduction deduction(String lossId, String dimension, String points, List<Long> anchors) {
        ChallengeScanner.Deduction deduction = new ChallengeScanner.Deduction();
        deduction.lossId = lossId;
        deduction.targetDimension = dimension;
        deduction.deductedPoints = new BigDecimal(points);
        deduction.anchorIds = anchors;
        deduction.reason = dimension + "证据不足";
        return deduction;
    }

    private static ChallengeScanner.Observation observation(String lossId, String dimension, String score) {
        ChallengeScanner.Observation observation = new ChallengeScanner.Observation();
        observation.lossId = lossId;
        observation.targetDimension = dimension;
        observation.rawScore = new BigDecimal(score);
        return observation;
    }

    private static ChallengeScanner.Anchor anchor(Long id, Long startMs, Long endMs, String sourceRef, String text) {
        ChallengeScanner.Anchor anchor = new ChallengeScanner.Anchor();
        anchor.id = id;
        anchor.startMs = startMs;
        anchor.endMs = endMs;
        anchor.sourceRef = sourceRef;
        anchor.evidenceText = text;
        anchor.validityStatus = "valid";
        return anchor;
    }
}
