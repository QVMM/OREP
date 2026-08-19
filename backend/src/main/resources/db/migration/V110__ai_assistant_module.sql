-- 竞赛助手：会话 / 消息 / 运行 / 记忆 / 文件 / 分享 / 知识索引

CREATE TABLE IF NOT EXISTS ai_assistant_session (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL COMMENT '会话所有者，个人空间',
  team_id         BIGINT DEFAULT NULL COMMENT '上下文团队：资源选材/保存目标',
  project_id      BIGINT DEFAULT NULL COMMENT '可选项目上下文',
  title           VARCHAR(200) NOT NULL DEFAULT '新对话',
  title_source    VARCHAR(20) NOT NULL DEFAULT 'default' COMMENT 'default|user|auto',
  status          VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT 'active|archived|deleted',
  model           VARCHAR(80) DEFAULT NULL,
  last_message_at DATETIME DEFAULT NULL,
  message_count   INT NOT NULL DEFAULT 0,
  pin             TINYINT NOT NULL DEFAULT 0,
  all_thread_id   VARCHAR(100) DEFAULT NULL COMMENT 'AnythingLLM thread 映射，可空',
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_owner_updated (tenant_id, user_id, status, updated_at),
  KEY idx_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手会话（个人）';

CREATE TABLE IF NOT EXISTS ai_assistant_message (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id        BIGINT NOT NULL,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL COMMENT '会话所有者冗余，便于鉴权',
  role              VARCHAR(20) NOT NULL COMMENT 'user|assistant|system',
  content_text      LONGTEXT COMMENT '纯文本/Markdown 正文',
  content_json      JSON DEFAULT NULL COMMENT '结构化块',
  thinking_text     LONGTEXT COMMENT '模型思考，仅展示',
  status            VARCHAR(20) NOT NULL DEFAULT 'completed'
                    COMMENT 'pending|streaming|completed|failed|cancelled',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手消息';

CREATE TABLE IF NOT EXISTS ai_assistant_run (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id            BIGINT NOT NULL,
  tenant_id             BIGINT NOT NULL,
  user_id               BIGINT NOT NULL,
  user_message_id       BIGINT NOT NULL,
  assistant_message_id  BIGINT DEFAULT NULL,
  status                VARCHAR(20) NOT NULL DEFAULT 'queued'
                        COMMENT 'queued|running|completed|failed|cancelled',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手单次生成运行';

CREATE TABLE IF NOT EXISTS ai_assistant_run_step (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id          BIGINT NOT NULL,
  session_id      BIGINT NOT NULL,
  step_no         INT NOT NULL,
  step_key        VARCHAR(64) NOT NULL,
  title           VARCHAR(120) NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT 'running|completed|failed|skipped',
  input_summary   VARCHAR(500) DEFAULT NULL,
  output_summary  VARCHAR(1000) DEFAULT NULL,
  detail_json     JSON DEFAULT NULL,
  started_at      DATETIME DEFAULT NULL,
  finished_at     DATETIME DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_run_step (run_id, step_no),
  KEY idx_session_steps (session_id, run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手运行步骤';

CREATE TABLE IF NOT EXISTS ai_assistant_file (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  session_id        BIGINT NOT NULL,
  message_id        BIGINT DEFAULT NULL,
  source            VARCHAR(20) NOT NULL COMMENT 'upload|generated|resource_ref|export',
  visibility        VARCHAR(20) NOT NULL DEFAULT 'private' COMMENT 'private|team_resource',
  name              VARCHAR(255) NOT NULL,
  mime_type         VARCHAR(120) DEFAULT NULL,
  size_bytes        BIGINT DEFAULT NULL,
  storage_key       VARCHAR(500) DEFAULT NULL,
  resource_id       INT DEFAULT NULL,
  sha256            VARCHAR(64) DEFAULT NULL,
  index_status      VARCHAR(20) NOT NULL DEFAULT 'none'
                    COMMENT 'none|pending|indexing|ready|failed|skipped',
  index_error       VARCHAR(500) DEFAULT NULL,
  all_document_id   VARCHAR(100) DEFAULT NULL,
  meta_json         JSON DEFAULT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_files (session_id, source),
  KEY idx_user_files (tenant_id, user_id, created_at),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手会话文件元数据';

CREATE TABLE IF NOT EXISTS ai_assistant_memory (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  team_id           BIGINT DEFAULT NULL COMMENT '关联团队上下文，仍仅本人可见',
  memory_type       VARCHAR(32) NOT NULL
                    COMMENT 'preference|goal|style|project_focus|manual|auto_summary',
  content           VARCHAR(500) NOT NULL COMMENT '单条短事实，禁止精确分数',
  importance        TINYINT NOT NULL DEFAULT 3 COMMENT '1-5',
  source            VARCHAR(20) NOT NULL DEFAULT 'manual' COMMENT 'manual|auto|system',
  source_session_id BIGINT DEFAULT NULL,
  status            VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT 'active|archived|deleted',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_user_active (tenant_id, user_id, status, importance),
  KEY idx_user_type (tenant_id, user_id, memory_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='竞赛助手个人记忆';

CREATE TABLE IF NOT EXISTS ai_assistant_share (
  id                BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id         BIGINT NOT NULL,
  user_id           BIGINT NOT NULL,
  session_id        BIGINT NOT NULL,
  team_id           BIGINT NOT NULL,
  share_mode        VARCHAR(20) NOT NULL COMMENT 'summary|full_text|artifacts_only',
  include_thinking  TINYINT NOT NULL DEFAULT 0,
  resource_id       INT DEFAULT NULL,
  file_id           BIGINT DEFAULT NULL,
  status            VARCHAR(20) NOT NULL DEFAULT 'completed',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_share (session_id),
  KEY idx_team_share (team_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='对话分享到团队审计';

CREATE TABLE IF NOT EXISTS ai_team_workspace_map (
  id                   BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id            BIGINT NOT NULL,
  team_id              BIGINT NOT NULL,
  all_workspace_slug   VARCHAR(120) NOT NULL,
  all_workspace_id     VARCHAR(80) DEFAULT NULL,
  status               VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_team (tenant_id, team_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='团队到 AnythingLLM Workspace 映射';

CREATE TABLE IF NOT EXISTS ai_knowledge_index_job (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  team_id         BIGINT NOT NULL,
  resource_id     INT NOT NULL,
  action          VARCHAR(20) NOT NULL COMMENT 'upsert|delete',
  status          VARCHAR(20) NOT NULL DEFAULT 'pending',
  attempts        INT NOT NULL DEFAULT 0,
  last_error      VARCHAR(500) DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_pending (status, id),
  KEY idx_resource (resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='资源中心知识索引任务';

-- 资源中心知识索引状态字段（幂等：列已存在则跳过，DEFAULT 不改写已有业务数据语义）
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'knowledge_status'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN knowledge_status VARCHAR(20) NOT NULL DEFAULT ''none'' COMMENT ''none|pending|indexing|ready|failed|skipped'' AFTER category',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'knowledge_document_id'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN knowledge_document_id VARCHAR(100) DEFAULT NULL AFTER knowledge_status',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'content_hash'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN content_hash VARCHAR(64) DEFAULT NULL AFTER knowledge_document_id',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'indexed_at'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN indexed_at DATETIME DEFAULT NULL AFTER content_hash',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'index_error'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN index_error VARCHAR(500) DEFAULT NULL AFTER indexed_at',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'resource' AND COLUMN_NAME = 'index_version'
);
SET @sql := IF(
  @col_exists = 0,
  'ALTER TABLE resource ADD COLUMN index_version INT NOT NULL DEFAULT 0 AFTER index_error',
  'SELECT 1'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
