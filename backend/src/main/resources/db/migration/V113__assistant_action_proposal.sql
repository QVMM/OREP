-- 小启 AI 可写操作确认卡（L2）：提案入库，用户确认后才执行
CREATE TABLE IF NOT EXISTS ai_assistant_action_proposal (
  id              BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id       BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  session_id      BIGINT DEFAULT NULL,
  run_id          BIGINT DEFAULT NULL,
  action_type     VARCHAR(64) NOT NULL
                  COMMENT 'collab_accept|collab_decline|collab_withdraw|create_task|complete_learning',
  title           VARCHAR(200) NOT NULL,
  summary         VARCHAR(1000) DEFAULT NULL,
  args_json       JSON NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                  COMMENT 'pending|confirmed|rejected|expired|failed',
  result_json     JSON DEFAULT NULL,
  error_message   VARCHAR(500) DEFAULT NULL,
  expires_at      DATETIME NOT NULL,
  confirmed_at    DATETIME DEFAULT NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user_status (tenant_id, user_id, status, id),
  KEY idx_session (session_id),
  KEY idx_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='小启AI待确认写操作';
