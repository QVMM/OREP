package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreReportSessionNativeHardeningTest {

    @Test
    void uploadedVideoReportBySessionDoesNotRequireMeetingId() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

        AiScoringSession session = new AiScoringSession();
        session.setId(88L);
        session.setReportId(55L);
        session.setMeetingId(null);
        session.setSessionNo("SC-20260624-000088");
        session.setTrackName("医学技术赛道");
        session.setSourceType("uploaded_video");
        when(sessionMapper.selectById(88L)).thenReturn(session);

        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setSessionId(88L);
        report.setMeetingId(null);
        report.setOverallScore(new BigDecimal("78.50"));
        report.setStatus("completed");
        when(reportMapper.selectById(55L)).thenReturn(report);
        when(observationMapper.selectList(any())).thenReturn(List.of());
        when(deductionMapper.selectList(any())).thenReturn(List.of());
        when(anchorMapper.selectList(any())).thenReturn(List.of());

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.reportBySession(88L);

        assertThat(response.getSessionId()).isEqualTo(88L);
        assertThat(response.getMeetingId()).isNull();
        assertThat(response.getSourceType()).isEqualTo("uploaded_video");
        assertThat(response.getScoringConsistencyNo()).isEqualTo("SC-20260624-000088");
    }

    @Test
    void structuredDeductionsKeepDistinctEvidenceAnchors() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

        AiScoringSession session = new AiScoringSession();
        session.setId(88L);
        session.setReportId(55L);
        session.setSessionNo("SC-20260624-000088");
        when(sessionMapper.selectById(88L)).thenReturn(session);

        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setMeetingId(-88L);
        report.setOverallScore(new BigDecimal("78.50"));
        report.setStatus("completed");
        when(reportMapper.selectById(55L)).thenReturn(report);
        when(observationMapper.selectList(any())).thenReturn(List.of());

        AiScoreDeduction first = deduction("D1", "技术演示中断", "A1");
        AiScoreDeduction second = deduction("D2", "商业证据不足", "A2");
        when(deductionMapper.selectList(any())).thenReturn(List.of(first, second));
        when(anchorMapper.selectList(any())).thenReturn(List.of(
                anchor("A1", 2000L, 5000L, "演示页面报错后切换到截图"),
                anchor("A2", 20000L, 26000L, "只口头说明客户，没有订单或访谈截图")
        ));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.reportBySession(88L);

        assertThat(response.getEvidenceAnchors()).hasSize(2);
        assertThat(response.getEvidenceAnchors()).extracting("sourceRef")
                .containsExactly("A1", "A2");
        assertThat(response.getEvidenceAnchors()).extracting("evidenceText")
                .doesNotContain("大家好。");
    }

    private AiScoreDeduction deduction(String id, String reason, String evidenceRef) {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setDeductionId(id);
        deduction.setDimensionCode("综合");
        deduction.setReason(reason);
        deduction.setEvidenceAnchorIdsJson("[\"" + evidenceRef + "\"]");
        deduction.setDeductedPoints(new BigDecimal("3.00"));
        deduction.setMaxRecoverablePoints(new BigDecimal("3.00"));
        return deduction;
    }

    private AiScoreEvidenceAnchor anchor(String sourceRef, Long startMs, Long endMs, String text) {
        AiScoreEvidenceAnchor anchor = new AiScoreEvidenceAnchor();
        anchor.setSourceRef(sourceRef);
        anchor.setAnchorType("transcript");
        anchor.setStartMs(startMs);
        anchor.setEndMs(endMs);
        anchor.setEvidenceText(text);
        anchor.setConfidence(new BigDecimal("0.80"));
        return anchor;
    }
}
