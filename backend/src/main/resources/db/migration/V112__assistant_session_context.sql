-- 竞赛助手：会话级上下文 Slot（项目名/报告/产物偏好等）
-- 幂等：列已存在则跳过

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'ai_assistant_session'
    AND COLUMN_NAME = 'context_json'
);

SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE ai_assistant_session ADD COLUMN context_json JSON DEFAULT NULL COMMENT ''会话 Slot 记忆：project/track/artifact 等'' AFTER all_thread_id',
  'SELECT 1'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
