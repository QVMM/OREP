package com.orep.backend.controller;

import com.orep.backend.common.Result;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;

/**
 * 数据库维护接口
 */
@RestController
@RequestMapping("/api/admin/maintenance")
public class MaintenanceController {

    @Autowired
    private JdbcTemplate jdbc;

    /**
     * 修复所有数据库表和列的中文注释
     */
    @PostMapping("/fix-comments")
    public Result<List<String>> fixComments(HttpServletRequest req) {
        List<String> logs = new ArrayList<>();

        // 表注释修复
        exec(logs, "ALTER TABLE tenant COMMENT = '租户/学校表'");
        exec(logs, "ALTER TABLE users COMMENT = '用户表'");
        exec(logs, "ALTER TABLE email_verification_code COMMENT = '邮箱验证码表'");
        exec(logs, "ALTER TABLE meeting COMMENT = '会议表'");
        exec(logs, "ALTER TABLE score_template COMMENT = '评分模板表'");
        exec(logs, "ALTER TABLE score_item COMMENT = '评分项表'");
        exec(logs, "ALTER TABLE score_record COMMENT = '评分记录表'");
        exec(logs, "ALTER TABLE score_detail COMMENT = '评分详情表'");
        exec(logs, "ALTER TABLE issue COMMENT = '问题跟踪表'");
        exec(logs, "ALTER TABLE meeting_participant COMMENT = '会议参与者表'");

        // tenant 表列注释
        exec(logs, "ALTER TABLE tenant MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE tenant MODIFY COLUMN name VARCHAR(255) NOT NULL COMMENT '学校名称'");
        exec(logs, "ALTER TABLE tenant MODIFY COLUMN code VARCHAR(100) NOT NULL COMMENT '学校编码'");
        exec(logs, "ALTER TABLE tenant MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");

        // users 表列注释
        exec(logs, "ALTER TABLE users MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN tenant_id BIGINT NOT NULL COMMENT '所属租户'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN username VARCHAR(100) NOT NULL COMMENT '用户名'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NOT NULL COMMENT '密码(BCrypt加密)'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN email VARCHAR(255) NOT NULL COMMENT '邮箱'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN role ENUM('ADMIN','SCHOOL_ADMIN','TEACHER','STUDENT','REVIEWER','EXPERT') NOT NULL COMMENT '角色'");
        exec(logs, "ALTER TABLE users MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");

        // email_verification_code 表列注释
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN email VARCHAR(255) NOT NULL COMMENT '邮箱地址'");
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN code VARCHAR(10) NOT NULL COMMENT '验证码'");
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN expired_at DATETIME NOT NULL COMMENT '过期时间'");
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN used TINYINT NOT NULL DEFAULT 0 COMMENT '是否已使用'");
        exec(logs, "ALTER TABLE email_verification_code MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");

        // meeting 表列注释
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN tenant_id BIGINT NOT NULL COMMENT '所属租户'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN title VARCHAR(255) NOT NULL COMMENT '会议标题'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN creator_id BIGINT NOT NULL COMMENT '创建者ID'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN meeting_code VARCHAR(16) NOT NULL COMMENT '会议编号(用于分享)'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN meeting_password VARCHAR(64) NOT NULL COMMENT '会议密码'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN jitsi_room_id VARCHAR(128) NOT NULL COMMENT '视频房间ID'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN status ENUM('CREATED','RUNNING','ENDED') NOT NULL DEFAULT 'CREATED' COMMENT '状态'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN duration_minutes INT NOT NULL DEFAULT 60 COMMENT '路演时长(分钟)'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN start_time DATETIME DEFAULT NULL COMMENT '实际开始时间'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN end_time DATETIME DEFAULT NULL COMMENT '实际结束时间'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN countdown_end_at DATETIME DEFAULT NULL COMMENT '倒计时结束时间'");
        exec(logs, "ALTER TABLE meeting MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");

        // score_template 表列注释
        exec(logs, "ALTER TABLE score_template MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE score_template MODIFY COLUMN name VARCHAR(255) NOT NULL COMMENT '模板名称'");
        exec(logs, "ALTER TABLE score_template MODIFY COLUMN description TEXT COMMENT '模板描述'");
        exec(logs, "ALTER TABLE score_template MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");

        // score_item 表列注释
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN template_id BIGINT NOT NULL COMMENT '所属模板'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN category VARCHAR(100) NOT NULL COMMENT '评分类别'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN name VARCHAR(255) NOT NULL COMMENT '评分项名称'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN max_score DECIMAL(5,2) NOT NULL COMMENT '满分'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN description TEXT COMMENT '评分说明'");
        exec(logs, "ALTER TABLE score_item MODIFY COLUMN sort_order INT NOT NULL DEFAULT 0 COMMENT '排序'");

        // score_record 表列注释
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN tenant_id BIGINT NOT NULL COMMENT '所属租户'");
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN meeting_id BIGINT NOT NULL COMMENT '会议ID'");
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN user_id BIGINT NOT NULL COMMENT '评分人ID'");
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN total_score DECIMAL(5,2) NOT NULL DEFAULT 0 COMMENT '总分'");
        exec(logs, "ALTER TABLE score_record MODIFY COLUMN submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间'");

        // score_detail 表列注释
        exec(logs, "ALTER TABLE score_detail MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE score_detail MODIFY COLUMN record_id BIGINT NOT NULL COMMENT '评分记录ID'");
        exec(logs, "ALTER TABLE score_detail MODIFY COLUMN item_id BIGINT NOT NULL COMMENT '评分项ID'");
        exec(logs, "ALTER TABLE score_detail MODIFY COLUMN score DECIMAL(5,2) NOT NULL COMMENT '得分'");
        exec(logs, "ALTER TABLE score_detail MODIFY COLUMN comment TEXT COMMENT '评语'");

        // issue 表列注释
        exec(logs, "ALTER TABLE issue MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN tenant_id BIGINT NOT NULL COMMENT '所属租户'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN meeting_id BIGINT NOT NULL COMMENT '来源会议'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN score_detail_id BIGINT DEFAULT NULL COMMENT '来源评分详情'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN category VARCHAR(100) DEFAULT NULL COMMENT '问题类别'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN description TEXT NOT NULL COMMENT '问题描述'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN source_user_id BIGINT DEFAULT NULL COMMENT '来源评分人'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN status INT NOT NULL DEFAULT 0 COMMENT '状态: 0=待解决, 1=已解决'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN resolved_at DATETIME DEFAULT NULL COMMENT '解决时间'");
        exec(logs, "ALTER TABLE issue MODIFY COLUMN resolved_meeting_id BIGINT DEFAULT NULL COMMENT '在哪次会议解决的'");

        // meeting_participant 表列注释
        exec(logs, "ALTER TABLE meeting_participant MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键'");
        exec(logs, "ALTER TABLE meeting_participant MODIFY COLUMN meeting_id BIGINT NOT NULL COMMENT '会议ID'");
        exec(logs, "ALTER TABLE meeting_participant MODIFY COLUMN user_id BIGINT NOT NULL COMMENT '用户ID'");
        exec(logs, "ALTER TABLE meeting_participant MODIFY COLUMN joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间'");
        exec(logs, "ALTER TABLE meeting_participant MODIFY COLUMN left_at DATETIME DEFAULT NULL COMMENT '离开时间'");

        return Result.success(logs);
    }

    /**
     * 清理评分详情和评分项的乱码数据，重新初始化
     */
    @PostMapping("/clean-score-data")
    public Result<String> cleanScoreData() {
        jdbc.execute("DELETE FROM score_detail");
        jdbc.execute("DELETE FROM score_item");
        jdbc.execute("DELETE FROM score_record");
        return Result.success("已清理 score_detail、score_item、score_record 表数据");
    }

    /**
     * 修复租户和评分模板的乱码数据
     */
    @PostMapping("/fix-data")
    public Result<String> fixData() {
        // 修复租户名称（只有 id=1 的默认学校）
        jdbc.update("UPDATE tenant SET name = ? WHERE id = 1", "默认学校");

        // 修复评分模板（只有 id=1 的模板）
        jdbc.update("UPDATE score_template SET name = ?, description = ? WHERE id = 1",
                "2025世界职业院校技能大赛总决赛评分模板",
                "根据2025年世界职业院校技能大赛总决赛评分要素制定，共5项评分指标，总分100分");

        return Result.success("已修复租户和评分模板数据");
    }

    /**
     * 创建聊天消息表
     */
    @PostMapping("/create-chat-table")
    public Result<String> createChatTable() {
        jdbc.execute("""
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
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表'
                """);
        return Result.success("已创建 chat_message 表");
    }

    /**
     * 补齐 PPT 讲稿与独立讲稿编辑的持久化关联字段。
     * 可重复执行：每一步都会先检查当前库结构。
     */
    @PostMapping("/fix-ppt-script-schema")
    public Result<List<String>> fixPptScriptSchema() {
        List<String> logs = new ArrayList<>();

        ensureColumn(logs, "script", "source_type",
                "ALTER TABLE script ADD COLUMN source_type VARCHAR(32) NOT NULL DEFAULT 'manual' COMMENT '来源: manual/ppt' AFTER roles");
        ensureColumn(logs, "script", "ppt_job_id",
                "ALTER TABLE script ADD COLUMN ppt_job_id VARCHAR(64) DEFAULT NULL COMMENT '关联 PPT 生成任务ID' AFTER source_type");
        ensureColumn(logs, "script", "sync_status",
                "ALTER TABLE script ADD COLUMN sync_status VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态' AFTER ppt_job_id");
        ensureColumn(logs, "script", "content_version",
                "ALTER TABLE script ADD COLUMN content_version INT NOT NULL DEFAULT 1 COMMENT '内容版本号' AFTER sync_status");
        ensureColumn(logs, "script", "last_synced_at",
                "ALTER TABLE script ADD COLUMN last_synced_at DATETIME DEFAULT NULL COMMENT '最近同步时间' AFTER content_version");
        exec(logs, "ALTER TABLE script MODIFY COLUMN meeting_id BIGINT DEFAULT NULL COMMENT '历史兼容字段，PPT讲稿不依赖会议ID'");

        dropIndexIfExists(logs, "script", "uk_meeting");
        dropIndexIfExists(logs, "script", "uk_meeting_user");
        ensureIndex(logs, "script", "uk_ppt_job_user",
                "ALTER TABLE script ADD UNIQUE KEY uk_ppt_job_user (ppt_job_id, created_by)");
        ensureIndex(logs, "script", "idx_script_source",
                "ALTER TABLE script ADD KEY idx_script_source (source_type, created_by)");

        ensureColumn(logs, "ppt_script_page", "script_id",
                "ALTER TABLE ppt_script_page ADD COLUMN script_id BIGINT DEFAULT NULL COMMENT '关联独立讲稿ID' AFTER created_by");
        ensureColumn(logs, "ppt_script_page", "script_step_id",
                "ALTER TABLE ppt_script_page ADD COLUMN script_step_id VARCHAR(64) DEFAULT NULL COMMENT '独立讲稿步骤ID' AFTER script_id");
        ensureColumn(logs, "ppt_script_page", "content_hash",
                "ALTER TABLE ppt_script_page ADD COLUMN content_hash VARCHAR(64) DEFAULT NULL COMMENT '讲稿内容哈希' AFTER script_step_id");
        ensureColumn(logs, "ppt_script_page", "version",
                "ALTER TABLE ppt_script_page ADD COLUMN version INT NOT NULL DEFAULT 1 COMMENT '页讲稿版本号' AFTER content_hash");
        ensureColumn(logs, "ppt_script_page", "sync_state",
                "ALTER TABLE ppt_script_page ADD COLUMN sync_state VARCHAR(32) NOT NULL DEFAULT 'synced' COMMENT '同步状态' AFTER version");
        ensureColumn(logs, "ppt_script_page", "last_synced_at",
                "ALTER TABLE ppt_script_page ADD COLUMN last_synced_at DATETIME DEFAULT NULL COMMENT '最近同步时间' AFTER sync_state");
        ensureIndex(logs, "ppt_script_page", "uk_job_page_user",
                "ALTER TABLE ppt_script_page ADD UNIQUE KEY uk_job_page_user (job_id, page_index, created_by)");
        ensureIndex(logs, "ppt_script_page", "idx_job_user",
                "ALTER TABLE ppt_script_page ADD KEY idx_job_user (job_id, created_by)");
        ensureIndex(logs, "ppt_script_page", "idx_created_by",
                "ALTER TABLE ppt_script_page ADD KEY idx_created_by (created_by)");
        ensureIndex(logs, "ppt_script_page", "idx_ppt_script_link",
                "ALTER TABLE ppt_script_page ADD KEY idx_ppt_script_link (script_id, script_step_id)");

        return Result.success(logs);
    }

    private void exec(List<String> logs, String sql) {
        try {
            jdbc.execute(sql);
            logs.add("OK: " + sql.substring(0, Math.min(60, sql.length())));
        } catch (Exception e) {
            logs.add("ERR: " + e.getMessage().substring(0, Math.min(80, e.getMessage().length())));
        }
    }

    private void ensureColumn(List<String> logs, String table, String column, String sql) {
        if (columnExists(table, column)) {
            logs.add("SKIP: " + table + "." + column + " exists");
            return;
        }
        exec(logs, sql);
    }

    private void ensureIndex(List<String> logs, String table, String index, String sql) {
        if (indexExists(table, index)) {
            logs.add("SKIP: " + table + "." + index + " exists");
            return;
        }
        exec(logs, sql);
    }

    private void dropIndexIfExists(List<String> logs, String table, String index) {
        if (!indexExists(table, index)) {
            logs.add("SKIP: " + table + "." + index + " absent");
            return;
        }
        exec(logs, "ALTER TABLE " + table + " DROP INDEX " + index);
    }

    private boolean columnExists(String table, String column) {
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = ?
                  AND COLUMN_NAME = ?
                """, Integer.class, table, column);
        return count != null && count > 0;
    }

    private boolean indexExists(String table, String index) {
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = ?
                  AND INDEX_NAME = ?
                """, Integer.class, table, index);
        return count != null && count > 0;
    }
}
