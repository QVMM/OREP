-- =====================================================
-- PPT智能生成系统 数据库表
-- =====================================================

USE orep;

-- 1. 评分规则表 - 存储各领域的评分规则配置
CREATE TABLE IF NOT EXISTS `scoring_rule` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `domain` VARCHAR(64) NOT NULL COMMENT '领域标识 (如: ai_iot, fintech, healthcare)',
    `domain_name` VARCHAR(128) NOT NULL COMMENT '领域名称',
    `rule_name` VARCHAR(128) NOT NULL COMMENT '规则名称',
    `rule_config` JSON NOT NULL COMMENT '规则配置JSON (条件+动作)',
    `priority` INT DEFAULT 0 COMMENT '优先级 (越大越高)',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_by` BIGINT COMMENT '创建者ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_domain` (`domain`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分规则表';

-- 2. PPT问卷表 - 存储用户填写的问卷数据
CREATE TABLE IF NOT EXISTS `ppt_questionnaire` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `tenant_id` BIGINT NOT NULL COMMENT '租户ID',
    `domain` VARCHAR(64) NOT NULL COMMENT '技术领域',
    `project_name` VARCHAR(256) NOT NULL COMMENT '项目名称',
    `team_name` VARCHAR(128) COMMENT '团队名称',
    `responses` JSON NOT NULL COMMENT '问卷回答JSON',
    `enhanced_data` JSON COMMENT '规则引擎增强后的数据',
    `status` VARCHAR(32) DEFAULT 'draft' COMMENT '状态: draft/submitted/enhanced',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_tenant_id` (`tenant_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT问卷表';

-- 3. PPT任务表 - 存储PPT生成任务
CREATE TABLE IF NOT EXISTS `ppt_task` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `user_id` BIGINT NOT NULL COMMENT '用户ID',
    `tenant_id` BIGINT NOT NULL COMMENT '租户ID',
    `questionnaire_id` BIGINT COMMENT '关联问卷ID',
    `project_name` VARCHAR(256) NOT NULL COMMENT '项目名称',
    `team_name` VARCHAR(128) COMMENT '团队名称',
    `domain` VARCHAR(64) NOT NULL COMMENT '技术领域',
    `theme` VARCHAR(64) DEFAULT 'dark_tech' COMMENT '主题风格',
    `outline_json` JSON COMMENT 'DSL v3.0大纲JSON',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '状态: pending/generating/outline_ready/confirmed/rendering/completed/failed',
    `progress` INT DEFAULT 0 COMMENT '生成进度 0-100',
    `current_step` VARCHAR(128) COMMENT '当前步骤描述',
    `pptx_path` VARCHAR(512) COMMENT '生成的PPTX文件路径',
    `error_msg` TEXT COMMENT '错误信息',
    `applied_rules` JSON COMMENT '应用的规则ID列表',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_tenant_id` (`tenant_id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_questionnaire_id` (`questionnaire_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT任务表';

-- 4. PPT模板表 - 存储PPT视觉模板配置
CREATE TABLE IF NOT EXISTS `ppt_template` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL COMMENT '模板名称',
    `theme_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '主题标识',
    `description` TEXT COMMENT '模板描述',
    `preview_url` VARCHAR(512) COMMENT '预览图URL',
    `theme_config` JSON NOT NULL COMMENT '主题配置 (颜色/字体等)',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认模板',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_theme_id` (`theme_id`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT模板表';

-- 5. PPT生成图片表 - 存储AI生成的图片记录
CREATE TABLE IF NOT EXISTS `ppt_generated_image` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联任务ID',
    `page_index` INT NOT NULL COMMENT '页码',
    `image_type` VARCHAR(32) NOT NULL COMMENT '类型: background/decoration/icon',
    `prompt` TEXT COMMENT '生成prompt',
    `image_url` VARCHAR(512) COMMENT '图片URL',
    `local_path` VARCHAR(512) COMMENT '本地存储路径',
    `status` VARCHAR(32) DEFAULT 'pending' COMMENT '状态: pending/generating/completed/failed',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT生成图片表';

-- 6. 问卷表单配置表 - 存储各领域的问卷表单配置
CREATE TABLE IF NOT EXISTS `questionnaire_form_config` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `domain` VARCHAR(64) NOT NULL COMMENT '领域标识',
    `form_name` VARCHAR(128) NOT NULL COMMENT '表单名称',
    `form_schema` JSON NOT NULL COMMENT '表单结构JSON',
    `version` INT DEFAULT 1 COMMENT '版本号',
    `is_active` TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_domain` (`domain`),
    INDEX `idx_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问卷表单配置表';

-- =====================================================
-- 插入默认数据
-- =====================================================

-- 插入默认PPT模板
INSERT INTO `ppt_template` (`name`, `theme_id`, `description`, `theme_config`, `is_default`, `is_active`) VALUES
('暗黑科技风', 'dark_tech', '深色背景，蓝色主色调，适合科技类项目', '{"colors":{"bg":"#0D1117","card_bg":"#161B22","primary":"#4F8CF7","secondary":"#2ECC71","accent":"#F39C12","text_primary":"#FFFFFF","text_secondary":"#B0B0B0","text_muted":"#666666"},"fonts":{"title":{"name":"Microsoft YaHei","fallback":"sans-serif"},"body":{"name":"Microsoft YaHei","fallback":"sans-serif"}}}', 1, 1),
('清新蓝白', 'fresh_blue', '浅色背景，蓝色主题，适合教育类项目', '{"colors":{"bg":"#F5F7FA","card_bg":"#FFFFFF","primary":"#3498DB","secondary":"#27AE60","accent":"#E74C3C","text_primary":"#2C3E50","text_secondary":"#7F8C8D","text_muted":"#BDC3C7"},"fonts":{"title":{"name":"Microsoft YaHei","fallback":"sans-serif"},"body":{"name":"Microsoft YaHei","fallback":"sans-serif"}}}', 0, 1),
('商务简约', 'business', '简洁专业，适合商业路演', '{"colors":{"bg":"#FFFFFF","card_bg":"#F8F9FA","primary":"#2C3E50","secondary":"#18BC9C","accent":"#E67E22","text_primary":"#2C3E50","text_secondary":"#7F8C8D","text_muted":"#BDC3C7"},"fonts":{"title":{"name":"Microsoft YaHei","fallback":"sans-serif"},"body":{"name":"Microsoft YaHei","fallback":"sans-serif"}}}', 0, 1);

-- 插入示例评分规则 (AI+IoT领域)
INSERT INTO `scoring_rule` (`domain`, `domain_name`, `rule_name`, `rule_config`, `priority`, `is_active`) VALUES
('ai_iot', 'AI + 物联网', '路演必备章节', '{"condition":{"field":"report_type","operator":"equals","value":"路演PPT"},"action":{"type":"add_sections","sections":["项目概述","技术方案","商业模式","团队介绍","财务预测"]}}', 10, 1),
('ai_iot', 'AI + 物联网', '含技术指标则添加技术架构图', '{"condition":{"field":"key_metrics","operator":"contains","value":"技术指标"},"action":{"type":"enhance_slide","slide_type":"infographic_flow","title":"技术架构"}}', 5, 1),
('ai_iot', 'AI + 物联网', '详细版增加风险分析', '{"condition":{"field":"detail_level","operator":"equals","value":"详细版"},"action":{"type":"add_sections","sections":["风险分析","竞争优势"]}}', 3, 1);

-- 插入AI+IoT领域问卷表单配置
INSERT INTO `questionnaire_form_config` (`domain`, `form_name`, `form_schema`, `is_active`) VALUES
('ai_iot', 'AI+IoT项目路演问卷', '{
  "sections": [
    {
      "id": "basic_info",
      "title": "基本信息",
      "fields": [
        {"id": "project_name", "label": "项目名称", "type": "text", "required": true},
        {"id": "team_name", "label": "团队名称", "type": "text", "required": true},
        {"id": "tech_direction", "label": "技术方向", "type": "select", "options": ["AI + 物联网", "AI + 医疗", "AI + 教育", "AI + 金融", "其他"], "required": true}
      ]
    },
    {
      "id": "project_core",
      "title": "项目核心",
      "fields": [
        {"id": "core_problem", "label": "解决的核心问题", "type": "textarea", "required": true},
        {"id": "target_users", "label": "目标用户群体", "type": "text", "required": true},
        {"id": "solution", "label": "解决方案概述", "type": "textarea", "required": true}
      ]
    },
    {
      "id": "tech_innovation",
      "title": "技术创新",
      "fields": [
        {"id": "tech_highlights", "label": "技术亮点", "type": "textarea", "required": true},
        {"id": "key_metrics", "label": "关键指标(逗号分隔)", "type": "text", "placeholder": "如: 检测准确率97%, 响应延迟<200ms"},
        {"id": "patents", "label": "专利/软著情况", "type": "text"}
      ]
    },
    {
      "id": "business",
      "title": "商业价值",
      "fields": [
        {"id": "market_size", "label": "市场规模", "type": "text"},
        {"id": "business_model", "label": "商业模式", "type": "textarea"},
        {"id": "competitors", "label": "主要竞争对手", "type": "text"}
      ]
    },
    {
      "id": "team",
      "title": "团队信息",
      "fields": [
        {"id": "team_members", "label": "核心成员(姓名+角色)", "type": "textarea", "required": true},
        {"id": "team_advantage", "label": "团队优势", "type": "textarea"}
      ]
    },
    {
      "id": "output_config",
      "title": "输出配置",
      "fields": [
        {"id": "slide_count", "label": "期望页数", "type": "range", "min": 10, "max": 30, "default": 20},
        {"id": "detail_level", "label": "详细程度", "type": "select", "options": ["精简版", "标准版", "详细版"], "default": "标准版"},
        {"id": "theme", "label": "视觉风格", "type": "select", "options": ["dark_tech", "fresh_blue", "business"], "default": "dark_tech"}
      ]
    }
  ]
}', 1);

-- 插入其他领域表单配置
INSERT INTO `questionnaire_form_config` (`domain`, `form_name`, `form_schema`, `is_active`) VALUES
('fintech', '金融科技项目路演问卷', '{
  "sections": [
    {
      "id": "basic_info",
      "title": "基本信息",
      "fields": [
        {"id": "project_name", "label": "项目名称", "type": "text", "required": true},
        {"id": "team_name", "label": "团队名称", "type": "text", "required": true},
        {"id": "tech_direction", "label": "技术方向", "type": "select", "options": ["区块链", "智能投顾", "风控系统", "支付科技", "其他"], "required": true}
      ]
    },
    {
      "id": "project_core",
      "title": "项目核心",
      "fields": [
        {"id": "core_problem", "label": "解决的金融痛点", "type": "textarea", "required": true},
        {"id": "target_users", "label": "目标客户群体", "type": "text", "required": true},
        {"id": "solution", "label": "解决方案概述", "type": "textarea", "required": true}
      ]
    },
    {
      "id": "compliance",
      "title": "合规与安全",
      "fields": [
        {"id": "compliance_status", "label": "合规资质情况", "type": "textarea"},
        {"id": "security_measures", "label": "安全措施", "type": "textarea"},
        {"id": "data_privacy", "label": "数据隐私保护", "type": "textarea"}
      ]
    },
    {
      "id": "business",
      "title": "商业价值",
      "fields": [
        {"id": "market_size", "label": "目标市场规模", "type": "text"},
        {"id": "business_model", "label": "盈利模式", "type": "textarea", "required": true},
        {"id": "revenue_projection", "label": "收入预测", "type": "text"}
      ]
    },
    {
      "id": "team",
      "title": "团队信息",
      "fields": [
        {"id": "team_members", "label": "核心成员", "type": "textarea", "required": true},
        {"id": "team_advantage", "label": "团队金融背景", "type": "textarea"}
      ]
    },
    {
      "id": "output_config",
      "title": "输出配置",
      "fields": [
        {"id": "slide_count", "label": "期望页数", "type": "range", "min": 10, "max": 30, "default": 20},
        {"id": "detail_level", "label": "详细程度", "type": "select", "options": ["精简版", "标准版", "详细版"], "default": "标准版"},
        {"id": "theme", "label": "视觉风格", "type": "select", "options": ["dark_tech", "fresh_blue", "business"], "default": "business"}
      ]
    }
  ]
}', 1);

-- 插入金融科技评分规则
INSERT INTO `scoring_rule` (`domain`, `domain_name`, `rule_name`, `rule_config`, `priority`, `is_active`) VALUES
('fintech', '金融科技', '路演必备章节', '{"condition":{"field":"report_type","operator":"equals","value":"路演PPT"},"action":{"type":"add_sections","sections":["项目概述","解决方案","合规安全","商业模式","团队介绍","财务预测"]}}', 10, 1),
('fintech', '金融科技', '含合规要求则添加合规章节', '{"condition":{"field":"compliance_status","operator":"exists","value":true},"action":{"type":"enhance_slide","slide_type":"two_column_contrast","title":"合规优势对比"}}', 5, 1);

SELECT 'PPT相关表创建完成！' AS message;
