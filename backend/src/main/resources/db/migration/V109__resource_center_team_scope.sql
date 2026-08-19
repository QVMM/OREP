ALTER TABLE resource
    ADD COLUMN team_id BIGINT NULL AFTER uploaded_by,
    ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at,
    ADD INDEX idx_resource_team_category_updated (team_id, category, updated_at);

ALTER TABLE resource_category
    ADD COLUMN team_id BIGINT NULL AFTER id,
    ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at,
    ADD INDEX idx_resource_category_team (team_id),
    ADD UNIQUE KEY uk_resource_category_team_label (team_id, label);
