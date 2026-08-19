package com.orep.backend.service;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.sql.Date;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * 备赛日报：一人一天一份，不依赖训练营（camp_id 可空）。
 * 内容字段支持富文本 HTML（图片等）。
 */
@Service
public class DailyReportService {

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");
    private static final int MAX_HTML_LEN = 50_000;
    private static final Pattern SCRIPT_TAG = Pattern.compile("(?is)<script[^>]*>.*?</script>");
    private static final Pattern EVENT_ATTR = Pattern.compile("(?i)\\s+on[a-z]+\\s*=\\s*(\"[^\"]*\"|'[^']*'|[^\\s>]+)");
    private static final Pattern JS_HREF = Pattern.compile("(?i)\\s(href|src)\\s*=\\s*([\"'])\\s*javascript:[^\"']*\\2");

    private final JdbcTemplate jdbc;
    private volatile boolean schemaReady = false;

    public DailyReportService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Map<String, Object> today(Long tenantId, Long userId) {
        return bundleForDate(tenantId, userId, LocalDate.now(ZONE));
    }

    public Map<String, Object> forDate(Long tenantId, Long userId, String dateStr) {
        ensureSchema();
        LocalDate today = LocalDate.now(ZONE);
        LocalDate requested = parseDate(dateStr);
        try {
            return bundleForDate(tenantId, userId, DailyReportDatePolicy.resolveWritableDate(today, requested));
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, e.getMessage());
        }
    }

    private Map<String, Object> bundleForDate(Long tenantId, Long userId, LocalDate date) {
        ensureSchema();
        Map<String, Object> report = findByDate(tenantId, userId, date);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("reportDate", date.toString());
        result.put("submitted", report != null && "SUBMITTED".equals(text(report.get("status"), "")));
        result.put("report", enrich(report));
        result.put("contextType", resolveContextType(tenantId, userId));
        result.put("canBackfill", DailyReportDatePolicy.isBackfillAllowed(LocalDate.now(ZONE), date));
        return result;
    }

    public Map<String, Object> getById(Long tenantId, Long userId, Long id) {
        ensureSchema();
        Map<String, Object> row = findById(tenantId, userId, id);
        if (row == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "日报不存在");
        }
        return enrich(row);
    }

    public Map<String, Object> getOrCreate(Long tenantId, Long userId, String dateStr) {
        ensureSchema();
        LocalDate date = parseDate(dateStr);
        Map<String, Object> existing = findByDate(tenantId, userId, date);
        if (existing != null) return enrich(existing);
        String contextType = resolveContextType(tenantId, userId);
        Long campId = currentCampId(tenantId, userId);
        Long teamId = currentTeamId(tenantId, userId);
        jdbc.update("""
            INSERT INTO daily_report (
              tenant_id, user_id, report_date, camp_id, team_id, context_type,
              content_done, content_blocker, content_next, effort_hours, mood, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, '', '', '', NULL, NULL, 'DRAFT', ?, ?)
            """,
                tenantId, userId, Date.valueOf(date), campId, teamId, contextType,
                Timestamp.from(Instant.now()), Timestamp.from(Instant.now()));
        return enrich(findByDate(tenantId, userId, date));
    }

    public Map<String, Object> save(Long tenantId, Long userId, Map<String, Object> body) {
        ensureSchema();
        LocalDate date;
        try {
            date = DailyReportDatePolicy.resolveWritableDate(
                    LocalDate.now(ZONE), parseDate(text(body.get("reportDate"), null)));
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, e.getMessage());
        }
        Map<String, Object> existing = findByDate(tenantId, userId, date);
        if (existing == null) {
            existing = getOrCreate(tenantId, userId, date.toString());
        }
        Long id = longVal(existing.get("id"), null);
        String done = sanitizeHtml(text(body.get("contentDone"), text(existing.get("contentDone"), "")));
        String blocker = sanitizeHtml(text(body.get("contentBlocker"), text(existing.get("contentBlocker"), "")));
        String next = sanitizeHtml(text(body.get("contentNext"), text(existing.get("contentNext"), "")));
        Double hours = body.containsKey("effortHours") ? doubleOrNull(body.get("effortHours")) : doubleOrNull(existing.get("effortHours"));
        String mood = body.containsKey("mood") ? text(body.get("mood"), null) : text(existing.get("mood"), null);
        boolean submit = Boolean.TRUE.equals(body.get("submit"))
                || "SUBMITTED".equalsIgnoreCase(text(body.get("status"), ""));

        if (done != null && done.length() > MAX_HTML_LEN) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "「今天做了什么」内容过长");
        }
        if (blocker != null && blocker.length() > MAX_HTML_LEN) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "「卡点」内容过长");
        }
        if (next != null && next.length() > MAX_HTML_LEN) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "「明天计划」内容过长");
        }

        if (submit) {
            if (plainText(done).isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请填写「今天做了什么」");
            }
            if (plainText(next).isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请填写「明天计划」");
            }
        }

        String status = submit ? "SUBMITTED" : "DRAFT";
        Timestamp submittedAt = submit ? Timestamp.from(Instant.now()) : null;

        jdbc.update("""
            UPDATE daily_report
            SET content_done = ?, content_blocker = ?, content_next = ?,
                effort_hours = ?, mood = ?, status = ?,
                submitted_at = CASE WHEN ? = 'SUBMITTED' THEN COALESCE(?, submitted_at, NOW()) ELSE submitted_at END,
                updated_at = NOW()
            WHERE id = ? AND tenant_id = ? AND user_id = ?
            """,
                done, blocker == null ? "" : blocker, next,
                hours, mood, status,
                status, submittedAt,
                id, tenantId, userId);

        return enrich(findByDate(tenantId, userId, date));
    }

    public List<Map<String, Object>> history(Long tenantId, Long userId, Integer limit) {
        ensureSchema();
        int lim = limit == null ? 30 : Math.min(90, Math.max(1, limit));
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, report_date reportDate, camp_id campId, team_id teamId, context_type contextType,
                   content_done contentDone, content_blocker contentBlocker, content_next contentNext,
                   effort_hours effortHours, mood, status, submitted_at submittedAt, updated_at updatedAt
            FROM daily_report
            WHERE tenant_id = ? AND user_id = ?
            ORDER BY report_date DESC, id DESC
            LIMIT ?
            """, tenantId, userId, lim);
        List<Map<String, Object>> out = new ArrayList<>(rows.size());
        for (Map<String, Object> row : rows) {
            out.add(enrich(row));
        }
        return out;
    }

    /** 个人日报统计：连续天数、近 7/30 天完成率、累计提交等 */
    public Map<String, Object> stats(Long tenantId, Long userId) {
        ensureSchema();
        LocalDate today = LocalDate.now(ZONE);
        List<Map<String, Object>> submittedDates = jdbc.queryForList("""
            SELECT report_date AS reportDate
            FROM daily_report
            WHERE tenant_id = ? AND user_id = ? AND status = 'SUBMITTED'
            ORDER BY report_date DESC
            LIMIT 120
            """, tenantId, userId);

        int totalSubmitted = submittedDates.size();
        Integer totalAll = jdbc.queryForObject("""
            SELECT COUNT(*) FROM daily_report WHERE tenant_id = ? AND user_id = ?
            """, Integer.class, tenantId, userId);

        int last7Submitted = 0;
        int last30Submitted = 0;
        LocalDate d7 = today.minusDays(6);
        LocalDate d30 = today.minusDays(29);
        for (Map<String, Object> row : submittedDates) {
            LocalDate d = toLocalDate(row.get("reportDate"));
            if (d == null) continue;
            if (!d.isBefore(d7) && !d.isAfter(today)) last7Submitted++;
            if (!d.isBefore(d30) && !d.isAfter(today)) last30Submitted++;
        }

        int streak = 0;
        // 连续：从今天或昨天起往回数（今天未交则从昨天开始，避免断 streak 太狠）
        java.util.Set<String> set = new java.util.HashSet<>();
        for (Map<String, Object> row : submittedDates) {
            LocalDate d = toLocalDate(row.get("reportDate"));
            if (d != null) set.add(d.toString());
        }
        LocalDate cursor = today;
        if (!set.contains(today.toString())) {
            cursor = today.minusDays(1);
        }
        while (set.contains(cursor.toString())) {
            streak++;
            cursor = cursor.minusDays(1);
            if (streak > 365) break;
        }

        Map<String, Object> todayBundle = today(tenantId, userId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("todaySubmitted", Boolean.TRUE.equals(todayBundle.get("submitted")));
        result.put("todayReportId", todayBundle.get("report") instanceof Map<?, ?> r ? r.get("id") : null);
        result.put("streakDays", streak);
        result.put("totalSubmitted", totalSubmitted);
        result.put("totalRecords", totalAll == null ? 0 : totalAll);
        result.put("last7Submitted", last7Submitted);
        result.put("last7Rate", Math.round(last7Submitted * 1000.0 / 7.0) / 10.0);
        result.put("last30Submitted", last30Submitted);
        result.put("last30Rate", Math.round(last30Submitted * 1000.0 / 30.0) / 10.0);
        // 近 14 天打卡矩阵（含今天）
        List<Map<String, Object>> calendar = new ArrayList<>();
        for (int i = 13; i >= 0; i--) {
            LocalDate d = today.minusDays(i);
            Map<String, Object> cell = new LinkedHashMap<>();
            cell.put("date", d.toString());
            cell.put("submitted", set.contains(d.toString()));
            cell.put("isToday", d.equals(today));
            calendar.add(cell);
        }
        result.put("calendar14", calendar);
        return result;
    }

    /** 是否今日未交（用于待办红点） */
    public boolean isTodayPending(Long tenantId, Long userId) {
        ensureSchema();
        Map<String, Object> t = today(tenantId, userId);
        return !Boolean.TRUE.equals(t.get("submitted"));
    }

    private Map<String, Object> enrich(Map<String, Object> row) {
        if (row == null) return null;
        Map<String, Object> out = new LinkedHashMap<>(row);
        String done = text(row.get("contentDone"), "");
        String blocker = text(row.get("contentBlocker"), "");
        String next = text(row.get("contentNext"), "");
        out.put("preview", truncate(plainText(done), 80));
        out.put("hasImages", done.contains("<img") || blocker.contains("<img") || next.contains("<img"));
        Object rd = row.get("reportDate");
        if (rd instanceof Date sqlDate) {
            out.put("reportDate", sqlDate.toLocalDate().toString());
        } else if (rd instanceof java.util.Date utilDate) {
            out.put("reportDate", Instant.ofEpochMilli(utilDate.getTime()).atZone(ZONE).toLocalDate().toString());
        }
        return out;
    }

    private Map<String, Object> findById(Long tenantId, Long userId, Long id) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, user_id userId, report_date reportDate,
                   camp_id campId, team_id teamId, context_type contextType,
                   content_done contentDone, content_blocker contentBlocker, content_next contentNext,
                   effort_hours effortHours, mood, status,
                   submitted_at submittedAt, created_at createdAt, updated_at updatedAt
            FROM daily_report
            WHERE id = ? AND tenant_id = ? AND user_id = ?
            LIMIT 1
            """, id, tenantId, userId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Map<String, Object> findByDate(Long tenantId, Long userId, LocalDate date) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT id, tenant_id tenantId, user_id userId, report_date reportDate,
                   camp_id campId, team_id teamId, context_type contextType,
                   content_done contentDone, content_blocker contentBlocker, content_next contentNext,
                   effort_hours effortHours, mood, status,
                   submitted_at submittedAt, created_at createdAt, updated_at updatedAt
            FROM daily_report
            WHERE tenant_id = ? AND user_id = ? AND report_date = ?
            LIMIT 1
            """, tenantId, userId, Date.valueOf(date));
        return rows.isEmpty() ? null : rows.get(0);
    }

    private String resolveContextType(Long tenantId, Long userId) {
        boolean hasCamp = currentCampId(tenantId, userId) != null;
        if (hasCamp) return "CAMP";
        try {
            Integer meetings = jdbc.queryForObject("""
                SELECT COUNT(*) FROM meeting m
                WHERE m.tenant_id = ? AND m.creator_id = ?
                  AND m.created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
                """, Integer.class, tenantId, userId);
            if (meetings != null && meetings > 0) return "ROADSHOW";
        } catch (Exception ignored) {
            // meeting 表结构差异或无表时，降级为 FREE
        }
        return "FREE";
    }

    private Long currentCampId(Long tenantId, Long userId) {
        List<Long> ids = jdbc.query("""
            SELECT c.id
            FROM training_camp c
            JOIN training_camp_team ct ON ct.camp_id = c.id AND ct.status = 'ACTIVE'
            JOIN project_team pt ON pt.id = ct.team_id AND pt.tenant_id = c.tenant_id
            JOIN project_team_member tm ON tm.team_id = pt.id AND tm.user_id = ?
            WHERE c.tenant_id = ? AND c.status IN ('PLANNED', 'ACTIVE')
            ORDER BY c.start_date DESC, c.id DESC
            LIMIT 1
            """, (rs, i) -> rs.getLong(1), userId, tenantId);
        return ids.isEmpty() ? null : ids.get(0);
    }

    private Long currentTeamId(Long tenantId, Long userId) {
        List<Long> ids = jdbc.query("""
            SELECT pt.id
            FROM project_team pt
            JOIN project_team_member tm ON tm.team_id = pt.id AND tm.user_id = ?
            WHERE pt.tenant_id = ?
            ORDER BY pt.updated_at DESC
            LIMIT 1
            """, (rs, i) -> rs.getLong(1), userId, tenantId);
        return ids.isEmpty() ? null : ids.get(0);
    }

    private void ensureSchema() {
        if (schemaReady) return;
        synchronized (this) {
            if (schemaReady) return;
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS daily_report (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  tenant_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  report_date DATE NOT NULL,
                  camp_id BIGINT DEFAULT NULL,
                  team_id BIGINT DEFAULT NULL,
                  context_type VARCHAR(32) NOT NULL DEFAULT 'FREE',
                  content_done TEXT,
                  content_blocker TEXT,
                  content_next TEXT,
                  effort_hours DECIMAL(4,1) DEFAULT NULL,
                  mood VARCHAR(32) DEFAULT NULL,
                  status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
                  submitted_at DATETIME DEFAULT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_daily_report_user_day (user_id, report_date),
                  KEY idx_daily_report_tenant_day (tenant_id, report_date),
                  KEY idx_daily_report_camp (camp_id, report_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """);
            schemaReady = true;
        }
    }

    private LocalDate parseDate(String s) {
        if (s == null || s.isBlank()) return LocalDate.now(ZONE);
        try {
            return LocalDate.parse(s.trim());
        } catch (Exception e) {
            return LocalDate.now(ZONE);
        }
    }

    private static LocalDate toLocalDate(Object v) {
        if (v == null) return null;
        if (v instanceof Date d) return d.toLocalDate();
        if (v instanceof java.util.Date ud) {
            return Instant.ofEpochMilli(ud.getTime()).atZone(ZONE).toLocalDate();
        }
        if (v instanceof LocalDate ld) return ld;
        try {
            return LocalDate.parse(String.valueOf(v).substring(0, 10));
        } catch (Exception e) {
            return null;
        }
    }

    /** 基础 HTML 消毒：去 script / on* / javascript: */
    static String sanitizeHtml(String html) {
        if (html == null) return "";
        String s = html;
        s = SCRIPT_TAG.matcher(s).replaceAll("");
        s = EVENT_ATTR.matcher(s).replaceAll("");
        s = JS_HREF.matcher(s).replaceAll("");
        return s.trim();
    }

    static String plainText(String html) {
        if (html == null || html.isBlank()) return "";
        String s = html
                .replaceAll("(?is)<br\\s*/?>", "\n")
                .replaceAll("(?is)</p>", "\n")
                .replaceAll("(?is)<[^>]+>", " ")
                .replace("&nbsp;", " ")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replaceAll("\\s+", " ")
                .trim();
        return s;
    }

    private static String truncate(String s, int max) {
        if (s == null) return "";
        if (s.length() <= max) return s;
        return s.substring(0, max) + "…";
    }

    private static String text(Object v, String def) {
        if (v == null) return def;
        String s = String.valueOf(v).trim();
        return s.isEmpty() ? def : s;
    }

    private static Long longVal(Object v, Long def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static Double doubleOrNull(Object v) {
        if (v == null || "".equals(String.valueOf(v).trim())) return null;
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }
}
