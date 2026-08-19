package com.orep.backend.service;

import com.orep.backend.dto.BatchDeleteResult;
import jakarta.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

@Service
public class HomeService {
    private final JdbcTemplate jdbc;

    public HomeService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void ensureSchema() {
        jdbc.execute("""
            CREATE TABLE IF NOT EXISTS home_banner (
              id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
              tenant_id BIGINT NOT NULL COMMENT '租户ID',
              title VARCHAR(120) NOT NULL COMMENT '标题',
              subtitle VARCHAR(500) DEFAULT NULL COMMENT '副标题',
              image_url VARCHAR(500) DEFAULT NULL COMMENT '图片地址',
              cta_text VARCHAR(40) DEFAULT NULL COMMENT '主按钮文案',
              cta_path VARCHAR(200) DEFAULT NULL COMMENT '主按钮地址',
              secondary_text VARCHAR(40) DEFAULT NULL COMMENT '次按钮文案',
              secondary_path VARCHAR(200) DEFAULT NULL COMMENT '次按钮地址',
              sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
              status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
              created_by BIGINT DEFAULT NULL COMMENT '创建人',
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
              PRIMARY KEY (id),
              KEY idx_home_banner_tenant_status (tenant_id, status, sort_order)
            ) COMMENT='用户端首页轮播图'
            """);
    }

    public Map<String, Object> userHome(Long tenantId, Long userId, String role) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("banners", activeBanners(tenantId));
        data.put("priority", priorityMetrics(tenantId, userId, role));
        data.put("mainEntries", mainEntries(tenantId, userId, role));
        data.put("quickEntries", quickEntries(tenantId, userId));
        data.put("nextActions", nextActions(tenantId, userId, role));
        return data;
    }

    public Map<String, Object> adminBanners(Long tenantId, String role, int page, int pageSize) {
        assertAdmin(role);
        int safePage = Math.max(1, page);
        int safeSize = Math.max(1, Math.min(50, pageSize));
        int offset = (safePage - 1) * safeSize;
        Integer total = jdbc.queryForObject("SELECT COUNT(*) FROM home_banner WHERE tenant_id = ?", Integer.class, tenantId);
        List<Map<String, Object>> items = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, title, subtitle, image_url imageUrl,
                   cta_text ctaText, cta_path ctaPath, secondary_text secondaryText,
                   secondary_path secondaryPath, sort_order sortOrder, status, created_at createdAt, updated_at updatedAt
            FROM home_banner
            WHERE tenant_id = ?
            ORDER BY sort_order ASC, id DESC
            LIMIT ? OFFSET ?
            """, tenantId, safeSize, offset);
        return Map.of(
                "items", items,
                "total", total == null ? 0 : total,
                "page", safePage,
                "pageSize", safeSize
        );
    }

    public Map<String, Object> createBanner(Long tenantId, Long userId, String role, Map<String, Object> body) {
        assertAdmin(role);
        jdbc.update("""
            INSERT INTO home_banner
            (tenant_id, title, subtitle, image_url, cta_text, cta_path, secondary_text, secondary_path, sort_order, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                tenantId,
                requiredText(body.get("title"), "轮播标题不能为空"),
                text(body.get("subtitle"), ""),
                text(body.get("imageUrl"), ""),
                text(body.get("ctaText"), "继续推进"),
                text(body.get("ctaPath"), "/project-team"),
                text(body.get("secondaryText"), ""),
                text(body.get("secondaryPath"), ""),
                intValue(body.get("sortOrder"), 0),
                normalizeBannerStatus(body.get("status")),
                userId
        );
        Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return bannerById(tenantId, id);
    }

    public Map<String, Object> updateBanner(Long tenantId, Long id, String role, Map<String, Object> body) {
        assertAdmin(role);
        if (bannerById(tenantId, id).isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "轮播不存在");
        }
        jdbc.update("""
            UPDATE home_banner
            SET title = ?, subtitle = ?, image_url = ?, cta_text = ?, cta_path = ?,
                secondary_text = ?, secondary_path = ?, sort_order = ?, status = ?
            WHERE tenant_id = ? AND id = ?
            """,
                requiredText(body.get("title"), "轮播标题不能为空"),
                text(body.get("subtitle"), ""),
                text(body.get("imageUrl"), ""),
                text(body.get("ctaText"), "继续推进"),
                text(body.get("ctaPath"), "/project-team"),
                text(body.get("secondaryText"), ""),
                text(body.get("secondaryPath"), ""),
                intValue(body.get("sortOrder"), 0),
                normalizeBannerStatus(body.get("status")),
                tenantId,
                id
        );
        return bannerById(tenantId, id);
    }

    public void deleteBanner(Long tenantId, Long id, String role) {
        assertAdmin(role);
        jdbc.update("DELETE FROM home_banner WHERE tenant_id = ? AND id = ?", tenantId, id);
    }

    public BatchDeleteResult deleteBanners(Long tenantId, List<Long> ids, String role) {
        assertAdmin(role);
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = ids == null ? List.of() : ids.stream().filter(Objects::nonNull).distinct().toList();
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            int rows = jdbc.update("DELETE FROM home_banner WHERE tenant_id = ? AND id = ?", tenantId, id);
            if (rows > 0) {
                result.addDeleted();
            } else {
                result.addFailure(id, "轮播不存在");
            }
        }
        return result;
    }

    private List<Map<String, Object>> activeBanners(Long tenantId) {
        return jdbc.queryForList("""
            SELECT id, title, subtitle, image_url imageUrl, cta_text ctaText, cta_path ctaPath,
                   secondary_text secondaryText, secondary_path secondaryPath
            FROM home_banner
            WHERE tenant_id = ? AND status = 'ACTIVE'
            ORDER BY sort_order ASC, id DESC
            LIMIT 6
            """, tenantId);
    }

    private Map<String, Object> priorityMetrics(Long tenantId, Long userId, String role) {
        int pendingTasks = queryInt("""
            SELECT COUNT(*)
            FROM project_task t
            JOIN project_team pt ON pt.id = t.team_id AND pt.tenant_id = ?
            WHERE t.owner_user_id = ? AND t.status <> 'DONE'
            """, tenantId, userId);
        int pendingReview = canUseTeacherScope(role)
                ? queryInt("""
                    SELECT COUNT(*)
                    FROM project_task_submission s
                    JOIN project_team pt ON pt.id = s.team_id AND pt.tenant_id = ?
                    WHERE s.status = 'PENDING_REVIEW'
                    """, tenantId)
                : queryInt("""
                    SELECT COUNT(*)
                    FROM project_task_submission s
                    JOIN project_team_member m ON m.team_id = s.team_id AND m.user_id = ? AND m.role_in_team = 'CAPTAIN'
                    JOIN project_team pt ON pt.id = s.team_id AND pt.tenant_id = ?
                    WHERE s.status = 'PENDING_REVIEW'
                    """, userId, tenantId);
        int availableExams = queryInt("SELECT COUNT(*) FROM exam_paper WHERE status = 'published'");
        int reviewIssues = queryInt("""
            SELECT COUNT(*)
            FROM project_review_issue i
            JOIN project_team pt ON pt.id = i.team_id AND pt.tenant_id = ?
            LEFT JOIN project_team_member m ON m.team_id = i.team_id AND m.user_id = ?
            WHERE i.status <> 'DONE' AND (i.owner_user_id IS NULL OR i.owner_user_id = ? OR m.role_in_team IN ('CAPTAIN', 'MENTOR'))
            """, tenantId, userId, userId);
        return Map.of(
                "pendingTasks", pendingTasks,
                "pendingReviews", pendingReview,
                "availableExams", availableExams,
                "reviewIssues", reviewIssues
        );
    }

    private List<Map<String, Object>> mainEntries(Long tenantId, Long userId, String role) {
        int teamCount = queryInt("""
            SELECT COUNT(DISTINCT pt.id)
            FROM project_team pt
            LEFT JOIN project_team_member m ON m.team_id = pt.id AND m.user_id = ?
            WHERE pt.tenant_id = ? AND (? = 1 OR m.id IS NOT NULL)
            """, userId, tenantId, canUseTeacherScope(role) ? 1 : 0);
        int openTasks = queryInt("""
            SELECT COUNT(*)
            FROM project_task t
            JOIN project_team pt ON pt.id = t.team_id AND pt.tenant_id = ?
            WHERE t.owner_user_id = ? AND t.status <> 'DONE'
            """, tenantId, userId);
        int courseCount = queryInt("SELECT COUNT(*) FROM course WHERE status = 'published'");
        int courseProgress = queryInt("""
            SELECT COALESCE(ROUND(AVG(progress_percent)), 0)
            FROM course_learning_progress
            WHERE user_id = ?
            """, userId);
        int paperCount = queryInt("SELECT COUNT(*) FROM exam_paper WHERE status = 'published'");
        int wrongCount = queryInt("SELECT COUNT(*) FROM exam_wrong_question WHERE user_id = ?", userId);
        return List.of(
                entry("TEAM", "项目团队", "推进任务、材料、路演和复盘闭环", "/project-team", teamCount + " 个项目", openTasks + " 项待办"),
                entry("LEARN", "课程学习", "继续课程目录、附件和学习进度", "/course-learning", courseProgress + "% 平均进度", courseCount + " 门课程"),
                entry("EXAM", "考试系统", "参加测评、训练错题并收藏题目", "/exam-system", paperCount + " 场可参加", wrongCount + " 道错题")
        );
    }

    private List<Map<String, Object>> quickEntries(Long tenantId, Long userId) {
        int meetings = queryInt("""
            SELECT COUNT(DISTINCT mp.meeting_id)
            FROM meeting_participant mp
            JOIN meeting m ON m.id = mp.meeting_id AND m.tenant_id = ?
            WHERE mp.user_id = ?
            """, tenantId, userId);
        return List.of(
                entry("MEET", "在线会议", "进入路演会议", "/online-meeting", meetings + " 次参与", ""),
                entry("PPT", "AI PPT生成", "生成路演材料", "/ppt-editor", "可用", ""),
                entry("SCRIPT", "讲稿编辑", "沉淀表达稿", "/script-editor", "可编辑", ""),
                entry("REC", "我的录制", "查看会议录制", "/my-recordings", "录制库", ""),
                entry("DATA", "数据分析", "查看评分趋势", "/statistics", "复盘数据", ""),
                entry("RES", "资源中心", "下载模板资料", "/resources", "资料库", "")
        );
    }

    private List<Map<String, Object>> nextActions(Long tenantId, Long userId, String role) {
        List<Map<String, Object>> actions = new ArrayList<>();
        actions.addAll(safeQuery("""
            SELECT 'TASK' source, t.title title, CONCAT('截止：', COALESCE(DATE_FORMAT(t.due_at, '%m-%d %H:%i'), '未设置')) meta,
                   '/project-team' path, '去提交' actionText
            FROM project_task t
            JOIN project_team pt ON pt.id = t.team_id AND pt.tenant_id = ?
            WHERE t.owner_user_id = ? AND t.status <> 'DONE'
            ORDER BY t.due_at IS NULL, t.due_at ASC, t.id DESC
            LIMIT 2
            """, tenantId, userId));
        if (actions.size() < 3) {
            actions.addAll(safeQuery("""
                SELECT 'EXAM' source, p.title title,
                       CONCAT('已开始 · ', COALESCE(DATE_FORMAT(a.deadline_at, '%m-%d %H:%i'), CONCAT(p.duration_minutes, ' 分钟测评'))) meta,
                       '/exam-system' path, '继续测评' actionText
                FROM exam_attempt a
                JOIN exam_paper p ON p.id = a.paper_id
                WHERE a.user_id = ? AND LOWER(a.status) = 'in_progress'
                ORDER BY a.deadline_at IS NULL, a.deadline_at ASC, a.id DESC
                LIMIT ?
                """, userId, 3 - actions.size()));
        }
        return actions.stream().limit(3).toList();
    }

    private Map<String, Object> entry(String code, String title, String description, String path, String primaryMetric, String secondaryMetric) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("code", code);
        item.put("title", title);
        item.put("description", description);
        item.put("path", path);
        item.put("primaryMetric", primaryMetric);
        item.put("secondaryMetric", secondaryMetric);
        return item;
    }

    private Map<String, Object> bannerById(Long tenantId, Long id) {
        if (id == null) return Map.of();
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, title, subtitle, image_url imageUrl,
                   cta_text ctaText, cta_path ctaPath, secondary_text secondaryText,
                   secondary_path secondaryPath, sort_order sortOrder, status, created_at createdAt, updated_at updatedAt
            FROM home_banner
            WHERE tenant_id = ? AND id = ?
            """, tenantId, id);
        return rows.isEmpty() ? Map.of() : rows.get(0);
    }

    private List<Map<String, Object>> safeQuery(String sql, Object... args) {
        try {
            return jdbc.queryForList(sql, args);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private int queryInt(String sql, Object... args) {
        try {
            Integer value = jdbc.queryForObject(sql, Integer.class, args);
            return value == null ? 0 : value;
        } catch (Exception ignored) {
            return 0;
        }
    }

    private void assertAdmin(String role) {
        if (!Set.of("ADMIN", "SCHOOL_ADMIN").contains(String.valueOf(role).toUpperCase(Locale.ROOT))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权维护首页轮播");
        }
    }

    private boolean canUseTeacherScope(String role) {
        return Set.of("ADMIN", "SCHOOL_ADMIN", "TEACHER").contains(String.valueOf(role).toUpperCase(Locale.ROOT));
    }

    private String normalizeBannerStatus(Object value) {
        String status = text(value, "ACTIVE").toUpperCase(Locale.ROOT);
        return "INACTIVE".equals(status) ? "INACTIVE" : "ACTIVE";
    }

    private String requiredText(Object value, String message) {
        String text = nullableText(value);
        if (text == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
        return text;
    }

    private String text(Object value, String fallback) {
        String text = nullableText(value);
        return text == null ? fallback : text;
    }

    private String nullableText(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isBlank() ? null : text;
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) return number.intValue();
        String text = nullableText(value);
        if (text == null) return fallback;
        try {
            return Integer.parseInt(text);
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        String text = nullableText(value);
        if (text == null) return null;
        try {
            return Long.parseLong(text);
        } catch (Exception ignored) {
            return null;
        }
    }
}
