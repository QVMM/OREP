-- OREP AI scoring P7 upgrade: bind evidence schema metadata to scoring sessions.
-- MySQL 8.0 compatible and repeatable.

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

DELIMITER //
CREATE PROCEDURE add_ai_scoring_session_column_if_missing(
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'ai_scoring_session'
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE ai_scoring_session ADD COLUMN ', p_column_name, ' ', p_column_definition);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL add_ai_scoring_session_column_if_missing('evidence_schema_id', 'BIGINT NULL');
CALL add_ai_scoring_session_column_if_missing('evidence_schema_version', 'VARCHAR(64) NULL');

DROP PROCEDURE add_ai_scoring_session_column_if_missing;
