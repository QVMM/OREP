-- AI 复盘问答会话表
CREATE TABLE IF NOT EXISTS `ai_chat_session` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `meeting_id` BIGINT NOT NULL COMMENT '关联会议ID',
  `session_key` VARCHAR(100) DEFAULT NULL COMMENT 'Python 服务会话ID',
  `project_name` VARCHAR(200) DEFAULT NULL COMMENT '项目名称',
  `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态: active/closed',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_meeting` (`meeting_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI复盘问答会话';

-- AI 复盘问答消息表
CREATE TABLE IF NOT EXISTS `ai_chat_message` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `session_id` BIGINT NOT NULL COMMENT '关联会话ID',
  `role` VARCHAR(20) NOT NULL COMMENT '角色: user/assistant',
  `content` LONGTEXT NOT NULL COMMENT '消息内容',
  `model` VARCHAR(50) DEFAULT NULL COMMENT '回答使用的模型',
  `route_type` VARCHAR(20) DEFAULT NULL COMMENT '路由类型: TEXT/VISUAL',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_session` (`session_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI复盘问答消息';
