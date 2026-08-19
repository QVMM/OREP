ALTER TABLE training_day
    ADD COLUMN content_html LONGTEXT NULL COMMENT '经过服务端清洗的日任务富文本说明' AFTER summary;

CREATE TABLE training_day_attachment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    training_day_id BIGINT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url VARCHAR(700) NOT NULL,
    file_size BIGINT NOT NULL DEFAULT 0,
    mime_type VARCHAR(160) DEFAULT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    created_by BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_training_day_attachment_day (training_day_id, status, sort_order),
    CONSTRAINT fk_training_day_attachment_day FOREIGN KEY (training_day_id) REFERENCES training_day(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='集训日任务独立附件';
