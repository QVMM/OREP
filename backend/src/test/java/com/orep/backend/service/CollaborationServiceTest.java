package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.web.server.ResponseStatusException;

import java.util.Map;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CollaborationServiceTest {
    private JdbcTemplate jdbc;
    private ProjectTeamService projectTeamService;
    private ApplicationEventPublisher eventPublisher;
    private CollaborationService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:collaboration_" + UUID.randomUUID()
                        + ";MODE=MySQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        createSchema();
        insertFixtures();
        projectTeamService = mock(ProjectTeamService.class);
        eventPublisher = mock(ApplicationEventPublisher.class);
        service = new CollaborationService(jdbc, projectTeamService, eventPublisher);
    }

    @Test
    void requestMustStayInsideOneActiveTeamAndCannotTargetSelf() {
        ResponseStatusException self = assertThrows(ResponseStatusException.class, () ->
                service.createRequest(7L, 21L, "STUDENT", "self", Map.of(
                        "teamId", 8L,
                        "recipientUserId", 21L,
                        "title", "自己处理"
                )));
        ResponseStatusException outsideTeam = assertThrows(ResponseStatusException.class, () ->
                service.createRequest(7L, 21L, "STUDENT", "outside", Map.of(
                        "teamId", 8L,
                        "recipientUserId", 31L,
                        "title", "跨团队任务"
                )));

        assertEquals(HttpStatus.BAD_REQUEST, self.getStatusCode());
        assertEquals(HttpStatus.FORBIDDEN, outsideTeam.getStatusCode());
    }

    @Test
    void duplicateIdempotencyKeyReturnsTheOriginalRequest() {
        Map<String, Object> body = Map.of(
                "teamId", 8L,
                "recipientUserId", 22L,
                "title", "完善路演稿",
                "priority", "HIGH"
        );

        Map<String, Object> first = service.createRequest(7L, 21L, "STUDENT", "same-key", body);
        Map<String, Object> second = service.createRequest(7L, 21L, "STUDENT", "same-key", body);

        assertEquals(number(first.get("id")), number(second.get("id")));
        assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM collaboration_request", Integer.class));
        verify(eventPublisher).publishEvent(any(CollaborationEvent.class));
    }

    @Test
    void batchCreatesIndependentRequestsAndDeduplicatesRecipientsInSelectionOrder() {
        Map<String, Object> result = service.createRequests(7L, 21L, "STUDENT", "batch-key", Map.of(
                "teamId", 8L,
                "recipientUserIds", List.of(23L, 22L, 23L),
                "title", "联合完善路演材料",
                "description", "请分别提交负责部分",
                "priority", "HIGH"
        ));

        List<?> items = (List<?>) result.get("items");
        assertEquals(2, result.get("count"));
        assertEquals(23L, number(((Map<?, ?>) items.get(0)).get("recipientId")));
        assertEquals(22L, number(((Map<?, ?>) items.get(1)).get("recipientId")));
        assertEquals(2, jdbc.queryForObject(
                "SELECT COUNT(*) FROM collaboration_request",
                Integer.class
        ));
        verify(eventPublisher, times(2)).publishEvent(any(CollaborationEvent.class));
    }

    @Test
    void batchRetryReturnsOriginalRequestsWithoutDuplicates() {
        Map<String, Object> body = Map.of(
                "teamId", 8L,
                "recipientUserIds", List.of(22L, 23L),
                "title", "联合完善路演材料",
                "priority", "MEDIUM"
        );

        Map<String, Object> first = service.createRequests(
                7L, 21L, "STUDENT", "same-batch-key", body
        );
        Map<String, Object> second = service.createRequests(
                7L, 21L, "STUDENT", "same-batch-key", body
        );

        assertEquals(
                ((Map<?, ?>) ((List<?>) first.get("items")).get(0)).get("id"),
                ((Map<?, ?>) ((List<?>) second.get("items")).get(0)).get("id")
        );
        assertEquals(2, jdbc.queryForObject(
                "SELECT COUNT(*) FROM collaboration_request",
                Integer.class
        ));
        verify(eventPublisher, times(2)).publishEvent(any(CollaborationEvent.class));
    }

    @Test
    void batchRejectsEveryRequestBeforeInsertWhenOneRecipientIsInvalid() {
        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.createRequests(7L, 21L, "STUDENT", "invalid-batch", Map.of(
                        "teamId", 8L,
                        "recipientUserIds", List.of(22L, 31L),
                        "title", "联合完善路演材料"
                )));

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
        assertEquals(0, jdbc.queryForObject(
                "SELECT COUNT(*) FROM collaboration_request",
                Integer.class
        ));
    }

    @Test
    void batchIdempotencyKeyCannotBeReusedForDifferentContent() {
        service.createRequests(7L, 21L, "STUDENT", "changed-batch", Map.of(
                "teamId", 8L,
                "recipientUserIds", List.of(22L, 23L),
                "title", "第一版任务"
        ));

        ResponseStatusException error = assertThrows(ResponseStatusException.class, () ->
                service.createRequests(7L, 21L, "STUDENT", "changed-batch", Map.of(
                        "teamId", 8L,
                        "recipientUserIds", List.of(22L, 23L),
                        "title", "修改后的任务"
                )));

        assertEquals(HttpStatus.CONFLICT, error.getStatusCode());
        assertEquals(2, jdbc.queryForObject(
                "SELECT COUNT(*) FROM collaboration_request",
                Integer.class
        ));
    }

    @Test
    void onlyRecipientCanAcceptAndAcceptanceLinksOneFormalTask() {
        Map<String, Object> created = service.createRequest(7L, 21L, "STUDENT", "accept-key", Map.of(
                "teamId", 8L,
                "recipientUserId", 22L,
                "title", "完善路演稿"
        ));
        long requestId = number(created.get("id"));
        when(projectTeamService.createAcceptedCollaborationTask(
                8L, 21L, 22L, "完善路演稿", null, "MEDIUM", null
        )).thenReturn(Map.of("id", 55L));

        ResponseStatusException unauthorized = assertThrows(ResponseStatusException.class, () ->
                service.accept(requestId, 7L, 21L, "STUDENT"));
        Map<String, Object> accepted = service.accept(requestId, 7L, 22L, "STUDENT");
        Map<String, Object> acceptedAgain = service.accept(requestId, 7L, 22L, "STUDENT");

        assertEquals(HttpStatus.FORBIDDEN, unauthorized.getStatusCode());
        assertEquals("ACCEPTED", accepted.get("status"));
        assertEquals(55L, number(accepted.get("linkedTaskId")));
        assertEquals(55L, number(acceptedAgain.get("linkedTaskId")));
        assertTrue((Boolean) accepted.get("recipientIsCurrentUser"));
        verify(projectTeamService).createAcceptedCollaborationTask(
                8L, 21L, 22L, "完善路演稿", null, "MEDIUM", null
        );
    }

    @Test
    void summaryCountsPendingRecipientWork() {
        service.createRequest(7L, 21L, "STUDENT", "summary-key", Map.of(
                "teamId", 8L,
                "recipientUserId", 22L,
                "title", "整理答辩数据"
        ));

        Map<String, Object> summary = service.summary(7L, 22L, "STUDENT");
        Map<String, Object> items = service.items(
                7L, 22L, "STUDENT", "ACTION_REQUIRED", null, null, 30
        );

        assertEquals(1, summary.get("actionRequired"));
        assertEquals(1, ((java.util.List<?>) items.get("items")).size());
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
              id BIGINT PRIMARY KEY,status VARCHAR(32),reviewer_user_id BIGINT
            )
            """);
        jdbc.execute("""
            CREATE TABLE project_task_submission(
              id BIGINT PRIMARY KEY,task_id BIGINT,version_no INT,status VARCHAR(32)
            )
            """);
        jdbc.execute("""
            CREATE TABLE collaboration_request(
              id BIGINT AUTO_INCREMENT PRIMARY KEY,tenant_id BIGINT NOT NULL,team_id BIGINT NOT NULL,
              requester_id BIGINT NOT NULL,recipient_id BIGINT NOT NULL,title VARCHAR(160) NOT NULL,
              description VARCHAR(1000),priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
              status VARCHAR(32) NOT NULL DEFAULT 'PENDING',due_at TIMESTAMP,response_reason VARCHAR(500),
              linked_task_id BIGINT,idempotency_key VARCHAR(120) NOT NULL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              responded_at TIMESTAMP,withdrawn_at TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              CONSTRAINT uk_collaboration_request_idempotency UNIQUE(tenant_id,requester_id,idempotency_key),
              CONSTRAINT uk_collaboration_request_task UNIQUE(linked_task_id)
            )
            """);
    }

    private void insertFixtures() {
        jdbc.update("INSERT INTO users(id,username) VALUES (21,'发起人'),(22,'接收人'),(23,'协作者'),(31,'其他团队')");
        jdbc.update("INSERT INTO project_team(id,tenant_id,name,status,mentor_id) VALUES (8,7,'应用攻坚队','ACTIVE',99),(9,7,'其他队','ACTIVE',99)");
        jdbc.update("INSERT INTO project_team_member(team_id,user_id,role_in_team) VALUES (8,21,'MEMBER'),(8,22,'MEMBER'),(8,23,'MEMBER'),(9,31,'MEMBER')");
    }

    private long number(Object value) {
        return ((Number) value).longValue();
    }
}
