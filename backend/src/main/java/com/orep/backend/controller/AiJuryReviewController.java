package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.service.AiJuryReviewService;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.entity.AiScoringSession;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class AiJuryReviewController {
    private final AiJuryReviewService juryReviewService;
    private final AiScoringSessionService scoringSessionService;
    private final AiScoreAccessControlService accessControlService;

    public AiJuryReviewController(AiJuryReviewService juryReviewService,
                                  AiScoringSessionService scoringSessionService,
                                  AiScoreAccessControlService accessControlService) {
        this.juryReviewService = juryReviewService;
        this.scoringSessionService = scoringSessionService;
        this.accessControlService = accessControlService;
    }

    @PostMapping("/api/ai-score/sessions/{sessionId}/jury/start")
    public Result<AiJuryReviewUserResponse> startBySession(@PathVariable Long sessionId,
                                                           HttpServletRequest request) {
        assertSessionAccess(sessionId, request);
        return Result.success(juryReviewService.startForSession(sessionId));
    }

    @GetMapping("/api/ai-score/sessions/{sessionId}/jury/result")
    public Result<AiJuryReviewUserResponse> resultBySession(@PathVariable Long sessionId,
                                                            HttpServletRequest request) {
        assertSessionAccess(sessionId, request);
        return Result.success(juryReviewService.resultBySession(sessionId));
    }

    @GetMapping("/api/ai-score/sessions/{sessionId}/jury/report")
    public Result<AiJuryReviewUserResponse> reportBySession(@PathVariable Long sessionId,
                                                            HttpServletRequest request) {
        assertSessionAccess(sessionId, request);
        return Result.success(juryReviewService.resultBySession(sessionId));
    }

    @PostMapping("/api/ai/jury/{meetingId}/start")
    public AiJuryReviewUserResponse startByMeetingLegacy(@PathVariable Long meetingId,
                                                         HttpServletRequest request) {
        assertMeetingAccess(meetingId, request);
        return juryReviewService.startForLatestMeeting(meetingId);
    }

    @GetMapping("/api/ai/jury/{meetingId}/result")
    public AiJuryReviewUserResponse resultByMeetingLegacy(@PathVariable Long meetingId,
                                                          HttpServletRequest request) {
        assertMeetingAccess(meetingId, request);
        return juryReviewService.resultByLatestMeeting(meetingId);
    }

    private void assertSessionAccess(Long sessionId, HttpServletRequest request) {
        accessControlService.assertSessionAccess(
                scoringSessionService.requireSessionForAccess(sessionId),
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "role")
        );
    }

    private void assertMeetingAccess(Long meetingId, HttpServletRequest request) {
        AiScoringSession session = scoringSessionService.sessionForMeetingAccess(meetingId);
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "该会议暂未生成AI评分报告");
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
}
