package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.entity.Resource;
import com.orep.backend.service.ResourceService;
import com.orep.backend.config.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 管理端资源管理（上传/删除/列表）
 */
@RestController
@RequestMapping("/api/admin/ppt")
@RequiredArgsConstructor
public class AdminPptController {

    private static final String PPT_RESOURCE_DIR = "ppt-templates";

    private final ResourceService resourceService;
    private final JwtUtil jwtUtil;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    private Path getPptDir() throws IOException {
        Path dir = Path.of(uploadDir).resolve(PPT_RESOURCE_DIR).toAbsolutePath().normalize();
        Files.createDirectories(dir);
        return dir;
    }

    /** 列出所有资源 */
    @GetMapping
    public Result<?> list() {
        List<Resource> items = resourceService.list();
        List<Map<String, Object>> result = items.stream().map(r -> {
            Map<String, Object> m = new HashMap<>();
            m.put("id", r.getId());
            m.put("name", r.getName());
            m.put("ext", r.getExt());
            m.put("fileSize", r.getFileSize());
            m.put("size", formatSize(r.getFileSize()));
            m.put("category", r.getCategory() == null ? "public" : r.getCategory());
            m.put("filePath", r.getFilePath());
            m.put("uploadedBy", r.getUploadedBy());
            m.put("uploaderName", r.getUploaderName());
            m.put("createdAt", r.getCreatedAt());
            m.put("url", "/api/ppt-template/download/" + URLEncoder.encode(r.getName(), StandardCharsets.UTF_8).replace("+", "%20"));
            return m;
        }).collect(Collectors.toList());
        return Result.success(result);
    }

    /** 上传资源 */
    @PostMapping("/upload")
    public Result<?> upload(@RequestParam("file") MultipartFile file,
                            @RequestHeader("Authorization") String authHeader) throws IOException {
        String originalName = file.getOriginalFilename();
        if (originalName == null || !isAllowedFile(originalName)) {
            return Result.error("仅支持 .pptx .ppt .pdf .doc .docx 文件");
        }
        String safeName = originalName.replaceAll("[^a-zA-Z0-9._\\-\\u4e00-\\u9fff]", "_");
        String ext = getExt(safeName);
        Path dir = getPptDir();
        Path target = dir.resolve(safeName).normalize();
        if (!target.startsWith(dir)) {
            return Result.error("文件名不合法");
        }
        Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);

        // 获取上传人 ID
        Integer userId = null;
        try {
            String token = authHeader.replace("Bearer ", "");
            userId = jwtUtil.getUserId(token).intValue();
        } catch (Exception ignored) {}

        Resource resource = new Resource();
        resource.setName(safeName);
        resource.setFileSize(Files.size(target));
        resource.setExt(ext);
        resource.setFilePath("uploads/ppt-templates/" + safeName);
        resource.setUploadedBy(userId);
        resourceService.add(resource);

        return Result.success(Map.of(
                "id", resource.getId(),
                "name", safeName,
                "size", formatSize(Files.size(target)),
                "ext", ext));
    }

    /** 删除资源 */
    @DeleteMapping("/{id}")
    public Result<?> delete(@PathVariable Integer id) {
        if (!deleteResource(id)) {
            return Result.error("资源不存在");
        }
        return Result.success("已删除");
    }

    @PostMapping("/batch-delete")
    public Result<BatchDeleteResult> batchDelete(@RequestBody BatchDeleteRequest request) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> ids = request.getIds() == null ? List.of() : request.getIds().stream().distinct().toList();
        result.setRequested(ids.size());
        for (Long id : ids) {
            if (id == null || id > Integer.MAX_VALUE || id < Integer.MIN_VALUE) {
                result.addFailure(id, "资源 ID 不合法");
                continue;
            }
            if (deleteResource(id.intValue())) {
                result.addDeleted();
            } else {
                result.addFailure(id, "资源不存在");
            }
        }
        return Result.success(result);
    }

    private boolean deleteResource(Integer id) {
        Resource resource = resourceService.getById(id);
        if (resource == null) {
            return false;
        }
        // 删除文件
        try {
            Path dir = getPptDir();
            Path filePath = dir.resolve(resource.getName()).normalize();
            if (filePath.startsWith(dir)) {
                Files.deleteIfExists(filePath);
            }
        } catch (IOException ignored) {}
        // 删除数据库记录
        resourceService.delete(id);
        return true;
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        return String.format("%.1f MB", bytes / (1024.0 * 1024));
    }

    private boolean isAllowedFile(String filename) {
        return getExt(filename).matches("pptx?|pdf|docx?");
    }

    private String getExt(String filename) {
        int dot = filename.lastIndexOf('.');
        return dot >= 0 ? filename.substring(dot + 1).toLowerCase() : "";
    }
}
