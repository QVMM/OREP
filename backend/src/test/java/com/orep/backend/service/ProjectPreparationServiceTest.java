package com.orep.backend.service;

import com.orep.backend.dto.ProjectPreparationAiResponse;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.lang.reflect.Method;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ProjectPreparationServiceTest {

    @Test
    void ensureSchemaCreatesAgentStepTableAndDirectionScoreColumns() {
        TestHarness harness = harness("project_prep_agent_schema");
        JdbcTemplate jdbc = harness.jdbc;

        Integer stepTableCount = jdbc.queryForObject("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'project_prep_agent_step'
                """, Integer.class);
        Integer scoreColumnCount = jdbc.queryForObject("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'project_prep_direction'
                AND COLUMN_NAME IN ('scores_json', 'recommendation_level', 'expert_rationale')
                """, Integer.class);

        assertThat(stepTableCount).isEqualTo(1);
        assertThat(scoreColumnCount).isEqualTo(3);
    }

    @Test
    void sendMessageMarksSessionAiFailedWhenAiServiceRejects() {
        TestHarness harness = harness("project_prep_failure");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;

        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'DRAFT')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
        ProjectPreparationAiResponse rejected = new ProjectPreparationAiResponse();
        rejected.setAccepted(false);
        rejected.setMessage("Mimo 服务暂不可用");
        rejected.setModel("mimo-v2.5-pro");
        when(harness.aiClient.analyze(any())).thenReturn(rejected);

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "我们有传感器基础"),
                3L,
                12L,
                "STUDENT"
        );

        assertThat(result.get("accepted")).isEqualTo(true);
        assertThat(result.get("message")).isEqualTo("已提交选题策划生成");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_session WHERE id = 88", String.class))
                .isEqualTo("AI_FAILED");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE session_id = 88", String.class))
                .isEqualTo("FAILED");
        Map<String, Object> session = (Map<String, Object>) result.get("session");
        assertThat(session.get("status")).isEqualTo("AI_FAILED");
        assertThat((Map<String, Object>) session.get("latestRun")).containsEntry("status", "FAILED");
    }

    @Test
    void createDocumentReturnsExistingDraftForSameDirectionByDefault() {
        TestHarness harness = harness("project_prep_document_idempotent");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'ACTIVE')
                """);
        jdbc.update("""
                INSERT INTO project_prep_direction
                (id, session_id, title, summary, evidence_gaps_json, risks_json, next_tasks_json)
                VALUES (71, 88, '真实方向', '方向摘要', '[]', '[]', '[]')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队")));

        Map<String, Object> first = service.createDocument(88L, Map.of("directionId", 71L), 3L, 12L, "STUDENT");
        Map<String, Object> second = service.createDocument(88L, Map.of("directionId", 71L), 3L, 12L, "STUDENT");

        assertThat(first.get("alreadyGenerated")).isEqualTo(false);
        assertThat(second.get("alreadyGenerated")).isEqualTo(true);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_document WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
        assertThat((Map<String, Object>) second.get("document")).containsEntry("title", "真实方向 - 策划书草稿");
    }

    @Test
    void sendMessagePersistsGenerationAndSourceDisclosureWhenAiSucceeds() {
        TestHarness harness = harness("project_prep_success_generation");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'DRAFT')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("已基于真实材料生成方向。");
        accepted.setResearchSummary("公开资料显示节能方向值得关注，团队事实仅来自已上传材料。");
        accepted.setQuestions(List.of("赛项类别是什么？"));
        accepted.setSources(List.of(Map.of("title", "用户补充", "sourceType", "USER_INPUT")));
        accepted.setNextActions(List.of("采纳方向"));
        accepted.setModel("mimo-v2.5-pro");
        ProjectPreparationAiResponse.AgentStep agentStep = new ProjectPreparationAiResponse.AgentStep();
        agentStep.setAgentKey("topic_planner");
        agentStep.setAgentName("赵选题");
        agentStep.setAgentRole("选题总策划");
        agentStep.setStatus("COMPLETED");
        agentStep.setInputSummary("用户希望做温室选题。");
        agentStep.setOutputSummary("建议收窄到温室诊断。");
        agentStep.setFindings(List.of("边界清晰"));
        agentStep.setQuestions(List.of("是否有传感器数据？"));
        agentStep.setSources(List.of(Map.of("title", "用户补充", "sourceType", "USER_INPUT")));
        accepted.setAgentSteps(Arrays.asList(null, agentStep));
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("真实方向");
        direction.setSummary("方向摘要");
        direction.setEquipmentMatch("HIGH");
        direction.setCompetitionMatch("MEDIUM");
        direction.setRecommendationLevel("RECOMMENDED");
        direction.setExpertRationale("赵选题认为边界清晰，周可行认为可演示闭环较强。");
        ProjectPreparationAiResponse.DirectionScore scores = new ProjectPreparationAiResponse.DirectionScore();
        scores.setCompetitionFit(8);
        scores.setResourceFit(7);
        scores.setInnovation(6);
        scores.setDemoReadiness(8);
        scores.setRiskControl(6);
        direction.setScores(scores);
        direction.setEvidenceGaps(List.of("补充数据"));
        direction.setRisks(List.of("样本不足"));
        direction.setNextTasks(List.of(Map.of("title", "整理字段", "stageKey", "TOPIC")));
        direction.setResearchRefs(List.of(Map.of("title", "公开趋势", "sourceType", "PUBLIC_WEB")));
        accepted.setDirections(Arrays.asList(null, direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "我们有传感器基础"),
                3L,
                12L,
                "STUDENT"
        );

        Map<String, Object> session = (Map<String, Object>) result.get("session");
        List<Map<String, Object>> directions = (List<Map<String, Object>>) session.get("directions");
        Map<String, Object> latestRun = (Map<String, Object>) session.get("latestRun");
        assertThat(directions).hasSize(1);
        assertThat(directions.get(0)).containsEntry("generationNo", 1);
        assertThat(directions.get(0).get("aiRunId")).isNotNull();
        assertThat(directions.get(0)).containsEntry("recommendationLevel", "RECOMMENDED");
        assertThat((Map<String, Object>) directions.get(0).get("scores")).containsEntry("competitionFit", 8);
        assertThat(latestRun).containsEntry("researchSummary", accepted.getResearchSummary());
        List<Map<String, Object>> agentSteps = (List<Map<String, Object>>) latestRun.get("agentSteps");
        assertThat(agentSteps).hasSize(1);
        assertThat(agentSteps.get(0)).containsEntry("agentName", "赵选题");
        assertThat(agentSteps.get(0)).containsEntry("findings", List.of("边界清晰"));
        assertThat(agentSteps.get(0)).containsEntry("questions", List.of("是否有传感器数据？"));
        assertThat((List<Map<String, Object>>) agentSteps.get(0).get("sources"))
                .containsExactly(Map.of("title", "用户补充", "sourceType", "USER_INPUT"));
        assertThat(directions.get(0)).containsEntry("expertRationale", "赵选题认为边界清晰，周可行认为可演示闭环较强。");
        assertThat((List<Object>) latestRun.get("questions")).contains("赛项类别是什么？");
        assertThat(jdbc.queryForObject("SELECT generation_no FROM project_prep_direction WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_agent_step WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
    }

    @Test
    void sendMessageMarksAcceptedResponsePersistenceFailureAsAiFailed() {
        TestHarness harness = harness("project_prep_persistence_failure");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'DRAFT')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("已生成方向。 ");
        accepted.setModel("mimo-v2.5-pro");
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("   ");
        direction.setSummary("方向摘要");
        accepted.setDirections(List.of(direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "我们有传感器基础"),
                3L,
                12L,
                "STUDENT"
        );

        Map<String, Object> session = (Map<String, Object>) result.get("session");
        Map<String, Object> latestRun = (Map<String, Object>) session.get("latestRun");
        assertThat(session.get("status")).isEqualTo("AI_FAILED");
        assertThat(latestRun).containsEntry("status", "FAILED");
        assertThat((String) latestRun.get("errorMessage")).contains("方向标题不能为空");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_session WHERE id = 88", String.class))
                .isEqualTo("AI_FAILED");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE session_id = 88", String.class))
                .isEqualTo("FAILED");
    }

    @Test
    void sendMessagePersistsMissingDirectionScoresAsEmptyMap() {
        TestHarness harness = harness("project_prep_empty_scores");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'DRAFT')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("已生成方向。 ");
        accepted.setModel("mimo-v2.5-pro");
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("真实方向");
        direction.setSummary("方向摘要");
        accepted.setDirections(List.of(direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "我们有传感器基础"),
                3L,
                12L,
                "STUDENT"
        );

        Map<String, Object> session = (Map<String, Object>) result.get("session");
        List<Map<String, Object>> directions = (List<Map<String, Object>>) session.get("directions");
        assertThat(directions).hasSize(1);
        assertThat(directions.get(0).get("scores")).isEqualTo(Map.of());
        assertThat(jdbc.queryForObject("SELECT scores_json FROM project_prep_direction WHERE session_id = 88", String.class))
                .isEqualTo("{}");
    }

    @Test
    void sendMessageDoesNotCreateSecondRunWhenSessionAlreadyRunning() {
        TestHarness harness = harness("project_prep_running_blocks_second_run");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
                """);
        jdbc.update("""
                INSERT INTO project_prep_ai_run (session_id, run_type, status, started_at)
                VALUES (88, 'TOPIC_PLANNING', 'RUNNING', ?)
                """, LocalDateTime.now().minusMinutes(2));
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队")));

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "再补充一个选题方向"),
                3L,
                12L,
                "STUDENT"
        );

        assertThat(result.get("accepted")).isEqualTo(true);
        assertThat(result.get("message")).isEqualTo("上一轮选题策划仍在生成中");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_message WHERE session_id = 88", Integer.class))
                .isZero();
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE session_id = 88", String.class))
                .isEqualTo("RUNNING");
        verify(harness.aiClient, never()).analyze(any());
    }

    @Test
    void sendMessageExpiresStaleRunningRunBeforeCreatingNewRun() {
        TestHarness harness = harness("project_prep_expires_stale_run");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
                """);
        jdbc.update("""
                INSERT INTO project_prep_ai_run (session_id, run_type, status, started_at)
                VALUES (88, 'TOPIC_PLANNING', 'RUNNING', ?)
                """, LocalDateTime.now().minusMinutes(11));
        Long staleRunId = jdbc.queryForObject("SELECT id FROM project_prep_ai_run WHERE session_id = 88", Long.class);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        when(harness.scriptService.listByUserId(12L)).thenReturn(List.of());
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("已生成新方向。");
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("新方向");
        direction.setSummary("方向摘要");
        accepted.setDirections(List.of(direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        Map<String, Object> result = service.sendMessage(
                88L,
                Map.of("content", "旧任务卡住了，请重新生成"),
                3L,
                12L,
                "STUDENT"
        );

        Long newRunId = (Long) result.get("runId");
        assertThat(newRunId).isNotEqualTo(staleRunId);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88", Integer.class))
                .isEqualTo(2);
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE id = ?", String.class, staleRunId))
                .isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("SELECT error_message FROM project_prep_ai_run WHERE id = ?", String.class, staleRunId))
                .isEqualTo("AI 运行超时，已允许重新提交");
        assertThat(jdbc.queryForObject("SELECT completed_at FROM project_prep_ai_run WHERE id = ?", LocalDateTime.class, staleRunId))
                .isNotNull();
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE id = ?", String.class, newRunId))
                .isEqualTo("COMPLETED");
    }

    @Test
    void sessionExpiresStaleRunningRunAndReturnsFailedPayload() {
        TestHarness harness = harness("project_prep_session_expires_stale_run");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
                """);
        jdbc.update("""
                INSERT INTO project_prep_ai_run (session_id, run_type, status, started_at)
                VALUES (88, 'TOPIC_PLANNING', 'RUNNING', ?)
                """, LocalDateTime.now().minusMinutes(11));
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队")));

        Map<String, Object> session = service.session(88L, 3L, 12L, "STUDENT");

        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE session_id = 88", String.class))
                .isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_session WHERE id = 88", String.class))
                .isEqualTo("AI_FAILED");
        assertThat(session.get("status")).isEqualTo("AI_FAILED");
        Map<String, Object> latestRun = (Map<String, Object>) session.get("latestRun");
        assertThat(latestRun).containsEntry("status", "FAILED");
        assertThat(latestRun).containsEntry("errorMessage", "AI 运行超时，已允许重新提交");
    }

    @Test
    void completeAiRunDoesNotPersistWhenRunIsNoLongerRunning() throws Exception {
        TestHarness harness = harness("project_prep_expired_completion_guard");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_FAILED')
                """);
        jdbc.update("""
                INSERT INTO project_prep_ai_run (id, session_id, run_type, status, started_at, completed_at, error_message)
                VALUES (101, 88, 'TOPIC_PLANNING', 'FAILED', ?, ?, 'AI 运行超时，已允许重新提交')
                """, LocalDateTime.now().minusMinutes(12), LocalDateTime.now().minusMinutes(1));
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("迟到的旧响应不应写入。");
        ProjectPreparationAiResponse.AgentStep agentStep = new ProjectPreparationAiResponse.AgentStep();
        agentStep.setAgentName("赵选题");
        accepted.setAgentSteps(List.of(agentStep));
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("旧方向");
        direction.setSummary("旧摘要");
        accepted.setDirections(List.of(direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        Method method = ProjectPreparationService.class.getDeclaredMethod(
                "completeAiRun", Long.class, Long.class, Map.class, Map.class);
        method.setAccessible(true);
        method.invoke(service, 88L, 101L, Map.of("sessionId", 88L), Map.of("teamId", 9L));

        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE id = 101", String.class))
                .isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_session WHERE id = 88", String.class))
                .isEqualTo("AI_FAILED");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_message WHERE session_id = 88", Integer.class))
                .isZero();
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_agent_step WHERE session_id = 88", Integer.class))
                .isZero();
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_direction WHERE session_id = 88", Integer.class))
                .isZero();
    }

    @Test
    void sendMessageSerializesConcurrentSubmissionsForSameSession() throws Exception {
        ConcurrentLinkedQueue<Runnable> queuedAiTasks = new ConcurrentLinkedQueue<>();
        TestHarness harness = harness("project_prep_concurrent_send", queuedAiTasks::add);
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'DRAFT')
                """);
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "真实团队"),
                        "members", List.of(),
                        "tasks", List.of(),
                        "materials", List.of()
                ));
        CountDownLatch firstContextStarted = new CountDownLatch(1);
        CountDownLatch releaseFirstContext = new CountDownLatch(1);
        AtomicInteger scriptCalls = new AtomicInteger();
        when(harness.scriptService.listByUserId(12L)).thenAnswer(invocation -> {
            if (scriptCalls.incrementAndGet() == 1) {
                firstContextStarted.countDown();
                assertThat(releaseFirstContext.await(2, TimeUnit.SECONDS)).isTrue();
            }
            return List.of();
        });
        ProjectPreparationAiResponse accepted = new ProjectPreparationAiResponse();
        accepted.setAccepted(true);
        accepted.setAssistantMessage("已生成方向。");
        ProjectPreparationAiResponse.Direction direction = new ProjectPreparationAiResponse.Direction();
        direction.setTitle("真实方向");
        direction.setSummary("方向摘要");
        accepted.setDirections(List.of(direction));
        when(harness.aiClient.analyze(any())).thenReturn(accepted);

        List<Map<String, Object>> results = new ArrayList<>();
        CountDownLatch secondCompleted = new CountDownLatch(1);
        Thread first = new Thread(() -> results.add(service.sendMessage(
                88L, Map.of("content", "第一条补充"), 3L, 12L, "STUDENT")));
        Thread second = new Thread(() -> {
            try {
                assertThat(firstContextStarted.await(2, TimeUnit.SECONDS)).isTrue();
                results.add(service.sendMessage(88L, Map.of("content", "第二条补充"), 3L, 12L, "STUDENT"));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(e);
            } finally {
                secondCompleted.countDown();
            }
        });

        first.start();
        second.start();
        assertThat(firstContextStarted.await(2, TimeUnit.SECONDS)).isTrue();
        releaseFirstContext.countDown();
        first.join(2000);
        second.join(2000);

        assertThat(secondCompleted.await(1, TimeUnit.SECONDS)).isTrue();
        assertThat(results).hasSize(2);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_ai_run WHERE session_id = 88 AND status = 'RUNNING'", Integer.class))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM project_prep_message WHERE session_id = 88", Integer.class))
                .isEqualTo(1);
        assertThat(results.stream().filter(result -> "已提交选题策划生成".equals(result.get("message"))).count())
                .isEqualTo(1);
        assertThat(results.stream().filter(result -> "上一轮选题策划仍在生成中".equals(result.get("message"))).count())
                .isEqualTo(1);

        Runnable task = queuedAiTasks.poll();
        assertThat(task).isNotNull();
        task.run();
        assertThat(queuedAiTasks).isEmpty();
        verify(harness.aiClient, times(1)).analyze(any());
    }

    @Test
    void sendMessageExpiresStaleRunAndMarksSessionFailedBeforeContentValidation() {
        TestHarness harness = harness("project_prep_expire_before_validation");
        JdbcTemplate jdbc = harness.jdbc;
        ProjectPreparationService service = harness.service;
        jdbc.update("""
                INSERT INTO project_prep_session (id, tenant_id, team_id, created_by, title, status)
                VALUES (88, 3, 9, 12, '真实团队 选题策划', 'AI_RUNNING')
                """);
        jdbc.update("""
                INSERT INTO project_prep_ai_run (session_id, run_type, status, started_at)
                VALUES (88, 'TOPIC_PLANNING', 'RUNNING', ?)
                """, LocalDateTime.now().minusMinutes(11));
        when(harness.projectTeamService.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("team", Map.of("id", 9L, "name", "真实团队")));

        assertThatThrownBy(() -> service.sendMessage(88L, Map.of("content", "   "), 3L, 12L, "STUDENT"))
                .hasMessageContaining("补充信息不能为空");

        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_ai_run WHERE session_id = 88", String.class))
                .isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("SELECT status FROM project_prep_session WHERE id = 88", String.class))
                .isEqualTo("AI_FAILED");
        verify(harness.aiClient, never()).analyze(any());
    }

    private TestHarness harness(String databaseName) {
        return harness(databaseName, Runnable::run);
    }

    private TestHarness harness(String databaseName, Executor aiExecutor) {
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:" + databaseName + ";MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        ProjectTeamService projectTeamService = mock(ProjectTeamService.class);
        ScriptService scriptService = mock(ScriptService.class);
        ScriptTemplateService scriptTemplateService = mock(ScriptTemplateService.class);
        ResourceService resourceService = mock(ResourceService.class);
        ProjectPreparationAiClient aiClient = mock(ProjectPreparationAiClient.class);
        ProjectPreparationService service = new ProjectPreparationService(
                jdbc, projectTeamService, scriptService, scriptTemplateService, resourceService, aiClient, aiExecutor);
        service.ensureSchema();
        return new TestHarness(jdbc, projectTeamService, scriptService, aiClient, service);
    }

    private record TestHarness(
            JdbcTemplate jdbc,
            ProjectTeamService projectTeamService,
            ScriptService scriptService,
            ProjectPreparationAiClient aiClient,
            ProjectPreparationService service
    ) {}
}
