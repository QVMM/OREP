-- ============================================================
-- OREP 课程学习模块
-- ============================================================

CREATE TABLE IF NOT EXISTS course (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL COMMENT '课程标题',
    subtitle VARCHAR(255) DEFAULT NULL COMMENT '课程副标题',
    description TEXT DEFAULT NULL COMMENT '课程简介',
    course_type VARCHAR(32) NOT NULL DEFAULT 'required' COMMENT 'required=必修课, elective=选修课',
    category VARCHAR(100) NOT NULL DEFAULT '人工智能' COMMENT '课程分类',
    cover_url VARCHAR(512) DEFAULT NULL COMMENT '封面图地址',
    accent_color VARCHAR(32) DEFAULT '#7cffb2' COMMENT '前端强调色',
    status VARCHAR(32) NOT NULL DEFAULT 'published' COMMENT 'published=已发布, draft=草稿',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    created_by BIGINT DEFAULT NULL COMMENT '创建者用户ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status_sort (status, sort_order),
    KEY idx_type (course_type),
    KEY idx_category (category),
    KEY idx_course_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程主表';

CREATE TABLE IF NOT EXISTS course_chapter (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL COMMENT '课程ID',
    title VARCHAR(255) NOT NULL COMMENT '章节标题',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_course_sort (course_id, sort_order),
    CONSTRAINT fk_course_chapter_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程章节表';

CREATE TABLE IF NOT EXISTS course_lesson (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL COMMENT '课程ID',
    chapter_id BIGINT NOT NULL COMMENT '章节ID',
    title VARCHAR(255) NOT NULL COMMENT '课时标题',
    lesson_type VARCHAR(32) NOT NULL DEFAULT 'video' COMMENT 'video=视频, document=文档',
    duration_seconds INT NOT NULL DEFAULT 0 COMMENT '时长秒数',
    resource_url VARCHAR(512) DEFAULT NULL COMMENT '播放或资料地址',
    video_file_path VARCHAR(512) DEFAULT NULL COMMENT '课程视频本地相对路径',
    video_mime_type VARCHAR(100) DEFAULT NULL COMMENT '课程视频 MIME 类型',
    video_size_bytes BIGINT DEFAULT NULL COMMENT '课程视频大小',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_course_sort (course_id, sort_order),
    KEY idx_chapter_sort (chapter_id, sort_order),
    CONSTRAINT fk_course_lesson_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
    CONSTRAINT fk_course_lesson_chapter FOREIGN KEY (chapter_id) REFERENCES course_chapter(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程课时表';

CREATE TABLE IF NOT EXISTS course_attachment (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id BIGINT NOT NULL COMMENT '课程ID',
    name VARCHAR(255) NOT NULL COMMENT '附件名称',
    file_url VARCHAR(512) NOT NULL COMMENT '附件地址',
    file_type VARCHAR(32) DEFAULT NULL COMMENT '附件类型',
    file_size VARCHAR(64) DEFAULT NULL COMMENT '展示用大小',
    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_course_sort (course_id, sort_order),
    CONSTRAINT fk_course_attachment_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程附件表';

CREATE TABLE IF NOT EXISTS course_learning_progress (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL COMMENT '用户ID',
    course_id BIGINT NOT NULL COMMENT '课程ID',
    lesson_id BIGINT DEFAULT NULL COMMENT '最近学习课时ID',
    learned_seconds INT NOT NULL DEFAULT 0 COMMENT '当前课时已学秒数',
    progress_percent INT NOT NULL DEFAULT 0 COMMENT '课程进度百分比',
    completed_lessons INT NOT NULL DEFAULT 0 COMMENT '已完成课时数',
    status VARCHAR(32) NOT NULL DEFAULT 'not_started' COMMENT 'not_started, learning, completed',
    last_learned_at DATETIME DEFAULT NULL COMMENT '最近学习时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_course (user_id, course_id),
    KEY idx_user_status (user_id, status),
    KEY idx_lesson (lesson_id),
    CONSTRAINT fk_course_progress_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
    CONSTRAINT fk_course_progress_lesson FOREIGN KEY (lesson_id) REFERENCES course_lesson(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程学习进度表';

INSERT IGNORE INTO course (id, title, subtitle, description, course_type, category, cover_url, accent_color, status, sort_order) VALUES
(1, '人工智能进阶课程', 'rag测试课程', '面向项目路演和智能应用实践，学习 RAG、微调与 AI 产品化表达。', 'required', '人工智能', '', '#ff8a16', 'published', 10),
(2, 'Python编程基础', 'AI 应用开发基础课', '掌握 Python 语法、数据处理与智能应用原型开发基础。', 'required', '编程基础', '', '#7cffb2', 'published', 20),
(3, '前后端分离之Springboot与Vue', '工程化开发实践', '围绕 Spring Boot 与 Vue 构建前后端分离业务系统。', 'required', '工程实践', '', '#6aa6ff', 'published', 30);

INSERT IGNORE INTO course_chapter (id, course_id, title, sort_order) VALUES
(1, 1, 'rag与微调的区别', 10),
(2, 2, 'Python 语言入门', 10),
(3, 3, '前后端分离架构', 10);

INSERT IGNORE INTO course_lesson (id, course_id, chapter_id, title, lesson_type, duration_seconds, resource_url, sort_order) VALUES
(1, 1, 1, 'rag与微调区别', 'video', 71, '/course-assets/ai-rag-finetune.mp4', 10),
(2, 2, 2, 'Python 基础语法与运行环境', 'video', 860, '/course-assets/python-basic.mp4', 10),
(3, 3, 3, 'Spring Boot 与 Vue 分层协作', 'video', 960, '/course-assets/springboot-vue.mp4', 10);

INSERT IGNORE INTO course_attachment (id, course_id, name, file_url, file_type, file_size, sort_order) VALUES
(1, 1, 'RAG 与微调对比速查表.pdf', '/course-assets/rag-finetune-guide.pdf', 'pdf', '1.2 MB', 10),
(2, 2, 'Python 练习题包.zip', '/course-assets/python-exercises.zip', 'zip', '820 KB', 10),
(3, 3, '前后端接口约定模板.docx', '/course-assets/api-contract-template.docx', 'docx', '460 KB', 10);

INSERT IGNORE INTO course_learning_progress (id, user_id, course_id, lesson_id, learned_seconds, progress_percent, completed_lessons, status, last_learned_at) VALUES
(1, 1, 1, 1, 64, 1, 0, 'learning', CURRENT_TIMESTAMP);
