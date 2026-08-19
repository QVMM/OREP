-- OREP AI scoring P8 upgrade: structured observations, deductions, and report calibration fields.
-- MySQL 8.0 compatible and repeatable.

CREATE TABLE IF NOT EXISTS ai_score_observation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  dimension_name VARCHAR(128) NOT NULL,
  raw_score DECIMAL(6,2) NOT NULL,
  score_cap DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  validity_status VARCHAR(32) NOT NULL,
  model_reason TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_observation_session (session_id),
  INDEX idx_ai_score_observation_report (report_id),
  INDEX idx_ai_score_observation_code (observation_code)
);

CREATE TABLE IF NOT EXISTS ai_score_deduction (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  deduction_id VARCHAR(128) NOT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  deducted_points DECIMAL(6,2) NOT NULL,
  recovered_points DECIMAL(6,2) NOT NULL DEFAULT 0,
  reason TEXT NOT NULL,
  required_fix TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL,
  max_recoverable_points DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  recovery_source_deduction_id VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_deduction_session_id (session_id, deduction_id),
  INDEX idx_ai_score_deduction_report (report_id),
  INDEX idx_ai_score_deduction_observation (observation_code)
);

DROP PROCEDURE IF EXISTS orep_p8_add_ai_score_report_column_if_missing;

DELIMITER //
CREATE PROCEDURE orep_p8_add_ai_score_report_column_if_missing(
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE ai_score_report ADD COLUMN ', p_column_name, ' ', p_column_definition);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL orep_p8_add_ai_score_report_column_if_missing('rule_engine_version', 'VARCHAR(64) DEFAULT NULL COMMENT ''规则引擎版本''');
CALL orep_p8_add_ai_score_report_column_if_missing('structured_result_json', 'TEXT COMMENT ''规则引擎结构化结果 JSON''');
CALL orep_p8_add_ai_score_report_column_if_missing('current_score_cap', 'DECIMAL(6,2) DEFAULT NULL COMMENT ''本轮证据上限''');
CALL orep_p8_add_ai_score_report_column_if_missing('recovered_score', 'DECIMAL(6,2) DEFAULT NULL COMMENT ''本轮追回分''');

DROP PROCEDURE orep_p8_add_ai_score_report_column_if_missing;
