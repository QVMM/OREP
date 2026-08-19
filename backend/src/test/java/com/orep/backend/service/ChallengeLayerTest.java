package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.Challenge;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ChallengeLayerTest {

    @Test
    void completedReportScansTypeOneAndTeacherAcceptDoesNotChangeOfficial() {
        Fixture fixture = new Fixture();
        fixture.session.setStatus("completed");

        AiScoreReportUserResponse before = fixture.service.reportBySession(101L, "TEACHER");
        assertTrue(before.getChallenges().isScanned());
        assertEquals(DeliberationStageMachine.AWAIT_TEACHER, before.getDeliberation().getStage());
        assertEquals(1, before.getChallenges().getItems().size());
        Challenge first = before.getChallenges().getItems().get(0);
        assertEquals(ChallengeScanner.SCORE_WITHOUT_ANCHOR, first.getType());
        assertEquals("technology", first.getTargetDimension());
        assertFalse(first.isSeekable());
        BigDecimal official = before.getOverallScore();

        assertThrows(IllegalArgumentException.class,
                () -> fixture.service.resolveChallenge(101L, first.getChallengeId(), "accept", "无锚点", "STUDENT", 8L));

        AiScoreReportUserResponse accepted = fixture.service.resolveChallenge(
                101L, first.getChallengeId(), "accept", "无锚点，扣分站不住", "TEACHER", 7L);
        assertEquals(ChallengeScanner.STATUS_ACCEPTED, accepted.getChallenges().getItems().get(0).getStatus());
        assertEquals(official, accepted.getOverallScore());
        assertEquals(new BigDecimal("5.00"), accepted.getChallenges().getAcceptedAdjustment());
        assertEquals(new BigDecimal("42.60"), accepted.getChallenges().getAdjustedDraftScore());
        assertEquals("无锚点，扣分站不住", accepted.getChallenges().getItems().get(0).getTeacherReason());

        fixture.service.confirmDeliberation(101L, "TEACHER", 7L);
        assertThrows(IllegalArgumentException.class,
                () -> fixture.service.resolveChallenge(101L, first.getChallengeId(), "reject", "太晚", "TEACHER", 7L));
    }

    @Test
    void studentCannotSeeFinalBeforeTeacherEvenAfterScan() {
        Fixture fixture = new Fixture();
        AiScoreReportUserResponse student = fixture.service.reportBySession(101L, "STUDENT");
        assertFalse(student.getDeliberation().isFinalized());
        assertTrue(student.getTaskBook().getItems().isEmpty());
    }

    private static final class Fixture {
        private final AiScoringSession session;
        private final AiScoreReport report;
        private final AiScoringSessionService service;

        private Fixture() {
            AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
            AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
            AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
            AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
            AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

            session = new AiScoringSession();
            session.setId(101L);
            session.setSessionNo("SC-CH-101");
            session.setReportId(55L);
            session.setTrackName("新一代信息技术赛道");
            session.setSourceType("uploaded_video");
            session.setStatus("completed");
            session.setTeacherConfirmed(false);
            session.setChallengeCompleted(false);

            report = new AiScoreReport();
            report.setId(55L);
            report.setSessionId(101L);
            report.setOverallScore(new BigDecimal("37.6"));
            report.setContractVersion("ai-score-report-v3");
            report.setStatus("completed");
            report.setTaskBookPublished(false);

            when(sessionMapper.selectById(101L)).thenReturn(session);
            when(reportMapper.selectById(55L)).thenReturn(report);
            when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(report);
            when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of());
            when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of(deduction()));
            when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of());
            when(sessionMapper.updateById(any(AiScoringSession.class))).thenAnswer(invocation -> {
                AiScoringSession updated = invocation.getArgument(0);
                session.setTeacherConfirmed(updated.getTeacherConfirmed());
                session.setTeacherConfirmedAt(updated.getTeacherConfirmedAt());
                session.setTeacherConfirmedBy(updated.getTeacherConfirmedBy());
                session.setDeliberationStage(updated.getDeliberationStage());
                session.setChallengeCompleted(updated.getChallengeCompleted());
                session.setChallengeJson(updated.getChallengeJson());
                return 1;
            });
            when(reportMapper.updateById(any(AiScoreReport.class))).thenAnswer(invocation -> {
                AiScoreReport updated = invocation.getArgument(0);
                report.setTaskBookPublished(updated.getTaskBookPublished());
                report.setTaskBookJson(updated.getTaskBookJson());
                return 1;
            });

            service = new AiScoringSessionService(
                    sessionMapper,
                    reportMapper,
                    observationMapper,
                    deductionMapper,
                    anchorMapper,
                    mock(RubricResolverService.class),
                    mock(ScoringFingerprintService.class)
            );
        }
    }

    private static AiScoreDeduction deduction() {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setId(2L);
        deduction.setDeductionId("deduction-1");
        deduction.setObservationCode("obs-tech-demo");
        deduction.setDimensionCode("technology");
        deduction.setDeductedPoints(new BigDecimal("5"));
        deduction.setReason("仓库提交记录不足");
        deduction.setRequiredFix("补齐仓库提交记录");
        deduction.setAcceptanceCriteria("下场能打开仓库提交页");
        deduction.setMaxRecoverablePoints(new BigDecimal("5"));
        deduction.setStatus("new");
        return deduction;
    }
}
