-- 竞赛助手表结构（与 Flyway V110 对齐，供手工/离线部署）
-- 若使用 Flyway，请直接依赖 backend/src/main/resources/db/migration/V110__ai_assistant_module.sql

CREATE TABLE IF NOT EXISTS ai_assistant_session (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  team_id         BIGINT DEFAULT NULL,
  project_id      BIGINT DEFAULT NULL,
  title           VARCHAR(200) NOT NULL DEFAULT '新对话',
  title_source    VARCHAR(20) NOT NULL DEFAULT 'default',
  status          VARCHAR(20) NOT NULL DEFAULT 'active',
  model           VARCHAR(80) DEFAULT NULL,
  last_message_at DATETIME DEFAULT NULL,
  message_count   INT NOT NULL DEFAULT 0,
  pin             TINYINT NOT NULL DEFAULT 0,
  all_thread_id   VARCHAR(100) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_owner_updated (tenant_id, user_id, status, updated_at),
  KEY idx_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_message (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id        BIGINT NOT NULL,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  role              VARCHAR(20) NOT NULL,
  content_text      LONGTEXT,
  content_json      JSON DEFAULT NULL,
  thinking_text     LONGTEXT,
  status            VARCHAR(20) NOT NULL DEFAULT 'completed',
  model             VARCHAR(80) DEFAULT NULL,
  run_id            BIGINT DEFAULT NULL,
  parent_message_id BIGINT DEFAULT NULL,
  client_message_id VARCHAR(64) DEFAULT NULL,
  token_prompt      INT DEFAULT NULL,
  token_completion  INT DEFAULT NULL,
  error_code        VARCHAR(40) DEFAULT NULL,
  error_message     VARCHAR(500) DEFAULT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_session_time (session_id, id),
  KEY idx_run (run_id),
  UNIQUE KEY uk_session_client_msg (session_id, client_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_run (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id            BIGINT NOT NULL,
  tenant_id             BIGINT NOT NULL,
  user_id               BIGINT NOT NULL,
  user_message_id       BIGINT NOT NULL,
  assistant_message_id  BIGINT DEFAULT NULL,
  status                VARCHAR(20) NOT NULL DEFAULT 'queued',
  intent_json           JSON DEFAULT NULL,
  request_json          JSON DEFAULT NULL,
  trace_id              VARCHAR(64) NOT NULL,
  started_at            DATETIME DEFAULT NULL,
  finished_at           DATETIME DEFAULT NULL,
  error_code            VARCHAR(40) DEFAULT NULL,
  error_message         VARCHAR(500) DEFAULT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_run (session_id, id),
  KEY idx_trace (trace_id),
  KEY idx_status (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_run_step (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id          BIGINT NOT NULL,
  session_id      BIGINT NOT NULL,
  step_no         INT NOT NULL,
  step_key        VARCHAR(64) NOT NULL,
  title           VARCHAR(120) NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'running',
  input_summary   VARCHAR(500) DEFAULT NULL,
  output_summary  VARCHAR(1000) DEFAULT NULL,
  detail_json     JSON DEFAULT NULL,
  started_at      DATETIME DEFAULT NULL,
  finished_at     DATETIME DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_run_step (run_id, step_no),
  KEY idx_session_steps (session_id, run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_file (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  session_id        BIGINT NOT NULL,
  message_id        BIGINT DEFAULT NULL,
  source            VARCHAR(20) NOT NULL,
  visibility        VARCHAR(20) NOT NULL DEFAULT 'private',
  name              VARCHAR(255) NOT NULL,
  mime_type         VARCHAR(120) DEFAULT NULL,
  size_bytes        BIGINT DEFAULT NULL,
  storage_key       VARCHAR(500) DEFAULT NULL,
  resource_id       INT DEFAULT NULL,
  sha256            VARCHAR(64) DEFAULT NULL,
  index_status      VARCHAR(20) NOT NULL DEFAULT 'none',
  index_error       VARCHAR(500) DEFAULT NULL,
  all_document_id   VARCHAR(100) DEFAULT NULL,
  meta_json         JSON DEFAULT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_files (session_id, source),
  KEY idx_user_files (tenant_id, user_id, created_at),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_memory (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  team_id           BIGINT DEFAULT NULL,
  memory_type       VARCHAR(32) NOT NULL,
  content           VARCHAR(500) NOT NULL,
  importance        TINYINT NOT NULL DEFAULT 3,
  source            VARCHAR(20) NOT NULL DEFAULT 'manual',
  source_session_id BIGINT DEFAULT NULL,
  status            VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_user_active (tenant_id, user_id, status, importance),
  KEY idx_user_type (tenant_id, user_id, memory_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_assistant_share (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  session_id        BIGINT NOT NULL,
  team_id           BIGINT NOT NULL,
  share_mode        VARCHAR(20) NOT NULL,
  include_thinking  TINYINT NOT NULL DEFAULT 0,
  resource_id       INT DEFAULT NULL,
  file_id           BIGINT DEFAULT NULL,
  status            VARCHAR(20) NOT NULL DEFAULT 'completed',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_share (session_id),
  KEY idx_team_share (team_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_team_workspace_map (
  id                   BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id            BIGINT NOT NULL,
  team_id              BIGINT NOT NULL,
  all_workspace_slug   VARCHAR(120) NOT NULL,
  all_workspace_id     VARCHAR(80) DEFAULT NULL,
  status               VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ai_knowledge_index_job (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  team_id         BIGINT NOT NULL,
  resource_id     INT NOT NULL,
  action          VARCHAR(20) NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'pending',
  attempts        INT NOT NULL DEFAULT 0,
  last_error      VARCHAR(500) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_pending (status, id),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
