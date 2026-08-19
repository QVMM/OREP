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
  response_reason VARCHAR(500) DEFAULT NULL COMMENT '婉拒等响应说明',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='团队成员协调请求';

ALTER TABLE project_task
  ADD COLUMN source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER' COMMENT '任务来源类型',
  ADD COLUMN reviewer_user_id BIGINT DEFAULT NULL COMMENT '指定成果审核人',
  ADD KEY idx_project_task_source_type (source_type),
  ADD KEY idx_project_task_reviewer (reviewer_user_id);

ALTER TABLE project_material
  ADD COLUMN source_submission_id BIGINT DEFAULT NULL COMMENT '来源提交ID',
  ADD COLUMN source_item_key VARCHAR(190) DEFAULT NULL COMMENT '来源成果稳定键',
  ADD UNIQUE KEY uk_project_material_source_item (source_item_key),
  ADD KEY idx_project_material_submission (source_submission_id);
