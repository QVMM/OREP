-- =====================================================
-- AI PPT 历史产物与质量升级基础表
-- 用途：
-- 1. 持久化每页 HTML，避免只依赖本地 preview_xx 文件夹
-- 2. 持久化大纲、最终结果、质量报告等生成快照
-- 3. 预留素材证据、视觉风格、页面质量报告的落库能力
-- =====================================================

USE orep;

-- 1. 每页 HTML 历史表
CREATE TABLE IF NOT EXISTS `ppt_html_page` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `page_index` INT NOT NULL COMMENT '页码，从 1 开始',
    `title` VARCHAR(255) COMMENT '页面标题',
    `section` VARCHAR(128) COMMENT '章节/阶段',
    `html_content` LONGTEXT NOT NULL COMMENT 'HTML 页面源码',
    `content_hash` VARCHAR(64) COMMENT 'HTML 内容 hash，用于判断是否变化',
    `source` VARCHAR(32) DEFAULT 'ai' COMMENT '来源: ai/fallback/manual/regenerated',
    `status` VARCHAR(32) DEFAULT 'active' COMMENT '状态: active/archived/failed',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_page` (`task_id`, `page_index`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`),
    CONSTRAINT `fk_ppt_html_page_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 每页 HTML 历史表';

-- 2. 生成快照表：保存 outline、final_outline、quality_report、style_preview 等阶段性产物
CREATE TABLE IF NOT EXISTS `ppt_generation_snapshot` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `questionnaire_id` BIGINT COMMENT '关联问卷 ID',
    `snapshot_type` VARCHAR(64) NOT NULL COMMENT '快照类型: outline/final_outline/quality_report/style_preview/material_analysis',
    `stage` VARCHAR(64) COMMENT '生成阶段: round1/round2/round3/round4/completed',
    `version` INT DEFAULT 1 COMMENT '同类型快照版本号',
    `payload` JSON NOT NULL COMMENT '快照 JSON 内容',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_task_type` (`task_id`, `snapshot_type`),
    INDEX `idx_questionnaire_id` (`questionnaire_id`),
    CONSTRAINT `fk_ppt_snapshot_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE,
    CONSTRAINT `fk_ppt_snapshot_questionnaire`
        FOREIGN KEY (`questionnaire_id`) REFERENCES `ppt_questionnaire` (`id`)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 生成阶段快照表';

-- 3. 视觉风格选择表：后续接入风格预览三选一
CREATE TABLE IF NOT EXISTS `ppt_visual_style_selection` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `style_id` VARCHAR(64) NOT NULL COMMENT '风格 ID',
    `style_name` VARCHAR(128) COMMENT '风格名称',
    `style_profile` JSON NOT NULL COMMENT '结构化视觉风格配置',
    `preview_pages` JSON COMMENT '风格预览页面或截图信息',
    `is_selected` TINYINT(1) DEFAULT 0 COMMENT '是否为用户最终选择',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_style_id` (`style_id`),
    CONSTRAINT `fk_ppt_visual_style_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 视觉风格选择表';

-- 4. 素材证据表：后续接入截图、照片、数据图、视频关键帧
CREATE TABLE IF NOT EXISTS `ppt_material_asset` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `asset_type` VARCHAR(32) NOT NULL COMMENT '素材类型: image/screenshot/chart/video_frame/document',
    `filename` VARCHAR(255) COMMENT '原始文件名',
    `file_path` VARCHAR(512) COMMENT '本地文件路径',
    `file_url` VARCHAR(512) COMMENT '可访问 URL',
    `description` TEXT COMMENT '用户或 AI 生成的素材说明',
    `analysis_result` JSON COMMENT '素材分析结果',
    `quality` VARCHAR(32) COMMENT '素材质量: high/medium/low',
    `privacy_risk` VARCHAR(32) COMMENT '匿名风险: low/medium/high',
    `status` VARCHAR(32) DEFAULT 'active' COMMENT '状态: active/ignored/deleted',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_asset_type` (`asset_type`),
    INDEX `idx_status` (`status`),
    CONSTRAINT `fk_ppt_material_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 素材证据表';

-- 5. 页面质量报告表：后续接入密度、视口、评分点、HTML 渲染检查
CREATE TABLE IF NOT EXISTS `ppt_page_quality_report` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `page_index` INT NOT NULL COMMENT '页码，从 1 开始',
    `status` VARCHAR(32) DEFAULT 'unknown' COMMENT '状态: pass/warning/fail/unknown',
    `score` INT COMMENT '页面质量分 0-100',
    `checks` JSON COMMENT '检查项详情',
    `regeneration_strategy` VARCHAR(64) COMMENT '建议重生成策略',
    `can_auto_fix` TINYINT(1) DEFAULT 0 COMMENT '是否可自动修复',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_page_quality` (`task_id`, `page_index`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`),
    CONSTRAINT `fk_ppt_quality_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 页面质量报告表';

-- 6. 评分点覆盖矩阵表：记录每个评分点是否被大纲/页面覆盖
CREATE TABLE IF NOT EXISTS `ppt_scoring_coverage` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `point_id` VARCHAR(128) NOT NULL COMMENT '评分点稳定 ID',
    `category` VARCHAR(128) COMMENT '评分点分类',
    `point_name` VARCHAR(255) NOT NULL COMMENT '评分点名称',
    `required` TINYINT(1) DEFAULT 0 COMMENT '是否必备评分点',
    `covered` TINYINT(1) DEFAULT 0 COMMENT '是否已覆盖',
    `page_indices` JSON COMMENT '覆盖该评分点的页码列表',
    `evidence` JSON COMMENT '覆盖证据，如页面标题、关键词、命中片段',
    `hint` TEXT COMMENT '缺失或优化提示',
    `severity` VARCHAR(32) DEFAULT 'info' COMMENT '严重程度: error/warning/info',
    `stage` VARCHAR(64) DEFAULT 'outline' COMMENT '生成阶段: outline/final_outline',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_point_stage` (`task_id`, `point_id`, `stage`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_covered` (`covered`),
    INDEX `idx_required` (`required`),
    CONSTRAINT `fk_ppt_scoring_coverage_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 评分点覆盖矩阵表';

-- 7. 技术实操演示步骤表：记录项目路演中的现场实操结构
CREATE TABLE IF NOT EXISTS `ppt_practice_demo_step` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `step_id` VARCHAR(128) NOT NULL COMMENT '实操步骤稳定 ID',
    `step_order` INT NOT NULL COMMENT '步骤顺序',
    `step_title` VARCHAR(255) NOT NULL COMMENT '步骤标题',
    `operation_goal` TEXT COMMENT '操作目标',
    `technical_points` JSON COMMENT '关键技术点',
    `required_evidence` JSON COMMENT '建议准备的证据素材',
    `available_evidence` JSON COMMENT '当前可用证据素材',
    `missing_evidence` JSON COMMENT '缺失证据提醒',
    `target_pages` JSON COMMENT '建议绑定的 PPT 页码',
    `scoring_dimensions` JSON COMMENT '支撑的评分维度',
    `demo_mode` VARCHAR(32) DEFAULT 'onsite' COMMENT '演示方式: onsite/ppt/fallback',
    `speaker_script` TEXT COMMENT '现场讲解建议',
    `fallback_script` TEXT COMMENT '无法现场演示时的兜底讲法',
    `stage` VARCHAR(64) DEFAULT 'outline' COMMENT '生成阶段: outline/final_outline',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_step_stage` (`task_id`, `step_id`, `stage`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_stage` (`stage`),
    CONSTRAINT `fk_ppt_practice_demo_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 技术实操演示步骤表';

-- 8. 优化任务队列状态表：记录用户对自动生成优化任务的处理状态
CREATE TABLE IF NOT EXISTS `ppt_optimization_task_status` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `task_id` BIGINT NOT NULL COMMENT '关联 PPT 任务 ID',
    `queue_task_id` VARCHAR(64) NOT NULL COMMENT '优化任务稳定 ID',
    `status` VARCHAR(32) DEFAULT 'todo' COMMENT '状态: todo/in_progress/done/skipped',
    `note` TEXT COMMENT '用户处理备注',
    `completed_at` DATETIME NULL COMMENT '完成时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_queue_task` (`task_id`, `queue_task_id`),
    INDEX `idx_task_id` (`task_id`),
    INDEX `idx_status` (`status`),
    CONSTRAINT `fk_ppt_optimization_status_task`
        FOREIGN KEY (`task_id`) REFERENCES `ppt_task` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 优化任务处理状态表';

-- 9. PPT 每页讲稿表：用于跨刷新、跨设备、跨浏览器持久化用户讲稿
CREATE TABLE IF NOT EXISTS `ppt_script_page` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `job_id` VARCHAR(64) NOT NULL COMMENT 'PPT 生成任务 ID',
    `page_index` INT NOT NULL COMMENT '页码，从 1 开始',
    `page_name` VARCHAR(128) DEFAULT NULL COMMENT 'SVG/页面文件名',
    `page_title` VARCHAR(255) DEFAULT NULL COMMENT '页面标题',
    `notes` TEXT COMMENT '本页讲稿',
    `document_json` LONGTEXT COMMENT '编辑器结构化文档快照 JSON',
    `source` VARCHAR(32) DEFAULT 'ppt-editor' COMMENT '来源: generated/manual/ppt-editor/import',
    `manual_edited` TINYINT(1) DEFAULT 1 COMMENT '是否用户手动修改过',
    `created_by` BIGINT NOT NULL COMMENT '创建者用户 ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_job_page_user` (`job_id`, `page_index`, `created_by`),
    INDEX `idx_job_user` (`job_id`, `created_by`),
    INDEX `idx_created_by` (`created_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PPT 每页讲稿持久化表';

SELECT 'PPT 历史产物、质量升级基础表与讲稿持久化表创建完成' AS message;
