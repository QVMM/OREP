package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class MeetingReportByMeetingTest {

    @Test
    void meetingLookupUsesLatestCompletedWhenSessionHasNoReportId() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        AiScoringSession session = new AiScoringSession();
        session.setId(200L);
        session.setMeetingId(9L);
        session.setStatus("scoring");
        when(sessionMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(session);

        AiScoreReport older = report(11L, "completed", LocalDateTime.parse("2026-08-17T10:00:00"), new BigDecimal("40.9"));
        AiScoreReport latest = report(22L, "completed", LocalDateTime.parse("2026-08-17T12:00:00"), new BigDecimal("48.3"));
        AiScoreReport processing = report(23L, "processing", LocalDateTime.parse("2026-08-17T13:00:00"), null);
        when(reportMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(older, processing, latest));
        when(reportMapper.selectById(22L)).thenReturn(latest);
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(latest);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class)
        );

        AiScoreReportUserResponse response = service.reportByMeetingId(9L, "TEACHER");
        assertEquals(new BigDecimal("48.3"), response.getOverallScore());
        assertEquals(22L, response.getReportId());
    }

    private static AiScoreReport report(Long id, String status, LocalDateTime completedAt, BigDecimal score) {
        AiScoreReport report = new AiScoreReport();
        report.setId(id);
        report.setMeetingId(9L);
        report.setStatus(status);
        report.setCompletedAt(completedAt);
        report.setOverallScore(score);
        report.setContractVersion("ai-score-report-v3");
        return report;
    }
}
