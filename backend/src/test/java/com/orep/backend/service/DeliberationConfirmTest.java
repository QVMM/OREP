package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
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

class DeliberationConfirmTest {

    @Test
    void studentDoesNotSeePublishedTodosUntilTeacherConfirms() {
        Fixture fixture = new Fixture();
        fixture.session.setStatus("completed");
        fixture.report.setTaskBookPublished(true);

        AiScoreReportUserResponse student = fixture.service.reportBySession(101L, "STUDENT");
        assertEquals(DeliberationStageMachine.AWAIT_TEACHER, student.getDeliberation().getStage());
        assertFalse(student.getDeliberation().isFinalized());
        assertFalse(student.getDeliberation().isChallengeIncomplete());
        assertTrue(student.getTaskBook().getItems().isEmpty());
        assertFalse(student.getTaskBook().isPublished());
        assertEquals(1, student.getChallenges().getItems().size());
        assertEquals(ChallengeScanner.SCORE_WITHOUT_ANCHOR, student.getChallenges().getItems().get(0).getType());

        assertThrows(IllegalArgumentException.class, () -> fixture.service.confirmDeliberation(101L, "STUDENT", 10L));

        AiScoreReportUserResponse teacher = fixture.service.confirmDeliberation(101L, "TEACHER", 7L);
        assertEquals(DeliberationStageMachine.FROZEN, teacher.getDeliberation().getStage());
        assertTrue(teacher.getDeliberation().isFinalized());
        assertTrue(Boolean.TRUE.equals(fixture.session.getTeacherConfirmed()));

        AiScoreReportUserResponse after = fixture.service.reportBySession(101L, "STUDENT");
        assertTrue(after.getDeliberation().isFinalized());
        assertFalse(after.getTaskBook().getItems().isEmpty());
        assertTrue(after.getTaskBook().isPublished());
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
            session.setSessionNo("SC-DELI-101");
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
