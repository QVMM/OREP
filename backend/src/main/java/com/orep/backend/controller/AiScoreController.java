package com.orep.backend.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.common.Result;
import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.AiScoreRuleEngineResult;
import com.orep.backend.dto.AiScoreRuleEngineUserResponse;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.dto.SpeakerIdentityUpdateRequest;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.AiScoreSpeakerIdentityService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.ProjectTeamService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

@RestController
@RequestMapping("/api/ai-score")
public class AiScoreController {

    private final AiScoreReportMapper reportMapper;
    private final ProjectTeamService projectTeamService;
    private final AiScoringSessionService scoringSessionService;
    private final AiScoreEvidenceBundleService evidenceBundleService;
    private final AiScoreStructuredResultService structuredResultService;
    private final AiScoreAccessControlService accessControlService;
    private final AiScoreSpeakerIdentityService speakerIdentityService;
    private final AiScoringPipelineClient pipelineClient;
    private final String uploadDir;
    /**
     * AI speaker-attribution snapshots may include diagnostics / future fields.
     * Ignore unknowns so recompute does not break on contract extensions.
     */
    private final ObjectMapper objectMapper = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    @Autowired
    public AiScoreController(AiScoreReportMapper reportMapper,
                             ProjectTeamService projectTeamService,
                             AiScoringSessionService scoringSessionService,
                             AiScoreEvidenceBundleService evidenceBundleService,
                             AiScoreStructuredResultService structuredResultService,
                             AiScoreAccessControlService accessControlService,
                             AiScoreSpeakerIdentityService speakerIdentityService,
                             AiScoringPipelineClient pipelineClient,
                             @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.reportMapper = reportMapper;
        this.projectTeamService = projectTeamService;
        this.scoringSessionService = scoringSessionService;
        this.evidenceBundleService = evidenceBundleService;
        this.structuredResultService = structuredResultService;
        this.accessControlService = accessControlService;
        this.speakerIdentityService = speakerIdentityService;
        this.pipelineClient = pipelineClient;
        this.uploadDir = uploadDir;
    }

    public AiScoreController(AiScoreReportMapper reportMapper,
                             ProjectTeamService projectTeamService,
                             AiScoringSessionService scoringSessionService,
                             AiScoreEvidenceBundleService evidenceBundleService,
                             AiScoreStructuredResultService structuredResultService,
                             AiScoreAccessControlService accessControlService) {
        this(reportMapper, projectTeamService, scoringSessionService, evidenceBundleService,
                structuredResultService, accessControlService, null, null, "./uploads");
    }

    public AiScoreController(AiScoreReportMapper reportMapper,
                             ProjectTeamService projectTeamService,
                             AiScoringSessionService scoringSessionService,
                             AiScoreEvidenceBundleService evidenceBundleService,
                             AiScoreStructuredResultService structuredResultService,
                             AiScoreAccessControlService accessControlService,
                             AiScoreSpeakerIdentityService speakerIdentityService) {
        this(reportMapper, projectTeamService, scoringSessionService, evidenceBundleService,
                structuredResultService, accessControlService, speakerIdentityService, null, "./uploads");
    }

    @PostMapping("/sessions")
    public Result<AiScoringSessionUserResponse> createSession(@RequestBody AiScoringSessionCreateRequest request,
                                                              HttpServletRequest httpRequest) {
        try {
            Long userId = (Long) httpRequest.getAttribute("userId");
            accessControlService.assertTeamAccess(
                    request == null ? null : request.getTeamId(),
                    attrLong(httpRequest, "tenantId"),
                    userId,
                    attrString(httpRequest, "role")
            );
            return Result.success(scoringSessionService.createSession(request, userId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/start")
    public Result<AiScoringSessionUserResponse> startSession(@PathVariable("sessionId") Long sessionId,
                                                             HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.start(sessionId));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/cancel")
    public Result<AiScoringSessionUserResponse> cancelSession(@PathVariable("sessionId") Long sessionId,
                                                              HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.cancel(sessionId));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/restart")
    public Result<AiScoringSessionUserResponse> restartSession(@PathVariable("sessionId") Long sessionId,
                                                               HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.restart(sessionId));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/sessions/{sessionId}/status")
    public Result<AiScoringSessionUserResponse> sessionStatus(@PathVariable("sessionId") Long sessionId,
                                                              HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.getStatus(sessionId));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PatchMapping("/sessions/{sessionId}/speakers/{rawSpeaker}")
    public Result<AiScoreReportUserResponse.SpeakerMapping> updateSpeakerIdentity(
            @PathVariable("sessionId") Long sessionId,
            @PathVariable("rawSpeaker") String rawSpeaker,
            @RequestBody SpeakerIdentityUpdateRequest body,
            HttpServletRequest request
    ) {
        try {
            assertSessionAccess(sessionId, request);
            if (speakerIdentityService == null) {
                throw new IllegalStateException("发言人修正服务不可用");
            }
            AiScoreSpeakerIdentity identity = speakerIdentityService.confirm(
                    sessionId,
                    rawSpeaker,
                    body == null ? null : body.getDisplayName(),
                    body == null ? null : body.getRoleName(),
                    attrLong(request, "userId")
            );
            return Result.success(toSpeakerMapping(identity));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    /**
     * One-click rebuild of FINAL speaker attribution for an existing completed
     * session. Reuses stored ASR/cluster evidence; does not re-score.
     */
    @PostMapping("/sessions/{sessionId}/recompute-speaker-attribution")
    public Result<AiScoreReportUserResponse> recomputeSpeakerAttribution(
            @PathVariable("sessionId") Long sessionId,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request
    ) {
        try {
            assertSessionAccess(sessionId, request);
            if (pipelineClient == null) {
                throw new IllegalStateException("AI 评分服务客户端不可用");
            }
            if (speakerIdentityService == null) {
                throw new IllegalStateException("人物归属持久化服务不可用");
            }
            // Ensure session exists and is at least reportable
            scoringSessionService.requireSessionForAccess(sessionId);
            Integer contestantSlots = null;
            if (body != null && body.get("contestantSlots") instanceof Number number) {
                contestantSlots = number.intValue();
            }
            Map<String, Object> aiPayload = pipelineClient.recomputeSpeakerAttribution(
                    sessionId, contestantSlots
            );
            Object rawSnapshot = aiPayload.get("speakerAttribution");
            PipelineCallbackRequest.SpeakerAttributionInput snapshot = objectMapper.convertValue(
                    rawSnapshot,
                    PipelineCallbackRequest.SpeakerAttributionInput.class
            );
            speakerIdentityService.persistAttribution(sessionId, snapshot);
            return Result.success(scoringSessionService.reportBySession(sessionId, attrString(request, "role")));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            String message = e.getMessage() == null ? "" : e.getMessage();
            if (message.contains("不存在") || message.contains("未完成") || message.contains("报告")) {
                return Result.error(404, message);
            }
            return Result.error(409, message);
        } catch (Exception e) {
            return Result.error(500, "人物归属重算失败");
        }
    }

    private AiScoreReportUserResponse.SpeakerMapping toSpeakerMapping(AiScoreSpeakerIdentity identity) {
        AiScoreReportUserResponse.SpeakerMapping response = new AiScoreReportUserResponse.SpeakerMapping();
        response.setRawSpeaker(identity.getRawSpeakerLabel());
        response.setDisplayName(identity.getDisplayName());
        response.setRoleName(identity.getRoleName());
        response.setStatus(identity.getStatus());
        response.setConfidence(identity.getConfidence());
        response.setRevision(identity.getRevision());
        return response;
    }

    @PostMapping("/sessions/{sessionId}/prepare-evidence")
    public Result<AiScoreEvidenceBundleResponse> prepareEvidence(@PathVariable("sessionId") Long sessionId,
                                                                 HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            scoringSessionService.markEvidencePreparing(sessionId);
            AiScoreEvidenceBundleResponse response = evidenceBundleService.prepareEvidence(sessionId);
            scoringSessionService.markEvidenceReady(sessionId);
            return Result.success(response);
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            markFailedQuietly(sessionId, e.getMessage(), "evidence_failed");
            return Result.error(409, e.getMessage());
        }
    }

    @GetMapping("/sessions/{sessionId}/evidence-bundle")
    public Result<AiScoreEvidenceBundleResponse> evidenceBundle(@PathVariable("sessionId") Long sessionId,
                                                                HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(evidenceBundleService.latestBundle(sessionId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/structured-result")
    public Result<AiScoreRuleEngineUserResponse> applyStructuredResult(@PathVariable("sessionId") Long sessionId,
                                                                       @RequestBody AiScoreStructuredResultRequest request,
                                                                       HttpServletRequest httpRequest) {
        try {
            assertSessionAccess(sessionId, httpRequest);
            AiScoreRuleEngineResult result = structuredResultService.applyStructuredResult(sessionId, request, List.of());
            return Result.success(AiScoreRuleEngineUserResponse.from(result));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/pipeline-callback")
    public Result<Void> pipelineCallback(@PathVariable("sessionId") Long sessionId,
                                         @RequestBody PipelineCallbackRequest callback) {
        try {
            callback.setSessionId(sessionId);
            scoringSessionService.processPipelineCallback(callback);
            return Result.success();
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    private void markFailedQuietly(Long sessionId, String message, String stage) {
        try {
            scoringSessionService.markFailed(sessionId, message, stage);
        } catch (Exception ignored) {
        }
    }

    private void assertSessionAccess(Long sessionId, HttpServletRequest request) {
        accessControlService.assertSessionAccess(
                scoringSessionService.requireSessionForAccess(sessionId),
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        );
    }

    private void assertReportAccess(Long reportId, HttpServletRequest request) {
        AiScoringSession session = scoringSessionService.sessionForReportAccess(reportId);
        if (session == null) {
            throw new IllegalStateException("报告不存在或未完成");
        }
        accessControlService.assertSessionAccess(
                session,
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        );
    }

    private void assertMeetingAccess(Long meetingId, HttpServletRequest request) {
        AiScoringSession session = scoringSessionService.sessionForMeetingAccess(meetingId);
        if (session == null) {
            throw new IllegalStateException("该会议暂未生成AI评分报告");
        }
        accessControlService.assertSessionAccess(
                session,
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        );
    }

    private Long attrLong(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value instanceof Number number ? number.longValue() : null;
    }

    private String attrString(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value == null ? null : String.valueOf(value);
    }

    @GetMapping("/sessions/latest")
    public Result<AiScoringSessionUserResponse> latestSession(@RequestParam(value = "projectId", required = false) Long projectId,
                                                               @RequestParam(value = "teamId", required = false) Long teamId,
                                                               @RequestParam(value = "trackId", required = false) String trackId,
                                                               HttpServletRequest request) {
        try {
            return Result.success(scoringSessionService.latest(
                    projectId,
                    teamId,
                    trackId,
                    attrLong(request, "tenantId"),
                    attrLong(request, "userId"),
                    attrString(request, "role")
            ));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/reports/summary")
    public Result<List<Map<String, Object>>> reportSummaries(@RequestParam(value = "scope", defaultValue = "participant") String scope,
                                                             HttpServletRequest request) {
        return Result.success(scoringSessionService.reportSummaries(
                scope,
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        ));
    }

    @GetMapping("/reports/by-session/{sessionId}")
    public Result<AiScoreReportUserResponse> reportBySession(@PathVariable("sessionId") Long sessionId,
                                                             HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.reportBySession(sessionId, attrString(request, "role")));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/reports/by-report/{reportId}")
    public Result<AiScoreReportUserResponse> reportByReport(@PathVariable("reportId") Long reportId,
                                                            HttpServletRequest request) {
        try {
            assertReportAccess(reportId, request);
            return Result.success(scoringSessionService.reportByReportId(reportId, attrString(request, "role")));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @GetMapping("/reports/by-meeting/{meetingId}")
    public Result<AiScoreReportUserResponse> reportByMeeting(@PathVariable("meetingId") Long meetingId,
                                                             HttpServletRequest request) {
        try {
            assertMeetingAccess(meetingId, request);
            return Result.success(scoringSessionService.reportByMeetingId(meetingId, attrString(request, "role")));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/task-book/items/{index}/hang")
    public Result<AiScoreReportUserResponse> hangTaskBookEvidence(@PathVariable("sessionId") Long sessionId,
                                                                  @PathVariable("index") int index,
                                                                  @RequestBody(required = false) Map<String, Object> body,
                                                                  HttpServletRequest request) {
        try {
            accessControlService.assertSessionParticipantWrite(
                    scoringSessionService.requireSessionForAccess(sessionId),
                    attrLong(request, "tenantId"),
                    attrLong(request, "userId"),
                    attrString(request, "role"));
            Map<String, Object> payload = body == null ? Map.of() : body;
            Object raw = payload.get("evidence");
            if (raw == null) {
                raw = payload.get("hungEvidence");
            }
            return Result.success(scoringSessionService.hangTaskBookEvidence(
                    sessionId,
                    index,
                    raw == null ? "" : String.valueOf(raw),
                    attrLong(request, "userId"),
                    attrString(request, "role")));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/task-book/publish")
    public Result<AiScoreReportUserResponse> publishTaskBook(@PathVariable("sessionId") Long sessionId,
                                                             HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.publishTaskBook(sessionId, attrString(request, "role")));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/confirm")
    public Result<AiScoreReportUserResponse> confirmDeliberation(@PathVariable("sessionId") Long sessionId,
                                                                 HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            return Result.success(scoringSessionService.confirmDeliberation(
                    sessionId, attrString(request, "role"), attrLong(request, "userId")));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/sessions/{sessionId}/challenges/{challengeId}/resolve")
    public Result<AiScoreReportUserResponse> resolveChallenge(@PathVariable("sessionId") Long sessionId,
                                                              @PathVariable("challengeId") String challengeId,
                                                              @RequestBody(required = false) Map<String, Object> body,
                                                              HttpServletRequest request) {
        try {
            assertSessionAccess(sessionId, request);
            Map<String, Object> payload = body == null ? Map.of() : body;
            return Result.success(scoringSessionService.resolveChallenge(
                    sessionId,
                    challengeId,
                    String.valueOf(payload.getOrDefault("action", "")),
                    payload.get("reason") == null ? "" : String.valueOf(payload.get("reason")),
                    attrString(request, "role"),
                    attrLong(request, "userId")));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PatchMapping("/reports/{reportId}/remediation-tasks/{taskId}/status")
    public Result<Map<String, Object>> updateRemediationTaskStatus(
            @PathVariable("reportId") Long reportId,
            @PathVariable("taskId") Long taskId,
            @RequestBody Map<String, Object> body
    ) {
        try {
            String status = String.valueOf(body.getOrDefault("status", ""));
            return Result.success(scoringSessionService.updateRemediationTaskStatus(reportId, taskId, status));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(503, e.getMessage());
        }
    }

    /**
     * AI 评分服务回调（由 Python AI 微服务调用）
     */
    @PostMapping("/callback")
    public Result<Void> callback(@RequestBody Map<String, Object> body) {
        String meetingId = String.valueOf(body.get("meetingId"));
        String status = String.valueOf(body.get("status"));

        // 查找或创建记录
        AiScoreReport report = reportMapper.selectOne(
            new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, Long.parseLong(meetingId))
        );
        if (report == null) {
            report = new AiScoreReport();
            report.setMeetingId(Long.parseLong(meetingId));
            report.setStartedAt(LocalDateTime.now());
        }

        report.setStatus(status);
        report.setCompletedAt(LocalDateTime.now());
        report.setUpdatedAt(LocalDateTime.now());

        if ("completed".equals(status)) {
            // 解析评分结果
            Object overallScore = body.get("overallScore");
            if (overallScore != null) {
                if (overallScore instanceof Number) {
                    report.setOverallScore(new java.math.BigDecimal(overallScore.toString()));
                }
            }

            report.setResultPath(safeStr(body.get("resultPath")));
            report.setModel(safeStr(body.get("model")));
            report.setTranscript(safeStr(body.get("transcript")));
            report.setDimensionsJson(safeJson(body.get("dimensions")));
            report.setHighlightsJson(safeJson(body.get("highlights")));
            report.setCriticalIssuesJson(safeJson(body.get("criticalIssues")));
            report.setImprovementPrioritiesJson(safeJson(body.get("improvementPriorities")));
            report.setSpeechQualityJson(safeJson(body.get("speechQuality")));
            report.setScoreCalibrationJson(safeJson(body.get("scoreCalibration")));
        } else if ("failed".equals(status)) {
            report.setErrorMessage(safeStr(body.get("error")));
        }

        if (report.getId() == null) {
            report.setCreatedAt(LocalDateTime.now());
            reportMapper.insert(report);
        } else {
            reportMapper.updateById(report);
        }

        // AI 评分落库后：写入分发言人分析（可选）+ 置脏绑定该会议的团队能力画像，触发下一次读取时重算
        if ("completed".equals(status)) {
            try {
                Object speakers = body.get("speakers");
                if (speakers instanceof java.util.List<?> list) {
                    @SuppressWarnings("unchecked")
                    java.util.List<Map<String, Object>> speakerList = (java.util.List<Map<String, Object>>) list;
                    projectTeamService.ingestRoadshowSpeakers(report.getMeetingId(), speakerList);
                }
                projectTeamService.markAbilityDirtyByMeeting(report.getMeetingId());
            } catch (Exception ignored) {
            }
        }

        return Result.success();
    }

    /**
     * 查询 AI 评分状态
     */
    @GetMapping("/status/{meetingId}")
    public Result<AiScoreReport> getStatus(@PathVariable("meetingId") Long meetingId,
                                           HttpServletRequest request) {
        try {
            assertMeetingAccess(meetingId, request);
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
        AiScoreReport report = reportMapper.selectOne(
            new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, meetingId)
        );
        if (report == null) {
            return Result.error(404, "未找到该会议的AI评分记录");
        }
        return Result.success(report);
    }

    /**
     * 下载 AI 评分 PDF 报告
     */
    @GetMapping("/reports/by-session/{sessionId}/pdf")
    public void downloadPdfBySession(@PathVariable("sessionId") Long sessionId,
                                     HttpServletRequest request,
                                     HttpServletResponse response) throws Exception {
        AiScoringSession session;
        try {
            assertSessionAccess(sessionId, request);
            session = scoringSessionService.requireSessionForAccess(sessionId);
        } catch (IllegalStateException e) {
            response.setStatus(404);
            response.getWriter().write(e.getMessage());
            return;
        }

        AiScoreReport report = null;
        if (session.getReportId() != null) {
            report = reportMapper.selectById(session.getReportId());
        }
        if (report == null) {
            report = reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getSessionId, sessionId)
                .last("LIMIT 1"));
        }
        if (report == null && session.getMeetingId() != null) {
            report = reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, session.getMeetingId())
                .last("LIMIT 1"));
        }
        if (report == null) {
            report = reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, -sessionId)
                .last("LIMIT 1"));
        }
        if (report == null || !"completed".equals(report.getStatus())) {
            response.setStatus(404);
            response.getWriter().write("报告不存在或未完成");
            return;
        }

        java.io.File pdfFile = resolvePdfFile(session, report);
        if (pdfFile == null) {
            response.setStatus(404);
            response.getWriter().write("PDF报告文件不存在");
            return;
        }

        streamPdf(response, pdfFile, "AI评分报告_" + session.getSessionNo() + ".pdf");
    }

    @GetMapping("/pdf/{meetingId}")
    public void downloadPdf(@PathVariable("meetingId") Long meetingId,
                            HttpServletRequest request,
                            HttpServletResponse response) throws Exception {
        try {
            assertMeetingAccess(meetingId, request);
        } catch (IllegalStateException e) {
            response.setStatus(404);
            response.getWriter().write(e.getMessage());
            return;
        }
        AiScoreReport report = reportMapper.selectOne(
            new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, meetingId)
        );
        if (report == null || !"completed".equals(report.getStatus())) {
            response.setStatus(404);
            response.getWriter().write("报告不存在或未完成");
            return;
        }

        java.io.File pdfFile = resolvePdfFileByIds(List.of(meetingId));
        if (pdfFile == null) {
            response.setStatus(404);
            response.getWriter().write("PDF报告文件不存在");
            return;
        }

        streamPdf(response, pdfFile, "AI评分报告_会议" + meetingId + ".pdf");
    }

    private java.io.File resolvePdfFile(AiScoringSession session, AiScoreReport report) {
        Set<Long> ids = new LinkedHashSet<>();
        if (session != null && session.getId() != null) {
            ids.add(session.getId());
        }
        if (session != null && session.getMeetingId() != null) {
            ids.add(session.getMeetingId());
        }
        if (report != null) {
            if (report.getId() != null) {
                ids.add(report.getId());
            }
            if (report.getSessionId() != null) {
                ids.add(report.getSessionId());
            }
            if (report.getMeetingId() != null) {
                ids.add(report.getMeetingId());
                ids.add(Math.abs(report.getMeetingId()));
            }
        }
        return resolvePdfFileByIds(new ArrayList<>(ids));
    }

    /**
     * PDF 由 ai-scoring 写入共享 uploads 卷：reports/ 与历史 results/。
     * 禁止再写死本机开发路径（user.home/...），否则生产容器永远 404。
     */
    private java.io.File resolvePdfFileByIds(List<Long> ids) {
        List<Path> dirs = reportPdfDirectories();
        for (Long id : ids) {
            if (id == null) {
                continue;
            }
            String name = "report_" + id + ".pdf";
            for (Path dir : dirs) {
                java.io.File pdfFile = dir.resolve(name).toFile();
                if (pdfFile.exists() && pdfFile.isFile() && pdfFile.length() > 0) {
                    return pdfFile;
                }
            }
        }
        return null;
    }

    private List<Path> reportPdfDirectories() {
        String root = (uploadDir == null || uploadDir.isBlank()) ? "./uploads" : uploadDir.trim();
        Path base = Path.of(root).toAbsolutePath().normalize();
        List<Path> dirs = new ArrayList<>();
        dirs.add(base.resolve("reports"));
        dirs.add(base.resolve("results"));
        // 兼容本地开发：仓库内 ai-scoring 相对路径
        Path cwd = Path.of("").toAbsolutePath().normalize();
        dirs.add(cwd.resolve("ai-scoring/uploads/reports"));
        dirs.add(cwd.resolve("../ai-scoring/uploads/reports"));
        String home = System.getProperty("user.home");
        if (home != null && !home.isBlank()) {
            dirs.add(Path.of(home, "项目", "OREP", "ai-scoring", "uploads", "reports"));
        }
        return dirs;
    }

    private void streamPdf(HttpServletResponse response, java.io.File pdfFile, String filename) throws Exception {
        response.setContentType("application/pdf");
        response.setHeader("Content-Disposition",
            "inline; filename=" + URLEncoder.encode(filename, StandardCharsets.UTF_8));
        response.setContentLengthLong(pdfFile.length());

        try (java.io.FileInputStream fis = new java.io.FileInputStream(pdfFile)) {
            fis.transferTo(response.getOutputStream());
        }
    }

    /**
     * 下载 AI 评分报告（JSON）
     */
    @GetMapping("/report/{meetingId}")
    public void downloadReport(@PathVariable("meetingId") Long meetingId,
                               HttpServletRequest request,
                               HttpServletResponse response) throws Exception {
        try {
            assertMeetingAccess(meetingId, request);
        } catch (IllegalStateException e) {
            response.setStatus(404);
            response.getWriter().write(e.getMessage());
            return;
        }
        AiScoreReport report = reportMapper.selectOne(
            new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, meetingId)
        );
        if (report == null || !"completed".equals(report.getStatus())) {
            response.setStatus(404);
            response.getWriter().write("报告不存在或未完成");
            return;
        }

        // 构建完整报告 JSON
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"meetingId\":").append(report.getMeetingId()).append(",");
        json.append("\"overallScore\":").append(report.getOverallScore()).append(",");
        json.append("\"model\":\"").append(escapeJson(report.getModel())).append("\",");
        json.append("\"dimensions\":").append(report.getDimensionsJson() != null ? report.getDimensionsJson() : "{}").append(",");
        json.append("\"highlights\":").append(report.getHighlightsJson() != null ? report.getHighlightsJson() : "[]").append(",");
        json.append("\"criticalIssues\":").append(report.getCriticalIssuesJson() != null ? report.getCriticalIssuesJson() : "[]").append(",");
        json.append("\"improvementPriorities\":").append(report.getImprovementPrioritiesJson() != null ? report.getImprovementPrioritiesJson() : "[]").append(",");
        json.append("\"speechQuality\":").append(report.getSpeechQualityJson() != null ? report.getSpeechQualityJson() : "{}").append(",");
        json.append("\"scoreCalibration\":").append(report.getScoreCalibrationJson() != null ? report.getScoreCalibrationJson() : "{}").append(",");
        json.append("\"transcript\":\"").append(escapeJson(report.getTranscript())).append("\",");
        json.append("\"completedAt\":\"").append(report.getCompletedAt()).append("\"");
        json.append("}");

        byte[] data = json.toString().getBytes(StandardCharsets.UTF_8);
        response.setContentType("application/json");
        response.setHeader("Content-Disposition",
            "attachment; filename=" + URLEncoder.encode("AI评分报告_会议" + meetingId + ".json", StandardCharsets.UTF_8));
        response.setContentLength(data.length);
        response.getOutputStream().write(data);
        response.getOutputStream().flush();
    }

    private String safeStr(Object obj) {
        return obj != null ? obj.toString() : null;
    }

    private String safeJson(Object obj) {
        if (obj == null) return null;
        // 如果已经是字符串，直接返回
        if (obj instanceof String) return (String) obj;
        // 如果是 Map 或 List，转 JSON
        try {
            com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
            return mapper.writeValueAsString(obj);
        } catch (Exception e) {
            return obj.toString();
        }
    }

    private String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r");
    }
}
