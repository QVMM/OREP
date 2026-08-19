package com.orep.backend.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ScoreEvidenceAnchorStoreTest {

    private JdbcTemplate jdbc;
    private ScoreEvidenceAnchorStore store;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:score_memory;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("""
            CREATE TABLE project_assessment (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                team_id BIGINT NOT NULL,
                meeting_id BIGINT NOT NULL,
                assessment_round INT NOT NULL,
                assessment_type VARCHAR(32) NOT NULL DEFAULT 'AI_ROADSHOW',
                overall_score DECIMAL(6,2),
                technical_ceiling_score DECIMAL(6,2),
                score_calibration_json CLOB,
                evidence_snapshot_json CLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, meeting_id)
            )
            """);
        jdbc.execute("""
            CREATE TABLE score_memory_item (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                assessment_id BIGINT NOT NULL,
                team_id BIGINT NOT NULL,
                memory_type VARCHAR(32) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description CLOB,
                severity VARCHAR(32),
                status VARCHAR(32),
                source_round INT,
                resolved_round INT,
                recovered_score DECIMAL(6,2),
                metadata_json CLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """);
        jdbc.execute("""
            CREATE TABLE score_evidence_anchor (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                memory_item_id BIGINT NOT NULL,
                assessment_id BIGINT NOT NULL,
                anchor_type VARCHAR(32) NOT NULL,
                evidence_text CLOB NOT NULL,
                source_ref VARCHAR(255),
                confidence DECIMAL(5,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """);
        store = new ScoreEvidenceAnchorStore(jdbc);
    }

    @Test
    void persistsRoundAnchorsOnceAndReusesExistingRows() {
        Map<String, Object> roadshow = Map.of(
                "teamId", 9L,
                "meetingId", 42L,
                "aiReportId", 1001L,
                "aiScore", 82,
                "scoreCalibrationJson", "{\"ceilingScore\":92}"
        );
        List<Map<String, Object>> anchors = List.of(
                Map.of("type", "key_frame", "summary", "屏幕展示登录成功", "sourceRef", "frame-001@00:31.5"),
                Map.of("type", "screen_ocr", "summary", "OCR识别到性能数据缺失", "sourceRef", "fusion.screen_content_summary")
        );

        List<Map<String, Object>> first = store.syncRoundAnchors(9L, roadshow, anchors);
        List<Map<String, Object>> second = store.syncRoundAnchors(9L, roadshow, anchors);

        assertEquals(2, first.size());
        assertEquals(2, second.size());
        assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM project_assessment", Integer.class));
        assertEquals(1, jdbc.queryForObject("SELECT COUNT(*) FROM score_memory_item", Integer.class));
        assertEquals(2, jdbc.queryForObject("SELECT COUNT(*) FROM score_evidence_anchor", Integer.class));
        assertNotNull(second.get(0).get("evidenceAnchorId"));
        assertEquals(42L, second.get(0).get("meetingId"));
        assertEquals(1001L, second.get(0).get("aiReportId"));
    }

    @Test
    void appendsNewAnchorsForExistingAssessmentWithoutDuplicatingOldOnes() {
        Map<String, Object> roadshow = Map.of(
                "teamId", 9L,
                "meetingId", 42L,
                "aiReportId", 1001L,
                "aiScore", 82
        );
        List<Map<String, Object>> firstAnchors = List.of(
                Map.of("type", "key_frame", "summary", "屏幕展示登录成功", "sourceRef", "frame-001@00:31.5")
        );
        List<Map<String, Object>> secondAnchors = List.of(
                Map.of("type", "key_frame", "summary", "屏幕展示登录成功", "sourceRef", "frame-001@00:31.5"),
                Map.of("type", "recording_screen", "summary", "屏幕录制已归档", "sourceRef", "/api/recording/77/stream?file=screen")
        );

        store.syncRoundAnchors(9L, roadshow, firstAnchors);
        List<Map<String, Object>> second = store.syncRoundAnchors(9L, roadshow, secondAnchors);

        assertEquals(2, second.size());
        assertEquals(2, jdbc.queryForObject("SELECT COUNT(*) FROM score_evidence_anchor", Integer.class));
        assertTrue(second.stream().anyMatch(anchor -> "recording_screen".equals(anchor.get("type"))));
    }
}
