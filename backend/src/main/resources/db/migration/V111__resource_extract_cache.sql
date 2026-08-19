-- 资源中心文档抽取缓存（含 OCR），避免重复解析
-- 幂等：列/索引已存在则跳过，不改写已有行数据

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_text'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_text LONGTEXT NULL COMMENT ''抽取正文缓存（含OCR）'' AFTER index_version',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_method'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_method VARCHAR(32) NULL COMMENT ''text_layer|ocr|docx|pptx|text|empty'' AFTER extract_text',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_hash'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_hash VARCHAR(64) NULL COMMENT ''源文件SHA-256，变更则失效'' AFTER extract_method',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_chars'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_chars INT NULL COMMENT ''抽取字符数'' AFTER extract_hash',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_at'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_at DATETIME NULL COMMENT ''抽取完成时间'' AFTER extract_chars',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND COLUMN_NAME = 'extract_error'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN extract_error VARCHAR(500) NULL COMMENT ''最近一次抽取错误'' AFTER extract_at',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @idx_exists := (
  SELECT COUNT(*) FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'resource'
    AND INDEX_NAME = 'idx_resource_extract_hash'
);
SET @sql := IF(
  @idx_exists = 0,
  'CREATE INDEX idx_resource_extract_hash ON resource (extract_hash)',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
