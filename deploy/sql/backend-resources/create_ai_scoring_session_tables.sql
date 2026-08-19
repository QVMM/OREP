CREATE TABLE IF NOT EXISTS ai_scoring_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_no VARCHAR(64) NOT NULL UNIQUE,
  source_type VARCHAR(32) NOT NULL,
  source_id BIGINT NULL,
  project_id BIGINT NULL,
  team_id BIGINT NULL,
  meeting_id BIGINT NULL,
  recording_id BIGINT NULL,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(128) NOT NULL,
  rubric_id VARCHAR(128) NOT NULL,
  rubric_internal_version VARCHAR(64) NOT NULL,
  rubric_hash VARCHAR(128) NOT NULL,
  evidence_schema_id BIGINT NULL,
  evidence_schema_version VARCHAR(64) NULL,
  speaker_attribution_revision INT NULL,
  speaker_attribution_status VARCHAR(24) NULL,
  speaker_attribution_contract_version VARCHAR(64) NULL,
  speaker_attribution_clock_id VARCHAR(160) NULL,
  speaker_attribution_snapshot_hash VARCHAR(80) NULL,
  scoring_fingerprint VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL,
  current_stage VARCHAR(64) NULL,
  progress_percent INT NOT NULL DEFAULT 0,
  use_history_memory TINYINT NOT NULL DEFAULT 1,
  jury_enabled TINYINT NOT NULL DEFAULT 0,
  report_id BIGINT NULL,
  error_message TEXT NULL,
  created_by BIGINT NULL,
  started_at DATETIME NULL,
  completed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_ai_scoring_session_meeting (meeting_id),
  INDEX idx_ai_scoring_session_team_project (project_id, team_id),
  INDEX idx_ai_scoring_session_status (status),
  INDEX idx_ai_scoring_session_upload_queue (created_by, source_type, created_at, id),
  INDEX idx_ai_scoring_session_fingerprint (scoring_fingerprint)
);

CREATE TABLE IF NOT EXISTS track_rubric_config (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(128) NOT NULL,
  rubric_id VARCHAR(128) NOT NULL,
  internal_version VARCHAR(64) NOT NULL,
  rubric_hash VARCHAR(128) NOT NULL,
  rubric_path VARCHAR(512) NOT NULL,
  status VARCHAR(32) NOT NULL,
  active_slot VARCHAR(128) NOT NULL,
  effective_from DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_track_active_slot (track_id, active_slot),
  INDEX idx_track_rubric_status (track_id, status)
);

CREATE TABLE IF NOT EXISTS track_evidence_schema (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(128) NOT NULL,
  schema_version VARCHAR(64) NOT NULL,
  schema_hash VARCHAR(128) NOT NULL,
  material_types_json JSON NOT NULL,
  frame_targets_json JSON NOT NULL,
  demo_actions_json JSON NOT NULL,
  risk_patterns_json JSON NOT NULL,
  third_party_packaging_signals_json JSON NOT NULL,
  acceptable_evidence_levels_json JSON NOT NULL,
  status VARCHAR(32) NOT NULL,
  active_slot VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_track_evidence_active_slot (track_id, active_slot),
  INDEX idx_track_evidence_schema_track (track_id, status)
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-c889f0110e2d',
  '人工智能赛道',
  'rubric-track-c889f0110e2d-v1.2',
  'v1.2',
  '3e91ee0f9b409862a403c8b1c766d49251ed89cfb75cfcaca0f49476ea390be7',
  '42赛道梯度评分规则v1.2-证据审查版/人工智能赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-c889f0110e2d' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-3393b28e46a3',
  '健康养老与婴幼儿托育赛道',
  'rubric-track-3393b28e46a3-v1.2',
  'v1.2',
  '965e417b4abcf7da28225a1befc0d0d2aaea7d2f2fbbad23b16a9b5c570ef49b',
  '42赛道梯度评分规则v1.2-证据审查版/健康养老与婴幼儿托育赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-3393b28e46a3' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-ea14884d6f52',
  '公共安全、管理与服务赛道',
  'rubric-track-ea14884d6f52-v1.2',
  'v1.2',
  'd6a2573a92ed9e052817464740739697e13dbb01040238020d0be85780b7321e',
  '42赛道梯度评分规则v1.2-证据审查版/公共安全、管理与服务赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-ea14884d6f52' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-3ea1635a85f1',
  '化工技术赛道',
  'rubric-track-3ea1635a85f1-v1.2',
  'v1.2',
  '65c9bb51fa907b05d0e9bc230ac2204e7155e7fa0b4e0be0d12390c7b6bdba25',
  '42赛道梯度评分规则v1.2-证据审查版/化工技术赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-3ea1635a85f1' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-medical-technology',
  '医学技术赛道',
  'rubric-track-medical-technology-v1.2',
  'v1.2',
  'f842443d2ad71c5aabff55266bb962302bdb46378457c3e44f00ce95a332255b',
  '42赛道梯度评分规则v1.2-证据审查版/医学技术赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-medical-technology' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-4f826b7a9c24',
  '医疗器械制造与运维赛道',
  'rubric-track-4f826b7a9c24-v1.2',
  'v1.2',
  '9047012529f178518fa901390a6e36f505c9486fc3a0dc04c596a50b1fa9f495',
  '42赛道梯度评分规则v1.2-证据审查版/医疗器械制造与运维赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-4f826b7a9c24' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-8b603920897f',
  '医药生产与经营赛道',
  'rubric-track-8b603920897f-v1.2',
  'v1.2',
  'cc4f680db04f1090af94b40745187f80c845d08e4c9a93b095ad5de29ef84ca5',
  '42赛道梯度评分规则v1.2-证据审查版/医药生产与经营赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-8b603920897f' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-ed3d87701522',
  '商贸赛道',
  'rubric-track-ed3d87701522-v1.2',
  'v1.2',
  '4715618b877697511ac71f22faa6f471c0e46932001655464e11bb7d72f17e9d',
  '42赛道梯度评分规则v1.2-证据审查版/商贸赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-ed3d87701522' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-99e599dd7dc5',
  '土木建筑施工赛道',
  'rubric-track-99e599dd7dc5-v1.2',
  'v1.2',
  'd458423c888d8b5d7155483da4fb98d2ab51ee96df5fcb2b3803a01eb98a0cec',
  '42赛道梯度评分规则v1.2-证据审查版/土木建筑施工赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-99e599dd7dc5' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-7360fa996273',
  '土木建筑设计与管理赛道',
  'rubric-track-7360fa996273-v1.2',
  'v1.2',
  '4a3dc012024cee7e5aa5d34e78a0aa21608d874915740bf31299b3352ee30d2d',
  '42赛道梯度评分规则v1.2-证据审查版/土木建筑设计与管理赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-7360fa996273' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-3357e6f34ee7',
  '地质勘察与地理测绘赛道',
  'rubric-track-3357e6f34ee7-v1.2',
  'v1.2',
  '6a803b6fc071e0eef6e1b034073f4b6c9b0357cfc7539b49c1d0ab4da8b14dbc',
  '42赛道梯度评分规则v1.2-证据审查版/地质勘察与地理测绘赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-3357e6f34ee7' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-a30566591ce2',
  '康复治疗与护理赛道',
  'rubric-track-a30566591ce2-v1.2',
  'v1.2',
  '91f3eee3a1142582aa48c6408d5ba84b47f530068ecf8434cdf9229f2c29754e',
  '42赛道梯度评分规则v1.2-证据审查版/康复治疗与护理赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-a30566591ce2' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-25f4270d0226',
  '教育与体育赛道',
  'rubric-track-25f4270d0226-v1.2',
  'v1.2',
  '6c57d2f16f2a50f6927cb4dcca7870fbeed50413628ad26611a02f8f942f9b2b',
  '42赛道梯度评分规则v1.2-证据审查版/教育与体育赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-25f4270d0226' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-it',
  '新一代信息技术赛道',
  'rubric-track-it-v1.2',
  'v1.2',
  'fb841b22320c310400d5d2125051fccfa9d1bce257ddff75463ec7cb8a66bc03',
  '42赛道梯度评分规则v1.2-证据审查版/新一代信息技术赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-it' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-c6708705cc12',
  '新闻传播赛道',
  'rubric-track-c6708705cc12-v1.2',
  'v1.2',
  '6ed6d0041b0083e734cd8d8d4b8461d19dfa0fb2907dbfc837289505128bafea',
  '42赛道梯度评分规则v1.2-证据审查版/新闻传播赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-c6708705cc12' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-687a86f9028e',
  '旅游赛道',
  'rubric-track-687a86f9028e-v1.2',
  'v1.2',
  '78e4778af78c30b2395b4230e3ec218ee39253ccf7ef6a24e26e68eabc900226',
  '42赛道梯度评分规则v1.2-证据审查版/旅游赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-687a86f9028e' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-08ab795b0bfd',
  '智能装备应用赛道',
  'rubric-track-08ab795b0bfd-v1.2',
  'v1.2',
  '1f3837ea3669d2b070f9d9b3a47688faf8cda428d0f5acc6ea02ee9de3310b36',
  '42赛道梯度评分规则v1.2-证据审查版/智能装备应用赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-08ab795b0bfd' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-97d1a0e91c0f',
  '机械设计与制造赛道',
  'rubric-track-97d1a0e91c0f-v1.2',
  'v1.2',
  'a99520d210f5b29f80e46190fde059c99b6f666f7c867d20bff70d2b657155af',
  '42赛道梯度评分规则v1.2-证据审查版/机械设计与制造赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-97d1a0e91c0f' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-d990bf7ee380',
  '机电设备安装与运维赛道',
  'rubric-track-d990bf7ee380-v1.2',
  'v1.2',
  'e50b217359977b830a1be1ede0adb875dc0cbe8e678c588fe60749fa1533668e',
  '42赛道梯度评分规则v1.2-证据审查版/机电设备安装与运维赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-d990bf7ee380' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-4059c428f2ed',
  '材料赛道',
  'rubric-track-4059c428f2ed-v1.2',
  'v1.2',
  '0d90b4320507dc823901c4406cec40f545efc8c3879d1db4d018ed4a3292917e',
  '42赛道梯度评分规则v1.2-证据审查版/材料赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-4059c428f2ed' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-7c8f9dfb6c2b',
  '林业赛道',
  'rubric-track-7c8f9dfb6c2b-v1.2',
  'v1.2',
  'f1536ce061d0bbd62a0bcd19dde7ccf48cb69f78985a4d2a4b50d04a6db29239',
  '42赛道梯度评分规则v1.2-证据审查版/林业赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-7c8f9dfb6c2b' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-4905e18c469f',
  '水利赛道',
  'rubric-track-4905e18c469f-v1.2',
  'v1.2',
  '713850a004c7fdca979af0f3532d5f0b2ac81e77bfa7acb0b0b61593577930c7',
  '42赛道梯度评分规则v1.2-证据审查版/水利赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-4905e18c469f' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-f48337e2f035',
  '汽车制造与维修赛道',
  'rubric-track-f48337e2f035-v1.2',
  'v1.2',
  '4373a7329a1879ebd00a4d96313243670f6faa21d899dee0e980c89663407da9',
  '42赛道梯度评分规则v1.2-证据审查版/汽车制造与维修赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-f48337e2f035' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-4f28232b4b81',
  '物流与供应链赛道',
  'rubric-track-4f28232b4b81-v1.2',
  'v1.2',
  'adca68c34acd09ae705e5f6ed86b5fe6fd2fed6b4d12933a4ccaabedbe43e8e6',
  '42赛道梯度评分规则v1.2-证据审查版/物流与供应链赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-4f28232b4b81' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-a00c6482aa3e',
  '现代农业赛道',
  'rubric-track-a00c6482aa3e-v1.2',
  'v1.2',
  'c9de29c1ab97b486f4a23247be1558fed5e61f7c0f2316739645916aee07c545',
  '42赛道梯度评分规则v1.2-证据审查版/现代农业赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-a00c6482aa3e' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-8a889b6d8a57',
  '生态保护与环境治理赛道',
  'rubric-track-8a889b6d8a57-v1.2',
  'v1.2',
  '61111d561c180ed905c546b0368edcfaa2ffb1432b1ee9a2e6db0bc5e3c6f625',
  '42赛道梯度评分规则v1.2-证据审查版/生态保护与环境治理赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-8a889b6d8a57' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-2bf1f62d9f86',
  '生物技术赛道',
  'rubric-track-2bf1f62d9f86-v1.2',
  'v1.2',
  '7bc075bb13fe2cf6b6b85635e5e201fecc33e33c55e67af983bba96b34a111a4',
  '42赛道梯度评分规则v1.2-证据审查版/生物技术赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-2bf1f62d9f86' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-15c928b76a9d',
  '电子电器与集成电路赛道',
  'rubric-track-15c928b76a9d-v1.2',
  'v1.2',
  '6c976242c3f4617dc7ca6e49ed169cba7c2f9b6e0a6d3646f4b554cc3653b865',
  '42赛道梯度评分规则v1.2-证据审查版/电子电器与集成电路赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-15c928b76a9d' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-0fb8aa91cd88',
  '畜牧与水产赛道',
  'rubric-track-0fb8aa91cd88-v1.2',
  'v1.2',
  'c2409bcbeb313ddacb261c8651a1ce60b5a2fa00dbfb5ff5df9b862785ed1efd',
  '42赛道梯度评分规则v1.2-证据审查版/畜牧与水产赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-0fb8aa91cd88' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-edb04e8025df',
  '纺织服装赛道',
  'rubric-track-edb04e8025df-v1.2',
  'v1.2',
  'ebda5499b79de67c9d81a83f441637af0203b878716ab44ba483d4bb7c94b278',
  '42赛道梯度评分规则v1.2-证据审查版/纺织服装赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-edb04e8025df' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-b879be45bbb5',
  '能源动力赛道',
  'rubric-track-b879be45bbb5-v1.2',
  'v1.2',
  '13fd18758c48597927809ba753031c9b1ffc548b39848144069e186899a5634e',
  '42赛道梯度评分规则v1.2-证据审查版/能源动力赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-b879be45bbb5' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-452af63b2dcf',
  '航空交通运输赛道',
  'rubric-track-452af63b2dcf-v1.2',
  'v1.2',
  '6592cb196a0aa72956d8d5c090a50d81897061268d874b47f22601122c23c095',
  '42赛道梯度评分规则v1.2-证据审查版/航空交通运输赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-452af63b2dcf' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-a61007fe5ef9',
  '船舶交通运输赛道',
  'rubric-track-a61007fe5ef9-v1.2',
  'v1.2',
  '2d0c809750a1ce736fa0432abd31f5a9ee810486babc0263ff67b1f604139632',
  '42赛道梯度评分规则v1.2-证据审查版/船舶交通运输赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-a61007fe5ef9' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-f1873e627bc9',
  '艺术设计赛道',
  'rubric-track-f1873e627bc9-v1.2',
  'v1.2',
  '7c67ac5b62c9a0361717eaabc90fb3507795538e74bc7c2c3d715e36009448dc',
  '42赛道梯度评分规则v1.2-证据审查版/艺术设计赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-f1873e627bc9' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-0a28058b7b90',
  '表演艺术赛道',
  'rubric-track-0a28058b7b90-v1.2',
  'v1.2',
  '2caedaba28caf4b1f5b55098365ce74ebf6887073fc2a81a5a649c700256e00e',
  '42赛道梯度评分规则v1.2-证据审查版/表演艺术赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-0a28058b7b90' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-7a3e02bcbaf6',
  '财经赛道',
  'rubric-track-7a3e02bcbaf6-v1.2',
  'v1.2',
  '2218000cdf9e86c628c2e0263b81811b081226bbb558691ee5d3a92acfc8120b',
  '42赛道梯度评分规则v1.2-证据审查版/财经赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-7a3e02bcbaf6' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-5996390346dd',
  '资源开采赛道',
  'rubric-track-5996390346dd-v1.2',
  'v1.2',
  'f9046fa888114a5fb7aad1dba50f4c62e08c1536a499cbc1c1a6e5b33a4c6da9',
  '42赛道梯度评分规则v1.2-证据审查版/资源开采赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-5996390346dd' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-6d10f0113d8d',
  '轨道交通运输赛道',
  'rubric-track-6d10f0113d8d-v1.2',
  'v1.2',
  '9573a3f40265795557918ced316378d465d37af2569f5ce72a5d6e73f68b0886',
  '42赛道梯度评分规则v1.2-证据审查版/轨道交通运输赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-6d10f0113d8d' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-3d0395ca595d',
  '轻工赛道',
  'rubric-track-3d0395ca595d-v1.2',
  'v1.2',
  '293f0965daa7466077f2481a2ced1178f0f1b2b0af4867d115672d5c75e57b32',
  '42赛道梯度评分规则v1.2-证据审查版/轻工赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-3d0395ca595d' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-7a41d18ae0c4',
  '道路与管道运输赛道',
  'rubric-track-7a41d18ae0c4-v1.2',
  'v1.2',
  '0185eb3ebb0474ba82e435f25ad0a45ba25cc43d33dc5f76d431247db808bbd6',
  '42赛道梯度评分规则v1.2-证据审查版/道路与管道运输赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-7a41d18ae0c4' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-f0734338087e',
  '食品与粮食赛道',
  'rubric-track-f0734338087e-v1.2',
  'v1.2',
  'e23d47a8ba799943adc8ece3d1ed162bd02ce1150d2d8abc4ca162ab99d72a76',
  '42赛道梯度评分规则v1.2-证据审查版/食品与粮食赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-f0734338087e' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_rubric_config (
  track_id, track_name, rubric_id, internal_version, rubric_hash, rubric_path,
  status, active_slot, effective_from
)
SELECT
  'track-catering',
  '餐饮赛道',
  'rubric-track-catering-v1.2',
  'v1.2',
  '5a998ccb56da23344686b587d6fe0b756c1f8c1664ce4dc6b3c9c2dfdaf08952',
  '42赛道梯度评分规则v1.2-证据审查版/餐饮赛道.md',
  'active',
  'ACTIVE',
  NOW()
WHERE NOT EXISTS (
  SELECT 1 FROM track_rubric_config
  WHERE track_id = 'track-catering' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_evidence_schema (
  track_id, track_name, schema_version, schema_hash,
  material_types_json, frame_targets_json, demo_actions_json, risk_patterns_json,
  third_party_packaging_signals_json, acceptable_evidence_levels_json,
  status, active_slot
)
SELECT
  'track-it',
  '新一代信息技术赛道',
  'v1.2',
  '5ab131370721a52aaf82b40bf938abe61393e9aba5c2b96bc6529c9f2cd90cbe',
  JSON_ARRAY('技术架构图', '代码仓库', '系统演示视频', '数据与实验记录', '现场演示稳定性记录'),
  JSON_ARRAY('代码/系统演示', '技术架构', '数据与实验', '现场演示稳定性'),
  JSON_ARRAY('运行核心业务流程', '展示关键代码与模块映射', '复现实验数据结论', '现场演示稳定性验证'),
  JSON_ARRAY('模板套壳', '第三方系统二次包装', '低代码平台替代核心实现', '演示功能找不到代码对应'),
  JSON_ARRAY('公开模板结构高度相似', '比赛前一次性导入大量代码', '账号或域名指向第三方 SaaS'),
  JSON_ARRAY('代码与演示功能可对应', '架构说明能解释核心实现', '数据与实验记录可复核', '现场演示稳定性达到核心流程连续完成'),
  'active',
  'ACTIVE'
WHERE NOT EXISTS (
  SELECT 1 FROM track_evidence_schema
  WHERE track_id = 'track-it' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_evidence_schema (
  track_id, track_name, schema_version, schema_hash,
  material_types_json, frame_targets_json, demo_actions_json, risk_patterns_json,
  third_party_packaging_signals_json, acceptable_evidence_levels_json,
  status, active_slot
)
SELECT
  'track-medical-technology',
  '医学技术赛道',
  'v1.2',
  '892447bfcb876448a41802eabe8370754d56f818eb8a02da3b30e6f5a778586b',
  JSON_ARRAY('临床/适用场景说明', '伦理合规材料', '实验验证记录', '安全风险清单', '转化路径计划'),
  JSON_ARRAY('临床/适用场景', '伦理合规', '实验验证', '安全风险', '转化路径'),
  JSON_ARRAY('说明适用边界', '展示实验或质控流程', '复核风险控制步骤', '解释转化路径里程碑'),
  JSON_ARRAY('缺少伦理合规说明', '实验验证无法复核', '夸大临床效果', '安全风险未闭环'),
  JSON_ARRAY('机构能力被包装成团队项目', '设备自动输出被包装成学生能力', '临床背书替代项目证据'),
  JSON_ARRAY('临床/适用场景边界清晰', '伦理合规材料完整', '实验验证可追溯', '安全风险有控制方案', '转化路径可执行'),
  'active',
  'ACTIVE'
WHERE NOT EXISTS (
  SELECT 1 FROM track_evidence_schema
  WHERE track_id = 'track-medical-technology' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_evidence_schema (
  track_id, track_name, schema_version, schema_hash,
  material_types_json, frame_targets_json, demo_actions_json, risk_patterns_json,
  third_party_packaging_signals_json, acceptable_evidence_levels_json,
  status, active_slot
)
SELECT
  'track-catering',
  '餐饮赛道',
  'v1.2',
  '1a86b4e7dd35b4ee03f79c8c5a25530c21aab56389dfbbb6228f3e51f7e247d2',
  JSON_ARRAY('产品制作流程记录', '食品安全台账', '成本毛利表', '服务运营记录', '现场出品一致性记录'),
  JSON_ARRAY('产品制作流程', '食品安全', '成本毛利', '服务运营', '现场出品一致性'),
  JSON_ARRAY('现场完成关键制作步骤', '展示温控留样记录', '核算单品成本毛利', '说明服务运营排班与动线'),
  JSON_ARRAY('预制成品冒充现场制作', '食品安全记录后补', '成本毛利无法对应', '现场出品一致性不足'),
  JSON_ARRAY('外购成品包装', '文化故事替代制作技能', '加盟供应链能力被包装成团队能力'),
  JSON_ARRAY('产品制作流程可现场复现', '食品安全记录完整', '成本毛利测算可核验', '服务运营有过程证据', '现场出品一致性稳定'),
  'active',
  'ACTIVE'
WHERE NOT EXISTS (
  SELECT 1 FROM track_evidence_schema
  WHERE track_id = 'track-catering' AND status = 'active' AND active_slot = 'ACTIVE'
);

INSERT INTO track_evidence_schema (
  track_id, track_name, schema_version, schema_hash,
  material_types_json, frame_targets_json, demo_actions_json, risk_patterns_json,
  third_party_packaging_signals_json, acceptable_evidence_levels_json,
  status, active_slot
)
SELECT
  'track-ed3d87701522',
  '商贸赛道',
  'v1.2',
  '491dcb2f8f0f2d9389fc2fbd44e30bd58ab6cf198d2df20561d7fe3a8aaf3c1a',
  JSON_ARRAY('商业模式说明', '交易流程记录', '客户调研与订单证据', '供应链与库存记录', '成本收益测算表', '营销运营数据'),
  JSON_ARRAY('商品/服务展示', '交易流程', '客户需求验证', '供应链履约', '成本收益', '营销运营'),
  JSON_ARRAY('演示从获客到下单的完整流程', '展示客户需求或订单证据', '核算单品/单客成本收益', '说明供应链履约与库存周转', '复盘营销转化数据'),
  JSON_ARRAY('只讲商业故事但缺少交易证据', '订单或客户数据无法核验', '成本收益测算口径不清', '供应链履约风险未说明', '把第三方平台能力包装为团队经营能力'),
  JSON_ARRAY('套用电商模板无真实商品/服务闭环', '用平台后台截图替代自有经营数据', '供应商能力被包装成团队能力', '虚构订单或客户访谈', '只展示宣传页不展示交易过程'),
  JSON_ARRAY('商业模式与交易流程闭环清晰', '客户需求和订单证据可核验', '成本收益测算口径一致', '供应链履约过程可追溯', '营销运营数据能支撑结论'),
  'active',
  'ACTIVE'
WHERE NOT EXISTS (
  SELECT 1 FROM track_evidence_schema
  WHERE track_id = 'track-ed3d87701522' AND status = 'active' AND active_slot = 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS ai_score_evidence_snapshot (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  media_asset_hash VARCHAR(128) NULL,
  asr_snapshot_hash VARCHAR(128) NULL,
  frame_snapshot_hash VARCHAR(128) NULL,
  ocr_snapshot_hash VARCHAR(128) NULL,
  material_snapshot_hash VARCHAR(128) NULL,
  history_memory_snapshot_id BIGINT NULL,
  snapshot_status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_evidence_snapshot_session (session_id)
);

CREATE TABLE IF NOT EXISTS ai_score_media_asset (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NULL,
  asset_type VARCHAR(32) NOT NULL,
  source_type VARCHAR(32) NOT NULL,
  file_path VARCHAR(1024) NOT NULL,
  original_name VARCHAR(255) NULL,
  mime_type VARCHAR(128) NULL,
  file_hash VARCHAR(128) NULL,
  size_bytes BIGINT NULL,
  duration_seconds DECIMAL(12, 3) NULL,
  has_audio TINYINT NOT NULL DEFAULT 0,
  has_video TINYINT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL,
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_media_asset_session (session_id),
  INDEX idx_ai_score_media_asset_hash (file_hash),
  INDEX idx_ai_score_media_asset_source (source_type, asset_type)
);

CREATE TABLE IF NOT EXISTS ai_score_media_preprocess_job (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_no VARCHAR(64) NOT NULL UNIQUE,
  session_id BIGINT NULL,
  media_asset_id BIGINT NULL,
  project_id BIGINT NULL,
  team_id BIGINT NULL,
  track_id VARCHAR(128) NULL,
  track_name VARCHAR(255) NULL,
  source_file_path VARCHAR(1024) NOT NULL,
  source_file_size BIGINT NULL,
  source_mime_type VARCHAR(128) NULL,
  target_file_path VARCHAR(1024) NULL,
  target_file_size BIGINT NULL,
  status VARCHAR(32) NOT NULL,
  progress_percent INT NOT NULL DEFAULT 0,
  error_message VARCHAR(1024) NULL,
  use_history_memory TINYINT NOT NULL DEFAULT 1,
  jury_enabled TINYINT NOT NULL DEFAULT 0,
  created_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  INDEX idx_ai_score_preprocess_job_session (session_id),
  INDEX idx_ai_score_preprocess_job_status (status),
  INDEX idx_ai_score_preprocess_job_creator (created_by)
);

CREATE TABLE IF NOT EXISTS ai_score_transcript_segment (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  media_asset_id BIGINT NULL,
  segment_no INT NOT NULL,
  segment_uid VARCHAR(160) NULL,
  attribution_revision INT NULL,
  speaker_label VARCHAR(128) NULL,
  person_id VARCHAR(160) NULL,
  speaker_state VARCHAR(32) NULL,
  speaker_confidence DECIMAL(7,6) NULL,
  is_final TINYINT(1) NULL,
  start_ms BIGINT NOT NULL,
  end_ms BIGINT NOT NULL,
  text TEXT NOT NULL,
  source_type VARCHAR(32) NOT NULL,
  confidence DECIMAL(5,4) NULL,
  segment_hash VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_transcript_segment_session_no (session_id, segment_no),
  INDEX idx_transcript_segment_session (session_id),
  INDEX idx_transcript_segment_hash (segment_hash),
  UNIQUE KEY uk_ai_score_transcript_segment_uid (session_id, segment_uid)
);

CREATE TABLE IF NOT EXISTS ai_score_speaker_identity (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  raw_speaker_label VARCHAR(128) NULL COMMENT '模型原始声音簇，不可人工覆盖',
  person_id VARCHAR(160) NULL,
  person_type VARCHAR(24) NULL,
  contestant_slot INT NULL,
  display_name VARCHAR(120) NULL,
  role_name VARCHAR(120) NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'AUTO' COMMENT 'AUTO/CONFIRMED/REJECTED',
  source VARCHAR(24) NOT NULL DEFAULT 'MODEL' COMMENT 'MODEL/USER',
  confidence DECIMAL(5,4) NULL,
  revision INT NOT NULL DEFAULT 1,
  person_state VARCHAR(24) NULL,
  first_seen_ms BIGINT NULL,
  last_seen_ms BIGINT NULL,
  voice_cluster_ids_json LONGTEXT NULL,
  updated_by BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_speaker_identity (session_id, raw_speaker_label),
  INDEX idx_ai_score_speaker_identity_session (session_id),
  UNIQUE KEY uk_ai_score_speaker_person (session_id, person_id)
);

CREATE TABLE IF NOT EXISTS ai_score_speaker_turn (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  turn_uid VARCHAR(160) NOT NULL,
  attribution_revision INT NOT NULL,
  start_ms BIGINT NOT NULL,
  end_ms BIGINT NOT NULL,
  person_id VARCHAR(160) NULL,
  speaker_state VARCHAR(32) NOT NULL,
  confidence DECIMAL(7,6) NULL,
  candidate_person_ids_json LONGTEXT NULL,
  source_cluster_id VARCHAR(160) NULL,
  source_visual_identity_id VARCHAR(160) NULL,
  speaker_verification VARCHAR(40) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_speaker_turn (session_id, turn_uid),
  INDEX idx_ai_score_speaker_turn_session (session_id),
  INDEX idx_ai_score_speaker_turn_person (session_id, person_id)
);

CREATE TABLE IF NOT EXISTS ai_score_frame (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  media_asset_id BIGINT NULL,
  frame_no INT NOT NULL,
  timestamp_ms BIGINT NOT NULL,
  frame_path VARCHAR(1024) NULL,
  frame_hash VARCHAR(128) NOT NULL,
  perceptual_hash VARCHAR(128) NULL,
  ocr_text TEXT NULL,
  frame_reason VARCHAR(64) NOT NULL,
  confidence DECIMAL(5,4) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_frame_session_no (session_id, frame_no),
  INDEX idx_ai_score_frame_session (session_id),
  INDEX idx_ai_score_frame_hash (frame_hash)
);

CREATE TABLE IF NOT EXISTS ai_score_evidence_anchor (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  anchor_type VARCHAR(64) NOT NULL,
  anchor_title VARCHAR(255) NOT NULL,
  evidence_text TEXT NOT NULL,
  source_ref VARCHAR(512) NULL,
  transcript_segment_id BIGINT NULL,
  frame_id BIGINT NULL,
  media_asset_id BIGINT NULL,
  start_ms BIGINT NULL,
  end_ms BIGINT NULL,
  confidence DECIMAL(5,4) NULL,
  validity_status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_evidence_anchor_session (session_id),
  INDEX idx_ai_score_evidence_anchor_type (anchor_type),
  INDEX idx_ai_score_evidence_anchor_segment (transcript_segment_id),
  INDEX idx_ai_score_evidence_anchor_frame (frame_id)
);

CREATE TABLE IF NOT EXISTS ai_score_observation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  dimension_name VARCHAR(128) NOT NULL,
  raw_score DECIMAL(6,2) NOT NULL,
  score_cap DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  validity_status VARCHAR(32) NOT NULL,
  model_reason TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_observation_session (session_id),
  INDEX idx_ai_score_observation_report (report_id),
  INDEX idx_ai_score_observation_code (observation_code)
);

CREATE TABLE IF NOT EXISTS ai_score_deduction (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  deduction_id VARCHAR(128) NOT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  deducted_points DECIMAL(6,2) NOT NULL,
  recovered_points DECIMAL(6,2) NOT NULL DEFAULT 0,
  reason TEXT NOT NULL,
  required_fix TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL,
  max_recoverable_points DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  recovery_source_deduction_id VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_deduction_session_id (session_id, deduction_id),
  INDEX idx_ai_score_deduction_report (report_id),
  INDEX idx_ai_score_deduction_observation (observation_code)
);
