-- 备赛日报：一人一天一份，camp_id 可空（非训练营也可用）
CREATE TABLE IF NOT EXISTS daily_report (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  report_date DATE NOT NULL,
  camp_id BIGINT DEFAULT NULL,
  team_id BIGINT DEFAULT NULL,
  context_type VARCHAR(32) NOT NULL DEFAULT 'FREE',
  content_done TEXT,
  content_blocker TEXT,
  content_next TEXT,
  effort_hours DECIMAL(4,1) DEFAULT NULL,
  mood VARCHAR(32) DEFAULT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  submitted_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_daily_report_user_day (user_id, report_date),
  KEY idx_daily_report_tenant_day (tenant_id, report_date),
  KEY idx_daily_report_camp (camp_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
