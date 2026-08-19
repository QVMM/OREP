package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreStructuredResultServiceTest {

    private final AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
    private final AiScoreEvidenceAnchorMapper evidenceAnchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
    private final AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
    private final AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
    private final AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
    private final AiScoreStructuredResultValidator validator = new AiScoreStructuredResultValidator();
    private final AiScoreRuleEngine ruleEngine = new AiScoreRuleEngine();
    private final AiScoreRecoveryMemoryService recoveryMemoryService = mock(AiScoreRecoveryMemoryService.class);
    private final AiScoreStructuredResultService service = new AiScoreStructuredResultService(
            sessionMapper,
            evidenceAnchorMapper,
            reportMapper,
            observationMapper,
            deductionMapper,
            validator,
            ruleEngine,
            recoveryMemoryService,
            new ObjectMapper()
    );

    @Test
    void validResultPersistsStructuredRowsReportAndCompletedSession() {
        AiScoringSession session = session(123L, 456L, null);
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(888L);
        existingReport.setMeetingId(456L);
        existingReport.setStartedAt(LocalDateTime.now().minusMinutes(5));
        when(sessionMapper.selectById(123L)).thenReturn(session);
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);

        AiScoreRuleEngineResult result = service.applyStructuredResult(123L, validRequest(123L), List.of());

        assertSame(result, result);
        assertScore("95.00", result.getFinalScore());

        ArgumentCaptor<AiScoreReport> reportCaptor = ArgumentCaptor.forClass(AiScoreReport.class);
        verify(reportMapper).updateById(reportCaptor.capture());
        AiScoreReport savedReport = reportCaptor.getValue();
        assertEquals(888L, savedReport.getId());
        assertEquals(456L, savedReport.getMeetingId());
        assertScore("95.00", savedReport.getOverallScore());
        assertEquals("completed", savedReport.getStatus());
        assertEquals("p8-c", savedReport.getRuleEngineVersion());
        assertNotNull(savedReport.getStructuredResultJson());
        assertTrue(savedReport.getStructuredResultJson().contains("\"sessionId\":123"));

        ArgumentCaptor<AiScoreObservation> observationCaptor = ArgumentCaptor.forClass(AiScoreObservation.class);
        verify(observationMapper).insert(observationCaptor.capture());
        AiScoreObservation observation = observationCaptor.getValue();
        assertEquals(123L, observation.getSessionId());
        assertEquals(888L, observation.getReportId());
        assertEquals("[10,11]", observation.getEvidenceAnchorIdsJson());

        ArgumentCaptor<AiScoreDeduction> deductionCaptor = ArgumentCaptor.forClass(AiScoreDeduction.class);
        verify(deductionMapper).insert(deductionCaptor.capture());
        AiScoreDeduction deduction = deductionCaptor.getValue();
        assertEquals(123L, deduction.getSessionId());
        assertEquals(888L, deduction.getReportId());
        assertEquals("medium", deduction.getEvidenceLevel());
        assertScore("0.81", deduction.getConfidence());
        assertScore("0", deduction.getRecoveredPoints());
        assertEquals("[10]", deduction.getEvidenceAnchorIdsJson());

        InOrder rowWriteOrder = inOrder(observationMapper, deductionMapper);
        rowWriteOrder.verify(observationMapper).delete(any(LambdaQueryWrapper.class));
        rowWriteOrder.verify(deductionMapper).delete(any(LambdaQueryWrapper.class));
        rowWriteOrder.verify(observationMapper).insert(any(AiScoreObservation.class));
        rowWriteOrder.verify(deductionMapper).insert(any(AiScoreDeduction.class));

        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        verify(sessionMapper).updateById(sessionCaptor.capture());
        AiScoringSession updatedSession = sessionCaptor.getValue();
        assertEquals(888L, updatedSession.getReportId());
        assertEquals("completed", updatedSession.getStatus());
        assertEquals("rule_engine_completed", updatedSession.getCurrentStage());
        assertEquals(100, updatedSession.getProgressPercent());
        assertNotNull(updatedSession.getCompletedAt());
        assertNotNull(updatedSession.getUpdatedAt());
    }

    @Test
    void rejectsHallucinatedEvidenceAnchorId() {
        when(sessionMapper.selectById(123L)).thenReturn(session(123L, 456L, null));
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        AiScoreStructuredResultRequest request = validRequest(123L);
        request.getDeductions().getFirst().setEvidenceAnchorIds(List.of(99L));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.applyStructuredResult(123L, request, List.of())
        );

        assertTrue(exception.getMessage().contains("99"));
        verify(reportMapper, never()).insert(any(AiScoreReport.class));
        verify(observationMapper, never()).insert(any(AiScoreObservation.class));
        verify(deductionMapper, never()).insert(any(AiScoreDeduction.class));
    }

    @Test
    void validatesStructuredShapeBeforeEvidenceAnchorWhitelist() {
        when(sessionMapper.selectById(123L)).thenReturn(session(123L, 456L, null));
        AiScoreStructuredResultRequest request = validRequest(123L);
        List<AiScoreStructuredResultRequest.ObservationInput> observations = new ArrayList<>();
        observations.add(null);
        request.setObservations(observations);

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.applyStructuredResult(123L, request, List.of())
        );

        assertTrue(exception.getMessage().contains("observations[0]"));
        verify(evidenceAnchorMapper, never()).selectList(any(LambdaQueryWrapper.class));
    }

    @Test
    void appliesTrustedRecoveryFromPreviousDeductionAndPersistsRecoveryRow() {
        AiScoreRecoveryMemoryService realRecoveryMemoryService = new AiScoreRecoveryMemoryService(
                sessionMapper,
                deductionMapper
        );
        AiScoreStructuredResultService serviceWithRealRecovery = new AiScoreStructuredResultService(
                sessionMapper,
                evidenceAnchorMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                validator,
                ruleEngine,
                realRecoveryMemoryService,
                new ObjectMapper()
        );
        AiScoringSession session = session(123L, 456L, null);
        session.setProjectId(1L);
        session.setTeamId(2L);
        session.setTrackId("track-a");
        session.setUseHistoryMemory(true);
        AiScoringSession previousSession = session(122L, 455L, 887L);
        previousSession.setProjectId(1L);
        previousSession.setTeamId(2L);
        previousSession.setTrackId("track-a");
        previousSession.setStatus("completed");
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(888L);
        existingReport.setMeetingId(456L);
        when(sessionMapper.selectById(123L)).thenReturn(session);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession));
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
                "deduction-1",
                "6"
        )));

        AiScoreStructuredResultRequest request = validRequest(123L);
        request.setRecoveryClaims(List.of(recoveryClaim("deduction-1", "fixed", "10", 11L)));

        AiScoreRuleEngineResult result = serviceWithRealRecovery.applyStructuredResult(123L, request, List.of());

        assertScore("100.00", result.getFinalScore());
        assertScore("6.00", result.getRecoveredScore());
        assertEquals(1, result.getRecoveries().size());
        assertEquals("deduction-1", result.getRecoveries().getFirst().getSourceDeductionId());
        assertScore("6", result.getRecoveries().getFirst().getMaxRecoverablePoints());

        ArgumentCaptor<AiScoreDeduction> deductionCaptor = ArgumentCaptor.forClass(AiScoreDeduction.class);
        verify(deductionMapper, times(2)).insert(deductionCaptor.capture());
        List<AiScoreDeduction> insertedDeductions = deductionCaptor.getAllValues();
        assertEquals("deduction-1", insertedDeductions.get(0).getDeductionId());
        assertEquals("recovery-deduction-1", insertedDeductions.get(1).getDeductionId());
        assertEquals("deduction-1", insertedDeductions.get(1).getRecoverySourceDeductionId());
        assertScore("6", insertedDeductions.get(1).getRecoveredPoints());
        assertEquals("[11]", insertedDeductions.get(1).getEvidenceAnchorIdsJson());
        assertEquals("验收证据", insertedDeductions.get(1).getAcceptanceCriteria());
    }

    @Test
    void doesNotUseExplicitRecoveryFallbackWhenRecoveryClaimsArePresent() {
        AiScoringSession session = session(123L, 456L, null);
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(888L);
        existingReport.setMeetingId(456L);
        when(sessionMapper.selectById(123L)).thenReturn(session);
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);

        AiScoreStructuredResultRequest request = validRequest(123L);
        request.setRecoveryClaims(List.of(recoveryClaim("deduction-1", "fixed", "10", 11L)));
        AiScoreRecoveryInput bypassRecovery = recovery("deduction-1", "fixed", "10", "10");

        AiScoreRuleEngineResult result = service.applyStructuredResult(123L, request, List.of(bypassRecovery));

        assertScore("95.00", result.getFinalScore());
        assertScore("0.00", result.getRecoveredScore());
        assertTrue(result.getRecoveries().isEmpty());
    }

    @Test
    void rejectsHallucinatedRecoveryClaimEvidenceAnchorId() {
        when(sessionMapper.selectById(123L)).thenReturn(session(123L, 456L, null));
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        AiScoreStructuredResultRequest request = validRequest(123L);
        request.setRecoveryClaims(List.of(recoveryClaim("deduction-1", "fixed", "5", 99L)));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.applyStructuredResult(123L, request, List.of())
        );

        assertTrue(exception.getMessage().contains("99"));
        verify(recoveryMemoryService, never()).resolveTrustedRecoveries(any(), any(), any());
        verify(reportMapper, never()).insert(any(AiScoreReport.class));
        verify(observationMapper, never()).insert(any(AiScoreObservation.class));
        verify(deductionMapper, never()).insert(any(AiScoreDeduction.class));
    }

    @Test
    void structuredResultSummaryDoesNotExposeRuleEngineVersion() throws Exception {
        AiScoringSession session = session(123L, 456L, null);
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(888L);
        existingReport.setMeetingId(456L);
        when(sessionMapper.selectById(123L)).thenReturn(session);
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);

        service.applyStructuredResult(123L, validRequest(123L), List.of());

        ArgumentCaptor<AiScoreReport> reportCaptor = ArgumentCaptor.forClass(AiScoreReport.class);
        verify(reportMapper).updateById(reportCaptor.capture());
        AiScoreReport savedReport = reportCaptor.getValue();
        assertNotNull(savedReport.getStructuredResultJson());
        assertFalse(savedReport.getStructuredResultJson().contains("ruleEngineVersion"));
        assertFalse(savedReport.getStructuredResultJson().contains("resultRuleEngineVersion"));
        assertNoVersionKey(new ObjectMapper().readTree(savedReport.getStructuredResultJson()));
    }

    @Test
    void usesSessionIdWhenMeetingIdIsMissing() {
        when(sessionMapper.selectById(123L)).thenReturn(session(123L, null, null));
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.insert(any(AiScoreReport.class))).thenAnswer(invocation -> {
            AiScoreReport report = invocation.getArgument(0);
            report.setId(777L);
            return 1;
        });

        service.applyStructuredResult(123L, validRequest(null), List.of());

        ArgumentCaptor<AiScoreReport> reportCaptor = ArgumentCaptor.forClass(AiScoreReport.class);
        verify(reportMapper).insert(reportCaptor.capture());
        assertEquals(123L, reportCaptor.getValue().getSessionId());
        assertNull(reportCaptor.getValue().getMeetingId());
    }

    @Test
    void rejectsSessionIdMismatch() {
        AiScoreStructuredResultRequest request = validRequest(124L);

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.applyStructuredResult(123L, request, List.of())
        );

        assertTrue(exception.getMessage().contains("sessionId"));
        verify(sessionMapper, never()).selectById(any());
    }

    @Test
    void recoveryRowsDoNotRemoveCurrentNewDeductions() {
        AiScoreRecoveryMemoryService realRecoveryMemoryService = new AiScoreRecoveryMemoryService(
                sessionMapper,
                deductionMapper
        );
        AiScoreStructuredResultService serviceWithRealRecovery = new AiScoreStructuredResultService(
                sessionMapper,
                evidenceAnchorMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                validator,
                ruleEngine,
                realRecoveryMemoryService,
                new ObjectMapper()
        );
        AiScoringSession session = session(123L, 456L, null);
        session.setProjectId(1L);
        session.setTeamId(2L);
        session.setTrackId("track-a");
        session.setUseHistoryMemory(true);
        AiScoringSession previousSession = session(122L, 455L, 887L);
        previousSession.setProjectId(1L);
        previousSession.setTeamId(2L);
        previousSession.setTrackId("track-a");
        previousSession.setStatus("completed");
        AiScoreReport existingReport = new AiScoreReport();
        existingReport.setId(888L);
        existingReport.setMeetingId(456L);
        when(sessionMapper.selectById(123L)).thenReturn(session);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession));
        when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
        when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
                "deduction-old",
                "6"
        )));

        AiScoreStructuredResultRequest request = validRequest(123L);
        request.getDeductions().getFirst().setDeductionId("deduction-new");
        request.setRecoveryClaims(List.of(recoveryClaim("deduction-old", "fixed", "6", 11L)));

        serviceWithRealRecovery.applyStructuredResult(123L, request, List.of());

        ArgumentCaptor<AiScoreDeduction> deductionCaptor = ArgumentCaptor.forClass(AiScoreDeduction.class);
        verify(deductionMapper, times(2)).insert(deductionCaptor.capture());
        List<AiScoreDeduction> insertedDeductions = deductionCaptor.getAllValues();
        assertEquals("deduction-new", insertedDeductions.get(0).getDeductionId());
        assertEquals(null, insertedDeductions.get(0).getRecoverySourceDeductionId());
        assertEquals("recovery-deduction-old", insertedDeductions.get(1).getDeductionId());
        assertEquals("deduction-old", insertedDeductions.get(1).getRecoverySourceDeductionId());
        assertScore("6", insertedDeductions.get(1).getRecoveredPoints());
    }

    private AiScoringSession session(Long id, Long meetingId, Long reportId) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setMeetingId(meetingId);
        session.setReportId(reportId);
        session.setStartedAt(LocalDateTime.now().minusMinutes(10));
        return session;
    }

    private AiScoreEvidenceAnchor anchor(Long id) {
        AiScoreEvidenceAnchor anchor = new AiScoreEvidenceAnchor();
        anchor.setId(id);
        anchor.setSessionId(123L);
        return anchor;
    }

    private AiScoreStructuredResultRequest validRequest(Long sessionId) {
        AiScoreStructuredResultRequest request = new AiScoreStructuredResultRequest();
        request.setSessionId(sessionId);
        request.setRuleEngineVersion("p8-d-test");
        request.setScoreSummary(scoreSummary());
        request.setObservations(List.of(observation()));
        request.setDeductions(List.of(deduction()));
        return request;
    }

    private AiScoreStructuredResultRequest.ScoreSummary scoreSummary() {
        AiScoreStructuredResultRequest.ScoreSummary summary = new AiScoreStructuredResultRequest.ScoreSummary();
        summary.setRawTotalScore(new BigDecimal("100"));
        summary.setFinalScore(new BigDecimal("95"));
        summary.setScoreCap(new BigDecimal("100"));
        return summary;
    }

    private AiScoreStructuredResultRequest.ObservationInput observation() {
        AiScoreStructuredResultRequest.ObservationInput observation = new AiScoreStructuredResultRequest.ObservationInput();
        observation.setObservationCode("market_need");
        observation.setDimensionCode("market");
        observation.setDimensionName("市场需求");
        observation.setRawScore(new BigDecimal("100"));
        observation.setScoreCap(new BigDecimal("100"));
        observation.setEvidenceLevel("medium");
        observation.setConfidence(new BigDecimal("0.9"));
        observation.setValidityStatus("valid");
        observation.setModelReason("证据支持市场需求");
        observation.setEvidenceAnchorIds(List.of(10L, 11L));
        return observation;
    }

    private AiScoreStructuredResultRequest.DeductionInput deduction() {
        AiScoreStructuredResultRequest.DeductionInput deduction = new AiScoreStructuredResultRequest.DeductionInput();
        deduction.setDeductionId("deduction-1");
        deduction.setObservationCode("market_need");
        deduction.setDimensionCode("market");
        deduction.setDeductedPoints(new BigDecimal("5"));
        deduction.setMaxRecoverablePoints(new BigDecimal("5"));
        deduction.setReason("缺少客户访谈");
        deduction.setRequiredFix("补充客户访谈");
        deduction.setAcceptanceCriteria("访谈记录覆盖目标客户");
        deduction.setEvidenceLevel("medium");
        deduction.setConfidence(new BigDecimal("0.81"));
        deduction.setStatus("new");
        deduction.setEvidenceAnchorIds(List.of(10L));
        return deduction;
    }

    private AiScoreStructuredResultRequest.RecoveryClaimInput recoveryClaim(
            String sourceDeductionId,
            String recoveryStatus,
            String requestedRecoverPoints,
            Long evidenceAnchorId
    ) {
        AiScoreStructuredResultRequest.RecoveryClaimInput claim =
                new AiScoreStructuredResultRequest.RecoveryClaimInput();
        claim.setSourceDeductionId(sourceDeductionId);
        claim.setRecoveryStatus(recoveryStatus);
        claim.setRequestedRecoverPoints(new BigDecimal(requestedRecoverPoints));
        claim.setAcceptanceEvidence("验收证据");
        claim.setEvidenceAnchorIds(List.of(evidenceAnchorId));
        return claim;
    }

    private AiScoreDeduction previousDeduction(String deductionId, String maxRecoverablePoints) {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setDeductionId(deductionId);
        deduction.setMaxRecoverablePoints(new BigDecimal(maxRecoverablePoints));
        return deduction;
    }

    private AiScoreRecoveryInput recovery(
            String sourceDeductionId,
            String recoveryStatus,
            String requestedRecoverPoints,
            String maxRecoverablePoints
    ) {
        AiScoreRecoveryInput recovery = new AiScoreRecoveryInput();
        recovery.setSourceDeductionId(sourceDeductionId);
        recovery.setRecoveryStatus(recoveryStatus);
        recovery.setRequestedRecoverPoints(new BigDecimal(requestedRecoverPoints));
        recovery.setMaxRecoverablePoints(new BigDecimal(maxRecoverablePoints));
        recovery.setAcceptanceEvidence("验收证据");
        return recovery;
    }

    private void assertScore(String expected, BigDecimal actual) {
        assertEquals(new BigDecimal(expected), actual);
    }

    private void assertNoVersionKey(JsonNode node) {
        if (node == null) {
            return;
        }
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                assertFalse(field.getKey().toLowerCase().contains("version"), field.getKey());
                assertNoVersionKey(field.getValue());
            }
        } else if (node.isArray()) {
            for (JsonNode child : node) {
                assertNoVersionKey(child);
            }
        }
    }
}
