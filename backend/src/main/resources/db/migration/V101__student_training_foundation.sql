CREATE TABLE IF NOT EXISTS training_camp (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '集训营ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  name VARCHAR(120) NOT NULL COMMENT '集训营名称',
  subtitle VARCHAR(255) DEFAULT NULL COMMENT '集训说明',
  start_date DATE NOT NULL COMMENT '开始日期',
  end_date DATE NOT NULL COMMENT '结束日期',
  total_days INT NOT NULL DEFAULT 21 COMMENT '总训练天数',
  status VARCHAR(24) NOT NULL DEFAULT 'PLANNED' COMMENT 'PLANNED/ACTIVE/COMPLETED/ARCHIVED',
  created_by BIGINT DEFAULT NULL COMMENT '创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_training_camp_tenant_status (tenant_id, status, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目集训营';

CREATE TABLE IF NOT EXISTS training_camp_week (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '集训周ID',
  camp_id BIGINT NOT NULL COMMENT '集训营ID',
  week_no INT NOT NULL COMMENT '第几周',
  title VARCHAR(120) NOT NULL COMMENT '周主题',
  start_date DATE NOT NULL COMMENT '本周开始日期',
  end_date DATE NOT NULL COMMENT '本周结束日期',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_training_week (camp_id, week_no),
  KEY idx_training_week_dates (camp_id, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集训周';

CREATE TABLE IF NOT EXISTS training_camp_team (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '集训营队伍关系ID',
  camp_id BIGINT NOT NULL COMMENT '集训营ID',
  team_id BIGINT NOT NULL COMMENT '项目队伍ID',
  status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/INACTIVE',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_training_camp_team (camp_id, team_id),
  KEY idx_training_team_lookup (team_id, status, camp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集训营参训队伍';

CREATE TABLE IF NOT EXISTS training_day (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '训练日ID',
  camp_id BIGINT NOT NULL COMMENT '集训营ID',
  week_id BIGINT DEFAULT NULL COMMENT '所属集训周ID',
  day_no INT NOT NULL COMMENT '第几天',
  training_date DATE NOT NULL COMMENT '训练日期',
  title VARCHAR(160) NOT NULL COMMENT '当日训练主题',
  summary VARCHAR(800) DEFAULT NULL COMMENT '训练说明',
  due_at DATETIME DEFAULT NULL COMMENT '截止时间',
  status VARCHAR(24) NOT NULL DEFAULT 'PUBLISHED' COMMENT 'DRAFT/PUBLISHED/CLOSED',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_training_day_no (camp_id, day_no),
  UNIQUE KEY uk_training_day_date (camp_id, training_date),
  KEY idx_training_day_week (week_id, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集训日';

CREATE TABLE IF NOT EXISTS training_day_task (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '训练日任务关系ID',
  training_day_id BIGINT NOT NULL COMMENT '训练日ID',
  task_id BIGINT NOT NULL COMMENT '项目任务ID',
  is_primary TINYINT NOT NULL DEFAULT 0 COMMENT '是否当日主任务',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_training_day_task (training_day_id, task_id),
  KEY idx_training_day_task_order (training_day_id, is_primary, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练日与项目任务关系';

CREATE TABLE IF NOT EXISTS project_task_requirement (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '任务交付要求ID',
  task_id BIGINT NOT NULL COMMENT '项目任务ID',
  title VARCHAR(160) NOT NULL COMMENT '要求名称',
  description VARCHAR(500) DEFAULT NULL COMMENT '要求说明',
  required TINYINT NOT NULL DEFAULT 1 COMMENT '是否必交',
  asset_type VARCHAR(40) DEFAULT NULL COMMENT 'FILE/LINK/TEXT/AUDIO/VIDEO',
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_task_requirement_order (task_id, sort_order, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目任务交付要求';
