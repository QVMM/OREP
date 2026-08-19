package com.orep.backend.service;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CollaborationMigrationContractTest {

    @Test
    void migrationDefinesRequestsTaskOriginAndStableMaterialSource() throws Exception {
        ClassPathResource resource = new ClassPathResource(
                "db/migration/V107__global_collaboration_requests.sql"
        );
        String sql;
        try (var input = resource.getInputStream()) {
            sql = new String(input.readAllBytes(), StandardCharsets.UTF_8)
                    .toLowerCase();
        }

        assertTrue(sql.contains("create table if not exists collaboration_request"));
        assertTrue(sql.contains("idempotency_key varchar(120) not null"));
        assertTrue(sql.contains("unique key uk_collaboration_request_idempotency"));
        assertTrue(sql.contains("unique key uk_collaboration_request_task"));
        assertTrue(sql.contains("idx_collaboration_recipient_status_time"));
        assertTrue(sql.contains("idx_collaboration_requester_status_time"));

        assertTrue(sql.contains("source_type varchar(40) not null default 'other'"));
        assertTrue(sql.contains("reviewer_user_id bigint default null"));
        assertTrue(sql.contains("idx_project_task_reviewer"));

        assertTrue(sql.contains("source_submission_id bigint default null"));
        assertTrue(sql.contains("source_item_key varchar(190) default null"));
        assertTrue(sql.contains("unique key uk_project_material_source_item"));
    }

    @Test
    void v107MigrationNumberIsUnique() throws Exception {
        var resources = new org.springframework.core.io.support.PathMatchingResourcePatternResolver()
                .getResources("classpath*:db/migration/V107__*.sql");
        assertEquals(1, resources.length);
    }
}
