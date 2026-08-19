package com.orep.backend.service;

import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.math.BigDecimal;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AiScoringSessionServiceTest {

    @Test
    void completedSessionIgnoresLateProgressCallback() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(83L);
        session.setStatus("completed");
        session.setCurrentStage("completed");
        session.setProgressPercent(100);
        when(sessionMapper.selectById(83L)).thenReturn(session);

        serviceWith(sessionMapper).processPipelineCallback(progressCallback(83L, "report_generating", 95));

        assertEquals("completed", session.getStatus());
        assertEquals("completed", session.getCurrentStage());
        assertEquals(100, session.getProgressPercent());
        verify(sessionMapper, never()).updateById(any());
    }

    @Test
    void failedSessionIgnoresLateProgressCallback() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(84L);
        session.setStatus("failed");
        session.setCurrentStage("result_writeback_failed");
        session.setProgressPercent(95);
        when(sessionMapper.selectById(84L)).thenReturn(session);

        serviceWith(sessionMapper).processPipelineCallback(progressCallback(84L, "report_generating", 95));

        assertEquals("failed", session.getStatus());
        assertEquals("result_writeback_failed", session.getCurrentStage());
        verify(sessionMapper, never()).updateById(any());
    }

    @Test
    void progressPercentNeverMovesBackward() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(85L);
        session.setStatus("scoring");
        session.setCurrentStage("model_scoring");
        session.setProgressPercent(80);
        when(sessionMapper.selectById(85L)).thenReturn(session);

        serviceWith(sessionMapper).processPipelineCallback(progressCallback(85L, "speakers", 70));

        assertEquals(80, session.getProgressPercent());
        verify(sessionMapper).updateById(session);
    }

    @Test
    void authoritativeScoreMismatchMarksCalculationFailedWithoutPublishingReport() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(81L);
        session.setStatus("scoring");
        when(sessionMapper.selectById(81L)).thenReturn(session);

        PipelineCallbackRequest.ObservationInput observation = new PipelineCallbackRequest.ObservationInput();
        observation.setObservationCode("O1");
        observation.setDimensionCode("D1");
        observation.setMaxScore(new BigDecimal("20"));
        observation.setBaseScore(new BigDecimal("16"));
        observation.setScoreCap(new BigDecimal("14"));

        PipelineCallbackRequest.DeductionInput deduction = new PipelineCallbackRequest.DeductionInput();
        deduction.setDeductionId("O1:missing-proof");
        deduction.setObservationCode("O1");
        deduction.setDimensionCode("D1");
        deduction.setDeductedPoints(new BigDecimal("3"));
        deduction.setStatus("new");

        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("structured_rule_engine");
        result.setOverallScore(new BigDecimal("15"));
        result.setObservations(List.of(observation));
        result.setDeductions(List.of(deduction));

        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(81L);
        callback.setStatus("completed");
        callback.setFinalResult(result);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        service.processPipelineCallback(callback);

        assertEquals("failed", session.getStatus());
        assertEquals("calculation_failed", session.getCurrentStage());
        assertTrue(session.getErrorMessage().contains("does not match Java recomputed score 13.00"));
        verify(sessionMapper).updateById(session);
        verify(reportMapper, never()).insert(any());
    }

    @Test
    void completedCallbackUpdatesExistingSessionReportAndReplacesStructuredRows() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper evidenceAnchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreRemediationService remediationService = mock(AiScoreRemediationService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(82L);
        session.setReportId(37L);
        session.setDocketId("ab".repeat(32));
        session.setStatus("completed");
        when(sessionMapper.selectById(82L)).thenReturn(session);
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(37L);
        existingReport.setSessionId(82L);
        existingReport.setOverallScore(new BigDecimal("0.00"));
        when(reportMapper.selectById(37L)).thenReturn(existingReport);

        PipelineCallbackRequest.PipelineFinalResult result = new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("diagnostic_llm");
        result.setOverallScore(new BigDecimal("53.40"));
        result.setModel("DeepSeek V3");
        result.setActionPlanJson("[{\"id\":\"action-1\",\"title\":\"加固AI演示\"}]");
        result.setLossLedgerJson("[{\"lossId\":\"loss-1\",\"points\":46.6}]");
        result.setCoverageSummaryJson("{\"coverageRate\":1.0,\"status\":\"complete\"}");
        result.setScoreProjectionJson("{\"goalScore\":100,\"predictedScoreLower\":61.0,\"predictedScoreUpper\":67.5}");
        result.setContractVersion("ai-score-report-v3");
        result.setTodoPortfolioStatus("complete");

        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(82L);
        callback.setStatus("completed");
        callback.setFinalResult(result);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                evidenceAnchorMapper,
                mock(RubricResolverService.class),
                new ScoringFingerprintService(),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null,
                remediationService
        );
        service.setDocketService(mock(AiScoreDocketService.class));

        service.processPipelineCallback(callback);

        assertEquals(37L, session.getReportId());
        assertEquals("completed", session.getStatus());
        assertEquals(new BigDecimal("53.40"), existingReport.getOverallScore());
        assertEquals(result.getActionPlanJson(), existingReport.getActionPlanJson());
        assertEquals(result.getLossLedgerJson(), existingReport.getLossLedgerJson());
        assertEquals(result.getCoverageSummaryJson(), existingReport.getCoverageSummaryJson());
        assertEquals(result.getScoreProjectionJson(), existingReport.getScoreProjectionJson());
        assertEquals(result.getContractVersion(), existingReport.getContractVersion());
        assertEquals(result.getTodoPortfolioStatus(), existingReport.getTodoPortfolioStatus());
        verify(reportMapper).updateById(existingReport);
        verify(reportMapper, never()).insert(any());
        verify(observationMapper).delete(any());
        verify(deductionMapper).delete(any());
        verify(evidenceAnchorMapper).delete(any());
        verify(remediationService).persistSnapshot(
                "session:82",
                37L,
                82L,
                result.getActionPlanJson(),
                result.getLossLedgerJson(),
                result.getCoverageSummaryJson()
        );
    }

    @Test
    void completedCallbackPersistsFinalSpeakerEvidenceAfterTranscriptReplacement() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreTranscriptService transcriptService = mock(AiScoreTranscriptService.class);
        AiScoreSpeakerIdentityService speakerIdentityService = mock(AiScoreSpeakerIdentityService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(86L);
        session.setReportId(38L);
        session.setDocketId("ab".repeat(32));
        session.setStatus("scoring");
        AiScoringSession refreshedSession = new AiScoringSession();
        refreshedSession.setId(86L);
        refreshedSession.setReportId(38L);
        refreshedSession.setDocketId("ab".repeat(32));
        refreshedSession.setStatus("scoring");
        refreshedSession.setSpeakerAttributionRevision(2);
        refreshedSession.setSpeakerAttributionStatus("FINAL");
        refreshedSession.setSpeakerAttributionContractVersion("speaker-attribution-v1");
        refreshedSession.setSpeakerAttributionSnapshotHash("sha256:revision-2");
        when(sessionMapper.selectById(86L)).thenReturn(session, refreshedSession);
        AiScoreReport report = new AiScoreReport();
        report.setId(38L);
        report.setSessionId(86L);
        when(reportMapper.selectById(38L)).thenReturn(report);

        PipelineCallbackRequest.SpeakerEvidenceInput evidence =
                new PipelineCallbackRequest.SpeakerEvidenceInput();
        evidence.setRawSpeakerId("SPEAKER_0");
        evidence.setDisplayName("1号发言人");
        evidence.setStatus("AUTO");
        evidence.setSource("final_asr");
        PipelineCallbackRequest.PipelineFinalResult result =
                new PipelineCallbackRequest.PipelineFinalResult();
        result.setScoreAuthority("diagnostic_llm");
        result.setOverallScore(new BigDecimal("49.50"));
        result.setAsrSegments(List.of());
        result.setSpeakerEvidence(List.of(evidence));
        PipelineCallbackRequest.SpeakerAttributionInput attribution =
                new PipelineCallbackRequest.SpeakerAttributionInput();
        attribution.setContractVersion("speaker-attribution-v1");
        attribution.setRevision(1);
        attribution.setStatus("FINAL");
        result.setSpeakerAttribution(attribution);
        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(86L);
        callback.setStatus("completed");
        callback.setFinalResult(result);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService(),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null,
                null,
                null,
                transcriptService,
                speakerIdentityService
        );
        service.setDocketService(mock(AiScoreDocketService.class));

        service.processPipelineCallback(callback);

        var inOrder = inOrder(transcriptService, speakerIdentityService);
        inOrder.verify(transcriptService).replaceFromCallback(86L, List.of());
        inOrder.verify(speakerIdentityService).upsertAutoEvidence(86L, List.of(evidence));
        inOrder.verify(speakerIdentityService).persistAttribution(86L, attribution);
        verify(sessionMapper).updateById(refreshedSession);
        assertEquals(2, refreshedSession.getSpeakerAttributionRevision());
        assertEquals("FINAL", refreshedSession.getSpeakerAttributionStatus());
    }

    @Test
    void createsMeetingScoringSessionWithoutLeakingRubricInternals() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(101L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
        request.setSourceType("meeting_recording");
        request.setMeetingId(12L);
        request.setProjectId(3L);
        request.setTeamId(9L);
        request.setTrackId("track-it");
        request.setTrackName("新一代信息技术赛道");
        request.setUseHistoryMemory(true);
        request.setJuryEnabled(true);

        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        assertEquals(101L, response.getSessionId());
        assertEquals("created", response.getStatus());
        assertEquals("新一代信息技术赛道", response.getTrackName());
        assertNull(response.getRubricHash());
        assertNull(response.getRubricPath());
        assertNull(response.getInternalVersion());
        verify(sessionMapper).insert(sessionCaptor.capture());
        AiScoringSession inserted = sessionCaptor.getValue();
        assertEquals("track-it", inserted.getTrackId());
        assertEquals("新一代信息技术赛道", inserted.getTrackName());
        assertEquals("rubric-it-v1", inserted.getRubricId());
        assertEquals("v1.2-internal", inserted.getRubricInternalVersion());
        assertEquals("secret-hash", inserted.getRubricHash());
        assertEquals(33L, inserted.getEvidenceSchemaId());
        assertEquals("schema-v1", inserted.getEvidenceSchemaVersion());
        assertEquals(false, inserted.getJuryEnabled());
        assertEquals(false, response.getJuryEnabled());
        verify(rubricResolverService).resolve("track-it", "新一代信息技术赛道");
    }

    @Test
    void createSessionFailsWhenRubricResolverFails() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("missing-track", null))
                .thenThrow(new IllegalStateException("未找到有效评分规则或证据Schema"));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
        request.setTrackId("missing-track");

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> service.createSession(request, 7L));

        assertEquals("未找到有效评分规则或证据Schema", error.getMessage());
        verify(sessionMapper, never()).insert(any(AiScoringSession.class));
    }

    @Test
    void meetingRecordingCreatesNewSessionByDefaultEvenWhenFingerprintMatches() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        when(sessionMapper.selectOne(any())).thenReturn(cachedCompletedSession(202L));
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(404L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = createRequest("meeting_recording");
        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        assertEquals(404L, response.getSessionId());
        assertFalse(response.getCached());
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper).insert(any(AiScoringSession.class));
    }

    @Test
    void reuseCompletedStillReturnsCacheForMeetingRecording() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        AiScoringSession cached = cachedCompletedSession(202L);
        when(sessionMapper.selectOne(any())).thenReturn(cached);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = createRequest("meeting_recording");
        request.setReuseCompleted(true);
        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        assertEquals(202L, response.getSessionId());
        assertTrue(response.getCached());
        assertEquals("检测到与历史评分输入完全一致，已返回同一份评分结果。", response.getMessage());
        verify(sessionMapper, never()).insert(any(AiScoringSession.class));
    }

    @Test
    void uploadedVideoSkipsCompletedCacheAndCreatesNewSession() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        when(sessionMapper.selectOne(any())).thenReturn(cachedCompletedSession(202L));
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(303L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = createRequest("uploaded_video");
        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        assertEquals(303L, response.getSessionId());
        assertFalse(response.getCached());
        assertNull(response.getMessage());
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper).insert(sessionCaptor.capture());
        assertEquals("uploaded_video", sessionCaptor.getValue().getSourceType());
    }

    @Test
    void normalizedUploadedVideoSkipsCompletedCacheAndPersistsCanonicalSourceType() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        when(sessionMapper.selectOne(any())).thenReturn(cachedCompletedSession(202L));
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(404L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = createRequest(" Uploaded_Video ");
        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        assertEquals(404L, response.getSessionId());
        assertFalse(response.getCached());
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper).insert(sessionCaptor.capture());
        assertEquals("uploaded_video", sessionCaptor.getValue().getSourceType());
    }

    @Test
    void uploadedVideoAliasesSkipCompletedCacheAndPersistCanonicalSourceType() {
        for (String sourceType : new String[]{"uploadedVideo", "uploaded-video", "uploaded video"}) {
            AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
            AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
            RubricResolverService rubricResolverService = mock(RubricResolverService.class);
            when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
            when(sessionMapper.selectOne(any())).thenReturn(cachedCompletedSession(202L));
            doAnswer(invocation -> {
                AiScoringSession session = invocation.getArgument(0);
                session.setId(405L);
                return 1;
            }).when(sessionMapper).insert(any(AiScoringSession.class));

            AiScoringSessionService service = new AiScoringSessionService(
                    sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

            AiScoringSessionCreateRequest request = createRequest(sourceType);
            AiScoringSessionUserResponse response = service.createSession(request, 7L);

            ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
            assertEquals(405L, response.getSessionId());
            assertFalse(response.getCached());
            verify(sessionMapper, never()).selectOne(any());
            verify(sessionMapper).insert(sessionCaptor.capture());
            assertEquals("uploaded_video", sessionCaptor.getValue().getSourceType());
        }
    }

    @Test
    void rejectsUnsupportedSourceType() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionCreateRequest request = createRequest("unknown_source");

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
                () -> service.createSession(request, 7L));
        assertEquals("评分来源类型不支持", error.getMessage());
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper, never()).insert(any());
    }

    @Test
    void statusFlowCanStartCancelAndRestart() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        AiScoringSession stored = new AiScoringSession();
        stored.setId(5L);
        stored.setSessionNo("SC-20260623-000005");
        stored.setStatus("created");
        stored.setTrackId("track-it");
        stored.setTrackName("新一代信息技术赛道");
        stored.setSourceType("meeting_recording");
        stored.setUseHistoryMemory(true);
        stored.setJuryEnabled(false);
        when(sessionMapper.selectById(5L)).thenReturn(stored);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        stored.setDocketId("ab".repeat(32));
        assertEquals("scoring", service.start(5L).getStatus());
        assertEquals("cancelled", service.cancel(5L).getStatus());
        AiScoringSessionUserResponse restarted = service.restart(5L);
        assertEquals("created", restarted.getStatus());
        assertEquals("ab".repeat(32), restarted.getDocketId());
        verify(sessionMapper, times(3)).updateById(stored);
        verify(sessionMapper, never()).insert(any(AiScoringSession.class));
    }

    @Test
    void restartCompletedSessionOpensNewSessionAndKeepsDocket() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        AiScoringSession stored = cachedCompletedSession(5L);
        stored.setDocketId("cd".repeat(32));
        stored.setMeetingId(12L);
        stored.setScoringFingerprint("fp-1");
        when(sessionMapper.selectById(5L)).thenReturn(stored);
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(6L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionUserResponse response = service.restart(5L);

        assertEquals(6L, response.getSessionId());
        assertEquals("created", response.getStatus());
        assertEquals("cd".repeat(32), response.getDocketId());
        assertEquals("completed", stored.getStatus());
        verify(sessionMapper, never()).updateById(stored);
        ArgumentCaptor<AiScoringSession> captor = ArgumentCaptor.forClass(AiScoringSession.class);
        verify(sessionMapper).insert(captor.capture());
        assertEquals(12L, captor.getValue().getMeetingId());
        assertEquals("fp-1", captor.getValue().getScoringFingerprint());
        assertEquals("cd".repeat(32), captor.getValue().getDocketId());
    }

    @Test
    void createMeetingSessionRegistersRecordingAsset() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        AiScoreMediaAssetService mediaAssetService = mock(AiScoreMediaAssetService.class);
        when(rubricResolverService.resolve("track-it", "新一代信息技术赛道")).thenReturn(resolvedRubric());
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(808L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                null,
                null,
                null,
                rubricResolverService,
                new ScoringFingerprintService(),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null,
                null,
                mediaAssetService
        );

        AiScoringSessionCreateRequest request = createRequest("meeting_recording");
        request.setRecordingId(11L);
        AiScoringSessionUserResponse response = service.createSession(request, 7L);

        assertEquals(808L, response.getSessionId());
        verify(mediaAssetService).registerMeetingRecordingForSession(808L, 11L, 12L, 7L);
    }

    @Test
    void markFailedKeepsUploadCompatibilityAndAllowsEvidenceStage() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        RubricResolverService rubricResolverService = mock(RubricResolverService.class);
        AiScoringSession stored = new AiScoringSession();
        stored.setId(5L);
        stored.setSessionNo("SC-20260623-000005");
        stored.setTrackName("新一代信息技术赛道");
        stored.setSourceType("meeting_recording");
        stored.setUseHistoryMemory(true);
        stored.setJuryEnabled(false);
        when(sessionMapper.selectById(5L)).thenReturn(stored);

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper, reportMapper, rubricResolverService, new ScoringFingerprintService());

        AiScoringSessionUserResponse uploadFailure = service.markFailed(5L, "上传失败");
        assertEquals("failed", uploadFailure.getStatus());
        assertEquals("upload_failed", uploadFailure.getCurrentStage());

        AiScoringSessionUserResponse evidenceFailure = service.markFailed(5L, "证据失败", "evidence_failed");
        assertEquals("failed", evidenceFailure.getStatus());
        assertEquals("evidence_failed", evidenceFailure.getCurrentStage());
        verify(sessionMapper, times(2)).updateById(stored);
    }

    @Test
    void ensureReportSchemaCompatibilityAddsSessionIdToExistingReportTable() {
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:ai_score_report_schema_compat;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("""
                CREATE TABLE ai_score_report (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  meeting_id BIGINT NOT NULL,
                  overall_score DECIMAL(5,2) DEFAULT NULL,
                  status VARCHAR(32) DEFAULT NULL,
                  PRIMARY KEY (id)
                )
                """);
        AiScoringSessionService service = new AiScoringSessionService(
                mock(AiScoringSessionMapper.class),
                mock(AiScoreReportMapper.class),
                null,
                null,
                null,
                mock(RubricResolverService.class),
                new ScoringFingerprintService(),
                jdbc
        );

        jdbc.execute("CREATE UNIQUE INDEX uk_meeting ON ai_score_report (meeting_id)");
        service.ensureReportSchemaCompatibility();

        assertTrue(hasColumn(jdbc, "ai_score_report", "session_id"));
        assertTrue(hasColumn(jdbc, "ai_score_report", "task_book_published"));
        assertTrue(hasColumn(jdbc, "ai_score_report", "task_book_json"));
        assertTrue(hasIndex(jdbc, "ai_score_report", "uk_session"));
        assertFalse(hasIndex(jdbc, "ai_score_report", "uk_meeting"));
        assertTrue(hasIndex(jdbc, "ai_score_report", "idx_ai_score_report_meeting"));
        jdbc.update("INSERT INTO ai_score_report (meeting_id, status) VALUES (9, 'completed')");
        jdbc.update("INSERT INTO ai_score_report (meeting_id, status) VALUES (9, 'completed')");
        Integer sameMeetingReports = jdbc.queryForObject(
                "SELECT COUNT(*) FROM ai_score_report WHERE meeting_id = 9", Integer.class);
        assertEquals(2, sameMeetingReports);
    }

    @Test
    void ensureSchemaCompatibilityAddsVersionedSpeakerAttributionStructures() {
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:ai_score_speaker_schema_compat;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("CREATE TABLE ai_scoring_session (id BIGINT PRIMARY KEY)");
        jdbc.execute("""
                CREATE TABLE ai_score_transcript_segment (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  session_id BIGINT NOT NULL,
                  segment_no INT NOT NULL,
                  speaker_label VARCHAR(128),
                  start_ms BIGINT NOT NULL,
                  end_ms BIGINT NOT NULL,
                  text CLOB NOT NULL,
                  source_type VARCHAR(32) NOT NULL,
                  confidence DECIMAL(5,4),
                  segment_hash VARCHAR(128) NOT NULL
                )
                """);
        AiScoringSessionService service = new AiScoringSessionService(
                mock(AiScoringSessionMapper.class),
                mock(AiScoreReportMapper.class),
                null,
                null,
                null,
                mock(RubricResolverService.class),
                new ScoringFingerprintService(),
                jdbc
        );

        service.ensureReportSchemaCompatibility();

        assertTrue(hasColumn(jdbc, "ai_scoring_session", "speaker_attribution_revision"));
        assertTrue(hasColumn(jdbc, "ai_score_speaker_identity", "person_id"));
        assertTrue(hasColumn(jdbc, "ai_score_transcript_segment", "segment_uid"));
        assertTrue(hasIndex(jdbc, "ai_score_transcript_segment", "uk_ai_score_transcript_segment_uid"));
        Integer turnTables = jdbc.queryForObject("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE LOWER(TABLE_NAME)='ai_score_speaker_turn'
                """, Integer.class);
        assertEquals(1, turnTables);
    }

    private PipelineCallbackRequest progressCallback(Long sessionId, String stage, int progress) {
        PipelineCallbackRequest callback = new PipelineCallbackRequest();
        callback.setSessionId(sessionId);
        callback.setStatus("scoring");
        callback.setCurrentStage(stage);
        callback.setProgressPercent(progress);
        return callback;
    }

    private AiScoringSessionService serviceWith(AiScoringSessionMapper sessionMapper) {
        return new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );
    }

    private ResolvedRubric resolvedRubric() {
        ResolvedRubric rubric = new ResolvedRubric();
        rubric.setTrackId("track-it");
        rubric.setTrackName("新一代信息技术赛道");
        rubric.setRubricId("rubric-it-v1");
        rubric.setRubricInternalVersion("v1.2-internal");
        rubric.setRubricHash("secret-hash");
        rubric.setRubricPath("/secret/rubric.md");
        rubric.setEvidenceSchemaId(33L);
        rubric.setEvidenceSchemaVersion("schema-v1");
        rubric.setEvidenceSchemaHash("schema-hash-v1");
        return rubric;
    }

    private AiScoringSessionCreateRequest createRequest(String sourceType) {
        AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
        request.setSourceType(sourceType);
        request.setMeetingId(12L);
        request.setProjectId(3L);
        request.setTeamId(9L);
        request.setTrackId("track-it");
        request.setTrackName("新一代信息技术赛道");
        request.setUseHistoryMemory(true);
        return request;
    }

    private AiScoringSession cachedCompletedSession(Long id) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setSessionNo("SC-20260623-000202");
        session.setStatus("completed");
        session.setCurrentStage("completed");
        session.setProgressPercent(100);
        session.setTrackId("track-it");
        session.setTrackName("新一代信息技术赛道");
        session.setSourceType("meeting_recording");
        session.setUseHistoryMemory(true);
        session.setJuryEnabled(false);
        return session;
    }

    private boolean hasColumn(JdbcTemplate jdbc, String tableName, String columnName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (var columns = connection.getMetaData().getColumns(null, null, tableName, null)) {
                while (columns.next()) {
                    if (columnName.equalsIgnoreCase(columns.getString("COLUMN_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private boolean hasIndex(JdbcTemplate jdbc, String tableName, String indexName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (var indexes = connection.getMetaData().getIndexInfo(null, null, tableName, false, false)) {
                while (indexes.next()) {
                    String existingName = indexes.getString("INDEX_NAME");
                    if (existingName != null && indexName.equalsIgnoreCase(existingName)) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }
}
