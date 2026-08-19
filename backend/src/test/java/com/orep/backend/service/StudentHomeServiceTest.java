package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class StudentHomeServiceTest {
    @Test
    void uploadedVideoScoreAppearsOnHomeWithoutMeetingBinding() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:student-home;MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("""
                CREATE TABLE users (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, username VARCHAR(100), role VARCHAR(30),
                    school_name VARCHAR(100), college_name VARCHAR(100), class_name VARCHAR(100)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, name VARCHAR(100), description VARCHAR(255),
                    status VARCHAR(30), updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team_member (
                    id BIGINT PRIMARY KEY, team_id BIGINT, user_id BIGINT, role_in_team VARCHAR(30),
                    position_name VARCHAR(100), joined_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE meeting (
                    id BIGINT PRIMARY KEY, title VARCHAR(255), status VARCHAR(30), start_time TIMESTAMP,
                    end_time TIMESTAMP, duration_minutes INT
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_roadshow_binding (
                    id BIGINT PRIMARY KEY, team_id BIGINT, meeting_id BIGINT, roadshow_type VARCHAR(30)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY, team_id BIGINT, source_type VARCHAR(40), meeting_id BIGINT,
                    report_id BIGINT, created_by BIGINT, status VARCHAR(30), completed_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_report (
                    id BIGINT PRIMARY KEY, session_id BIGINT, meeting_id BIGINT, overall_score DECIMAL(6,2),
                    dimensions_json CLOB, improvement_priorities_json CLOB, status VARCHAR(30), completed_at TIMESTAMP
                )
                """);

        jdbc.update("INSERT INTO users(id, tenant_id, username, role) VALUES (17, 1, 'student', 'STUDENT')");
        jdbc.update("INSERT INTO project_team(id, tenant_id, name, status, updated_at) VALUES (5, 1, 'team', 'ACTIVE', CURRENT_TIMESTAMP)");
        jdbc.update("INSERT INTO project_team_member(id, team_id, user_id, role_in_team, joined_at) VALUES (1, 5, 17, 'MEMBER', CURRENT_TIMESTAMP)");
        jdbc.update("INSERT INTO ai_scoring_session(id, team_id, source_type, meeting_id, report_id, created_by, status, completed_at) VALUES (34, 5, 'uploaded_video', NULL, 45, 17, 'completed', CURRENT_TIMESTAMP)");
        jdbc.update("""
                INSERT INTO ai_score_report(
                    id, session_id, meeting_id, overall_score, dimensions_json,
                    improvement_priorities_json, status, completed_at
                ) VALUES (45, 34, NULL, 55.20, '{"技能水平":{"score":10,"maxScore":20}}',
                    '[{"issue":"提升演示稳定性"}]', 'completed', CURRENT_TIMESTAMP)
                """);

        StudentTrainingService training = mock(StudentTrainingService.class);
        when(training.currentCamp(1L, 17L)).thenReturn(Map.of("hasCamp", true, "teamId", 5L));
        when(training.today(1L, 17L)).thenReturn(Map.of("hasTrainingDay", false));
        when(training.plan(1L, 17L)).thenReturn(Map.of("hasCamp", false));
        StudentLearningAnalyticsService analytics = mock(StudentLearningAnalyticsService.class);
        when(analytics.weekly(17L)).thenReturn(Map.of("daily", List.of(), "totalSeconds", 0));

        StudentHomeService service = new StudentHomeService(jdbc, new ObjectMapper(), training, analytics);
        Map<String, Object> home = service.home(1L, 17L);

        @SuppressWarnings("unchecked")
        Map<String, Object> latestScore = (Map<String, Object>) home.get("latestScore");
        @SuppressWarnings("unchecked")
        Map<String, Object> roadshow = (Map<String, Object>) home.get("roadshow");

        assertTrue(Boolean.TRUE.equals(latestScore.get("hasReport")));
        assertEquals(45L, ((Number) valueIgnoreCase(latestScore, "reportId")).longValue());
        assertEquals(34L, ((Number) valueIgnoreCase(latestScore, "sessionId")).longValue());
        assertEquals(0, new java.math.BigDecimal("55.20").compareTo((java.math.BigDecimal) valueIgnoreCase(latestScore, "overallScore")));
        assertEquals("HAS_SCORE", roadshow.get("state"));
        assertTrue(Boolean.TRUE.equals(roadshow.get("hasScoreReport")));
    }

    @Test
    void latestScoreFollowsNewestDocketRun() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:student-home-docket;MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("""
                CREATE TABLE users (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, username VARCHAR(100), role VARCHAR(30),
                    school_name VARCHAR(100), college_name VARCHAR(100), class_name VARCHAR(100)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, name VARCHAR(100), description VARCHAR(255),
                    status VARCHAR(30), updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team_member (
                    id BIGINT PRIMARY KEY, team_id BIGINT, user_id BIGINT, role_in_team VARCHAR(30),
                    position_name VARCHAR(100), joined_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE meeting (
                    id BIGINT PRIMARY KEY, title VARCHAR(255), status VARCHAR(30), start_time TIMESTAMP,
                    end_time TIMESTAMP, duration_minutes INT
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_roadshow_binding (
                    id BIGINT PRIMARY KEY, team_id BIGINT, meeting_id BIGINT, roadshow_type VARCHAR(30)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY, team_id BIGINT, source_type VARCHAR(40), meeting_id BIGINT,
                    report_id BIGINT, created_by BIGINT, status VARCHAR(30), completed_at TIMESTAMP,
                    docket_id VARCHAR(64)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_report (
                    id BIGINT PRIMARY KEY, session_id BIGINT, meeting_id BIGINT, overall_score DECIMAL(6,2),
                    dimensions_json CLOB, improvement_priorities_json CLOB, status VARCHAR(30), completed_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_docket_run (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT, docket_id VARCHAR(64), run_index INT,
                    session_id BIGINT, report_id BIGINT, status VARCHAR(30)
                )
                """);

        jdbc.update("INSERT INTO users(id, tenant_id, username, role) VALUES (17, 1, 'student', 'STUDENT')");
        jdbc.update("INSERT INTO project_team(id, tenant_id, name, status, updated_at) VALUES (5, 1, 'team', 'ACTIVE', CURRENT_TIMESTAMP)");
        jdbc.update("INSERT INTO project_team_member(id, team_id, user_id, role_in_team, joined_at) VALUES (1, 5, 17, 'MEMBER', CURRENT_TIMESTAMP)");
        jdbc.update("INSERT INTO ai_scoring_session(id, team_id, source_type, meeting_id, report_id, created_by, status, completed_at, docket_id) VALUES (45, 5, 'uploaded_video', NULL, 53, 17, 'completed', TIMESTAMP '2026-08-16 10:00:00', 'docket-a')");
        jdbc.update("INSERT INTO ai_scoring_session(id, team_id, source_type, meeting_id, report_id, created_by, status, completed_at, docket_id) VALUES (47, 5, 'uploaded_video', NULL, 55, 17, 'completed', TIMESTAMP '2026-08-17 10:00:00', 'docket-a')");
        jdbc.update("""
                INSERT INTO ai_score_report(
                    id, session_id, meeting_id, overall_score, dimensions_json,
                    improvement_priorities_json, status, completed_at
                ) VALUES (53, 45, NULL, 40.90, '{}', '[]', 'completed', TIMESTAMP '2026-08-17 12:00:00')
                """);
        jdbc.update("""
                INSERT INTO ai_score_report(
                    id, session_id, meeting_id, overall_score, dimensions_json,
                    improvement_priorities_json, status, completed_at
                ) VALUES (55, 47, NULL, 48.30, '{}', '[]', 'completed', TIMESTAMP '2026-08-16 12:00:00')
                """);
        jdbc.update("INSERT INTO ai_score_docket_run(docket_id, run_index, session_id, report_id, status) VALUES ('docket-a', 7, 45, 53, 'completed')");
        jdbc.update("INSERT INTO ai_score_docket_run(docket_id, run_index, session_id, report_id, status) VALUES ('docket-a', 9, 47, 55, 'completed')");

        StudentTrainingService training = mock(StudentTrainingService.class);
        when(training.currentCamp(1L, 17L)).thenReturn(Map.of("hasCamp", true, "teamId", 5L));
        when(training.today(1L, 17L)).thenReturn(Map.of("hasTrainingDay", false));
        when(training.plan(1L, 17L)).thenReturn(Map.of("hasCamp", false));
        StudentLearningAnalyticsService analytics = mock(StudentLearningAnalyticsService.class);
        when(analytics.weekly(17L)).thenReturn(Map.of("daily", List.of(), "totalSeconds", 0));

        StudentHomeService service = new StudentHomeService(jdbc, new ObjectMapper(), training, analytics);
        Map<String, Object> home = service.home(1L, 17L);

        @SuppressWarnings("unchecked")
        Map<String, Object> latestScore = (Map<String, Object>) home.get("latestScore");
        assertTrue(Boolean.TRUE.equals(latestScore.get("hasReport")));
        assertEquals(55L, ((Number) valueIgnoreCase(latestScore, "reportId")).longValue());
        assertEquals(47L, ((Number) valueIgnoreCase(latestScore, "sessionId")).longValue());
        assertEquals(0, new java.math.BigDecimal("48.30").compareTo((java.math.BigDecimal) valueIgnoreCase(latestScore, "overallScore")));
    }

    @Test
    void frozenPublishedTaskBookLeadsHomeActions() {
        Fixture fixture = homeFixture("student-home-task-book", true, true);
        Map<String, Object> home = fixture.service.home(1L, 17L);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> actions = (List<Map<String, Object>>) home.get("nextActions");
        assertEquals(1, actions.size());
        assertEquals("TASK_BOOK", actions.get(0).get("type"));
        assertEquals("补齐差异与仓库证据", actions.get(0).get("title"));
        assertEquals("/ai-score/report/47/todos", actions.get(0).get("path"));
        assertEquals("本场任务书", actions.get(0).get("meta"));
    }

    @Test
    void hungTaskBookShowsProgressOnHomeWithoutCallingItClosure() {
        Fixture fixture = homeFixture("student-home-task-book-hung", true, true,
                "{\"published\":true,\"items\":[{\"title\":\"补齐差异与仓库证据\",\"hungEvidence\":\"仓库页\"},{\"title\":\"补齐对比测试证据\"}]}");
        Map<String, Object> home = fixture.service.home(1L, 17L);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> actions = (List<Map<String, Object>>) home.get("nextActions");
        assertEquals("TASK_BOOK", actions.get(0).get("type"));
        assertEquals("已回挂 1/2", actions.get(0).get("meta"));
        assertEquals(1, ((Number) actions.get(0).get("hungCount")).intValue());
        assertEquals(2, ((Number) actions.get(0).get("hungTotal")).intValue());
    }

    @Test
    void unconfirmedTaskBookDoesNotLeadHome() {
        Fixture fixture = homeFixture("student-home-task-book-open", true, false);
        Map<String, Object> home = fixture.service.home(1L, 17L);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> actions = (List<Map<String, Object>>) home.get("nextActions");
        assertTrue(actions.stream().noneMatch(action -> "TASK_BOOK".equals(action.get("type"))));
    }

    @Test
    void unpublishedTaskBookDoesNotLeadHome() {
        Fixture fixture = homeFixture("student-home-task-book-draft", false, true);
        Map<String, Object> home = fixture.service.home(1L, 17L);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> actions = (List<Map<String, Object>>) home.get("nextActions");
        assertTrue(actions.stream().noneMatch(action -> "TASK_BOOK".equals(action.get("type"))));
    }

    private static Fixture homeFixture(String dbName, boolean published, boolean confirmed) {
        return homeFixture(dbName, published, confirmed,
                published ? "{\"published\":true,\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}" : null);
    }

    private static Fixture homeFixture(String dbName, boolean published, boolean confirmed, String taskBookJson) {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:" + dbName + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("""
                CREATE TABLE users (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, username VARCHAR(100), role VARCHAR(30),
                    school_name VARCHAR(100), college_name VARCHAR(100), class_name VARCHAR(100)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team (
                    id BIGINT PRIMARY KEY, tenant_id BIGINT, name VARCHAR(100), description VARCHAR(255),
                    status VARCHAR(30), updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team_member (
                    id BIGINT PRIMARY KEY, team_id BIGINT, user_id BIGINT, role_in_team VARCHAR(30),
                    position_name VARCHAR(100), joined_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE meeting (
                    id BIGINT PRIMARY KEY, title VARCHAR(255), status VARCHAR(30), start_time TIMESTAMP,
                    end_time TIMESTAMP, duration_minutes INT
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_roadshow_binding (
                    id BIGINT PRIMARY KEY, team_id BIGINT, meeting_id BIGINT, roadshow_type VARCHAR(30)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY, team_id BIGINT, source_type VARCHAR(40), meeting_id BIGINT,
                    report_id BIGINT, created_by BIGINT, status VARCHAR(30), completed_at TIMESTAMP,
                    docket_id VARCHAR(64), teacher_confirmed TINYINT, deliberation_stage VARCHAR(32)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_report (
                    id BIGINT PRIMARY KEY, session_id BIGINT, meeting_id BIGINT, overall_score DECIMAL(6,2),
                    dimensions_json CLOB, improvement_priorities_json CLOB, status VARCHAR(30),
                    completed_at TIMESTAMP, task_book_published TINYINT, task_book_json CLOB
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_docket (
                    docket_id VARCHAR(64) PRIMARY KEY, task_book_published TINYINT, task_book_json CLOB,
                    task_book_published_session_id BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_docket_run (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT, docket_id VARCHAR(64), run_index INT,
                    session_id BIGINT, report_id BIGINT, status VARCHAR(30)
                )
                """);
        jdbc.update("INSERT INTO users(id, tenant_id, username, role) VALUES (17, 1, 'student', 'STUDENT')");
        jdbc.update("INSERT INTO project_team(id, tenant_id, name, status, updated_at) VALUES (5, 1, 'team', 'ACTIVE', CURRENT_TIMESTAMP)");
        jdbc.update("INSERT INTO project_team_member(id, team_id, user_id, role_in_team, joined_at) VALUES (1, 5, 17, 'MEMBER', CURRENT_TIMESTAMP)");
        jdbc.update("""
                INSERT INTO ai_scoring_session(
                    id, team_id, source_type, meeting_id, report_id, created_by, status, completed_at,
                    docket_id, teacher_confirmed, deliberation_stage
                ) VALUES (47, 5, 'uploaded_video', NULL, 55, 17, 'completed', CURRENT_TIMESTAMP,
                    'docket-a', ?, ?)
                """, confirmed ? 1 : 0, confirmed ? "frozen" : "await_teacher");
        jdbc.update("""
                INSERT INTO ai_score_report(
                    id, session_id, meeting_id, overall_score, dimensions_json,
                    improvement_priorities_json, status, completed_at, task_book_published, task_book_json
                ) VALUES (55, 47, NULL, 48.30, '{}', '[]', 'completed', CURRENT_TIMESTAMP, ?, ?)
                """, published ? 1 : 0, taskBookJson);
        jdbc.update("""
                INSERT INTO ai_score_docket(docket_id, task_book_published, task_book_json, task_book_published_session_id)
                VALUES ('docket-a', ?, ?, ?)
                """, published ? 1 : 0, taskBookJson,
                published ? 47L : null);
        jdbc.update("INSERT INTO ai_score_docket_run(docket_id, run_index, session_id, report_id, status) VALUES ('docket-a', 9, 47, 55, 'completed')");

        StudentTrainingService training = mock(StudentTrainingService.class);
        when(training.currentCamp(1L, 17L)).thenReturn(Map.of("hasCamp", true, "teamId", 5L));
        when(training.today(1L, 17L)).thenReturn(Map.of("hasTrainingDay", false));
        when(training.plan(1L, 17L)).thenReturn(Map.of("hasCamp", false));
        StudentLearningAnalyticsService analytics = mock(StudentLearningAnalyticsService.class);
        when(analytics.weekly(17L)).thenReturn(Map.of("daily", List.of(), "totalSeconds", 0));
        return new Fixture(new StudentHomeService(jdbc, new ObjectMapper(), training, analytics));
    }

    private record Fixture(StudentHomeService service) {
    }

    private Object valueIgnoreCase(Map<String, Object> values, String key) {
        return values.entrySet().stream()
                .filter(entry -> entry.getKey().equalsIgnoreCase(key))
                .map(Map.Entry::getValue)
                .findFirst()
                .orElse(null);
    }
}
