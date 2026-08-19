package com.orep.backend.service.roadshow;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class LegacyDeckService {

    private final JdbcTemplate jdbc;
    private final String uploadDir;
    private final SlidePreviewService previews;

    public LegacyDeckService(
            JdbcTemplate jdbc,
            @Value("${file.upload-dir:./uploads}") String uploadDir,
            SlidePreviewService previews
    ) {
        this.jdbc = jdbc;
        this.uploadDir = uploadDir;
        this.previews = previews;
    }

    public List<Map<String, Object>> mine(Long userId) {
        List<Map<String, Object>> out = new ArrayList<>();
        List<Map<String, Object>> rows = jdbc.queryForList(
                """
                SELECT id, original_name, original_hash, page_count, created_at
                FROM legacy_deck
                WHERE created_by = ?
                ORDER BY id DESC
                LIMIT 20
                """,
                userId
        );
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (Map<String, Object> d : rows) {
            String hash = String.valueOf(d.get("original_hash"));
            if (!seen.add(hash)) continue;
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("kind", "upload");
            row.put("id", asLong(d.get("id")));
            row.put("title", d.get("original_name"));
            row.put("pageCount", d.get("page_count"));
            row.put("createdAt", String.valueOf(d.get("created_at")));
            row.put("usable", true);
            out.add(row);
            if (out.size() >= 8) break;
        }
        return out;
    }

    public List<Map<String, Object>> candidates(Long userId) {
        List<Map<String, Object>> out = new ArrayList<>();
        List<Map<String, Object>> docs = jdbc.queryForList(
                """
                SELECT id, title, ext, size_bytes, storage_path, updated_at
                FROM inspire_office_document
                WHERE owner_user_id = ? AND status = 'active'
                  AND LOWER(ext) IN ('pptx', 'ppt')
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                userId
        );
        for (Map<String, Object> d : docs) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("kind", "office");
            row.put("documentId", asLong(d.get("id")));
            row.put("title", d.get("title"));
            row.put("ext", d.get("ext"));
            row.put("sizeBytes", d.get("size_bytes"));
            row.put("updatedAt", String.valueOf(d.get("updated_at")));
            row.put("usable", "pptx".equalsIgnoreCase(String.valueOf(d.get("ext"))));
            out.add(row);
        }
        return out;
    }

    public Map<String, Object> ingestUpload(Long userId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请先选一份 PPT");
        }
        if (file.getSize() > LegacyDeckInspector.MAX_BYTES) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "太大了，先删附录再传，或拆开。");
        }
        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件打不开。");
        }
        return persist(userId, "upload", null, file.getOriginalFilename(), bytes);
    }

    public Map<String, Object> ingestDocument(Long userId, Long documentId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                """
                SELECT id, title, ext, storage_path, owner_user_id
                FROM inspire_office_document
                WHERE id = ? AND status = 'active'
                """,
                documentId
        );
        if (rows.isEmpty() || !userId.equals(asLong(rows.get(0).get("owner_user_id")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "找不到这份 PPT");
        }
        Map<String, Object> doc = rows.get(0);
        Path src = officePath(String.valueOf(doc.get("storage_path")));
        if (!Files.isRegularFile(src)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件打不开。");
        }
        byte[] bytes;
        try {
            bytes = Files.readAllBytes(src);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件打不开。");
        }
        String name = String.valueOf(doc.get("title"));
        if (!name.toLowerCase().endsWith(".pptx") && !name.toLowerCase().endsWith(".ppt")) {
            name = name + "." + doc.get("ext");
        }
        return persist(userId, "office", documentId, name, bytes);
    }

    private Map<String, Object> persist(Long userId, String source, Long documentId, String name, byte[] bytes) {
        LegacyDeckInspector.Result inspect = LegacyDeckInspector.inspect(bytes, name);
        if (!inspect.ok()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, inspect.message());
        }
        String day = LocalDate.now().toString().replace("-", "/");
        Path dir = Paths.get(uploadDir).toAbsolutePath().normalize().resolve("roadshow/legacy").resolve(day);
        try {
            Files.createDirectories(dir);
            Path original = dir.resolve(inspect.hash() + "-original.pptx");
            Path work = dir.resolve(inspect.hash() + "-work.pptx");
            Files.write(original, bytes);
            Files.copy(original, work, StandardCopyOption.REPLACE_EXISTING);
            jdbc.update(
                    """
                    INSERT INTO legacy_deck
                      (created_by, source_type, source_document_id, original_name, original_hash,
                       original_path, work_path, page_count, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'received')
                    """,
                    userId,
                    source,
                    documentId,
                    name == null ? "路演.pptx" : name,
                    inspect.hash(),
                    original.toString(),
                    work.toString(),
                    inspect.pageCount()
            );
            Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
            Map<String, Object> view = new LinkedHashMap<>();
            view.put("id", id);
            view.put("title", name);
            view.put("pageCount", inspect.pageCount());
            view.put("hash", inspect.hash());
            view.put("status", "received");
            view.put("source", source);
            return view;
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "收下这份 PPT 失败");
        }
    }

    public Map<String, Object> pages(Long id, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, created_by, original_name, original_hash, page_count, status, work_path FROM legacy_deck WHERE id = ?",
                id
        );
        if (rows.isEmpty() || !userId.equals(asLong(rows.get(0).get("created_by")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "找不到这份 PPT");
        }
        Map<String, Object> row = rows.get(0);
        List<String> xml = readSlideXml(Path.of(String.valueOf(row.get("work_path"))));
        List<Map<String, Object>> pages = LegacySlideReader.grade(xml);
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", asLong(row.get("id")));
        view.put("title", row.get("original_name"));
        view.put("pageCount", pages.size());
        view.put("hash", row.get("original_hash"));
        view.put("status", row.get("status"));
        view.put("pages", pages);
        view.put("editable", pages.stream().filter(p -> "editable".equals(p.get("grade"))).count());
        view.put("picture", pages.stream().filter(p -> "picture".equals(p.get("grade"))).count());
        view.put("empty", pages.stream().filter(p -> "empty".equals(p.get("grade"))).count());
        view.put("partial", pages.stream().filter(p -> "partial".equals(p.get("grade"))).count());
        return view;
    }

    public void resetWork(Long id, Long userId) {
        Map<String, Object> row = requireRow(id, userId);
        Object rawOriginal = row.get("original_path");
        if (rawOriginal == null || String.valueOf(rawOriginal).isBlank()) return;
        Path original = Path.of(String.valueOf(rawOriginal));
        Path work = Path.of(String.valueOf(row.get("work_path")));
        if (!Files.isRegularFile(original) || work == null) return;
        try {
            Files.copy(original, work, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "还原这份 PPT 失败");
        }
    }

    public Map<String, Object> applyPage(Long id, Long userId, int pageNo, String action, String title, String number, String line) {
        if ("drop".equals(action) || "add".equals(action) || "replace".equals(action)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "这份页数不动，也不整页换掉。");
        }
        if (unsafeClaim(title) || unsafeClaim(line)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "这段不像页上的标题，改上去会把设计改坏。");
        }
        Map<String, Object> row = requireRow(id, userId);
        Path work = Path.of(String.valueOf(row.get("work_path")));
        if (!Files.isRegularFile(work)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "找不到可改的副本");
        }
        String name = "ppt/slides/slide" + pageNo + ".xml";
        String xml = readZipEntry(work, name);
        if (xml.isBlank()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "没有这一页");
        }
        String next;
        if ("drop".equals(action)) {
            next = RoadshowPptxWriter.slideXml(Map.of("kicker", "本次不讲", "title", "这页台上不翻", "number", "", "line", "原件里还在"));
        } else if ("replace".equals(action) || "add".equals(action)) {
            next = RoadshowPptxWriter.slideXml(Map.of(
                    "kicker", "按讲稿",
                    "title", title == null || title.isBlank() ? "这一页" : title,
                    "number", number == null ? "" : number,
                    "line", line == null ? "" : line
            ));
        } else {
            List<String> from = pageLines(xml);
            List<String> to = new ArrayList<>();
            if (title != null && !title.isBlank()) to.add(title);
            if (number != null && !number.isBlank()) to.add(number);
            if (line != null && !line.isBlank()) to.add(line);
            while (to.size() < from.size()) to.add(from.get(to.size()));
            next = SlideTextPatcher.patch(xml, from, to);
        }
        rewriteZipEntry(work, name, next);
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", id);
        view.put("page", pageNo);
        view.put("action", action);
        view.put("ok", true);
        return view;
    }

    public byte[] previewPage(Long id, Long userId, int page) {
        Map<String, Object> row = requireRow(id, userId);
        Path work = Path.of(String.valueOf(row.get("work_path")));
        if (!Files.isRegularFile(work)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "找不到这份 PPT");
        }
        try {
            return previews.png(work, page);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "这一页现在画不出来");
        }
    }

    public byte[] downloadWork(Long id, Long userId) {
        Map<String, Object> row = requireRow(id, userId);
        Path work = Path.of(String.valueOf(row.get("work_path")));
        if (!Files.isRegularFile(work)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "还没有可下载的文件");
        }
        try {
            return Files.readAllBytes(work);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "下载失败");
        }
    }

    public String downloadName(Long id, Long userId) {
        Map<String, Object> row = requireRow(id, userId);
        String title = String.valueOf(row.getOrDefault("original_name", "路演.pptx"));
        if (!title.toLowerCase().endsWith(".pptx")) title = title + ".pptx";
        return title.replace(".pptx", " · 改过.pptx");
    }

    static boolean unsafeClaim(String raw) {
        if (raw == null || raw.isBlank()) return false;
        String t = raw.trim();
        if (t.contains("nitrogen") || t.contains("raw_data") || t.contains("ustruct") || t.contains("&quot;")) {
            return true;
        }
        return t.contains("：") && t.length() > 22;
    }

    private Map<String, Object> requireRow(Long id, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, created_by, original_name, original_hash, page_count, status, original_path, work_path FROM legacy_deck WHERE id = ?",
                id
        );
        if (rows.isEmpty() || !userId.equals(asLong(rows.get(0).get("created_by")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "找不到这份 PPT");
        }
        return rows.get(0);
    }

    private static List<String> pageLines(String xml) {
        Map<String, Object> graded = LegacySlideReader.grade(List.of(xml)).get(0);
        Object raw = graded.get("lines");
        if (raw instanceof List<?> list) {
            List<String> out = new ArrayList<>();
            for (Object o : list) out.add(String.valueOf(o));
            return out;
        }
        return List.of();
    }

    private static String readZipEntry(Path zip, String name) {
        try (java.util.zip.ZipInputStream in = new java.util.zip.ZipInputStream(Files.newInputStream(zip))) {
            java.util.zip.ZipEntry e;
            while ((e = in.getNextEntry()) != null) {
                if (name.equals(e.getName())) {
                    return new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
                }
            }
        } catch (IOException e) {
            return "";
        }
        return "";
    }

    private static void rewriteZipEntry(Path zip, String name, String xml) {
        Path tmp = zip.resolveSibling(zip.getFileName() + ".tmp");
        try (java.util.zip.ZipInputStream in = new java.util.zip.ZipInputStream(Files.newInputStream(zip));
             java.util.zip.ZipOutputStream out = new java.util.zip.ZipOutputStream(Files.newOutputStream(tmp))) {
            java.util.zip.ZipEntry e;
            boolean written = false;
            while ((e = in.getNextEntry()) != null) {
                byte[] data = name.equals(e.getName())
                        ? xml.getBytes(java.nio.charset.StandardCharsets.UTF_8)
                        : in.readAllBytes();
                if (name.equals(e.getName())) written = true;
                java.util.zip.ZipEntry next = new java.util.zip.ZipEntry(e.getName());
                out.putNextEntry(next);
                out.write(data);
                out.closeEntry();
            }
            if (!written) {
                out.putNextEntry(new java.util.zip.ZipEntry(name));
                out.write(xml.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                out.closeEntry();
            }
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "改这一页失败");
        }
        try {
            Files.move(tmp, zip, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "保存改动失败");
        }
    }

    public Map<String, Object> get(Long id, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, created_by, original_name, original_hash, page_count, status FROM legacy_deck WHERE id = ?",
                id
        );
        if (rows.isEmpty() || !userId.equals(asLong(rows.get(0).get("created_by")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "找不到这份 PPT");
        }
        Map<String, Object> row = rows.get(0);
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("id", asLong(row.get("id")));
        view.put("title", row.get("original_name"));
        view.put("pageCount", row.get("page_count"));
        view.put("hash", row.get("original_hash"));
        view.put("status", row.get("status"));
        return view;
    }

    private static List<String> readSlideXml(Path pptx) {
        List<String> slides = new ArrayList<>();
        if (pptx == null || !Files.isRegularFile(pptx)) return slides;
        try (java.util.zip.ZipInputStream in = new java.util.zip.ZipInputStream(Files.newInputStream(pptx))) {
            java.util.zip.ZipEntry e;
            Map<Integer, String> byIndex = new java.util.TreeMap<>();
            while ((e = in.getNextEntry()) != null) {
                String name = e.getName();
                if (!name.matches("ppt/slides/slide\\d+\\.xml")) continue;
                int n = Integer.parseInt(name.replaceAll("\\D+", ""));
                byIndex.put(n, new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8));
            }
            slides.addAll(byIndex.values());
        } catch (IOException ignored) {
            return List.of();
        }
        return slides;
    }

    private Path officePath(String relative) {
        Path base = Paths.get(uploadDir).toAbsolutePath().normalize().resolve("office");
        Path target = base.resolve(relative == null ? "" : relative).normalize();
        if (!target.startsWith(base)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "文件打不开。");
        }
        return target;
    }

    private static Long asLong(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
