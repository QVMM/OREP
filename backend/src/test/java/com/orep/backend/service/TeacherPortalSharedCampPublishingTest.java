package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TeacherPortalSharedCampPublishingTest {
    private JdbcTemplate jdbc;
    private TrainingDayContentService contentService;
    private TeacherPortalService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:shared_camp_" + UUID.randomUUID()
                        + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        createSchema();
        seedSharedCamp();
        contentService = mock(TrainingDayContentService.class);
        when(contentService.sanitizeHtml(org.mockito.ArgumentMatchers.any())).thenReturn("");
        when(contentService.teacherAttachments(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyLong()
        )).thenReturn(java.util.List.of());
        service = new TeacherPortalService(
                jdbc,
                new ObjectMapper(),
                contentService,
                mock(NotificationService.class),
                new TrainingDayAvailabilityService(),
                mock(PlaybackLibraryService.class),
                mock(StudentLearningAnalyticsService.class)
        );
    }

    @Test
    void publishingSharedDayCreatesAndMaintainsOneTaskPerActiveTeam() {
        service.updateTrainingDay(
                7L,
                88L,
                "TEACHER",
                51L,
                Map.of(
                        "title", "共享训练任务",
                        "summary", "每队独立提交",
                        "status", "PUBLISHED",
                        "dueAt", LocalDateTime.of(2026, 7, 24, 22, 0)
                )
        );

        assertEquals(2, count("SELECT COUNT(*) FROM project_task"));
        assertEquals(2, count("SELECT COUNT(*) FROM training_day_task WHERE training_day_id=51"));
        assertEquals(1, count("SELECT COUNT(*) FROM project_task WHERE team_id=101"));
        assertEquals(1, count("SELECT COUNT(*) FROM project_task WHERE team_id=102"));
        assertEquals(1, count("""
                SELECT COUNT(*) FROM project_task_assignee a
                JOIN project_task t ON t.id=a.task_id
                WHERE t.team_id=101 AND a.team_id=101 AND a.user_id=201
                """));
        assertEquals(1, count("""
                SELECT COUNT(*) FROM project_task_assignee a
                JOIN project_task t ON t.id=a.task_id
                WHERE t.team_id=102 AND a.team_id=102 AND a.user_id=202
                """));
        assertEquals(0, count("""
                SELECT COUNT(*) FROM project_task_assignee a
                JOIN project_task t ON t.id=a.task_id
                WHERE t.team_id<>a.team_id
                """));

        service.updateTrainingDay(
                7L,
                88L,
                "TEACHER",
                51L,
                Map.of("title", "同步后的标题", "summary", "同步后的说明")
        );

        assertEquals(2, count("SELECT COUNT(*) FROM project_task WHERE title='同步后的标题'"));
        assertEquals(2, count("SELECT COUNT(*) FROM project_task WHERE description='同步后的说明'"));
    }

    @Test
    void teacherMissingOneActiveTeamCannotWriteSharedTrainingDay() {
        jdbc.update("UPDATE project_team SET mentor_id=99 WHERE id=102");

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.updateTrainingDay(
                        7L,
                        88L,
                        "TEACHER",
                        51L,
                        Map.of("title", "越权修改")
                )
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertEquals("原始标题", jdbc.queryForObject(
                "SELECT title FROM training_day WHERE id=51",
                String.class
        ));
        assertEquals(0, count("SELECT COUNT(*) FROM project_task"));
    }

    @Test
    void draftTrainingDayCannotTransitionDirectlyToClosed() {
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.updateTrainingDay(
                        7L,
                        88L,
                        "TEACHER",
                        51L,
                        Map.of("status", "CLOSED")
                )
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals("DRAFT", jdbc.queryForObject(
                "SELECT status FROM training_day WHERE id=51",
                String.class
        ));
    }

    private int count(String sql) {
        Integer value = jdbc.queryForObject(sql, Integer.class);
        return value == null ? 0 : value;
    }

    private void seedSharedCamp() {
        jdbc.update("""
                INSERT INTO training_camp
                (id,tenant_id,name,start_date,end_date,total_days,status)
                VALUES (31,7,'共享营期','2026-07-01','2026-07-31',31,'PLANNED')
                """);
        jdbc.update("""
                INSERT INTO project_team(id,tenant_id,name,status,mentor_id)
                VALUES (101,7,'一队','ACTIVE',88),(102,7,'二队','ACTIVE',88)
                """);
        jdbc.update("""
                INSERT INTO training_camp_team(camp_id,team_id,status)
                VALUES (31,101,'ACTIVE'),(31,102,'ACTIVE')
                """);
        jdbc.update("""
                INSERT INTO users(id,role) VALUES (201,'STUDENT'),(202,'STUDENT')
                """);
        jdbc.update("""
                INSERT INTO project_team_member(team_id,user_id,role_in_team)
                VALUES (101,201,'MEMBER'),(102,202,'MEMBER')
                """);
        jdbc.update("""
                INSERT INTO training_day
                (id,camp_id,day_no,training_date,title,summary,content_html,requirements_json,due_at,status)
                VALUES (51,31,1,'2026-07-24','原始标题','','','[]','2026-07-24 22:00:00','DRAFT')
                """);
    }

    private void createSchema() {
        jdbc.execute("""
                CREATE TABLE training_camp(
                  id BIGINT PRIMARY KEY,
                  tenant_id BIGINT NOT NULL,
                  name VARCHAR(120),
                  start_date DATE,
                  end_date DATE,
                  total_days INT,
                  status VARCHAR(24)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team(
                  id BIGINT PRIMARY KEY,
                  tenant_id BIGINT NOT NULL,
                  name VARCHAR(120),
                  status VARCHAR(24),
                  mentor_id BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_camp_team(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  camp_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  status VARCHAR(24)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_team_member(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  team_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  role_in_team VARCHAR(24)
                )
                """);
        jdbc.execute("CREATE TABLE users(id BIGINT PRIMARY KEY,role VARCHAR(24))");
        jdbc.execute("""
                CREATE TABLE training_day(
                  id BIGINT PRIMARY KEY,
                  camp_id BIGINT NOT NULL,
                  day_no INT,
                  training_date DATE,
                  title VARCHAR(160),
                  summary VARCHAR(800),
                  content_html CLOB,
                  requirements_json CLOB,
                  due_at TIMESTAMP,
                  status VARCHAR(24),
                  early_unlocked_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  team_id BIGINT NOT NULL,
                  stage_key VARCHAR(40),
                  title VARCHAR(160),
                  description VARCHAR(800),
                  task_type VARCHAR(40),
                  task_type_label VARCHAR(80),
                  created_by BIGINT,
                  priority VARCHAR(24),
                  status VARCHAR(24),
                  start_at TIMESTAMP,
                  due_at TIMESTAMP,
                  review_required INT,
                  updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_day_task(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  training_day_id BIGINT NOT NULL,
                  task_id BIGINT NOT NULL,
                  is_primary INT,
                  sort_order INT,
                  UNIQUE(training_day_id,task_id)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task_requirement(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  task_id BIGINT,
                  title VARCHAR(160),
                  description VARCHAR(500),
                  required INT,
                  asset_type VARCHAR(40),
                  sort_order INT
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task_assignee(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  task_id BIGINT,
                  team_id BIGINT,
                  user_id BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE teacher_portal_event(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  tenant_id BIGINT,
                  actor_user_id BIGINT,
                  event_type VARCHAR(60),
                  target_type VARCHAR(60),
                  target_id BIGINT,
                  payload_json CLOB
                )
                """);
    }
}
