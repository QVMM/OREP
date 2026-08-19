-- 启发 Office（Collabora Online / WOPI）文档元数据
CREATE TABLE IF NOT EXISTS inspire_office_document (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  file_key VARCHAR(64) NOT NULL COMMENT '稳定文件标识',
  version INT NOT NULL DEFAULT 1 COMMENT '内容版本（WOPI Version）',
  owner_user_id BIGINT NOT NULL COMMENT '所有者',
  owner_tenant_id BIGINT DEFAULT NULL COMMENT '租户',
  title VARCHAR(255) NOT NULL COMMENT '标题',
  ext VARCHAR(16) NOT NULL COMMENT '扩展名 docx/xlsx/pptx',
  storage_path VARCHAR(512) NOT NULL COMMENT '相对 office/ 路径',
  size_bytes BIGINT NOT NULL DEFAULT 0 COMMENT '字节数',
  scope VARCHAR(16) NOT NULL DEFAULT 'personal' COMMENT 'personal|project|team',
  team_id BIGINT DEFAULT NULL COMMENT 'project_team.id',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT 'active|deleted',
  last_opened_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_inspire_office_file_key (file_key),
  KEY idx_inspire_office_owner (owner_user_id, status),
  KEY idx_inspire_office_team (team_id, status),
  KEY idx_inspire_office_scope (scope, status),
  KEY idx_inspire_office_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='启发 Office 文档（Collabora）';
