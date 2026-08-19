package com.orep.backend.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class StudentLearningAnalyticsService {
    private static final ZoneId CHINA_ZONE = ZoneId.of("Asia/Shanghai");

    private final JdbcTemplate jdbc;

    public StudentLearningAnalyticsService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Map<String, Object>> learningSessions(Long userId) {
        return jdbc.queryForList("""
            SELECT activityType, startedAt, durationSeconds
            FROM (
                SELECT 'COURSE' activityType,
                       COALESCE(last_learned_at, updated_at, created_at) startedAt,
                       GREATEST(COALESCE(learned_seconds, 0), 0) durationSeconds
                FROM course_learning_progress
                WHERE user_id = ? AND COALESCE(learned_seconds, 0) > 0

                UNION ALL

                -- 训练营「今日学习」：站内视频 / 站外嵌入视频 / 文档课件
                SELECT 'TRAINING' activityType,
                       COALESCE(last_learned_at, heartbeat_at, updated_at, created_at) startedAt,
                       GREATEST(
                         COALESCE(actual_learning_seconds, 0),
                         COALESCE(learned_seconds, 0),
                         0
                       ) durationSeconds
                FROM training_learning_progress
                WHERE user_id = ?
                  AND GREATEST(COALESCE(actual_learning_seconds, 0), COALESCE(learned_seconds, 0)) > 0

                UNION ALL

                SELECT 'EXAM' activityType,
                       started_at startedAt,
                       GREATEST(TIMESTAMPDIFF(SECOND, started_at, submitted_at), 0) durationSeconds
                FROM exam_attempt
                WHERE user_id = ? AND started_at IS NOT NULL AND submitted_at IS NOT NULL

                UNION ALL

                SELECT 'ROADSHOW' activityType,
                       joined_at startedAt,
                       GREATEST(COALESCE(duration_seconds, TIMESTAMPDIFF(SECOND, joined_at, left_at), 0), 0) durationSeconds
                FROM meeting_participant
                WHERE user_id = ? AND joined_at IS NOT NULL

                UNION ALL

                -- 打字练习（自主 / 代码 / 排位）
                SELECT 'TYPING' activityType,
                       created_at startedAt,
                       GREATEST(FLOOR(COALESCE(elapsed_ms, 0) / 1000), 0) durationSeconds
                FROM typing_session
                WHERE user_id = ?
                  AND COALESCE(elapsed_ms, 0) > 0

                UNION ALL

                SELECT activity_type activityType,
                       started_at startedAt,
                       GREATEST(COALESCE(duration_seconds, 0), 0) durationSeconds
                FROM student_learning_session
                WHERE user_id = ?
                  AND activity_type IN (
                    'COLLABORATION', 'TRAINING', 'COURSE', 'EXAM', 'ROADSHOW',
                    'TASK_BOOK', 'INSPIRE_OFFICE', 'TYPING'
                  )
            ) activity
            WHERE startedAt IS NOT NULL AND durationSeconds > 0
            ORDER BY startedAt
            """, userId, userId, userId, userId, userId, userId);
    }

    public Map<String, Object> summary(List<Map<String, Object>> sessions) {
        LocalDate today = LocalDate.now(CHINA_ZONE);
        // 近一周：含今天共 7 天，避免「自然周」周一后半周全空
        LocalDate weekStart = today.minusDays(6);
        long totalSeconds = 0;
        long weekSeconds = 0;
        long longestSeconds = 0;
        Map<LocalDate, Long> daily = new LinkedHashMap<>();

        for (Map<String, Object> session : sessions) {
            long seconds = Math.max(0L, longValue(session.get("durationSeconds")));
            LocalDate date = dateValue(session.get("startedAt"));
            totalSeconds += seconds;
            longestSeconds = Math.max(longestSeconds, seconds);
            if (date != null && seconds > 0) {
                daily.merge(date, seconds, Long::sum);
                if (!date.isBefore(weekStart) && !date.isAfter(today)) weekSeconds += seconds;
            }
        }

        List<LocalDate> activeDates = daily.keySet().stream().sorted().toList();
        int longestStreak = 0;
        int runningStreak = 0;
        LocalDate previous = null;
        for (LocalDate date : activeDates) {
            runningStreak = previous != null && ChronoUnit.DAYS.between(previous, date) == 1 ? runningStreak + 1 : 1;
            longestStreak = Math.max(longestStreak, runningStreak);
            previous = date;
        }

        int currentStreak = 0;
        LocalDate cursor = today;
        if (!daily.containsKey(cursor)) cursor = cursor.minusDays(1);
        while (daily.containsKey(cursor)) {
            currentStreak++;
            cursor = cursor.minusDays(1);
        }

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("totalSeconds", totalSeconds);
        summary.put("weekSeconds", weekSeconds);
        summary.put("longestSessionSeconds", longestSeconds);
        summary.put("currentStreakDays", currentStreak);
        summary.put("longestStreakDays", longestStreak);
        summary.put("todaySeconds", daily.getOrDefault(today, 0L));
        return summary;
    }

    public List<Map<String, Object>> heatmap(List<Map<String, Object>> sessions) {
        LocalDate from = LocalDate.now(CHINA_ZONE).minusDays(364);
        Map<LocalDate, Long> daily = new LinkedHashMap<>();
        for (Map<String, Object> session : sessions) {
            LocalDate date = dateValue(session.get("startedAt"));
            long seconds = Math.max(0L, longValue(session.get("durationSeconds")));
            if (date == null || date.isBefore(from) || seconds == 0) continue;
            daily.merge(date, seconds, Long::sum);
        }
        return daily.entrySet().stream().map(entry -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("date", entry.getKey().toString());
            row.put("durationSeconds", entry.getValue());
            return row;
        }).toList();
    }

    /**
     * 学生端完整分布：每类单独展示，避免打字/训练营/任务书被吞掉导致「时间没算」。
     */
    public List<Map<String, Object>> distribution(List<Map<String, Object>> sessions) {
        Map<String, Long> seconds = new LinkedHashMap<>();
        seconds.put("COURSE", 0L);
        seconds.put("TRAINING", 0L);
        seconds.put("TYPING", 0L);
        seconds.put("EXAM", 0L);
        seconds.put("ROADSHOW", 0L);
        seconds.put("TASK_BOOK", 0L);
        seconds.put("INSPIRE_OFFICE", 0L);
        seconds.put("COLLABORATION", 0L);
        for (Map<String, Object> session : sessions) {
            String type = String.valueOf(session.get("activityType"));
            if (!seconds.containsKey(type)) {
                // 未知类型并入协作，避免丢秒数
                type = "COLLABORATION";
            }
            final String key = type;
            seconds.computeIfPresent(key, (k, value) -> value + Math.max(0L, longValue(session.get("durationSeconds"))));
        }
        long total = seconds.values().stream().mapToLong(Long::longValue).sum();
        return seconds.entrySet().stream().map(entry -> {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("activityType", entry.getKey());
            row.put("durationSeconds", entry.getValue());
            row.put("percent", total == 0 ? 0 : Math.round(entry.getValue() * 1000.0 / total) / 10.0);
            return row;
        }).toList();
    }

    public Map<String, Object> weekly(Long userId) {
        return weeklyFromSessions(learningSessions(userId), LocalDate.now(CHINA_ZONE));
    }

    /**
     * 教师档案用：平台内视频 / 站外视频 / 任务书驻留 / 打字 / 启发 Office 精准累计秒数 + 明细。
     */
    public Map<String, Object> preciseDurations(Long tenantId, Long userId) {
        List<Map<String, Object>> platformVideos = listVideoDetails(userId, "VIDEO");
        List<Map<String, Object>> embedVideos = listVideoDetails(userId, "EMBED_VIDEO");
        List<Map<String, Object>> taskBookDays = listTaskBookDetails(userId);
        List<Map<String, Object>> typingSessions = listTypingDetails(tenantId, userId);
        List<Map<String, Object>> inspireDocuments = listInspireOfficeDetails(userId);

        long platformVideoSeconds = sumField(platformVideos, "seconds");
        long embedVideoSeconds = sumField(embedVideos, "seconds");
        long taskBookDwellSeconds = sumField(taskBookDays, "seconds");
        long typingSeconds = sumField(typingSessions, "seconds");
        long inspireOfficeSeconds = sumField(inspireDocuments, "onlineSeconds");
        long inspireOfficeEditSeconds = sumField(inspireDocuments, "editSeconds");

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("platformVideoSeconds", platformVideoSeconds);
        out.put("embedVideoSeconds", embedVideoSeconds);
        out.put("taskBookDwellSeconds", taskBookDwellSeconds);
        out.put("typingSeconds", typingSeconds);
        out.put("inspireOfficeSeconds", inspireOfficeSeconds);
        out.put("inspireOfficeEditSeconds", inspireOfficeEditSeconds);
        out.put("totalPreciseSeconds",
                platformVideoSeconds + embedVideoSeconds + taskBookDwellSeconds
                        + typingSeconds + inspireOfficeSeconds);

        Map<String, Object> details = new LinkedHashMap<>();
        details.put("platformVideos", platformVideos);
        details.put("embedVideos", embedVideos);
        details.put("taskBookDays", taskBookDays);
        details.put("typingSessions", typingSessions);
        details.put("inspireDocuments", inspireDocuments);
        out.put("details", details);
        return out;
    }

    private List<Map<String, Object>> listVideoDetails(Long userId, String resourceType) {
        try {
            return jdbc.queryForList("""
                SELECT r.id resourceId, r.title title, r.resource_type resourceType,
                       d.day_no dayNo, d.title dayTitle, d.training_date trainingDate,
                       GREATEST(COALESCE(p.actual_learning_seconds, 0), COALESCE(p.learned_seconds, 0)) seconds,
                       COALESCE(p.progress_percent, 0) progressPercent,
                       COALESCE(p.status, 'NOT_STARTED') status,
                       p.last_learned_at lastLearnedAt
                FROM training_learning_progress p
                JOIN training_day_learning_resource r ON r.id = p.learning_resource_id
                LEFT JOIN training_day d ON d.id = r.training_day_id
                WHERE p.user_id = ?
                  AND UPPER(r.resource_type) = ?
                  AND GREATEST(COALESCE(p.actual_learning_seconds, 0), COALESCE(p.learned_seconds, 0)) > 0
                ORDER BY COALESCE(p.last_learned_at, p.updated_at) DESC, p.id DESC
                LIMIT 50
                """, userId, resourceType.toUpperCase());
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> listTaskBookDetails(Long userId) {
        try {
            return jdbc.queryForList("""
                SELECT s.source_id dayId, d.day_no dayNo, d.title dayTitle, d.training_date trainingDate,
                       GREATEST(COALESCE(s.duration_seconds, 0), 0) seconds,
                       s.started_at startedAt, s.ended_at endedAt
                FROM student_learning_session s
                LEFT JOIN training_day d ON d.id = s.source_id
                WHERE s.user_id = ?
                  AND UPPER(s.activity_type) = 'TASK_BOOK'
                  AND GREATEST(COALESCE(s.duration_seconds, 0), 0) > 0
                ORDER BY COALESCE(s.ended_at, s.started_at) DESC, s.id DESC
                LIMIT 50
                """, userId);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Map<String, Object>> listInspireOfficeDetails(Long userId) {
        try {
            List<Map<String, Object>> rows = jdbc.queryForList("""
                SELECT s.source_id documentId,
                       GREATEST(COALESCE(s.duration_seconds, 0), 0) onlineSeconds,
                       s.started_at startedAt,
                       s.ended_at endedAt,
                       s.metadata_json metadataJson,
                       d.title documentTitle,
                       d.ext documentExt,
                       d.scope documentScope,
                       d.team_id teamId
                FROM student_learning_session s
                LEFT JOIN inspire_office_document d ON d.id = s.source_id
                WHERE s.user_id = ?
                  AND UPPER(s.activity_type) = 'INSPIRE_OFFICE'
                  AND GREATEST(COALESCE(s.duration_seconds, 0), 0) > 0
                ORDER BY COALESCE(s.ended_at, s.started_at) DESC, s.id DESC
                LIMIT 50
                """, userId);
            for (Map<String, Object> row : rows) {
                String meta = String.valueOf(row.getOrDefault("metadataJson", "{}"));
                int editSeconds = extractMetaInt(meta, "editSeconds");
                String titleFromMeta = extractMetaString(meta, "title");
                String kindFromMeta = extractMetaString(meta, "documentKind");
                String title = firstNonBlank(
                        row.get("documentTitle"),
                        titleFromMeta,
                        "文档 #" + row.get("documentId")
                );
                long online = longValue(row.get("onlineSeconds"));
                row.put("title", title);
                row.put("onlineSeconds", online);
                row.put("seconds", online);
                row.put("editSeconds", Math.min(Math.max(0, editSeconds), online));
                row.put("documentKind", firstNonBlank(kindFromMeta, kindFromExt(row.get("documentExt")), "word"));
                row.remove("metadataJson");
            }
            return rows;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private static int extractMetaInt(String json, String key) {
        if (json == null || key == null) return 0;
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
                "\"" + key + "\"\\s*:\\s*(-?\\d+)"
        ).matcher(json);
        if (!m.find()) return 0;
        try {
            return Integer.parseInt(m.group(1));
        } catch (NumberFormatException ignored) {
            return 0;
        }
    }

    private static String extractMetaString(String json, String key) {
        if (json == null || key == null) return null;
        java.util.regex.Matcher m = java.util.regex.Pattern.compile(
                "\"" + key + "\"\\s*:\\s*\"([^\"]*)\""
        ).matcher(json);
        return m.find() ? m.group(1) : null;
    }

    private static String firstNonBlank(Object... values) {
        if (values == null) return null;
        for (Object v : values) {
            if (v == null) continue;
            String s = String.valueOf(v).trim();
            if (!s.isEmpty() && !"null".equalsIgnoreCase(s)) return s;
        }
        return null;
    }

    private static String kindFromExt(Object ext) {
        String e = ext == null ? "" : String.valueOf(ext).replace(".", "").toLowerCase();
        if (List.of("pptx", "ppt", "odp", "ppsx", "potx").contains(e)) return "slide";
        if (List.of("xlsx", "xls", "ods", "csv").contains(e)) return "sheet";
        return "word";
    }

    private List<Map<String, Object>> listTypingDetails(Long tenantId, Long userId) {
        try {
            if (tenantId != null) {
                return jdbc.queryForList("""
                    SELECT id sessionId, mode,
                           GREATEST(FLOOR(COALESCE(elapsed_ms, 0) / 1000), 0) seconds,
                           COALESCE(cpm, 0) cpm,
                           COALESCE(accuracy, 0) accuracy,
                           COALESCE(correct_chars, 0) correctChars,
                           created_at createdAt
                    FROM typing_session
                    WHERE tenant_id = ? AND user_id = ?
                      AND COALESCE(elapsed_ms, 0) > 0
                    ORDER BY created_at DESC, id DESC
                    LIMIT 50
                    """, tenantId, userId);
            }
            return jdbc.queryForList("""
                SELECT id sessionId, mode,
                       GREATEST(FLOOR(COALESCE(elapsed_ms, 0) / 1000), 0) seconds,
                       COALESCE(cpm, 0) cpm,
                       COALESCE(accuracy, 0) accuracy,
                       COALESCE(correct_chars, 0) correctChars,
                       created_at createdAt
                FROM typing_session
                WHERE user_id = ?
                  AND COALESCE(elapsed_ms, 0) > 0
                ORDER BY created_at DESC, id DESC
                LIMIT 50
                """, userId);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private static long sumField(List<Map<String, Object>> rows, String field) {
        long total = 0L;
        for (Map<String, Object> row : rows) {
            total += longValue(row.get(field));
        }
        return total;
    }

    /**
     * 近一周学习（滚动 7 天：today-6 … today），不是自然周（周一到周日）。
     * 避免周初后半周柱图全空；weekStart/weekEnd 字段名保留以兼容前端。
     */
    static Map<String, Object> weeklyFromSessions(List<Map<String, Object>> sessions, LocalDate today) {
        LocalDate weekStart = today.minusDays(6);
        LocalDate weekEnd = today;
        Map<LocalDate, Long> secondsByDate = new LinkedHashMap<>();
        for (int index = 0; index < 7; index++) {
            secondsByDate.put(weekStart.plusDays(index), 0L);
        }
        for (Map<String, Object> session : sessions) {
            LocalDate date = dateValue(session.get("startedAt"));
            long seconds = Math.max(0L, longValue(session.get("durationSeconds")));
            if (date == null || date.isBefore(weekStart) || date.isAfter(today) || seconds == 0) continue;
            secondsByDate.computeIfPresent(date, (key, value) -> value + seconds);
        }
        List<Map<String, Object>> daily = secondsByDate.entrySet().stream()
                .map(entry -> Map.<String, Object>of(
                        "date", entry.getKey().toString(),
                        "durationSeconds", entry.getValue()
                ))
                .toList();
        long totalSeconds = secondsByDate.values().stream().mapToLong(Long::longValue).sum();
        long activeDays = secondsByDate.entrySet().stream()
                .filter(entry -> !entry.getKey().isAfter(today) && entry.getValue() > 0)
                .count();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("weekStart", weekStart.toString());
        result.put("weekEnd", weekEnd.toString());
        result.put("serverDate", today.toString());
        result.put("totalSeconds", totalSeconds);
        result.put("activeDays", activeDays);
        result.put("daily", daily);
        return result;
    }

    private static long longValue(Object value) {
        if (value == null) return 0L;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return 0L;
        }
    }

    private static LocalDate dateValue(Object value) {
        if (value == null) return null;
        if (value instanceof java.sql.Timestamp timestamp) return timestamp.toLocalDateTime().toLocalDate();
        if (value instanceof java.time.LocalDateTime dateTime) return dateTime.toLocalDate();
        if (value instanceof java.util.Date date) return date.toInstant().atZone(CHINA_ZONE).toLocalDate();
        try {
            return java.time.LocalDateTime.parse(String.valueOf(value).replace(' ', 'T')).toLocalDate();
        } catch (Exception ignored) {
            return null;
        }
    }
}
