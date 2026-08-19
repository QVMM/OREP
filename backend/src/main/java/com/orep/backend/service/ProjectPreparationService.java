package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.ProjectPreparationAiResponse;
import com.orep.backend.entity.Resource;
import com.orep.backend.entity.Script;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class ProjectPreparationService {
    private static final int PREP_RUN_STALE_MINUTES = 10;

    private final JdbcTemplate jdbc;
    private final ProjectTeamService projectTeamService;
    private final ScriptService scriptService;
    private final ScriptTemplateService scriptTemplateService;
    private final ResourceService resourceService;
    private final ProjectPreparationAiClient aiClient;
    private final Executor aiExecutor;
    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private final ConcurrentHashMap<Long, Object> sessionLocks = new ConcurrentHashMap<>();

    @Autowired
    public ProjectPreparationService(
            JdbcTemplate jdbc,
            ProjectTeamService projectTeamService,
            ScriptService scriptService,
            ScriptTemplateService scriptTemplateService,
            ResourceService resourceService,
            ProjectPreparationAiClient aiClient
    ) {
        this(jdbc, projectTeamService, scriptService, scriptTemplateService, resourceService, aiClient,
                defaultAiExecutor());
    }

    private static Executor defaultAiExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setThreadNamePrefix("project-prep-ai-");
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(4);
        executor.setQueueCapacity(50);
        executor.initialize();
        return executor;
    }

    ProjectPreparationService(
            JdbcTemplate jdbc,
            ProjectTeamService projectTeamService,
            ScriptService scriptService,
            ScriptTemplateService scriptTemplateService,
            ResourceService resourceService,
            ProjectPreparationAiClient aiClient,
            Executor aiExecutor
    ) {
        this.jdbc = jdbc;
        this.projectTeamService = projectTeamService;
        this.scriptService = scriptService;
        this.scriptTemplateService = scriptTemplateService;
        this.resourceService = resourceService;
        this.aiClient = aiClient;
        this.aiExecutor = aiExecutor;
    }

    @PostConstruct
    public void ensureSchema() {
        try (InputStream in = new ClassPathResource("sql/create_project_preparation_tables.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
            ensureSchemaUpgrades();
        } catch (Exception e) {
            throw new IllegalStateException("项目准备表初始化失败", e);
        }
    }

    private void ensureSchemaUpgrades() {
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN ai_run_id BIGINT DEFAULT NULL");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN generation_no INT NOT NULL DEFAULT 1");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD INDEX idx_project_prep_direction_run (session_id, ai_run_id)");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN scores_json TEXT");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN recommendation_level VARCHAR(40) DEFAULT NULL");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE project_prep_direction ADD COLUMN expert_rationale TEXT");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                    CREATE TABLE IF NOT EXISTS project_prep_agent_step (
                      id BIGINT NOT NULL AUTO_INCREMENT,
                      session_id BIGINT NOT NULL,
                      ai_run_id BIGINT NOT NULL,
                      step_no INT NOT NULL,
                      agent_key VARCHAR(80) NOT NULL,
                      agent_name VARCHAR(80) NOT NULL,
                      agent_role VARCHAR(120) NOT NULL,
                      status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
                      input_summary TEXT,
                      output_summary TEXT,
                      findings_json TEXT,
                      questions_json TEXT,
                      sources_json TEXT,
                      started_at DATETIME DEFAULT NULL,
                      completed_at DATETIME DEFAULT NULL,
                      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      PRIMARY KEY (id),
                      UNIQUE KEY uk_project_prep_agent_step (session_id, ai_run_id, step_no),
                      KEY idx_project_prep_agent_step_run (session_id, ai_run_id),
                      KEY idx_project_prep_agent_step_agent (session_id, agent_key)
                    )
                    """);
        } catch (Exception ignored) {
        }
    }

    public Map<String, Object> bootstrap(Long requestedTeamId, Long tenantId, Long userId, String role) {
        List<Map<String, Object>> teams = projectTeamService.myTeams(tenantId, userId, role);
        Long activeTeamId = pickTeamId(requestedTeamId, teams);
        Map<String, Object> dashboard = activeTeamId == null
                ? Map.of()
                : projectTeamService.dashboard(activeTeamId, tenantId, userId, role);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("teams", teams);
        result.put("activeTeamId", activeTeamId);
        result.put("dashboard", dashboard);
        result.put("scripts", scriptService.listByUserId(userId));
        result.put("scriptTemplates", scriptTemplateService.listAvailable(userId));
        result.put("resources", resourceService.list().stream().map(this::resourceView).toList());
        result.put("prepSession", activeTeamId == null ? null : loadOrCreateSession(activeTeamId, tenantId, userId, dashboard));
        result.put("workspaces", List.of("topic-planning", "materials", "ppt", "script", "roadshow", "versions"));
        return result;
    }

    public Map<String, Object> teamWorkspace(Long teamId, Long tenantId, Long userId, String role) {
        Map<String, Object> dashboard = projectTeamService.dashboard(teamId, tenantId, userId, role);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("activeTeamId", teamId);
        result.put("dashboard", dashboard);
        result.put("prepSession", loadOrCreateSession(teamId, tenantId, userId, dashboard));
        return result;
    }

    public Map<String, Object> session(Long sessionId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        Long teamId = longValue(row.get("team_id"));
        projectTeamService.dashboard(teamId, tenantId, userId, role);
        return refreshedSessionPayload(sessionId);
    }

    public Map<String, Object> sendMessage(Long sessionId, Map<String, Object> body, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        Long teamId = longValue(row.get("team_id"));
        Map<String, Object> dashboard = projectTeamService.dashboard(teamId, tenantId, userId, role);
        Long userMessageId;
        Long runId;
        Map<String, Object> request;
        Map<String, Object> context;
        synchronized (lockForSession(sessionId)) {
            expireStaleRuns(sessionId);
            Map<String, Object> runningRun = activeRunningRun(sessionId);
            if (!runningRun.isEmpty()) {
                Map<String, Object> result = new LinkedHashMap<>();
                result.put("accepted", true);
                result.put("message", "上一轮选题策划仍在生成中");
                result.put("runId", longValue(runningRun.get("id")));
                result.put("session", sessionPayload(sessionRow(sessionId)));
                return result;
            }
            String content = requiredText(body.get("content"), "补充信息不能为空");
            userMessageId = insert("""
                    INSERT INTO project_prep_message (session_id, role, content, source_type)
                    VALUES (?, 'USER', ?, 'USER_INPUT')
                    """, sessionId, content);

            context = contextSnapshot(teamId, dashboard, userId);
            request = new LinkedHashMap<>();
            request.put("sessionId", sessionId);
            request.put("teamId", teamId);
            request.put("context", context);
            request.put("messages", messages(sessionId));
            request.put("latestUserMessage", content);

            runId = insert("""
                    INSERT INTO project_prep_ai_run
                    (session_id, run_type, status, request_json, started_at)
                    VALUES (?, 'TOPIC_PLANNING', 'RUNNING', ?, ?)
                    """, sessionId, json(request), LocalDateTime.now());

            jdbc.update("""
                    UPDATE project_prep_session
                    SET context_snapshot_json = ?, status = 'AI_RUNNING'
                    WHERE id = ?
                    """, json(context), sessionId);
        }

        Long submittedRunId = runId;
        Map<String, Object> submittedRequest = request;
        Map<String, Object> submittedContext = context;
        CompletableFuture.runAsync(() -> completeAiRun(sessionId, submittedRunId, submittedRequest, submittedContext), aiExecutor);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("accepted", true);
        result.put("message", "已提交选题策划生成");
        result.put("userMessageId", userMessageId);
        result.put("runId", runId);
        result.put("session", sessionPayload(sessionRow(sessionId)));
        return result;
    }

    private void completeAiRun(Long sessionId, Long runId, Map<String, Object> request, Map<String, Object> context) {
        ProjectPreparationAiResponse response;
        try {
            response = aiClient.analyze(request);
        } catch (Exception e) {
            response = new ProjectPreparationAiResponse();
            response.setAccepted(false);
            response.setMessage("AI 服务调用异常: " + e.getMessage());
        }
        synchronized (lockForSession(sessionId)) {
            if (!isRunRunning(runId)) {
                return;
            }
            if (!response.isAccepted()) {
                int updated = jdbc.update("""
                        UPDATE project_prep_ai_run
                        SET status = 'FAILED', response_json = ?, error_message = ?, model = ?, completed_at = ?
                        WHERE id = ? AND status = 'RUNNING'
                        """, json(response), response.getMessage(), response.getModel(), LocalDateTime.now(), runId);
                if (updated > 0) {
                    jdbc.update("""
                            UPDATE project_prep_session
                            SET context_snapshot_json = ?, status = 'AI_FAILED'
                            WHERE id = ?
                            """, json(context), sessionId);
                }
                return;
            }

            try {
                String assistantMessage = firstNonBlank(response.getAssistantMessage(), response.getMessage(), "已生成选题策划建议。");
                insert("""
                        INSERT INTO project_prep_message (session_id, role, content, source_type, model)
                        VALUES (?, 'ASSISTANT', ?, 'MIMO_WEB', ?)
                        """, sessionId, assistantMessage, response.getModel());
                saveAgentSteps(sessionId, runId, response.getAgentSteps());
                int generationNo = nextGenerationNo(sessionId);
                for (ProjectPreparationAiResponse.Direction direction : response.getDirections()) {
                    if (direction == null) continue;
                    saveDirection(sessionId, runId, generationNo, direction);
                }
                int updated = jdbc.update("""
                        UPDATE project_prep_ai_run
                        SET status = 'COMPLETED', response_json = ?, model = ?, completed_at = ?
                        WHERE id = ? AND status = 'RUNNING'
                        """, json(response), response.getModel(), LocalDateTime.now(), runId);
                if (updated > 0) {
                    jdbc.update("""
                            UPDATE project_prep_session
                            SET context_snapshot_json = ?, status = 'ACTIVE'
                            WHERE id = ?
                            """, json(context), sessionId);
                }
            } catch (Exception e) {
                String errorMessage = firstNonBlank(e.getMessage(), e.getClass().getSimpleName());
                int updated = jdbc.update("""
                        UPDATE project_prep_ai_run
                        SET status = 'FAILED', response_json = ?, error_message = ?, model = ?, completed_at = ?
                        WHERE id = ? AND status = 'RUNNING'
                        """, safeJson(response), errorMessage, response.getModel(), LocalDateTime.now(), runId);
                if (updated > 0) {
                    jdbc.update("""
                            UPDATE project_prep_session
                            SET context_snapshot_json = ?, status = 'AI_FAILED'
                            WHERE id = ?
                            """, json(context), sessionId);
                }
            }
        }
    }

    public Map<String, Object> selectDirection(Long sessionId, Long directionId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        projectTeamService.dashboard(longValue(row.get("team_id")), tenantId, userId, role);
        assertDirectionInSession(sessionId, directionId);
        jdbc.update("UPDATE project_prep_direction SET selected = 0 WHERE session_id = ?", sessionId);
        jdbc.update("UPDATE project_prep_direction SET selected = 1 WHERE id = ?", directionId);
        jdbc.update("UPDATE project_prep_session SET active_direction_id = ?, status = 'ACTIVE' WHERE id = ?", directionId, sessionId);
        return sessionPayload(sessionRow(sessionId));
    }

    public Map<String, Object> createTasksFromDirection(Long sessionId, Long directionId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        Long teamId = longValue(row.get("team_id"));
        projectTeamService.dashboard(teamId, tenantId, userId, role);
        Map<String, Object> direction = directionRow(sessionId, directionId);
        List<Map<String, Object>> existing = generatedTasks(sessionId, directionId);
        if (!existing.isEmpty()) {
            return Map.of(
                    "alreadyGenerated", true,
                    "createdTasks", existing,
                    "dashboard", projectTeamService.dashboard(teamId, tenantId, userId, role)
            );
        }
        List<Map<String, Object>> nextTasks = parseListMap(direction.get("next_tasks_json"));
        if (nextTasks.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该方向没有可生成的任务");
        }
        List<Map<String, Object>> created = nextTasks.stream()
                .map(task -> projectTeamService.createTask(teamId, tenantId, userId, role, Map.of(
                        "stageKey", firstNonBlank(text(task.get("stageKey")), "TOPIC"),
                        "title", firstNonBlank(text(task.get("title")), text(task.get("name")), "补充选题证据"),
                        "description", firstNonBlank(text(task.get("description")), text(task.get("detail")), ""),
                        "priority", firstNonBlank(text(task.get("priority")), "MEDIUM"),
                        "status", "TODO",
                        "reviewRequired", true
                )))
                .toList();
        for (Map<String, Object> task : created) {
            Long taskId = longValue(task.get("id"));
            if (taskId != null) {
                jdbc.update("""
                        INSERT INTO project_prep_task_generation (session_id, direction_id, task_id, task_title)
                        VALUES (?, ?, ?, ?)
                        """, sessionId, directionId, taskId, firstNonBlank(text(task.get("title")), "生成任务"));
            }
        }
        return Map.of(
                "alreadyGenerated", false,
                "createdTasks", created,
                "dashboard", projectTeamService.dashboard(teamId, tenantId, userId, role)
        );
    }

    public Map<String, Object> createDocument(Long sessionId, Map<String, Object> body, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        projectTeamService.dashboard(longValue(row.get("team_id")), tenantId, userId, role);
        Long directionId = longValue(body.get("directionId"));
        if (directionId == null) directionId = longValue(row.get("active_direction_id"));
        Map<String, Object> direction = directionId == null ? Map.of() : directionRow(sessionId, directionId);
        boolean regenerate = Boolean.TRUE.equals(body.get("regenerate"));
        if (!regenerate) {
            Map<String, Object> existing = latestDocument(sessionId, directionId);
            if (!existing.isEmpty()) {
                return Map.of("alreadyGenerated", true, "document", existing);
            }
        }
        String title = "选题策划书草稿";
        if (!direction.isEmpty()) title = text(direction.get("title")) + " - 策划书草稿";
        String content = buildDocumentContent(row, direction);
        Long documentId = insert("""
                INSERT INTO project_prep_document (session_id, direction_id, title, content, created_by)
                VALUES (?, ?, ?, ?, ?)
                """, sessionId, directionId, title, content, userId);
        return Map.of("alreadyGenerated", false, "document", document(documentId));
    }

    public Map<String, Object> documentDetail(Long sessionId, Long documentId, Long tenantId, Long userId, String role) {
        Map<String, Object> row = sessionRow(sessionId);
        projectTeamService.dashboard(longValue(row.get("team_id")), tenantId, userId, role);
        Map<String, Object> document = document(documentId);
        if (!Objects.equals(longValue(document.get("sessionId")), sessionId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "策划文档不存在");
        }
        return Map.of("document", document);
    }

    private Map<String, Object> loadOrCreateSession(Long teamId, Long tenantId, Long userId, Map<String, Object> dashboard) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT * FROM project_prep_session
                WHERE tenant_id = ? AND team_id = ? AND created_by = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """, tenantId, teamId, userId);
        if (rows.isEmpty()) {
            Map<String, Object> team = mapValue(dashboard.get("team"));
            String teamName = firstNonBlank(text(team.get("name")), "项目团队");
            Long sessionId = insert("""
                    INSERT INTO project_prep_session
                    (tenant_id, team_id, created_by, title, status, context_snapshot_json)
                    VALUES (?, ?, ?, ?, 'DRAFT', ?)
                    """, tenantId, teamId, userId, teamName + " 选题策划", json(contextSnapshot(teamId, dashboard, userId)));
            return refreshedSessionPayload(sessionId);
        }
        return refreshedSessionPayload(longValue(rows.get(0).get("id")));
    }

    private Map<String, Object> refreshedSessionPayload(Long sessionId) {
        synchronized (lockForSession(sessionId)) {
            expireStaleRuns(sessionId);
            return sessionPayload(sessionRow(sessionId));
        }
    }

    private Map<String, Object> sessionPayload(Map<String, Object> row) {
        Long sessionId = longValue(row.get("id"));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", sessionId);
        result.put("teamId", longValue(row.get("team_id")));
        result.put("title", row.get("title"));
        result.put("status", row.get("status"));
        result.put("activeDirectionId", longValue(row.get("active_direction_id")));
        result.put("messages", messages(sessionId));
        result.put("directions", directions(sessionId));
        result.put("documents", documents(sessionId));
        result.put("latestRun", latestRun(sessionId));
        result.put("generationGroups", generationGroups(sessionId));
        return result;
    }

    private Map<String, Object> contextSnapshot(Long teamId, Map<String, Object> dashboard, Long userId) {
        Map<String, Object> context = new LinkedHashMap<>();
        context.put("teamId", teamId);
        context.put("team", dashboard.getOrDefault("team", Map.of()));
        context.put("members", dashboard.getOrDefault("members", List.of()));
        context.put("tasks", dashboard.getOrDefault("tasks", List.of()));
        context.put("materials", dashboard.getOrDefault("materials", List.of()));
        context.put("submissions", dashboard.getOrDefault("submissions", List.of()));
        context.put("stages", dashboard.getOrDefault("stages", List.of()));
        context.put("roadshow", dashboard.getOrDefault("roadshow", Map.of()));
        context.put("scripts", scriptService.listByUserId(userId).stream().limit(20).map(this::scriptContextView).toList());
        context.put("sourcePolicy", Map.of(
                "teamFacts", "ONLY_FROM_DASHBOARD",
                "webFacts", "PUBLIC_WEB_RESEARCH",
                "modelInference", "MUST_BE_MARKED"
        ));
        return context;
    }

    private List<Map<String, Object>> messages(Long sessionId) {
        return jdbc.queryForList("""
                SELECT id, role, content, source_type sourceType, model, created_at createdAt
                FROM project_prep_message
                WHERE session_id = ?
                ORDER BY created_at ASC, id ASC
                """, sessionId);
    }

    private List<Map<String, Object>> directions(Long sessionId) {
        return jdbc.queryForList("""
                SELECT id, ai_run_id aiRunId, generation_no generationNo,
                       title, summary, tags_json tagsJson, equipment_match equipmentMatch,
                       competition_match competitionMatch, scores_json scoresJson,
                       recommendation_level recommendationLevel, expert_rationale expertRationale,
                       evidence_gaps_json evidenceGapsJson,
                       risks_json risksJson, next_tasks_json nextTasksJson, research_refs_json researchRefsJson,
                       selected, created_at createdAt, updated_at updatedAt
                FROM project_prep_direction
                WHERE session_id = ?
                ORDER BY selected DESC, updated_at DESC, id DESC
                """, sessionId).stream().map(this::directionView).toList();
    }

    private List<Map<String, Object>> documents(Long sessionId) {
        return jdbc.queryForList("""
                SELECT id, session_id sessionId, direction_id directionId, title, status, created_at createdAt, updated_at updatedAt
                FROM project_prep_document
                WHERE session_id = ?
                ORDER BY updated_at DESC, id DESC
                """, sessionId);
    }

    private Map<String, Object> latestRun(Long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, run_type runType, status, error_message errorMessage, model,
                       response_json responseJson, started_at startedAt, completed_at completedAt
                FROM project_prep_ai_run
                WHERE session_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """, sessionId);
        if (rows.isEmpty()) return null;
        Map<String, Object> row = new LinkedHashMap<>(rows.get(0));
        Map<String, Object> response = parseMap(row.get("responseJson"));
        row.put("researchSummary", text(response.get("researchSummary")));
        row.put("questions", parseList(jsonOrValue(response.get("questions"))));
        row.put("sources", parseListMap(jsonOrValue(response.get("sources"))));
        row.put("nextActions", parseList(jsonOrValue(response.get("nextActions"))));
        row.put("agentSteps", agentSteps(sessionId, longValue(row.get("id"))));
        row.remove("responseJson");
        return row;
    }

    private List<Map<String, Object>> agentSteps(Long sessionId, Long runId) {
        if (runId == null) return List.of();
        return jdbc.queryForList("""
                SELECT id, step_no stepNo, agent_key agentKey, agent_name agentName, agent_role agentRole,
                       status, input_summary inputSummary, output_summary outputSummary,
                       findings_json findingsJson, questions_json questionsJson, sources_json sourcesJson,
                       started_at startedAt, completed_at completedAt, created_at createdAt
                FROM project_prep_agent_step
                WHERE session_id = ? AND ai_run_id = ?
                ORDER BY step_no ASC, id ASC
                """, sessionId, runId).stream().map(row -> {
            Map<String, Object> view = new LinkedHashMap<>(row);
            view.put("findings", parseList(row.get("findingsJson")));
            view.put("questions", parseList(row.get("questionsJson")));
            view.put("sources", parseListMap(row.get("sourcesJson")));
            view.remove("findingsJson");
            view.remove("questionsJson");
            view.remove("sourcesJson");
            return view;
        }).toList();
    }

    private List<Map<String, Object>> generatedTasks(Long sessionId, Long directionId) {
        return jdbc.queryForList("""
                SELECT task_id id, task_title title, created_at createdAt
                FROM project_prep_task_generation
                WHERE session_id = ? AND direction_id = ?
                ORDER BY created_at ASC, id ASC
                """, sessionId, directionId);
    }

    private Map<String, Object> activeRunningRun(Long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, status, started_at startedAt
                FROM project_prep_ai_run
                WHERE session_id = ? AND status = 'RUNNING'
                ORDER BY id DESC
                LIMIT 1
                """, sessionId);
        if (rows.isEmpty()) return Map.of();
        return new LinkedHashMap<>(rows.get(0));
    }

    private void expireStaleRuns(Long sessionId) {
        LocalDateTime now = LocalDateTime.now();
        int expired = jdbc.update("""
                UPDATE project_prep_ai_run
                SET status = 'FAILED', error_message = 'AI 运行超时，已允许重新提交', completed_at = ?
                WHERE session_id = ? AND status = 'RUNNING' AND started_at < ?
                """, now, sessionId, now.minusMinutes(PREP_RUN_STALE_MINUTES));
        if (expired > 0 && activeRunningRun(sessionId).isEmpty()) {
            jdbc.update("""
                    UPDATE project_prep_session
                    SET status = 'AI_FAILED'
                    WHERE id = ?
                    """, sessionId);
        }
    }

    private boolean isRunRunning(Long runId) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id
                FROM project_prep_ai_run
                WHERE id = ? AND status = 'RUNNING'
                LIMIT 1
                """, runId);
        return !rows.isEmpty();
    }

    private Object lockForSession(Long sessionId) {
        return sessionLocks.computeIfAbsent(sessionId, ignored -> new Object());
    }

    private Map<String, Object> latestDocument(Long sessionId, Long directionId) {
        if (directionId == null) return Map.of();
        List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT id, session_id sessionId, direction_id directionId, title, content, status, created_at createdAt, updated_at updatedAt
                FROM project_prep_document
                WHERE session_id = ? AND direction_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """, sessionId, directionId);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    private void saveDirection(Long sessionId, Long runId, int generationNo, ProjectPreparationAiResponse.Direction direction) {
        String title = requiredText(direction.getTitle(), "方向标题不能为空");
        insert("""
                INSERT INTO project_prep_direction
                (session_id, ai_run_id, generation_no, title, summary, tags_json, equipment_match, competition_match,
                 scores_json, recommendation_level, expert_rationale, evidence_gaps_json, risks_json, next_tasks_json, research_refs_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sessionId,
                runId,
                generationNo,
                title,
                firstNonBlank(direction.getSummary(), "待补充方向摘要"),
                json(direction.getTags()),
                direction.getEquipmentMatch(),
                direction.getCompetitionMatch(),
                json(direction.getScores() == null ? Map.of() : direction.getScores()),
                direction.getRecommendationLevel(),
                direction.getExpertRationale(),
                json(direction.getEvidenceGaps()),
                json(direction.getRisks()),
                json(direction.getNextTasks()),
                json(direction.getResearchRefs()));
    }

    private void saveAgentSteps(Long sessionId, Long runId, List<ProjectPreparationAiResponse.AgentStep> agentSteps) {
        if (agentSteps == null || agentSteps.isEmpty()) return;
        int stepNo = 1;
        for (ProjectPreparationAiResponse.AgentStep step : agentSteps) {
            if (step == null) continue;
            insert("""
                    INSERT INTO project_prep_agent_step
                    (session_id, ai_run_id, step_no, agent_key, agent_name, agent_role, status,
                     input_summary, output_summary, findings_json, questions_json, sources_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    sessionId,
                    runId,
                    stepNo++,
                    firstNonBlank(step.getAgentKey(), "agent"),
                    firstNonBlank(step.getAgentName(), "选题专家"),
                    firstNonBlank(step.getAgentRole(), "选题分析"),
                    firstNonBlank(step.getStatus(), "COMPLETED"),
                    step.getInputSummary(),
                    step.getOutputSummary(),
                    json(step.getFindings()),
                    json(step.getQuestions()),
                    json(step.getSources()));
        }
    }

    private Map<String, Object> directionView(Map<String, Object> row) {
        Map<String, Object> view = new LinkedHashMap<>(row);
        view.put("selected", Objects.equals(String.valueOf(row.get("selected")), "1") || Objects.equals(row.get("selected"), true));
        view.put("tags", parseList(row.get("tagsJson")));
        view.put("scores", parseMap(row.get("scoresJson")));
        view.put("evidenceGaps", parseList(row.get("evidenceGapsJson")));
        view.put("risks", parseList(row.get("risksJson")));
        view.put("nextTasks", parseListMap(row.get("nextTasksJson")));
        view.put("researchRefs", parseListMap(row.get("researchRefsJson")));
        view.remove("tagsJson");
        view.remove("scoresJson");
        view.remove("evidenceGapsJson");
        view.remove("risksJson");
        view.remove("nextTasksJson");
        view.remove("researchRefsJson");
        return view;
    }

    private List<Map<String, Object>> generationGroups(Long sessionId) {
        return jdbc.queryForList("""
                SELECT generation_no generationNo, ai_run_id aiRunId, COUNT(*) directionCount, MAX(updated_at) updatedAt
                FROM project_prep_direction
                WHERE session_id = ?
                GROUP BY generation_no, ai_run_id
                ORDER BY generation_no DESC, ai_run_id DESC
                """, sessionId);
    }

    private int nextGenerationNo(Long sessionId) {
        Integer max = jdbc.queryForObject("""
                SELECT COALESCE(MAX(generation_no), 0)
                FROM project_prep_direction
                WHERE session_id = ?
                """, Integer.class, sessionId);
        return (max == null ? 0 : max) + 1;
    }

    private Map<String, Object> document(Long documentId) {
        return jdbc.queryForMap("""
                SELECT id, session_id sessionId, direction_id directionId, title, content, status, created_at createdAt, updated_at updatedAt
                FROM project_prep_document
                WHERE id = ?
                """, documentId);
    }

    private String buildDocumentContent(Map<String, Object> session, Map<String, Object> direction) {
        StringBuilder builder = new StringBuilder();
        builder.append("# ").append(firstNonBlank(text(direction.get("title")), text(session.get("title")), "选题策划书草稿")).append("\n\n");
        builder.append("## 方向摘要\n").append(firstNonBlank(text(direction.get("summary")), "待基于真实材料补充。")).append("\n\n");
        builder.append("## 材料缺口\n");
        for (Object gap : parseList(direction.get("evidence_gaps_json"))) {
            builder.append("- ").append(gap).append("\n");
        }
        builder.append("\n## 风险\n");
        for (Object risk : parseList(direction.get("risks_json"))) {
            builder.append("- ").append(risk).append("\n");
        }
        builder.append("\n## 下一步任务\n");
        for (Map<String, Object> task : parseListMap(direction.get("next_tasks_json"))) {
            builder.append("- ").append(firstNonBlank(text(task.get("title")), text(task.get("name")), "待补任务")).append("\n");
        }
        return builder.toString();
    }

    private Map<String, Object> resourceView(Resource resource) {
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", resource.getId());
        view.put("name", resource.getName());
        view.put("ext", resource.getExt());
        view.put("fileSize", resource.getFileSize());
        view.put("category", resource.getCategory() == null ? "public" : resource.getCategory());
        view.put("url", "/api/ppt-template/download/" + URLEncoder.encode(resource.getName(), StandardCharsets.UTF_8).replace("+", "%20"));
        view.put("fileUrl", "/api/ppt-template/preview/" + URLEncoder.encode(resource.getName(), StandardCharsets.UTF_8).replace("+", "%20"));
        view.put("createdAt", resource.getCreatedAt());
        return view;
    }

    private Map<String, Object> scriptContextView(Script script) {
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", script.getId());
        view.put("title", script.getTitle());
        view.put("sourceType", script.getSourceType());
        view.put("syncStatus", script.getSyncStatus());
        view.put("contentVersion", script.getContentVersion());
        view.put("updatedAt", script.getUpdatedAt());
        return view;
    }

    private Map<String, Object> sessionRow(Long sessionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT * FROM project_prep_session WHERE id = ?", sessionId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "选题策划会话不存在");
        return rows.get(0);
    }

    private Map<String, Object> directionRow(Long sessionId, Long directionId) {
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT * FROM project_prep_direction WHERE id = ? AND session_id = ?", directionId, sessionId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "选题方向不存在");
        return rows.get(0);
    }

    private void assertDirectionInSession(Long sessionId, Long directionId) {
        directionRow(sessionId, directionId);
    }

    private Long pickTeamId(Long requestedTeamId, List<Map<String, Object>> teams) {
        if (teams.isEmpty()) return null;
        if (requestedTeamId != null && teams.stream().anyMatch(team -> Objects.equals(longValue(team.get("id")), requestedTeamId))) {
            return requestedTeamId;
        }
        return longValue(teams.get(0).get("id"));
    }

    private Long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement ps = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int i = 0; i < args.length; i++) ps.setObject(i + 1, args[i]);
            return ps;
        }, keyHolder);
        Number key;
        if (!keyHolder.getKeyList().isEmpty() && keyHolder.getKeyList().get(0).get("id") instanceof Number id) {
            key = id;
        } else {
            key = keyHolder.getKey();
        }
        if (key == null) throw new IllegalStateException("新增记录未返回主键");
        return key.longValue();
    }

    private String json(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalArgumentException("JSON 序列化失败", e);
        }
    }

    private String safeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignored) {
            return "{}";
        }
    }

    private List<Object> parseList(Object value) {
        if (value == null) return List.of();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> parseListMap(Object value) {
        if (value == null) return List.of();
        try {
            return objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Map<String, Object> parseMap(Object value) {
        if (value == null) return Map.of();
        try {
            Map<String, Object> parsed = objectMapper.readValue(String.valueOf(value), new TypeReference<>() {});
            return parsed == null ? Map.of() : parsed;
        } catch (Exception ignored) {
            return Map.of();
        }
    }

    private Object jsonOrValue(Object value) {
        if (value == null) return null;
        if (value instanceof String) return value;
        return json(value);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private String requiredText(Object value, String message) {
        String text = text(value);
        if (text == null || text.isBlank()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
        return text.trim();
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (value != null && !value.isBlank()) return value.trim();
        }
        return "";
    }

    private String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    private LocalDateTime dateTime(Object value) {
        if (value instanceof LocalDateTime dateTime) return dateTime;
        if (value instanceof Timestamp timestamp) return timestamp.toLocalDateTime();
        return null;
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }
}
