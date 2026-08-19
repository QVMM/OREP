package com.orep.backend.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.jdbc.support.KeyHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.PreparedStatement;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class TeacherGrowthService {

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("pdf", "png", "jpg", "jpeg");
    private static final long MAX_UPLOAD_BYTES = 15L * 1024 * 1024;

    private final JdbcTemplate jdbc;
    private final PdfService pdfService;
    private final Path uploadRoot;

    public TeacherGrowthService(
            JdbcTemplate jdbc,
            PdfService pdfService,
            @Value("${file.upload-dir:./uploads}") String uploadDir
    ) {
        this.jdbc = jdbc;
        this.pdfService = pdfService;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public List<Map<String, Object>> listCertificates(Long tenantId, Long teamId) {
        if (teamId == null) {
            return jdbc.queryForList("""
                SELECT c.id, c.title, c.certificate_type certificateType, c.description,
                       c.issuer_user_id issuerUserId, c.issued_at issuedAt, c.certificate_no certificateNo,
                       c.pdf_url pdfUrl, c.status, c.source_type sourceType, c.award_level awardLevel,
                       c.issuer_name issuerName, c.original_file_name originalFileName, c.mime_type mimeType,
                       c.created_at createdAt
                FROM student_certificate c
                WHERE c.tenant_id = ?
                ORDER BY c.issued_at DESC, c.id DESC
                LIMIT 100
                """, tenantId);
        }
        return jdbc.queryForList("""
            SELECT DISTINCT c.id, c.title, c.certificate_type certificateType, c.description,
                   c.issuer_user_id issuerUserId, c.issued_at issuedAt, c.certificate_no certificateNo,
                   c.pdf_url pdfUrl, c.status, c.source_type sourceType, c.award_level awardLevel,
                   c.issuer_name issuerName, c.original_file_name originalFileName, c.mime_type mimeType,
                   c.created_at createdAt
            FROM student_certificate c
            JOIN student_certificate_recipient r ON r.certificate_id = c.id
            WHERE c.tenant_id = ?
              AND (
                (r.recipient_type = 'TEAM' AND r.team_id = ?)
                OR (r.recipient_type = 'USER' AND r.user_id IN (
                    SELECT user_id FROM project_team_member WHERE team_id = ?
                ))
              )
            ORDER BY c.issued_at DESC, c.id DESC
            LIMIT 100
            """, tenantId, teamId, teamId);
    }

    @Transactional
    public Map<String, Object> createCertificate(Long tenantId, Long issuerUserId, Map<String, Object> body) {
        String title = requiredText(body.get("title"), "请填写奖状名称");
        String recipientType = recipientType(body.get("recipientType"));
        List<Long> recipientIds = longList(body.get("recipientIds"));
        if (recipientIds.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择获奖个人或团队");
        assertRecipients(tenantId, recipientType, recipientIds);

        LocalDateTime issuedAt = dateTime(body.get("issuedAt"), LocalDateTime.now());
        String sourceType = sourceType(body.get("sourceType"), "GENERATED");
        String awardLevel = nullableText(body.get("awardLevel"));
        String issuerName = nullableText(body.get("issuerName"));
        String description = nullableText(body.get("description"));
        String certificateNo = nullableText(body.get("certificateNo"));
        if (certificateNo == null) {
            certificateNo = "JSDN-" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                    + "-" + UUID.randomUUID().toString().substring(0, 6).toUpperCase(Locale.ROOT);
        }

        String pdfUrl = nullableText(body.get("pdfUrl"));
        String originalFileName = nullableText(body.get("originalFileName"));
        String mimeType = nullableText(body.get("mimeType"));

        if ("GENERATED".equals(sourceType)) {
            try {
                List<String> recipientNames = resolveRecipientNames(recipientType, recipientIds);
                byte[] pdfBytes = pdfService.generateCertificatePdf(
                        title,
                        awardLevel,
                        description,
                        issuerName == null ? "竞赛大脑" : issuerName,
                        certificateNo,
                        issuedAt.format(DateTimeFormatter.ofPattern("yyyy-MM-dd")),
                        recipientNames
                );
                String stored = storeBytes(pdfBytes, "pdf", "application/pdf");
                pdfUrl = stored;
                originalFileName = title + ".pdf";
                mimeType = "application/pdf";
            } catch (IOException ex) {
                throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                        ex.getMessage() == null ? "奖状 PDF 生成失败" : ex.getMessage());
            }
        } else if (pdfUrl == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "上传奖状需要提供文件");
        }

        Long id = insert("""
            INSERT INTO student_certificate
            (tenant_id, title, certificate_type, description, issuer_user_id, issued_at, certificate_no, pdf_url, status,
             source_type, award_level, issuer_name, original_file_name, mime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?)
            """,
            tenantId,
            title,
            recipientType.equals("TEAM") ? "TEAM" : "PERSONAL",
            description,
            issuerUserId,
            Timestamp.valueOf(issuedAt),
            certificateNo,
            pdfUrl,
            sourceType,
            awardLevel,
            issuerName,
            originalFileName,
            mimeType
        );

        for (Long recipientId : recipientIds) {
            jdbc.update("""
                INSERT INTO student_certificate_recipient
                (certificate_id, recipient_type, user_id, team_id)
                VALUES (?, ?, ?, ?)
                """, id, recipientType, recipientType.equals("USER") ? recipientId : null, recipientType.equals("TEAM") ? recipientId : null);
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", id);
        result.put("status", "ACTIVE");
        result.put("certificateNo", certificateNo);
        result.put("pdfUrl", pdfUrl);
        result.put("sourceType", sourceType);
        return result;
    }

    @Transactional
    public Map<String, Object> uploadCertificate(
            Long tenantId,
            Long issuerUserId,
            MultipartFile file,
            Map<String, Object> body
    ) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请上传奖状文件");
        }
        if (file.getSize() > MAX_UPLOAD_BYTES) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "奖状文件不能超过 15MB");
        }
        String original = file.getOriginalFilename() == null ? "certificate" : file.getOriginalFilename();
        String extension = extensionOf(original);
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "仅支持 PDF、PNG、JPG 奖状文件");
        }
        String mime = detectMime(extension, file.getContentType());
        try {
            String pdfUrl = storeBytes(file.getBytes(), extension, mime);
            Map<String, Object> payload = new LinkedHashMap<>(body == null ? Map.of() : body);
            payload.put("sourceType", "UPLOADED");
            payload.put("pdfUrl", pdfUrl);
            payload.put("originalFileName", original);
            payload.put("mimeType", mime);
            return createCertificate(tenantId, issuerUserId, payload);
        } catch (IOException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "奖状文件保存失败");
        }
    }

    @Transactional
    public Map<String, Object> revokeCertificate(Long tenantId, Long certificateId) {
        Integer updated = jdbc.update("""
            UPDATE student_certificate
            SET status = 'REVOKED'
            WHERE id = ? AND tenant_id = ? AND status = 'ACTIVE'
            """, certificateId, tenantId);
        if (updated == null || updated == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "奖状不存在或已撤销");
        }
        return Map.of("id", certificateId, "status", "REVOKED");
    }

    @Transactional
    public Map<String, Object> createRectification(Long tenantId, Long issuerUserId, Map<String, Object> body) {
        String title = requiredText(body.get("title"), "请填写惩罚或整改名称");
        String recipientType = recipientType(body.get("recipientType"));
        List<Long> recipientIds = longList(body.get("recipientIds"));
        if (recipientIds.isEmpty()) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请选择相关个人或团队");
        assertRecipients(tenantId, recipientType, recipientIds);
        LocalDateTime issuedAt = dateTime(body.get("issuedAt"), LocalDateTime.now());
        LocalDateTime dueAt = dateTime(body.get("dueAt"), null);
        Long relatedTaskId = nullableLong(body.get("relatedTaskId"));
        if (relatedTaskId != null) {
            Integer count = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM project_task t
                JOIN project_team pt ON pt.id = t.team_id
                WHERE t.id = ? AND pt.tenant_id = ?
                """, Integer.class, relatedTaskId, tenantId);
            if (count == null || count == 0) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "关联任务不存在");
        }

        Long id = insert("""
            INSERT INTO student_rectification
            (tenant_id, title, description, requirement_text, issuer_user_id, issued_at, due_at, status, related_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            tenantId,
            title,
            nullableText(body.get("description")),
            nullableText(body.get("requirementText")),
            issuerUserId,
            Timestamp.valueOf(issuedAt),
            dueAt == null ? null : Timestamp.valueOf(dueAt),
            relatedTaskId
        );

        for (Long recipientId : recipientIds) {
            jdbc.update("""
                INSERT INTO student_rectification_recipient
                (rectification_id, recipient_type, user_id, team_id)
                VALUES (?, ?, ?, ?)
                """, id, recipientType, recipientType.equals("USER") ? recipientId : null, recipientType.equals("TEAM") ? recipientId : null);
        }
        return Map.of("id", id, "status", "PENDING");
    }

    private String storeBytes(byte[] bytes, String extension, String mimeType) throws IOException {
        String storedName = UUID.randomUUID().toString().replace("-", "") + "." + extension;
        Path relative = Paths.get("certificates", storedName);
        Path target = uploadRoot.resolve(relative).normalize();
        if (!target.startsWith(uploadRoot)) {
            throw new IOException("非法存储路径");
        }
        Files.createDirectories(target.getParent());
        Files.write(target, bytes);
        return "/uploads/" + relative.toString().replace('\\', '/');
    }

    private List<String> resolveRecipientNames(String recipientType, List<Long> recipientIds) {
        if (recipientIds.isEmpty()) return List.of();
        String placeholders = String.join(",", java.util.Collections.nCopies(recipientIds.size(), "?"));
        if ("USER".equals(recipientType)) {
            return jdbc.queryForList(
                    "SELECT username FROM users WHERE id IN (" + placeholders + ")",
                    String.class,
                    recipientIds.toArray()
            );
        }
        return jdbc.queryForList(
                "SELECT name FROM project_team WHERE id IN (" + placeholders + ")",
                String.class,
                recipientIds.toArray()
        );
    }

    private void assertRecipients(Long tenantId, String recipientType, List<Long> recipientIds) {
        String table = recipientType.equals("USER") ? "users" : "project_team";
        String placeholders = String.join(",", java.util.Collections.nCopies(recipientIds.size(), "?"));
        Object[] args = new Object[recipientIds.size() + 1];
        for (int index = 0; index < recipientIds.size(); index++) args[index] = recipientIds.get(index);
        args[recipientIds.size()] = tenantId;
        Integer count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM " + table + " WHERE id IN (" + placeholders + ") AND tenant_id = ?",
            Integer.class,
            args
        );
        if (count == null || count != recipientIds.size()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "部分接收对象不存在或不属于当前机构");
        }
    }

    private Long insert(String sql, Object... args) {
        KeyHolder keyHolder = new GeneratedKeyHolder();
        jdbc.update(connection -> {
            PreparedStatement statement = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            for (int index = 0; index < args.length; index++) statement.setObject(index + 1, args[index]);
            return statement;
        }, keyHolder);
        Number key = keyHolder.getKey();
        if (key == null) throw new IllegalStateException("创建记录失败");
        return key.longValue();
    }

    private String recipientType(Object value) {
        String type = String.valueOf(value == null ? "" : value).trim().toUpperCase(Locale.ROOT);
        if (!type.equals("USER") && !type.equals("TEAM")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "接收对象类型必须是个人或团队");
        }
        return type;
    }

    private String sourceType(Object value, String fallback) {
        String type = String.valueOf(value == null ? fallback : value).trim().toUpperCase(Locale.ROOT);
        if (!"GENERATED".equals(type) && !"UPLOADED".equals(type)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "奖状来源必须是 GENERATED 或 UPLOADED");
        }
        return type;
    }

    private String extensionOf(String name) {
        int index = name.lastIndexOf('.');
        if (index < 0 || index == name.length() - 1) return "";
        return name.substring(index + 1).toLowerCase(Locale.ROOT);
    }

    private String detectMime(String extension, String contentType) {
        if (contentType != null && !contentType.isBlank() && !contentType.equals("application/octet-stream")) {
            return contentType;
        }
        return switch (extension) {
            case "pdf" -> "application/pdf";
            case "png" -> "image/png";
            case "jpg", "jpeg" -> "image/jpeg";
            default -> "application/octet-stream";
        };
    }

    private List<Long> longList(Object value) {
        if (value instanceof List<?> values) {
            return values.stream().map(this::nullableLong).filter(java.util.Objects::nonNull).distinct().toList();
        }
        if (value instanceof String text && !text.isBlank()) {
            List<Long> ids = new ArrayList<>();
            for (String part : text.split(",")) {
                Long id = nullableLong(part.trim());
                if (id != null) ids.add(id);
            }
            return ids.stream().distinct().toList();
        }
        Long single = nullableLong(value);
        return single == null ? List.of() : List.of(single);
    }

    private Long nullableLong(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String requiredText(Object value, String message) {
        String text = nullableText(value);
        if (text == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
        return text;
    }

    private String nullableText(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isBlank() ? null : text;
    }

    private LocalDateTime dateTime(Object value, LocalDateTime fallback) {
        if (value == null || String.valueOf(value).isBlank()) return fallback;
        try {
            String text = String.valueOf(value).trim();
            if (text.length() == 10) return java.time.LocalDate.parse(text).atTime(23, 59, 59);
            return LocalDateTime.parse(text.replace(' ', 'T'));
        } catch (Exception ignored) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "日期时间格式不正确");
        }
    }
}
