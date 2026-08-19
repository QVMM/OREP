-- 用户行为监控与在线状态
CREATE TABLE IF NOT EXISTS user_activity_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    username VARCHAR(100) NOT NULL COMMENT '用户名冗余',
    role VARCHAR(40) DEFAULT NULL COMMENT '角色冗余',
    source VARCHAR(40) NOT NULL COMMENT '来源: backend/user_frontend/admin_frontend',
    action_type VARCHAR(80) NOT NULL COMMENT '操作类型',
    action_name VARCHAR(255) NOT NULL COMMENT '操作名称',
    method VARCHAR(12) DEFAULT NULL COMMENT 'HTTP 方法',
    path VARCHAR(500) DEFAULT NULL COMMENT '接口路径',
    route VARCHAR(255) DEFAULT NULL COMMENT '前端路由',
    page_title VARCHAR(255) DEFAULT NULL COMMENT '页面标题',
    ip_address VARCHAR(64) DEFAULT NULL COMMENT 'IP 地址',
    ip_location VARCHAR(255) DEFAULT NULL COMMENT 'IP 归属地',
    user_agent VARCHAR(500) DEFAULT NULL COMMENT '浏览器 UA',
    status_code INT DEFAULT NULL COMMENT '响应状态码',
    duration_ms BIGINT DEFAULT NULL COMMENT '接口耗时毫秒',
    metadata JSON DEFAULT NULL COMMENT '扩展信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_tenant_created (tenant_id, created_at),
    KEY idx_user_created (user_id, created_at),
    KEY idx_action_type (action_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户行为监控日志';

CREATE TABLE IF NOT EXISTS user_online_status (
    user_id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL COMMENT '所属租户',
    username VARCHAR(100) NOT NULL COMMENT '用户名冗余',
    role VARCHAR(40) DEFAULT NULL COMMENT '角色冗余',
    online TINYINT(1) NOT NULL DEFAULT 0 COMMENT '在线标记',
    last_seen_at DATETIME NOT NULL COMMENT '最近活跃时间',
    last_ip VARCHAR(64) DEFAULT NULL COMMENT '最近 IP',
    ip_location VARCHAR(255) DEFAULT NULL COMMENT 'IP 归属地',
    user_agent VARCHAR(500) DEFAULT NULL COMMENT '浏览器 UA',
    current_route VARCHAR(255) DEFAULT NULL COMMENT '当前前端路由',
    current_page VARCHAR(255) DEFAULT NULL COMMENT '当前页面',
    session_id VARCHAR(80) DEFAULT NULL COMMENT '会话ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_tenant_seen (tenant_id, last_seen_at),
    KEY idx_online (online)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户在线状态';
