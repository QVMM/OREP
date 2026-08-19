package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.DocketIdentity;
import com.orep.backend.dto.DocketStability;
import com.orep.backend.entity.AiScoreDocket;
import com.orep.backend.entity.AiScoreDocketRun;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDocketMapper;
import com.orep.backend.mapper.AiScoreDocketRunMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
public class AiScoreDocketService {
    public static final String DEFAULT_CONTRACT_VERSION = "ai-score-report-v3";
    private static final ObjectMapper JSON = new ObjectMapper();

    private final AiScoringSessionMapper sessionMapper;
    private final AiScoreDocketMapper docketMapper;
    private final DocketIdService docketIdService;
    private final AiScoreDocketRunMapper runMapper;

    public AiScoreDocketService(AiScoringSessionMapper sessionMapper,
                                AiScoreDocketMapper docketMapper,
                                DocketIdService docketIdService,
                                AiScoreDocketRunMapper runMapper) {
        this.sessionMapper = sessionMapper;
        this.docketMapper = docketMapper;
        this.docketIdService = docketIdService;
        this.runMapper = runMapper;
    }

    public String bindAfterVideoHash(Long sessionId, String videoSha256) {
        if (videoSha256 == null || videoSha256.isBlank()) {
            return null;
        }
        AiScoringSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new IllegalArgumentException("评分会话不存在");
        }
        if (!isBlank(session.getDocketId())) {
            return session.getDocketId();
        }
        if (isBlank(session.getRubricInternalVersion())) {
            throw new IllegalArgumentException("ruleVersion cannot be blank");
        }
        if (isBlank(session.getRubricHash())) {
            throw new IllegalArgumentException("ruleHash cannot be blank");
        }
        if (isBlank(session.getTrackId())) {
            throw new IllegalArgumentException("trackId cannot be blank");
        }

        DocketIdentity identity = new DocketIdentity();
        identity.setVideoSha256(videoSha256.trim().toLowerCase(Locale.ROOT));
        identity.setRuleVersion(session.getRubricInternalVersion().trim());
        identity.setRuleHash(session.getRubricHash().trim().toLowerCase(Locale.ROOT));
        identity.setContractVersion(DEFAULT_CONTRACT_VERSION);
        identity.setTrackId(session.getTrackId().trim());

        String docketId = docketIdService.docketId(identity);
        AiScoreDocket existing = findExisting(docketId, identity);
        if (existing == null) {
            existing = insertOrFind(docketId, identity);
        }
        session.setDocketId(existing.getDocketId());
        sessionMapper.updateById(session);
        return existing.getDocketId();
    }

    public AiScoreDocketRun recordSuccessfulRun(AiScoringSession session, AiScoreReport report) {
        return recordSuccessfulRun(session, report, null);
    }

    public AiScoreDocketRun recordSuccessfulRun(
            AiScoringSession session,
            AiScoreReport report,
            RunCoverageCalculator.Rates coverage
    ) {
        if (session == null || report == null) {
            throw new IllegalArgumentException("session and report are required when recording a successful run");
        }
        if (isBlank(session.getDocketId())) {
            throw new IllegalArgumentException("docketId cannot be blank when recording a successful run");
        }

        AiScoreDocketRun existing = findRunBySessionId(session.getId());
        if (existing != null) {
            return existing;
        }

        int runIndex = nextRunIndex(session.getDocketId());
        BigDecimal thisScore = report.getOverallScore();
        BigDecimal scoreDeltaAbs = BigDecimal.ZERO;
        if (runIndex != 1 && thisScore != null) {
            BigDecimal firstSuccessfulScore = firstSuccessfulOfficialScore(session.getDocketId());
            if (firstSuccessfulScore != null) {
                scoreDeltaAbs = thisScore.subtract(firstSuccessfulScore).abs();
            }
        }
        BigDecimal transcriptCoverage = coverage == null ? null : coverage.transcriptCoverage;
        BigDecimal seekableAnchorRate = coverage == null ? null : coverage.seekableAnchorRate;
        BigDecimal dimRatio = DimensionScoreDelta.maxRatio(
                firstSuccessfulDimensionJson(session.getDocketId()),
                report.getDimensionsJson()
        );

        AiScoreDocketRun row = new AiScoreDocketRun();
        row.setDocketId(session.getDocketId());
        row.setRunIndex(runIndex);
        row.setSessionId(session.getId());
        row.setReportId(report.getId());
        row.setOfficialScore(thisScore);
        row.setDimensionScoresJson(report.getDimensionsJson());
        row.setTranscriptCoverage(transcriptCoverage);
        row.setSeekableAnchorRate(seekableAnchorRate);
        row.setScoreDeltaAbs(scoreDeltaAbs);
        row.setTapeGrounded(tapeGroundedFrom(report));
        row.setStabilityBand(StabilityBandCalculator.band(
                runIndex,
                maxAbsDelta(session.getDocketId(), scoreDeltaAbs),
                minSeekable(session.getDocketId(), seekableAnchorRate),
                maxDimRatio(session.getDocketId(), dimRatio)
        ));
        row.setStatus("completed");
        row.setCreatedAt(LocalDateTime.now());
        try {
            runMapper.insert(row);
            return row;
        } catch (DuplicateKeyException ex) {
            AiScoreDocketRun raced = findRunBySessionId(session.getId());
            if (raced != null) {
                return raced;
            }
            throw ex;
        }
    }

    public boolean hasSuccessfulRun(Long sessionId) {
        return findRunBySessionId(sessionId) != null;
    }

    public void updatePublishedTaskBookJson(String docketId, String json) {
        if (isBlank(docketId) || isBlank(json)) {
            return;
        }
        AiScoreDocket docket = docketMapper.selectById(docketId);
        if (docket == null || !Boolean.TRUE.equals(docket.getTaskBookPublished())) {
            return;
        }
        docket.setTaskBookJson(json);
        docketMapper.updateById(docket);
    }

    public void persistPublishedTaskBook(String docketId, Long sessionId, String json) {
        if (isBlank(docketId) || isBlank(json)) {
            return;
        }
        AiScoreDocket docket = docketMapper.selectById(docketId);
        if (docket == null) {
            return;
        }
        docket.setTaskBookPublished(true);
        docket.setTaskBookJson(json);
        docket.setTaskBookPublishedSessionId(sessionId);
        docket.setTaskBookPublishedAt(LocalDateTime.now());
        docketMapper.updateById(docket);
    }

    public DocketTaskBook.Snapshot loadTeamTrackPriorBook(String trackId, Long teamId, Long currentSessionId) {
        if (isBlank(trackId) || teamId == null || currentSessionId == null) {
            return DocketTaskBook.Snapshot.unpublished();
        }
        List<AiScoringSession> sessions = sessionMapper.selectList(new LambdaQueryWrapper<AiScoringSession>()
                .eq(AiScoringSession::getTeamId, teamId)
                .eq(AiScoringSession::getTrackId, trackId)
                .lt(AiScoringSession::getId, currentSessionId)
                .isNotNull(AiScoringSession::getDocketId)
                .orderByDesc(AiScoringSession::getId));
        java.util.LinkedHashSet<String> seen = new java.util.LinkedHashSet<>();
        for (AiScoringSession session : sessions == null ? List.<AiScoringSession>of() : sessions) {
            if (session == null || isBlank(session.getDocketId()) || !seen.add(session.getDocketId())) {
                continue;
            }
            DocketTaskBook.Snapshot snapshot = loadPublishedTaskBook(session.getDocketId());
            if (snapshot.published()
                    && snapshot.publishedSessionId() != null
                    && snapshot.publishedSessionId() < currentSessionId) {
                return snapshot;
            }
        }
        return DocketTaskBook.Snapshot.unpublished();
    }

    public BigDecimal latestTeamTrackOfficialScore(String trackId, Long teamId, Long currentSessionId) {
        if (isBlank(trackId) || teamId == null || currentSessionId == null) {
            return null;
        }
        List<AiScoringSession> sessions = sessionMapper.selectList(new LambdaQueryWrapper<AiScoringSession>()
                .eq(AiScoringSession::getTeamId, teamId)
                .eq(AiScoringSession::getTrackId, trackId)
                .lt(AiScoringSession::getId, currentSessionId)
                .orderByDesc(AiScoringSession::getId));
        for (AiScoringSession session : sessions == null ? List.<AiScoringSession>of() : sessions) {
            if (session == null) {
                continue;
            }
            AiScoreDocketRun run = findRunBySessionId(session.getId());
            if (run == null || run.getOfficialScore() == null) {
                continue;
            }
            if (run.getOfficialScore().compareTo(BigDecimal.ZERO) == 0) {
                continue;
            }
            return run.getOfficialScore();
        }
        return null;
    }

    public DocketTaskBook.Snapshot loadPublishedTaskBook(String docketId) {
        if (isBlank(docketId)) {
            return DocketTaskBook.Snapshot.unpublished();
        }
        AiScoreDocket docket = docketMapper.selectById(docketId);
        if (docket == null) {
            return DocketTaskBook.Snapshot.unpublished();
        }
        if (!Boolean.TRUE.equals(docket.getTaskBookPublished()) || isBlank(docket.getTaskBookJson())) {
            return DocketTaskBook.Snapshot.unpublished();
        }
        return new DocketTaskBook.Snapshot(true, docket.getTaskBookJson(), docket.getTaskBookPublishedSessionId());
    }

    public DocketStability stabilitySnapshot(String docketId) {
        DocketStability snapshot = new DocketStability();
        if (docketId == null || docketId.isBlank()) {
            snapshot.setBand(StabilityBandCalculator.NOT_REVIEWED);
            snapshot.setRunCount(0);
            return snapshot;
        }
        List<AiScoreDocketRun> runs = runMapper.selectList(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .eq(AiScoreDocketRun::getStatus, "completed")
                .orderByAsc(AiScoreDocketRun::getRunIndex));
        snapshot.setRuns(runs);
        snapshot.setRunCount(runs.size());
        snapshot.setBand(StabilityBandCalculator.band(
                runs.size(),
                maxAbsDelta(docketId, null),
                minSeekable(docketId, null),
                maxDimRatio(docketId, null)
        ));
        IdentityStability.Slice identity = IdentityStability.evaluate(runs);
        snapshot.setIdentityBand(identity.band);
        snapshot.setIdentityRunCount(identity.runCount);
        snapshot.setIdentityHeadline(identity.headline);
        return snapshot;
    }

    static Boolean tapeGroundedFrom(AiScoreReport report) {
        if (report == null || report.getStructuredResultJson() == null || report.getStructuredResultJson().isBlank()) {
            return null;
        }
        try {
            Map<?, ?> source = JSON.readValue(report.getStructuredResultJson(), Map.class);
            Object value = source.get("tapeGrounded");
            if (value instanceof Boolean flag) {
                return flag;
            }
            if (value instanceof String text) {
                if ("true".equalsIgnoreCase(text.trim())) {
                    return true;
                }
                if ("false".equalsIgnoreCase(text.trim())) {
                    return false;
                }
            }
        } catch (Exception ignored) {
            return null;
        }
        return null;
    }

    public AiScoreDocketRun previousCompletedRun(String docketId, Long currentSessionId) {
        if (docketId == null || docketId.isBlank()) {
            return null;
        }
        List<AiScoreDocketRun> runs = runMapper.selectList(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .eq(AiScoreDocketRun::getStatus, "completed")
                .orderByAsc(AiScoreDocketRun::getRunIndex));
        AiScoreDocketRun previous = null;
        for (AiScoreDocketRun run : runs == null ? List.<AiScoreDocketRun>of() : runs) {
            if (run == null) {
                continue;
            }
            if (currentSessionId != null && currentSessionId.equals(run.getSessionId())) {
                return previous;
            }
            previous = run;
        }
        return previous;
    }

    private BigDecimal maxAbsDelta(String docketId, BigDecimal incomingDelta) {
        BigDecimal max = incomingDelta;
        List<AiScoreDocketRun> prior = completedRuns(docketId);
        for (AiScoreDocketRun run : prior) {
            if (run.getScoreDeltaAbs() != null && (max == null || run.getScoreDeltaAbs().compareTo(max) > 0)) {
                max = run.getScoreDeltaAbs();
            }
        }
        return max;
    }

    private BigDecimal minSeekable(String docketId, BigDecimal incoming) {
        BigDecimal min = incoming;
        for (AiScoreDocketRun run : completedRuns(docketId)) {
            if (run.getSeekableAnchorRate() == null) {
                continue;
            }
            if (min == null || run.getSeekableAnchorRate().compareTo(min) < 0) {
                min = run.getSeekableAnchorRate();
            }
        }
        return min;
    }

    private BigDecimal maxDimRatio(String docketId, BigDecimal incoming) {
        BigDecimal max = incoming;
        AiScoreDocketRun first = firstCompletedRun(docketId);
        if (first == null) {
            return max;
        }
        for (AiScoreDocketRun run : completedRuns(docketId)) {
            if (run.getRunIndex() != null && run.getRunIndex() == 1) {
                continue;
            }
            BigDecimal ratio = DimensionScoreDelta.maxRatio(first.getDimensionScoresJson(), run.getDimensionScoresJson());
            if (ratio != null && (max == null || ratio.compareTo(max) > 0)) {
                max = ratio;
            }
        }
        return max;
    }

    private List<AiScoreDocketRun> completedRuns(String docketId) {
        return runMapper.selectList(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .eq(AiScoreDocketRun::getStatus, "completed"));
    }

    private String firstSuccessfulDimensionJson(String docketId) {
        AiScoreDocketRun first = firstCompletedRun(docketId);
        return first == null ? null : first.getDimensionScoresJson();
    }

    private AiScoreDocketRun firstCompletedRun(String docketId) {
        return runMapper.selectOne(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .eq(AiScoreDocketRun::getStatus, "completed")
                .orderByAsc(AiScoreDocketRun::getRunIndex)
                .last("LIMIT 1"));
    }

    public AiScoreDocketRun findRunBySessionId(Long sessionId) {
        if (sessionId == null) {
            return null;
        }
        return runMapper.selectOne(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getSessionId, sessionId)
                .last("LIMIT 1"));
    }

    private int nextRunIndex(String docketId) {
        AiScoreDocketRun latest = runMapper.selectOne(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .orderByDesc(AiScoreDocketRun::getRunIndex)
                .last("LIMIT 1"));
        if (latest == null || latest.getRunIndex() == null) {
            return 1;
        }
        return latest.getRunIndex() + 1;
    }

    private BigDecimal firstSuccessfulOfficialScore(String docketId) {
        AiScoreDocketRun first = runMapper.selectOne(new LambdaQueryWrapper<AiScoreDocketRun>()
                .eq(AiScoreDocketRun::getDocketId, docketId)
                .eq(AiScoreDocketRun::getStatus, "completed")
                .orderByAsc(AiScoreDocketRun::getRunIndex)
                .last("LIMIT 1"));
        return first == null ? null : first.getOfficialScore();
    }

    private AiScoreDocket insertOrFind(String docketId, DocketIdentity identity) {
        AiScoreDocket row = new AiScoreDocket();
        row.setDocketId(docketId);
        row.setVideoSha256(identity.getVideoSha256());
        row.setRuleVersion(identity.getRuleVersion());
        row.setRuleHash(identity.getRuleHash());
        row.setContractVersion(identity.getContractVersion());
        row.setTrackId(identity.getTrackId());
        row.setCreatedAt(LocalDateTime.now());
        try {
            docketMapper.insert(row);
            return row;
        } catch (DuplicateKeyException ex) {
            AiScoreDocket existing = findExisting(docketId, identity);
            if (existing == null) {
                throw ex;
            }
            return existing;
        }
    }

    private AiScoreDocket findExisting(String docketId, DocketIdentity identity) {
        AiScoreDocket byId = docketMapper.selectById(docketId);
        if (byId != null) {
            return byId;
        }
        return docketMapper.selectOne(new LambdaQueryWrapper<AiScoreDocket>()
                .eq(AiScoreDocket::getVideoSha256, identity.getVideoSha256())
                .eq(AiScoreDocket::getRuleVersion, identity.getRuleVersion())
                .eq(AiScoreDocket::getRuleHash, identity.getRuleHash())
                .eq(AiScoreDocket::getContractVersion, identity.getContractVersion())
                .eq(AiScoreDocket::getTrackId, identity.getTrackId())
                .last("LIMIT 1"));
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
