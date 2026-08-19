package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.entity.AiJudgeReport;
import com.orep.backend.entity.AiJuryAggregate;
import com.orep.backend.entity.AiJuryMember;
import com.orep.backend.entity.AiJurySession;
import com.orep.backend.mapper.AiJudgeReportMapper;
import com.orep.backend.mapper.AiJuryAggregateMapper;
import com.orep.backend.mapper.AiJuryMemberMapper;
import com.orep.backend.mapper.AiJurySessionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class AiJuryReviewService {
    private static final String PYTHON_REVIEW_VERSION = "python-jury-v1";
    private final AiScoringSessionService scoringSessionService;
    private final AiJudgePersonaService personaService;
    private final AiJuryPythonClient pythonClient;
    private final AiJurySessionMapper jurySessionMapper;
    private final AiJuryMemberMapper juryMemberMapper;
    private final AiJudgeReportMapper judgeReportMapper;
    private final AiJuryAggregateMapper aggregateMapper;
    private final ObjectMapper objectMapper;

    @Autowired
    public AiJuryReviewService(AiScoringSessionService scoringSessionService,
                               AiJudgePersonaService personaService,
                               AiJuryPythonClient pythonClient,
                               AiJurySessionMapper jurySessionMapper,
                               AiJuryMemberMapper juryMemberMapper,
                               AiJudgeReportMapper judgeReportMapper,
                               AiJuryAggregateMapper aggregateMapper,
                               ObjectMapper objectMapper) {
        this.scoringSessionService = scoringSessionService;
        this.personaService = personaService;
        this.pythonClient = pythonClient;
        this.jurySessionMapper = jurySessionMapper;
        this.juryMemberMapper = juryMemberMapper;
        this.judgeReportMapper = judgeReportMapper;
        this.aggregateMapper = aggregateMapper;
        this.objectMapper = objectMapper == null ? new ObjectMapper() : objectMapper;
    }

    public AiJuryReviewService(AiScoringSessionService scoringSessionService,
                               AiJudgePersonaService personaService,
                               AiJurySessionMapper jurySessionMapper,
                               AiJuryMemberMapper juryMemberMapper,
                               AiJudgeReportMapper judgeReportMapper,
                               AiJuryAggregateMapper aggregateMapper,
                               ObjectMapper objectMapper) {
        this(scoringSessionService, personaService, null, jurySessionMapper, juryMemberMapper, judgeReportMapper,
                aggregateMapper, objectMapper);
    }

    public AiJuryReviewUserResponse startForSession(Long sessionId) {
        AiScoreReportUserResponse base = scoringSessionService.reportBySession(sessionId);
        return startFromPython(base);
    }

    public AiJuryReviewUserResponse resultBySession(Long sessionId) {
        AiJurySession latest = latestBySession(sessionId);
        if (isPythonReview(latest)) {
            return toUserResponse(latest);
        }
        AiScoreReportUserResponse base = scoringSessionService == null ? null : scoringSessionService.reportBySession(sessionId);
        return resultFromPython(base, sessionId, latest == null ? null : latest.getMeetingId());
    }

    public AiJuryReviewUserResponse startForLatestMeeting(Long meetingId) {
        AiScoreReportUserResponse base = scoringSessionService.reportByMeetingId(meetingId);
        return startFromPython(base);
    }

    public AiJuryReviewUserResponse resultByLatestMeeting(Long meetingId) {
        AiJurySession latest = latestByMeeting(meetingId);
        if (isPythonReview(latest)) {
            return toUserResponse(latest);
        }
        AiScoreReportUserResponse base = scoringSessionService == null ? null : scoringSessionService.reportByMeetingId(meetingId);
        return resultFromPython(base, base == null ? null : base.getSessionId(), meetingId);
    }

    private AiJuryReviewUserResponse startFromPython(AiScoreReportUserResponse base) {
        if (base == null) {
            return emptyResponse(null, null, "当前评分会话暂未生成AI评分结果，无法启动评审团复核。");
        }
        AiJuryReviewUserResponse.DisputeReviewContext disputeContext = buildDisputeReviewContext(base);
        Map<String, Object> payload = pythonClient == null
                ? Map.of("status", "failed", "message", "Python评审团服务未配置")
                : pythonClient.startJuryReview(pythonResultKey(base), toPayload(disputeContext));
        AiJuryReviewUserResponse response = fromPythonPayload(payload, base);
        response.setDisputeReviewContext(firstContext(response.getDisputeReviewContext(), disputeContext));
        if (hasRealPythonResult(response)) {
            persistPythonReview(response, base, payload);
        } else {
            response = withoutUnverifiedMembers(response, base == null ? null : base.getSessionId(), base == null ? null : base.getMeetingId());
            response.setDisputeReviewContext(disputeContext);
        }
        return response;
    }

    private AiJuryReviewUserResponse resultFromPython(AiScoreReportUserResponse base, Long sessionId, Long meetingId) {
        Long resolvedMeetingId = base == null ? meetingId : base.getMeetingId();
        Long resultKey = base == null ? resolvedMeetingId : pythonResultKey(base);
        Map<String, Object> payload = pythonClient == null
                ? Map.of("status", "empty", "message", "评审团复核暂未生成")
                : pythonClient.getJuryResult(resultKey);
        AiJuryReviewUserResponse response = fromPythonPayload(payload, base);
        if (base != null) {
            response.setDisputeReviewContext(firstContext(response.getDisputeReviewContext(), buildDisputeReviewContext(base)));
        }
        if (response.getSessionId() == null) response.setSessionId(sessionId);
        if (response.getMeetingId() == null) response.setMeetingId(resolvedMeetingId);
        if (hasRealPythonResult(response) && base != null) {
            persistPythonReview(response, base, payload);
        } else if (!hasRealPythonResult(response)) {
            response = withoutUnverifiedMembers(response, sessionId, resolvedMeetingId);
            if (base != null) response.setDisputeReviewContext(buildDisputeReviewContext(base));
        }
        return response;
    }

    @SuppressWarnings("unchecked")
    private AiJuryReviewUserResponse fromPythonPayload(Map<String, Object> payload, AiScoreReportUserResponse base) {
        Map<String, Object> safePayload = payload == null ? Map.of() : payload;
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setJurySessionId(toLong(first(safePayload, "jury_session_id", "jurySessionId")));
        response.setSessionId(base == null ? null : base.getSessionId());
        response.setMeetingId(base == null ? toLong(first(safePayload, "meeting_id", "meetingId")) : base.getMeetingId());
        response.setStatus(safeStr(first(safePayload, "status")));
        if (response.getStatus().isBlank()) response.setStatus("empty");
        response.setReviewMode("复核层");
        response.setTrackName(base == null ? null : base.getTrackName());
        response.setOfficialScore(firstDecimal(
                base == null ? null : base.getOverallScore(),
                first(safePayload, "official_score", "officialScore"),
                BigDecimal.ZERO));

        Map<String, Object> jury = asMap(first(safePayload, "jury"));
        response.setJuryAverageScore(firstDecimal(
                first(jury, "trimmed_average_score", "trimmedAverageScore", "raw_average_score"),
                first(safePayload, "juryAverageScore"),
                null));
        response.setScoreDiffFromOfficial(firstDecimal(
                first(jury, "score_diff_from_official", "scoreDiffFromOfficial"),
                first(safePayload, "scoreDiffFromOfficial"),
                null));
        response.setJudgeCount(toInteger(first(safePayload, "judge_count", "judgeCount", "successful_count")));
        response.setSuccessfulCount(toInteger(first(jury, "successful_count", "successfulCount")));
        if (response.getSuccessfulCount() == null) {
            response.setSuccessfulCount(toInteger(first(safePayload, "successful_count", "successfulCount")));
        }
        response.setExplanation(safeStr(first(safePayload, "message", "error_message", "errorMessage")));
        if (response.getExplanation().isBlank()) {
            response.setExplanation(hasCompletedStatus(response.getStatus())
                    ? "AI评审团复核由 Python 评审团服务生成，基础AI评分不被修改。"
                    : "评审团复核暂未生成/生成失败。");
        }

        List<AiJuryReviewUserResponse.MemberReview> members = new ArrayList<>();
        for (Object memberPayload : asList(first(safePayload, "members"))) {
            Map<String, Object> memberMap = asMap(memberPayload);
            AiJuryReviewUserResponse.MemberReview member = toMemberReviewFromPython(memberMap, response.getOfficialScore());
            if (hasMemberContent(member)) {
                members.add(member);
            }
        }
        response.setMembers(members);
        if (response.getJudgeCount() == null && !members.isEmpty()) response.setJudgeCount(members.size());
        if (response.getSuccessfulCount() == null && !members.isEmpty()) {
            response.setSuccessfulCount((int) members.stream()
                    .filter(member -> member.getReferenceScore() != null)
                    .count());
        }
        if (response.getJuryAverageScore() == null && !members.isEmpty()) {
            response.setJuryAverageScore(averageScore(members));
        }
        if (response.getScoreDiffFromOfficial() == null
                && response.getJuryAverageScore() != null
                && response.getOfficialScore() != null) {
            response.setScoreDiffFromOfficial(response.getJuryAverageScore()
                    .subtract(response.getOfficialScore())
                    .setScale(1, RoundingMode.HALF_UP));
        } else if (response.getJuryAverageScore() != null && response.getOfficialScore() != null) {
            response.setScoreDiffFromOfficial(response.getJuryAverageScore()
                    .subtract(response.getOfficialScore())
                    .setScale(1, RoundingMode.HALF_UP));
        }

        response.setAggregate(toAggregateFromPython(asMap(first(safePayload, "aggregate"))));
        response.setDisputeReviewContext(toDisputeReviewContext(asMap(first(safePayload,
                "dispute_review_context", "disputeReviewContext"))));
        return response;
    }

    private Long pythonResultKey(AiScoreReportUserResponse base) {
        if (base == null) return null;
        return base.getMeetingId() == null ? base.getSessionId() : base.getMeetingId();
    }

    private AiJuryReviewUserResponse.MemberReview toMemberReviewFromPython(
            Map<String, Object> payload,
            BigDecimal officialScore
    ) {
        AiJuryReviewUserResponse.MemberReview member = new AiJuryReviewUserResponse.MemberReview();
        String code = safeStr(first(payload, "persona_code", "personaCode", "code"));
        member.setPersonaCode(code);
        member.setDisplayName(firstNonBlank(
                first(payload, "display_name", "displayName", "name"),
                first(payload, "role_label", "roleLabel"),
                code));
        member.setRoleLabel(firstNonBlank(first(payload, "role_label", "roleLabel"), member.getDisplayName()));
        member.setReferenceScore(firstDecimal(
                first(payload, "overall_score", "overallScore", "reference_score", "referenceScore", "score"),
                null));
        member.setStatus(safeStr(first(payload, "status")));
        if (member.getStatus().isBlank()) {
            member.setStatus(member.getReferenceScore() == null ? "failed" : "completed");
        }
        member.setScoreRelationToOfficial(scoreRelation(member.getReferenceScore(), officialScore));

        Map<String, Object> personaView = asMap(first(payload, "persona_view", "personaView"));
        member.setPerspectiveQuestions(firstList(
                first(payload, "perspective_questions", "perspectiveQuestions"),
                first(payload, "critical_issues", "criticalIssues"),
                first(personaView, "top_concerns", "topConcerns")));
        member.setExpressionRisks(firstList(
                first(payload, "expression_risks", "expressionRisks"),
                first(personaView, "expression_risks", "expressionRisks"),
                first(payload, "summary")));
        member.setTrainingSuggestions(firstList(
                first(payload, "training_suggestions", "trainingSuggestions"),
                first(payload, "improvement_priorities", "improvementPriorities")));
        member.setEvidenceConcerns(firstList(
                first(payload, "evidence_concerns", "evidenceConcerns"),
                first(payload, "critical_issues", "criticalIssues"),
                first(payload, "evidence_summary", "evidenceSummary")));
        return member;
    }

    private AiJuryReviewUserResponse.AggregateReview toAggregateFromPython(Map<String, Object> aggregatePayload) {
        AiJuryReviewUserResponse.AggregateReview aggregate = new AiJuryReviewUserResponse.AggregateReview();
        aggregate.setConsensusIssues(firstList(first(aggregatePayload, "consensus_issues", "consensusIssues")));
        aggregate.setDisagreementFocus(firstList(first(aggregatePayload, "dimension_stats", "dimensionStats", "disagreement_focus", "disagreementFocus")));
        aggregate.setNextTrainingPriorities(firstList(first(aggregatePayload, "next_training_priorities", "nextTrainingPriorities", "optimization_suggestions", "optimizationSuggestions")));
        return aggregate;
    }

    private void persistPythonReview(
            AiJuryReviewUserResponse response,
            AiScoreReportUserResponse base,
            Map<String, Object> rawPayload
    ) {
        if (jurySessionMapper == null || juryMemberMapper == null || judgeReportMapper == null || aggregateMapper == null) {
            return;
        }
        LocalDateTime now = LocalDateTime.now();
        Map<String, Map<String, Object>> personaByCode = personaByCode();

        AiJurySession session = new AiJurySession();
        session.setScoringSessionId(base.getSessionId());
        session.setMeetingId(base.getMeetingId());
        session.setBaseReportId(base.getReportId());
        session.setSeed("python-jury-" + safeStr(first(rawPayload, "jury_session_id", "jurySessionId")));
        session.setStandardVersion(PYTHON_REVIEW_VERSION);
        session.setPersonaPoolVersion("python");
        session.setJudgeCount(response.getJudgeCount());
        session.setStatus(response.getStatus());
        session.setOfficialScore(response.getOfficialScore());
        session.setJuryTrimmedAvg(response.getJuryAverageScore());
        session.setJuryRawAvg(firstDecimal(first(asMap(first(rawPayload, "jury")), "raw_average_score", "rawAverageScore"), response.getJuryAverageScore()));
        session.setHighestScore(firstDecimal(first(asMap(first(rawPayload, "jury")), "highest_score", "highestScore"), maxScore(response.getMembers())));
        session.setLowestScore(firstDecimal(first(asMap(first(rawPayload, "jury")), "lowest_score", "lowestScore"), minScore(response.getMembers())));
        session.setScoreDiffFromOfficial(response.getScoreDiffFromOfficial());
        session.setErrorMessage(safeStr(first(rawPayload, "error_message", "errorMessage")));
        session.setStartedAt(now);
        session.setCompletedAt(now);
        session.setCreatedAt(now);
        session.setUpdatedAt(now);
        jurySessionMapper.insert(session);

        AiJuryAggregate aggregate = new AiJuryAggregate();
        aggregate.setJurySessionId(session.getId());
        aggregate.setScoringSessionId(base.getSessionId());
        aggregate.setMeetingId(base.getMeetingId());
        aggregate.setOfficialScore(response.getOfficialScore());
        aggregate.setRawAverageScore(session.getJuryRawAvg());
        aggregate.setTrimmedAverageScore(response.getJuryAverageScore());
        aggregate.setConsensusIssuesJson(writeSafeJson(response.getAggregate().getConsensusIssues()));
        aggregate.setDimensionDisagreementJson(writeSafeJson(response.getAggregate().getDisagreementFocus()));
        aggregate.setOptimizationSuggestionsJson(writeSafeJson(response.getAggregate().getNextTrainingPriorities()));
        aggregate.setAggregateReportJson(writeSafeJson(rawPayload));
        aggregate.setCreatedAt(now);
        aggregateMapper.insert(aggregate);

        for (int i = 0; i < response.getMembers().size(); i++) {
            AiJuryReviewUserResponse.MemberReview member = response.getMembers().get(i);
            Map<String, Object> persona = personaByCode.getOrDefault(safeStr(member.getPersonaCode()).toUpperCase(), Map.of());

            AiJuryMember juryMember = new AiJuryMember();
            juryMember.setJurySessionId(session.getId());
            juryMember.setPersonaId(toLong(first(persona, "id")));
            juryMember.setPersonaCode(member.getPersonaCode());
            juryMember.setSeatNo(i + 1);
            juryMember.setDisplayName(member.getDisplayName());
            juryMember.setRoleLabel(member.getRoleLabel());
            juryMember.setCreatedAt(now);
            juryMemberMapper.insert(juryMember);

            AiJudgeReport report = new AiJudgeReport();
            report.setJurySessionId(session.getId());
            report.setMemberId(juryMember.getId());
            report.setScoringSessionId(base.getSessionId());
            report.setMeetingId(base.getMeetingId());
            report.setPersonaCode(member.getPersonaCode());
            report.setOverallScore(member.getReferenceScore());
            report.setReportJson(writeSafeJson(member));
            report.setStatus(firstNonBlank(member.getStatus(),
                    member.getReferenceScore() == null ? "failed" : "completed"));
            report.setStartedAt(now);
            report.setCompletedAt(now);
            report.setCreatedAt(now);
            report.setUpdatedAt(now);
            judgeReportMapper.insert(report);
        }
    }

    private AiJuryReviewUserResponse toUserResponse(AiJurySession session) {
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setJurySessionId(session.getId());
        response.setSessionId(session.getScoringSessionId());
        response.setMeetingId(session.getMeetingId());
        response.setStatus(session.getStatus());
        response.setReviewMode("复核层");
        response.setOfficialScore(valueOrZero(session.getOfficialScore()));
        response.setJuryAverageScore(session.getJuryTrimmedAvg());
        response.setScoreDiffFromOfficial(session.getScoreDiffFromOfficial());
        response.setJudgeCount(session.getJudgeCount());
        response.setExplanation("AI评审团复核由 Python 评审团服务生成，基础AI评分不被修改。");
        response.setCompletedAt(session.getCompletedAt());

        List<AiJudgeReport> reports = judgeReportMapper.selectList(
                new LambdaQueryWrapper<AiJudgeReport>()
                        .eq(AiJudgeReport::getJurySessionId, session.getId())
                        .orderByAsc(AiJudgeReport::getId));
        List<AiJuryReviewUserResponse.MemberReview> members = new ArrayList<>();
        for (AiJudgeReport report : reports) {
            members.add(toMemberReviewFromReport(report, session.getOfficialScore()));
        }
        response.setMembers(members);
        response.setSuccessfulCount((int) reports.stream()
                .filter(report -> "completed".equalsIgnoreCase(safeStr(report.getStatus()))
                        || (!hasText(report.getStatus()) && report.getOverallScore() != null))
                .count());

        AiJuryAggregate aggregate = aggregateMapper.selectOne(
                new LambdaQueryWrapper<AiJuryAggregate>()
                        .eq(AiJuryAggregate::getJurySessionId, session.getId())
                        .last("LIMIT 1"));
        response.setAggregate(toAggregateFromEntity(aggregate));
        response.setDisputeReviewContext(disputeContextFromAggregate(aggregate));
        return response;
    }

    private AiJuryReviewUserResponse.MemberReview toMemberReviewFromReport(AiJudgeReport report, BigDecimal officialScore) {
        AiJuryReviewUserResponse.MemberReview member = new AiJuryReviewUserResponse.MemberReview();
        member.setPersonaCode(report.getPersonaCode());
        member.setDisplayName(report.getPersonaCode());
        member.setRoleLabel(report.getPersonaCode());
        member.setStatus(firstNonBlank(report.getStatus(), report.getOverallScore() == null ? "failed" : "completed"));
        member.setReferenceScore(report.getOverallScore());
        member.setScoreRelationToOfficial(scoreRelation(report.getOverallScore(), officialScore));

        if (report.getReportJson() != null && !report.getReportJson().isBlank()) {
            try {
                @SuppressWarnings("unchecked")
                Map<String, Object> stored = objectMapper.readValue(report.getReportJson(), Map.class);
                if (stored.containsKey("displayName")) member.setDisplayName(safeStr(stored.get("displayName")));
                if (stored.containsKey("roleLabel")) member.setRoleLabel(safeStr(stored.get("roleLabel")));
                if (stored.containsKey("status")) member.setStatus(safeStr(stored.get("status")));
                if (stored.containsKey("perspectiveQuestions")) member.setPerspectiveQuestions(firstList(stored.get("perspectiveQuestions")));
                if (stored.containsKey("expressionRisks")) member.setExpressionRisks(firstList(stored.get("expressionRisks")));
                if (stored.containsKey("trainingSuggestions")) member.setTrainingSuggestions(firstList(stored.get("trainingSuggestions")));
                if (stored.containsKey("evidenceConcerns")) member.setEvidenceConcerns(firstList(stored.get("evidenceConcerns")));
            } catch (Exception ignored) {
            }
        }
        return member;
    }

    private AiJuryReviewUserResponse.AggregateReview toAggregateFromEntity(AiJuryAggregate entity) {
        AiJuryReviewUserResponse.AggregateReview aggregate = new AiJuryReviewUserResponse.AggregateReview();
        if (entity == null) return aggregate;
        aggregate.setConsensusIssues(parseStrList(entity.getConsensusIssuesJson()));
        aggregate.setDisagreementFocus(parseStrList(entity.getDimensionDisagreementJson()));
        aggregate.setNextTrainingPriorities(parseStrList(entity.getOptimizationSuggestionsJson()));
        return aggregate;
    }

    private AiJuryReviewUserResponse.DisputeReviewContext buildDisputeReviewContext(AiScoreReportUserResponse base) {
        AiJuryReviewUserResponse.DisputeReviewContext context = new AiJuryReviewUserResponse.DisputeReviewContext();
        context.setOfficialScore(base.getOverallScore());
        AiScoreReportUserResponse.RuleEngineShadow shadow = base.getRuleEngineShadow();
        if (shadow != null) {
            context.setLlmRawScore(shadow.getLlmRawScore());
            context.setRuleEngineScore(shadow.getRuleEngineScore());
            context.setScoreDiff(shadow.getScoreDiff());
            context.setDiffReasons(shadow.getDiffReasons() == null ? List.of() : shadow.getDiffReasons());
        } else {
            context.setRuleEngineScore(base.getOverallScore());
        }

        List<String> triggers = new ArrayList<>();
        if (context.getScoreDiff() != null && context.getScoreDiff().abs().compareTo(new BigDecimal("10")) > 0) {
            triggers.add("规则引擎分与旧 LLM 分差异超过10分");
        }
        if (context.getDiffReasons() != null) {
            for (String reason : context.getDiffReasons()) {
                if (hasText(reason) && !triggers.contains(reason)) triggers.add(reason);
            }
        }

        Map<Long, Integer> anchorUsage = new LinkedHashMap<>();
        if (base.getStructuredObservations() != null) {
            for (AiScoreReportUserResponse.StructuredObservation observation : base.getStructuredObservations()) {
                if (observation.getEvidenceAnchorIds() == null) continue;
                for (Long anchorId : observation.getEvidenceAnchorIds()) {
                    if (anchorId != null) anchorUsage.merge(anchorId, 1, Integer::sum);
                }
            }
        }

        List<AiJuryReviewUserResponse.DisputedObservation> observations = new ArrayList<>();
        if (base.getStructuredObservations() != null) {
            for (AiScoreReportUserResponse.StructuredObservation observation : base.getStructuredObservations()) {
                AiJuryReviewUserResponse.DisputedObservation item = toDisputedObservation(observation, anchorUsage);
                if (!item.getReasons().isEmpty()) observations.add(item);
            }
        }
        context.setDisputedObservations(observations);
        if (observations.stream().anyMatch(item -> item.getReasons().stream().anyMatch(reason -> reason.contains("证据锚点少于要求")))) {
            triggers.add("E4/E5 高证据等级存在锚点不足风险");
        }
        if (observations.stream().anyMatch(item -> item.getReasons().stream().anyMatch(reason -> reason.contains("低置信度")))) {
            triggers.add("关键证据来自低置信度识别结果");
        }
        if (observations.stream().anyMatch(item -> item.getReasons().stream().anyMatch(reason -> reason.contains("同一证据")))) {
            triggers.add("同一证据被绑定到多个观测点");
        }

        List<AiJuryReviewUserResponse.DeductionReviewItem> deductions = new ArrayList<>();
        if (base.getStructuredDeductions() != null) {
            for (AiScoreReportUserResponse.StructuredDeduction deduction : base.getStructuredDeductions()) {
                if (deduction == null) continue;
                BigDecimal deducted = valueOrZero(deduction.getDeductedPoints());
                if (deducted.compareTo(BigDecimal.ZERO) <= 0) continue;
                deductions.add(toDeductionReviewItem(deduction));
            }
        }
        context.setDeductionReviewItems(deductions);
        if (!deductions.isEmpty()) triggers.add("存在当前扣分项需要复核轻重");

        List<String> uniqueTriggers = triggers.stream().filter(this::hasText).distinct().toList();
        context.setReviewTriggers(uniqueTriggers);
        context.setHumanReviewSuggested(!uniqueTriggers.isEmpty());
        context.setSummary(uniqueTriggers.isEmpty()
                ? "规则引擎结果暂无明显争议，评审团仅提供训练视角复核建议。"
                : "已触发" + uniqueTriggers.size() + "类争议复核信号，评审团仅输出争议解释与人工复核建议，不修改规则引擎最终分。");
        return context;
    }

    private AiJuryReviewUserResponse.DisputedObservation toDisputedObservation(
            AiScoreReportUserResponse.StructuredObservation observation,
            Map<Long, Integer> anchorUsage
    ) {
        AiJuryReviewUserResponse.DisputedObservation item = new AiJuryReviewUserResponse.DisputedObservation();
        if (observation == null) return item;
        item.setDimensionName(observation.getDimensionName());
        item.setEvidenceLevel(observation.getEvidenceLevel());
        item.setRawScore(observation.getRawScore());
        item.setScoreCap(observation.getScoreCap());
        item.setConfidence(observation.getConfidence());
        int anchorCount = observation.getEvidenceAnchorIds() == null ? 0 : observation.getEvidenceAnchorIds().size();
        item.setAnchorCount(anchorCount);

        List<String> reasons = new ArrayList<>();
        String evidenceLevel = safeStr(observation.getEvidenceLevel()).toUpperCase();
        int requiredAnchors = "E5".equals(evidenceLevel) ? 3 : "E4".equals(evidenceLevel) ? 2 : 0;
        if (requiredAnchors > 0 && anchorCount < requiredAnchors) {
            reasons.add(evidenceLevel + " 证据等级的证据锚点少于要求");
        }
        if (observation.getConfidence() != null && observation.getConfidence().compareTo(new BigDecimal("0.60")) < 0) {
            reasons.add("观测点证据来自低置信度识别结果");
        }
        if (observation.getRawScore() != null
                && observation.getScoreCap() != null
                && observation.getRawScore().compareTo(observation.getScoreCap()) > 0) {
            reasons.add("高分被规则引擎封顶，需要复核封顶原因");
        }
        if (observation.getEvidenceAnchorIds() != null
                && observation.getEvidenceAnchorIds().stream().filter(Objects::nonNull).anyMatch(id -> anchorUsage.getOrDefault(id, 0) > 1)) {
            reasons.add("同一证据被绑定到多个观测点");
        }
        item.setReasons(reasons);
        return item;
    }

    private AiJuryReviewUserResponse.DeductionReviewItem toDeductionReviewItem(AiScoreReportUserResponse.StructuredDeduction deduction) {
        AiJuryReviewUserResponse.DeductionReviewItem item = new AiJuryReviewUserResponse.DeductionReviewItem();
        item.setDimensionName(deduction.getDimensionName());
        item.setReason(deduction.getReason());
        item.setDeductedPoints(deduction.getDeductedPoints());
        item.setRecoveredPoints(deduction.getRecoveredPoints());
        item.setConfidence(deduction.getConfidence());
        item.setEvidenceLevel(deduction.getEvidenceLevel());
        item.setAnchorCount(deduction.getEvidenceAnchorIds() == null ? 0 : deduction.getEvidenceAnchorIds().size());
        item.setStatus(deduction.getStatus());
        item.setRequiredFix(deduction.getRequiredFix());
        return item;
    }

    private AiJuryReviewUserResponse.DisputeReviewContext toDisputeReviewContext(Map<String, Object> payload) {
        if (payload == null || payload.isEmpty()) return null;
        AiJuryReviewUserResponse.DisputeReviewContext context = new AiJuryReviewUserResponse.DisputeReviewContext();
        context.setMode(firstNonBlank(first(payload, "mode"), "dispute_review"));
        context.setOfficialScore(toDecimal(first(payload, "officialScore", "official_score")));
        context.setLlmRawScore(toDecimal(first(payload, "llmRawScore", "llm_raw_score")));
        context.setRuleEngineScore(toDecimal(first(payload, "ruleEngineScore", "rule_engine_score")));
        context.setScoreDiff(toDecimal(first(payload, "scoreDiff", "score_diff")));
        context.setDiffReasons(firstList(first(payload, "diffReasons", "diff_reasons")));
        context.setReviewTriggers(firstList(first(payload, "reviewTriggers", "review_triggers")));
        context.setHumanReviewSuggested(Boolean.TRUE.equals(first(payload, "humanReviewSuggested", "human_review_suggested")));
        context.setSummary(safeStr(first(payload, "summary")));

        List<AiJuryReviewUserResponse.DisputedObservation> observations = new ArrayList<>();
        for (Object raw : asList(first(payload, "disputedObservations", "disputed_observations"))) {
            Map<String, Object> map = asMap(raw);
            AiJuryReviewUserResponse.DisputedObservation item = new AiJuryReviewUserResponse.DisputedObservation();
            item.setDimensionName(safeStr(first(map, "dimensionName", "dimension_name")));
            item.setEvidenceLevel(safeStr(first(map, "evidenceLevel", "evidence_level")));
            item.setRawScore(toDecimal(first(map, "rawScore", "raw_score")));
            item.setScoreCap(toDecimal(first(map, "scoreCap", "score_cap")));
            item.setConfidence(toDecimal(first(map, "confidence")));
            item.setAnchorCount(toInteger(first(map, "anchorCount", "anchor_count")));
            item.setReasons(firstList(first(map, "reasons")));
            observations.add(item);
        }
        context.setDisputedObservations(observations);

        List<AiJuryReviewUserResponse.DeductionReviewItem> deductions = new ArrayList<>();
        for (Object raw : asList(first(payload, "deductionReviewItems", "deduction_review_items"))) {
            Map<String, Object> map = asMap(raw);
            AiJuryReviewUserResponse.DeductionReviewItem item = new AiJuryReviewUserResponse.DeductionReviewItem();
            item.setDimensionName(safeStr(first(map, "dimensionName", "dimension_name")));
            item.setReason(safeStr(first(map, "reason")));
            item.setDeductedPoints(toDecimal(first(map, "deductedPoints", "deducted_points")));
            item.setRecoveredPoints(toDecimal(first(map, "recoveredPoints", "recovered_points")));
            item.setConfidence(toDecimal(first(map, "confidence")));
            item.setEvidenceLevel(safeStr(first(map, "evidenceLevel", "evidence_level")));
            item.setAnchorCount(toInteger(first(map, "anchorCount", "anchor_count")));
            item.setStatus(safeStr(first(map, "status")));
            item.setRequiredFix(safeStr(first(map, "requiredFix", "required_fix")));
            deductions.add(item);
        }
        context.setDeductionReviewItems(deductions);
        return context;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> toPayload(AiJuryReviewUserResponse.DisputeReviewContext context) {
        if (context == null) return Map.of();
        return objectMapper.convertValue(context, Map.class);
    }

    private AiJuryReviewUserResponse.DisputeReviewContext firstContext(
            AiJuryReviewUserResponse.DisputeReviewContext first,
            AiJuryReviewUserResponse.DisputeReviewContext fallback
    ) {
        return first == null ? fallback : first;
    }

    @SuppressWarnings("unchecked")
    private AiJuryReviewUserResponse.DisputeReviewContext disputeContextFromAggregate(AiJuryAggregate aggregate) {
        if (aggregate == null || aggregate.getAggregateReportJson() == null || aggregate.getAggregateReportJson().isBlank()) {
            return null;
        }
        try {
            Map<String, Object> raw = objectMapper.readValue(aggregate.getAggregateReportJson(), Map.class);
            return toDisputeReviewContext(asMap(first(raw, "dispute_review_context", "disputeReviewContext")));
        } catch (Exception ignored) {
            return null;
        }
    }

    private AiJurySession latestBySession(Long sessionId) {
        if (jurySessionMapper == null) return null;
        return jurySessionMapper.selectOne(
                new LambdaQueryWrapper<AiJurySession>()
                        .eq(AiJurySession::getScoringSessionId, sessionId)
                        .orderByDesc(AiJurySession::getCreatedAt)
                        .last("LIMIT 1"));
    }

    private AiJurySession latestByMeeting(Long meetingId) {
        if (jurySessionMapper == null) return null;
        return jurySessionMapper.selectOne(
                new LambdaQueryWrapper<AiJurySession>()
                        .eq(AiJurySession::getMeetingId, meetingId)
                        .orderByDesc(AiJurySession::getCreatedAt)
                        .last("LIMIT 1"));
    }

    private boolean isPythonReview(AiJurySession session) {
        return session != null && PYTHON_REVIEW_VERSION.equalsIgnoreCase(safeStr(session.getStandardVersion()));
    }

    private boolean hasRealPythonResult(AiJuryReviewUserResponse response) {
        return response != null
                && hasCompletedStatus(response.getStatus())
                && response.getMembers() != null
                && response.getMembers().stream().anyMatch(member -> member.getReferenceScore() != null);
    }

    private boolean hasCompletedStatus(String status) {
        return "completed".equalsIgnoreCase(status) || "partial_failed".equalsIgnoreCase(status);
    }

    private boolean hasMemberContent(AiJuryReviewUserResponse.MemberReview member) {
        return member != null
                && (hasText(member.getPersonaCode())
                || hasText(member.getDisplayName())
                || member.getReferenceScore() != null);
    }

    private AiJuryReviewUserResponse emptyResponse(Long sessionId, Long meetingId, String explanation) {
        AiJuryReviewUserResponse empty = new AiJuryReviewUserResponse();
        empty.setSessionId(sessionId);
        empty.setMeetingId(meetingId);
        empty.setStatus("empty");
        empty.setReviewMode("复核层");
        empty.setExplanation(explanation);
        return empty;
    }

    private AiJuryReviewUserResponse withoutUnverifiedMembers(
            AiJuryReviewUserResponse response,
            Long sessionId,
            Long meetingId
    ) {
        AiJuryReviewUserResponse empty = emptyResponse(
                sessionId == null ? response.getSessionId() : sessionId,
                meetingId == null ? response.getMeetingId() : meetingId,
                firstNonBlank(response.getExplanation(), "评审团复核暂未生成/生成失败。")
        );
        String status = safeStr(response.getStatus());
        if ("processing".equalsIgnoreCase(status) || "pending".equalsIgnoreCase(status) || "running".equalsIgnoreCase(status)) {
            empty.setStatus("processing");
        } else {
            empty.setStatus("failed".equalsIgnoreCase(status) ? "failed" : "empty");
        }
        empty.setOfficialScore(response.getOfficialScore());
        empty.setJudgeCount(response.getJudgeCount());
        empty.setSuccessfulCount(response.getSuccessfulCount());
        return empty;
    }

    private Map<String, Map<String, Object>> personaByCode() {
        if (personaService == null) return Map.of();
        return personaService.listUserPersonaPayloads().stream()
                .filter(Objects::nonNull)
                .filter(persona -> hasText(first(persona, "code", "personaCode")))
                .collect(Collectors.toMap(
                        persona -> safeStr(first(persona, "code", "personaCode")).toUpperCase(),
                        persona -> persona,
                        (left, right) -> left,
                        LinkedHashMap::new));
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> result = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                result.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return result;
        }
        return Map.of();
    }

    private List<Object> asList(Object value) {
        if (value instanceof List<?> list) return new ArrayList<>(list);
        if (value == null) return List.of();
        return List.of(value);
    }

    private List<String> firstList(Object... values) {
        for (Object value : values) {
            List<String> list = toStrList(value);
            if (!list.isEmpty()) return list;
        }
        return List.of();
    }

    private List<String> toStrList(Object value) {
        if (value == null) return List.of();
        if (value instanceof List<?> list) {
            List<String> result = new ArrayList<>();
            for (Object item : list) {
                if (item == null) continue;
                if (item instanceof Map<?, ?> map) {
                    Object text = first(asMap(map), "issue", "text", "summary", "question", "suggestion", "dimension_name", "dimension");
                    if (text != null && hasText(text)) result.add(safeStr(text));
                } else if (hasText(item)) {
                    result.add(safeStr(item));
                }
            }
            return result;
        }
        if (value instanceof Map<?, ?> map) {
            List<String> result = new ArrayList<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                Object v = entry.getValue();
                if (v == null) continue;
                if (v instanceof Number || hasText(v)) {
                    result.add(safeStr(entry.getKey()) + ": " + safeStr(v));
                }
            }
            return result;
        }
        return hasText(value) ? List.of(safeStr(value)) : List.of();
    }

    private List<String> parseStrList(String json) {
        if (json == null || json.isBlank()) return List.of();
        try {
            return toStrList(objectMapper.readValue(json, List.class));
        } catch (Exception e) {
            return List.of();
        }
    }

    private Object first(Map<String, Object> map, String... keys) {
        if (map == null || keys == null) return null;
        for (String key : keys) {
            if (map.containsKey(key)) return map.get(key);
        }
        return null;
    }

    private String firstNonBlank(Object... values) {
        for (Object value : values) {
            if (hasText(value)) return safeStr(value);
        }
        return "";
    }

    private BigDecimal firstDecimal(Object first, Object fallback) {
        return firstDecimal(first, fallback, null);
    }

    private BigDecimal firstDecimal(Object first, Object fallback, BigDecimal defaultValue) {
        BigDecimal parsed = toDecimal(first);
        if (parsed != null) return parsed;
        parsed = toDecimal(fallback);
        return parsed == null ? defaultValue : parsed;
    }

    private BigDecimal toDecimal(Object value) {
        if (value instanceof BigDecimal decimal) return decimal;
        if (value instanceof Number number) return BigDecimal.valueOf(number.doubleValue()).setScale(1, RoundingMode.HALF_UP);
        if (value instanceof String text && !text.isBlank()) {
            try {
                return new BigDecimal(text.trim()).setScale(1, RoundingMode.HALF_UP);
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private BigDecimal averageScore(List<AiJuryReviewUserResponse.MemberReview> members) {
        List<BigDecimal> scores = members.stream()
                .map(AiJuryReviewUserResponse.MemberReview::getReferenceScore)
                .filter(Objects::nonNull)
                .toList();
        if (scores.isEmpty()) return null;
        BigDecimal total = scores.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        return total.divide(BigDecimal.valueOf(scores.size()), 1, RoundingMode.HALF_UP);
    }

    private BigDecimal maxScore(List<AiJuryReviewUserResponse.MemberReview> members) {
        return members.stream()
                .map(AiJuryReviewUserResponse.MemberReview::getReferenceScore)
                .filter(Objects::nonNull)
                .max(BigDecimal::compareTo)
                .orElse(null);
    }

    private BigDecimal minScore(List<AiJuryReviewUserResponse.MemberReview> members) {
        return members.stream()
                .map(AiJuryReviewUserResponse.MemberReview::getReferenceScore)
                .filter(Objects::nonNull)
                .min(BigDecimal::compareTo)
                .orElse(null);
    }

    private String scoreRelation(BigDecimal score, BigDecimal officialScore) {
        if (score == null || officialScore == null) return "";
        int compare = score.compareTo(officialScore);
        if (compare > 0) return "高于本场得分";
        if (compare < 0) return "低于本场得分";
        return "等于本场得分";
    }

    private Integer toInteger(Object value) {
        if (value instanceof Number number) return number.intValue();
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private Long toLong(Object value) {
        if (value instanceof Number number) return number.longValue();
        if (value instanceof String text && !text.isBlank()) {
            try {
                return Long.parseLong(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    private BigDecimal valueOrZero(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private boolean hasText(Object value) {
        return value != null && !String.valueOf(value).isBlank();
    }

    private String safeStr(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String writeSafeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return "[]";
        }
    }
}
