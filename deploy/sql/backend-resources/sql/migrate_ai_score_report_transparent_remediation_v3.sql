-- AI score transparent remediation v3. MySQL 8.0 compatible and repeatable.

DROP PROCEDURE IF EXISTS orep_v3_add_report_column_if_missing;

DELIMITER //
CREATE PROCEDURE orep_v3_add_report_column_if_missing(
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.COLUMNS
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

CALL orep_v3_add_report_column_if_missing('loss_ledger_json', 'LONGTEXT NULL COMMENT ''不可变失分账本快照''');
CALL orep_v3_add_report_column_if_missing('coverage_summary_json', 'LONGTEXT NULL COMMENT ''整改覆盖摘要''');
CALL orep_v3_add_report_column_if_missing('contract_version', 'VARCHAR(64) NULL COMMENT ''报告数据契约版本''');
CALL orep_v3_add_report_column_if_missing('todo_portfolio_status', 'VARCHAR(32) NULL COMMENT ''complete/incomplete''');

DROP PROCEDURE orep_v3_add_report_column_if_missing;

CREATE TABLE IF NOT EXISTS ai_score_remediation_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_scope_key VARCHAR(128) NOT NULL,
  task_key VARCHAR(128) NOT NULL,
  root_cause_key VARCHAR(191) NOT NULL,
  title VARCHAR(500) NOT NULL,
  task_json LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'not_started',
  source_report_id BIGINT NOT NULL,
  latest_report_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_remediation_project_task (project_scope_key, task_key),
  INDEX idx_ai_score_remediation_source_report (source_report_id),
  INDEX idx_ai_score_remediation_latest_report (latest_report_id)
);

CREATE TABLE IF NOT EXISTS ai_score_task_loss_link (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  report_id BIGINT NOT NULL,
  task_id BIGINT NOT NULL,
  loss_id VARCHAR(128) NOT NULL,
  loss_key VARCHAR(255) NOT NULL,
  observation_code VARCHAR(128) NULL,
  score_budget_key VARCHAR(255) NOT NULL,
  gap_points DECIMAL(7,2) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_task_loss (report_id, task_id, loss_key),
  INDEX idx_ai_score_task_loss_task (task_id),
  INDEX idx_ai_score_task_loss_report (report_id)
);

CREATE TABLE IF NOT EXISTS ai_score_task_verification (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  task_id BIGINT NOT NULL,
  source_session_id BIGINT NULL,
  verification_session_id BIGINT NOT NULL,
  report_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  minimum_passed TINYINT(1) NULL,
  full_score_passed TINYINT(1) NULL,
  evidence_anchor_ids_json LONGTEXT NULL,
  previous_state_json LONGTEXT NULL,
  current_state_json LONGTEXT NULL,
  reason TEXT NULL,
  rule_comparable TINYINT(1) NOT NULL DEFAULT 1,
  verified_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_task_verification (task_id, verification_session_id),
  INDEX idx_ai_score_task_verification_report (report_id)
);
