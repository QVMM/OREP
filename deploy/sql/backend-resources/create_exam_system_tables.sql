-- ============================================================
-- OREP 考试系统一期
-- ============================================================

CREATE TABLE IF NOT EXISTS exam_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question_type VARCHAR(32) NOT NULL COMMENT 'single,multiple,judge,blank,programming',
    stem TEXT NOT NULL COMMENT '题干',
    options_json TEXT DEFAULT NULL COMMENT '选项 JSON',
    answer_json TEXT NOT NULL COMMENT '答案 JSON',
    analysis TEXT DEFAULT NULL COMMENT '解析',
    category VARCHAR(100) DEFAULT '通用',
    difficulty VARCHAR(32) DEFAULT 'normal',
    score INT DEFAULT 5,
    status VARCHAR(32) DEFAULT 'enabled',
    created_by BIGINT DEFAULT NULL COMMENT '创建者用户ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_type (question_type),
    KEY idx_category (category),
    KEY idx_status (status),
    KEY idx_exam_question_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试题库';

CREATE TABLE IF NOT EXISTS exam_paper (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    duration_minutes INT NOT NULL DEFAULT 45,
    pass_score INT NOT NULL DEFAULT 60,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    shuffle_questions TINYINT(1) NOT NULL DEFAULT 1,
    shuffle_options TINYINT(1) NOT NULL DEFAULT 1,
    anti_cheat_enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_by BIGINT DEFAULT NULL COMMENT '创建者用户ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_status (status),
    KEY idx_exam_paper_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试试卷';

CREATE TABLE IF NOT EXISTS exam_paper_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    paper_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    score INT NOT NULL DEFAULT 5,
    sort_order INT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_paper_question (paper_id, question_id),
    KEY idx_paper_sort (paper_id, sort_order),
    CONSTRAINT fk_exam_paper_question_paper FOREIGN KEY (paper_id) REFERENCES exam_paper(id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_paper_question_question FOREIGN KEY (question_id) REFERENCES exam_question(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='试卷题目';

CREATE TABLE IF NOT EXISTS exam_attempt (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    paper_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'in_progress',
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at DATETIME DEFAULT NULL,
    deadline_at DATETIME DEFAULT NULL,
    score INT DEFAULT 0,
    total_score INT DEFAULT 0,
    correct_count INT DEFAULT 0,
    question_count INT DEFAULT 0,
    screen_leave_count INT DEFAULT 0,
    KEY idx_user_status (user_id, status),
    KEY idx_paper_user (paper_id, user_id),
    CONSTRAINT fk_exam_attempt_paper FOREIGN KEY (paper_id) REFERENCES exam_paper(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试作答记录';

CREATE TABLE IF NOT EXISTS exam_attempt_answer (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    attempt_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    answer_json TEXT DEFAULT NULL,
    correct TINYINT(1) DEFAULT 0,
    score INT DEFAULT 0,
    UNIQUE KEY uk_attempt_question (attempt_id, question_id),
    CONSTRAINT fk_exam_answer_attempt FOREIGN KEY (attempt_id) REFERENCES exam_attempt(id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_answer_question FOREIGN KEY (question_id) REFERENCES exam_question(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='考试答案';

CREATE TABLE IF NOT EXISTS exam_favorite (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_question (user_id, question_id),
    CONSTRAINT fk_exam_favorite_question FOREIGN KEY (question_id) REFERENCES exam_question(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='题目收藏';

CREATE TABLE IF NOT EXISTS exam_wrong_question (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL,
    last_attempt_id BIGINT DEFAULT NULL,
    wrong_count INT NOT NULL DEFAULT 1,
    last_wrong_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_question (user_id, question_id),
    CONSTRAINT fk_exam_wrong_question FOREIGN KEY (question_id) REFERENCES exam_question(id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_wrong_attempt FOREIGN KEY (last_attempt_id) REFERENCES exam_attempt(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错题归纳';

INSERT IGNORE INTO exam_question (id, question_type, stem, options_json, answer_json, analysis, category, difficulty, score, status) VALUES
(1, 'single', 'RAG 系统中，检索阶段最主要的作用是什么？', '[{"key":"A","text":"从知识库召回相关上下文"},{"key":"B","text":"直接训练大模型参数"},{"key":"C","text":"替代所有提示词"},{"key":"D","text":"压缩视频文件"}]', '["A"]', 'RAG 通过检索外部知识补充上下文，再交给生成模型回答。', '人工智能', 'easy', 5, 'enabled'),
(2, 'multiple', '以下哪些做法可以降低学生记答案的风险？', '[{"key":"A","text":"随机题序"},{"key":"B","text":"随机选项顺序"},{"key":"C","text":"考试前下发答案解析"},{"key":"D","text":"服务端保存 attempt 校验"}]', '["A","B","D"]', '随机题序和选项、服务端 attempt 校验都能降低答案传播风险。', '考试安全', 'normal', 5, 'enabled'),
(3, 'judge', '考试倒计时应只依赖前端本地时间。', '[{"key":"true","text":"正确"},{"key":"false","text":"错误"}]', '["false"]', '倒计时需要服务端 deadline 兜底，避免本地时间被篡改。', '考试安全', 'easy', 5, 'enabled'),
(4, 'blank', '在线考试到点后应由系统自动____。', '[]', '["交卷"]', '到点自动交卷可以保证考试时间一致性。', '考试流程', 'easy', 5, 'enabled'),
(5, 'programming', '请写出一个函数名，用于提交考试答案。', '[]', '["submitAttempt"]', '一期编程题先按文本答案判分，后续可接代码沙箱。', '编程题', 'normal', 5, 'enabled');

INSERT IGNORE INTO exam_paper (id, title, description, duration_minutes, pass_score, status, shuffle_questions, shuffle_options, anti_cheat_enabled) VALUES
(1, 'AI 课程阶段测评', '覆盖课程学习后的 RAG、考试安全和基础流程能力验证。', 30, 60, 'published', 1, 1, 1);

INSERT IGNORE INTO exam_paper_question (paper_id, question_id, score, sort_order) VALUES
(1, 1, 20, 10),
(1, 2, 20, 20),
(1, 3, 20, 30),
(1, 4, 20, 40),
(1, 5, 20, 50);
