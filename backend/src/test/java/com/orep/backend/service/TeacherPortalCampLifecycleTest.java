package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.web.server.ResponseStatusException;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;

class TeacherPortalCampLifecycleTest {
    private JdbcTemplate jdbc;
    private TeacherPortalService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:camp_lifecycle_" + UUID.randomUUID()
                        + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        createSchema();
        seedCamp();
        service = new TeacherPortalService(
                jdbc,
                new ObjectMapper(),
                mock(TrainingDayContentService.class),
                mock(NotificationService.class),
                new TrainingDayAvailabilityService(),
                mock(PlaybackLibraryService.class),
                mock(StudentLearningAnalyticsService.class)
        );
    }

    @Test
    void rescheduleMovesCampWeeksDaysAndTasksByTheSameOffset() {
        service.rescheduleCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("startDate", "2026-07-27")
        );

        assertEquals(LocalDate.of(2026, 7, 27), date("training_camp", 101L, "start_date"));
        assertEquals(LocalDate.of(2026, 7, 28), date("training_camp", 101L, "end_date"));
        assertEquals(LocalDate.of(2026, 7, 27), date("training_camp_week", 501L, "start_date"));
        assertEquals(LocalDate.of(2026, 7, 28), date("training_camp_week", 501L, "end_date"));
        assertEquals(LocalDate.of(2026, 7, 27), date("training_day", 1001L, "training_date"));
        assertEquals(LocalDateTime.of(2026, 7, 27, 22, 0), dateTime("training_day", 1001L, "due_at"));
        assertEquals(null, dateTime("training_day", 1001L, "early_unlocked_at"));
        assertEquals(LocalDateTime.of(2026, 7, 27, 0, 0), dateTime("project_task", 2001L, "start_at"));
        assertEquals(LocalDateTime.of(2026, 7, 27, 22, 0), dateTime("project_task", 2001L, "due_at"));
    }

    @Test
    void rescheduleCanShiftIntoDatesStillOccupiedByTheSameCamp() {
        service.rescheduleCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("startDate", "2026-07-23")
        );

        assertEquals(LocalDate.of(2026, 7, 23), date("training_day", 1001L, "training_date"));
        assertEquals(LocalDate.of(2026, 7, 24), date("training_day", 1002L, "training_date"));
    }

    @Test
    void rescheduleRejectsCampWithSubmissions() {
        insertSubmission();

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.rescheduleCamp(
                        1L,
                        9L,
                        "TEACHER",
                        101L,
                        Map.of("startDate", "2026-07-27")
                )
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals(LocalDate.of(2026, 7, 22), date("training_camp", 101L, "start_date"));
    }

    @Test
    void rescheduleRejectsOverlappingCampForTheSameTeam() {
        jdbc.update("""
                INSERT INTO training_camp(id,tenant_id,name,start_date,end_date,total_days,status)
                VALUES (102,1,'第二期集训','2026-07-28','2026-08-02',6,'PLANNED')
                """);
        jdbc.update("""
                INSERT INTO training_camp_team(camp_id,team_id,status)
                VALUES (102,301,'ACTIVE')
                """);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.rescheduleCamp(
                        1L,
                        9L,
                        "TEACHER",
                        101L,
                        Map.of("startDate", "2026-07-27")
                )
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals(LocalDate.of(2026, 7, 22), date("training_camp", 101L, "start_date"));
    }

    @Test
    void archiveOnlyChangesCampStatusAndKeepsHistory() {
        insertSubmission();

        Map<String, Object> result = service.deleteCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("mode", "ARCHIVE")
        );

        assertEquals("ARCHIVE", result.get("mode"));
        assertEquals("ARCHIVED", text("training_camp", 101L, "status"));
        assertEquals(2, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
        assertEquals(1, count("SELECT COUNT(*) FROM project_task_submission WHERE task_id=2001"));
    }

    @Test
    void purgeRequiresExactCampName() {
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.deleteCamp(
                        1L,
                        9L,
                        "TEACHER",
                        101L,
                        Map.of("mode", "PURGE", "confirmationName", "错误名称")
                )
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        assertEquals(1, count("SELECT COUNT(*) FROM training_camp WHERE id=101"));
    }

    @Test
    void extendCampAppendsDraftDaysAndKeepsExistingSchedule() {
        Map<String, Object> result = service.extendCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("totalDays", 5)
        );

        assertEquals("EXTENDED", result.get("operation"));
        assertEquals(5, intColumn("training_camp", 101L, "total_days"));
        assertEquals(LocalDate.of(2026, 7, 22), date("training_camp", 101L, "start_date"));
        assertEquals(LocalDate.of(2026, 7, 26), date("training_camp", 101L, "end_date"));
        assertEquals(5, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
        assertEquals(LocalDate.of(2026, 7, 22), date("training_day", 1001L, "training_date"));
        assertEquals(LocalDate.of(2026, 7, 23), date("training_day", 1002L, "training_date"));
        assertEquals(LocalDate.of(2026, 7, 24), dayDateByNo(101L, 3));
        assertEquals(LocalDate.of(2026, 7, 26), dayDateByNo(101L, 5));
        assertEquals("DRAFT", dayStatusByNo(101L, 3));
        assertEquals("PUBLISHED", text("training_day", 1001L, "status"));
        assertEquals(LocalDate.of(2026, 7, 22), date("training_camp_week", 501L, "start_date"));
        assertEquals(LocalDate.of(2026, 7, 26), date("training_camp_week", 501L, "end_date"));
    }

    @Test
    void extendCampAcceptsAddedDaysAndAllowsExistingSubmissions() {
        insertSubmission();

        Map<String, Object> result = service.extendCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("addedDays", 3)
        );

        assertEquals("EXTENDED", result.get("operation"));
        assertEquals(5, intColumn("training_camp", 101L, "total_days"));
        assertEquals(5, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
        assertEquals(1, count("SELECT COUNT(*) FROM project_task_submission WHERE task_id=2001"));
    }

    @Test
    void extendCampRejectsDecreaseOrUnchangedDays() {
        ResponseStatusException unchanged = assertThrows(
                ResponseStatusException.class,
                () -> service.extendCamp(1L, 9L, "TEACHER", 101L, Map.of("totalDays", 2))
        );
        ResponseStatusException decreased = assertThrows(
                ResponseStatusException.class,
                () -> service.extendCamp(1L, 9L, "TEACHER", 101L, Map.of("totalDays", 1))
        );

        assertEquals(HttpStatus.BAD_REQUEST, unchanged.getStatusCode());
        assertEquals(HttpStatus.BAD_REQUEST, decreased.getStatusCode());
        assertEquals(2, intColumn("training_camp", 101L, "total_days"));
    }

    @Test
    void extendCampCreatesAnotherWeekWhenCrossingSevenDays() {
        service.extendCamp(1L, 9L, "TEACHER", 101L, Map.of("totalDays", 10));

        assertEquals(10, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
        assertEquals(2, count("SELECT COUNT(*) FROM training_camp_week WHERE camp_id=101"));
        assertEquals(LocalDate.of(2026, 7, 28), date("training_camp_week", 501L, "end_date"));
        assertEquals(LocalDate.of(2026, 7, 29), dayDateByNo(101L, 8));
        assertEquals(LocalDate.of(2026, 7, 31), date("training_camp", 101L, "end_date"));
    }

    @Test
    void extendCampRejectsMoreThan365Days() {
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.extendCamp(1L, 9L, "TEACHER", 101L, Map.of("totalDays", 366))
        );

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        assertEquals(2, intColumn("training_camp", 101L, "total_days"));
    }

    @Test
    void extendCampReactivatesCompletedCampWhenNewEndIsInTheFuture() {
        jdbc.update("UPDATE training_camp SET status='COMPLETED' WHERE id=101");

        Map<String, Object> result = service.extendCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("totalDays", 360)
        );

        assertEquals("EXTENDED", result.get("operation"));
        assertEquals("ACTIVE", text("training_camp", 101L, "status"));
        assertEquals(360, intColumn("training_camp", 101L, "total_days"));
    }

    @Test
    void extendCampRejectsOverlappingCampForTheSameTeam() {
        jdbc.update("""
                INSERT INTO training_camp(id,tenant_id,name,start_date,end_date,total_days,status)
                VALUES (102,1,'第二期集训','2026-07-25','2026-07-30',6,'PLANNED')
                """);
        jdbc.update("""
                INSERT INTO training_camp_team(camp_id,team_id,status)
                VALUES (102,301,'ACTIVE')
                """);

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.extendCamp(1L, 9L, "TEACHER", 101L, Map.of("totalDays", 5))
        );

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals(2, intColumn("training_camp", 101L, "total_days"));
        assertEquals(2, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
    }

    @Test
    void teacherWithoutAllCampTeamsCannotManageTheCamp() {
        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.rescheduleCamp(
                        1L,
                        10L,
                        "TEACHER",
                        101L,
                        Map.of("startDate", "2026-07-27")
                )
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertEquals(LocalDate.of(2026, 7, 22), date("training_camp", 101L, "start_date"));
    }

    @Test
    void purgeDeletesCampOwnedGraphButKeepsTeamAndUsers() {
        insertSubmission();
        jdbc.update("""
                INSERT INTO project_task_requirement(task_id,title)
                VALUES (2001,'提交说明')
                """);
        jdbc.update("""
                INSERT INTO project_task_assignee(task_id,team_id,user_id)
                VALUES (2001,301,401)
                """);
        jdbc.update("""
                INSERT INTO training_day_attachment(training_day_id,file_url)
                VALUES (1001,'/uploads/task/instructions/1001/attachments/a.pdf')
                """);
        jdbc.update("""
                INSERT INTO training_day_learning_resource(training_day_id,resource_url)
                VALUES (1001,'/uploads/task/learning/1001/a.pdf')
                """);

        Map<String, Object> result = service.deleteCamp(
                1L,
                9L,
                "TEACHER",
                101L,
                Map.of("mode", "PURGE", "confirmationName", "第一阶段集训")
        );

        assertEquals("PURGE", result.get("mode"));
        assertEquals(0, count("SELECT COUNT(*) FROM training_camp WHERE id=101"));
        assertEquals(0, count("SELECT COUNT(*) FROM training_day WHERE camp_id=101"));
        assertEquals(0, count("SELECT COUNT(*) FROM project_task WHERE id IN (2001,2002)"));
        assertEquals(0, count("SELECT COUNT(*) FROM project_task_submission WHERE task_id=2001"));
        assertEquals(0, count("SELECT COUNT(*) FROM training_day_attachment WHERE training_day_id=1001"));
        assertEquals(0, count("SELECT COUNT(*) FROM training_day_learning_resource WHERE training_day_id=1001"));
        assertEquals(1, count("SELECT COUNT(*) FROM project_team WHERE id=301"));
        assertEquals(1, count("SELECT COUNT(*) FROM users WHERE id=401"));
    }

    private void insertSubmission() {
        jdbc.update("""
                INSERT INTO project_task_submission(id,task_id,team_id,submitter_id,status)
                VALUES (3001,2001,301,401,'PENDING_REVIEW')
                """);
    }

    private LocalDate date(String table, Long id, String column) {
        Date value = jdbc.queryForObject(
                "SELECT " + column + " FROM " + table + " WHERE id=?",
                Date.class,
                id
        );
        return value == null ? null : value.toLocalDate();
    }

    private LocalDateTime dateTime(String table, Long id, String column) {
        Timestamp value = jdbc.queryForObject(
                "SELECT " + column + " FROM " + table + " WHERE id=?",
                Timestamp.class,
                id
        );
        return value == null ? null : value.toLocalDateTime();
    }

    private String text(String table, Long id, String column) {
        return jdbc.queryForObject(
                "SELECT " + column + " FROM " + table + " WHERE id=?",
                String.class,
                id
        );
    }

    private int count(String sql) {
        Integer value = jdbc.queryForObject(sql, Integer.class);
        return value == null ? 0 : value;
    }

    private int intColumn(String table, Long id, String column) {
        Integer value = jdbc.queryForObject(
                "SELECT " + column + " FROM " + table + " WHERE id=?",
                Integer.class,
                id
        );
        return value == null ? 0 : value;
    }

    private LocalDate dayDateByNo(Long campId, int dayNo) {
        Date value = jdbc.queryForObject(
                "SELECT training_date FROM training_day WHERE camp_id=? AND day_no=?",
                Date.class,
                campId,
                dayNo
        );
        return value == null ? null : value.toLocalDate();
    }

    private String dayStatusByNo(Long campId, int dayNo) {
        return jdbc.queryForObject(
                "SELECT status FROM training_day WHERE camp_id=? AND day_no=?",
                String.class,
                campId,
                dayNo
        );
    }

    private void seedCamp() {
        jdbc.update("""
                INSERT INTO project_team(id,tenant_id,name,status,mentor_id)
                VALUES (301,1,'应用攻坚队','ACTIVE',9)
                """);
        jdbc.update("INSERT INTO users(id,role) VALUES (401,'STUDENT')");
        jdbc.update("""
                INSERT INTO training_camp(id,tenant_id,name,start_date,end_date,total_days,status)
                VALUES (101,1,'第一阶段集训','2026-07-22','2026-07-23',2,'PLANNED')
                """);
        jdbc.update("""
                INSERT INTO training_camp_team(camp_id,team_id,status)
                VALUES (101,301,'ACTIVE')
                """);
        jdbc.update("""
                INSERT INTO training_camp_week(id,camp_id,week_no,title,start_date,end_date)
                VALUES (501,101,1,'第 1 周','2026-07-22','2026-07-23')
                """);
        jdbc.update("""
                INSERT INTO training_day
                (id,camp_id,week_id,day_no,training_date,title,due_at,status,early_unlocked_at)
                VALUES
                (1001,101,501,1,'2026-07-22','第 1 天','2026-07-22 22:00:00','PUBLISHED','2026-07-21 08:00:00'),
                (1002,101,501,2,'2026-07-23','第 2 天','2026-07-23 22:00:00','DRAFT',NULL)
                """);
        jdbc.update("""
                INSERT INTO project_task(id,team_id,title,start_at,due_at)
                VALUES
                (2001,301,'第 1 天任务','2026-07-22 00:00:00','2026-07-22 22:00:00'),
                (2002,301,'第 2 天任务','2026-07-23 00:00:00','2026-07-23 22:00:00')
                """);
        jdbc.update("""
                INSERT INTO training_day_task(training_day_id,task_id)
                VALUES (1001,2001),(1002,2002)
                """);
    }

    private void createSchema() {
        jdbc.execute("""
                CREATE TABLE project_team(
                  id BIGINT PRIMARY KEY,
                  tenant_id BIGINT NOT NULL,
                  name VARCHAR(120),
                  status VARCHAR(24),
                  mentor_id BIGINT
                )
                """);
        jdbc.execute("CREATE TABLE users(id BIGINT PRIMARY KEY,role VARCHAR(24))");
        jdbc.execute("""
                CREATE TABLE project_team_member(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  team_id BIGINT,
                  user_id BIGINT,
                  role_in_team VARCHAR(24)
                )
                """);
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
                CREATE TABLE training_camp_team(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  camp_id BIGINT,
                  team_id BIGINT,
                  status VARCHAR(24)
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_camp_week(
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  camp_id BIGINT,
                  week_no INT,
                  title VARCHAR(120),
                  start_date DATE,
                  end_date DATE,
                  sort_order INT
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_day(
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  camp_id BIGINT,
                  week_id BIGINT,
                  day_no INT,
                  training_date DATE,
                  title VARCHAR(160),
                  summary VARCHAR(500),
                  requirements_json CLOB,
                  due_at TIMESTAMP,
                  status VARCHAR(24),
                  sort_order INT,
                  early_unlocked_at TIMESTAMP,
                  CONSTRAINT uk_training_day_date UNIQUE(camp_id, training_date)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task(
                  id BIGINT PRIMARY KEY,
                  team_id BIGINT,
                  title VARCHAR(160),
                  start_at TIMESTAMP,
                  due_at TIMESTAMP,
                  updated_at TIMESTAMP
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_day_task(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  training_day_id BIGINT,
                  task_id BIGINT
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task_submission(
                  id BIGINT PRIMARY KEY,
                  task_id BIGINT,
                  team_id BIGINT,
                  submitter_id BIGINT,
                  status VARCHAR(32),
                  attachment_url VARCHAR(500)
                )
                """);
        jdbc.execute("""
                CREATE TABLE project_task_requirement(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  task_id BIGINT,
                  title VARCHAR(160)
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
                CREATE TABLE training_day_attachment(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  training_day_id BIGINT,
                  file_url VARCHAR(500)
                )
                """);
        jdbc.execute("""
                CREATE TABLE training_day_learning_resource(
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  training_day_id BIGINT,
                  resource_url VARCHAR(1000)
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
