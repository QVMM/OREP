package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.DocketStability;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreDocketRun;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoringSessionReportDetailTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    @Test
    void reportBySessionReturnsStructuredDetailsAndRecoverySummary() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        when(sessionMapper.selectById(101L)).thenReturn(session());
        when(reportMapper.selectById(55L)).thenReturn(report());
        when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(observation()));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(
                currentDeduction(),
                recoveryDeduction()
        ));
        when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor()));

        AiScoreReportUserResponse response = service(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper
        ).reportBySession(101L);

        assertThat(response.getStructuredObservations()).hasSize(1);
        assertThat(response.getStructuredObservations().getFirst().getDimensionName()).isEqualTo("技术能力");
        assertThat(response.getStructuredObservations().getFirst().getEvidenceAnchorIds()).containsExactly(10L, 11L);
        assertThat(response.getStructuredDeductions()).hasSize(2);
        assertThat(response.getStructuredDeductions().get(0).getRecovery()).isFalse();
        assertThat(response.getStructuredDeductions().get(0).getDimensionName()).isEqualTo("技术能力");
        assertThat(response.getStructuredDeductions().get(1).getRecovery()).isTrue();
        assertThat(response.getStructuredDeductions().get(1).getRecoveredPoints()).isEqualByComparingTo("6");
        assertThat(response.getEvidenceAnchors()).hasSize(1);
        assertThat(response.getEvidenceAnchors().getFirst().getEvidenceText()).contains("核心演示流程");
        assertThat(response.getScoreRecoverySummary().getRecoveredCount()).isEqualTo(1);
        assertThat(response.getScoreRecoverySummary().getRecoveredPoints()).isEqualByComparingTo("6");
        assertThat(response.getScoreRecoverySummary().getCurrentDeductedPoints()).isEqualByComparingTo("5");
        assertThat(response.getScoreRecoverySummary().getRecoverableScore()).isEqualByComparingTo("5");
        assertThat(response.getScoreRecoverySummary().getNewIssueCount()).isEqualTo(1);
        assertThat(response.getScoreRecoverySummary().getNotPerfectReasons()).contains("current_deductions");
        assertThat(response.getRuleEngineShadow().getLlmRawScore()).isEqualByComparingTo("88.50");
        assertThat(response.getRuleEngineShadow().getRuleEngineScore()).isEqualByComparingTo("82.00");
        assertThat(response.getRuleEngineShadow().getScoreDiff()).isEqualByComparingTo("-6.50");
        assertThat(response.getRuleEngineShadow().getDiffReasons()).containsExactly("score_diff_exceeds_10");
        assertThat(response.getRuleEngineShadow().getScoringFingerprint()).isEqualTo("fp-user-safe-101");
        assertThat(response.getTrainingTasks()).hasSize(1);
        assertThat(response.getTrainingTasks().getFirst().getTaskId()).isEqualTo("training-task-1");
        assertThat(response.getTrainingTasks().getFirst().getTitle()).contains("关键算法测试数据不足");
        assertThat(response.getTrainingTasks().getFirst().getCorrespondingDeduction()).isEqualTo("关键算法测试数据不足");
        assertThat(response.getTrainingTasks().getFirst().getTrainingAction()).isEqualTo("补充稳定性和准确率测试记录");
        assertThat(response.getTrainingTasks().getFirst().getOwnerRole()).isEqualTo("技术负责人");
        assertThat(response.getTrainingTasks().getFirst().getTimeSuggestion()).contains("下一轮复评前");
        assertThat(response.getTrainingTasks().getFirst().getAcceptanceCriteria()).isEqualTo("测试记录能证明核心演示稳定跑通");
        assertThat(response.getTrainingTasks().getFirst().getExpectedRecoverPoints()).isEqualByComparingTo("5");
        assertThat(response.getTrainingTasks().getFirst().getEvidenceAnchorIds()).containsExactly(10L);
        assertThat(response.getTrainingTasks().getFirst().getPriority()).isEqualTo("P0");
        assertThat(response.getTrainingTasks().getFirst().getObservationCode()).isEqualTo("obs-tech-demo");
        assertThat(response.getTrainingTasks().getFirst().getSourceIssueKey()).isEqualTo("score-deduction:obs-tech-demo");
        assertThat(response.getActionPlanJson()).contains("补充稳定性测试");
        assertThat(response.getActionPlan()).hasSize(1);
        assertThat(response.getActionPlan().getFirst().get("id")).isEqualTo("action-1");
        assertThat(response.getScoreProjectionJson()).contains("predictedScoreUpper");
        assertThat(response.getScoreProjection())
                .containsEntry("goalScore", 100)
                .containsEntry("predictedScoreLower", 61.0)
                .containsEntry("predictedScoreUpper", 67.5);
        assertThat(response.getContractVersion()).isEqualTo("ai-score-report-v3");
        assertThat(response.getTodoPortfolioStatus()).isEqualTo("complete");
        assertThat(response.getLossLedger()).hasSize(1);
        assertThat(response.getLossLedger().getFirst()).containsEntry("lossId", "loss-1");
        assertThat(response.getCoverageSummary())
                .containsEntry("lossItemCount", 1)
                .containsEntry("coverageRate", 1.0)
                .containsEntry("status", "complete");
        assertThat(response.getRemediationTasks()).hasSize(1);
        assertThat(response.getRemediationTasks().getFirst()).containsEntry("taskId", "task-1");
        assertThat(response.getTaskVerifications()).isEmpty();
        assertThat(response.getStability().getBand()).isEqualTo(StabilityBandCalculator.NOT_REVIEWED);
        assertThat(response.getStability().getRunCount()).isEqualTo(0);
        assertThat(response.getStability().getHeadline()).isEqualTo("尚未复评");
        assertThat(response.getStability().getRuns()).isEmpty();

        String responseJson = OBJECT_MAPPER.writeValueAsString(response);
        assertNoInternalFields(OBJECT_MAPPER.readTree(responseJson), responseJson);
        assertThat(responseJson)
                .doesNotContain("deduction-1")
                .doesNotContain("previous-demo-failure")
                .doesNotContain("secret-rubric")
                .doesNotContain("prompt")
                .doesNotContain("weight");
    }

    @Test
    void userFacingDeductionsAreClampedToTheirActualScoreImpact() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreObservation observation = observation();
        observation.setRawScore(new BigDecimal("1.5"));
        observation.setScoreCap(new BigDecimal("1.5"));
        AiScoreDeduction deduction = currentDeduction();
        deduction.setDeductedPoints(new BigDecimal("2"));
        deduction.setMaxRecoverablePoints(new BigDecimal("2"));

        when(sessionMapper.selectById(101L)).thenReturn(session());
        when(reportMapper.selectById(55L)).thenReturn(report());
        when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(observation));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(deduction));
        when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());

        AiScoreReportUserResponse response = service(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper
        ).reportBySession(101L);

        assertThat(response.getStructuredDeductions().getFirst().getDeductedPoints())
                .isEqualByComparingTo("1.5");
        assertThat(response.getStructuredDeductions().getFirst().getMaxRecoverablePoints())
                .isEqualByComparingTo("1.5");
        assertThat(response.getScoreRecoverySummary().getCurrentDeductedPoints())
                .isEqualByComparingTo("1.5");
        assertThat(response.getScoreRecoverySummary().getRecoverableScore())
                .isEqualByComparingTo("1.5");
        assertThat(response.getTrainingTasks().getFirst().getExpectedRecoverPoints())
                .isEqualByComparingTo("1.5");
    }

    @Test
    void reportBySessionExposesStabilityWithoutInternalRunFields() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoringSession session = session();
        session.setDocketId("ab".repeat(32));
        when(sessionMapper.selectById(101L)).thenReturn(session);
        when(reportMapper.selectById(55L)).thenReturn(report());

        AiScoreDocketRun first = new AiScoreDocketRun();
        first.setRunIndex(1);
        first.setOfficialScore(new BigDecimal("80"));
        first.setScoreDeltaAbs(BigDecimal.ZERO);
        first.setSessionId(101L);
        first.setDimensionScoresJson("{\"secret\":true}");
        AiScoreDocketRun second = new AiScoreDocketRun();
        second.setRunIndex(2);
        second.setSessionId(202L);
        second.setOfficialScore(new BigDecimal("84"));
        second.setScoreDeltaAbs(new BigDecimal("4"));
        DocketStability snapshot = new DocketStability();
        snapshot.setBand(StabilityBandCalculator.RED);
        snapshot.setRunCount(2);
        snapshot.setRuns(List.of(first, second));
        when(docketService.stabilitySnapshot("ab".repeat(32))).thenReturn(snapshot);

        AiScoringSessionService scoringService = service(
                sessionMapper,
                reportMapper,
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class)
        );
        scoringService.setDocketService(docketService);

        AiScoreReportUserResponse response = scoringService.reportBySession(101L);
        assertThat(response.getStability().getBand()).isEqualTo(StabilityBandCalculator.RED);
        assertThat(response.getStability().getRunCount()).isEqualTo(2);
        assertThat(response.getStability().getHeadline()).isEqualTo("本场不稳定，请教师复核");
        assertThat(response.getStability().getThisRunIndex()).isEqualTo(1);
        assertThat(response.getStability().getNewerSessionId()).isEqualTo(202L);
        assertThat(response.getStability().getNewerRunIndex()).isEqualTo(2);
        assertThat(response.getStability().getRuns()).hasSize(2);
        assertThat(response.getStability().getRuns().getFirst().getRunIndex()).isEqualTo(1);
        assertThat(response.getStability().getRuns().getFirst().getOfficialScore()).isEqualByComparingTo("80");
        assertThat(response.getStability().getRuns().get(1).getScoreDeltaAbs()).isEqualByComparingTo("4");
        assertThat(response.getScoreGap()).isNotNull();
        assertThat(response.getScoreGap().getOfficialScore()).isEqualByComparingTo("95");
        assertThat(response.getScoreGap().getClosureRate()).isNull();
        assertThat(response.getScoreGap().getDeltaFromLast()).isNull();
        assertThat(response.getCoverageSummary()).containsEntry("coverageRate", 1.0);
        assertThat(response.getScoreGap().getClosureRate()).isNotEqualTo(BigDecimal.ONE);

        String responseJson = OBJECT_MAPPER.writeValueAsString(response);
        assertThat(responseJson).doesNotContain("dimensionScoresJson");
        assertThat(responseJson).doesNotContain("secret");
        assertThat(responseJson).doesNotContain("已经很准");
        assertNoInternalFields(OBJECT_MAPPER.readTree(responseJson), responseJson);
    }

    @Test
    void malformedActionPlanJsonReturnsEmptyParsedPlanWithoutBreakingReport() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreReport report = report();
        report.setActionPlanJson("[{broken");
        report.setScoreProjectionJson("{broken");
        when(sessionMapper.selectById(101L)).thenReturn(session());
        when(reportMapper.selectById(55L)).thenReturn(report);
        when(observationMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());
        when(anchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of());

        AiScoreReportUserResponse response = service(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper
        ).reportBySession(101L);

        assertThat(response.getActionPlanJson()).isEqualTo("[{broken");
        assertThat(response.getActionPlan()).isEmpty();
        assertThat(response.getScoreProjectionJson()).isEqualTo("{broken");
        assertThat(response.getScoreProjection()).isEmpty();
    }

    @Test
    void reportExposesUserSafePlaybackMetadataForItsRealVideoAsset() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreMediaAssetService mediaService = mock(AiScoreMediaAssetService.class);
        when(sessionMapper.selectById(101L)).thenReturn(session());
        when(reportMapper.selectById(55L)).thenReturn(report());
        AiScoreMediaAsset asset = new AiScoreMediaAsset();
        asset.setId(77L);
        asset.setMimeType("video/mp4");
        asset.setSizeBytes(496000000L);
        asset.setDurationSeconds(3270.592);
        when(mediaService.getVideoAssetBySession(101L)).thenReturn(asset);

        AiScoreReportUserResponse response = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                null,
                null,
                null,
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null,
                null,
                mediaService
        ).reportBySession(101L);

        assertThat(response.getMediaPlayback().getAssetId()).isEqualTo(77L);
        assertThat(response.getMediaPlayback().getContentType()).isEqualTo("video/mp4");
        assertThat(response.getMediaPlayback().getSizeBytes()).isEqualTo(496000000L);
        assertThat(response.getMediaPlayback().getDurationSeconds()).isEqualTo(3270.592);
        assertThat(response.getMediaPlayback().getStreamUrl())
                .isEqualTo("/api/ai-score/sessions/101/media/video");
        assertThat(OBJECT_MAPPER.writeValueAsString(response)).doesNotContain("filePath");
    }

    @Test
    void reportExposesRealTranscriptSegmentsWithCorrectedSpeakerDisplay() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreTranscriptService transcriptService = mock(AiScoreTranscriptService.class);
        AiScoreSpeakerIdentityService identityService = mock(AiScoreSpeakerIdentityService.class);
        when(sessionMapper.selectById(101L)).thenReturn(session());
        when(reportMapper.selectById(55L)).thenReturn(report());

        AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
        segment.setId(12L);
        segment.setSegmentNo(1);
        segment.setStartMs(1250L);
        segment.setEndMs(3750L);
        segment.setText("我们展示核心算法");
        segment.setSpeakerLabel("SPEAKER_2");
        segment.setConfidence(new BigDecimal("0.8700"));
        when(transcriptService.listForSession(101L)).thenReturn(List.of(segment));

        AiScoreSpeakerIdentity identity = new AiScoreSpeakerIdentity();
        identity.setRawSpeakerLabel("SPEAKER_2");
        identity.setDisplayName("3号选手");
        identity.setRoleName("AI算法工程师");
        identity.setStatus("CONFIRMED");
        identity.setRevision(2);
        when(identityService.listForSession(101L)).thenReturn(List.of(identity));

        AiScoreReportUserResponse response = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                null,
                null,
                null,
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null,
                null,
                null,
                transcriptService,
                identityService
        ).reportBySession(101L);

        assertThat(response.getAsrSegments()).hasSize(1);
        assertThat(response.getAsrSegments().getFirst().getStartMs()).isEqualTo(1250L);
        assertThat(response.getAsrSegments().getFirst().getEndMs()).isEqualTo(3750L);
        assertThat(response.getAsrSegments().getFirst().getRawSpeaker()).isEqualTo("SPEAKER_2");
        assertThat(response.getAsrSegments().getFirst().getSpeakerName()).isEqualTo("3号选手");
        assertThat(response.getAsrSegments().getFirst().getRoleName()).isEqualTo("AI算法工程师");
        assertThat(response.getSpeakerMappings()).hasSize(1);
        assertThat(response.getSpeakerMappings().getFirst().getRevision()).isEqualTo(2);

        String responseJson = OBJECT_MAPPER.writeValueAsString(response);
        JsonNode firstSegment = OBJECT_MAPPER.readTree(responseJson).path("asrSegments").get(0);
        assertThat(firstSegment.has("segmentHash")).isFalse();
        assertThat(firstSegment.has("sourceType")).isFalse();
    }

    @Test
    void reportExposesFinalStablePeopleAndSafeUnknownOverlapSegments() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreTranscriptService transcriptService = mock(AiScoreTranscriptService.class);
        AiScoreSpeakerIdentityService identityService = mock(AiScoreSpeakerIdentityService.class);
        AiScoringSession finalSession = session();
        finalSession.setSpeakerAttributionStatus("FINAL");
        finalSession.setSpeakerAttributionRevision(7);
        when(sessionMapper.selectById(101L)).thenReturn(finalSession);
        when(reportMapper.selectById(55L)).thenReturn(report());

        AiScoreSpeakerIdentity contestantTwo = stablePerson("CONTESTANT_2", "CONTESTANT", 2, "2号选手", "产品负责人");
        AiScoreSpeakerIdentity visitor = stablePerson("VISITOR_1", "VISITOR", null, "现场指导老师", null);
        AiScoreSpeakerIdentity offscreen = stablePerson("OFFSCREEN_1", "OFFSCREEN", null, null, null);
        AiScoreSpeakerIdentity contestantOne = stablePerson("CONTESTANT_1", "CONTESTANT", 1, "1号选手", "主讲人");
        when(identityService.listForSession(101L)).thenReturn(List.of(
                contestantTwo, visitor, offscreen, contestantOne
        ));

        AiScoreTranscriptSegment confirmed = finalSegment("seg-1", 1, 0L, 1200L, "各位评委好。", "CONTESTANT_1", "CONFIRMED");
        AiScoreTranscriptSegment unknown = finalSegment("seg-2", 2, 1200L, 2000L, "听不清是谁。", null, "UNKNOWN");
        AiScoreTranscriptSegment overlap = finalSegment("seg-3", 3, 2000L, 2600L, "多人同时回应。", null, "OVERLAP");
        when(transcriptService.listForSession(101L)).thenReturn(List.of(confirmed, unknown, overlap));

        AiScoreReportUserResponse response = new AiScoringSessionService(
                sessionMapper, reportMapper, null, null, null,
                mock(RubricResolverService.class), mock(ScoringFingerprintService.class),
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()),
                null, null, null, transcriptService, identityService
        ).reportBySession(101L);

        assertThat(response.getSpeakerAttributionStatus()).isEqualTo("FINAL");
        assertThat(response.getSpeakerAttributionRevision()).isEqualTo(7);
        assertThat(response.getStablePeople()).extracting(AiScoreReportUserResponse.StablePerson::getPersonId)
                .containsExactly("CONTESTANT_1", "CONTESTANT_2", "VISITOR_1", "OFFSCREEN_1");
        assertThat(response.getStablePeople()).extracting(AiScoreReportUserResponse.StablePerson::getPersonTypeLabel)
                .containsExactly("参赛选手", "参赛选手", "外部人员", "画外人员");
        assertThat(response.getFinalSpeakerSegments()).hasSize(3);
        assertThat(response.getFinalSpeakerSegments().get(0).getPersonId()).isEqualTo("CONTESTANT_1");
        assertThat(response.getFinalSpeakerSegments().get(0).getSpeakerName()).isEqualTo("1号选手");
        assertThat(response.getFinalSpeakerSegments().get(1).getPersonId()).isNull();
        assertThat(response.getFinalSpeakerSegments().get(1).getSpeakerName()).isEqualTo("发言人待确认");
        assertThat(response.getFinalSpeakerSegments().get(2).getPersonId()).isNull();
        assertThat(response.getFinalSpeakerSegments().get(2).getSpeakerName()).isEqualTo("多人同时发言");
        assertThat(OBJECT_MAPPER.writeValueAsString(response))
                .doesNotContain("voiceClusterIds")
                .doesNotContain("candidatePersonIds");
    }

    private AiScoreSpeakerIdentity stablePerson(
            String personId,
            String personType,
            Integer slot,
            String displayName,
            String roleName
    ) {
        AiScoreSpeakerIdentity identity = new AiScoreSpeakerIdentity();
        identity.setPersonId(personId);
        identity.setPersonType(personType);
        identity.setContestantSlot(slot);
        identity.setDisplayName(displayName);
        identity.setRoleName(roleName);
        identity.setPersonState("STABLE");
        identity.setConfidence(new BigDecimal("0.9200"));
        identity.setFirstSeenMs(0L);
        identity.setLastSeenMs(3000L);
        return identity;
    }

    private AiScoreTranscriptSegment finalSegment(
            String uid,
            int number,
            long startMs,
            long endMs,
            String text,
            String personId,
            String state
    ) {
        AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
        segment.setSegmentUid(uid);
        segment.setSegmentNo(number);
        segment.setAttributionRevision(7);
        segment.setStartMs(startMs);
        segment.setEndMs(endMs);
        segment.setText(text);
        segment.setPersonId(personId);
        segment.setSpeakerState(state);
        segment.setSpeakerConfidence(new BigDecimal("0.9100"));
        segment.setIsFinal(true);
        return segment;
    }

    private AiScoringSessionService service(
            AiScoringSessionMapper sessionMapper,
            AiScoreReportMapper reportMapper,
            AiScoreObservationMapper observationMapper,
            AiScoreDeductionMapper deductionMapper,
            AiScoreEvidenceAnchorMapper anchorMapper
    ) {
        return new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class)
        );
    }

    private AiScoringSession session() {
        AiScoringSession session = new AiScoringSession();
        session.setId(101L);
        session.setSessionNo("SC-20260624102500001");
        session.setReportId(55L);
        session.setTrackName("新一代信息技术赛道");
        session.setSourceType("uploaded_video");
        return session;
    }

    private AiScoreReport report() {
        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setSessionId(101L);
        report.setOverallScore(new BigDecimal("95"));
        report.setActionPlanJson("[{\"id\":\"action-1\",\"taskId\":\"task-1\",\"title\":\"补充稳定性测试\",\"acceptance\":\"连续五次通过\",\"coveredLossIds\":[\"loss-1\"]}]");
        report.setLossLedgerJson("[{\"lossId\":\"loss-1\",\"lossKey\":\"rule:O1:performance\",\"points\":5.0}]");
        report.setCoverageSummaryJson("{\"lossItemCount\":1,\"remediationTaskCount\":1,\"coverageRate\":1.0,\"status\":\"complete\"}");
        report.setScoreProjectionJson("{\"goalScore\":100,\"predictedScoreLower\":61.0,\"predictedScoreUpper\":67.5}");
        report.setContractVersion("ai-score-report-v3");
        report.setTodoPortfolioStatus("complete");
        report.setScoreCalibrationJson("{\"notPerfectReasons\":[\"current_deductions\"]}");
        report.setStructuredResultJson("""
                {
                  "llmRawScore": 88.5,
                  "ruleEngineScore": 82,
                  "scoreDiff": -6.5,
                  "diffReasons": ["score_diff_exceeds_10"],
                  "ruleEngineVersion": "internal-rule-engine-v1",
                  "scoringFingerprint": "fp-user-safe-101"
                }
                """);
        report.setStatus("completed");
        return report;
    }

    private AiScoreObservation observation() {
        AiScoreObservation observation = new AiScoreObservation();
        observation.setId(1L);
        observation.setObservationCode("obs-tech-demo");
        observation.setDimensionCode("technology");
        observation.setDimensionName("技术能力");
        observation.setRawScore(new BigDecimal("90"));
        observation.setScoreCap(new BigDecimal("95"));
        observation.setEvidenceLevel("strong");
        observation.setConfidence(new BigDecimal("0.91"));
        observation.setValidityStatus("valid");
        observation.setModelReason("现场演示证据充分");
        observation.setEvidenceAnchorIdsJson("[10,11]");
        return observation;
    }

    private AiScoreDeduction currentDeduction() {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setId(2L);
        deduction.setDeductionId("deduction-1");
        deduction.setObservationCode("obs-tech-demo");
        deduction.setDimensionCode("technology");
        deduction.setDeductedPoints(new BigDecimal("5"));
        deduction.setRecoveredPoints(BigDecimal.ZERO);
        deduction.setReason("关键算法测试数据不足");
        deduction.setRequiredFix("补充稳定性和准确率测试记录");
        deduction.setAcceptanceCriteria("测试记录能证明核心演示稳定跑通");
        deduction.setMaxRecoverablePoints(new BigDecimal("5"));
        deduction.setEvidenceLevel("medium");
        deduction.setConfidence(new BigDecimal("0.80"));
        deduction.setEvidenceAnchorIdsJson("[10]");
        deduction.setStatus("new");
        return deduction;
    }

    private AiScoreDeduction recoveryDeduction() {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setId(3L);
        deduction.setDeductionId("recovery-previous-demo-failure");
        deduction.setObservationCode("obs-tech-demo");
        deduction.setDimensionCode("technology");
        deduction.setDeductedPoints(BigDecimal.ZERO);
        deduction.setRecoveredPoints(new BigDecimal("6"));
        deduction.setReason("上一轮扣分项已提交恢复证据并通过本轮验收");
        deduction.setRequiredFix("保持已恢复项的支撑材料完整可追溯");
        deduction.setAcceptanceCriteria("本轮视频显示核心演示流程稳定跑通");
        deduction.setMaxRecoverablePoints(new BigDecimal("6"));
        deduction.setEvidenceLevel("medium");
        deduction.setConfidence(new BigDecimal("0.80"));
        deduction.setEvidenceAnchorIdsJson("[11]");
        deduction.setRecoverySourceDeductionId("previous-demo-failure");
        deduction.setStatus("fixed");
        return deduction;
    }

    private AiScoreEvidenceAnchor anchor() {
        AiScoreEvidenceAnchor anchor = new AiScoreEvidenceAnchor();
        anchor.setId(10L);
        anchor.setSessionId(101L);
        anchor.setAnchorType("frame_ocr");
        anchor.setAnchorTitle("核心演示流程");
        anchor.setEvidenceText("本轮视频显示核心演示流程稳定跑通");
        anchor.setSourceRef("00:02:10-00:02:45");
        anchor.setStartMs(130000L);
        anchor.setEndMs(165000L);
        anchor.setConfidence(new BigDecimal("0.92"));
        anchor.setValidityStatus("valid");
        return anchor;
    }

    private void assertNoInternalFields(JsonNode node, String responseJson) {
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String key = field.getKey().toLowerCase();
                assertThat(key)
                        .describedAs(responseJson)
                        .doesNotContain("rubric")
                        .doesNotContain("prompt")
                        .doesNotContain("weight")
                        .doesNotContain("internal")
                        .doesNotContain("engineversion");
                assertNoInternalFields(field.getValue(), responseJson);
            }
        } else if (node.isArray()) {
            for (JsonNode child : node) {
                assertNoInternalFields(child, responseJson);
            }
        }
    }
}
