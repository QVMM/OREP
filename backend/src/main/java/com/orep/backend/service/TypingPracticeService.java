package com.orep.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 打字练习：会话落库 + 同组织（租户）排位榜。
 * 排位榜仅统计 mode=ranked 的有效成绩，按用户取最佳 CPM。
 */
@Service
public class TypingPracticeService {

    private static final Logger log = LoggerFactory.getLogger(TypingPracticeService.class);
    private static final String RANKED_MODE = "ranked";
    private static final int LEADERBOARD_LIMIT = 50;

    private final JdbcTemplate jdbc;
    private volatile boolean schemaReady = false;

    public TypingPracticeService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Map<String, Object> saveSession(Long tenantId, Long userId, Map<String, Object> body) {
        ensureSchema();
        if (tenantId == null || userId == null) {
            throw new RuntimeException("未登录");
        }

        String requestedMode = text(body.get("mode"), "practice").toLowerCase(Locale.ROOT);
        if (!"practice".equals(requestedMode) && !RANKED_MODE.equals(requestedMode)
                && !"timed".equals(requestedMode) && !"count".equals(requestedMode)) {
            requestedMode = "practice";
        }
        // 旧前端 timed/count 归入 practice
        if ("timed".equals(requestedMode) || "count".equals(requestedMode)) {
            requestedMode = "practice";
        }

        int durationSec = intVal(body.get("durationSec"), 0);
        int targetCount = intVal(body.get("targetCount"), 0);
        int cpm = Math.max(0, intVal(body.get("cpm"), 0));
        double accuracy = Math.max(0, Math.min(100, doubleVal(body.get("accuracy"), 0)));
        int correctChars = Math.max(0, intVal(body.get("correctChars"), 0));
        int totalKeystrokes = Math.max(0, intVal(body.get("totalKeystrokes"), 0));
        long elapsedMs = Math.max(0L, longVal(body.get("elapsedMs"), 0L));
        String lang = text(body.get("lang"), "zh");
        int difficulty = intVal(body.get("difficulty"), 2);
        String textVersion = text(body.get("textVersion"), null);
        String sourceType = text(body.get("sourceType"), "catalog");
        String clientSessionId = TypingSessionPolicy.normalizeClientSessionId(
                text(body.get("clientSessionId"), null));

        String mode = TypingSessionPolicy.resolveMode(requestedMode, elapsedMs, correctChars, textVersion);
        boolean rankedDowngraded = RANKED_MODE.equals(requestedMode) && !RANKED_MODE.equals(mode);
        String reason = text(body.get("reason"), "complete");
        log.info(
                "typing_session save reason={} httpStatus=200 elapsedMs={} rankedDowngraded={} mode={} clientSessionId={} userId={}",
                reason, elapsedMs, rankedDowngraded, mode, clientSessionId, userId);

        Long id = upsertSession(
                tenantId, userId, clientSessionId, mode, durationSec, targetCount,
                cpm, accuracy, correctChars, totalKeystrokes, elapsedMs,
                lang, difficulty, textVersion, sourceType);

        Map<String, Object> result = new HashMap<>();
        result.put("id", id);
        result.put("mode", mode);
        result.put("cpm", cpm);
        result.put("accuracy", accuracy);
        result.put("elapsedMs", elapsedMs);
        if (rankedDowngraded) {
            result.put("rankedDowngraded", true);
        }

        if (RANKED_MODE.equals(mode)) {
            result.put("rank", resolveUserRank(tenantId, userId, textVersion));
            result.put("leaderboard", leaderboard(tenantId, userId, textVersion, LEADERBOARD_LIMIT));
        }
        return result;
    }

    private Long upsertSession(
            Long tenantId,
            Long userId,
            String clientSessionId,
            String mode,
            int durationSec,
            int targetCount,
            int cpm,
            double accuracy,
            int correctChars,
            int totalKeystrokes,
            long elapsedMs,
            String lang,
            int difficulty,
            String textVersion,
            String sourceType
    ) {
        Timestamp now = Timestamp.from(Instant.now());
        if (clientSessionId != null) {
            jdbc.update("""
                INSERT INTO typing_session (
                  tenant_id, user_id, client_session_id, mode, duration_sec, target_count,
                  cpm, accuracy, correct_chars, total_keystrokes, elapsed_ms,
                  lang, difficulty, text_version, source_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON DUPLICATE KEY UPDATE
                  id = LAST_INSERT_ID(id),
                  mode = VALUES(mode),
                  duration_sec = VALUES(duration_sec),
                  target_count = VALUES(target_count),
                  cpm = VALUES(cpm),
                  accuracy = VALUES(accuracy),
                  correct_chars = VALUES(correct_chars),
                  total_keystrokes = VALUES(total_keystrokes),
                  elapsed_ms = GREATEST(COALESCE(elapsed_ms, 0), VALUES(elapsed_ms)),
                  lang = VALUES(lang),
                  difficulty = VALUES(difficulty),
                  text_version = COALESCE(VALUES(text_version), text_version),
                  source_type = VALUES(source_type)
                """,
                    tenantId, userId, clientSessionId, mode, durationSec, targetCount,
                    cpm, accuracy, correctChars, totalKeystrokes, elapsedMs,
                    lang, difficulty, textVersion, sourceType, now);
        } else {
            jdbc.update("""
                INSERT INTO typing_session (
                  tenant_id, user_id, mode, duration_sec, target_count,
                  cpm, accuracy, correct_chars, total_keystrokes, elapsed_ms,
                  lang, difficulty, text_version, source_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    tenantId, userId, mode, durationSec, targetCount,
                    cpm, accuracy, correctChars, totalKeystrokes, elapsedMs,
                    lang, difficulty, textVersion, sourceType, now);
        }
        return jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
    }

    public Map<String, Object> leaderboard(Long tenantId, Long viewerUserId, String textVersion, Integer limit) {
        ensureSchema();
        if (tenantId == null) {
            throw new RuntimeException("未登录");
        }
        int lim = limit == null ? LEADERBOARD_LIMIT : Math.min(100, Math.max(1, limit));
        String version = textVersion == null || textVersion.isBlank() ? latestRankedVersion(tenantId) : textVersion;

        List<Map<String, Object>> rows;
        if (version == null) {
            rows = List.of();
        } else {
            // 每人取最高 CPM 的一条（同 CPM 取最早 id），再排序截断
            rows = jdbc.queryForList("""
                SELECT
                  t.user_id AS userId,
                  u.username AS username,
                  u.school_name AS schoolName,
                  u.class_name AS className,
                  t.cpm AS cpm,
                  t.accuracy AS accuracy,
                  t.correct_chars AS correctChars,
                  t.elapsed_ms AS elapsedMs,
                  t.created_at AS createdAt
                FROM typing_session t
                INNER JOIN (
                  SELECT user_id, MAX(cpm) AS max_cpm
                  FROM typing_session
                  WHERE tenant_id = ? AND mode = ? AND text_version = ?
                  GROUP BY user_id
                ) best ON best.user_id = t.user_id AND best.max_cpm = t.cpm
                INNER JOIN (
                  SELECT s.user_id, MIN(s.id) AS sid
                  FROM typing_session s
                  INNER JOIN (
                    SELECT user_id, MAX(cpm) AS max_cpm
                    FROM typing_session
                    WHERE tenant_id = ? AND mode = ? AND text_version = ?
                    GROUP BY user_id
                  ) b ON b.user_id = s.user_id AND b.max_cpm = s.cpm
                  WHERE s.tenant_id = ? AND s.mode = ? AND s.text_version = ?
                  GROUP BY s.user_id
                ) pick ON pick.sid = t.id
                LEFT JOIN users u ON u.id = t.user_id
                ORDER BY t.cpm DESC, t.accuracy DESC, t.created_at ASC
                LIMIT ?
                """,
                    tenantId, RANKED_MODE, version,
                    tenantId, RANKED_MODE, version,
                    tenantId, RANKED_MODE, version,
                    lim);
        }

        List<Map<String, Object>> list = new ArrayList<>();
        int rank = 1;
        Integer myRank = null;
        Map<String, Object> me = null;
        for (Map<String, Object> row : rows) {
            Map<String, Object> item = new HashMap<>();
            Long uid = longVal(row.get("userId"), null);
            item.put("rank", rank);
            item.put("userId", uid);
            item.put("username", maskName(String.valueOf(row.get("username") == null ? "用户" : row.get("username"))));
            item.put("schoolName", row.get("schoolName"));
            item.put("className", row.get("className"));
            item.put("cpm", row.get("cpm"));
            item.put("accuracy", row.get("accuracy"));
            item.put("correctChars", row.get("correctChars"));
            item.put("elapsedMs", row.get("elapsedMs"));
            item.put("createdAt", row.get("createdAt"));
            item.put("isMe", viewerUserId != null && viewerUserId.equals(uid));
            if (Boolean.TRUE.equals(item.get("isMe"))) {
                myRank = rank;
                me = item;
            }
            list.add(item);
            rank += 1;
        }

        if (viewerUserId != null && myRank == null && version != null) {
            myRank = resolveUserRank(tenantId, viewerUserId, version);
            me = myBest(tenantId, viewerUserId, version);
            if (me != null) {
                me.put("rank", myRank);
                me.put("isMe", true);
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("textVersion", version);
        result.put("total", list.size());
        result.put("list", list);
        result.put("myRank", myRank);
        result.put("me", me);
        return result;
    }

    public Map<String, Object> myStats(Long tenantId, Long userId) {
        ensureSchema();
        if (tenantId == null || userId == null) {
            throw new RuntimeException("未登录");
        }
        Map<String, Object> stats = new HashMap<>();
        Integer practiceCount = jdbc.queryForObject(
                "SELECT COUNT(*) FROM typing_session WHERE tenant_id = ? AND user_id = ?",
                Integer.class, tenantId, userId);
        Integer rankedCount = jdbc.queryForObject(
                "SELECT COUNT(*) FROM typing_session WHERE tenant_id = ? AND user_id = ? AND mode = ?",
                Integer.class, tenantId, userId, RANKED_MODE);
        Integer bestPractice = jdbc.queryForObject(
                "SELECT COALESCE(MAX(cpm), 0) FROM typing_session WHERE tenant_id = ? AND user_id = ? AND mode = 'practice'",
                Integer.class, tenantId, userId);
        Integer bestRanked = jdbc.queryForObject(
                "SELECT COALESCE(MAX(cpm), 0) FROM typing_session WHERE tenant_id = ? AND user_id = ? AND mode = ?",
                Integer.class, tenantId, userId, RANKED_MODE);
        Double avgAcc = jdbc.queryForObject(
                "SELECT COALESCE(AVG(accuracy), 0) FROM typing_session WHERE tenant_id = ? AND user_id = ?",
                Double.class, tenantId, userId);
        Double avgCpm = jdbc.queryForObject(
                "SELECT COALESCE(AVG(cpm), 0) FROM typing_session WHERE tenant_id = ? AND user_id = ?",
                Double.class, tenantId, userId);
        Double avgCpm7d = jdbc.queryForObject("""
                SELECT COALESCE(AVG(cpm), 0) FROM typing_session
                WHERE tenant_id = ? AND user_id = ?
                  AND created_at >= CURDATE() - INTERVAL 6 DAY
                """, Double.class, tenantId, userId);
        Long totalElapsedMs = jdbc.queryForObject(
                "SELECT COALESCE(SUM(elapsed_ms), 0) FROM typing_session WHERE tenant_id = ? AND user_id = ?",
                Long.class, tenantId, userId);
        Integer totalSessions = practiceCount == null ? 0 : practiceCount;

        stats.put("practiceCount", totalSessions);
        stats.put("sessionCount", totalSessions);
        stats.put("rankedCount", rankedCount == null ? 0 : rankedCount);
        stats.put("bestPracticeCpm", bestPractice == null ? 0 : bestPractice);
        stats.put("bestRankedCpm", bestRanked == null ? 0 : bestRanked);
        stats.put("bestCpm", Math.max(
                bestPractice == null ? 0 : bestPractice,
                bestRanked == null ? 0 : bestRanked
        ));
        stats.put("avgAccuracy", avgAcc == null ? 0 : Math.round(avgAcc * 10.0) / 10.0);
        stats.put("avgCpm", avgCpm == null ? 0 : (int) Math.round(avgCpm));
        stats.put("avgCpm7d", avgCpm7d == null ? 0 : (int) Math.round(avgCpm7d));
        stats.put("totalElapsedMs", totalElapsedMs == null ? 0L : totalElapsedMs);

        // 今日汇总（服务端本地日期，与 MySQL CURRENT_DATE 一致）
        Map<String, Object> today = new HashMap<>();
        try {
            Map<String, Object> row = jdbc.queryForMap("""
                SELECT
                  COUNT(*) AS sessionCount,
                  COALESCE(SUM(CASE WHEN mode = 'ranked' THEN 1 ELSE 0 END), 0) AS rankedCount,
                  COALESCE(SUM(CASE WHEN mode <> 'ranked' THEN 1 ELSE 0 END), 0) AS practiceCount,
                  COALESCE(SUM(elapsed_ms), 0) AS totalElapsedMs,
                  COALESCE(SUM(correct_chars), 0) AS totalCorrectChars,
                  COALESCE(MAX(cpm), 0) AS bestCpm,
                  COALESCE(MAX(CASE WHEN mode = 'ranked' THEN cpm ELSE 0 END), 0) AS bestRankedCpm,
                  COALESCE(AVG(cpm), 0) AS avgCpm,
                  COALESCE(AVG(accuracy), 0) AS avgAccuracy
                FROM typing_session
                WHERE tenant_id = ? AND user_id = ?
                  AND created_at >= CURDATE()
                  AND created_at < CURDATE() + INTERVAL 1 DAY
                """, tenantId, userId);
            int count = intVal(row.get("sessionCount"), 0);
            today.put("count", count);
            today.put("practiceCount", intVal(row.get("practiceCount"), 0));
            today.put("rankedCount", intVal(row.get("rankedCount"), 0));
            today.put("totalElapsedMs", longVal(row.get("totalElapsedMs"), 0L));
            today.put("totalCorrectChars", intVal(row.get("totalCorrectChars"), 0));
            today.put("bestCpm", intVal(row.get("bestCpm"), 0));
            today.put("bestRankedCpm", intVal(row.get("bestRankedCpm"), 0));
            today.put("avgCpm", (int) Math.round(doubleVal(row.get("avgCpm"), 0)));
            today.put("avgAccuracy", Math.round(doubleVal(row.get("avgAccuracy"), 0) * 10.0) / 10.0);
        } catch (Exception e) {
            today.put("count", 0);
            today.put("practiceCount", 0);
            today.put("rankedCount", 0);
            today.put("totalElapsedMs", 0L);
            today.put("totalCorrectChars", 0);
            today.put("bestCpm", 0);
            today.put("bestRankedCpm", 0);
            today.put("avgCpm", 0);
            today.put("avgAccuracy", 0);
        }
        stats.put("today", today);

        // 近 14 天每日趋势（含无练习日）
        stats.put("dailyTrend", buildDailyTrend(tenantId, userId, 14));
        // 最近练习记录
        stats.put("recentSessions", listRecentSessions(tenantId, userId, 12));

        String version = latestRankedVersion(tenantId);
        stats.put("textVersion", version);
        if (version != null) {
            stats.put("myRank", resolveUserRank(tenantId, userId, version));
        }
        return stats;
    }

    /** 近 N 天每日：场次 / 均速 / 最高 / 正确率 / 时长 */
    private List<Map<String, Object>> buildDailyTrend(Long tenantId, Long userId, int days) {
        int n = Math.max(7, Math.min(30, days));
        Map<String, Map<String, Object>> byDate = new HashMap<>();
        try {
            List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT
                  DATE(created_at) AS dayKey,
                  COUNT(*) AS sessionCount,
                  COALESCE(AVG(cpm), 0) AS avgCpm,
                  COALESCE(MAX(cpm), 0) AS bestCpm,
                  COALESCE(AVG(accuracy), 0) AS avgAccuracy,
                  COALESCE(SUM(elapsed_ms), 0) AS totalElapsedMs,
                  COALESCE(SUM(correct_chars), 0) AS totalCorrectChars
                FROM typing_session
                WHERE tenant_id = ? AND user_id = ?
                  AND created_at >= CURDATE() - INTERVAL ? DAY
                GROUP BY DATE(created_at)
                ORDER BY dayKey ASC
                """, tenantId, userId, n - 1);
            for (Map<String, Object> row : rows) {
                String key = String.valueOf(row.get("dayKey"));
                if (key.length() > 10) key = key.substring(0, 10);
                Map<String, Object> item = new HashMap<>();
                item.put("date", key);
                item.put("sessionCount", intVal(row.get("sessionCount"), 0));
                item.put("avgCpm", (int) Math.round(doubleVal(row.get("avgCpm"), 0)));
                item.put("bestCpm", intVal(row.get("bestCpm"), 0));
                item.put("avgAccuracy", Math.round(doubleVal(row.get("avgAccuracy"), 0) * 10.0) / 10.0);
                item.put("totalElapsedMs", longVal(row.get("totalElapsedMs"), 0L));
                item.put("totalCorrectChars", intVal(row.get("totalCorrectChars"), 0));
                byDate.put(key, item);
            }
        } catch (Exception ignored) {
            // 空趋势
        }

        List<Map<String, Object>> trend = new ArrayList<>();
        java.time.LocalDate end = java.time.LocalDate.now(java.time.ZoneId.of("Asia/Shanghai"));
        java.time.LocalDate start = end.minusDays(n - 1L);
        for (java.time.LocalDate d = start; !d.isAfter(end); d = d.plusDays(1)) {
            String key = d.toString();
            if (byDate.containsKey(key)) {
                trend.add(byDate.get(key));
            } else {
                Map<String, Object> empty = new HashMap<>();
                empty.put("date", key);
                empty.put("sessionCount", 0);
                empty.put("avgCpm", 0);
                empty.put("bestCpm", 0);
                empty.put("avgAccuracy", 0);
                empty.put("totalElapsedMs", 0L);
                empty.put("totalCorrectChars", 0);
                trend.add(empty);
            }
        }
        return trend;
    }

    private List<Map<String, Object>> listRecentSessions(Long tenantId, Long userId, int limit) {
        int lim = Math.max(1, Math.min(30, limit));
        try {
            List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT
                  id,
                  mode,
                  cpm,
                  accuracy,
                  correct_chars AS correctChars,
                  total_keystrokes AS totalKeystrokes,
                  elapsed_ms AS elapsedMs,
                  lang,
                  difficulty,
                  source_type AS sourceType,
                  created_at AS createdAt
                FROM typing_session
                WHERE tenant_id = ? AND user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """, tenantId, userId, lim);
            List<Map<String, Object>> list = new ArrayList<>();
            for (Map<String, Object> row : rows) {
                Map<String, Object> item = new HashMap<>();
                item.put("id", row.get("id"));
                item.put("mode", row.get("mode"));
                item.put("cpm", intVal(row.get("cpm"), 0));
                item.put("accuracy", Math.round(doubleVal(row.get("accuracy"), 0) * 10.0) / 10.0);
                item.put("correctChars", intVal(row.get("correctChars"), 0));
                item.put("totalKeystrokes", intVal(row.get("totalKeystrokes"), 0));
                item.put("elapsedMs", longVal(row.get("elapsedMs"), 0L));
                item.put("lang", row.get("lang"));
                item.put("difficulty", intVal(row.get("difficulty"), 0));
                item.put("sourceType", row.get("sourceType"));
                Object created = row.get("createdAt");
                if (created instanceof Timestamp ts) {
                    item.put("createdAt", ts.toInstant().toString());
                } else {
                    item.put("createdAt", created == null ? null : String.valueOf(created));
                }
                list.add(item);
            }
            return list;
        } catch (Exception e) {
            return List.of();
        }
    }

    private Integer resolveUserRank(Long tenantId, Long userId, String textVersion) {
        Integer best = jdbc.queryForObject("""
            SELECT MAX(cpm) FROM typing_session
            WHERE tenant_id = ? AND user_id = ? AND mode = ? AND text_version = ?
            """, Integer.class, tenantId, userId, RANKED_MODE, textVersion);
        if (best == null || best <= 0) return null;
        Integer better = jdbc.queryForObject("""
            SELECT COUNT(*) FROM (
              SELECT user_id, MAX(cpm) AS max_cpm
              FROM typing_session
              WHERE tenant_id = ? AND mode = ? AND text_version = ?
              GROUP BY user_id
              HAVING max_cpm > ?
            ) t
            """, Integer.class, tenantId, RANKED_MODE, textVersion, best);
        return (better == null ? 0 : better) + 1;
    }

    private Map<String, Object> myBest(Long tenantId, Long userId, String textVersion) {
        List<Map<String, Object>> rows = jdbc.queryForList("""
            SELECT cpm, accuracy, correct_chars AS correctChars, elapsed_ms AS elapsedMs, created_at AS createdAt
            FROM typing_session
            WHERE tenant_id = ? AND user_id = ? AND mode = ? AND text_version = ?
            ORDER BY cpm DESC, accuracy DESC, created_at ASC
            LIMIT 1
            """, tenantId, userId, RANKED_MODE, textVersion);
        if (rows.isEmpty()) return null;
        Map<String, Object> row = new HashMap<>(rows.get(0));
        row.put("userId", userId);
        return row;
    }

    private String latestRankedVersion(Long tenantId) {
        List<String> versions = jdbc.query("""
            SELECT text_version FROM typing_session
            WHERE tenant_id = ? AND mode = ? AND text_version IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
            """, (rs, i) -> rs.getString(1), tenantId, RANKED_MODE);
        return versions.isEmpty() ? null : versions.get(0);
    }

    // --- 自定义文案（账户级） ---

    private static final int CUSTOM_TEXT_MAX = 30;
    private static final int CUSTOM_CONTENT_MAX = 20000;
    private static final int CUSTOM_TITLE_MAX = 120;

    public List<Map<String, Object>> listCustomTexts(Long userId) {
        ensureSchema();
        if (userId == null) throw new RuntimeException("未登录");
        return jdbc.query("""
            SELECT id, title, content, created_at AS createdAt, updated_at AS updatedAt,
                   CHAR_LENGTH(content) AS charCount
            FROM typing_custom_text
            WHERE user_id = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """, (rs, i) -> {
            Map<String, Object> m = new HashMap<>();
            m.put("id", rs.getLong("id"));
            m.put("title", rs.getString("title"));
            m.put("content", rs.getString("content"));
            m.put("charCount", rs.getInt("charCount"));
            Timestamp c = rs.getTimestamp("createdAt");
            Timestamp u = rs.getTimestamp("updatedAt");
            m.put("createdAt", c != null ? c.toInstant().toString() : null);
            m.put("updatedAt", u != null ? u.toInstant().toString() : null);
            return m;
        }, userId, CUSTOM_TEXT_MAX);
    }

    public Map<String, Object> saveCustomText(Long tenantId, Long userId, Map<String, Object> body) {
        ensureSchema();
        if (userId == null) throw new RuntimeException("未登录");
        String title = cleanTitle(body.get("title"));
        String content = cleanContent(body.get("content"));
        if (content.isBlank()) throw new RuntimeException("文案内容不能为空");

        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM typing_custom_text WHERE user_id = ?",
                Integer.class, userId
        );
        if (count != null && count >= CUSTOM_TEXT_MAX) {
            throw new RuntimeException("最多保存 " + CUSTOM_TEXT_MAX + " 条文案，请先删除旧的");
        }

        jdbc.update("""
            INSERT INTO typing_custom_text (user_id, tenant_id, title, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, userId, tenantId, title, content,
                Timestamp.from(Instant.now()), Timestamp.from(Instant.now()));
        Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        return getCustomText(userId, id);
    }

    public Map<String, Object> updateCustomText(Long userId, Long id, Map<String, Object> body) {
        ensureSchema();
        if (userId == null) throw new RuntimeException("未登录");
        if (id == null) throw new RuntimeException("缺少文案 id");
        Map<String, Object> existing = getCustomText(userId, id);
        if (existing == null) throw new RuntimeException("文案不存在");

        String title = body.containsKey("title") ? cleanTitle(body.get("title")) : String.valueOf(existing.get("title"));
        String content = body.containsKey("content") ? cleanContent(body.get("content")) : String.valueOf(existing.get("content"));
        if (content.isBlank()) throw new RuntimeException("文案内容不能为空");

        int n = jdbc.update("""
            UPDATE typing_custom_text
            SET title = ?, content = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """, title, content, Timestamp.from(Instant.now()), id, userId);
        if (n == 0) throw new RuntimeException("文案不存在");
        return getCustomText(userId, id);
    }

    public void deleteCustomText(Long userId, Long id) {
        ensureSchema();
        if (userId == null) throw new RuntimeException("未登录");
        int n = jdbc.update("DELETE FROM typing_custom_text WHERE id = ? AND user_id = ?", id, userId);
        if (n == 0) throw new RuntimeException("文案不存在");
    }

    private Map<String, Object> getCustomText(Long userId, Long id) {
        List<Map<String, Object>> rows = jdbc.query("""
            SELECT id, title, content, created_at AS createdAt, updated_at AS updatedAt,
                   CHAR_LENGTH(content) AS charCount
            FROM typing_custom_text
            WHERE id = ? AND user_id = ?
            """, (rs, i) -> {
            Map<String, Object> m = new HashMap<>();
            m.put("id", rs.getLong("id"));
            m.put("title", rs.getString("title"));
            m.put("content", rs.getString("content"));
            m.put("charCount", rs.getInt("charCount"));
            Timestamp c = rs.getTimestamp("createdAt");
            Timestamp u = rs.getTimestamp("updatedAt");
            m.put("createdAt", c != null ? c.toInstant().toString() : null);
            m.put("updatedAt", u != null ? u.toInstant().toString() : null);
            return m;
        }, id, userId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static String cleanTitle(Object v) {
        String t = text(v, "我的文案").trim();
        if (t.isEmpty()) t = "我的文案";
        if (t.length() > CUSTOM_TITLE_MAX) t = t.substring(0, CUSTOM_TITLE_MAX);
        return t;
    }

    private static String cleanContent(Object v) {
        String c = v == null ? "" : String.valueOf(v);
        // 统一换行，去掉首尾空白但保留正文换行
        c = c.replace("\r\n", "\n").replace('\r', '\n').trim();
        if (c.length() > CUSTOM_CONTENT_MAX) c = c.substring(0, CUSTOM_CONTENT_MAX);
        return c;
    }

    private void ensureSchema() {
        if (schemaReady) return;
        synchronized (this) {
            if (schemaReady) return;
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS typing_session (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  tenant_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  client_session_id VARCHAR(64) DEFAULT NULL,
                  mode VARCHAR(32) NOT NULL DEFAULT 'practice',
                  duration_sec INT NOT NULL DEFAULT 0,
                  target_count INT NOT NULL DEFAULT 0,
                  cpm INT NOT NULL DEFAULT 0,
                  accuracy DECIMAL(6,2) NOT NULL DEFAULT 0,
                  correct_chars INT NOT NULL DEFAULT 0,
                  total_keystrokes INT NOT NULL DEFAULT 0,
                  elapsed_ms BIGINT NOT NULL DEFAULT 0,
                  lang VARCHAR(16) DEFAULT 'zh',
                  difficulty INT DEFAULT 2,
                  text_version VARCHAR(64) DEFAULT NULL,
                  source_type VARCHAR(32) DEFAULT 'catalog',
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_typing_tenant_mode_ver (tenant_id, mode, text_version),
                  INDEX idx_typing_user (tenant_id, user_id, created_at),
                  INDEX idx_typing_rank (tenant_id, mode, text_version, cpm),
                  UNIQUE KEY uk_typing_client_session (tenant_id, user_id, client_session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """);
            ensureColumn("typing_session", "client_session_id", "VARCHAR(64) DEFAULT NULL");
            ensureUniqueIndex(
                    "typing_session",
                    "uk_typing_client_session",
                    "UNIQUE KEY uk_typing_client_session (tenant_id, user_id, client_session_id)");
            jdbc.execute("""
                CREATE TABLE IF NOT EXISTS typing_custom_text (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  user_id BIGINT NOT NULL,
                  tenant_id BIGINT DEFAULT NULL,
                  title VARCHAR(120) NOT NULL DEFAULT '我的文案',
                  content MEDIUMTEXT NOT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  INDEX idx_typing_custom_user (user_id, updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """);
            schemaReady = true;
        }
    }

    private void ensureColumn(String table, String column, String definition) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema=DATABASE() AND table_name=? AND column_name=?
            """, Integer.class, table, column);
        if (count != null && count == 0) {
            jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition);
        }
    }

    private void ensureUniqueIndex(String table, String indexName, String definition) {
        Integer count = jdbc.queryForObject("""
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema=DATABASE() AND table_name=? AND index_name=?
            """, Integer.class, table, indexName);
        if (count != null && count == 0) {
            jdbc.execute("ALTER TABLE " + table + " ADD " + definition);
        }
    }

    private static String maskName(String name) {
        if (name == null || name.isBlank()) return "用户";
        String n = name.trim();
        if (n.length() <= 1) return n + "*";
        if (n.length() == 2) return n.charAt(0) + "*";
        return n.charAt(0) + "*".repeat(Math.min(3, n.length() - 2)) + n.charAt(n.length() - 1);
    }

    private static String text(Object v, String def) {
        if (v == null) return def;
        String s = String.valueOf(v).trim();
        return s.isEmpty() ? def : s;
    }

    private static int intVal(Object v, int def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.intValue();
        try {
            return (int) Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static long longVal(Object v, long def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.longValue();
        try {
            return (long) Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static Long longVal(Object v, Long def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.longValue();
        try {
            return (long) Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static double doubleVal(Object v, double def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }
}
