-- 启发 Office：文档元数据（与 AI PPT 生成管线无关）
CREATE TABLE IF NOT EXISTS inspire_office_document (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  file_key VARCHAR(64) NOT NULL COMMENT '协同会话 key 基座',
  version INT NOT NULL DEFAULT 1 COMMENT '保存版本；参与 document.key',
  owner_user_id BIGINT NOT NULL COMMENT '所有者用户ID',
  owner_tenant_id BIGINT DEFAULT NULL COMMENT '租户ID',
  title VARCHAR(255) NOT NULL COMMENT '显示标题',
  ext VARCHAR(16) NOT NULL COMMENT '扩展名 docx/xlsx/pptx 等',
  storage_path VARCHAR(512) NOT NULL COMMENT '相对 office/ 的存储路径',
  size_bytes BIGINT NOT NULL DEFAULT 0 COMMENT '文件字节数',
  scope VARCHAR(16) NOT NULL DEFAULT 'personal' COMMENT 'personal|project|team',
  team_id BIGINT DEFAULT NULL COMMENT '关联 project_team.id；个人为空',
  status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT 'active|deleted',
  last_opened_at DATETIME DEFAULT NULL COMMENT '最近打开时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_inspire_office_file_key (file_key),
  KEY idx_inspire_office_owner (owner_user_id, status),
  KEY idx_inspire_office_team (team_id, status),
  KEY idx_inspire_office_scope (scope, status),
  KEY idx_inspire_office_updated (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='启发 Office 文档元数据';
