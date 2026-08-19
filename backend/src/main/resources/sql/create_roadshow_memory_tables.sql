CREATE TABLE IF NOT EXISTS project_assessment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    team_id BIGINT NOT NULL,
    meeting_id BIGINT NOT NULL,
    assessment_round INT NOT NULL,
    assessment_type VARCHAR(32) NOT NULL DEFAULT 'AI_ROADSHOW',
    overall_score DECIMAL(6,2) NULL,
    technical_ceiling_score DECIMAL(6,2) NULL,
    score_calibration_json LONGTEXT NULL,
    evidence_snapshot_json LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_project_assessment_team_meeting (team_id, meeting_id),
    KEY idx_project_assessment_team_round (team_id, assessment_round),
    KEY idx_project_assessment_meeting (meeting_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS score_memory_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    assessment_id BIGINT NOT NULL,
    team_id BIGINT NOT NULL,
    memory_type VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    severity VARCHAR(32) DEFAULT 'MEDIUM',
    status VARCHAR(32) DEFAULT 'OPEN',
    source_round INT NULL,
    resolved_round INT NULL,
    recovered_score DECIMAL(6,2) DEFAULT 0,
    metadata_json LONGTEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_score_memory_team_status (team_id, status),
    KEY idx_score_memory_assessment (assessment_id),
    KEY idx_score_memory_type (memory_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS score_evidence_anchor (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    memory_item_id BIGINT NOT NULL,
    assessment_id BIGINT NOT NULL,
    anchor_type VARCHAR(32) NOT NULL,
    evidence_text TEXT NOT NULL,
    source_ref VARCHAR(255) NULL,
    confidence DECIMAL(5,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_score_evidence_memory (memory_item_id),
    KEY idx_score_evidence_assessment (assessment_id),
    KEY idx_score_evidence_type (anchor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS improvement_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    team_id BIGINT NOT NULL,
    memory_item_id BIGINT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    acceptance_criteria TEXT NULL,
    status VARCHAR(32) DEFAULT 'TODO',
    due_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_improvement_task_team_status (team_id, status),
    KEY idx_improvement_task_memory (memory_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
