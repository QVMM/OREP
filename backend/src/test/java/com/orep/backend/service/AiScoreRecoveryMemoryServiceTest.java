package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreRecoveryMemoryServiceTest {

    private final AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
    private final AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
    private final AiScoreRecoveryMemoryService service = new AiScoreRecoveryMemoryService(
            sessionMapper,
            deductionMapper
    );

    @Test
    void historyDisabledReturnsEmpty() {
        AiScoringSession currentSession = session(12L, false);

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession,
                List.of(claim("deduction-1", "fixed", "4", 10L)),
                Set.of(10L)
        );

        assertTrue(recoveries.isEmpty());
        verify(sessionMapper, never()).selectList(any(LambdaQueryWrapper.class));
        verify(deductionMapper, never()).selectList(any(LambdaQueryWrapper.class));
    }

    @Test
    void noPreviousCompletedSessionReturnsEmpty() {
        AiScoringSession currentSession = session(12L, true);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession,
                List.of(claim("deduction-1", "fixed", "4", 10L)),
                Set.of(10L)
        );

        assertTrue(recoveries.isEmpty());
        verify(deductionMapper, never()).selectList(any(LambdaQueryWrapper.class));
    }

    @Test
    void missingHistoryScopeReturnsEmptyWithoutQueryingHistory() {
        AiScoringSession currentSession = session(12L, true);
        currentSession.setTrackId(" ");

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession,
                List.of(claim("deduction-1", "fixed", "4", 10L)),
                Set.of(10L)
        );

        assertTrue(recoveries.isEmpty());
        verify(sessionMapper, never()).selectList(any(LambdaQueryWrapper.class));
        verify(deductionMapper, never()).selectList(any(LambdaQueryWrapper.class));
    }

    @Test
    void capComesFromPreviousDeductionMaxRecoverablePoints() {
        AiScoringSession currentSession = session(12L, true);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(session(9L, true)));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
                "deduction-1",
                "2.5"
        )));

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession,
                List.of(claim("deduction-1", " VERIFIED ", "9", 10L)),
                Set.of(10L)
        );

        assertEquals(1, recoveries.size());
        assertEquals("deduction-1", recoveries.getFirst().getSourceDeductionId());
        assertEquals("verified", recoveries.getFirst().getRecoveryStatus());
        assertScore("9", recoveries.getFirst().getRequestedRecoverPoints());
        assertScore("2.5", recoveries.getFirst().getMaxRecoverablePoints());
        assertEquals("验收证据", recoveries.getFirst().getAcceptanceEvidence());
    }

    @Test
    void missingSourceDeductionThrows() {
        AiScoringSession currentSession = session(12L, true);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(session(9L, true)));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
                "deduction-1",
                "2.5"
        )));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.resolveTrustedRecoveries(
                        currentSession,
                        List.of(claim("missing-deduction", "recovered", "1", 10L)),
                        Set.of(10L)
                )
        );

        assertTrue(exception.getMessage().contains("missing-deduction"));
    }

    @Test
    void anchorOutsideCurrentSessionThrows() {
        AiScoringSession currentSession = session(12L, true);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(session(9L, true)));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
                "deduction-1",
                "2.5"
        )));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.resolveTrustedRecoveries(
                        currentSession,
                        List.of(claim("deduction-1", "fixed", "1", 99L)),
                        Set.of(10L)
                )
        );

        assertTrue(exception.getMessage().contains("99"));
    }

    @Test
    void buildRecoveryRowsCapsRecoveredPointsAndWritesEvidenceAnchorIdsJson() {
        LocalDateTime now = LocalDateTime.of(2026, 6, 24, 9, 30);
        AiScoreRecoveryInput recovery = recovery("deduction-1", "fixed", "8", "3");

        List<AiScoreDeduction> rows = service.buildRecoveryRows(
                12L,
                88L,
                List.of(recovery),
                List.of(claim("deduction-1", "fixed", "8", 10L)),
                now
        );

        assertEquals(1, rows.size());
        AiScoreDeduction row = rows.getFirst();
        assertEquals(12L, row.getSessionId());
        assertEquals(88L, row.getReportId());
        assertEquals("recovery-deduction-1", row.getDeductionId());
        assertScore("0", row.getDeductedPoints());
        assertScore("3", row.getRecoveredPoints());
        assertEquals("deduction-1", row.getRecoverySourceDeductionId());
        assertEquals("fixed", row.getStatus());
        assertEquals("medium", row.getEvidenceLevel());
        assertScore("0.80", row.getConfidence());
        assertEquals("[10]", row.getEvidenceAnchorIdsJson());
        assertEquals(now, row.getCreatedAt());
        assertTrue(row.getReason().contains("上一轮扣分项"));
        assertTrue(row.getRequiredFix().contains("恢复"));
        assertTrue(row.getAcceptanceCriteria().contains("验收"));
    }

    @Test
    void buildRecoveryRowsRejectsNegativeRecoveredPoints() {
        AiScoreRecoveryInput recovery = recovery("deduction-1", "fixed", "-1", "3");

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.buildRecoveryRows(
                        12L,
                        88L,
                        List.of(recovery),
                        List.of(claim("deduction-1", "fixed", "-1", 10L)),
                        LocalDateTime.now()
                )
        );

        assertTrue(exception.getMessage().contains("requestedRecoverPoints"));
    }

    @Test
    void nullPreviousMaxRecoverablePointsBecomesZero() {
        AiScoringSession currentSession = session(12L, true);
        AiScoreDeduction previousDeduction = previousDeduction("deduction-1", "2.5");
        previousDeduction.setMaxRecoverablePoints(null);
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(session(9L, true)));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction));

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession,
                List.of(claim("deduction-1", "fixed", "9", 10L)),
                Set.of(10L)
        );

        assertEquals(1, recoveries.size());
        assertScore("0", recoveries.getFirst().getMaxRecoverablePoints());
    }

    @Test
    void buildRecoveryRowsCannotRecoverMoreThanPreviousMaxRecoverablePoints() {
        LocalDateTime now = LocalDateTime.of(2026, 6, 24, 10, 0);
        AiScoreRecoveryInput recovery = recovery("deduction-1", "fixed", "10", "4");

        List<AiScoreDeduction> rows = service.buildRecoveryRows(
                12L,
                88L,
                List.of(recovery),
                List.of(claim("deduction-1", "fixed", "10", 10L)),
                now
        );

        assertEquals(1, rows.size());
        AiScoreDeduction row = rows.getFirst();
        assertScore("4", row.getRecoveredPoints());
        assertScore("0", row.getDeductedPoints());
        assertEquals("deduction-1", row.getRecoverySourceDeductionId());
        assertEquals("[10]", row.getEvidenceAnchorIdsJson());
    }

    private AiScoringSession session(Long id, Boolean useHistoryMemory) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setProjectId(1L);
        session.setTeamId(2L);
        session.setTrackId("track-a");
        session.setUseHistoryMemory(useHistoryMemory);
        session.setStatus("completed");
        return session;
    }

    private AiScoreDeduction previousDeduction(String deductionId, String maxRecoverablePoints) {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setDeductionId(deductionId);
        deduction.setMaxRecoverablePoints(new BigDecimal(maxRecoverablePoints));
        return deduction;
    }

    private AiScoreStructuredResultRequest.RecoveryClaimInput claim(
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
}
