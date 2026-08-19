package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoringSessionDocketRunTest {

    @Test
    void completedCallbackWithoutDocketIdFailsAndDoesNotRecordRun() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoringSession session = scoringSession(82L, 37L, null);
        when(sessionMapper.selectById(82L)).thenReturn(session);
        AiScoreReport existingReport = existingReport(37L, 82L);
        when(reportMapper.selectById(37L)).thenReturn(existingReport);

        AiScoringSessionService service = sessionService(sessionMapper, reportMapper, docketService);
        service.processPipelineCallback(completedCallback(82L, new BigDecimal("53.40")));

        assertEquals("failed", session.getStatus());
        assertEquals("calculation_failed", session.getCurrentStage());
        assertTrue(session.getErrorMessage().contains("docketId"));
        assertNotEquals("completed", session.getStatus());
        verify(docketService, never()).recordSuccessfulRun(any(), any());
        verify(docketService, never()).recordSuccessfulRun(any(), any(), any());
        verify(reportMapper).updateById(existingReport);
        verify(sessionMapper).updateById(session);
    }

    @Test
    void completedCallbackWithoutDocketServiceFailsAndDoesNotComplete() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoringSession session = scoringSession(82L, 37L, "ab".repeat(32));
        when(sessionMapper.selectById(82L)).thenReturn(session);
        when(reportMapper.selectById(37L)).thenReturn(existingReport(37L, 82L));

        AiScoringSessionService service = sessionService(sessionMapper, reportMapper, null);
        service.processPipelineCallback(completedCallback(82L, new BigDecimal("53.40")));

        assertEquals("failed", session.getStatus());
        assertEquals("calculation_failed", session.getCurrentStage());
        assertTrue(session.getErrorMessage().contains("docketService"));
        assertNotEquals("completed", session.getStatus());
    }

    @Test
    void completedCallbackWithDocketIdRecordsSuccessfulRunOnce() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoringSession session = scoringSession(82L, 37L, "ab".repeat(32));
        when(sessionMapper.selectById(82L)).thenReturn(session);
        AiScoreReport existingReport = existingReport(37L, 82L);
        when(reportMapper.selectById(37L)).thenReturn(existingReport);

        AiScoringSessionService service = sessionService(sessionMapper, reportMapper, docketService);
        service.processPipelineCallback(completedCallback(82L, new BigDecimal("53.40")));

        assertEquals("completed", session.getStatus());
        assertEquals("completed", session.getCurrentStage());
        verify(docketService, times(1)).recordSuccessfulRun(eq(session), eq(existingReport), any());
        verify(reportMapper).updateById(existingReport);
    }

    @Test
    void failedCallbackDoesNotRecordCompletedRun() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoringSession session = scoringSession(82L, 37L, "ab".repeat(32));
        when(sessionMapper.selectById(82L)).thenReturn(session);

        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(82L);
        callback.setStatus("failed");
        callback.setErrorMessage("pipeline boom");

        AiScoringSessionService service = sessionService(sessionMapper, reportMapper, docketService);
        service.processPipelineCallback(callback);

        assertEquals("failed", session.getStatus());
        verify(docketService, never()).recordSuccessfulRun(any(), any());
        verify(docketService, never()).recordSuccessfulRun(any(), any(), any());
        verify(reportMapper, never()).insert(any());
        verify(reportMapper, never()).updateById(any());
    }

    private static AiScoringSessionService sessionService(AiScoringSessionMapper sessionMapper,
                                                          AiScoreReportMapper reportMapper,
                                                          AiScoreDocketService docketService) {
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );
        service.setDocketService(docketService);
        return service;
    }

    private static AiScoringSession scoringSession(Long sessionId, Long reportId, String docketId) {
        AiScoringSession session = new AiScoringSession();
        session.setId(sessionId);
        session.setReportId(reportId);
        session.setDocketId(docketId);
        session.setStatus("scoring");
        return session;
    }

    private static AiScoreReport existingReport(Long reportId, Long sessionId) {
        AiScoreReport report = new AiScoreReport();
        report.setId(reportId);
        report.setSessionId(sessionId);
        report.setOverallScore(new BigDecimal("0.00"));
        return report;
    }

    private static PipelineCallbackRequest completedCallback(Long sessionId, BigDecimal overallScore) {
        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("diagnostic_llm");
        result.setOverallScore(overallScore);
        result.setModel("DeepSeek V3");
        result.setActionPlanJson("[{\"id\":\"action-1\",\"title\":\"加固AI演示\"}]");
        result.setLossLedgerJson("[{\"lossId\":\"loss-1\",\"points\":46.6}]");
        result.setCoverageSummaryJson("{\"coverageRate\":1.0,\"status\":\"complete\"}");
        result.setScoreProjectionJson("{\"goalScore\":100,\"predictedScoreLower\":61.0,\"predictedScoreUpper\":67.5}");
        result.setContractVersion("ai-score-report-v3");
        result.setTodoPortfolioStatus("complete");

        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(sessionId);
        callback.setStatus("completed");
        callback.setFinalResult(result);
        return callback;
    }
}
