package com.orep.backend.service.roadshow.projection;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class RsProjectionMigrationContractTest {

    @Test
    void eightTablesNoExpressionTable() throws Exception {
        String sql = readV126();
        assertTrue(sql.contains("create table if not exists rs_evidence"));
        assertTrue(sql.contains("create table if not exists rs_claim"));
        assertTrue(sql.contains("create table if not exists rs_claim_evidence"));
        assertTrue(sql.contains("create table if not exists rs_claim_relation"));
        assertTrue(sql.contains("create table if not exists rs_assessment"));
        assertTrue(sql.contains("create table if not exists rs_page_intent"));
        assertTrue(sql.contains("create table if not exists rs_projection_run"));
        assertTrue(sql.contains("create table if not exists rs_projection_page"));
        assertFalse(sql.contains("create table if not exists rs_expression"));
        assertFalse(sql.contains("create table if not exists rs_observation"));
        assertFalse(sql.contains("create table if not exists rs_evaluation"));
    }

    @Test
    void assessmentLifecycleIsStructuredNotASentence() throws Exception {
        String sql = readV126();
        assertTrue(sql.contains("created_by_run_id"));
        assertTrue(sql.contains("created_by_page_intent_id"));
        assertTrue(sql.contains("created_for_rubric_id"));
        assertFalse(sql.contains("created_reason"));
    }

    @Test
    void projectionPageMaterializesExpression() throws Exception {
        String sql = readV126();
        assertTrue(sql.contains("expression_slide_text"));
        assertTrue(sql.contains("expression_speaking"));
        assertTrue(sql.contains("expression_task_focus"));
        assertTrue(sql.contains("decision_compact_json"));
    }

    @Test
    void v126NumberIsUnique() throws Exception {
        var resources = new org.springframework.core.io.support.PathMatchingResourcePatternResolver()
                .getResources("classpath*:db/migration/V126__*.sql");
        assertEquals(1, resources.length);
    }

    private static String readV126() throws Exception {
        try (var in = new ClassPathResource("db/migration/V126__rs_projection_mvp.sql").getInputStream()) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8).toLowerCase();
        }
    }
}
