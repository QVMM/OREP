CREATE TABLE IF NOT EXISTS student_learning_session (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    team_id BIGINT NULL,
    activity_type VARCHAR(32) NOT NULL COMMENT 'COURSE, EXAM, ROADSHOW, COLLABORATION',
    source_type VARCHAR(64) NOT NULL,
    source_id BIGINT NULL,
    started_at DATETIME NOT NULL,
    ended_at DATETIME NULL,
    duration_seconds INT NOT NULL DEFAULT 0,
    metadata_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_learning_session_source (user_id, source_type, source_id),
    KEY idx_learning_session_user_time (tenant_id, user_id, started_at),
    KEY idx_learning_session_team_time (tenant_id, team_id, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_certificate (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    title VARCHAR(160) NOT NULL,
    certificate_type VARCHAR(32) NOT NULL DEFAULT 'PERSONAL',
    description TEXT NULL,
    issuer_user_id BIGINT NOT NULL,
    issued_at DATETIME NOT NULL,
    certificate_no VARCHAR(64) NULL,
    pdf_url VARCHAR(1000) NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_certificate_no (certificate_no),
    KEY idx_certificate_tenant_time (tenant_id, issued_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_certificate_recipient (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    certificate_id BIGINT NOT NULL,
    recipient_type VARCHAR(16) NOT NULL COMMENT 'USER or TEAM',
    user_id BIGINT NULL,
    team_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_certificate_user (certificate_id, user_id),
    UNIQUE KEY uk_certificate_team (certificate_id, team_id),
    KEY idx_certificate_recipient_user (user_id),
    KEY idx_certificate_recipient_team (team_id),
    CONSTRAINT fk_certificate_recipient_certificate
        FOREIGN KEY (certificate_id) REFERENCES student_certificate(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_rectification (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL,
    title VARCHAR(160) NOT NULL,
    description TEXT NULL,
    requirement_text TEXT NULL,
    issuer_user_id BIGINT NOT NULL,
    issued_at DATETIME NOT NULL,
    due_at DATETIME NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    related_task_id BIGINT NULL,
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_rectification_tenant_status (tenant_id, status, due_at),
    KEY idx_rectification_task (related_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS student_rectification_recipient (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rectification_id BIGINT NOT NULL,
    recipient_type VARCHAR(16) NOT NULL COMMENT 'USER or TEAM',
    user_id BIGINT NULL,
    team_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_rectification_user (rectification_id, user_id),
    UNIQUE KEY uk_rectification_team (rectification_id, team_id),
    KEY idx_rectification_recipient_user (user_id),
    KEY idx_rectification_recipient_team (team_id),
    CONSTRAINT fk_rectification_recipient_rectification
        FOREIGN KEY (rectification_id) REFERENCES student_rectification(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
