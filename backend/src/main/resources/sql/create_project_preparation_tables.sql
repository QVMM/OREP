CREATE TABLE IF NOT EXISTS project_prep_session (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  team_id BIGINT NOT NULL COMMENT '项目团队ID',
  created_by BIGINT NOT NULL COMMENT '创建人',
  title VARCHAR(160) NOT NULL DEFAULT '选题策划会话' COMMENT '会话标题',
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  active_direction_id BIGINT DEFAULT NULL COMMENT '已采纳方向ID',
  context_snapshot_json MEDIUMTEXT COMMENT '上下文快照JSON',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_prep_session_team (tenant_id, team_id),
  KEY idx_project_prep_session_creator (created_by)
) COMMENT='项目准备选题会话';

CREATE TABLE IF NOT EXISTS project_prep_message (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  role VARCHAR(32) NOT NULL COMMENT '消息角色',
  content TEXT NOT NULL COMMENT '消息内容',
  source_type VARCHAR(40) NOT NULL DEFAULT 'USER_INPUT' COMMENT '来源类型',
  model VARCHAR(120) DEFAULT NULL COMMENT '模型名称',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_project_prep_message_session (session_id, id)
) COMMENT='项目准备选题消息';

CREATE TABLE IF NOT EXISTS project_prep_direction (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  ai_run_id BIGINT DEFAULT NULL COMMENT 'AI运行ID',
  generation_no INT NOT NULL DEFAULT 1 COMMENT '生成轮次',
  title VARCHAR(180) NOT NULL COMMENT '方向标题',
  summary TEXT COMMENT '方向摘要',
  tags_json TEXT COMMENT '标签JSON',
  equipment_match VARCHAR(80) DEFAULT NULL COMMENT '设备/资源匹配度',
  competition_match VARCHAR(80) DEFAULT NULL COMMENT '赛项匹配度',
  evidence_gaps_json TEXT COMMENT '证据缺口JSON',
  risks_json TEXT COMMENT '风险点JSON',
  next_tasks_json TEXT COMMENT '下一步任务JSON',
  research_refs_json TEXT COMMENT '研究来源JSON',
  scores_json TEXT COMMENT '专家评分JSON',
  recommendation_level VARCHAR(40) DEFAULT NULL COMMENT '推荐等级',
  expert_rationale TEXT COMMENT '专家团推荐理由',
  selected TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已采纳',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_prep_direction_session (session_id, selected),
  KEY idx_project_prep_direction_run (session_id, ai_run_id)
) COMMENT='项目准备选题方向';

CREATE TABLE IF NOT EXISTS project_prep_ai_run (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  run_type VARCHAR(40) NOT NULL DEFAULT 'TOPIC_PLANNING' COMMENT '运行类型',
  status VARCHAR(32) NOT NULL DEFAULT 'RUNNING' COMMENT '运行状态',
  model VARCHAR(120) DEFAULT NULL COMMENT '模型名称',
  request_json MEDIUMTEXT COMMENT '请求JSON',
  response_json MEDIUMTEXT COMMENT '响应JSON',
  error_message TEXT COMMENT '错误信息',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_project_prep_ai_run_session (session_id, id)
) COMMENT='项目准备AI运行记录';

CREATE TABLE IF NOT EXISTS project_prep_document (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  direction_id BIGINT DEFAULT NULL COMMENT '选题方向ID',
  title VARCHAR(180) NOT NULL COMMENT '文档标题',
  content MEDIUMTEXT COMMENT '文档内容',
  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' COMMENT '状态',
  created_by BIGINT NOT NULL COMMENT '创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_prep_document_session (session_id, id)
) COMMENT='项目准备策划文档';

CREATE TABLE IF NOT EXISTS project_prep_task_generation (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  direction_id BIGINT NOT NULL COMMENT '选题方向ID',
  task_id BIGINT NOT NULL COMMENT '项目任务ID',
  task_title VARCHAR(180) NOT NULL COMMENT '任务标题',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_prep_task_generation (session_id, direction_id, task_id),
  KEY idx_project_prep_task_generation_direction (session_id, direction_id)
) COMMENT='选题方向生成项目任务映射';

CREATE TABLE IF NOT EXISTS project_prep_agent_step (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  session_id BIGINT NOT NULL COMMENT '选题会话ID',
  ai_run_id BIGINT NOT NULL COMMENT 'AI运行ID',
  step_no INT NOT NULL COMMENT '步骤序号',
  agent_key VARCHAR(80) NOT NULL COMMENT '专家标识',
  agent_name VARCHAR(80) NOT NULL COMMENT '专家名称',
  agent_role VARCHAR(120) NOT NULL COMMENT '专家角色',
  status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED' COMMENT '步骤状态',
  input_summary TEXT COMMENT '输入摘要',
  output_summary TEXT COMMENT '输出摘要',
  findings_json TEXT COMMENT '发现JSON',
  questions_json TEXT COMMENT '追问JSON',
  sources_json TEXT COMMENT '来源JSON',
  started_at DATETIME DEFAULT NULL COMMENT '开始时间',
  completed_at DATETIME DEFAULT NULL COMMENT '完成时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_prep_agent_step (session_id, ai_run_id, step_no),
  KEY idx_project_prep_agent_step_run (session_id, ai_run_id),
  KEY idx_project_prep_agent_step_agent (session_id, agent_key)
) COMMENT='项目准备专家团接力步骤';
