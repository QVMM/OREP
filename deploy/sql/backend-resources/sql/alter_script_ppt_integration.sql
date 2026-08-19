-- PPT 讲稿与独立讲稿编辑打通所需字段
-- 生产库如已存在字段，请按实际情况逐条执行或忽略重复列错误。

ALTER TABLE `script`
  MODIFY COLUMN `meeting_id` BIGINT DEFAULT NULL COMMENT '历史兼容字段，PPT讲稿不依赖会议ID',
  ADD COLUMN `source_type` VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '来源: manual/ppt',
  ADD COLUMN `ppt_job_id` VARCHAR(64) DEFAULT NULL COMMENT '关联 PPT 生成任务 ID',
  ADD COLUMN `sync_status` VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态: synced/page_newer/script_newer/conflict',
  ADD COLUMN `content_version` INT NOT NULL DEFAULT 1 COMMENT '内容版本号',
  ADD COLUMN `last_synced_at` DATETIME DEFAULT NULL COMMENT '最近同步时间';

ALTER TABLE `script` DROP INDEX `uk_meeting`;
ALTER TABLE `script` DROP INDEX `uk_meeting_user`;
CREATE UNIQUE INDEX `uk_ppt_job_user` ON `script` (`ppt_job_id`, `created_by`);
CREATE INDEX `idx_script_source` ON `script` (`source_type`, `created_by`);

ALTER TABLE `ppt_script_page`
  ADD COLUMN `script_id` BIGINT DEFAULT NULL COMMENT '关联整篇讲稿 ID',
  ADD COLUMN `script_step_id` VARCHAR(64) DEFAULT NULL COMMENT '关联讲稿步骤 ID',
  ADD COLUMN `content_hash` VARCHAR(64) DEFAULT NULL COMMENT '讲稿内容哈希',
  ADD COLUMN `version` INT NOT NULL DEFAULT 1 COMMENT '页级版本',
  ADD COLUMN `sync_state` VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态: synced/page_newer/script_newer/conflict',
  ADD COLUMN `last_synced_at` DATETIME DEFAULT NULL COMMENT '最近同步时间';

CREATE INDEX `idx_ppt_script_link` ON `ppt_script_page` (`script_id`, `script_step_id`);
