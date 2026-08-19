CREATE TABLE IF NOT EXISTS project_team (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  name VARCHAR(120) NOT NULL COMMENT '项目团队名称',
  description VARCHAR(500) DEFAULT NULL COMMENT '项目简介',
  track_id VARCHAR(128) DEFAULT NULL COMMENT '赛道ID，对应评分规则',
  track_name VARCHAR(255) DEFAULT NULL COMMENT '赛道完整名称',
  current_stage VARCHAR(40) NOT NULL DEFAULT 'MATERIAL' COMMENT '当前阶段',
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  mentor_id BIGINT DEFAULT NULL COMMENT '指导教师',
  start_date DATE DEFAULT NULL COMMENT '开始日期',
  end_date DATE DEFAULT NULL COMMENT '结束日期',
  created_by BIGINT NOT NULL COMMENT '创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_team_tenant (tenant_id),
  KEY idx_project_team_track (track_id)
) COMMENT='项目团队';

CREATE TABLE IF NOT EXISTS project_team_member (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  role_in_team VARCHAR(32) NOT NULL DEFAULT 'MEMBER' COMMENT '团队内角色',
  position_name VARCHAR(80) DEFAULT NULL COMMENT '岗位名称',
  responsibility VARCHAR(500) DEFAULT NULL COMMENT '职责描述',
  captain_permissions VARCHAR(500) DEFAULT NULL COMMENT '队长权限JSON',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_team_member (team_id, user_id),
  KEY idx_project_team_member_user (user_id)
) COMMENT='项目团队成员';

CREATE TABLE IF NOT EXISTS project_position_role (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  name VARCHAR(80) NOT NULL COMMENT '岗位名称',
  description VARCHAR(300) DEFAULT NULL COMMENT '岗位说明',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_position_role (tenant_id, name),
  KEY idx_project_position_tenant (tenant_id, status)
) COMMENT='项目岗位角色';

CREATE TABLE IF NOT EXISTS project_stage (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  stage_key VARCHAR(40) NOT NULL COMMENT '阶段编码',
  title VARCHAR(80) NOT NULL COMMENT '阶段名称',
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT '状态',
  progress INT NOT NULL DEFAULT 0 COMMENT '进度',
  owner_user_id BIGINT DEFAULT NULL COMMENT '负责人',
  start_date DATE DEFAULT NULL COMMENT '开始日期',
  due_date DATE DEFAULT NULL COMMENT '截止日期',
  is_optional TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否可选阶段',
  suggestion_text VARCHAR(500) DEFAULT NULL COMMENT '阶段说明提示',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_stage (team_id, stage_key)
) COMMENT='项目阶段';

CREATE TABLE IF NOT EXISTS project_task (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  stage_key VARCHAR(40) NOT NULL COMMENT '阶段编码',
  title VARCHAR(160) NOT NULL COMMENT '任务标题',
  description TEXT COMMENT '任务说明',
  owner_user_id BIGINT DEFAULT NULL COMMENT '负责人',
  created_by BIGINT NOT NULL COMMENT '创建人',
  source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER' COMMENT '任务来源类型',
  reviewer_user_id BIGINT DEFAULT NULL COMMENT '指定成果审核人',
  priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' COMMENT '优先级',
  status VARCHAR(32) NOT NULL DEFAULT 'TODO' COMMENT '状态',
  start_at DATETIME DEFAULT NULL COMMENT '开始时间',
  due_at DATETIME DEFAULT NULL COMMENT '截止时间',
  review_required TINYINT NOT NULL DEFAULT 1 COMMENT '是否需要审核',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_task_team (team_id),
  KEY idx_project_task_owner (owner_user_id),
  KEY idx_project_task_source_type (source_type),
  KEY idx_project_task_reviewer (reviewer_user_id)
) COMMENT='项目任务';

CREATE TABLE IF NOT EXISTS project_task_submission (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id BIGINT NOT NULL COMMENT '任务ID',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  submitter_id BIGINT NOT NULL COMMENT '提交人',
  submission_type VARCHAR(60) NOT NULL DEFAULT 'OTHER' COMMENT '成果类型',
  content TEXT COMMENT '提交内容',
  attachment_url VARCHAR(500) DEFAULT NULL COMMENT '附件地址',
  attachment_name VARCHAR(255) DEFAULT NULL COMMENT '附件原始文件名',
  attachment_size BIGINT DEFAULT NULL COMMENT '附件大小',
  attachment_type VARCHAR(120) DEFAULT NULL COMMENT '附件MIME类型',
  sync_to_material TINYINT NOT NULL DEFAULT 1 COMMENT '是否同步到项目材料',
  version_no INT NOT NULL DEFAULT 1 COMMENT '版本号',
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW' COMMENT '审核状态',
  reviewer_id BIGINT DEFAULT NULL COMMENT '审核人',
  review_comment TEXT COMMENT '审核意见',
  source_submission_id BIGINT DEFAULT NULL COMMENT '来源提交ID',
  source_item_key VARCHAR(190) DEFAULT NULL COMMENT '来源成果稳定键',
  reviewed_at DATETIME DEFAULT NULL COMMENT '审核时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  PRIMARY KEY (id),
  KEY idx_project_submission_task (task_id),
  KEY idx_project_submission_team (team_id)
) COMMENT='项目任务提交';

CREATE TABLE IF NOT EXISTS project_submission_asset (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  submission_id BIGINT NOT NULL COMMENT '提交ID',
  task_id BIGINT NOT NULL COMMENT '任务ID',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  asset_kind VARCHAR(40) NOT NULL DEFAULT 'MAIN' COMMENT '资产用途',
  file_url VARCHAR(500) NOT NULL COMMENT '文件地址',
  file_name VARCHAR(255) DEFAULT NULL COMMENT '文件名',
  file_size BIGINT DEFAULT NULL COMMENT '文件大小',
  file_type VARCHAR(120) DEFAULT NULL COMMENT '文件MIME类型',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_submission_asset_submission (submission_id),
  KEY idx_submission_asset_task (task_id),
  KEY idx_submission_asset_team (team_id)
) COMMENT='任务提交文件资产';

CREATE TABLE IF NOT EXISTS project_submission_link (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  submission_id BIGINT NOT NULL COMMENT '提交ID',
  task_id BIGINT NOT NULL COMMENT '任务ID',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  link_type VARCHAR(40) NOT NULL DEFAULT 'OTHER' COMMENT '链接类型',
  title VARCHAR(160) DEFAULT NULL COMMENT '链接标题',
  url VARCHAR(800) NOT NULL COMMENT '链接地址',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_submission_link_submission (submission_id),
  KEY idx_submission_link_task (task_id),
  KEY idx_submission_link_team (team_id)
) COMMENT='任务提交外部链接';

CREATE TABLE IF NOT EXISTS project_task_assignee (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id BIGINT NOT NULL COMMENT '任务ID',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  user_id BIGINT NOT NULL COMMENT '负责人用户ID',
  sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_task_assignee (task_id, user_id),
  KEY idx_project_task_assignee_team (team_id),
  KEY idx_project_task_assignee_user (user_id)
) COMMENT='项目任务多人负责人';

CREATE TABLE IF NOT EXISTS project_material (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  material_type VARCHAR(40) NOT NULL COMMENT '材料类型',
  name VARCHAR(160) NOT NULL COMMENT '材料名称',
  description VARCHAR(500) DEFAULT NULL COMMENT '材料说明',
  owner_user_id BIGINT DEFAULT NULL COMMENT '负责人',
  source_type VARCHAR(40) NOT NULL DEFAULT 'MANUAL' COMMENT '来源',
  file_url VARCHAR(500) DEFAULT NULL COMMENT '文件地址',
  linked_task_id BIGINT DEFAULT NULL COMMENT '关联任务',
  review_status VARCHAR(32) NOT NULL DEFAULT 'DRAFT' COMMENT '审核状态',
  reviewer_id BIGINT DEFAULT NULL COMMENT '审核人',
  review_comment TEXT COMMENT '审核意见',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_material_source_item (source_item_key),
  KEY idx_project_material_team (team_id),
  KEY idx_project_material_submission (source_submission_id)
) COMMENT='项目材料';

CREATE TABLE IF NOT EXISTS collaboration_request (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '协调请求ID',
  tenant_id BIGINT NOT NULL COMMENT '租户ID',
  team_id BIGINT NOT NULL COMMENT '项目团队ID',
  requester_id BIGINT NOT NULL COMMENT '发起人用户ID',
  recipient_id BIGINT NOT NULL COMMENT '接收人用户ID',
  title VARCHAR(160) NOT NULL COMMENT '协调任务标题',
  description VARCHAR(1000) DEFAULT NULL COMMENT '任务说明',
  priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' COMMENT '优先级',
  status VARCHAR(32) NOT NULL DEFAULT 'PENDING' COMMENT '请求状态',
  due_at DATETIME DEFAULT NULL COMMENT '期望截止时间',
  response_reason VARCHAR(500) DEFAULT NULL COMMENT '响应说明',
  linked_task_id BIGINT DEFAULT NULL COMMENT '接受后创建的项目任务ID',
  idempotency_key VARCHAR(120) NOT NULL COMMENT '客户端幂等键',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  responded_at DATETIME DEFAULT NULL COMMENT '响应时间',
  withdrawn_at DATETIME DEFAULT NULL COMMENT '撤回时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_collaboration_request_idempotency (tenant_id, requester_id, idempotency_key),
  UNIQUE KEY uk_collaboration_request_task (linked_task_id),
  KEY idx_collaboration_tenant_team_status (tenant_id, team_id, status),
  KEY idx_collaboration_recipient_status_time (recipient_id, status, created_at),
  KEY idx_collaboration_requester_status_time (requester_id, status, created_at)
) COMMENT='团队成员协调请求';

CREATE TABLE IF NOT EXISTS project_roadshow_binding (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  meeting_id BIGINT NOT NULL COMMENT '会议ID',
  roadshow_type VARCHAR(32) NOT NULL DEFAULT 'REHEARSAL' COMMENT '路演类型',
  created_by BIGINT NOT NULL COMMENT '创建人',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_project_roadshow (team_id, meeting_id)
) COMMENT='项目路演会议绑定';

CREATE TABLE IF NOT EXISTS project_review_issue (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  source_type VARCHAR(40) NOT NULL DEFAULT 'MANUAL' COMMENT '来源',
  source_id BIGINT DEFAULT NULL COMMENT '来源ID',
  category VARCHAR(80) NOT NULL COMMENT '问题分类',
  title VARCHAR(160) NOT NULL COMMENT '问题标题',
  description TEXT COMMENT '问题说明',
  severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' COMMENT '严重程度',
  owner_user_id BIGINT DEFAULT NULL COMMENT '负责人',
  due_at DATETIME DEFAULT NULL COMMENT '截止时间',
  status VARCHAR(32) NOT NULL DEFAULT 'OPEN' COMMENT '状态',
  evidence TEXT COMMENT '解决证明',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_project_review_issue_team (team_id)
) COMMENT='项目复盘问题';

CREATE TABLE IF NOT EXISTS member_ability_snapshot (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  problem_solving INT NOT NULL DEFAULT 0 COMMENT '解决问题能力',
  coding INT NOT NULL DEFAULT 0 COMMENT '代码能力',
  communication INT NOT NULL DEFAULT 0 COMMENT '沟通能力',
  teamwork INT NOT NULL DEFAULT 0 COMMENT '团队协作能力',
  presentation INT NOT NULL DEFAULT 0 COMMENT '演讲能力',
  creativity INT NOT NULL DEFAULT 0 COMMENT '创意能力',
  confidence INT NOT NULL DEFAULT 0 COMMENT '置信度',
  calculated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '计算时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_member_ability_snapshot (team_id, user_id)
) COMMENT='成员能力画像快照';

CREATE TABLE IF NOT EXISTS member_ability_evidence (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  team_id BIGINT NOT NULL COMMENT '团队ID',
  user_id BIGINT NOT NULL COMMENT '用户ID',
  dimension_key VARCHAR(40) NOT NULL COMMENT '能力维度',
  source_type VARCHAR(40) NOT NULL COMMENT '证据来源',
  source_id BIGINT DEFAULT NULL COMMENT '来源ID',
  score INT NOT NULL DEFAULT 0 COMMENT '证据分',
  weight INT NOT NULL DEFAULT 1 COMMENT '权重',
  summary VARCHAR(500) NOT NULL COMMENT '证据摘要',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_member_ability_evidence (team_id, user_id, dimension_key)
) COMMENT='能力画像证据';
