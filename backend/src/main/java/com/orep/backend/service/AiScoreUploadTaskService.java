package com.orep.backend.service;

import com.orep.backend.dto.AiScoreUploadTaskResponse;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.regex.Pattern;

@Service
public class AiScoreUploadTaskService {
    private static final int DEFAULT_COMPLETED_LIMIT = 10;
    private static final String SAFE_FAILURE_MESSAGE = "评分处理失败，请稍后重试；如仍失败，请重新上传视频。";
    private static final List<Pattern> INTERNAL_ERROR_PATTERNS = List.of(
            Pattern.compile("(?i)(?:\\b(?:https?|ftp)://|\\b(?:localhost|(?:\\d{1,3}\\.){3}\\d{1,3}|[a-z][a-z0-9_-]{1,62}(?:\\.[a-z0-9_-]+)*):\\d{2,5}\\b|\\b(?:host|hostname|port|endpoint|base[_-]?url)\\s*[:=])"),
            Pattern.compile("(?i)(?:\\b[A-Z]:\\\\|\\\\\\\\|(?:^|[\\s='\"(])/(?:[^\\s/]+/)+[^\\s]*)"),
            Pattern.compile("(?i)(?:\\b(?:caused\\s+by|exception|traceback|stack\\s*trace)\\b|(?:^|\\R)\\s*at\\s+(?:[\\w$]+\\.){2,}|\\.java:\\d+|\\b(?:[a-z_$][\\w$]*\\.){2,}[A-Z][\\w$]*(?:\\.|\\b))"),
            Pattern.compile("(?i)\\b(?:rubric|prompt|system[_ -]?(?:message|instruction)|pipeline|internal[_ -]?(?:service|config|version|path|rule)?|api[_-]?key|secret|password|token|jdbc|redis|minio|mysql|postgresql|s3|bucket|model[_-]?(?:name|id)|scoring[_-]?(?:engine|service|rule|config))\\b"),
            Pattern.compile("(?:提示词|系统指令|评分量表|评分规则|内部规则|内部服务|服务地址|密钥|令牌|堆栈|类名)")
    );
    private final JdbcTemplate jdbc;

    public AiScoreUploadTaskService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<AiScoreUploadTaskResponse> listForUser(Long userId, Integer completedLimit) {
        if (userId == null) {
            throw new IllegalArgumentException("用户身份不能为空");
        }
        int terminalLimit = completedLimit == null
                ? DEFAULT_COMPLETED_LIMIT
                : Math.max(0, Math.min(DEFAULT_COMPLETED_LIMIT, completedLimit));
        return jdbc.query(query(), (rs, rowNum) -> new AiScoreUploadTaskResponse(
                rs.getLong("sessionId"),
                rs.getString("sessionNo"),
                rs.getString("fileName"),
                rs.getLong("fileSize"),
                nullableLong(rs, "projectId"),
                nullableLong(rs, "teamId"),
                rs.getString("teamName"),
                rs.getString("trackName"),
                rs.getString("status"),
                rs.getString("currentStage"),
                rs.getInt("progressPercent"),
                rs.getObject("useHistoryMemory", Boolean.class),
                rs.getObject("juryEnabled", Boolean.class),
                nullableLong(rs, "reportId"),
                sanitizePublicErrorMessage(rs.getString("errorMessage")),
                rs.getObject("createdAt", LocalDateTime.class),
                rs.getObject("updatedAt", LocalDateTime.class)
        ), userId, userId, terminalLimit);
    }

    private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
        long value = rs.getLong(column);
        return rs.wasNull() ? null : value;
    }

    private String sanitizePublicErrorMessage(String value) {
        if (value == null) {
            return null;
        }
        String normalized = value.strip();
        if (normalized.isEmpty()) {
            return null;
        }
        for (Pattern pattern : INTERNAL_ERROR_PATTERNS) {
            if (pattern.matcher(normalized).find()) {
                return SAFE_FAILURE_MESSAGE;
            }
        }
        return truncate(normalized.replaceAll("\\s+", " "));
    }

    private String truncate(String value) {
        int codePointCount = value.codePointCount(0, value.length());
        return codePointCount <= 160 ? value : value.substring(0, value.offsetByCodePoints(0, 160));
    }

    private String query() {
        return """
                SELECT sessionId, sessionNo, fileName, fileSize, projectId, teamId, teamName, trackName,
                       status, currentStage, progressPercent, useHistoryMemory, juryEnabled, reportId,
                       errorMessage, createdAt, updatedAt
                FROM (
                    SELECT s.id sessionId, s.session_no sessionNo,
                           COALESCE(NULLIF(a.original_name, ''), s.session_no) fileName,
                           COALESCE(a.size_bytes, 0) fileSize,
                           s.project_id projectId, s.team_id teamId,
                           COALESCE(NULLIF(pt.name, ''), '未命名团队') teamName,
                           s.track_name trackName, COALESCE(s.status, 'created') status, s.current_stage currentStage,
                           CASE WHEN s.progress_percent < 0 THEN 0
                                WHEN s.progress_percent > 100 THEN 100
                                ELSE COALESCE(s.progress_percent, 0) END progressPercent,
                           s.use_history_memory useHistoryMemory, s.jury_enabled juryEnabled,
                           s.report_id reportId, s.error_message errorMessage,
                           s.created_at createdAt, s.updated_at updatedAt,
                           0 sortGroup, s.created_at sortCreatedAt, s.id sortId
                    FROM ai_scoring_session s
                    LEFT JOIN ai_score_media_asset a ON a.id = (
                        SELECT MIN(a2.id) FROM ai_score_media_asset a2
                        WHERE a2.session_id = s.id AND a2.asset_type = 'video'
                    )
                    LEFT JOIN project_team pt ON pt.id = s.team_id
                    WHERE s.created_by = ? AND s.source_type = 'uploaded_video'
                      AND LOWER(COALESCE(s.status, 'created')) NOT IN ('completed', 'failed', 'cancelled')
                    UNION ALL
                    SELECT terminal.sessionId, terminal.sessionNo, terminal.fileName, terminal.fileSize,
                           terminal.projectId, terminal.teamId, terminal.teamName, terminal.trackName,
                           terminal.status, terminal.currentStage, terminal.progressPercent,
                           terminal.useHistoryMemory, terminal.juryEnabled, terminal.reportId,
                           terminal.errorMessage, terminal.createdAt, terminal.updatedAt,
                           terminal.sortGroup, terminal.sortCreatedAt, terminal.sortId
                    FROM (
                        SELECT s.id sessionId, s.session_no sessionNo,
                               COALESCE(NULLIF(a.original_name, ''), s.session_no) fileName,
                               COALESCE(a.size_bytes, 0) fileSize,
                               s.project_id projectId, s.team_id teamId,
                               COALESCE(NULLIF(pt.name, ''), '未命名团队') teamName,
                               s.track_name trackName, COALESCE(s.status, 'created') status, s.current_stage currentStage,
                               CASE WHEN s.progress_percent < 0 THEN 0
                                    WHEN s.progress_percent > 100 THEN 100
                                    ELSE COALESCE(s.progress_percent, 0) END progressPercent,
                               s.use_history_memory useHistoryMemory, s.jury_enabled juryEnabled,
                               s.report_id reportId, s.error_message errorMessage,
                               s.created_at createdAt, s.updated_at updatedAt,
                               1 sortGroup, s.created_at sortCreatedAt, s.id sortId
                        FROM ai_scoring_session s
                        LEFT JOIN ai_score_media_asset a ON a.id = (
                            SELECT MIN(a2.id) FROM ai_score_media_asset a2
                            WHERE a2.session_id = s.id AND a2.asset_type = 'video'
                        )
                        LEFT JOIN project_team pt ON pt.id = s.team_id
                        WHERE s.created_by = ? AND s.source_type = 'uploaded_video'
                          AND LOWER(COALESCE(s.status, 'created')) IN ('completed', 'failed', 'cancelled')
                        ORDER BY s.created_at DESC, s.id DESC
                        LIMIT ?
                    ) terminal
                ) queue
                ORDER BY sortGroup ASC, sortCreatedAt DESC, sortId DESC
                """;
    }
}
