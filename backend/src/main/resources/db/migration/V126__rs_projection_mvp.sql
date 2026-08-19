-- 竞赛大脑 MVP Block 0：8 张表。
-- Evidence→Claim→Assessment(按需) / ClaimRelation→PageIntent→ProjectionRun→ProjectionPage
-- ProjectionRun = 一次执行记录，不是第七层对象。
-- ProjectionPage = 页结果 + Expression + compact Decision 的物化，禁止另建 rs_expression。

CREATE TABLE IF NOT EXISTS rs_evidence (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id            BIGINT NOT NULL,
  source_url            VARCHAR(1024) DEFAULT NULL,
  file_id               BIGINT DEFAULT NULL,
  source_title          VARCHAR(255) NOT NULL,
  source_date           DATE DEFAULT NULL,
  original_quote        TEXT NOT NULL,
  extracted_fact        TEXT NOT NULL,
  metric_json           JSON DEFAULT NULL,
  verification_status   VARCHAR(16) NOT NULL DEFAULT 'draft',
  category              VARCHAR(32) DEFAULT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_rs_evidence_project (project_id, verification_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='事实证据；已核验≠命题已被证明';

CREATE TABLE IF NOT EXISTS rs_claim (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id            BIGINT NOT NULL,
  stable_id             VARCHAR(64) NOT NULL,
  proposition           TEXT NOT NULL,
  status                VARCHAR(16) NOT NULL DEFAULT 'draft',
  category              VARCHAR(32) DEFAULT NULL,
  rank_factors_json     JSON DEFAULT NULL,
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_rs_claim_project_stable (project_id, stable_id),
  KEY idx_rs_claim_project_status (project_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='瘦命题。ready=可进候选，不是已被证明。禁止 slide_line/sufficiency';

CREATE TABLE IF NOT EXISTS rs_claim_evidence (
  claim_id              BIGINT NOT NULL,
  evidence_id           BIGINT NOT NULL,
  PRIMARY KEY (claim_id, evidence_id),
  KEY idx_rs_ce_evidence (evidence_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='命题—证据多对多';

CREATE TABLE IF NOT EXISTS rs_claim_relation (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id            BIGINT NOT NULL,
  from_claim_id         BIGINT NOT NULL,
  to_claim_id           BIGINT NOT NULL,
  type                  VARCHAR(32) NOT NULL,
  UNIQUE KEY uk_rs_rel (from_claim_id, to_claim_id, type),
  KEY idx_rs_rel_project (project_id, type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='supports/contradicts/responds_to/bridges_to/depends_on/refines';

CREATE TABLE IF NOT EXISTS rs_assessment (
  id                          BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id                  BIGINT NOT NULL,
  claim_id                    BIGINT NOT NULL,
  rubric_id                   VARCHAR(128) NOT NULL,
  strength                    TINYINT NOT NULL,
  verifiability               TINYINT NOT NULL,
  chi                         TINYINT NOT NULL,
  status                      VARCHAR(16) NOT NULL DEFAULT 'suggested',
  created_by_run_id           BIGINT DEFAULT NULL,
  created_by_page_intent_id   VARCHAR(64) NOT NULL,
  created_for_rubric_id       VARCHAR(128) NOT NULL,
  created_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_rs_assess_claim_rubric (claim_id, rubric_id),
  KEY idx_rs_assess_project (project_id),
  KEY idx_rs_assess_run (created_by_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='按需 Assessment。created_by_* 记首次进入候选的原因，禁止全矩阵';

CREATE TABLE IF NOT EXISTS rs_page_intent (
  id                    VARCHAR(64) PRIMARY KEY,
  profile_id            VARCHAR(64) NOT NULL,
  page_index            INT NOT NULL,
  role                  VARCHAR(64) NOT NULL,
  spec_json             JSON NOT NULL,
  UNIQUE KEY uk_rs_intent_profile_page (profile_id, page_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='页面任务种子。老师本 MVP 不建 Intent';

CREATE TABLE IF NOT EXISTS rs_projection_run (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_id            BIGINT NOT NULL,
  profile_id            VARCHAR(64) NOT NULL,
  config_version        VARCHAR(32) NOT NULL,
  status                VARCHAR(16) NOT NULL DEFAULT 'done',
  created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_rs_run_project (project_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='一次投影执行记录，不是对象层';

CREATE TABLE IF NOT EXISTS rs_projection_page (
  id                    BIGINT PRIMARY KEY AUTO_INCREMENT,
  run_id                BIGINT NOT NULL,
  page_index            INT NOT NULL,
  intent_id             VARCHAR(64) NOT NULL,
  selected_claim_ids_json JSON NOT NULL,
  expression_slide_text TEXT,
  expression_speaking   TEXT,
  expression_task_focus VARCHAR(32) DEFAULT NULL,
  hard_success_pass     TINYINT NOT NULL DEFAULT 0,
  soft_success_status   VARCHAR(16) NOT NULL DEFAULT 'pending',
  page_status           VARCHAR(16) NOT NULL,
  block_reason          VARCHAR(255) DEFAULT NULL,
  decision_compact_json JSON NOT NULL,
  UNIQUE KEY uk_rs_page_run (run_id, page_index),
  KEY idx_rs_page_intent (intent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='页结果+Expression+compact Decision。禁止拆 rs_expression';

INSERT INTO rs_page_intent (id, profile_id, page_index, role, spec_json) VALUES
('intent_urgency', 'contest_1h_slice_news', 4, 'urgency',
 JSON_OBJECT(
   'required_impact_min', 4,
   'required_ostensible_min', 4,
   'budget', 1,
   'related_rubrics', JSON_ARRAY('实用性'),
   'forbid_tech', true,
   'require_bridge', false
 )),
('intent_bridge', 'contest_1h_slice_news', 5, 'bridge',
 JSON_OBJECT(
   'required_impact_min', 0,
   'required_ostensible_min', 0,
   'budget', 1,
   'related_rubrics', JSON_ARRAY('实用性'),
   'forbid_tech', true,
   'require_bridge', true
 ));
