-- OREP AI score report session-native upgrade.
-- New upload-video reports should bind to ai_scoring_session.id through session_id.
-- meeting_id remains nullable for legacy meeting-room reports and historical compatibility.

DROP PROCEDURE IF EXISTS orep_add_ai_score_report_column_if_missing;

DELIMITER //
CREATE PROCEDURE orep_add_ai_score_report_column_if_missing(
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

CALL orep_add_ai_score_report_column_if_missing('session_id', 'BIGINT DEFAULT NULL COMMENT ''AI评分会话ID'' AFTER id');

DROP PROCEDURE orep_add_ai_score_report_column_if_missing;

ALTER TABLE ai_score_report
  MODIFY COLUMN meeting_id BIGINT DEFAULT NULL COMMENT '关联会议ID，上传视频评分可为空';

DROP PROCEDURE IF EXISTS orep_add_ai_score_report_index_if_missing;

DELIMITER //
CREATE PROCEDURE orep_add_ai_score_report_index_if_missing(
    IN p_index_name VARCHAR(64),
    IN p_index_definition TEXT
)
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_score_report'
          AND INDEX_NAME = p_index_name
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE ai_score_report ADD ', p_index_definition);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL orep_add_ai_score_report_index_if_missing('uk_session', 'UNIQUE KEY uk_session (session_id)');

DROP PROCEDURE orep_add_ai_score_report_index_if_missing;
