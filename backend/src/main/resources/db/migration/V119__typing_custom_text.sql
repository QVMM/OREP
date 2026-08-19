-- 打字练习：用户账户级自定义文案（跨设备/重登保留）
CREATE TABLE IF NOT EXISTS typing_custom_text (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  user_id BIGINT NOT NULL COMMENT '用户',
  tenant_id BIGINT DEFAULT NULL COMMENT '租户',
  title VARCHAR(120) NOT NULL DEFAULT '我的文案' COMMENT '标题',
  content MEDIUMTEXT NOT NULL COMMENT '正文',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_typing_custom_user (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='打字练习自定义文案';
