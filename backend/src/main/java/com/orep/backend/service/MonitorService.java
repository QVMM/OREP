package com.orep.backend.service;

import cn.hutool.http.HttpUtil;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.security.AdminAccess;
import com.orep.backend.dto.MonitorTrackRequest;
import jakarta.annotation.PostConstruct;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class MonitorService {

    private static final int ONLINE_SECONDS = 120;
    private static final int MAX_TEXT = 500;

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    private final Map<String, String> ipLocationCache = new ConcurrentHashMap<>();

    @Value("${orep.monitor.geo.enabled:true}")
    private boolean geoEnabled;

    @Value("${orep.monitor.geo.api-url:http://ip-api.com/json/%s?lang=zh-CN&fields=status,country,countryCode,regionName,city,isp,query}")
    private String geoApiUrl;

    @Value("${orep.monitor.allowed-roles:ADMIN,SCHOOL_ADMIN,TEACHER}")
    private String allowedRoles;

    public MonitorService(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void ensureTables() {
        jdbcTemplate.execute("""
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    tenant_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    role VARCHAR(40) DEFAULT NULL,
                    source VARCHAR(40) NOT NULL,
                    action_type VARCHAR(80) NOT NULL,
                    action_name VARCHAR(255) NOT NULL,
                    method VARCHAR(12) DEFAULT NULL,
                    path VARCHAR(500) DEFAULT NULL,
                    route VARCHAR(255) DEFAULT NULL,
                    page_title VARCHAR(255) DEFAULT NULL,
                    ip_address VARCHAR(64) DEFAULT NULL,
                    ip_location VARCHAR(255) DEFAULT NULL,
                    user_agent VARCHAR(500) DEFAULT NULL,
                    status_code INT DEFAULT NULL,
                    duration_ms BIGINT DEFAULT NULL,
                    metadata JSON DEFAULT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_tenant_created (tenant_id, created_at),
                    KEY idx_user_created (user_id, created_at),
                    KEY idx_action_type (action_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户行为监控日志'
                """);
        jdbcTemplate.execute("""
                CREATE TABLE IF NOT EXISTS user_online_status (
                    user_id BIGINT PRIMARY KEY,
                    tenant_id BIGINT NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    role VARCHAR(40) DEFAULT NULL,
                    online TINYINT(1) NOT NULL DEFAULT 0,
                    last_seen_at DATETIME NOT NULL,
                    last_ip VARCHAR(64) DEFAULT NULL,
                    ip_location VARCHAR(255) DEFAULT NULL,
                    user_agent VARCHAR(500) DEFAULT NULL,
                    current_route VARCHAR(255) DEFAULT NULL,
                    current_page VARCHAR(255) DEFAULT NULL,
                    session_id VARCHAR(80) DEFAULT NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_tenant_seen (tenant_id, last_seen_at),
                    KEY idx_online (online)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户在线状态'
                """);
    }

    public void recordBackendAccess(HttpServletRequest request, int statusCode, long durationMs, Exception ex) {
        Long userId = attrLong(request, "userId");
        Long tenantId = attrLong(request, "tenantId");
        if (userId == null || tenantId == null) {
            return;
        }
        String path = request.getRequestURI();
        if (path.startsWith("/api/monitor") || path.startsWith("/api/admin/monitor")) {
            return;
        }

        MonitorTrackRequest body = new MonitorTrackRequest();
        body.setSource("backend");
        body.setActionType("backend_api");
        body.setActionName(buildApiActionName(request.getMethod(), path));
        body.setRoute(path);
        if (ex != null) {
            body.setMetadata("{\"error\":\"" + escapeJson(limit(ex.getClass().getSimpleName())) + "\"}");
        }
        writeLog(
                tenantId,
                userId,
                attrString(request, "username"),
                attrString(request, "role"),
                body,
                request,
                statusCode,
                durationMs
        );
        updateOnlineStatus(tenantId, userId, attrString(request, "username"), attrString(request, "role"), body, request);
    }

    public void trackFrontend(Long tenantId, Long userId, String username, String role, MonitorTrackRequest body, HttpServletRequest request) {
        if (body == null) {
            body = new MonitorTrackRequest();
        }
        if (!StringUtils.hasText(body.getSource())) {
            body.setSource("user_frontend");
        }
        if (!StringUtils.hasText(body.getActionType())) {
            body.setActionType("frontend_event");
        }
        if (!StringUtils.hasText(body.getActionName())) {
            body.setActionName("前端操作");
        }
        writeLog(tenantId, userId, username, role, body, request, 200, null);
        updateOnlineStatus(tenantId, userId, username, role, body, request);
    }

    public void heartbeat(Long tenantId, Long userId, String username, String role, MonitorTrackRequest body, HttpServletRequest request) {
        if (body == null) {
            body = new MonitorTrackRequest();
        }
        if (!StringUtils.hasText(body.getSource())) {
            body.setSource("user_frontend");
        }
        updateOnlineStatus(tenantId, userId, username, role, body, request);
    }

    public Map<String, Object> dashboard(Long tenantId) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("onlineUsers", jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM user_online_status WHERE tenant_id = ? AND last_seen_at >= DATE_SUB(NOW(), INTERVAL ? SECOND)",
                Long.class,
                tenantId,
                ONLINE_SECONDS
        ));
        data.put("todayActions", jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM user_activity_log WHERE tenant_id = ? AND created_at >= CURDATE()",
                Long.class,
                tenantId
        ));
        data.put("frontendActions", jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM user_activity_log WHERE tenant_id = ? AND source IN ('user_frontend','admin_frontend') AND created_at >= CURDATE()",
                Long.class,
                tenantId
        ));
        data.put("backendActions", jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM user_activity_log WHERE tenant_id = ? AND source = 'backend' AND created_at >= CURDATE()",
                Long.class,
                tenantId
        ));
        data.put("actionTypes", jdbcTemplate.queryForList(
                """
                SELECT action_type actionType, COUNT(*) count
                FROM user_activity_log
                WHERE tenant_id = ? AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY action_type
                ORDER BY count DESC
                LIMIT 8
                """,
                tenantId
        ));
        return data;
    }

    public List<Map<String, Object>> listUserStatuses(Long tenantId, String keyword) {
        List<Object> params = new ArrayList<>();
        StringBuilder sql = new StringBuilder("""
                SELECT
                  u.id, u.username, u.email, u.role,
                  COALESCE(s.last_seen_at, u.created_at) lastSeenAt,
                  CASE WHEN s.last_seen_at >= DATE_SUB(NOW(), INTERVAL ? SECOND) THEN 1 ELSE 0 END online,
                  s.last_ip lastIp,
                  s.ip_location ipLocation,
                  s.current_route currentRoute,
                  s.current_page currentPage,
                  s.user_agent userAgent,
                  COALESCE(t.action_count, 0) actionCount
                FROM users u
                LEFT JOIN user_online_status s ON s.user_id = u.id
                LEFT JOIN (
                  SELECT user_id, COUNT(*) action_count
                  FROM user_activity_log
                  WHERE tenant_id = ?
                  GROUP BY user_id
                ) t ON t.user_id = u.id
                WHERE u.tenant_id = ?
                """);
        params.add(ONLINE_SECONDS);
        params.add(tenantId);
        params.add(tenantId);
        if (StringUtils.hasText(keyword)) {
            sql.append(" AND (u.username LIKE ? OR u.email LIKE ? OR CAST(u.id AS CHAR) = ?) ");
            String like = "%" + keyword.trim() + "%";
            params.add(like);
            params.add(like);
            params.add(keyword.trim());
        }
        sql.append(" ORDER BY online DESC, lastSeenAt DESC, u.id DESC");
        return jdbcTemplate.queryForList(sql.toString(), params.toArray());
    }

    public List<Map<String, Object>> listLogs(Long tenantId, Long userId, String source, String actionType, Integer limit) {
        List<Object> params = new ArrayList<>();
        StringBuilder sql = new StringBuilder("""
                SELECT id, user_id userId, username, role, source, action_type actionType,
                       action_name actionName, method, path, route, page_title pageTitle,
                       ip_address ipAddress, ip_location ipLocation, status_code statusCode,
                       duration_ms durationMs, metadata, created_at createdAt
                FROM user_activity_log
                WHERE tenant_id = ?
                """);
        params.add(tenantId);
        if (userId != null) {
            sql.append(" AND user_id = ? ");
            params.add(userId);
        }
        if (StringUtils.hasText(source)) {
            sql.append(" AND source = ? ");
            params.add(source);
        }
        if (StringUtils.hasText(actionType)) {
            sql.append(" AND action_type = ? ");
            params.add(actionType);
        }
        sql.append(" ORDER BY created_at DESC, id DESC LIMIT ? ");
        params.add(Math.max(1, Math.min(limit == null ? 100 : limit, 500)));
        return jdbcTemplate.queryForList(sql.toString(), params.toArray());
    }

    public void assertAdminRole(String role) {
        AdminAccess.assertSuperAdmin(role);
    }

    private void writeLog(
            Long tenantId,
            Long userId,
            String username,
            String role,
            MonitorTrackRequest body,
            HttpServletRequest request,
            Integer statusCode,
            Long durationMs
    ) {
        try {
            String ip = clientIp(request);
            jdbcTemplate.update(
                    """
                    INSERT INTO user_activity_log
                    (tenant_id, user_id, username, role, source, action_type, action_name, method, path, route,
                     page_title, ip_address, ip_location, user_agent, status_code, duration_ms, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tenantId,
                    userId,
                    limit(username),
                    limit(role),
                    limit(defaultText(body.getSource(), "user_frontend")),
                    limit(defaultText(body.getActionType(), "frontend_event")),
                    limit(defaultText(body.getActionName(), "用户操作")),
                    limit(request.getMethod(), 12),
                    limit(request.getRequestURI()),
                    limit(body.getRoute()),
                    limit(body.getPageTitle()),
                    limit(ip, 64),
                    limit(resolveIpLocation(ip)),
                    limit(request.getHeader("User-Agent")),
                    statusCode,
                    durationMs,
                    metadataJson(body)
            );
        } catch (Exception ignored) {
            // Monitoring must never interrupt business traffic.
        }
    }

    private void updateOnlineStatus(
            Long tenantId,
            Long userId,
            String username,
            String role,
            MonitorTrackRequest body,
            HttpServletRequest request
    ) {
        try {
            String ip = clientIp(request);
            jdbcTemplate.update(
                    """
                    INSERT INTO user_online_status
                    (user_id, tenant_id, username, role, online, last_seen_at, last_ip, ip_location, user_agent, current_route, current_page, session_id)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                    ON DUPLICATE KEY UPDATE
                      tenant_id = VALUES(tenant_id),
                      username = VALUES(username),
                      role = VALUES(role),
                      online = 1,
                      last_seen_at = VALUES(last_seen_at),
                      last_ip = VALUES(last_ip),
                      ip_location = VALUES(ip_location),
                      user_agent = VALUES(user_agent),
                      current_route = VALUES(current_route),
                      current_page = VALUES(current_page),
                      session_id = VALUES(session_id)
                    """,
                    userId,
                    tenantId,
                    limit(username),
                    limit(role),
                    LocalDateTime.now(),
                    limit(ip, 64),
                    limit(resolveIpLocation(ip)),
                    limit(request.getHeader("User-Agent")),
                    limit(body.getRoute()),
                    limit(body.getPageTitle()),
                    limit(request.getSession(true).getId(), 80)
            );
        } catch (Exception ignored) {
            // Monitoring must never interrupt business traffic.
        }
    }

    private String metadataJson(MonitorTrackRequest body) throws JsonProcessingException {
        if (StringUtils.hasText(body.getMetadata())) {
            return body.getMetadata();
        }
        if (body.getDetail() == null || body.getDetail().isEmpty()) {
            return null;
        }
        return objectMapper.writeValueAsString(body.getDetail());
    }

    private String resolveIpLocation(String ip) {
        if (!StringUtils.hasText(ip)) {
            return "";
        }
        if ("127.0.0.1".equals(ip) || "::1".equals(ip)) {
            return "本机地址";
        }
        if (ip.startsWith("10.") || ip.startsWith("192.168.") || ip.matches("^172\\.(1[6-9]|2\\d|3[0-1])\\..*")) {
            return "内网地址";
        }
        return ipLocationCache.computeIfAbsent(ip, this::lookupPublicIpLocation);
    }

    private String lookupPublicIpLocation(String ip) {
        if (!geoEnabled) {
            return "公网地址";
        }
        try {
            String body = HttpUtil.createGet(String.format(geoApiUrl, ip)).timeout(900).execute().body();
            Map<String, Object> data = objectMapper.readValue(body, new TypeReference<>() {});
            if (!"success".equals(String.valueOf(data.get("status")))) {
                return "公网地址";
            }
            return formatIpLocation(data);
        } catch (Exception ignored) {
            return "公网地址";
        }
    }

    private String formatIpLocation(Map<String, Object> data) {
        String country = textValue(data.get("country"));
        String countryCode = textValue(data.get("countryCode"));
        String province = textValue(data.get("regionName"));
        String city = textValue(data.get("city"));
        String isp = textValue(data.get("isp"));

        List<String> parts = new ArrayList<>();
        if ("CN".equalsIgnoreCase(countryCode) || country.contains("中国")) {
            addPart(parts, normalizeChineseProvince(province));
            addPart(parts, normalizeChineseCity(city));
            addPart(parts, isp);
        } else {
            addPart(parts, country);
            addPart(parts, province);
            addPart(parts, city);
            addPart(parts, isp);
        }
        return parts.isEmpty() ? "公网地址" : String.join(" / ", parts);
    }

    private String normalizeChineseProvince(String province) {
        if (!StringUtils.hasText(province)) {
            return "";
        }
        if (
                province.endsWith("省")
                        || province.endsWith("市")
                        || province.endsWith("自治区")
                        || province.endsWith("特别行政区")
        ) {
            return province;
        }
        return province + "省";
    }

    private String normalizeChineseCity(String city) {
        if (!StringUtils.hasText(city)) {
            return "";
        }
        if (
                city.endsWith("市")
                        || city.endsWith("地区")
                        || city.endsWith("盟")
                        || city.endsWith("自治州")
                        || city.endsWith("特别行政区")
        ) {
            return city;
        }
        return city + "市";
    }

    private void addPart(List<String> parts, Object value) {
        String text = textValue(value);
        if (StringUtils.hasText(text) && !"null".equalsIgnoreCase(text) && !parts.contains(text)) {
            parts.add(text);
        }
    }

    private String textValue(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String clientIp(HttpServletRequest request) {
        String forwarded = request.getHeader("X-Forwarded-For");
        if (StringUtils.hasText(forwarded)) {
            return forwarded.split(",")[0].trim();
        }
        String realIp = request.getHeader("X-Real-IP");
        if (StringUtils.hasText(realIp)) {
            return realIp.trim();
        }
        return request.getRemoteAddr();
    }

    private String buildApiActionName(String method, String path) {
        return method + " " + path;
    }

    private Long attrLong(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value instanceof Long ? (Long) value : null;
    }

    private String attrString(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value == null ? "" : String.valueOf(value);
    }

    private String defaultText(String value, String fallback) {
        return StringUtils.hasText(value) ? value : fallback;
    }

    private String limit(String value) {
        return limit(value, MAX_TEXT);
    }

    private String limit(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.length() > maxLength ? trimmed.substring(0, maxLength) : trimmed;
    }

    private String escapeJson(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
