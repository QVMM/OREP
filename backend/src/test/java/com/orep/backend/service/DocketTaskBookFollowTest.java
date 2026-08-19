package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.DocketStability;
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
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DocketTaskBookFollowTest {

    @Test
    void laterRunReadsPublishedBookWithoutRewritingOfficialScore() {
        Fixture fixture = new Fixture();

        AiScoreReportUserResponse published = fixture.service.publishTaskBook(101L, "TEACHER");
        assertTrue(published.getTaskBook().isPublished());
        assertEquals(0, new BigDecimal("37.60").compareTo(published.getOverallScore()));
        assertEquals(0, new BigDecimal("48.30").compareTo(fixture.laterReport.getOverallScore()));

        AiScoreReportUserResponse laterTeacher = fixture.service.reportBySession(102L, "TEACHER");
        assertTrue(laterTeacher.getTaskBook().isPublished());
        assertFalse(laterTeacher.getTaskBook().getItems().isEmpty());
        assertEquals(0, new BigDecimal("48.30").compareTo(laterTeacher.getOverallScore()));
        assertFalse(Boolean.TRUE.equals(fixture.laterReport.getTaskBookPublished()));

        AiScoreReportUserResponse laterStudent = fixture.service.reportBySession(102L, "STUDENT");
        assertFalse(laterStudent.getTaskBook().isPublished());
        assertTrue(laterStudent.getTaskBook().getItems().isEmpty());
    }

    private static final class Fixture {
        private final AiScoreReport laterReport;
        private final AiScoringSessionService service;

        private Fixture() {
            AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
            AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
            AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
            AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
            AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
            AiScoreDocketService docketService = mock(AiScoreDocketService.class);

            AiScoringSession first = session(101L, 55L);
            AiScoringSession later = session(102L, 56L);
            AiScoreReport firstReport = report(55L, 101L, new BigDecimal("37.60"));
            laterReport = report(56L, 102L, new BigDecimal("48.30"));

            when(sessionMapper.selectById(101L)).thenReturn(first);
            when(sessionMapper.selectById(102L)).thenReturn(later);
            when(reportMapper.selectById(55L)).thenReturn(firstReport);
            when(reportMapper.selectById(56L)).thenReturn(laterReport);
            when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
            when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of());
            when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of(deduction()));
            when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(java.util.List.of());
            when(sessionMapper.updateById(any(AiScoringSession.class))).thenReturn(1);
            when(reportMapper.updateById(any(AiScoreReport.class))).thenAnswer(invocation -> {
                AiScoreReport updated = invocation.getArgument(0);
                if (updated.getId() != null && updated.getId().equals(55L)) {
                    firstReport.setTaskBookPublished(updated.getTaskBookPublished());
                    firstReport.setTaskBookJson(updated.getTaskBookJson());
                }
                return 1;
            });

            Map<String, String> docketJson = new HashMap<>();
            doAnswer(invocation -> {
                docketJson.put(invocation.getArgument(0), invocation.getArgument(2));
                return null;
            }).when(docketService).persistPublishedTaskBook(anyString(), any(), anyString());
            when(docketService.loadPublishedTaskBook(anyString())).thenAnswer(invocation -> {
                String json = docketJson.get(invocation.getArgument(0));
                return json == null
                        ? DocketTaskBook.Snapshot.unpublished()
                        : new DocketTaskBook.Snapshot(true, json);
            });
            DocketStability stability = new DocketStability();
            stability.setBand("not_reviewed");
            stability.setRunCount(0);
            when(docketService.stabilitySnapshot(anyString())).thenReturn(stability);
            when(docketService.previousCompletedRun(anyString(), any())).thenReturn(null);

            service = new AiScoringSessionService(
                    sessionMapper,
                    reportMapper,
                    observationMapper,
                    deductionMapper,
                    anchorMapper,
                    mock(RubricResolverService.class),
                    mock(ScoringFingerprintService.class)
            );
            service.setDocketService(docketService);
        }

        private static AiScoringSession session(Long id, Long reportId) {
            AiScoringSession session = new AiScoringSession();
            session.setId(id);
            session.setSessionNo("SC-DOCKET-" + id);
            session.setReportId(reportId);
            session.setDocketId("docket-a");
            session.setTrackName("新一代信息技术赛道");
            session.setSourceType("uploaded_video");
            session.setStatus("completed");
            session.setTeacherConfirmed(false);
            session.setChallengeCompleted(false);
            return session;
        }

        private static AiScoreReport report(Long id, Long sessionId, BigDecimal score) {
            AiScoreReport report = new AiScoreReport();
            report.setId(id);
            report.setSessionId(sessionId);
            report.setOverallScore(score);
            report.setContractVersion("ai-score-report-v3");
            report.setStatus("completed");
            report.setTaskBookPublished(false);
            return report;
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
}
