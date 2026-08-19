-- 讲稿确认写回前快照：每次 apply_script_patch 先留补丁前 JSON
CREATE TABLE IF NOT EXISTS script_revision (
  id               BIGINT PRIMARY KEY AUTO_INCREMENT,
  script_id        BIGINT NOT NULL,
  content_version  INT NOT NULL COMMENT '快照时的版本（补丁前）',
  content          LONGTEXT NOT NULL COMMENT '补丁前章节/步骤 JSON',
  roles            VARCHAR(500) DEFAULT NULL COMMENT '补丁前角色列表 JSON',
  source           VARCHAR(64) NOT NULL DEFAULT 'apply_script_patch',
  created_by       BIGINT DEFAULT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_script_rev (script_id, id),
  KEY idx_script_rev_user (created_by, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='讲稿补丁前版本快照';
