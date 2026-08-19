package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.AiScoreSpeakerIdentityService;
import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreSessionControllerTest {

    @Test
    void correctsSpeakerIdentityAfterCheckingSessionAccess() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreSpeakerIdentityService identityService = mock(AiScoreSpeakerIdentityService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        AiScoreSpeakerIdentity identity = new AiScoreSpeakerIdentity();
        identity.setRawSpeakerLabel("SPEAKER_2");
        identity.setDisplayName("3号选手");
        identity.setRoleName("AI算法工程师");
        identity.setStatus("CONFIRMED");
        identity.setConfidence(BigDecimal.ONE);
        identity.setRevision(2);
        when(identityService.confirm(101L, "SPEAKER_2", "3号选手", "AI算法工程师", 7L))
                .thenReturn(identity);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access,
                identityService)).build();

        mvc.perform(patch("/api/ai-score/sessions/101/speakers/SPEAKER_2")
                        .requestAttr("userId", 7L)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"displayName\":\"3号选手\",\"roleName\":\"AI算法工程师\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.rawSpeaker").value("SPEAKER_2"))
                .andExpect(jsonPath("$.data.displayName").value("3号选手"))
                .andExpect(jsonPath("$.data.roleName").value("AI算法工程师"))
                .andExpect(jsonPath("$.data.status").value("CONFIRMED"))
                .andExpect(jsonPath("$.data.revision").value(2));
    }

    @Test
    void updatesRemediationTaskExecutionStatus() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(sessionService.updateRemediationTaskStatus(55L, 91L, "in_progress"))
                .thenReturn(Map.of("taskRecordId", 91L, "taskId", "task-demo", "status", "in_progress"));
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class))).build();

        mvc.perform(patch("/api/ai-score/reports/55/remediation-tasks/91/status")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"in_progress\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.taskRecordId").value(91))
                .andExpect(jsonPath("$.data.status").value("in_progress"));
    }

    @Test
    void createsAndReturnsRedactedSessionResponse() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(sessionService.createSession(any(AiScoringSessionCreateRequest.class), eq(7L)))
                .thenReturn(sessionResponse("created"));
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                mock(AiScoreAccessControlService.class))).build();

        mvc.perform(post("/api/ai-score/sessions")
                        .requestAttr("userId", 7L)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"sourceType":"meeting_recording","meetingId":12,"projectId":3,"teamId":9,"trackId":"track-it","trackName":"新一代信息技术赛道"}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(101))
                .andExpect(jsonPath("$.data.status").value("created"))
                .andExpect(jsonPath("$.data.rubricHash").doesNotExist())
                .andExpect(jsonPath("$.data.rubricPath").doesNotExist())
                .andExpect(jsonPath("$.data.internalVersion").doesNotExist());
    }

    @Test
    void createSessionRejectsStudentAttachingAnotherTeam() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertTeamAccess(eq(1L), eq(3L), eq(10L), eq("STUDENT"));

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(post("/api/ai-score/sessions")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"sourceType":"uploaded_video","teamId":1,"trackId":"track-it","trackName":"新一代信息技术赛道"}
                                """))
                .andExpect(status().isForbidden());
        verify(sessionService, never()).createSession(any(), any());
    }

    @Test
    void statusActionsReturnSessionStatus() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        when(sessionService.start(101L)).thenReturn(sessionResponse("scoring"));
        when(sessionService.cancel(101L)).thenReturn(sessionResponse("cancelled"));
        when(sessionService.restart(101L)).thenReturn(sessionResponse("created"));
        when(sessionService.getStatus(101L)).thenReturn(sessionResponse("created"));
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(post("/api/ai-score/sessions/101/start")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("scoring"));
        mvc.perform(post("/api/ai-score/sessions/101/cancel")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("cancelled"));
        mvc.perform(post("/api/ai-score/sessions/101/restart")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("created"));
    }

    @Test
    void reportBySessionReturnsLegacyReportWithoutInternalFields() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreReportUserResponse report = new AiScoreReportUserResponse();
        report.setReportId(55L);
        report.setSessionId(101L);
        report.setSessionNo("SC-20260623120000001");
        report.setMeetingId(12L);
        report.setOverallScore(new BigDecimal("82.5"));
        report.setStatus("completed");
        AiScoreReportUserResponse.StructuredObservation observation = new AiScoreReportUserResponse.StructuredObservation();
        observation.setId(1L);
        observation.setDimensionName("技术能力");
        observation.setRawScore(new BigDecimal("90"));
        observation.setScoreCap(new BigDecimal("95"));
        observation.setEvidenceAnchorIds(List.of(10L));
        report.setStructuredObservations(List.of(observation));
        AiScoreReportUserResponse.StructuredDeduction deduction = new AiScoreReportUserResponse.StructuredDeduction();
        deduction.setId(2L);
        deduction.setDimensionName("技术能力");
        deduction.setDeductedPoints(new BigDecimal("5"));
        deduction.setRecoveredPoints(BigDecimal.ZERO);
        deduction.setReason("关键算法测试数据不足");
        deduction.setRecovery(false);
        report.setStructuredDeductions(List.of(deduction));
        AiScoreReportUserResponse.EvidenceAnchor anchor = new AiScoreReportUserResponse.EvidenceAnchor();
        anchor.setId(10L);
        anchor.setAnchorType("frame_ocr");
        anchor.setEvidenceText("核心演示流程稳定跑通");
        report.setEvidenceAnchors(List.of(anchor));
        AiScoreReportUserResponse.ScoreRecoverySummary summary = new AiScoreReportUserResponse.ScoreRecoverySummary();
        summary.setRecoveredCount(1);
        summary.setRecoveredPoints(new BigDecimal("6"));
        summary.setCurrentDeductedPoints(new BigDecimal("5"));
        summary.setNewIssueCount(1);
        summary.setNotPerfectReasons(List.of("current_deductions"));
        report.setScoreRecoverySummary(summary);
        when(sessionService.reportBySession(eq(101L), any())).thenReturn(report);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/reports/by-session/101")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.reportId").value(55))
                .andExpect(jsonPath("$.data.sessionId").value(101))
                .andExpect(jsonPath("$.data.overallScore").value(82.5))
                .andExpect(jsonPath("$.data.structuredObservations[0].dimensionName").value("技术能力"))
                .andExpect(jsonPath("$.data.structuredDeductions[0].reason").value("关键算法测试数据不足"))
                .andExpect(jsonPath("$.data.evidenceAnchors[0].evidenceText").value("核心演示流程稳定跑通"))
                .andExpect(jsonPath("$.data.scoreRecoverySummary.recoveredCount").value(1))
                .andExpect(jsonPath("$.data.scoreRecoverySummary.notPerfectReasons[0]").value("current_deductions"))
                .andExpect(jsonPath("$.data.rubric_hash").doesNotExist())
                .andExpect(jsonPath("$.data.prompt").doesNotExist())
                .andExpect(jsonPath("$.data.weight").doesNotExist());
    }

    @Test
    void publishTaskBookRequiresTeacherRoleAndReturnsReport() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        accessSession.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        AiScoreReportUserResponse report = new AiScoreReportUserResponse();
        report.setSessionId(101L);
        TaskBook book = new TaskBook();
        book.setPublished(true);
        report.setTaskBook(book);
        when(sessionService.publishTaskBook(eq(101L), eq("TEACHER"))).thenReturn(report);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(post("/api/ai-score/sessions/101/task-book/publish")
                        .requestAttr("userId", 7L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(101))
                .andExpect(jsonPath("$.data.taskBook.published").value(true));
    }

    @Test
    void hangTaskBookEvidenceRequiresSessionAccess() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(52L);
        accessSession.setCreatedBy(10L);
        when(sessionService.requireSessionForAccess(52L)).thenReturn(accessSession);
        AiScoreReportUserResponse report = new AiScoreReportUserResponse();
        report.setSessionId(52L);
        TaskBook book = new TaskBook();
        book.setPublished(true);
        TaskBookItem item = new TaskBookItem();
        item.setTitle("补齐差异与仓库证据");
        item.setHungEvidence("仓库 diff");
        book.setItems(List.of(item));
        report.setTaskBook(book);
        when(sessionService.hangTaskBookEvidence(eq(52L), eq(0), eq("仓库 diff"), eq(10L), eq("STUDENT")))
                .thenReturn(report);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(post("/api/ai-score/sessions/52/task-book/items/0/hang")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"evidence\":\"仓库 diff\"}")
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.taskBook.items[0].hungEvidence").value("仓库 diff"));
    }

    @Test
    void confirmDeliberationRequiresTeacherRole() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession accessSession = new AiScoringSession();
        accessSession.setId(101L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(accessSession);
        AiScoreReportUserResponse report = new AiScoreReportUserResponse();
        report.setSessionId(101L);
        report.setTeacherConfirmed(true);
        when(sessionService.confirmDeliberation(eq(101L), eq("TEACHER"), eq(7L))).thenReturn(report);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(post("/api/ai-score/sessions/101/confirm")
                        .requestAttr("userId", 7L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.teacherConfirmed").value(true));
    }

    private AiScoringSessionUserResponse sessionResponse(String status) {
        AiScoringSessionUserResponse response = new AiScoringSessionUserResponse();
        response.setSessionId(101L);
        response.setSessionNo("SC-20260623120000001");
        response.setStatus(status);
        response.setCurrentStage(status);
        response.setProgressPercent("scoring".equals(status) ? 10 : 0);
        response.setTrackName("新一代信息技术赛道");
        response.setSourceType("meeting_recording");
        response.setUseHistoryMemory(true);
        response.setJuryEnabled(false);
        response.setCached(false);
        response.setMeetingId(12L);
        return response;
    }

    @Test
    void statusRejectsCrossTeamUserBeforeReturningSession() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(101L);
        session.setTeamId(9L);
        session.setCreatedBy(7L);
        when(sessionService.requireSessionForAccess(101L)).thenReturn(session);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/sessions/101/status")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void reportByReportRejectsCrossTeamUser() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(21L);
        session.setTeamId(9L);
        session.setCreatedBy(7L);
        when(sessionService.sessionForReportAccess(33L)).thenReturn(session);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/reports/by-report/33")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void reportByMeetingRejectsCrossTeamUser() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(21L);
        session.setTeamId(9L);
        session.setCreatedBy(7L);
        when(sessionService.sessionForMeetingAccess(4L)).thenReturn(session);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/reports/by-meeting/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void reportByReportAllowsTeamMember() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(47L);
        session.setTeamId(3L);
        session.setCreatedBy(16L);
        when(sessionService.sessionForReportAccess(55L)).thenReturn(session);
        AiScoreReportUserResponse response = new AiScoreReportUserResponse();
        response.setSessionId(47L);
        response.setReportId(55L);
        when(sessionService.reportByReportId(55L, "STUDENT")).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/reports/by-report/55")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(47))
                .andExpect(jsonPath("$.data.reportId").value(55));
    }

    @Test
    void reportByReportWithoutSessionIsHidden() throws Exception {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        when(sessionService.sessionForReportAccess(21L)).thenReturn(null);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();

        mvc.perform(get("/api/ai-score/reports/by-report/21")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    void meetingPdfRejectsCrossTeamUser() throws Exception {
        MockMvc mvc = meetingShortcutMvc(true);
        mvc.perform(get("/api/ai-score/pdf/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void meetingStatusRejectsCrossTeamUser() throws Exception {
        MockMvc mvc = meetingShortcutMvc(true);
        mvc.perform(get("/api/ai-score/status/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void meetingReportJsonRejectsCrossTeamUser() throws Exception {
        MockMvc mvc = meetingShortcutMvc(true);
        mvc.perform(get("/api/ai-score/report/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 8L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isForbidden());
    }

    @Test
    void meetingStatusWithoutSessionIsHidden() throws Exception {
        MockMvc mvc = meetingShortcutMvc(false);
        mvc.perform(get("/api/ai-score/status/4")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 10L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(jsonPath("$.code").value(404));
    }

    private static MockMvc meetingShortcutMvc(boolean sessionExists) {
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
        if (sessionExists) {
            AiScoringSession session = new AiScoringSession();
            session.setId(21L);
            session.setTeamId(9L);
            session.setCreatedBy(7L);
            when(sessionService.sessionForMeetingAccess(4L)).thenReturn(session);
            doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话"))
                    .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));
        } else {
            when(sessionService.sessionForMeetingAccess(4L)).thenReturn(null);
        }
        return standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                mock(AiScoreEvidenceBundleService.class),
                mock(AiScoreStructuredResultService.class),
                access)).build();
    }
}
