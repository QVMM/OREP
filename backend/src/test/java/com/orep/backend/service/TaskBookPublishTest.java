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

class TaskBookPublishTest {

    @Test
    void studentSeesEmptyTaskBookUntilTeacherPublishes() {
        Fixture fixture = fixture();

        AiScoreReportUserResponse draft = fixture.service.reportBySession(101L, "STUDENT");
        assertFalse(draft.getTaskBook().isPublished());
        assertTrue(draft.getTaskBook().getItems().isEmpty());
        assertTrue(TaskBookBuilder.studentVisibleItems(draft.getTaskBook()).isEmpty());
        assertFalse(fixture.service.reportBySession(101L, "TEACHER").getTaskBook().getItems().isEmpty());

        assertThrows(IllegalArgumentException.class, () -> fixture.service.publishTaskBook(101L, "STUDENT"));

        AiScoreReportUserResponse published = fixture.service.publishTaskBook(101L, "TEACHER");
        assertTrue(published.getTaskBook().isPublished());
        assertFalse(published.getTaskBook().getItems().isEmpty());
        assertTrue(Boolean.TRUE.equals(fixture.report.getTaskBookPublished()));
        assertNotNull(fixture.report.getTaskBookJson());
        assertTrue(fixture.report.getTaskBookJson().contains("补齐"));

        AiScoreReportUserResponse studentBeforeConfirm = fixture.service.reportBySession(101L, "STUDENT");
        assertFalse(studentBeforeConfirm.getTaskBook().isPublished());
        assertTrue(studentBeforeConfirm.getTaskBook().getItems().isEmpty());

        fixture.session.setStatus("completed");
        fixture.service.confirmDeliberation(101L, "TEACHER", 7L);
        AiScoreReportUserResponse student = fixture.service.reportBySession(101L, "STUDENT");
        assertTrue(student.getTaskBook().isPublished());
        assertEquals(published.getTaskBook().getItems().size(), student.getTaskBook().getItems().size());
        assertFalse(student.getTaskBook().getItems().isEmpty());
        assertTrue(student.getTaskBook().getItems().getFirst().getExpectedGain().contains("下场对照，不保证"));
    }

    @Test
    void rejectsPublishWhenNoValidItems() {
        Fixture fixture = emptyFixture();
        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> fixture.service.publishTaskBook(101L, "TEACHER")
        );
        assertEquals("没有可发布的任务书", error.getMessage());
        assertFalse(Boolean.TRUE.equals(fixture.report.getTaskBookPublished()));
    }

    private static Fixture fixture() {
        return new Fixture(true);
    }

    private static Fixture emptyFixture() {
        return new Fixture(false);
    }

    private static final class Fixture {
        private final AiScoringSession session;
        private final AiScoreReport report;
        private final AiScoringSessionService service;

        private Fixture(boolean withDeduction) {
            AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
            AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
            AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
            AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
            AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

            session = new AiScoringSession();
            session.setId(101L);
            session.setSessionNo("SC-TASKBOOK-101");
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
            when(deductionMapper.selectList(any(LambdaQueryWrapper.class)))
                    .thenReturn(withDeduction ? java.util.List.of(deduction()) : java.util.List.of());
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
                report.setUpdatedAt(updated.getUpdatedAt());
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
        deduction.setRecoveredPoints(BigDecimal.ZERO);
        deduction.setReason("仓库提交记录不足");
        deduction.setRequiredFix("补齐仓库提交记录");
        deduction.setAcceptanceCriteria("下场能打开仓库提交页");
        deduction.setMaxRecoverablePoints(new BigDecimal("5"));
        deduction.setEvidenceLevel("medium");
        deduction.setConfidence(new BigDecimal("0.80"));
        deduction.setStatus("new");
        return deduction;
    }
}
