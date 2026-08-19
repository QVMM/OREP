-- 讲稿表
CREATE TABLE IF NOT EXISTS `script` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `meeting_id` BIGINT DEFAULT NULL COMMENT '历史兼容字段，PPT讲稿不依赖会议ID',
  `title` VARCHAR(200) NOT NULL DEFAULT '路演讲稿' COMMENT '讲稿标题',
  `content` LONGTEXT COMMENT '讲稿内容（JSON格式，存储所有章节和步骤）',
  `roles` VARCHAR(500) DEFAULT NULL COMMENT '团队角色（JSON数组）',
  `source_type` VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '来源: manual/ppt',
  `ppt_job_id` VARCHAR(64) DEFAULT NULL COMMENT '关联 PPT 生成任务 ID',
  `sync_status` VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态: synced/page_newer/script_newer/conflict',
  `content_version` INT NOT NULL DEFAULT 1 COMMENT '内容版本号',
  `last_synced_at` DATETIME DEFAULT NULL COMMENT '最近同步时间',
  `created_by` BIGINT NOT NULL COMMENT '创建者用户ID',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ppt_job_user` (`ppt_job_id`, `created_by`),
  KEY `idx_created_by` (`created_by`),
  KEY `idx_script_source` (`source_type`, `created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='路演讲稿';
