ALTER TABLE training_day
    ADD COLUMN early_unlocked_at DATETIME NULL COMMENT '教师提前开放时间，NULL 时按训练日期自动开放' AFTER status;

CREATE INDEX idx_training_day_early_unlocked_at
    ON training_day (early_unlocked_at);
