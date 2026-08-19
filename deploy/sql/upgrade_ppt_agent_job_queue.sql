-- =====================================================
-- PPT Agent (paper-ppt-agent) 任务队列表
-- 复用现有 orep MySQL，不新增数据库实例
-- =====================================================

USE orep;

CREATE TABLE IF NOT EXISTS `ppt_agent_session` (
    `id` VARCHAR(32) NOT NULL COMMENT 'session_id (hex)',
    `owner_key` VARCHAR(128) DEFAULT NULL COMMENT 'tenant:{tid}:user:{uid}',
    `owner_user_id` VARCHAR(64) DEFAULT NULL,
    `owner_name` VARCHAR(128) DEFAULT NULL,
    `owner_tenant_id` VARCHAR(64) DEFAULT NULL,
    `file_path` VARCHAR(1024) NOT NULL,
    `source_type` VARCHAR(32) NOT NULL DEFAULT 'pdf',
    `file_name` VARCHAR(512) NOT NULL DEFAULT '',
    `file_size` BIGINT NOT NULL DEFAULT 0,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_ppt_agent_session_owner` (`owner_key`),
    KEY `idx_ppt_agent_session_updated` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='PPT Agent 上传会话（与磁盘 workspace 对应）';

CREATE TABLE IF NOT EXISTS `ppt_agent_job` (
    `id` VARCHAR(32) NOT NULL COMMENT 'job_id (hex)',
    `session_id` VARCHAR(32) NOT NULL,
    `owner_key` VARCHAR(128) DEFAULT NULL,
    `owner_user_id` VARCHAR(64) DEFAULT NULL,
    `owner_name` VARCHAR(128) DEFAULT NULL,
    `owner_tenant_id` VARCHAR(64) DEFAULT NULL,
    `status` VARCHAR(48) NOT NULL DEFAULT 'pending'
        COMMENT 'queued/pending/parsing/.../complete/error/cancelled/waiting_confirmation',
    `progress` DOUBLE NOT NULL DEFAULT 0,
    `message` VARCHAR(1024) NOT NULL DEFAULT '',
    `error` TEXT,
    `slides_completed` INT NOT NULL DEFAULT 0,
    `total_slides` INT NOT NULL DEFAULT 0,
    `output_path` VARCHAR(1024) DEFAULT NULL,
    `project_dir` VARCHAR(1024) DEFAULT NULL,
    `parent_job_id` VARCHAR(32) DEFAULT NULL,
    `provider` VARCHAR(64) DEFAULT NULL,
    `model_name` VARCHAR(128) DEFAULT NULL,
    `base_url` VARCHAR(512) DEFAULT NULL,
    `canvas_format` VARCHAR(32) DEFAULT NULL,
    `style` VARCHAR(64) DEFAULT NULL,
    `render_engine` VARCHAR(32) DEFAULT NULL,
    `language` VARCHAR(16) DEFAULT NULL,
    `detail_level` VARCHAR(32) DEFAULT NULL,
    `instruction` MEDIUMTEXT,
    `deck_type` VARCHAR(32) DEFAULT NULL,
    `mode` VARCHAR(32) DEFAULT NULL COMMENT 'full/plan_only/render_from_cards',
    `request_json` MEDIUMTEXT COMMENT '序列化的 GenerationRequest（Worker 执行用）',
    `worker_id` VARCHAR(64) DEFAULT NULL,
    `claimed_at` DATETIME DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_ppt_agent_job_session` (`session_id`),
    KEY `idx_ppt_agent_job_owner` (`owner_key`),
    KEY `idx_ppt_agent_job_status_created` (`status`, `created_at`),
    KEY `idx_ppt_agent_job_updated` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='PPT Agent 生成任务（API 入队 / Worker 认领）';
