-- 讲稿绑定智能文档改稿工作台
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'script'
    AND COLUMN_NAME = 'sdoc_document_id'
);

SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE script ADD COLUMN sdoc_document_id BIGINT DEFAULT NULL COMMENT ''绑定的智能文档 ID'' AFTER ppt_job_id, ADD KEY idx_script_sdoc (sdoc_document_id)',
  'SELECT 1'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
