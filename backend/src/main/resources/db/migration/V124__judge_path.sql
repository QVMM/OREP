CREATE TABLE IF NOT EXISTS judge_path (
  id                      BIGINT PRIMARY KEY AUTO_INCREMENT,
  team_id                 BIGINT DEFAULT NULL,
  created_by              BIGINT NOT NULL,
  script_id               BIGINT DEFAULT NULL,
  score_report_id         BIGINT DEFAULT NULL,
  script_content_version  INT DEFAULT NULL,
  ppt_job_id              VARCHAR(64) DEFAULT NULL,
  status                  VARCHAR(32) NOT NULL DEFAULT 'compiled',
  path_json               LONGTEXT NOT NULL,
  created_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_jp_user (created_by, id),
  KEY idx_jp_script (script_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='路演评委路径';

CREATE TABLE IF NOT EXISTS judge_path_revision (
  id           BIGINT PRIMARY KEY AUTO_INCREMENT,
  path_id      BIGINT NOT NULL,
  path_json    LONGTEXT NOT NULL,
  created_by   BIGINT DEFAULT NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_jpr_path (path_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='评委路径确认前快照';
