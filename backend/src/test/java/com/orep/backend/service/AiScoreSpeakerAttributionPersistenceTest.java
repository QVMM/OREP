package com.orep.backend.service;

import com.orep.backend.dto.PipelineCallbackRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class AiScoreSpeakerAttributionPersistenceTest {
    private JdbcTemplate jdbc;
    private AiScoreSpeakerAttributionPersistenceService service;

    @BeforeEach
    void setUp() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:speaker_attribution_" + System.nanoTime()
                        + ";MODE=MySQL;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        );
        jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                  id BIGINT PRIMARY KEY,
                  speaker_attribution_revision INT NULL,
                  speaker_attribution_status VARCHAR(24) NULL,
                  speaker_attribution_contract_version VARCHAR(64) NULL,
                  speaker_attribution_clock_id VARCHAR(160) NULL,
                  speaker_attribution_snapshot_hash VARCHAR(80) NULL
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_speaker_identity (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  session_id BIGINT NOT NULL,
                  raw_speaker_label VARCHAR(128) NULL,
                  person_id VARCHAR(160) NULL,
                  person_type VARCHAR(24) NULL,
                  contestant_slot INT NULL,
                  display_name VARCHAR(120) NULL,
                  role_name VARCHAR(120) NULL,
                  status VARCHAR(24) NOT NULL DEFAULT 'AUTO',
                  source VARCHAR(24) NOT NULL DEFAULT 'MODEL',
                  confidence DECIMAL(7,6) NULL,
                  revision INT NOT NULL DEFAULT 1,
                  person_state VARCHAR(24) NULL,
                  first_seen_ms BIGINT NULL,
                  last_seen_ms BIGINT NULL,
                  voice_cluster_ids_json CLOB NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  CONSTRAINT uk_person UNIQUE(session_id, person_id),
                  CONSTRAINT uk_raw_speaker UNIQUE(session_id, raw_speaker_label)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_speaker_turn (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  session_id BIGINT NOT NULL,
                  turn_uid VARCHAR(160) NOT NULL,
                  attribution_revision INT NOT NULL,
                  start_ms BIGINT NOT NULL,
                  end_ms BIGINT NOT NULL,
                  person_id VARCHAR(160) NULL,
                  speaker_state VARCHAR(32) NOT NULL,
                  confidence DECIMAL(7,6) NULL,
                  candidate_person_ids_json CLOB NULL,
                  source_cluster_id VARCHAR(160) NULL,
                  source_visual_identity_id VARCHAR(160) NULL,
                  speaker_verification VARCHAR(40) NULL,
                  CONSTRAINT uk_turn UNIQUE(session_id, turn_uid)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_score_transcript_segment (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  session_id BIGINT NOT NULL,
                  segment_no INT NOT NULL,
                  segment_uid VARCHAR(160) NULL,
                  attribution_revision INT NULL,
                  speaker_label VARCHAR(128) NULL,
                  person_id VARCHAR(160) NULL,
                  speaker_state VARCHAR(32) NULL,
                  speaker_confidence DECIMAL(7,6) NULL,
                  is_final BOOLEAN NULL,
                  start_ms BIGINT NOT NULL,
                  end_ms BIGINT NOT NULL,
                  text CLOB NOT NULL,
                  source_type VARCHAR(32) NOT NULL,
                  confidence DECIMAL(7,6) NULL,
                  segment_hash VARCHAR(128) NOT NULL,
                  CONSTRAINT uk_segment_uid UNIQUE(session_id, segment_uid)
                )
                """);
        jdbc.update("INSERT INTO ai_scoring_session(id) VALUES (?)", 26L);
        service = new AiScoreSpeakerAttributionPersistenceService(jdbc);
    }

    @Test
    void replacesCompleteSnapshotAndSupportsUnlimitedVisitorsAndOffscreenPeople() {
        PipelineCallbackRequest.SpeakerAttributionInput provisional = snapshot(1, "PROVISIONAL", 1);
        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.APPLIED,
                service.persist(26L, provisional)
        );

        PipelineCallbackRequest.SpeakerAttributionInput terminal = snapshot(2, "FINAL", 7);
        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.APPLIED,
                service.persist(26L, terminal)
        );

        assertEquals(7, count("ai_score_speaker_identity"));
        assertEquals(2, count("ai_score_speaker_turn"));
        assertEquals(2, count("ai_score_transcript_segment"));
        assertEquals(2, jdbc.queryForObject(
                "SELECT speaker_attribution_revision FROM ai_scoring_session WHERE id=26",
                Integer.class
        ));
        assertEquals("FINAL", jdbc.queryForObject(
                "SELECT speaker_attribution_status FROM ai_scoring_session WHERE id=26",
                String.class
        ));
    }

    @Test
    void sameRevisionIsIdempotentAndOlderRevisionIsIgnored() {
        PipelineCallbackRequest.SpeakerAttributionInput terminal = snapshot(3, "FINAL", 4);
        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.APPLIED,
                service.persist(26L, terminal)
        );
        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.IDEMPOTENT,
                service.persist(26L, terminal)
        );
        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.STALE_IGNORED,
                service.persist(26L, snapshot(2, "FINAL", 1))
        );
        assertEquals(4, count("ai_score_speaker_identity"));
    }

    @Test
    void finalSnapshotRejectsEvenANewerProvisionalOverwrite() {
        service.persist(26L, snapshot(2, "FINAL", 4));

        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.FINAL_PROTECTED,
                service.persist(26L, snapshot(9, "PROVISIONAL", 1))
        );
        assertEquals(4, count("ai_score_speaker_identity"));
        assertEquals(2, jdbc.queryForObject(
                "SELECT speaker_attribution_revision FROM ai_scoring_session WHERE id=26",
                Integer.class
        ));
    }

    @Test
    void invalidPersonReferenceRollsBackWithoutDeletingThePreviousSnapshot() {
        service.persist(26L, snapshot(1, "PROVISIONAL", 4));
        PipelineCallbackRequest.SpeakerAttributionInput invalid = snapshot(2, "FINAL", 2);
        invalid.getTurns().get(0).setPersonId("MISSING_PERSON");

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.persist(26L, invalid)
        );

        assertTrue(error.getMessage().contains("unknown person reference"));
        assertEquals(4, count("ai_score_speaker_identity"));
        assertEquals(1, jdbc.queryForObject(
                "SELECT speaker_attribution_revision FROM ai_scoring_session WHERE id=26",
                Integer.class
        ));
    }

    @Test
    void unknownAndOffscreenTranscriptStatesPersistWithoutInventingAPerson() {
        service.persist(26L, snapshot(1, "FINAL", 4));

        Map<String, Object> row = jdbc.queryForMap("""
                SELECT person_id, speaker_state, speaker_label
                FROM ai_score_transcript_segment
                WHERE segment_uid='SEG_UNKNOWN'
                """);
        assertNull(row.get("PERSON_ID"));
        assertEquals("UNKNOWN", row.get("SPEAKER_STATE"));
        assertEquals("SPEAKER_EXTERNAL", row.get("SPEAKER_LABEL"));
    }

    @Test
    void finalSnapshotReusesHumanCorrectedClusterWithoutOverwritingHumanLabels() {
        jdbc.update(
                """
                INSERT INTO ai_score_speaker_identity(
                  session_id, raw_speaker_label, display_name, role_name,
                  status, source, confidence, revision
                ) VALUES (26, 'SPEAKER_1', '张三', '算法工程师', 'CONFIRMED', 'USER', 1.0, 3)
                """
        );

        assertEquals(
                AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome.APPLIED,
                service.persist(26L, snapshot(4, "FINAL", 4))
        );

        Map<String, Object> identity = jdbc.queryForMap("""
                SELECT person_id, person_type, contestant_slot, display_name,
                       role_name, status, source, person_state
                FROM ai_score_speaker_identity
                WHERE session_id=26 AND raw_speaker_label='SPEAKER_1'
                """);
        assertEquals("PERSON_1", identity.get("PERSON_ID"));
        assertEquals("CONTESTANT", identity.get("PERSON_TYPE"));
        assertEquals(1, ((Number) identity.get("CONTESTANT_SLOT")).intValue());
        assertEquals("张三", identity.get("DISPLAY_NAME"));
        assertEquals("算法工程师", identity.get("ROLE_NAME"));
        assertEquals("CONFIRMED", identity.get("STATUS"));
        assertEquals("USER", identity.get("SOURCE"));
        assertEquals("STABLE", identity.get("PERSON_STATE"));
        assertEquals(4, count("ai_score_speaker_identity"));
    }

    private int count(String table) {
        return jdbc.queryForObject("SELECT COUNT(*) FROM " + table + " WHERE session_id=26", Integer.class);
    }

    private PipelineCallbackRequest.SpeakerAttributionInput snapshot(
            int revision,
            String status,
            int peopleCount
    ) {
        PipelineCallbackRequest.SpeakerAttributionInput input = new PipelineCallbackRequest.SpeakerAttributionInput();
        input.setContractVersion("speaker-attribution-v1");
        input.setRevision(revision);
        input.setStatus(status);
        input.setClock(Map.of(
                "clockId", "clock-26",
                "timebase", "MILLISECONDS",
                "masterSource", "MEDIA_PTS"
        ));

        List<PipelineCallbackRequest.AttributionPersonInput> people = new ArrayList<>();
        for (int index = 1; index <= peopleCount; index++) {
            PipelineCallbackRequest.AttributionPersonInput person = new PipelineCallbackRequest.AttributionPersonInput();
            person.setPersonId("PERSON_" + index);
            person.setPersonType(index <= 4 ? "CONTESTANT" : index % 2 == 0 ? "VISITOR" : "OFFSCREEN");
            person.setContestantSlot(index <= 4 ? index : null);
            person.setState("STABLE");
            person.setConfidence(new BigDecimal("0.900000"));
            person.setFirstSeenMs(0L);
            person.setLastSeenMs(3000L);
            person.setVoiceClusterIds(List.of("SPEAKER_" + index));
            people.add(person);
        }
        input.setPeople(people);

        PipelineCallbackRequest.AttributionTurnInput confirmed = new PipelineCallbackRequest.AttributionTurnInput();
        confirmed.setTurnId("TURN_CONFIRMED");
        confirmed.setStartMs(0L);
        confirmed.setEndMs(1500L);
        confirmed.setPersonId("PERSON_1");
        confirmed.setSpeakerState("CONFIRMED");
        confirmed.setConfidence(new BigDecimal("0.900000"));
        confirmed.setCandidatePersonIds(List.of());

        PipelineCallbackRequest.AttributionTurnInput unknown = new PipelineCallbackRequest.AttributionTurnInput();
        unknown.setTurnId("TURN_UNKNOWN");
        unknown.setStartMs(1500L);
        unknown.setEndMs(3000L);
        unknown.setPersonId(null);
        unknown.setSpeakerState("UNKNOWN");
        unknown.setConfidence(BigDecimal.ZERO);
        unknown.setCandidatePersonIds(List.of());
        unknown.setSourceClusterId("SPEAKER_EXTERNAL");
        input.setTurns(List.of(confirmed, unknown));

        PipelineCallbackRequest.AttributionSegmentInput first = new PipelineCallbackRequest.AttributionSegmentInput();
        first.setSegmentId("SEG_CONFIRMED");
        first.setRevision(revision);
        first.setStartMs(0L);
        first.setEndMs(1500L);
        first.setText("选手发言");
        first.setPersonId("PERSON_1");
        first.setRawSpeakerId("SPEAKER_1");
        first.setSpeakerState("CONFIRMED");
        first.setSpeakerConfidence(new BigDecimal("0.900000"));
        first.setFinal(true);

        PipelineCallbackRequest.AttributionSegmentInput second = new PipelineCallbackRequest.AttributionSegmentInput();
        second.setSegmentId("SEG_UNKNOWN");
        second.setRevision(revision);
        second.setStartMs(1500L);
        second.setEndMs(3000L);
        second.setText("画外人员插话");
        second.setPersonId(null);
        second.setRawSpeakerId("SPEAKER_EXTERNAL");
        second.setSpeakerState("UNKNOWN");
        second.setSpeakerConfidence(BigDecimal.ZERO);
        second.setFinal("FINAL".equals(status));
        input.setSegments(List.of(first, second));
        return input;
    }
}
