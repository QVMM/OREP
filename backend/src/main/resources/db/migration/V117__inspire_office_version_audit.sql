-- 启发 Office：版本存档 + 操作溯源（业务侧自建，不依赖 Collabora 商业能力）

CREATE TABLE IF NOT EXISTS inspire_office_version (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  document_id BIGINT NOT NULL COMMENT '文档ID',
  version_no INT NOT NULL COMMENT '版本号（与文档 version 对齐或手动命名存档序号）',
  source VARCHAR(32) NOT NULL DEFAULT 'auto_save' COMMENT 'auto_save|manual|restore|create|upload',
  label VARCHAR(120) DEFAULT NULL COMMENT '可选标签，如 提交评审前',
  storage_path VARCHAR(512) NOT NULL COMMENT '快照相对 office/ 路径',
  size_bytes BIGINT NOT NULL DEFAULT 0,
  content_sha256 VARCHAR(64) DEFAULT NULL COMMENT '内容指纹，便于去重/比对',
  created_by BIGINT DEFAULT NULL COMMENT '操作人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_inspire_office_version (document_id, version_no),
  KEY idx_inspire_office_version_doc (document_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='启发 Office 文档版本快照';

CREATE TABLE IF NOT EXISTS inspire_office_audit (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  document_id BIGINT NOT NULL COMMENT '文档ID',
  action VARCHAR(40) NOT NULL COMMENT 'create|upload|open|save|manual_snapshot|restore|rename|delete|download',
  actor_user_id BIGINT DEFAULT NULL COMMENT '操作人',
  actor_name VARCHAR(80) DEFAULT NULL COMMENT '操作人显示名（冗余）',
  version_no INT DEFAULT NULL COMMENT '关联版本号',
  detail VARCHAR(500) DEFAULT NULL COMMENT '补充说明',
  meta_json VARCHAR(1000) DEFAULT NULL COMMENT '扩展 JSON',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_inspire_office_audit_doc (document_id, created_at),
  KEY idx_inspire_office_audit_actor (actor_user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='启发 Office 操作审计';
