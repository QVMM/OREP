CREATE TABLE IF NOT EXISTS training_day_learning_resource (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    training_day_id BIGINT NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(1000) DEFAULT NULL,
    resource_url VARCHAR(1000) NOT NULL,
    file_name VARCHAR(255) DEFAULT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    mime_type VARCHAR(120) DEFAULT NULL,
    duration_seconds INT NOT NULL DEFAULT 0,
    is_required TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_by BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_training_learning_day (training_day_id, status, sort_order),
    CONSTRAINT fk_training_learning_day
        FOREIGN KEY (training_day_id) REFERENCES training_day(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练日学习内容';

CREATE TABLE IF NOT EXISTS training_learning_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    learning_resource_id BIGINT NOT NULL,
    learned_seconds INT NOT NULL DEFAULT 0,
    actual_learning_seconds INT NOT NULL DEFAULT 0,
    progress_percent INT NOT NULL DEFAULT 0,
    watched_ranges_json TEXT DEFAULT NULL,
    last_position_seconds INT NOT NULL DEFAULT 0,
    video_duration_seconds INT NOT NULL DEFAULT 0,
    heartbeat_session VARCHAR(64) DEFAULT NULL,
    heartbeat_position_seconds INT DEFAULT NULL,
    heartbeat_at DATETIME(3) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED',
    last_learned_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_training_learning_user_resource (user_id, learning_resource_id),
    KEY idx_training_learning_progress_user (user_id, status, updated_at),
    CONSTRAINT fk_training_learning_progress_resource
        FOREIGN KEY (learning_resource_id) REFERENCES training_day_learning_resource(id) ON DELETE RESTRICT,
    CONSTRAINT fk_training_learning_progress_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生训练学习进度';
