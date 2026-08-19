-- Frozen docket + run history for 路演评议席 G1.
-- Safe to run after create_ai_scoring_session_tables.sql. Idempotent.

CREATE TABLE IF NOT EXISTS ai_score_docket (
  docket_id VARCHAR(64) PRIMARY KEY,
  video_sha256 VARCHAR(64) NOT NULL,
  rule_version VARCHAR(64) NOT NULL,
  rule_hash VARCHAR(128) NOT NULL,
  contract_version VARCHAR(64) NOT NULL,
  track_id VARCHAR(64) NOT NULL,
  task_book_published TINYINT NOT NULL DEFAULT 0,
  task_book_json LONGTEXT DEFAULT NULL,
  task_book_published_session_id BIGINT NULL,
  task_book_published_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_docket_identity (video_sha256, rule_version, rule_hash, contract_version, track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_score_docket_run (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  docket_id VARCHAR(64) NOT NULL,
  run_index INT NOT NULL,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  official_score DECIMAL(5,2) NULL,
  dimension_scores_json TEXT NULL,
  transcript_coverage DECIMAL(6,4) NULL,
  seekable_anchor_rate DECIMAL(6,4) NULL,
  score_delta_abs DECIMAL(6,2) NULL,
  stability_band VARCHAR(16) NULL,
  tape_grounded TINYINT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_docket_run (docket_id, run_index),
  UNIQUE KEY uk_docket_run_session (session_id),
  INDEX idx_docket_run_docket (docket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP PROCEDURE IF EXISTS orep_add_ai_scoring_session_docket_if_missing;

DELIMITER //
CREATE PROCEDURE orep_add_ai_scoring_session_docket_if_missing()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_scoring_session'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
          AND COLUMN_NAME = 'docket_id'
    ) THEN
        ALTER TABLE ai_scoring_session ADD COLUMN docket_id VARCHAR(64) NULL;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_scoring_session'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
          AND INDEX_NAME = 'idx_ai_scoring_session_docket'
    ) THEN
        CREATE INDEX idx_ai_scoring_session_docket ON ai_scoring_session (docket_id);
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_scoring_session'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
          AND COLUMN_NAME = 'teacher_confirmed'
    ) THEN
        ALTER TABLE ai_scoring_session
            ADD COLUMN teacher_confirmed TINYINT NOT NULL DEFAULT 0,
            ADD COLUMN teacher_confirmed_at DATETIME NULL,
            ADD COLUMN teacher_confirmed_by BIGINT NULL,
            ADD COLUMN challenge_completed TINYINT NOT NULL DEFAULT 0,
            ADD COLUMN deliberation_stage VARCHAR(32) NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_scoring_session'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
          AND COLUMN_NAME = 'challenge_json'
    ) THEN
        ALTER TABLE ai_scoring_session
            ADD COLUMN challenge_json LONGTEXT NULL;
    END IF;
END//
DELIMITER ;

CALL orep_add_ai_scoring_session_docket_if_missing();
DROP PROCEDURE orep_add_ai_scoring_session_docket_if_missing;

-- Same meeting may have many reports (one per rerun session). Official score is per session/run.
DROP PROCEDURE IF EXISTS orep_relax_ai_score_report_meeting_unique;

DELIMITER //
CREATE PROCEDURE orep_relax_ai_score_report_meeting_unique()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND INDEX_NAME = 'uk_meeting'
    ) THEN
        ALTER TABLE ai_score_report DROP INDEX uk_meeting;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND INDEX_NAME = 'idx_ai_score_report_meeting'
    ) THEN
        CREATE INDEX idx_ai_score_report_meeting ON ai_score_report (meeting_id);
    END IF;
END//
DELIMITER ;

CALL orep_relax_ai_score_report_meeting_unique();
DROP PROCEDURE IF EXISTS orep_relax_ai_score_report_meeting_unique;

DROP PROCEDURE IF EXISTS orep_add_docket_run_tape_grounded_if_missing;
DELIMITER //
CREATE PROCEDURE orep_add_docket_run_tape_grounded_if_missing()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_docket_run'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_docket_run'
          AND COLUMN_NAME = 'tape_grounded'
    ) THEN
        ALTER TABLE ai_score_docket_run
            ADD COLUMN tape_grounded TINYINT NULL;
    END IF;
END//
DELIMITER ;
CALL orep_add_docket_run_tape_grounded_if_missing();
DROP PROCEDURE IF EXISTS orep_add_docket_run_tape_grounded_if_missing;

DROP PROCEDURE IF EXISTS orep_add_ai_score_report_task_book_if_missing;
DELIMITER //
CREATE PROCEDURE orep_add_ai_score_report_task_book_if_missing()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND COLUMN_NAME = 'task_book_published'
    ) THEN
        ALTER TABLE ai_score_report ADD COLUMN task_book_published TINYINT NOT NULL DEFAULT 0
            COMMENT '教师是否已发布本场任务书';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND COLUMN_NAME = 'task_book_json'
    ) THEN
        ALTER TABLE ai_score_report ADD COLUMN task_book_json LONGTEXT DEFAULT NULL
            COMMENT '已发布任务书快照';
    END IF;
END//
DELIMITER ;
CALL orep_add_ai_score_report_task_book_if_missing();
DROP PROCEDURE IF EXISTS orep_add_ai_score_report_task_book_if_missing;

DROP PROCEDURE IF EXISTS orep_add_ai_score_docket_task_book_if_missing;
DELIMITER //
CREATE PROCEDURE orep_add_ai_score_docket_task_book_if_missing()
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_docket'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_docket'
          AND COLUMN_NAME = 'task_book_published'
    ) THEN
        ALTER TABLE ai_score_docket ADD COLUMN task_book_published TINYINT NOT NULL DEFAULT 0
            COMMENT '卷宗级任务书是否已发布';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_docket'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_docket'
          AND COLUMN_NAME = 'task_book_json'
    ) THEN
        ALTER TABLE ai_score_docket ADD COLUMN task_book_json LONGTEXT DEFAULT NULL
            COMMENT '卷宗级已发布任务书快照';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_docket'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_docket'
          AND COLUMN_NAME = 'task_book_published_session_id'
    ) THEN
        ALTER TABLE ai_score_docket ADD COLUMN task_book_published_session_id BIGINT NULL
            COMMENT '发布该任务书的场次';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_docket'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_docket'
          AND COLUMN_NAME = 'task_book_published_at'
    ) THEN
        ALTER TABLE ai_score_docket ADD COLUMN task_book_published_at DATETIME NULL;
    END IF;
END//
DELIMITER ;
CALL orep_add_ai_score_docket_task_book_if_missing();
DROP PROCEDURE IF EXISTS orep_add_ai_score_docket_task_book_if_missing;
