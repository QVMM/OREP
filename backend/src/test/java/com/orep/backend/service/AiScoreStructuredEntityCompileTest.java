package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AiScoreStructuredEntityCompileTest {
    @Test
    void structuredEntitiesExposeExpectedFields() {
        AiScoreObservation observation = new AiScoreObservation();
        observation.setSessionId(101L);
        observation.setObservationCode("tech_demo_stability");
        observation.setScoreCap(new BigDecimal("85.00"));
        observation.setEvidenceAnchorIdsJson("[1,2]");

        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setSessionId(101L);
        deduction.setDeductionId("TECH_DEMO_FAILURE_001");
        deduction.setDeductedPoints(new BigDecimal("6.00"));
        deduction.setMaxRecoverablePoints(new BigDecimal("6.00"));

        AiScoreReport report = new AiScoreReport();
        report.setRuleEngineVersion("rule-engine-v1");
        report.setCurrentScoreCap(new BigDecimal("85.00"));
        report.setRecoveredScore(new BigDecimal("0.00"));
        report.setStructuredResultJson("{\"version\":\"rule-engine-v1\"}");

        assertEquals(101L, observation.getSessionId());
        assertEquals("tech_demo_stability", observation.getObservationCode());
        assertEquals(new BigDecimal("85.00"), observation.getScoreCap());
        assertEquals("[1,2]", observation.getEvidenceAnchorIdsJson());
        assertEquals(101L, deduction.getSessionId());
        assertEquals("TECH_DEMO_FAILURE_001", deduction.getDeductionId());
        assertEquals(new BigDecimal("6.00"), deduction.getDeductedPoints());
        assertEquals(new BigDecimal("6.00"), deduction.getMaxRecoverablePoints());
        assertEquals("rule-engine-v1", report.getRuleEngineVersion());
        assertEquals(new BigDecimal("85.00"), report.getCurrentScoreCap());
        assertEquals(new BigDecimal("0.00"), report.getRecoveredScore());
        assertEquals("{\"version\":\"rule-engine-v1\"}", report.getStructuredResultJson());
    }

    @Test
    void p8SqlAssetsStayMirroredAcrossDeployTargets() throws IOException {
        assertMirrored(
            "src/main/resources/sql/create_ai_score_report_table.sql",
            "../dockerrun/sql/backend-resources/create_ai_score_report_table.sql",
            "../deploy/sql/backend-resources/create_ai_score_report_table.sql"
        );
        assertMirrored(
            "src/main/resources/sql/create_ai_scoring_session_tables.sql",
            "../dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql",
            "../deploy/sql/backend-resources/create_ai_scoring_session_tables.sql"
        );
        assertMirrored(
            "src/main/resources/sql/upgrade_ai_scoring_session_p7_schema.sql",
            "../dockerrun/sql/backend-resources/upgrade_ai_scoring_session_p7_schema.sql",
            "../deploy/sql/backend-resources/upgrade_ai_scoring_session_p7_schema.sql"
        );
        assertMirrored(
            "src/main/resources/sql/upgrade_ai_scoring_p8_rule_engine.sql",
            "../dockerrun/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql",
            "../deploy/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql"
        );
        assertMirrored(
            "src/main/resources/sql/alter_ai_score_report_add_score_calibration.sql",
            "../dockerrun/sql/backend-resources/alter_ai_score_report_add_score_calibration.sql",
            "../deploy/sql/backend-resources/alter_ai_score_report_add_score_calibration.sql"
        );
        assertMirrored(
            "src/main/resources/sql/migrate_ai_score_report_transparent_remediation_v3.sql",
            "../dockerrun/sql/backend-resources/migrate_ai_score_report_transparent_remediation_v3.sql",
            "../deploy/sql/backend-resources/migrate_ai_score_report_transparent_remediation_v3.sql"
        );
        assertMirrored(
            "src/main/resources/sql/upgrade_ai_score_speaker_attribution_v1.sql",
            "../dockerrun/sql/backend-resources/upgrade_ai_score_speaker_attribution_v1.sql",
            "../deploy/sql/backend-resources/upgrade_ai_score_speaker_attribution_v1.sql"
        );
    }

    @Test
    void deployComposeFilesMountP8ScoringSql() throws IOException {
        assertComposeMounts("../dockerrun/docker-compose.offline.yml");
        assertComposeMounts("../deploy/docker-compose.yml");
        assertComposeMounts("../deploy/docker-compose.prod.yml");
        assertComposeMounts("../deploy/docker-compose.release.yml");
    }

    private static void assertMirrored(String canonical, String... mirrors) throws IOException {
        String canonicalSql = Files.readString(Path.of(canonical));
        for (String mirror : mirrors) {
            assertEquals(canonicalSql, Files.readString(Path.of(mirror)), mirror + " drifted from " + canonical);
        }
    }

    private static void assertComposeMounts(String composePath) throws IOException {
        String compose = Files.readString(Path.of(composePath));
        assertTrue(compose.contains("create_ai_score_report_table.sql"), composePath);
        assertTrue(compose.contains("create_ai_scoring_session_tables.sql"), composePath);
        assertTrue(compose.contains("upgrade_ai_scoring_session_p7_schema.sql"), composePath);
        assertTrue(compose.contains("upgrade_ai_scoring_p8_rule_engine.sql"), composePath);
        assertTrue(compose.contains("migrate_ai_score_report_transparent_remediation_v3.sql"), composePath);
        assertTrue(compose.contains("upgrade_ai_score_speaker_attribution_v1.sql"), composePath);
    }
}
