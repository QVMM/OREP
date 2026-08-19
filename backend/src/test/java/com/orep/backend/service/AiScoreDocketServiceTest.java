package com.orep.backend.service;

import com.orep.backend.dto.DocketIdentity;
import com.orep.backend.entity.AiScoreDocket;
import com.orep.backend.entity.AiScoreDocketRun;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDocketMapper;
import com.orep.backend.mapper.AiScoreDocketRunMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DuplicateKeyException;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AiScoreDocketServiceTest {

    private static final String VIDEO_SHA256 = "aa".repeat(32);
    private static final String RULE_VERSION = "v1.2";
    private static final String RULE_HASH = "dd".repeat(32);
    private static final String TRACK_ID = "track-c889f0110e2d";

    private final DocketIdService docketIdService = new DocketIdService();
    private AiScoringSessionMapper sessionMapper;
    private AiScoreDocketMapper docketMapper;
    private AiScoreDocketRunMapper runMapper;
    private AiScoreDocketService service;

    @BeforeEach
    void setUp() {
        sessionMapper = mock(AiScoringSessionMapper.class);
        docketMapper = mock(AiScoreDocketMapper.class);
        runMapper = mock(AiScoreDocketRunMapper.class);
        service = new AiScoreDocketService(sessionMapper, docketMapper, docketIdService, runMapper);
    }

    @Test
    void blankHashReturnsNullWithoutWriting() {
        assertNull(service.bindAfterVideoHash(101L, null));
        assertNull(service.bindAfterVideoHash(101L, ""));
        assertNull(service.bindAfterVideoHash(101L, "   "));

        verifyNoInteractions(sessionMapper, docketMapper);
    }

    @Test
    void missingSessionThrows() {
        when(sessionMapper.selectById(101L)).thenReturn(null);

        assertThrows(IllegalArgumentException.class,
                () -> service.bindAfterVideoHash(101L, VIDEO_SHA256));

        verify(docketMapper, never()).insert(any());
        verify(sessionMapper, never()).updateById(any());
    }

    @Test
    void firstBindInsertsDocketAndUpdatesSession() {
        AiScoringSession session = unboundSession(101L);
        when(sessionMapper.selectById(101L)).thenReturn(session);

        String docketId = service.bindAfterVideoHash(101L, VIDEO_SHA256);

        assertEquals(expectedDocketId(VIDEO_SHA256), docketId);
        assertEquals(64, docketId.length());
        assertTrue(docketId.matches("[0-9a-f]{64}"));

        ArgumentCaptor<AiScoreDocket> docketCaptor = ArgumentCaptor.forClass(AiScoreDocket.class);
        verify(docketMapper).insert(docketCaptor.capture());
        AiScoreDocket inserted = docketCaptor.getValue();
        assertEquals(docketId, inserted.getDocketId());
        assertEquals(VIDEO_SHA256, inserted.getVideoSha256());
        assertEquals(RULE_VERSION, inserted.getRuleVersion());
        assertEquals(RULE_HASH, inserted.getRuleHash());
        assertEquals(AiScoreDocketService.DEFAULT_CONTRACT_VERSION, inserted.getContractVersion());
        assertEquals(TRACK_ID, inserted.getTrackId());
        assertNotNull(inserted.getCreatedAt());

        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        verify(sessionMapper).updateById(sessionCaptor.capture());
        assertEquals(docketId, sessionCaptor.getValue().getDocketId());
        assertEquals(docketId, session.getDocketId());
    }

    @Test
    void secondBindOnSameSessionKeepsOriginalDocketId() {
        String originalDocketId = "ab".repeat(32);
        AiScoringSession session = unboundSession(101L);
        session.setDocketId(originalDocketId);
        when(sessionMapper.selectById(101L)).thenReturn(session);

        String returned = service.bindAfterVideoHash(101L, "bb".repeat(32));

        assertEquals(originalDocketId, returned);
        verify(docketMapper, never()).insert(any());
        verify(docketMapper, never()).selectById(any());
        verify(sessionMapper, never()).updateById(any());
    }

    @Test
    void secondSessionSameIdentityReusesDocketRow() {
        String docketId = expectedDocketId(VIDEO_SHA256);
        AiScoreDocket existing = new AiScoreDocket();
        existing.setDocketId(docketId);
        existing.setVideoSha256(VIDEO_SHA256);
        existing.setRuleVersion(RULE_VERSION);
        existing.setRuleHash(RULE_HASH);
        existing.setContractVersion(AiScoreDocketService.DEFAULT_CONTRACT_VERSION);
        existing.setTrackId(TRACK_ID);

        AiScoringSession session = unboundSession(202L);
        when(sessionMapper.selectById(202L)).thenReturn(session);
        when(docketMapper.selectById(docketId)).thenReturn(existing);

        String returned = service.bindAfterVideoHash(202L, VIDEO_SHA256);

        assertEquals(docketId, returned);
        verify(docketMapper, never()).insert(any());
        ArgumentCaptor<AiScoringSession> sessionCaptor = ArgumentCaptor.forClass(AiScoringSession.class);
        verify(sessionMapper).updateById(sessionCaptor.capture());
        assertEquals(202L, sessionCaptor.getValue().getId());
        assertEquals(docketId, sessionCaptor.getValue().getDocketId());
    }

    @Test
    void missingTrackIdOrRubricThrows() {
        AiScoringSession missingTrack = unboundSession(101L);
        missingTrack.setTrackId("  ");
        when(sessionMapper.selectById(101L)).thenReturn(missingTrack);
        assertThrows(IllegalArgumentException.class,
                () -> service.bindAfterVideoHash(101L, VIDEO_SHA256));

        AiScoringSession missingRuleVersion = unboundSession(102L);
        missingRuleVersion.setRubricInternalVersion(null);
        when(sessionMapper.selectById(102L)).thenReturn(missingRuleVersion);
        assertThrows(IllegalArgumentException.class,
                () -> service.bindAfterVideoHash(102L, VIDEO_SHA256));

        AiScoringSession missingRuleHash = unboundSession(103L);
        missingRuleHash.setRubricHash("");
        when(sessionMapper.selectById(103L)).thenReturn(missingRuleHash);
        assertThrows(IllegalArgumentException.class,
                () -> service.bindAfterVideoHash(103L, VIDEO_SHA256));

        verify(docketMapper, never()).insert(any());
        verify(sessionMapper, never()).updateById(any());
    }

    @Test
    void recordsTapeGroundedFlagFromStructuredResult() {
        String docketId = "ab".repeat(32);
        AiScoringSession session = boundSession(101L, docketId);
        AiScoreReport report = report(37L, new BigDecimal("48.3"), "{\"技能水平\":48}");
        report.setStructuredResultJson("{\"ruleEngineScore\":48.3,\"tapeGrounded\":true}");
        when(runMapper.selectOne(any())).thenReturn(null);

        AiScoreDocketRun run = service.recordSuccessfulRun(session, report);

        assertEquals(Boolean.TRUE, run.getTapeGrounded());
        assertEquals(Boolean.TRUE, AiScoreDocketService.tapeGroundedFrom(report));
    }

    @Test
    void tapeGroundedFromIgnoresMissingField() {
        AiScoreReport report = report(37L, new BigDecimal("48.3"), "{}");
        report.setStructuredResultJson("{\"ruleEngineScore\":48.3}");
        assertNull(AiScoreDocketService.tapeGroundedFrom(report));
    }

    @Test
    void firstSuccessfulRunIsIndexOneWithZeroDelta() {
        String docketId = "ab".repeat(32);
        AiScoringSession session = boundSession(101L, docketId);
        AiScoreReport report = report(37L, new BigDecimal("80"), "{\"技能水平\":80}");
        when(runMapper.selectOne(any())).thenReturn(null);

        AiScoreDocketRun run = service.recordSuccessfulRun(session, report);

        assertEquals(1, run.getRunIndex());
        assertEquals(0, run.getScoreDeltaAbs().compareTo(BigDecimal.ZERO));
        assertEquals(docketId, run.getDocketId());
        assertEquals(101L, run.getSessionId());
        assertEquals(37L, run.getReportId());
        assertEquals(new BigDecimal("80"), run.getOfficialScore());
        assertEquals("{\"技能水平\":80}", run.getDimensionScoresJson());
        assertEquals("completed", run.getStatus());
        assertNull(run.getTranscriptCoverage());
        assertNull(run.getSeekableAnchorRate());
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, run.getStabilityBand());
        assertNotNull(run.getCreatedAt());

        ArgumentCaptor<AiScoreDocketRun> captor = ArgumentCaptor.forClass(AiScoreDocketRun.class);
        verify(runMapper).insert(captor.capture());
        assertSame(run, captor.getValue());
        verify(runMapper, never()).updateById(any());
    }

    @Test
    void recordsCoverageRatesAndKeepsGreenWhenAnchorsSeekable() {
        String docketId = "ab".repeat(32);
        AiScoreDocketRun first = completedRun(docketId, 1, 101L, new BigDecimal("48.3"));
        first.setDimensionScoresJson("{\"skill_level\":{\"score\":30.0,\"max_score\":60.0}}");
        first.setSeekableAnchorRate(new BigDecimal("0.80"));
        first.setTranscriptCoverage(new BigDecimal("1.0000"));
        AiScoringSession secondSession = boundSession(202L, docketId);
        AiScoreReport secondReport = report(54L, new BigDecimal("48.3"),
                "{\"skill_level\":{\"score\":30.0,\"max_score\":60.0}}");
        when(runMapper.selectOne(any())).thenReturn(null, first, first, first);
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first));

        RunCoverageCalculator.Rates rates = new RunCoverageCalculator.Rates(
                new BigDecimal("0.9800"),
                new BigDecimal("0.7500")
        );
        AiScoreDocketRun second = service.recordSuccessfulRun(secondSession, secondReport, rates);

        assertEquals(0, second.getTranscriptCoverage().compareTo(new BigDecimal("0.9800")));
        assertEquals(0, second.getSeekableAnchorRate().compareTo(new BigDecimal("0.7500")));
        assertEquals(0, second.getScoreDeltaAbs().compareTo(BigDecimal.ZERO));
        assertEquals(StabilityBandCalculator.GREEN, second.getStabilityBand());
    }

    @Test
    void secondSessionSameDocketRecordsDeltaAgainstFirstSuccessfulScore() {
        String docketId = "ab".repeat(32);
        AiScoreDocketRun first = completedRun(docketId, 1, 101L, new BigDecimal("80"));
        AiScoringSession secondSession = boundSession(202L, docketId);
        AiScoreReport secondReport = report(38L, new BigDecimal("84"), "{\"技能水平\":84}");
        when(runMapper.selectOne(any())).thenReturn(null, first, first);
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first));

        AiScoreDocketRun second = service.recordSuccessfulRun(secondSession, secondReport);

        assertEquals(2, second.getRunIndex());
        assertEquals(0, second.getScoreDeltaAbs().compareTo(new BigDecimal("4")));
        assertEquals(new BigDecimal("84"), second.getOfficialScore());
        assertEquals(38L, second.getReportId());
        assertEquals("completed", second.getStatus());
        assertEquals(StabilityBandCalculator.RED, second.getStabilityBand());
        verify(runMapper).insert(second);
        verify(runMapper, never()).updateById(any());
    }

    @Test
    void sameSessionRecordedTwiceIsIdempotentAndDoesNotOverwriteScores() {
        String docketId = "ab".repeat(32);
        AiScoringSession session = boundSession(101L, docketId);
        AiScoreReport firstReport = report(37L, new BigDecimal("80"), "{\"技能水平\":80}");
        when(runMapper.selectOne(any())).thenReturn(null);

        AiScoreDocketRun first = service.recordSuccessfulRun(session, firstReport);

        when(runMapper.selectOne(any())).thenReturn(first);
        AiScoreReport retryReport = report(37L, new BigDecimal("99"), "{\"changed\":true}");
        AiScoreDocketRun retry = service.recordSuccessfulRun(session, retryReport);

        assertSame(first, retry);
        assertEquals(new BigDecimal("80"), retry.getOfficialScore());
        assertEquals("{\"技能水平\":80}", retry.getDimensionScoresJson());
        assertEquals(1, retry.getRunIndex());
        verify(runMapper, times(1)).insert(any());
        verify(runMapper, never()).updateById(any());
    }

    @Test
    void blankDocketIdThrowsWithoutInserting() {
        AiScoreReport report = report(37L, new BigDecimal("80"), null);
        IllegalArgumentException blank = assertThrows(IllegalArgumentException.class,
                () -> service.recordSuccessfulRun(boundSession(101L, "  "), report));
        assertEquals("docketId cannot be blank when recording a successful run", blank.getMessage());

        IllegalArgumentException missing = assertThrows(IllegalArgumentException.class,
                () -> service.recordSuccessfulRun(boundSession(101L, null), report));
        assertEquals("docketId cannot be blank when recording a successful run", missing.getMessage());

        assertThrows(IllegalArgumentException.class, () -> service.recordSuccessfulRun(null, report));
        assertThrows(IllegalArgumentException.class,
                () -> service.recordSuccessfulRun(boundSession(101L, "ab".repeat(32)), null));

        verify(runMapper, never()).insert(any());
        verify(runMapper, never()).selectOne(any());
    }

    @Test
    void duplicateSessionKeyReturnsExistingWithoutOverwrite() {
        String docketId = "ab".repeat(32);
        AiScoringSession session = boundSession(101L, docketId);
        AiScoreReport report = report(37L, new BigDecimal("99"), "{\"changed\":true}");
        AiScoreDocketRun existing = completedRun(docketId, 1, 101L, new BigDecimal("80"));
        existing.setDimensionScoresJson("{\"技能水平\":80}");
        when(runMapper.selectOne(any())).thenReturn(null, existing);
        doThrow(new DuplicateKeyException("uk_docket_run_session")).when(runMapper).insert(any());

        AiScoreDocketRun returned = service.recordSuccessfulRun(session, report);

        assertSame(existing, returned);
        assertEquals(new BigDecimal("80"), returned.getOfficialScore());
        assertEquals("{\"技能水平\":80}", returned.getDimensionScoresJson());
        verify(runMapper, never()).updateById(any());
    }

    @Test
    void stabilitySnapshotUsesCompletedRunsAndNeverGreensASingleRun() {
        String docketId = "ab".repeat(32);
        AiScoreDocketRun first = completedRun(docketId, 1, 101L, new BigDecimal("80"));
        first.setScoreDeltaAbs(BigDecimal.ZERO);
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first));

        var single = service.stabilitySnapshot(docketId);
        assertEquals(1, single.getRunCount());
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, single.getBand());

        AiScoreDocketRun second = completedRun(docketId, 2, 202L, new BigDecimal("84"));
        second.setScoreDeltaAbs(new BigDecimal("4"));
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first, second));
        var red = service.stabilitySnapshot(docketId);
        assertEquals(2, red.getRunCount());
        assertEquals(StabilityBandCalculator.RED, red.getBand());
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, red.getIdentityBand());

        AiScoreDocketRun third = completedRun(docketId, 3, 303L, new BigDecimal("84"));
        third.setScoreDeltaAbs(new BigDecimal("4"));
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first, second, third));
        var mixed = service.stabilitySnapshot(docketId);
        assertEquals(StabilityBandCalculator.RED, mixed.getBand());
        assertEquals(StabilityBandCalculator.GREEN, mixed.getIdentityBand());
        assertEquals(2, mixed.getIdentityRunCount());
        assertTrue(mixed.getIdentityHeadline().contains("连续"));
        assertEquals(StabilityBandCalculator.NOT_REVIEWED, service.stabilitySnapshot("  ").getBand());
    }

    @Test
    void previousCompletedRunReturnsTheRunBeforeCurrentSession() {
        String docketId = "ab".repeat(32);
        AiScoreDocketRun first = completedRun(docketId, 1, 101L, new BigDecimal("80"));
        first.setReportId(55L);
        AiScoreDocketRun second = completedRun(docketId, 2, 202L, new BigDecimal("84"));
        second.setReportId(66L);
        when(runMapper.selectList(any())).thenReturn(java.util.List.of(first, second));
        assertEquals(55L, service.previousCompletedRun(docketId, 202L).getReportId());
        assertNull(service.previousCompletedRun(docketId, 101L));
        assertNull(service.previousCompletedRun("  ", 202L));
    }

    @Test
    void teamTrackPriorBookSkipsThisRoundAndOtherTeams() {
        AiScoringSession older = boundSession(47L, "old-docket");
        older.setTeamId(3L);
        older.setTrackId(TRACK_ID);
        AiScoringSession newer = boundSession(52L, "new-docket");
        newer.setTeamId(3L);
        newer.setTrackId(TRACK_ID);
        when(sessionMapper.selectList(any())).thenReturn(java.util.List.of(newer, older));

        AiScoreDocket published = new AiScoreDocket();
        published.setDocketId("new-docket");
        published.setTaskBookPublished(true);
        published.setTaskBookJson("{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}");
        published.setTaskBookPublishedSessionId(52L);
        when(docketMapper.selectById("new-docket")).thenReturn(published);

        DocketTaskBook.Snapshot prior = service.loadTeamTrackPriorBook(TRACK_ID, 3L, 53L);
        assertTrue(prior.published());
        assertTrue(prior.json().contains("补齐差异"));

        assertFalse(service.loadTeamTrackPriorBook(TRACK_ID, 3L, 52L).published());
        assertFalse(service.loadTeamTrackPriorBook(TRACK_ID, null, 53L).published());
    }

    @Test
    void latestTeamTrackOfficialSkipsZeroScore() {
        AiScoringSession skip = boundSession(49L, "skip-docket");
        skip.setTeamId(3L);
        skip.setTrackId(TRACK_ID);
        AiScoringSession scored = boundSession(52L, "green-docket");
        scored.setTeamId(3L);
        scored.setTrackId(TRACK_ID);
        when(sessionMapper.selectList(any())).thenReturn(java.util.List.of(skip, scored));
        when(runMapper.selectOne(any())).thenReturn(
                completedRun("skip-docket", 1, 49L, BigDecimal.ZERO),
                completedRun("green-docket", 3, 52L, new BigDecimal("43.20"))
        );
        assertEquals(0, new BigDecimal("43.20").compareTo(
                service.latestTeamTrackOfficialScore(TRACK_ID, 3L, 53L)));
    }

    private static AiScoringSession unboundSession(Long id) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setTrackId(TRACK_ID);
        session.setRubricInternalVersion(RULE_VERSION);
        session.setRubricHash(RULE_HASH);
        return session;
    }

    private static AiScoringSession boundSession(Long id, String docketId) {
        AiScoringSession session = unboundSession(id);
        session.setDocketId(docketId);
        return session;
    }

    private static AiScoreReport report(Long id, BigDecimal score, String dimensionsJson) {
        AiScoreReport report = new AiScoreReport();
        report.setId(id);
        report.setOverallScore(score);
        report.setDimensionsJson(dimensionsJson);
        return report;
    }

    private static AiScoreDocketRun completedRun(String docketId, int runIndex, Long sessionId, BigDecimal score) {
        AiScoreDocketRun run = new AiScoreDocketRun();
        run.setDocketId(docketId);
        run.setRunIndex(runIndex);
        run.setSessionId(sessionId);
        run.setOfficialScore(score);
        run.setStatus("completed");
        return run;
    }

    private String expectedDocketId(String videoSha256) {
        DocketIdentity identity = new DocketIdentity();
        identity.setVideoSha256(videoSha256);
        identity.setRuleVersion(RULE_VERSION);
        identity.setRuleHash(RULE_HASH);
        identity.setContractVersion(AiScoreDocketService.DEFAULT_CONTRACT_VERSION);
        identity.setTrackId(TRACK_ID);
        return docketIdService.docketId(identity);
    }
}
