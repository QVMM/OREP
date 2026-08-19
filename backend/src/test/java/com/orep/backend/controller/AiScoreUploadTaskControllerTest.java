package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaAssetService;
import com.orep.backend.service.AiScoreUploadTaskService;
import com.orep.backend.service.AiScoringPipelineClient;
import com.orep.backend.service.AiScoringSessionService;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreUploadTaskControllerTest {

    @Test
    void listsCurrentUsersUploadTasksWithoutInternalFields() throws Exception {
        AiScoreUploadTaskService taskService = mock(AiScoreUploadTaskService.class);
        when(taskService.listForUser(7L, 10)).thenReturn(List.of(task()));
        MockMvc mvc = standaloneSetup(controller(taskService)).build();

        mvc.perform(get("/api/ai-score/upload-tasks")
                        .param("completedLimit", "10")
                        .requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].sessionId").value(123))
                .andExpect(jsonPath("$.data[0].fileName").value("roadshow.mp4"))
                .andExpect(jsonPath("$.data[0].teamName").value("先锋队"))
                .andExpect(jsonPath("$.data[0].progressPercent").value(65))
                .andExpect(jsonPath("$.data[0].reportId").value(456))
                .andExpect(jsonPath("$.data[0].filePath").doesNotExist())
                .andExpect(jsonPath("$.data[0].rubricHash").doesNotExist())
                .andExpect(jsonPath("$.data[0].rubricPath").doesNotExist())
                .andExpect(jsonPath("$.data[0].internalVersion").doesNotExist());

        verify(taskService).listForUser(7L, 10);
    }

    @Test
    void rejectsUnauthenticatedUploadTaskRequestWithoutCallingService() throws Exception {
        AiScoreUploadTaskService taskService = mock(AiScoreUploadTaskService.class);
        MockMvc mvc = standaloneSetup(controller(taskService)).build();

        mvc.perform(get("/api/ai-score/upload-tasks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(401))
                .andExpect(jsonPath("$.message").value("用户未登录"));

        verify(taskService, never()).listForUser(org.mockito.ArgumentMatchers.anyLong(), org.mockito.ArgumentMatchers.any());
    }

    @Test
    void doesNotExposePersistedInternalFailureDetailsThroughQueueApi() throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.h2.Driver");
        dataSource.setUrl("jdbc:h2:mem:upload_queue_controller_" + UUID.randomUUID() + ";MODE=MySQL;DB_CLOSE_DELAY=-1");
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        createQueueSchema(jdbc);
        String internalFailure = """
                prompt/rubric config failed at /opt/orep/rules/internal.yaml and C:\\orep\\prompt.txt
                POST http://127.0.0.1:8090/internal/score
                at com.orep.pipeline.InternalScoringService.run(InternalScoringService.java:42)
                """;
        jdbc.update("""
                INSERT INTO ai_scoring_session(
                    id, session_no, source_type, team_id, track_name, status, current_stage,
                    progress_percent, use_history_memory, jury_enabled, error_message,
                    created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, 321L, "UP-321", "uploaded_video", 9L, "人工智能", "failed", "scoring",
                55, true, false, internalFailure, 7L);
        MockMvc mvc = standaloneSetup(controller(new AiScoreUploadTaskService(jdbc))).build();

        mvc.perform(get("/api/ai-score/upload-tasks").requestAttr("userId", 7L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].errorMessage")
                        .value("评分处理失败，请稍后重试；如仍失败，请重新上传视频。"))
                .andExpect(jsonPath("$.data[0].errorMessage").value(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("127.0.0.1"))))
                .andExpect(jsonPath("$.data[0].errorMessage").value(org.hamcrest.Matchers.not(
                        org.hamcrest.Matchers.containsString("InternalScoringService"))));
    }

    private AiScoreUploadController controller(AiScoreUploadTaskService taskService) {
        return new AiScoreUploadController(
                mock(AiScoringSessionService.class),
                mock(AiScoreMediaAssetService.class),
                mock(AiScoreAccessControlService.class),
                mock(AiScoringPipelineClient.class),
                "./uploads",
                taskService
        );
    }

    private AiScoreUploadTaskResponse task() {
        return new AiScoreUploadTaskResponse(
                123L, "session-123", "roadshow.mp4", 4096L, 3L, 9L,
                "先锋队", "人工智能", "scoring", "analysis", 65,
                true, false, 456L, null, LocalDateTime.now(), LocalDateTime.now()
        );
    }

    private void createQueueSchema(JdbcTemplate jdbc) {
        jdbc.execute("CREATE TABLE project_team (id BIGINT PRIMARY KEY, name VARCHAR(255))");
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY, session_no VARCHAR(64), source_type VARCHAR(32), project_id BIGINT,
                    team_id BIGINT, track_name VARCHAR(128), status VARCHAR(32), current_stage VARCHAR(64),
                    progress_percent INT, use_history_memory TINYINT, jury_enabled TINYINT, report_id BIGINT,
                    error_message VARCHAR(2000), created_by BIGINT, created_at TIMESTAMP, updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_media_asset (
                    id BIGINT PRIMARY KEY, session_id BIGINT, asset_type VARCHAR(32),
                    original_name VARCHAR(255), size_bytes BIGINT
                )
                """);
        jdbc.update("INSERT INTO project_team(id, name) VALUES (?, ?)", 9L, "先锋队");
    }
}
