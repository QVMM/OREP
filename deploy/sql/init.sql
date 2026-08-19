-- ============================================================
-- OREP 在线路演评审平台 - 完整数据库 Schema
-- 2025 世界职业院校技能大赛评分标准
-- ============================================================

-- 1. 租户（学校）
CREATE TABLE IF NOT EXISTS tenant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '学校名称',
    code VARCHAR(100) NOT NULL COMMENT '学校编码',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='租户/学校表';

-- 2. 用户
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码(BCrypt加密)',
    email VARCHAR(255) NOT NULL COMMENT '邮箱',
    role ENUM('ADMIN','SCHOOL_ADMIN','TEACHER','STUDENT','REVIEWER','EXPERT') NOT NULL COMMENT '角色',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    KEY idx_tenant (tenant_id),
    CONSTRAINT fk_user_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 3. 邮箱验证码
CREATE TABLE IF NOT EXISTS email_verification_code (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL COMMENT '邮箱地址',
    code VARCHAR(10) NOT NULL COMMENT '验证码',
    expired_at DATETIME NOT NULL COMMENT '过期时间',
    used TINYINT NOT NULL DEFAULT 0 COMMENT '是否已使用',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_email (email),
    KEY idx_expired (expired_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='邮箱验证码表';

-- 4. 会议
CREATE TABLE IF NOT EXISTS meeting (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    title VARCHAR(255) NOT NULL COMMENT '会议标题',
    creator_id BIGINT NOT NULL COMMENT '创建者ID',
    meeting_code VARCHAR(16) NOT NULL COMMENT '会议编号(用于分享)',
    meeting_password VARCHAR(64) NOT NULL COMMENT '会议密码',
    jitsi_room_id VARCHAR(128) NOT NULL COMMENT '视频房间ID',
    status ENUM('CREATED','RUNNING','ENDED') NOT NULL DEFAULT 'CREATED' COMMENT '状态',
    duration_minutes INT NOT NULL DEFAULT 60 COMMENT '路演时长(分钟)',
    start_time DATETIME DEFAULT NULL COMMENT '实际开始时间',
    end_time DATETIME DEFAULT NULL COMMENT '实际结束时间',
    countdown_end_at DATETIME DEFAULT NULL COMMENT '倒计时结束时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_meeting_code (meeting_code),
    UNIQUE KEY uk_jitsi_room (jitsi_room_id),
    KEY idx_tenant (tenant_id),
    KEY idx_creator (creator_id),
    CONSTRAINT fk_meeting_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    CONSTRAINT fk_meeting_creator FOREIGN KEY (creator_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议表';

-- 5. 评分模板
CREATE TABLE IF NOT EXISTS score_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分模板表';

-- 6. 评分项
CREATE TABLE IF NOT EXISTS score_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    template_id BIGINT NOT NULL COMMENT '所属模板',
    category VARCHAR(100) NOT NULL COMMENT '评分类别(一、技能水平 等)',
    name VARCHAR(255) NOT NULL COMMENT '评分项名称',
    max_score DECIMAL(5,2) NOT NULL COMMENT '满分',
    description TEXT COMMENT '评分说明',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    KEY idx_template (template_id),
    CONSTRAINT fk_item_template FOREIGN KEY (template_id) REFERENCES score_template(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分项表';

-- 7. 评分记录(每人每会议一条)
CREATE TABLE IF NOT EXISTS score_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    user_id BIGINT NOT NULL COMMENT '评分人ID',
    total_score DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '总分',
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    UNIQUE KEY uk_meeting_user (meeting_id, user_id),
    KEY idx_tenant (tenant_id),
    KEY idx_meeting (meeting_id),
    CONSTRAINT fk_record_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    CONSTRAINT fk_record_meeting FOREIGN KEY (meeting_id) REFERENCES meeting(id),
    CONSTRAINT fk_record_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分记录表';

-- 8. 评分详情(每项分数+评论)
CREATE TABLE IF NOT EXISTS score_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    record_id BIGINT NOT NULL COMMENT '评分记录ID',
    item_id BIGINT NOT NULL COMMENT '评分项ID',
    score DECIMAL(5,2) NOT NULL COMMENT '得分',
    comment TEXT COMMENT '评语',
    KEY idx_record (record_id),
    CONSTRAINT fk_detail_record FOREIGN KEY (record_id) REFERENCES score_record(id),
    CONSTRAINT fk_detail_item FOREIGN KEY (item_id) REFERENCES score_item(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分详情表';

-- 9. 问题跟踪
CREATE TABLE IF NOT EXISTS issue (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    meeting_id BIGINT NOT NULL COMMENT '来源会议',
    score_detail_id BIGINT DEFAULT NULL COMMENT '来源评分详情',
    category VARCHAR(100) DEFAULT NULL COMMENT '问题类别',
    description TEXT NOT NULL COMMENT '问题描述',
    source_user_id BIGINT DEFAULT NULL COMMENT '来源评分人',
    status INT NOT NULL DEFAULT 0 COMMENT '状态: 0=待解决, 1=已解决',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME DEFAULT NULL COMMENT '解决时间',
    resolved_meeting_id BIGINT DEFAULT NULL COMMENT '在哪次会议解决的',
    KEY idx_tenant (tenant_id),
    KEY idx_meeting (meeting_id),
    KEY idx_status (status),
    CONSTRAINT fk_issue_tenant FOREIGN KEY (tenant_id) REFERENCES tenant(id),
    CONSTRAINT fk_issue_meeting FOREIGN KEY (meeting_id) REFERENCES meeting(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问题跟踪表';

-- 10. 会议参与者
CREATE TABLE IF NOT EXISTS meeting_participant (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME DEFAULT NULL,
    UNIQUE KEY uk_meeting_user (meeting_id, user_id),
    CONSTRAINT fk_participant_meeting FOREIGN KEY (meeting_id) REFERENCES meeting(id),
    CONSTRAINT fk_participant_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议参与者表';

-- 11. 聊天消息
CREATE TABLE IF NOT EXISTS chat_message (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    sender_id BIGINT DEFAULT NULL COMMENT '发送者ID',
    sender_name VARCHAR(100) NOT NULL COMMENT '发送者名称',
    message_type ENUM('text','image','file') NOT NULL DEFAULT 'text' COMMENT '消息类型',
    content TEXT NOT NULL COMMENT '消息内容',
    file_name VARCHAR(255) DEFAULT NULL COMMENT '文件名(文件/图片类型)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    KEY idx_meeting (meeting_id),
    CONSTRAINT fk_chat_meeting FOREIGN KEY (meeting_id) REFERENCES meeting(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- 12. 会议录制
CREATE TABLE IF NOT EXISTS meeting_recording (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    user_id BIGINT NOT NULL COMMENT '发起录制用户ID',
    recording_id VARCHAR(64) DEFAULT NULL COMMENT '录制任务ID',
    status ENUM('STARTING','RECORDING','PROCESSING','READY','FAILED') NOT NULL DEFAULT 'STARTING' COMMENT '录制状态',
    file_path VARCHAR(512) DEFAULT NULL COMMENT '主录制视频对象路径，必须包含音频轨',
    mime_type VARCHAR(100) DEFAULT NULL COMMENT '主视频 MIME 类型',
    size_bytes BIGINT DEFAULT NULL COMMENT '主视频大小',
    has_audio TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否包含音频轨',
    has_video TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否包含视频轨',
    error_message TEXT DEFAULT NULL COMMENT '失败原因',
    camera_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：摄像头视频路径',
    screen_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：屏幕视频路径',
    audio_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：音频路径',
    audio_size_bytes BIGINT DEFAULT NULL COMMENT '兼容旧版：音频大小',
    duration_seconds INT DEFAULT NULL COMMENT '录制时长',
    meeting_title VARCHAR(255) DEFAULT NULL COMMENT '会议标题冗余',
    started_at DATETIME DEFAULT NULL COMMENT '开始录制时间',
    ended_at DATETIME DEFAULT NULL COMMENT '结束录制时间',
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_meeting (meeting_id),
    KEY idx_user (user_id),
    KEY idx_status (status),
    CONSTRAINT fk_recording_meeting FOREIGN KEY (meeting_id) REFERENCES meeting(id),
    CONSTRAINT fk_recording_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议录制表';

-- ============================================================
-- 预置数据：2025 世界职业院校技能大赛总决赛评分标准
-- ============================================================

-- 默认评分模板
INSERT INTO score_template (id, name, description) VALUES
(1, '2025世界职业院校技能大赛总决赛评分模板', '根据2025年世界职业院校技能大赛总决赛评分要素制定，共5项评分指标，总分100分');

-- 一、技能水平 (60分)
INSERT INTO score_item (template_id, category, name, max_score, description, sort_order) VALUES
(1, '一、技能水平（权重60%，60分）', '操作规范性', 10, '技能操作规范，符合行业标准和岗位要求', 1),
(1, '一、技能水平（权重60%，60分）', '技能熟练度', 15, '知识技术应用和软硬件等工具使用熟练，操作流畅，运用精准，任务进度控制和时间利用合理', 2),
(1, '一、技能水平（权重60%，60分）', '任务难易度', 15, '工作任务完整，突出关键技术，具有一定挑战性，需要较高技能操作水平和解决复杂问题的综合能力', 3),
(1, '一、技能水平（权重60%，60分）', '技术先进性', 15, '体现所属行业新标准、新技术、新场景应用，积极应用前沿技术、数字化技术，技术选择恰当', 4),
(1, '一、技能水平（权重60%，60分）', '现场讲解效果', 5, '讲解内容逻辑清晰，重点突出，表达准确', 5);

-- 二、职业素养 (10分)
INSERT INTO score_item (template_id, category, name, max_score, description, sort_order) VALUES
(1, '二、职业素养（权重10%，10分）', '职业道德与行为规范', 4, '诚信守法，尊重知识产权，遵守职业伦理，展现良好职业风貌', 6),
(1, '二、职业素养（权重10%，10分）', '工匠精神', 3, '注重细节，精益求精，追求卓越，体现管理意识和质量意识', 7),
(1, '二、职业素养（权重10%，10分）', '安全意识', 3, '严格遵守安全规范，具备劳动保护和风险防范意识', 8);

-- 三、应用价值 (10分)
INSERT INTO score_item (template_id, category, name, max_score, description, sort_order) VALUES
(1, '三、应用价值（权重10%，10分）', '实用性', 4, '解决方案可直接应用于实践，有效解决生产、生活中的实际问题，契合产业转型升级、区域经济社会发展、乡村振兴、促进高质量就业等国家战略需求', 9),
(1, '三、应用价值（权重10%，10分）', '经济性', 3, '资源利用合理，体现高效益、高质量', 10),
(1, '三、应用价值（权重10%，10分）', '可持续性', 3, '具有良好环保意识，绿色低碳，符合产业未来发展方向', 11);

-- 四、团队合作 (10分)
INSERT INTO score_item (template_id, category, name, max_score, description, sort_order) VALUES
(1, '四、团队合作（权重10%，10分）', '团队精神', 5, '团队成员能够准确理解共同目标和任务，清楚自己的角色定位和职责，团队成员相互尊重、信任和支持，拥有良好的团队氛围', 12),
(1, '四、团队合作（权重10%，10分）', '沟通协作', 5, '团队成员在比赛中能够有效沟通、紧密协作，能够相互补台，共同应对突发情况', 13);

-- 五、创新创意 (10分)
INSERT INTO score_item (template_id, category, name, max_score, description, sort_order) VALUES
(1, '五、创新创意（权重10%，10分）', '创新意识', 4, '体现原始创意、创新和团队成员创新精神、创新能力', 14),
(1, '五、创新创意（权重10%，10分）', '创新成效', 6, '在要素整合、新技术应用、工艺流程改进、服务模式优化等方面具有原创性，侧重加工工艺创新、实用技术创新、产品（技术）数字化改良、应用性优化、民生类创意等', 15);

-- 默认租户
INSERT INTO tenant (id, name, code) VALUES
(1, '默认学校', 'DEFAULT');

-- 默认管理员 (密码: admin123, BCrypt加密)
INSERT INTO users (id, tenant_id, username, password, email, role) VALUES
(1, 1, 'admin', '$2b$10$Kc/QS6iH/ZxwAuHPOIWiEuB4OKsuUzE8Zn/3p/cJKPUrKaC0Lmz/y', 'admin@orep.com', 'ADMIN');
