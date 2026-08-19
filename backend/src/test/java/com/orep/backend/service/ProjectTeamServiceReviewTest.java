package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.aop.framework.ProxyFactory;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.annotation.AnnotationTransactionAttributeSource;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.interceptor.TransactionInterceptor;
import org.springframework.web.server.ResponseStatusException;

import javax.sql.DataSource;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ProjectTeamServiceReviewTest {
    private JdbcTemplate jdbc;
    private ProjectTeamService service;

    @BeforeEach
    void setUp() {
        jdbc = mock(JdbcTemplate.class);
        service = new ProjectTeamService(
                jdbc,
                mock(RoadshowMemoryAnalyzer.class),
                mock(AiResultEvidenceAnchorExtractor.class),
                mock(RecordingEvidenceAnchorBuilder.class),
                mock(ScoreEvidenceAnchorStore.class),
                mock(CompetitionReadinessService.class),
                new TrainingDayAvailabilityService(),
                "./uploads"
        );
    }

    @Test
    void nonTeacherRoleCannotUseTeacherReviewEndpoints() {
        ResponseStatusException queueError = assertThrows(ResponseStatusException.class,
                () -> service.teacherReviewQueue(7L, 99L, "STUDENT"));
        ResponseStatusException detailError = assertThrows(ResponseStatusException.class,
                () -> service.teacherSubmissionDetail(101L, 7L, 99L, "CAPTAIN"));

        assertEquals(HttpStatus.FORBIDDEN, queueError.getStatusCode());
        assertEquals(HttpStatus.FORBIDDEN, detailError.getStatusCode());
        verify(jdbc, never()).queryForList(anyString(), any(Object[].class));
    }

    @Test
    void teacherQueueUsesTenantAndMentorScopeWithTeacherParameters() {
        List<QueryCall> calls = recordQueriesReturning(List.of());

        service.teacherReviewQueue(7L, 99L, "TEACHER");

        QueryCall queue = callContaining(calls, "JOIN project_team pt");
        assertTrue(queue.sql().contains("pt.tenant_id = ?"));
        assertTrue(queue.sql().contains("pt.mentor_id = ?"));
        assertTrue(queue.sql().contains("role_in_team = 'MENTOR'"));
        assertEquals(List.of(7L, 99L, 99L), List.of(queue.args()));
    }

    @Test
    void adminQueueUsesOnlyTenantScopeAndLatestPendingSubmissionFilter() {
        List<QueryCall> calls = recordQueriesReturning(List.of());

        service.teacherReviewQueue(7L, 99L, "ADMIN");

        QueryCall queue = callContaining(calls, "JOIN project_team pt");
        assertTrue(queue.sql().contains("pt.tenant_id = ?"));
        assertFalse(queue.sql().contains("pt.mentor_id = ?"));
        assertFalse(queue.sql().contains("role_in_team = 'MENTOR'"));
        assertTrue(queue.sql().contains("ORDER BY latest.version_no DESC, latest.id DESC LIMIT 1"));
        assertTrue(queue.sql().contains("s.status IN ('PENDING_REVIEW', 'REVIEWING')"));
        assertTrue(queue.sql().contains("ORDER BY s.created_at ASC"));
        assertEquals(List.of(7L), List.of(queue.args()));
    }

    @Test
    void detailIncludesRequirementsHistoryPayloadsAndCanReviewForLatestPendingVersion() {
        Map<String, Object> detail = mutableMap(
                "id", 101L,
                "submissionId", 101L,
                "taskId", 55L,
                "teamId", 8L,
                "status", "PENDING_REVIEW",
                "latestSubmissionId", 101L
        );
        List<Map<String, Object>> requirements = List.of(Map.of("id", 1L, "title", "提交文档"));
        List<Map<String, Object>> history = List.of(
                Map.of("id", 101L, "versionNo", 2),
                Map.of("id", 90L, "versionNo", 1)
        );
        List<Map<String, Object>> assets = List.of(Map.of("submissionId", 101L, "fileUrl", "/a.pdf"));
        List<Map<String, Object>> links = List.of(Map.of("submissionId", 101L, "url", "https://example.test"));
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("WHERE s.id = ?") && sql.contains("JOIN project_team pt")) return List.of(detail);
            if (sql.contains("FROM project_submission_asset")) return assets;
            if (sql.contains("FROM project_submission_link")) return links;
            if (sql.contains("FROM project_task_requirement")) return requirements;
            if (sql.contains("history.version_no")) return history;
            return List.of();
        });

        Map<String, Object> result = service.teacherSubmissionDetail(101L, 7L, 99L, "SCHOOL_ADMIN");

        assertEquals(requirements, result.get("requirements"));
        List<Map<String, Object>> resultHistory = mapRows(result.get("history"));
        assertEquals(2, resultHistory.size());
        assertEquals(101L, resultHistory.get(0).get("id"));
        assertEquals(assets, resultHistory.get(0).get("assets"));
        assertEquals(links, resultHistory.get(0).get("links"));
        assertEquals(90L, resultHistory.get(1).get("id"));
        assertEquals(List.of(), resultHistory.get(1).get("assets"));
        assertEquals(List.of(), resultHistory.get(1).get("links"));
        assertEquals(assets, result.get("assets"));
        assertEquals(links, result.get("links"));
        assertEquals(1, result.get("assetCount"));
        assertEquals(1, result.get("linkCount"));
        assertEquals(true, result.get("canReview"));
    }

    @Test
    void detailUsesSameTeacherScopeAndReturnsNotFoundWhenSubmissionIsOutsideIt() {
        List<QueryCall> calls = recordQueriesReturning(List.of());

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.teacherSubmissionDetail(101L, 7L, 99L, "TEACHER"));

        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
        QueryCall detail = callContaining(calls, "WHERE s.id = ?");
        assertTrue(detail.sql().contains("pt.tenant_id = ?"));
        assertTrue(detail.sql().contains("pt.mentor_id = ?"));
        assertEquals(List.of(101L, 7L, 99L, 99L), List.of(detail.args()));
    }

    @Test
    void detailCannotReviewAnOlderOrAlreadyReviewedVersion() {
        Map<String, Object> detail = mutableMap(
                "id", 90L,
                "submissionId", 90L,
                "taskId", 55L,
                "status", "APPROVED",
                "latestSubmissionId", 101L
        );
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            return sql.contains("WHERE s.id = ?") && sql.contains("JOIN project_team pt")
                    ? List.of(detail)
                    : List.of();
        });

        Map<String, Object> result = service.teacherSubmissionDetail(90L, 7L, 99L, "ADMIN");

        assertEquals(false, result.get("canReview"));
    }

    @Test
    void h2MySqlModeQueriesReturnScopedQueueAndCompleteDetailPayload() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        List<Map<String, Object>> queue = realService.teacherReviewQueue(7L, 99L, "TEACHER");

        assertEquals(1, queue.size());
        Map<String, Object> queued = queue.get(0);
        assertEquals(101L, number(queued.get("id")));
        assertEquals(101L, number(queued.get("submissionId")));
        assertEquals(55L, number(queued.get("taskId")));
        assertEquals("验收任务", queued.get("taskTitle"));
        assertEquals("待验收说明", queued.get("taskDescription"));
        assertEquals("DOCUMENT", queued.get("submissionType"));
        assertEquals("PENDING_REVIEW", queued.get("status"));
        assertEquals("指导团队", queued.get("teamName"));
        assertEquals(5L, number(queued.get("campId")));
        assertEquals("暑期营", queued.get("campName"));
        assertEquals(6L, number(queued.get("dayId")));
        assertEquals(3L, number(queued.get("dayNo")));
        assertEquals(1L, number(queued.get("assetCount")));
        assertEquals(1L, number(queued.get("linkCount")));

        Map<String, Object> detail = realService.teacherSubmissionDetail(101L, 7L, 99L, "TEACHER");

        assertEquals(101L, number(detail.get("submissionId")));
        assertEquals(5L, number(detail.get("campId")));
        assertEquals(6L, number(detail.get("dayId")));
        assertEquals(3L, number(detail.get("dayNo")));
        assertEquals("第三天", detail.get("dayTitle"));
        assertEquals(true, detail.get("canReview"));
        List<Map<String, Object>> requirements = mapRows(detail.get("requirements"));
        assertEquals(1, requirements.size());
        assertEquals("成果文件", requirements.get(0).get("title"));
        assertEquals("FILE", requirements.get(0).get("assetType"));
        List<Map<String, Object>> history = mapRows(detail.get("history"));
        assertEquals(2, history.size());
        assertEquals(101L, number(history.get(0).get("submissionId")));
        assertEquals(2L, number(history.get(0).get("versionNo")));
        assertEquals(90L, number(history.get(1).get("submissionId")));
        assertEquals(1L, number(history.get(1).get("versionNo")));
        List<Map<String, Object>> assets = mapRows(detail.get("assets"));
        assertEquals(1, assets.size());
        assertEquals("/files/result.pdf", assets.get(0).get("fileUrl"));
        List<Map<String, Object>> links = mapRows(detail.get("links"));
        assertEquals(1, links.size());
        assertEquals("https://example.test/result", links.get(0).get("url"));
    }

    @Test
    void sameTenantTeacherCannotReviewTeamTheyDoNotMentor() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> realService.reviewSubmission(102L, 7L, 99L, "TEACHER", reviewBody("APPROVED")));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertEquals("PENDING_REVIEW", submissionStatus(realJdbc, 102L));
        assertEquals("REVIEWING", taskStatus(realJdbc, 56L));
    }

    @Test
    void mentorTeacherCanReviewLatestPendingSubmission() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        Map<String, Object> result = realService.reviewSubmission(
                101L, 7L, 99L, "TEACHER", reviewBody("APPROVED"));

        assertEquals("APPROVED", result.get("status"));
        assertEquals("APPROVED", submissionStatus(realJdbc, 101L));
        assertEquals(99L, number(realJdbc.queryForObject(
                "SELECT reviewer_id FROM project_task_submission WHERE id = 101", Long.class)));
        assertEquals("DONE", taskStatus(realJdbc, 55L));
    }

    @Test
    void adminCanReviewAnyTeamInsideTenant() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        realService.reviewSubmission(102L, 7L, 500L, "SCHOOL_ADMIN", reviewBody("CHANGES_REQUESTED"));

        assertEquals("CHANGES_REQUESTED", submissionStatus(realJdbc, 102L));
        assertEquals("IN_PROGRESS", taskStatus(realJdbc, 56L));
    }

    @Test
    void captainReviewSubmissionPermissionStillWorks() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        realService.reviewSubmission(101L, 7L, 20L, "STUDENT", reviewBody("APPROVED"));

        assertEquals("APPROVED", submissionStatus(realJdbc, 101L));
        assertEquals("DONE", taskStatus(realJdbc, 55L));
    }

    @Test
    void olderSubmissionVersionCannotBeReviewed() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> realService.reviewSubmission(90L, 7L, 500L, "ADMIN", reviewBody("APPROVED")));

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals("CHANGES_REQUESTED", submissionStatus(realJdbc, 90L));
        assertEquals("REVIEWING", taskStatus(realJdbc, 55L));
    }

    @Test
    void reviewedSubmissionCannotBeReviewedAgain() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);
        realService.reviewSubmission(101L, 7L, 500L, "ADMIN", reviewBody("APPROVED"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> realService.reviewSubmission(101L, 7L, 500L, "ADMIN", reviewBody("REJECTED")));

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals("APPROVED", submissionStatus(realJdbc, 101L));
        assertEquals("DONE", taskStatus(realJdbc, 55L));
    }

    @Test
    void submissionFromAnotherTenantCannotBeReviewed() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> realService.reviewSubmission(103L, 7L, 500L, "ADMIN", reviewBody("APPROVED")));

        assertEquals(HttpStatus.NOT_FOUND, error.getStatusCode());
        assertEquals("PENDING_REVIEW", submissionStatus(realJdbc, 103L));
        assertEquals("REVIEWING", taskStatus(realJdbc, 57L));
    }

    @Test
    void invalidReviewTargetStatusRemainsBadRequest() {
        JdbcTemplate realJdbc = mysqlModeJdbc();
        createReviewSchema(realJdbc);
        insertReviewFixtures(realJdbc);
        ProjectTeamService realService = newService(realJdbc);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> realService.reviewSubmission(101L, 7L, 500L, "ADMIN", reviewBody("REVIEWING")));

        assertEquals(HttpStatus.BAD_REQUEST, error.getStatusCode());
        assertEquals("PENDING_REVIEW", submissionStatus(realJdbc, 101L));
        assertEquals("REVIEWING", taskStatus(realJdbc, 55L));
    }

    @Test
    void reviewSubmissionIsTransactional() throws Exception {
        Method method = ProjectTeamService.class.getMethod(
                "reviewSubmission", Long.class, Long.class, Long.class, String.class, Map.class);

        assertTrue(method.isAnnotationPresent(Transactional.class));
    }

    @Test
    void taskUpdateFailureRollsBackSuccessfulSubmissionUpdate() {
        JdbcTemplate setupJdbc = mysqlModeJdbc();
        createReviewSchema(setupJdbc);
        insertReviewFixtures(setupJdbc);
        DataSource dataSource = setupJdbc.getDataSource();
        JdbcTemplate failingJdbc = new JdbcTemplate(dataSource) {
            @Override
            public int update(String sql, Object... args) {
                if (sql.contains("UPDATE project_task SET status")) {
                    throw new IllegalStateException("simulated task update failure");
                }
                return super.update(sql, args);
            }
        };
        ProjectTeamService target = newService(failingJdbc);
        DataSourceTransactionManager transactionManager = new DataSourceTransactionManager(dataSource);
        TransactionInterceptor interceptor = new TransactionInterceptor();
        interceptor.setTransactionManager(transactionManager);
        interceptor.setTransactionAttributeSource(new AnnotationTransactionAttributeSource());
        ProxyFactory proxyFactory = new ProxyFactory(target);
        proxyFactory.setProxyTargetClass(true);
        proxyFactory.addAdvice(interceptor);
        ProjectTeamService transactionalService = (ProjectTeamService) proxyFactory.getProxy();

        assertThrows(IllegalStateException.class,
                () -> transactionalService.reviewSubmission(101L, 7L, 500L, "ADMIN", reviewBody("APPROVED")));

        assertEquals("PENDING_REVIEW", submissionStatus(setupJdbc, 101L));
        assertEquals("REVIEWING", taskStatus(setupJdbc, 55L));
    }

    @Test
    void conditionalSubmissionUpdateLosingRaceReturnsConflictWithoutSideEffects() {
        List<String> updateSql = new ArrayList<>();
        Map<String, Object> submission = mutableMap(
                "id", 101L,
                "taskId", 55L,
                "teamId", 8L,
                "status", "PENDING_REVIEW",
                "versionNo", 2
        );
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("FROM project_task_submission s") && sql.contains("WHERE s.id = ?")) {
                return List.of(submission);
            }
            if (sql.contains("FROM project_team WHERE id = ? AND tenant_id = ?")) {
                return List.of(Map.of("id", 8L, "tenantId", 7L));
            }
            return List.of();
        });
        when(jdbc.queryForObject(contains("SELECT latest.id"), org.mockito.ArgumentMatchers.eq(Long.class), any(Object[].class)))
                .thenReturn(101L);
        when(jdbc.update(contains("UPDATE project_task_submission"), any(Object[].class))).thenAnswer(invocation -> {
            updateSql.add(invocation.getArgument(0));
            return 0;
        });

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.reviewSubmission(101L, 7L, 500L, "ADMIN", reviewBody("APPROVED")));

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals(1, updateSql.size());
        assertTrue(updateSql.get(0).contains("UPDATE project_task_submission current"));
        assertTrue(updateSql.get(0).contains("current.id = ("));
        assertTrue(updateSql.get(0).contains("SELECT eligible.id"));
        assertTrue(updateSql.get(0).contains("FROM ("));
        assertTrue(updateSql.get(0).contains("SELECT candidate.id"));
        assertTrue(updateSql.get(0).contains("FROM project_task_submission candidate"));
        assertTrue(updateSql.get(0).contains("NOT EXISTS"));
        assertTrue(updateSql.get(0).contains("newer.task_id = candidate.task_id"));
        assertTrue(updateSql.get(0).contains("newer.version_no > candidate.version_no"));
        assertTrue(updateSql.get(0).contains("newer.version_no = candidate.version_no"));
        assertTrue(updateSql.get(0).contains("newer.id > candidate.id"));
        verify(jdbc, never()).update(contains("UPDATE project_task SET status"), any(Object[].class));
        verify(jdbc, never()).update(contains("ability_synced_at"), any(Object[].class));
        verify(jdbc, never()).update(contains("UPDATE project_stage"), any(Object[].class));
    }

    private JdbcTemplate mysqlModeJdbc() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.h2.Driver");
        dataSource.setUrl("jdbc:h2:mem:project_team_review_" + UUID.randomUUID()
                + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1");
        dataSource.setUsername("sa");
        dataSource.setPassword("");
        return new JdbcTemplate(dataSource);
    }

    private ProjectTeamService newService(JdbcTemplate template) {
        return new ProjectTeamService(
                template,
                mock(RoadshowMemoryAnalyzer.class),
                mock(AiResultEvidenceAnchorExtractor.class),
                mock(RecordingEvidenceAnchorBuilder.class),
                mock(ScoreEvidenceAnchorStore.class),
                mock(CompetitionReadinessService.class),
                new TrainingDayAvailabilityService(),
                "./uploads"
        );
    }

    private void createReviewSchema(JdbcTemplate template) {
        template.execute("""
                CREATE TABLE users (
                  id BIGINT PRIMARY KEY,
                  username VARCHAR(120) NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE project_team (
                  id BIGINT PRIMARY KEY,
                  tenant_id BIGINT NOT NULL,
                  name VARCHAR(160) NOT NULL,
                  description VARCHAR(500),
                  track_id BIGINT,
                  track_name VARCHAR(160),
                  current_stage VARCHAR(40) DEFAULT 'MATERIAL',
                  status VARCHAR(32) DEFAULT 'ACTIVE',
                  mentor_id BIGINT,
                  start_date DATE,
                  end_date DATE,
                  ability_synced_at TIMESTAMP
                )
                """);
        template.execute("""
                CREATE TABLE project_team_member (
                  team_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  role_in_team VARCHAR(40) NOT NULL,
                  captain_permissions VARCHAR(500)
                )
                """);
        template.execute("""
                CREATE TABLE project_task (
                  id BIGINT PRIMARY KEY,
                  team_id BIGINT NOT NULL,
                  title VARCHAR(160) NOT NULL,
                  description VARCHAR(500),
                  task_type VARCHAR(60),
                  task_type_label VARCHAR(80),
                  priority VARCHAR(20),
                  stage_key VARCHAR(40) DEFAULT 'MATERIAL',
                  status VARCHAR(32) DEFAULT 'REVIEWING',
                  source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER',
                  reviewer_user_id BIGINT,
                  due_at TIMESTAMP
                )
                """);
        template.execute("""
                CREATE TABLE project_task_submission (
                  id BIGINT PRIMARY KEY,
                  task_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  submitter_id BIGINT NOT NULL,
                  submission_type VARCHAR(60),
                  content VARCHAR(1000),
                  attachment_url VARCHAR(500),
                  attachment_name VARCHAR(255),
                  attachment_size BIGINT,
                  attachment_type VARCHAR(120),
                  sync_to_material TINYINT,
                  version_no INT NOT NULL,
                  status VARCHAR(32) NOT NULL,
                  reviewer_id BIGINT,
                  review_comment VARCHAR(1000),
                  reviewed_at TIMESTAMP,
                  created_at TIMESTAMP NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE project_task_assignee (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  task_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  sort_order INT NOT NULL DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE (task_id, user_id)
                )
                """);
        template.execute("""
                CREATE TABLE project_stage (
                  id BIGINT PRIMARY KEY,
                  team_id BIGINT NOT NULL,
                  stage_key VARCHAR(40) NOT NULL,
                  title VARCHAR(80) NOT NULL,
                  status VARCHAR(32) NOT NULL,
                  progress INT NOT NULL,
                  owner_user_id BIGINT,
                  start_date DATE,
                  due_date DATE,
                  is_optional TINYINT DEFAULT 0,
                  suggestion_text VARCHAR(500),
                  sort_order INT NOT NULL
                )
                """);
        template.execute("CREATE TABLE project_material (id BIGINT PRIMARY KEY, team_id BIGINT NOT NULL, review_status VARCHAR(32))");
        template.execute("CREATE TABLE project_roadshow_binding (team_id BIGINT NOT NULL, meeting_id BIGINT)");
        template.execute("CREATE TABLE project_review_issue (id BIGINT PRIMARY KEY, team_id BIGINT NOT NULL, status VARCHAR(32))");
        template.execute("CREATE TABLE course_learning_progress (user_id BIGINT NOT NULL, progress_percent INT)");
        template.execute("CREATE TABLE exam_attempt (user_id BIGINT NOT NULL, score DECIMAL(10,2), total_score DECIMAL(10,2), status VARCHAR(32))");
        template.execute("""
                CREATE TABLE training_camp (
                  id BIGINT PRIMARY KEY,
                  tenant_id BIGINT NOT NULL,
                  name VARCHAR(120) NOT NULL,
                  start_date DATE NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE training_camp_team (
                  camp_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  status VARCHAR(24) NOT NULL,
                  joined_at TIMESTAMP NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE training_day (
                  id BIGINT PRIMARY KEY,
                  camp_id BIGINT NOT NULL,
                  day_no INT NOT NULL,
                  training_date DATE NOT NULL,
                  title VARCHAR(160) NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE training_day_task (
                  training_day_id BIGINT NOT NULL,
                  task_id BIGINT NOT NULL
                )
                """);
        template.execute("""
                CREATE TABLE project_submission_asset (
                  id BIGINT PRIMARY KEY,
                  submission_id BIGINT NOT NULL,
                  task_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  asset_kind VARCHAR(40),
                  file_url VARCHAR(500),
                  file_name VARCHAR(255),
                  file_size BIGINT,
                  file_type VARCHAR(120),
                  sort_order INT,
                  created_at TIMESTAMP
                )
                """);
        template.execute("""
                CREATE TABLE project_submission_link (
                  id BIGINT PRIMARY KEY,
                  submission_id BIGINT NOT NULL,
                  task_id BIGINT NOT NULL,
                  team_id BIGINT NOT NULL,
                  link_type VARCHAR(40),
                  title VARCHAR(160),
                  url VARCHAR(800),
                  sort_order INT,
                  created_at TIMESTAMP
                )
                """);
        template.execute("""
                CREATE TABLE project_task_requirement (
                  id BIGINT PRIMARY KEY,
                  task_id BIGINT NOT NULL,
                  title VARCHAR(160) NOT NULL,
                  description VARCHAR(500),
                  required TINYINT,
                  asset_type VARCHAR(40),
                  sort_order INT
                )
                """);
    }

    private void insertReviewFixtures(JdbcTemplate template) {
        template.update("INSERT INTO users (id, username) VALUES (99, '张老师'), (199, '其他老师'), (20, '队长'), (10, '学生甲')");
        template.update("""
                INSERT INTO project_team (id, tenant_id, name, mentor_id) VALUES
                (8, 7, '指导团队', 199),
                (9, 7, '其他教师团队', 199),
                (10, 8, '其他租户团队', 99)
                """);
        template.update("""
                INSERT INTO project_team_member (team_id, user_id, role_in_team, captain_permissions) VALUES
                (8, 99, 'MENTOR', NULL),
                (8, 20, 'CAPTAIN', '["REVIEW_SUBMISSION"]'),
                (9, 199, 'MENTOR', NULL),
                (10, 99, 'MENTOR', NULL)
                """);
        template.update("""
                INSERT INTO project_task
                (id, team_id, title, description, task_type, task_type_label, priority, due_at) VALUES
                (55, 8, '验收任务', '待验收说明', 'DOCUMENT', '文档交付', 'HIGH', TIMESTAMP '2026-07-25 18:00:00'),
                (56, 9, '其他教师任务', '不可见', 'OTHER', '其他', 'MEDIUM', TIMESTAMP '2026-07-26 18:00:00'),
                (57, 10, '其他租户任务', '不可见', 'OTHER', '其他', 'MEDIUM', TIMESTAMP '2026-07-27 18:00:00')
                """);
        template.update("""
                INSERT INTO project_task_submission
                (id, task_id, team_id, submitter_id, submission_type, content,
                 attachment_url, attachment_name, attachment_size, attachment_type,
                 sync_to_material, version_no, status, reviewer_id, review_comment, reviewed_at, created_at) VALUES
                (90, 55, 8, 10, 'DOCUMENT', '旧版本', NULL, NULL, NULL, NULL,
                 1, 1, 'CHANGES_REQUESTED', 99, '请修改', TIMESTAMP '2026-07-20 10:00:00', TIMESTAMP '2026-07-20 09:00:00'),
                (101, 55, 8, 10, 'DOCUMENT', '最新版本', NULL, NULL, NULL, NULL,
                 1, 2, 'PENDING_REVIEW', NULL, NULL, NULL, TIMESTAMP '2026-07-21 09:00:00'),
                (102, 56, 9, 10, 'DOCUMENT', '其他教师提交', NULL, NULL, NULL, NULL,
                 1, 1, 'PENDING_REVIEW', NULL, NULL, NULL, TIMESTAMP '2026-07-19 09:00:00'),
                (103, 57, 10, 10, 'DOCUMENT', '其他租户提交', NULL, NULL, NULL, NULL,
                 1, 1, 'PENDING_REVIEW', NULL, NULL, NULL, TIMESTAMP '2026-07-18 09:00:00')
                """);
        template.update("""
                INSERT INTO project_task_assignee (task_id, team_id, user_id, sort_order) VALUES
                (55, 8, 10, 0),
                (56, 9, 10, 0),
                (57, 10, 10, 0)
                """);
        template.update("""
                INSERT INTO project_stage
                (id, team_id, stage_key, title, status, progress, owner_user_id, start_date, due_date, is_optional, sort_order) VALUES
                (1, 8, 'MATERIAL', '材料准备', 'IN_PROGRESS', 0, NULL, NULL, NULL, 0, 1),
                (2, 9, 'MATERIAL', '材料准备', 'IN_PROGRESS', 0, NULL, NULL, NULL, 0, 1),
                (3, 10, 'MATERIAL', '材料准备', 'IN_PROGRESS', 0, NULL, NULL, NULL, 0, 1)
                """);
        template.update("""
                INSERT INTO training_camp (id, tenant_id, name, start_date) VALUES
                (5, 7, '暑期营', DATE '2026-07-01'),
                (15, 8, '其他租户旧营', DATE '2026-07-10')
                """);
        template.update("""
                INSERT INTO training_camp_team (camp_id, team_id, status, joined_at) VALUES
                (5, 8, 'ACTIVE', TIMESTAMP '2026-07-01 08:00:00'),
                (15, 8, 'ACTIVE', TIMESTAMP '2026-07-10 08:00:00')
                """);
        template.update("""
                INSERT INTO training_day (id, camp_id, day_no, training_date, title) VALUES
                (6, 5, 3, DATE '2026-07-03', '第三天'),
                (16, 15, 99, DATE '2026-07-20', '其他租户较新训练日')
                """);
        template.update("""
                INSERT INTO training_day_task (training_day_id, task_id) VALUES
                (6, 55),
                (16, 55)
                """);
        template.update("""
                INSERT INTO project_submission_asset
                (id, submission_id, task_id, team_id, asset_kind, file_url, file_name, file_size, file_type, sort_order, created_at)
                VALUES (1, 101, 55, 8, 'MAIN', '/files/result.pdf', 'result.pdf', 128, 'application/pdf', 0, TIMESTAMP '2026-07-21 09:01:00')
                """);
        template.update("""
                INSERT INTO project_submission_link
                (id, submission_id, task_id, team_id, link_type, title, url, sort_order, created_at)
                VALUES (1, 101, 55, 8, 'DEMO', '演示地址', 'https://example.test/result', 0, TIMESTAMP '2026-07-21 09:02:00')
                """);
        template.update("""
                INSERT INTO project_task_requirement
                (id, task_id, title, description, required, asset_type, sort_order)
                VALUES (1, 55, '成果文件', '上传最终成果', 1, 'FILE', 0)
                """);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> mapRows(Object value) {
        return (List<Map<String, Object>>) value;
    }

    private long number(Object value) {
        return ((Number) value).longValue();
    }

    private Map<String, Object> reviewBody(String status) {
        return Map.of("status", status, "reviewComment", "审核意见");
    }

    private String submissionStatus(JdbcTemplate template, Long submissionId) {
        return template.queryForObject(
                "SELECT status FROM project_task_submission WHERE id = ?", String.class, submissionId);
    }

    private String taskStatus(JdbcTemplate template, Long taskId) {
        return template.queryForObject("SELECT status FROM project_task WHERE id = ?", String.class, taskId);
    }

    private List<QueryCall> recordQueriesReturning(List<Map<String, Object>> rows) {
        List<QueryCall> calls = new ArrayList<>();
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            Object[] args = new Object[invocation.getArguments().length - 1];
            System.arraycopy(invocation.getArguments(), 1, args, 0, args.length);
            calls.add(new QueryCall(sql, args));
            return rows;
        });
        return calls;
    }

    private QueryCall callContaining(List<QueryCall> calls, String fragment) {
        return calls.stream()
                .filter(call -> call.sql().contains(fragment))
                .findFirst()
                .orElseThrow(() -> new AssertionError("No SQL call contained: " + fragment));
    }

    private Map<String, Object> mutableMap(Object... entries) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < entries.length; i += 2) {
            result.put(String.valueOf(entries[i]), entries[i + 1]);
        }
        return result;
    }

    private record QueryCall(String sql, Object[] args) {
    }
}
