-- Versioned, evidence-only speaker attribution persistence.
-- Safe to run after create_ai_scoring_session_tables.sql.

DELIMITER //
CREATE PROCEDURE add_speaker_attribution_column_if_missing(
    IN p_table VARCHAR(64),
    IN p_column VARCHAR(64),
    IN p_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND COLUMN_NAME = p_column
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE ', p_table, ' ADD COLUMN ', p_column, ' ', p_definition);
        PREPARE statement FROM @ddl;
        EXECUTE statement;
        DEALLOCATE PREPARE statement;
    END IF;
END //

CREATE PROCEDURE add_speaker_attribution_index_if_missing(
    IN p_table VARCHAR(64),
    IN p_index VARCHAR(64),
    IN p_ddl TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = p_table AND INDEX_NAME = p_index
    ) THEN
        SET @ddl = p_ddl;
        PREPARE statement FROM @ddl;
        EXECUTE statement;
        DEALLOCATE PREPARE statement;
    END IF;
END //
DELIMITER ;

CALL add_speaker_attribution_column_if_missing('ai_scoring_session', 'speaker_attribution_revision', 'INT NULL');
CALL add_speaker_attribution_column_if_missing('ai_scoring_session', 'speaker_attribution_status', 'VARCHAR(24) NULL');
CALL add_speaker_attribution_column_if_missing('ai_scoring_session', 'speaker_attribution_contract_version', 'VARCHAR(64) NULL');
CALL add_speaker_attribution_column_if_missing('ai_scoring_session', 'speaker_attribution_clock_id', 'VARCHAR(160) NULL');
CALL add_speaker_attribution_column_if_missing('ai_scoring_session', 'speaker_attribution_snapshot_hash', 'VARCHAR(80) NULL');

CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'person_id', 'VARCHAR(160) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'person_type', 'VARCHAR(24) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'contestant_slot', 'INT NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'person_state', 'VARCHAR(24) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'first_seen_ms', 'BIGINT NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'last_seen_ms', 'BIGINT NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_speaker_identity', 'voice_cluster_ids_json', 'LONGTEXT NULL');

-- Stable people may be visual/off-screen identities without a raw acoustic cluster.
ALTER TABLE ai_score_speaker_identity MODIFY COLUMN raw_speaker_label VARCHAR(128) NULL;

CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'segment_uid', 'VARCHAR(160) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'attribution_revision', 'INT NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'person_id', 'VARCHAR(160) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'speaker_state', 'VARCHAR(32) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'speaker_confidence', 'DECIMAL(7,6) NULL');
CALL add_speaker_attribution_column_if_missing('ai_score_transcript_segment', 'is_final', 'TINYINT(1) NULL');

CREATE TABLE IF NOT EXISTS ai_score_speaker_turn (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  turn_uid VARCHAR(160) NOT NULL,
  attribution_revision INT NOT NULL,
  start_ms BIGINT NOT NULL,
  end_ms BIGINT NOT NULL,
  person_id VARCHAR(160) NULL,
  speaker_state VARCHAR(32) NOT NULL,
  confidence DECIMAL(7,6) NULL,
  candidate_person_ids_json LONGTEXT NULL,
  source_cluster_id VARCHAR(160) NULL,
  source_visual_identity_id VARCHAR(160) NULL,
  speaker_verification VARCHAR(40) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_speaker_turn (session_id, turn_uid),
  INDEX idx_ai_score_speaker_turn_session (session_id),
  INDEX idx_ai_score_speaker_turn_person (session_id, person_id)
);

CALL add_speaker_attribution_index_if_missing(
  'ai_score_speaker_identity', 'uk_ai_score_speaker_person',
  'CREATE UNIQUE INDEX uk_ai_score_speaker_person ON ai_score_speaker_identity(session_id, person_id)'
);
CALL add_speaker_attribution_index_if_missing(
  'ai_score_transcript_segment', 'uk_ai_score_transcript_segment_uid',
  'CREATE UNIQUE INDEX uk_ai_score_transcript_segment_uid ON ai_score_transcript_segment(session_id, segment_uid)'
);

DROP PROCEDURE add_speaker_attribution_index_if_missing;
DROP PROCEDURE add_speaker_attribution_column_if_missing;
