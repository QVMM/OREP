-- 启发 Office 与资源中心的关联，便于迁移/同步时追踪
ALTER TABLE inspire_office_document
  ADD COLUMN resource_id INT NULL COMMENT '资源中心 resource.id' AFTER team_id,
  ADD KEY idx_inspire_office_resource (resource_id);
