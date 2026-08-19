-- Add technical/demo score calibration payload to stored AI reports.
DROP PROCEDURE IF EXISTS orep_add_score_calibration_column_if_missing;

DELIMITER //
CREATE PROCEDURE orep_add_score_calibration_column_if_missing()
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
          AND COLUMN_NAME = 'score_calibration_json'
    ) THEN
        ALTER TABLE `ai_score_report`
          ADD COLUMN `score_calibration_json` TEXT COMMENT '技术与现场演示校准 JSON' AFTER `speech_quality_json`;
    END IF;
END//
DELIMITER ;

CALL orep_add_score_calibration_column_if_missing();

DROP PROCEDURE orep_add_score_calibration_column_if_missing;
