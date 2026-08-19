package com.orep.backend.service;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;

class AiScoreUploadTaskServiceTest {

    private JdbcTemplate jdbc;
    private AiScoreUploadTaskService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.h2.Driver");
        dataSource.setUrl("jdbc:h2:mem:upload_queue_" + UUID.randomUUID() + ";MODE=MySQL;DB_CLOSE_DELAY=-1");
        jdbc = new JdbcTemplate(dataSource);
        service = new AiScoreUploadTaskService(jdbc);
        createSchema();
        seedTasks();
    }

    @AfterEach
    void cleanUp() {
        jdbc.execute("DROP ALL OBJECTS");
    }

    @Test
    void listsActiveTasksBeforeNewerTerminalTasksAndUsesStableCreatedAtAndIdOrdering() {
        List<AiScoreUploadTaskResponse> result = service.listForUser(7L, null);

        assertEquals(13, result.size());
        assertEquals(List.of(101L, 103L, 102L, 200L, 201L, 202L, 203L, 204L, 205L, 206L, 207L, 208L, 209L),
                result.stream().map(AiScoreUploadTaskResponse::sessionId).toList());
        assertEquals(10, result.stream().filter(this::isTerminal).count());
        assertFalse(result.stream().map(AiScoreUploadTaskResponse::sessionId).anyMatch(id -> id == 301L || id == 302L || id == 210L || id == 211L));

        AiScoreUploadTaskResponse active = result.getFirst();
        assertEquals("pitch.mp4", active.fileName());
        assertEquals(2048L, active.fileSize());
        assertEquals(50L, active.projectId());
        assertEquals(9L, active.teamId());
        assertEquals("先锋队", active.teamName());
        assertEquals("人工智能", active.trackName());
        assertEquals(100, active.progressPercent());
        assertEquals(true, active.useHistoryMemory());
        assertEquals(false, active.juryEnabled());
        assertEquals("failed", result.get(3).status());

        AiScoreUploadTaskResponse fallback = result.get(2);
        assertEquals("UP-102", fallback.fileName());
        assertEquals(0L, fallback.fileSize());
        assertEquals("未命名团队", fallback.teamName());
        assertEquals(0, fallback.progressPercent());
        assertEquals("created", result.get(1).status());
        assertNull(result.get(1).projectId());
        assertNull(result.get(1).reportId());
    }

    @Test
    void clampsCompletedLimitAndErrorMessageLength() {
        jdbc.update("UPDATE ai_scoring_session SET error_message = ? WHERE id = 200", "x".repeat(200));

        List<AiScoreUploadTaskResponse> result = service.listForUser(7L, 99);

        assertEquals(13, result.size());
        assertEquals(160, result.stream().filter(row -> row.sessionId().equals(200L)).findFirst().orElseThrow().errorMessage().length());
        assertEquals(3, service.listForUser(7L, -1).size());
    }

    @Test
    void truncatesErrorMessageAtUnicodeCodePointBoundary() {
        jdbc.update("UPDATE ai_scoring_session SET error_message = ? WHERE id = 200", "x".repeat(159) + "😀" + "y".repeat(10));

        String message = service.listForUser(7L, 10).stream()
                .filter(row -> row.sessionId().equals(200L))
                .findFirst().orElseThrow().errorMessage();

        assertEquals(160, message.codePointCount(0, message.length()));
        assertFalse(Character.isHighSurrogate(message.charAt(message.length() - 1)));
    }

    @Test
    void redactsSensitiveInternalFailureDetailsFromPublicQueueMessage() {
        List<String> internalFailures = List.of(
                "无法读取 /srv/orep/config/scoring-rubric.yaml",
                "无法读取 C:\\orep\\secrets\\system-prompt.txt",
                "POST http://127.0.0.1:8090/internal/score returned 500",
                "host=scoring-engine.internal port=8090 connection refused",
                "连接 worker-node:8090 失败",
                "at com.orep.backend.pipeline.InternalScoringService.run(InternalScoringService.java:87)",
                "rubric={weights:[20,30]}; prompt=system instructions"
        );

        for (String internalFailure : internalFailures) {
            jdbc.update("UPDATE ai_scoring_session SET error_message = ? WHERE id = 200", internalFailure);

            String message = service.listForUser(7L, 10).stream()
                    .filter(row -> row.sessionId().equals(200L))
                    .findFirst().orElseThrow().errorMessage();

            assertEquals("评分处理失败，请稍后重试；如仍失败，请重新上传视频。", message,
                    () -> "未脱敏的内部错误: " + internalFailure);
            assertTrue(message.codePointCount(0, message.length()) <= 160);
        }
    }

    @Test
    void keepsShortUserSafeFailureReason() {
        jdbc.update("UPDATE ai_scoring_session SET error_message = ? WHERE id = 200", "视频格式暂不支持，请重新选择 MP4 文件");

        String message = service.listForUser(7L, 10).stream()
                .filter(row -> row.sessionId().equals(200L))
                .findFirst().orElseThrow().errorMessage();

        assertEquals("视频格式暂不支持，请重新选择 MP4 文件", message);
    }

    @Test
    void rejectsMissingUserIdentity() {
        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> service.listForUser(null, 10));

        assertEquals("用户身份不能为空", error.getMessage());
    }

    private boolean isTerminal(AiScoreUploadTaskResponse row) {
        return List.of("completed", "failed", "cancelled").contains(row.status());
    }

    private void createSchema() {
        jdbc.execute("""
                CREATE TABLE project_team (
                    id BIGINT PRIMARY KEY,
                    name VARCHAR(255)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY, session_no VARCHAR(64), source_type VARCHAR(32), project_id BIGINT,
                    team_id BIGINT, track_name VARCHAR(128), status VARCHAR(32), current_stage VARCHAR(64),
                    progress_percent INT, use_history_memory TINYINT, jury_enabled TINYINT, report_id BIGINT,
                    error_message VARCHAR(1000), created_by BIGINT, created_at TIMESTAMP, updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_media_asset (
                    id BIGINT PRIMARY KEY, session_id BIGINT, asset_type VARCHAR(32), original_name VARCHAR(255), size_bytes BIGINT
                )
                """);
    }

    private void seedTasks() {
        jdbc.update("INSERT INTO project_team(id, name) VALUES (?, ?)", 9L, "先锋队");
        insertSession(101, "UP-101", "uploaded_video", 7, "processing", 150, 9L, timestamp(30));
        insertSession(102, "UP-102", "uploaded_video", 7, "queued", -5, 99L, timestamp(20));
        insertSession(103, "UP-103", "uploaded_video", 7, null, 50, 9L, timestamp(20));
        jdbc.update("UPDATE ai_scoring_session SET project_id = NULL, report_id = NULL WHERE id = 103");
        jdbc.update("INSERT INTO ai_score_media_asset(id, session_id, asset_type, original_name, size_bytes) VALUES (?,?,?,?,?)", 5L, 101L, "video", "pitch.mp4", 2048L);
        jdbc.update("INSERT INTO ai_score_media_asset(id, session_id, asset_type, original_name, size_bytes) VALUES (?,?,?,?,?)", 6L, 101L, "video", "ignored.mp4", 4096L);
        for (int id = 200; id <= 211; id++) {
            insertSession(id, "UP-" + id, "uploaded_video", 7, id == 200 ? "failed" : "completed", 55, 9L,
                    id == 200 ? timestamp(50) : timestamp(100 - id));
        }
        insertSession(301, "OTHER", "uploaded_video", 8, "processing", 45, 9L, timestamp(40));
        insertSession(302, "MEETING", "meeting_recording", 7, "processing", 45, 9L, timestamp(40));
    }

    private void insertSession(long id, String sessionNo, String sourceType, long userId, String status, int progress, Long teamId, LocalDateTime updatedAt) {
        jdbc.update("""
                INSERT INTO ai_scoring_session(id, session_no, source_type, project_id, team_id, track_name, status,
                    current_stage, progress_percent, use_history_memory, jury_enabled, report_id, error_message,
                    created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, id, sessionNo, sourceType, 50L, teamId, "人工智能", status, "scoring", progress,
                true, false, 900L + id, "error-" + id, userId, updatedAt.minusMinutes(1), updatedAt);
    }

    private LocalDateTime timestamp(int minute) {
        return LocalDateTime.of(2026, 1, 1, 0, 0).plusMinutes(minute);
    }
}
