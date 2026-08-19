package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.config.JwtUtil;
import com.orep.backend.entity.Resource;
import com.orep.backend.service.ResourceService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/ppt-template")
@RequiredArgsConstructor
public class PptTemplateController {

    private static final String PPT_DIR = "static/ppt-templates";
    private static final String UPLOAD_PPT_DIR = "ppt-templates";

    private final ResourceService resourceService;
    private final JwtUtil jwtUtil;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    /** 列出所有资源 */
    @GetMapping
    public Result<?> list() {
        List<com.orep.backend.entity.Resource> items = resourceService.list();
        List<Map<String, Object>> result = items.stream().map(r -> {
            Map<String, Object> m = new HashMap<>();
            m.put("id", r.getId());
            m.put("name", r.getName());
            m.put("ext", r.getExt());
            m.put("fileSize", r.getFileSize());
            m.put("category", r.getCategory() == null ? "public" : r.getCategory());
            m.put("createdAt", r.getCreatedAt());
            m.put("size", formatSize(r.getFileSize()));
            m.put("url", "/api/ppt-template/download/" + URLEncoder.encode(r.getName(), StandardCharsets.UTF_8).replace("+", "%20"));
            m.put("fileUrl", "/api/ppt-template/preview/" + URLEncoder.encode(r.getName(), StandardCharsets.UTF_8).replace("+", "%20"));
            return m;
        }).collect(Collectors.toList());
        return Result.success(result);
    }

    @GetMapping("/categories")
    public Result<?> categories() {
        return Result.success(resourceService.listCategories());
    }

    @PostMapping("/categories")
    public Result<?> createCategory(@RequestBody Map<String, Object> payload,
                                    @RequestHeader(value = "Authorization", required = false) String authHeader) {
        try {
            return Result.success(resourceService.createCategory(String.valueOf(payload.getOrDefault("label", "")), getUserId(authHeader)));
        } catch (IllegalArgumentException e) {
            return Result.error(e.getMessage());
        }
    }

    @PostMapping("/upload")
    public Result<?> upload(@RequestParam("file") MultipartFile file,
                            @RequestParam(value = "category", required = false, defaultValue = "public") String category,
                            @RequestHeader(value = "Authorization", required = false) String authHeader) throws IOException {
        String originalName = file.getOriginalFilename();
        if (originalName == null || !isAllowedFile(originalName)) {
            return Result.error("仅支持 .pptx .ppt .pdf .doc .docx .xls .xlsx 文件");
        }
        String safeName = originalName.replaceAll("[^a-zA-Z0-9._\\-\\u4e00-\\u9fff]", "_");
        String ext = getExt(safeName);
        Path dir = getPptDir();
        Path target = dir.resolve(safeName).normalize();
        if (!target.startsWith(dir)) {
            return Result.error("文件名不合法");
        }
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

        Resource resource = new Resource();
        resource.setName(safeName);
        resource.setFileSize(Files.size(target));
        resource.setExt(ext);
        resource.setFilePath("uploads/ppt-templates/" + safeName);
        resource.setCategory(normalizeCategory(category));
        resource.setUploadedBy(getUserId(authHeader));
        resourceService.add(resource);

        Map<String, Object> result = new HashMap<>();
        result.put("id", resource.getId());
        result.put("name", safeName);
        result.put("size", formatSize(Files.size(target)));
        result.put("ext", ext);
        result.put("category", resource.getCategory());
        result.put("url", "/api/ppt-template/download/" + URLEncoder.encode(safeName, StandardCharsets.UTF_8).replace("+", "%20"));
        result.put("fileUrl", "/api/ppt-template/preview/" + URLEncoder.encode(safeName, StandardCharsets.UTF_8).replace("+", "%20"));
        return Result.success(result);
    }

    /** 下载资源文件 */
    @GetMapping("/download/{filename:.+}")
    public ResponseEntity<byte[]> download(@PathVariable String filename) throws IOException {
        if (filename.contains("..") || filename.contains("/")) {
            return ResponseEntity.badRequest().build();
        }

        byte[] content;
        Path uploadBase = Path.of(uploadDir).resolve(UPLOAD_PPT_DIR).toAbsolutePath().normalize();
        Path uploadedFile = uploadBase.resolve(filename).normalize();
        if (uploadedFile.startsWith(uploadBase) && Files.exists(uploadedFile)) {
            content = Files.readAllBytes(uploadedFile);
        } else {
            org.springframework.core.io.Resource resource = new ClassPathResource(PPT_DIR + "/" + filename);
            if (!resource.exists()) {
                return ResponseEntity.notFound().build();
            }
            content = resource.getInputStream().readAllBytes();
        }
        String encodedName = URLEncoder.encode(filename, StandardCharsets.UTF_8).replace("+", "%20");

        // 根据扩展名选择 content-type
        String contentType = detectContentType(filename);

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encodedName)
                .contentType(MediaType.parseMediaType(contentType))
                .body(content);
    }

    /** 预览 */
    @GetMapping("/preview/{filename:.+}")
    public ResponseEntity<byte[]> preview(@PathVariable String filename) throws IOException {
        return download(filename);
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        return String.format("%.1f MB", bytes / (1024.0 * 1024));
    }

    private Path getPptDir() throws IOException {
        Path dir = Path.of(uploadDir).resolve(UPLOAD_PPT_DIR).toAbsolutePath().normalize();
        Files.createDirectories(dir);
        return dir;
    }

    private Integer getUserId(String authHeader) {
        if (authHeader == null || authHeader.isBlank()) return null;
        try {
            String token = authHeader.replace("Bearer ", "");
            return jwtUtil.getUserId(token).intValue();
        } catch (Exception ignored) {
            return null;
        }
    }

    private String normalizeCategory(String category) {
        String value = category == null ? "" : category.trim();
        if (!value.matches("[a-zA-Z0-9_\\-]{1,64}")) return "public";
        return value;
    }

    private boolean isAllowedFile(String filename) {
        return getExt(filename).matches("pptx?|pdf|docx?|xlsx?");
    }

    private String getExt(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "";
    }

    private String detectContentType(String filename) {
        String ext = filename.substring(filename.lastIndexOf('.') + 1).toLowerCase();
        return switch (ext) {
            case "pdf" -> "application/pdf";
            case "docx" -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "doc" -> "application/msword";
            case "pptx" -> "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            case "ppt" -> "application/vnd.ms-powerpoint";
            case "xlsx" -> "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "xls" -> "application/vnd.ms-excel";
            default -> "application/octet-stream";
        };
    }
}
