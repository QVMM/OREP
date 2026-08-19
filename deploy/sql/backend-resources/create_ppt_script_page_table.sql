-- PPT 每页讲稿持久化表
-- 用于把 PPT 生成页里的 speaker notes 落到平台 MySQL，避免只依赖 AI 服务临时项目目录。
CREATE TABLE IF NOT EXISTS `ppt_script_page` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `job_id` VARCHAR(64) NOT NULL COMMENT 'PPT 生成任务 ID',
  `page_index` INT NOT NULL COMMENT '页码，从 1 开始',
  `page_name` VARCHAR(128) DEFAULT NULL COMMENT 'SVG/页面文件名',
  `page_title` VARCHAR(255) DEFAULT NULL COMMENT '页面标题',
  `notes` TEXT COMMENT '本页讲稿',
  `document_json` LONGTEXT COMMENT '编辑器结构化文档快照 JSON',
  `source` VARCHAR(32) DEFAULT 'ppt-editor' COMMENT '来源: generated/manual/ppt-editor/import',
  `manual_edited` TINYINT(1) DEFAULT 1 COMMENT '是否用户手动修改过',
  `script_id` BIGINT DEFAULT NULL COMMENT '关联整篇讲稿 ID',
  `script_step_id` VARCHAR(64) DEFAULT NULL COMMENT '关联讲稿步骤 ID',
  `content_hash` VARCHAR(64) DEFAULT NULL COMMENT '讲稿内容哈希',
  `version` INT NOT NULL DEFAULT 1 COMMENT '页级版本',
  `sync_state` VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态: synced/page_newer/script_newer/conflict',
  `last_synced_at` DATETIME DEFAULT NULL COMMENT '最近同步时间',
  `created_by` BIGINT NOT NULL COMMENT '创建者用户 ID',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_job_page_user` (`job_id`, `page_index`, `created_by`),
  KEY `idx_job_user` (`job_id`, `created_by`),
  KEY `idx_ppt_script_link` (`script_id`, `script_step_id`),
  KEY `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 每页讲稿持久化表';
