package com.orep.backend.service;

import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.safety.Safelist;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import javax.imageio.IIOImage;
import javax.imageio.ImageIO;
import javax.imageio.ImageWriteParam;
import javax.imageio.ImageWriter;
import javax.imageio.stream.ImageOutputStream;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

@Service
public class TrainingDayContentService {
    private static final long MAX_IMAGE_BYTES = 1024L * 1024L;
    private static final long MAX_ATTACHMENT_BYTES = 500L * 1024L * 1024L;
    private static final int MAX_IMAGE_SIDE = 2560;
    private static final Set<String> ATTACHMENT_EXTENSIONS = Set.of("pdf", "doc", "docx", "zip", "rar", "7z");
    private static final Map<String, String> TEXT_COLOR_VALUES = Map.ofEntries(
            Map.entry("ink", "#12141a"),
            Map.entry("muted", "#6b7280"),
            Map.entry("orange", "#e84a1c"),
            Map.entry("green", "#0f9f6e"),
            Map.entry("amber", "#d98200"),
            Map.entry("red", "#d83a45")
    );
    private static final Map<String, String> TEXT_COLOR_NAMES = Map.ofEntries(
            Map.entry("#12141a", "ink"),
            Map.entry("rgb(18,20,26)", "ink"),
            Map.entry("#6b7280", "muted"),
            Map.entry("rgb(107,114,128)", "muted"),
            Map.entry("#e84a1c", "orange"),
            Map.entry("rgb(232,74,28)", "orange"),
            Map.entry("#0f9f6e", "green"),
            Map.entry("rgb(15,159,110)", "green"),
            Map.entry("#d98200", "amber"),
            Map.entry("rgb(217,130,0)", "amber"),
            Map.entry("#d83a45", "red"),
            Map.entry("rgb(216,58,69)", "red")
    );

    private final JdbcTemplate jdbc;
    private final Path uploadRoot;

    public TrainingDayContentService(JdbcTemplate jdbc, @Value("${file.upload-dir:./uploads}") String uploadDir) {
        this.jdbc = jdbc;
        this.uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public String sanitizeHtml(Object rawValue) {
        String raw = rawValue == null ? "" : String.valueOf(rawValue);
        Safelist safelist = new Safelist()
                .addTags("p", "h1", "h2", "h3", "strong", "b", "ul", "ol", "li", "blockquote", "a", "img", "br", "span")
                .addAttributes("a", "href", "title", "target", "rel")
                .addAttributes("img", "src", "alt", "title")
                .addAttributes("span", "style", "data-text-color")
                .addProtocols("a", "href", "http", "https");
        Document.OutputSettings settings = new Document.OutputSettings().prettyPrint(false);
        String clean = Jsoup.clean(raw, "", safelist, settings);
        Document document = Jsoup.parseBodyFragment(clean);
        for (Element image : document.select("img")) {
            String src = image.attr("src").trim();
            if (!src.startsWith("/uploads/task/instructions/")) {
                image.remove();
                continue;
            }
            int cut = src.length();
            int query = src.indexOf('?');
            if (query >= 0) cut = query;
            int hash = src.indexOf('#');
            if (hash >= 0 && hash < cut) cut = hash;
            if (cut < src.length()) image.attr("src", src.substring(0, cut));
        }
        for (Element span : document.select("span")) {
            String colorName = normalizeTextColor(span);
            if (colorName == null) {
                span.unwrap();
                continue;
            }
            String colorValue = TEXT_COLOR_VALUES.get(colorName);
            span.clearAttributes();
            span.attr("data-text-color", colorName);
            span.attr("style", "color: " + colorValue);
        }
        for (Element link : document.select("a")) {
            String href = link.attr("href").trim().toLowerCase(Locale.ROOT);
            if (!(href.startsWith("http://") || href.startsWith("https://") || href.startsWith("/") || href.startsWith("#"))) {
                link.unwrap();
                continue;
            }
            link.attr("target", "_blank");
            link.attr("rel", "noopener noreferrer");
        }
        return document.body().html();
    }

    private String normalizeTextColor(Element span) {
        String declaredName = span.attr("data-text-color").trim().toLowerCase(Locale.ROOT);
        if (TEXT_COLOR_VALUES.containsKey(declaredName)) return declaredName;
        String style = span.attr("style");
        for (String declaration : style.split(";")) {
            String[] pair = declaration.split(":", 2);
            if (pair.length != 2 || !"color".equalsIgnoreCase(pair[0].trim())) continue;
            String compactValue = pair[1].trim().toLowerCase(Locale.ROOT).replaceAll("\\s+", "");
            return TEXT_COLOR_NAMES.get(compactValue);
        }
        return null;
    }

    public List<Map<String, Object>> teacherAttachments(Long tenantId, Long userId, String role, Long dayId) {
        assertTeacherReadAccess(tenantId, userId, role, dayId);
        return attachments(dayId, false);
    }

    public List<Map<String, Object>> studentAttachments(Long dayId) {
        return attachments(dayId, true);
    }

    public Map<String, Object> uploadContentImage(Long tenantId, Long userId, String role, Long dayId, MultipartFile file) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        if (file == null || file.isEmpty()) throw badRequest("请选择要插入的图片");
        BufferedImage source;
        try {
            source = ImageIO.read(file.getInputStream());
        } catch (IOException exception) {
            throw badRequest("图片读取失败");
        }
        if (source == null) throw badRequest("仅支持常见 JPG、PNG 等图片格式");

        boolean alpha = source.getColorModel().hasAlpha();
        BufferedImage working = fitWithin(source, MAX_IMAGE_SIDE);
        byte[] bytes = encodeWithinLimit(working, alpha);
        String extension = alpha ? "png" : "jpg";
        String fileName = UUID.randomUUID() + "." + extension;
        Path relative = Paths.get("task", "instructions", String.valueOf(dayId), "images", fileName);
        write(relative, bytes);
        return Map.of(
                "url", "/uploads/" + relative.toString().replace('\\', '/'),
                "fileName", fileName,
                "fileSize", bytes.length,
                "mimeType", alpha ? "image/png" : "image/jpeg",
                "width", working.getWidth(),
                "height", working.getHeight()
        );
    }

    @Transactional
    public Map<String, Object> uploadAttachment(Long tenantId, Long userId, String role, Long dayId, MultipartFile file) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        if (file == null || file.isEmpty()) throw badRequest("请选择附件");
        if (file.getSize() > MAX_ATTACHMENT_BYTES) throw badRequest("单个附件不能超过 500MB");
        String original = safeDisplayName(file.getOriginalFilename());
        String extension = extension(original);
        if (!ATTACHMENT_EXTENSIONS.contains(extension)) {
            throw badRequest("附件仅支持 PDF、Word（DOC、DOCX）与压缩包（ZIP、RAR、7Z）");
        }
        validateAttachmentContent(file, extension);

        String storedName = UUID.randomUUID() + "." + extension;
        Path relative = Paths.get("task", "instructions", String.valueOf(dayId), "attachments", storedName);
        try {
            Path target = uploadRoot.resolve(relative).normalize();
            if (!target.startsWith(uploadRoot)) throw badRequest("附件路径不合法");
            Files.createDirectories(target.getParent());
            Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "附件保存失败");
        }
        int nextOrder = jdbc.queryForObject("SELECT COALESCE(MAX(sort_order),-1)+1 FROM training_day_attachment WHERE training_day_id=?", Integer.class, dayId);
        String url = "/uploads/" + relative.toString().replace('\\', '/');
        jdbc.update("""
            INSERT INTO training_day_attachment
            (training_day_id,file_name,file_url,file_size,mime_type,sort_order,status,created_by)
            VALUES (?,?,?,?,?,?,'PENDING',?)
            """, dayId, original, url, file.getSize(), mimeType(extension), nextOrder, userId);
        return jdbc.queryForMap("""
            SELECT id,file_name fileName,file_url fileUrl,file_size fileSize,mime_type mimeType,
                   sort_order sortOrder,status,created_at createdAt
            FROM training_day_attachment WHERE training_day_id=? ORDER BY id DESC LIMIT 1
            """, dayId);
    }

    @Transactional
    public void deleteAttachment(Long tenantId, Long userId, String role, Long dayId, Long attachmentId) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        List<Map<String, Object>> rows = jdbc.queryForList("SELECT file_url fileUrl FROM training_day_attachment WHERE id=? AND training_day_id=?", attachmentId, dayId);
        if (rows.isEmpty()) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "附件不存在");
        jdbc.update("DELETE FROM training_day_attachment WHERE id=? AND training_day_id=?", attachmentId, dayId);
        deleteStoredFile(String.valueOf(rows.get(0).get("fileUrl")));
    }

    @Transactional
    public List<Map<String, Object>> reorderAttachments(Long tenantId, Long userId, String role, Long dayId, List<Long> ids) {
        assertTeacherWriteAccess(tenantId, userId, role, dayId);
        if (ids != null) {
            int order = 0;
            for (Long id : ids) {
                if (id != null) jdbc.update("UPDATE training_day_attachment SET sort_order=? WHERE id=? AND training_day_id=?", order++, id, dayId);
            }
        }
        return attachments(dayId, false);
    }

    public void activateAttachments(Long dayId) {
        jdbc.update("UPDATE training_day_attachment SET status='ACTIVE' WHERE training_day_id=? AND status='PENDING'", dayId);
    }

    private List<Map<String, Object>> attachments(Long dayId, boolean activeOnly) {
        String statusClause = activeOnly ? " AND status='ACTIVE'" : "";
        return jdbc.queryForList("""
            SELECT id,file_name fileName,file_url fileUrl,file_size fileSize,mime_type mimeType,
                   sort_order sortOrder,status,created_at createdAt
            FROM training_day_attachment
            WHERE training_day_id=?
            """ + statusClause + " ORDER BY sort_order ASC,id ASC", dayId);
    }

    private void assertTeacherWriteAccess(Long tenantId, Long userId, String role, Long dayId) {
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        List<Map<String, Object>> days = jdbc.queryForList("""
            SELECT d.camp_id campId
            FROM training_day d
            JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
            WHERE d.id=?
            """, tenantId, dayId);
        if (days.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "训练日不存在");
        }
        if (Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole)) return;
        if (!"TEACHER".equals(normalizedRole)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权编辑该训练日");
        }
        Long campId = longValue(days.get(0).get("campId"));
        List<Long> activeTeamIds = jdbc.queryForList("""
            SELECT ct.team_id
            FROM training_camp_team ct
            JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=?
            WHERE ct.camp_id=? AND ct.status='ACTIVE'
            ORDER BY ct.team_id
            """, Long.class, tenantId, campId);
        List<Long> accessibleTeamIds = jdbc.queryForList("""
            SELECT DISTINCT pt.id
            FROM project_team pt
            JOIN training_camp_team ct ON ct.team_id=pt.id
              AND ct.camp_id=? AND ct.status='ACTIVE'
            LEFT JOIN project_team_member mentor ON mentor.team_id=pt.id
              AND mentor.user_id=? AND mentor.role_in_team='MENTOR'
            WHERE pt.tenant_id=? AND pt.status='ACTIVE'
              AND (pt.mentor_id=? OR mentor.user_id IS NOT NULL)
            ORDER BY pt.id
            """, Long.class, campId, userId, tenantId, userId);
        if (activeTeamIds.isEmpty() || !accessibleTeamIds.containsAll(activeTeamIds)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "当前教师未覆盖该营期全部团队");
        }
    }

    private void assertTeacherReadAccess(Long tenantId, Long userId, String role, Long dayId) {
        String normalizedRole = String.valueOf(role).toUpperCase(Locale.ROOT);
        boolean administrator = Set.of("ADMIN", "SCHOOL_ADMIN").contains(normalizedRole);
        Integer count = administrator
                ? jdbc.queryForObject("""
                    SELECT COUNT(DISTINCT pt.id) FROM training_day d
                    JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
                    JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                    JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
                    WHERE d.id=?
                    """, Integer.class, tenantId, dayId)
                : jdbc.queryForObject("""
                    SELECT COUNT(DISTINCT pt.id) FROM training_day d
                    JOIN training_camp c ON c.id=d.camp_id AND c.tenant_id=?
                    JOIN training_camp_team ct ON ct.camp_id=c.id AND ct.status='ACTIVE'
                    JOIN project_team pt ON pt.id=ct.team_id AND pt.tenant_id=c.tenant_id
                    WHERE d.id=? AND (pt.mentor_id=? OR EXISTS (
                      SELECT 1 FROM project_team_member tm
                      WHERE tm.team_id=pt.id AND tm.user_id=? AND tm.role_in_team='MENTOR'
                    ))
                    """, Integer.class, tenantId, dayId, userId, userId);
        if (count == null || count == 0) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权查看该训练日");
        }
    }

    private byte[] encodeWithinLimit(BufferedImage source, boolean alpha) {
        BufferedImage current = source;
        for (int round = 0; round < 14; round++) {
            byte[] bytes = alpha ? encodePng(current) : encodeJpeg(current, Math.max(0.56f, 0.9f - round * 0.04f));
            if (bytes.length <= MAX_IMAGE_BYTES) return bytes;
            current = resize(current, Math.max(1, (int) (current.getWidth() * 0.86)), Math.max(1, (int) (current.getHeight() * 0.86)), alpha);
        }
        byte[] fallback = alpha ? encodePng(current) : encodeJpeg(current, 0.5f);
        if (fallback.length > MAX_IMAGE_BYTES) throw badRequest("图片内容过于复杂，压缩后仍超过 1MB，请换一张图片");
        return fallback;
    }

    private BufferedImage fitWithin(BufferedImage source, int maxSide) {
        int width = source.getWidth();
        int height = source.getHeight();
        if (Math.max(width, height) <= maxSide) return source;
        double scale = maxSide / (double) Math.max(width, height);
        return resize(source, Math.max(1, (int) Math.round(width * scale)), Math.max(1, (int) Math.round(height * scale)), source.getColorModel().hasAlpha());
    }

    private BufferedImage resize(BufferedImage source, int width, int height, boolean alpha) {
        BufferedImage target = new BufferedImage(width, height, alpha ? BufferedImage.TYPE_INT_ARGB : BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = target.createGraphics();
        if (!alpha) {
            graphics.setColor(Color.WHITE);
            graphics.fillRect(0, 0, width, height);
        }
        graphics.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BICUBIC);
        graphics.setRenderingHint(RenderingHints.KEY_RENDERING, RenderingHints.VALUE_RENDER_QUALITY);
        graphics.drawImage(source, 0, 0, width, height, null);
        graphics.dispose();
        return target;
    }

    private byte[] encodePng(BufferedImage image) {
        try (ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            ImageIO.write(image, "png", output);
            return output.toByteArray();
        } catch (IOException exception) {
            throw badRequest("PNG 图片压缩失败");
        }
    }

    private byte[] encodeJpeg(BufferedImage image, float quality) {
        try (ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            ImageWriter writer = ImageIO.getImageWritersByFormatName("jpeg").next();
            try (ImageOutputStream imageOutput = ImageIO.createImageOutputStream(output)) {
                writer.setOutput(imageOutput);
                ImageWriteParam params = writer.getDefaultWriteParam();
                params.setCompressionMode(ImageWriteParam.MODE_EXPLICIT);
                params.setCompressionQuality(quality);
                writer.write(null, new IIOImage(image, null, null), params);
            } finally {
                writer.dispose();
            }
            return output.toByteArray();
        } catch (IOException exception) {
            throw badRequest("JPG 图片压缩失败");
        }
    }

    private void write(Path relative, byte[] bytes) {
        try {
            Path target = uploadRoot.resolve(relative).normalize();
            if (!target.startsWith(uploadRoot)) throw badRequest("图片路径不合法");
            Files.createDirectories(target.getParent());
            Files.write(target, bytes);
        } catch (IOException exception) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "图片保存失败");
        }
    }

    private void deleteStoredFile(String url) {
        if (url == null || !url.startsWith("/uploads/task/instructions/")) return;
        try {
            Path target = uploadRoot.resolve(url.substring("/uploads/".length())).normalize();
            if (target.startsWith(uploadRoot)) Files.deleteIfExists(target);
        } catch (IOException ignored) { }
    }

    public void deleteCampFiles(Collection<Long> dayIds, Collection<String> urls) {
        if (urls != null) {
            for (String url : urls) deleteUploadFile(url);
        }
        if (dayIds == null) return;
        for (Long dayId : dayIds) {
            if (dayId == null) continue;
            deleteTree(uploadRoot.resolve(Paths.get("task", "instructions", String.valueOf(dayId))).normalize());
        }
    }

    private void deleteUploadFile(String url) {
        if (url == null || !url.startsWith("/uploads/")) return;
        try {
            Path target = uploadRoot.resolve(url.substring("/uploads/".length())).normalize();
            if (target.startsWith(uploadRoot)) Files.deleteIfExists(target);
        } catch (IOException ignored) { }
    }

    private void deleteTree(Path root) {
        if (!root.startsWith(uploadRoot) || !Files.exists(root)) return;
        try (var paths = Files.walk(root)) {
            paths.sorted(Comparator.reverseOrder()).forEach(path -> {
                try {
                    Files.deleteIfExists(path);
                } catch (IOException ignored) { }
            });
        } catch (IOException ignored) { }
    }

    private String safeDisplayName(String name) {
        String value = name == null ? "附件" : Paths.get(name).getFileName().toString().trim();
        if (value.isBlank()) value = "附件";
        return value.length() > 255 ? value.substring(value.length() - 255) : value;
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        if (value == null) return null;
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private String extension(String name) {
        int index = name.lastIndexOf('.');
        return index < 0 ? "" : name.substring(index + 1).toLowerCase(Locale.ROOT);
    }

    private String mimeType(String extension) {
        return switch (extension) {
            case "pdf" -> "application/pdf";
            case "doc" -> "application/msword";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "zip" -> "application/zip";
            case "rar" -> "application/vnd.rar";
            case "7z" -> "application/x-7z-compressed";
            default -> "application/octet-stream";
        };
    }

    private void validateAttachmentContent(MultipartFile file, String extension) {
        try {
            if ("pdf".equals(extension)) {
                try (InputStream input = new BufferedInputStream(file.getInputStream())) {
                    byte[] header = input.readNBytes(5);
                    if (header.length != 5 || header[0] != '%' || header[1] != 'P' || header[2] != 'D'
                            || header[3] != 'F' || header[4] != '-') {
                        throw badRequest("文件内容不是有效的 PDF");
                    }
                }
                return;
            }
            if ("doc".equals(extension)) {
                byte[] expected = {(byte) 0xD0, (byte) 0xCF, 0x11, (byte) 0xE0, (byte) 0xA1, (byte) 0xB1, 0x1A, (byte) 0xE1};
                try (InputStream input = new BufferedInputStream(file.getInputStream())) {
                    byte[] header = input.readNBytes(expected.length);
                    if (header.length != expected.length) throw badRequest("文件内容不是有效的 Word 文档");
                    for (int index = 0; index < expected.length; index++) {
                        if (header[index] != expected[index]) throw badRequest("文件内容不是有效的 Word 文档");
                    }
                }
                return;
            }
            if ("zip".equals(extension)) {
                try (InputStream input = new BufferedInputStream(file.getInputStream())) {
                    byte[] header = input.readNBytes(4);
                    // Local file header PK\x03\x04, empty archive PK\x05\x06, or spanned PK\x07\x08
                    boolean ok = header.length == 4
                            && header[0] == 'P'
                            && header[1] == 'K'
                            && ((header[2] == 3 && header[3] == 4)
                            || (header[2] == 5 && header[3] == 6)
                            || (header[2] == 7 && header[3] == 8));
                    if (!ok) throw badRequest("文件内容不是有效的 ZIP 压缩包");
                }
                return;
            }
            if ("rar".equals(extension)) {
                try (InputStream input = new BufferedInputStream(file.getInputStream())) {
                    byte[] header = input.readNBytes(7);
                    boolean rar4 = header.length >= 7
                            && header[0] == 'R' && header[1] == 'a' && header[2] == 'r'
                            && header[3] == '!' && header[4] == 0x1A && header[5] == 0x07 && header[6] == 0x00;
                    boolean rar5 = header.length >= 7
                            && header[0] == 'R' && header[1] == 'a' && header[2] == 'r'
                            && header[3] == '!' && header[4] == 0x1A && header[5] == 0x07 && header[6] == 0x01;
                    if (!rar4 && !rar5) throw badRequest("文件内容不是有效的 RAR 压缩包");
                }
                return;
            }
            if ("7z".equals(extension)) {
                try (InputStream input = new BufferedInputStream(file.getInputStream())) {
                    byte[] header = input.readNBytes(6);
                    boolean ok = header.length == 6
                            && header[0] == '7' && header[1] == 'z'
                            && (header[2] & 0xFF) == 0xBC && (header[3] & 0xFF) == 0xAF
                            && (header[4] & 0xFF) == 0x27 && (header[5] & 0xFF) == 0x1C;
                    if (!ok) throw badRequest("文件内容不是有效的 7Z 压缩包");
                }
                return;
            }

            // docx (OOXML zip package)
            boolean hasContentTypes = false;
            boolean hasWordDocument = false;
            int entries = 0;
            try (ZipInputStream zip = new ZipInputStream(new BufferedInputStream(file.getInputStream()))) {
                ZipEntry entry;
                while ((entry = zip.getNextEntry()) != null && entries++ < 10_000) {
                    String name = entry.getName();
                    if ("[Content_Types].xml".equals(name)) hasContentTypes = true;
                    if ("word/document.xml".equals(name)) hasWordDocument = true;
                    if (hasContentTypes && hasWordDocument) return;
                }
            }
            throw badRequest("文件内容不是有效的 DOCX 文档");
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (IOException exception) {
            throw badRequest("附件读取失败，请重新选择文件");
        }
    }

    private ResponseStatusException badRequest(String message) {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, message);
    }
}
