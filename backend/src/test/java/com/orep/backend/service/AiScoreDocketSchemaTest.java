package com.orep.backend.service;

import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;

class AiScoreDocketSchemaTest {

    @Test
    void ensureCreatesDocketTablesAndSessionColumn() {
        JdbcTemplate jdbc = newJdbc("ai_score_docket_schema");
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("CREATE TABLE ai_scoring_session (id BIGINT PRIMARY KEY)");

        AiScoringSessionService service = newService(jdbc);
        service.ensureReportSchemaCompatibility();

        assertTrue(tableExists(jdbc, "ai_score_docket"));
        assertTrue(tableExists(jdbc, "ai_score_docket_run"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "docket_id"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "challenge_json"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "challenge_completed"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "deliberation_stage"));
        assertTrue(hasColumn(jdbc, "ai_score_docket", "task_book_published"));
        assertTrue(hasColumn(jdbc, "ai_score_docket", "task_book_json"));
        assertTrue(hasColumn(jdbc, "ai_score_docket", "task_book_published_session_id"));

        String videoSha256 = "aa".repeat(32);
        String ruleHash = "dd".repeat(32);
        jdbc.update("""
                INSERT INTO ai_score_docket
                  (docket_id, video_sha256, rule_version, rule_hash, contract_version, track_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                "docket-one", videoSha256, "v1.2", ruleHash, "ai-score-report-v3", "track-it");

        assertThrows(Exception.class, () -> jdbc.update("""
                INSERT INTO ai_score_docket
                  (docket_id, video_sha256, rule_version, rule_hash, contract_version, track_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                "docket-two", videoSha256, "v1.2", ruleHash, "ai-score-report-v3", "track-it"));

        jdbc.update("""
                INSERT INTO ai_score_docket_run (docket_id, run_index, session_id, status)
                VALUES (?, ?, ?, ?)
                """, "docket-one", 1, 1L, "completed");

        assertThrows(Exception.class, () -> jdbc.update("""
                INSERT INTO ai_score_docket_run (docket_id, run_index, session_id, status)
                VALUES (?, ?, ?, ?)
                """, "docket-one", 1, 2L, "completed"));

        assertThrows(Exception.class, () -> jdbc.update("""
                INSERT INTO ai_score_docket_run (docket_id, run_index, session_id, status)
                VALUES (?, ?, ?, ?)
                """, "docket-one", 2, 1L, "completed"));

        jdbc.update("INSERT INTO ai_scoring_session (id) VALUES (1)");
        Integer sessionRows = jdbc.queryForObject(
                "SELECT COUNT(*) FROM ai_scoring_session WHERE id = 1 AND docket_id IS NULL",
                Integer.class);
        assertEquals(1, sessionRows);
    }

    @Test
    void reportSummariesJoinDoesNotThrowWhenDocketRowExists() {
        JdbcTemplate jdbc = newJdbc("ai_score_docket_report_summaries");
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                  id BIGINT PRIMARY KEY,
                  report_id BIGINT,
                  meeting_id BIGINT,
                  docket_id VARCHAR(64),
                  source_type VARCHAR(32),
                  status VARCHAR(32),
                  completed_at TIMESTAMP,
                  created_at TIMESTAMP,
                  updated_at TIMESTAMP,
                  team_id BIGINT,
                  teacher_confirmed TINYINT,
                  created_by BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_report (
                  id BIGINT PRIMARY KEY,
                  status VARCHAR(32),
                  overall_score DECIMAL(6,2),
                  task_book_published TINYINT,
                  task_book_json CLOB,
                  critical_issues_json CLOB,
                  improvement_priorities_json CLOB,
                  meeting_id BIGINT,
                  completed_at TIMESTAMP,
                  created_at TIMESTAMP,
                  updated_at TIMESTAMP
                )
                """);
        jdbc.execute("CREATE TABLE meeting (id BIGINT PRIMARY KEY, title VARCHAR(128), creator_id BIGINT)");
        jdbc.execute("CREATE TABLE project_team (id BIGINT PRIMARY KEY, name VARCHAR(128))");
        jdbc.execute("""
                CREATE TABLE project_roadshow_binding (
                  meeting_id BIGINT, team_id BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE meeting_participant (
                  meeting_id BIGINT, user_id BIGINT
                )
                """);

        AiScoringSessionService service = newService(jdbc);
        service.ensureReportSchemaCompatibility();

        jdbc.update("""
                INSERT INTO ai_score_docket
                  (docket_id, video_sha256, rule_version, rule_hash, contract_version, track_id)
                VALUES ('dock-1', ?, 'v1', ?, 'c1', 't1')
                """, "bb".repeat(32), "cc".repeat(32));
        jdbc.update("""
                INSERT INTO ai_score_report
                  (id, status, overall_score, task_book_published, completed_at, created_at, updated_at)
                VALUES (9, 'completed', 44.6, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """);
        jdbc.update("""
                INSERT INTO ai_scoring_session
                  (id, report_id, docket_id, status, teacher_confirmed, created_by, completed_at, created_at, updated_at)
                VALUES (8, 9, 'dock-1', 'completed', 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """);

        List<Map<String, Object>> rows = service.reportSummaries("participant", 1L, 1L, "ADMIN");
        assertEquals(1, rows.size());
        assertEquals(8L, ((Number) rows.get(0).get("sessionId")).longValue());
    }

    @Test
    void ensureIsIdempotent() {
        JdbcTemplate jdbc = newJdbc("ai_score_docket_schema_idempotent");
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("CREATE TABLE ai_scoring_session (id BIGINT PRIMARY KEY)");

        AiScoringSessionService service = newService(jdbc);
        service.ensureReportSchemaCompatibility();
        service.ensureReportSchemaCompatibility();

        assertTrue(tableExists(jdbc, "ai_score_docket"));
        assertTrue(tableExists(jdbc, "ai_score_docket_run"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "docket_id"));
        assertTrue(hasColumn(jdbc, "ai_scoring_session", "challenge_json"));
    }

    private static AiScoringSessionService newService(JdbcTemplate jdbc) {
        return new AiScoringSessionService(
                mock(AiScoringSessionMapper.class),
                mock(AiScoreReportMapper.class),
                null,
                null,
                null,
                mock(RubricResolverService.class),
                new ScoringFingerprintService(),
                jdbc
        );
    }

    private static JdbcTemplate newJdbc(String dbName) {
        return new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:" + dbName + ";MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
    }

    private static boolean tableExists(JdbcTemplate jdbc, String tableName) {
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE LOWER(TABLE_NAME)=?
                """, Integer.class, tableName.toLowerCase());
        return count != null && count > 0;
    }

    private static boolean hasColumn(JdbcTemplate jdbc, String tableName, String columnName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (var columns = connection.getMetaData().getColumns(null, null, tableName, null)) {
                while (columns.next()) {
                    if (columnName.equalsIgnoreCase(columns.getString("COLUMN_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }
}
