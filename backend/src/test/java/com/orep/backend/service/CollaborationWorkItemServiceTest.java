package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CollaborationWorkItemServiceTest {
    private JdbcTemplate jdbc;
    private CollaborationWorkItemService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:collaboration_work_items_" + UUID.randomUUID()
                        + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        createSchema();
        insertFixtures();
        service = new CollaborationWorkItemService(
                jdbc,
                new TrainingDayAvailabilityService()
        );
    }

    @Test
    void studentSeesUnifiedSourcesWithoutLockedOrForeignTasks() {
        List<Map<String, Object>> items = items(
                service.items(7L, 21L, "STUDENT", "ALL", null, null, 50)
        );
        Set<String> keys = keys(items);

        assertTrue(keys.containsAll(Set.of(
                "TASK:101", "TASK:102", "TASK:103", "TASK:106", "TASK:107", "REQUEST:202"
        )));
        assertFalse(keys.contains("TASK:104"));
        assertFalse(keys.contains("TASK:105"));
        assertFalse(keys.contains("REQUEST:201"));

        assertEquals("TRAINING_DAY", item(items, "TASK:101").get("sourceType"));
        assertEquals("TEACHER_ASSIGNMENT", item(items, "TASK:102").get("sourceType"));
        assertEquals("TEAM_TASK", item(items, "TASK:103").get("sourceType"));
        assertEquals("PEER_COLLABORATION", item(items, "TASK:106").get("sourceType"));
        assertEquals("/training/tasks/101?dayId=301", item(items, "TASK:101").get("targetPath"));
    }

    @Test
    void acceptedRequestIsReplacedByItsFormalTask() {
        List<Map<String, Object>> items = items(
                service.items(7L, 21L, "STUDENT", "ALL", null, null, 50)
        );

        assertTrue(keys(items).contains("TASK:106"));
        assertFalse(keys(items).contains("REQUEST:201"));
        assertEquals(1, items.stream()
                .filter(row -> "补充路演视觉稿".equals(row.get("title")))
                .count());
    }

    @Test
    void actionSummaryAndListUseTheSameProjection() {
        Map<String, Object> summary = service.summary(7L, 21L, "STUDENT");
        List<Map<String, Object>> actionItems = items(
                service.items(7L, 21L, "STUDENT", "ACTION_REQUIRED", null, null, 50)
        );

        assertEquals(actionItems.size(), ((Number) summary.get("actionRequired")).intValue());
        assertTrue(keys(actionItems).containsAll(Set.of(
                "TASK:101", "TASK:102", "TASK:103", "TASK:106", "REQUEST:202"
        )));
        assertFalse(keys(actionItems).contains("TASK:107"));
    }

    @Test
    void teacherGetsPendingReviewWithReviewAction() {
        List<Map<String, Object>> actionItems = items(
                service.items(7L, 99L, "TEACHER", "ACTION_REQUIRED", 8L, null, 50)
        );
        Map<String, Object> review = item(actionItems, "TASK:107");

        assertEquals("REVIEW", review.get("primaryAction"));
        assertEquals("待审核", review.get("statusLabel"));
        assertEquals(501L, ((Number) review.get("latestSubmissionId")).longValue());
    }

    @Test
    void teamFilterCannotExpandStudentScope() {
        List<Map<String, Object>> items = items(
                service.items(7L, 21L, "STUDENT", "ALL", 9L, null, 50)
        );
        assertTrue(items.isEmpty());
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> items(Map<String, Object> response) {
        return (List<Map<String, Object>>) response.get("items");
    }

    private Set<String> keys(List<Map<String, Object>> items) {
        return items.stream()
                .map(row -> String.valueOf(row.get("key")))
                .collect(Collectors.toSet());
    }

    private Map<String, Object> item(List<Map<String, Object>> items, String key) {
        return items.stream()
                .filter(row -> key.equals(row.get("key")))
                .findFirst()
                .orElseThrow();
    }

    private void createSchema() {
        jdbc.execute("CREATE TABLE users(id BIGINT PRIMARY KEY,username VARCHAR(120) NOT NULL)");
        jdbc.execute("""
            CREATE TABLE project_team(
              id BIGINT PRIMARY KEY,tenant_id BIGINT NOT NULL,name VARCHAR(120) NOT NULL,
              status VARCHAR(32) NOT NULL,mentor_id BIGINT
            )
            """);
        jdbc.execute("""
            CREATE TABLE project_team_member(
              id BIGINT AUTO_INCREMENT PRIMARY KEY,team_id BIGINT NOT NULL,user_id BIGINT NOT NULL,
              role_in_team VARCHAR(32) NOT NULL
            )
            """);
        jdbc.execute("""
            CREATE TABLE project_task(
              id BIGINT PRIMARY KEY,team_id BIGINT NOT NULL,title VARCHAR(160) NOT NULL,
              description VARCHAR(1000),owner_user_id BIGINT,created_by BIGINT NOT NULL,
              source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER',reviewer_user_id BIGINT,
              priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',status VARCHAR(32) NOT NULL,
              due_at TIMESTAMP,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """);
        jdbc.execute("""
            CREATE TABLE project_task_assignee(
              id BIGINT AUTO_INCREMENT PRIMARY KEY,task_id BIGINT NOT NULL,team_id BIGINT NOT NULL,
              user_id BIGINT NOT NULL,sort_order INT NOT NULL DEFAULT 0
            )
            """);
        jdbc.execute("""
            CREATE TABLE project_task_submission(
              id BIGINT PRIMARY KEY,task_id BIGINT NOT NULL,submitter_id BIGINT NOT NULL,
              version_no INT NOT NULL,status VARCHAR(32) NOT NULL
            )
            """);
        jdbc.execute("""
            CREATE TABLE training_day(
              id BIGINT PRIMARY KEY,day_no INT NOT NULL,training_date DATE NOT NULL,
              status VARCHAR(32) NOT NULL,early_unlocked_at TIMESTAMP
            )
            """);
        jdbc.execute("""
            CREATE TABLE training_day_task(
              id BIGINT AUTO_INCREMENT PRIMARY KEY,training_day_id BIGINT NOT NULL,task_id BIGINT NOT NULL
            )
            """);
        jdbc.execute("""
            CREATE TABLE collaboration_request(
              id BIGINT PRIMARY KEY,tenant_id BIGINT NOT NULL,team_id BIGINT NOT NULL,
              requester_id BIGINT NOT NULL,recipient_id BIGINT NOT NULL,title VARCHAR(160) NOT NULL,
              description VARCHAR(1000),priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
              status VARCHAR(32) NOT NULL,due_at TIMESTAMP,linked_task_id BIGINT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """);
    }

    private void insertFixtures() {
        jdbc.update("""
            INSERT INTO users(id,username) VALUES
              (21,'李同学'),(22,'王同学'),(31,'其他团队成员'),(99,'张老师')
            """);
        jdbc.update("""
            INSERT INTO project_team(id,tenant_id,name,status,mentor_id) VALUES
              (8,7,'应用攻坚队','ACTIVE',99),(9,7,'其他团队','ACTIVE',99)
            """);
        jdbc.update("""
            INSERT INTO project_team_member(team_id,user_id,role_in_team) VALUES
              (8,21,'MEMBER'),(8,22,'MEMBER'),(8,99,'MENTOR'),(9,31,'MEMBER')
            """);
        jdbc.update("""
            INSERT INTO project_task(
              id,team_id,title,description,owner_user_id,created_by,source_type,
              reviewer_user_id,priority,status,due_at
            ) VALUES
              (101,8,'完整路演第一次彩排','完成今日训练',21,99,'OTHER',99,'HIGH','TODO','2026-07-30 22:00:00'),
              (102,8,'补齐市场数据与来源','老师发布任务',21,99,'TEACHER_ASSIGNMENT',99,'HIGH','TODO','2026-08-03 20:00:00'),
              (103,8,'完善团队项目简介','团队任务',21,21,'OTHER',NULL,'MEDIUM','IN_PROGRESS','2026-08-04 20:00:00'),
              (104,9,'其他团队任务','不可见',31,31,'OTHER',NULL,'MEDIUM','TODO',NULL),
              (105,8,'未来训练任务','未解锁',21,99,'OTHER',99,'MEDIUM','TODO',NULL),
              (106,8,'补充路演视觉稿','同学协作',21,22,'PEER_COLLABORATION',22,'HIGH','TODO','2026-08-02 20:00:00'),
              (107,8,'完善产品论证','等待教师审核',21,99,'TEACHER_ASSIGNMENT',99,'HIGH','REVIEWING','2026-08-05 20:00:00')
            """);
        jdbc.update("""
            INSERT INTO project_task_assignee(task_id,team_id,user_id,sort_order) VALUES
              (101,8,21,0),(102,8,21,0),(103,8,21,0),
              (104,9,31,0),(105,8,21,0),(106,8,21,0),(107,8,21,0)
            """);
        jdbc.update("""
            INSERT INTO project_task_submission(id,task_id,submitter_id,version_no,status)
            VALUES (501,107,21,1,'PENDING_REVIEW')
            """);
        jdbc.update("""
            INSERT INTO training_day(id,day_no,training_date,status,early_unlocked_at) VALUES
              (301,8,'2026-07-30','PUBLISHED','2020-01-01 00:00:00'),
              (302,99,'2099-01-01','PUBLISHED',NULL)
            """);
        jdbc.update("""
            INSERT INTO training_day_task(training_day_id,task_id) VALUES (301,101),(302,105)
            """);
        jdbc.update("""
            INSERT INTO collaboration_request(
              id,tenant_id,team_id,requester_id,recipient_id,title,status,linked_task_id
            ) VALUES
              (201,7,8,22,21,'补充路演视觉稿','ACCEPTED',106),
              (202,7,8,22,21,'核对答辩数据','PENDING',NULL),
              (203,7,9,31,31,'其他团队申请','PENDING',NULL)
            """);
    }
}
