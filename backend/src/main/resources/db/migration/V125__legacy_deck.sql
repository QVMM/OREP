CREATE TABLE IF NOT EXISTS legacy_deck (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  created_by            BIGINT NOT NULL,
  source_type           VARCHAR(32) NOT NULL,
  source_document_id    BIGINT DEFAULT NULL,
  original_name         VARCHAR(255) NOT NULL,
  original_hash         CHAR(64) NOT NULL,
  original_path         VARCHAR(512) NOT NULL,
  work_path             VARCHAR(512) NOT NULL,
  page_count            INT NOT NULL DEFAULT 0,
  status                VARCHAR(32) NOT NULL DEFAULT 'received',
  reject_reason         VARCHAR(255) DEFAULT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_ld_user (created_by, id),
  KEY idx_ld_hash (original_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='路演台收下的已有PPT，原件只读';

ALTER TABLE judge_path
  ADD COLUMN legacy_deck_id BIGINT DEFAULT NULL AFTER ppt_job_id;
