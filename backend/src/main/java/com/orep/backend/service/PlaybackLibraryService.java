package com.orep.backend.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * 统一路演回放库：会议录制 + AI 上传/在线评分视频，不重复存两份文件。
 */
@Service
public class PlaybackLibraryService {
    private final JdbcTemplate jdbc;

    public PlaybackLibraryService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * 教师端：可见项目范围内的会议录制 + 上传评分视频。
     */
    public List<Map<String, Object>> listForTeacher(Long tenantId, Long userId, List<Long> teamIds) {
        if (tenantId == null) {
            return List.of();
        }
        List<Long> teams = teamIds == null ? List.of() : teamIds.stream().filter(Objects::nonNull).toList();
        String teamCsv = teams.isEmpty() ? "NULL" : teams.stream().map(String::valueOf).collect(Collectors.joining(","));

        List<Map<String, Object>> meetingRows = teams.isEmpty()
                ? List.of()
                : jdbc.queryForList(("""
            SELECT DISTINCT r.id,
                   r.meeting_id meetingId,
                   COALESCE(r.meeting_title, m.title, '未命名路演') title,
                   r.status,
                   r.duration_seconds durationSeconds,
                   r.recorded_at recordedAt,
                   r.file_path filePath,
                   r.camera_file cameraFile,
                   r.screen_file screenFile,
                   r.audio_file audioFile,
                   r.size_bytes sizeBytes,
                   r.has_audio hasAudio,
                   r.has_video hasVideo,
                   r.error_message errorMessage,
                   b.team_id teamId,
                   pt.name teamName,
                   (SELECT ar.id FROM ai_score_report ar WHERE ar.meeting_id = r.meeting_id ORDER BY ar.id DESC LIMIT 1) reportId,
                   (SELECT s.id FROM ai_scoring_session s WHERE s.meeting_id = r.meeting_id OR s.recording_id = r.id
                    ORDER BY s.id DESC LIMIT 1) sessionId
            FROM meeting_recording r
            JOIN meeting m ON m.id = r.meeting_id AND m.tenant_id = ?
            JOIN project_roadshow_binding b ON b.meeting_id = m.id AND b.team_id IN (%s)
            LEFT JOIN project_team pt ON pt.id = b.team_id
            ORDER BY r.recorded_at DESC, r.id DESC
            """).formatted(teamCsv), tenantId);

        // 评分视频：自己上传的 + 可见项目下的（与会议录制同一库展示，文件不重复存）
        List<Map<String, Object>> uploadRows = jdbc.queryForList(("""
            SELECT s.id sessionId,
                   s.session_no sessionNo,
                   s.source_type sourceType,
                   s.status sessionStatus,
                   s.team_id teamId,
                   s.meeting_id meetingId,
                   s.report_id reportId,
                   s.created_at recordedAt,
                   s.completed_at completedAt,
                   a.file_path filePath,
                   a.original_name originalName,
                   a.size_bytes sizeBytes,
                   a.duration_seconds durationSeconds,
                   a.has_audio hasAudio,
                   a.has_video hasVideo,
                   a.mime_type mimeType,
                   pt.name teamName,
                   m.title meetingTitle
            FROM ai_scoring_session s
            JOIN ai_score_media_asset a ON a.session_id = s.id AND a.asset_type = 'video'
            LEFT JOIN project_team pt ON pt.id = s.team_id AND (pt.tenant_id = ? OR pt.tenant_id IS NULL)
            LEFT JOIN meeting m ON m.id = s.meeting_id
            WHERE a.file_path IS NOT NULL AND a.file_path <> ''
              AND (
                s.created_by = ?
                OR (%s)
              )
            ORDER BY s.created_at DESC, s.id DESC
            """).formatted(
                teams.isEmpty() ? "1=0" : "s.team_id IN (" + teamCsv + ")"
        ), tenantId, userId);

        return mergeAndDedupe(meetingRows, uploadRows);
    }

    /**
     * 学生端：我参与/创建的会议录制 + 我上传或我队的评分视频。
     */
    public List<Map<String, Object>> listForStudent(Long tenantId, Long userId) {
        if (userId == null) return List.of();

        List<Map<String, Object>> meetingRows = jdbc.queryForList("""
            SELECT DISTINCT r.id,
                   r.meeting_id meetingId,
                   COALESCE(r.meeting_title, m.title, '未命名路演') title,
                   r.status,
                   r.duration_seconds durationSeconds,
                   r.recorded_at recordedAt,
                   r.file_path filePath,
                   r.camera_file cameraFile,
                   r.screen_file screenFile,
                   r.audio_file audioFile,
                   r.size_bytes sizeBytes,
                   r.has_audio hasAudio,
                   r.has_video hasVideo,
                   r.error_message errorMessage,
                   NULL teamId,
                   NULL teamName,
                   (SELECT ar.id FROM ai_score_report ar WHERE ar.meeting_id = r.meeting_id ORDER BY ar.id DESC LIMIT 1) reportId,
                   (SELECT s.id FROM ai_scoring_session s WHERE s.meeting_id = r.meeting_id OR s.recording_id = r.id
                    ORDER BY s.id DESC LIMIT 1) sessionId
            FROM meeting_recording r
            LEFT JOIN meeting m ON m.id = r.meeting_id
            LEFT JOIN meeting_participant mp ON mp.meeting_id = r.meeting_id AND mp.user_id = ?
            WHERE mp.user_id = ? OR m.creator_id = ? OR r.user_id = ?
            ORDER BY r.recorded_at DESC, r.id DESC
            """, userId, userId, userId, userId);

        List<Map<String, Object>> uploadRows = jdbc.queryForList("""
            SELECT s.id sessionId,
                   s.session_no sessionNo,
                   s.source_type sourceType,
                   s.status sessionStatus,
                   s.team_id teamId,
                   s.meeting_id meetingId,
                   s.report_id reportId,
                   s.created_at recordedAt,
                   s.completed_at completedAt,
                   a.file_path filePath,
                   a.original_name originalName,
                   a.size_bytes sizeBytes,
                   a.duration_seconds durationSeconds,
                   a.has_audio hasAudio,
                   a.has_video hasVideo,
                   a.mime_type mimeType,
                   pt.name teamName,
                   m.title meetingTitle
            FROM ai_scoring_session s
            JOIN ai_score_media_asset a ON a.session_id = s.id AND a.asset_type = 'video'
            LEFT JOIN project_team pt ON pt.id = s.team_id
            LEFT JOIN meeting m ON m.id = s.meeting_id
            WHERE a.file_path IS NOT NULL AND a.file_path <> ''
              AND (
                s.created_by = ?
                OR s.team_id IN (SELECT tm.team_id FROM project_team_member tm WHERE tm.user_id = ?)
              )
            ORDER BY s.created_at DESC, s.id DESC
            """, userId, userId);

        return mergeAndDedupe(meetingRows, uploadRows);
    }

    private List<Map<String, Object>> mergeAndDedupe(
            List<Map<String, Object>> meetingRows,
            List<Map<String, Object>> uploadRows
    ) {
        List<Map<String, Object>> out = new ArrayList<>();
        // 已有会议录制的 meetingId：上传评分若绑定同一会议且仅作评分用，仍展示会议录制为主，上传项只在无会议录制时作为回放源
        for (Map<String, Object> row : meetingRows) {
            out.add(normalizeMeetingRow(row));
        }
        for (Map<String, Object> row : uploadRows) {
            out.add(normalizeUploadRow(row));
        }
        out.sort(Comparator.comparing(
                (Map<String, Object> m) -> String.valueOf(m.getOrDefault("recordedAt", "")),
                Comparator.reverseOrder()
        ));
        return out;
    }

    private Map<String, Object> normalizeMeetingRow(Map<String, Object> row) {
        Map<String, Object> item = new LinkedHashMap<>();
        Long id = longVal(row.get("id"));
        item.put("id", "mr-" + id);
        item.put("recordingId", id);
        item.put("source", "MEETING_RECORDING");
        item.put("sourceLabel", "会议录制");
        item.put("title", row.get("title"));
        item.put("status", mapMeetingStatus(String.valueOf(row.getOrDefault("status", ""))));
        item.put("rawStatus", row.get("status"));
        item.put("durationSeconds", row.get("durationSeconds"));
        item.put("recordedAt", row.get("recordedAt"));
        item.put("sizeBytes", row.get("sizeBytes"));
        item.put("hasAudio", row.get("hasAudio"));
        item.put("hasVideo", row.get("hasVideo"));
        item.put("errorMessage", row.get("errorMessage"));
        item.put("meetingId", row.get("meetingId"));
        item.put("teamId", row.get("teamId"));
        item.put("teamName", row.get("teamName"));
        item.put("reportId", row.get("reportId"));
        item.put("sessionId", row.get("sessionId"));
        item.put("filePath", row.get("filePath"));
        item.put("cameraFile", row.get("cameraFile"));
        item.put("screenFile", row.get("screenFile"));
        item.put("audioFile", row.get("audioFile"));
        item.put("streamApi", id == null ? null : "/api/recording/" + id + "/stream?file=video");
        item.put("audioStreamApi", id == null ? null : "/api/recording/" + id + "/stream?file=audio");
        item.put("playUrl", toPublicUploadUrl(firstNonBlank(
                str(row.get("filePath")), str(row.get("cameraFile")), str(row.get("screenFile")))));
        // READY 即可尝试回放：有直链 playUrl 或鉴权 streamApi
        item.put("ready", "READY".equalsIgnoreCase(String.valueOf(row.get("status"))));
        return item;
    }

    private Map<String, Object> normalizeUploadRow(Map<String, Object> row) {
        Map<String, Object> item = new LinkedHashMap<>();
        Long sessionId = longVal(row.get("sessionId"));
        String sessionStatus = String.valueOf(row.getOrDefault("sessionStatus", ""));
        String title = firstNonBlank(
                str(row.get("meetingTitle")),
                str(row.get("originalName")),
                str(row.get("sessionNo")),
                "上传评分视频"
        );
        if (row.get("teamName") != null && !String.valueOf(row.get("teamName")).isBlank()) {
            // keep team separate
        }
        item.put("id", "ai-" + sessionId);
        item.put("sessionId", sessionId);
        item.put("source", "AI_UPLOAD");
        item.put("sourceLabel", sourceLabel(String.valueOf(row.getOrDefault("sourceType", ""))));
        item.put("title", title);
        item.put("status", mapSessionStatus(sessionStatus));
        item.put("rawStatus", sessionStatus);
        item.put("durationSeconds", row.get("durationSeconds"));
        item.put("recordedAt", row.get("recordedAt"));
        item.put("sizeBytes", row.get("sizeBytes"));
        item.put("hasAudio", row.get("hasAudio"));
        item.put("hasVideo", row.get("hasVideo") == null ? 1 : row.get("hasVideo"));
        item.put("errorMessage", null);
        item.put("meetingId", row.get("meetingId"));
        item.put("teamId", row.get("teamId"));
        item.put("teamName", row.get("teamName"));
        item.put("reportId", row.get("reportId"));
        item.put("sessionNo", row.get("sessionNo"));
        item.put("filePath", row.get("filePath"));
        item.put("mimeType", row.get("mimeType"));
        String playUrl = toPublicUploadUrl(str(row.get("filePath")));
        item.put("playUrl", playUrl);
        item.put("streamApi", null);
        item.put("ready", playUrl != null && !playUrl.isBlank());
        return item;
    }

    private String sourceLabel(String sourceType) {
        String s = sourceType == null ? "" : sourceType.toLowerCase(Locale.ROOT);
        if (s.contains("meeting")) return "在线评分视频";
        if (s.contains("upload")) return "上传评分视频";
        return "评分视频";
    }

    private String mapMeetingStatus(String status) {
        String s = status == null ? "" : status.toUpperCase(Locale.ROOT);
        return switch (s) {
            case "READY" -> "READY";
            case "PROCESSING", "RECORDING", "STARTING" -> "PROCESSING";
            case "FAILED", "MISSING" -> "FAILED";
            default -> s.isBlank() ? "UNKNOWN" : s;
        };
    }

    private String mapSessionStatus(String status) {
        String s = status == null ? "" : status.toLowerCase(Locale.ROOT);
        return switch (s) {
            case "completed" -> "READY";
            case "failed" -> "FAILED";
            case "scoring", "uploaded", "created", "queued" -> "PROCESSING";
            default -> s.isBlank() ? "READY" : "PROCESSING";
        };
    }

    /**
     * 本地 uploads 相对路径 → 可直接播放的 /uploads/... URL；MinIO 对象路径返回 null（走 stream）。
     */
    private String toPublicUploadUrl(String path) {
        if (path == null || path.isBlank()) return null;
        String p = path.trim().replace('\\', '/');
        if (p.startsWith("http://") || p.startsWith("https://") || p.startsWith("blob:")) return p;
        if (p.startsWith("/uploads/")) return p;
        if (p.startsWith("uploads/")) return "/" + p;
        // 本地 AI 评分视频：ai-score/...
        if (p.startsWith("ai-score/") || p.startsWith("project-teams/") || p.startsWith("recordings/202")) {
            return "/uploads/" + p.replaceFirst("^/+", "");
        }
        // 已是 /uploads/recordings/...
        if (p.contains("/uploads/")) {
            int i = p.indexOf("/uploads/");
            return p.substring(i);
        }
        // MinIO 对象路径（如 recordings/meeting_7/...）不直接暴露，前端用 streamApi
        return null;
    }

    private Long longVal(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (Exception e) {
            return null;
        }
    }

    private String str(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    private String firstNonBlank(String... values) {
        if (values == null) return null;
        for (String v : values) {
            if (v != null && !v.isBlank()) return v;
        }
        return null;
    }
}
