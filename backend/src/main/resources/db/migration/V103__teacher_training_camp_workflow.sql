ALTER TABLE training_day
    ADD COLUMN requirements_json TEXT NULL COMMENT '教师编辑中的交付要求 JSON' AFTER summary;

