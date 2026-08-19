CREATE TABLE IF NOT EXISTS ai_assistant_folder (
  id          BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id   BIGINT NOT NULL,
  user_id     BIGINT NOT NULL,
  name        VARCHAR(80) NOT NULL,
  slug        VARCHAR(40) NOT NULL,
  builtin     TINYINT NOT NULL DEFAULT 0,
  sort_order  INT NOT NULL DEFAULT 0,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_owner_slug (tenant_id, user_id, slug),
  KEY idx_owner (tenant_id, user_id, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE ai_assistant_session
  ADD COLUMN folder_id BIGINT NULL AFTER project_id,
  ADD KEY idx_owner_folder (tenant_id, user_id, folder_id);
