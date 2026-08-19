package com.orep.backend.controller;

import com.orep.backend.common.Result;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * 文件上传控制器
 */
@RestController
@RequestMapping("/api/upload")
public class FileUploadController {

    @Value("${file.upload-dir}")
    private String uploadDir;

    @PostMapping
    public Result<Map<String, Object>> upload(@RequestParam("file") MultipartFile file,
                                              @RequestParam(value = "category", required = false) String category) throws IOException {
        if (file.isEmpty()) {
            return Result.error("文件为空");
        }

        // 统一上传根目录下按业务分类，再按日期归档。
        String categoryPath = normalizeCategory(category, file.getContentType());
        String datePath = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyy/MM/dd"));
        Path baseDir = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path dir = baseDir.resolve(categoryPath).resolve(datePath).normalize();
        if (!dir.startsWith(baseDir)) {
            return Result.error("上传路径非法");
        }
        Files.createDirectories(dir);

        // 生成唯一文件名
        String originalName = file.getOriginalFilename();
        String ext = "";
        if (originalName != null && originalName.contains(".")) {
            ext = originalName.substring(originalName.lastIndexOf("."));
        }
        String fileName = UUID.randomUUID().toString().replace("-", "") + ext;
        Path target = dir.resolve(fileName).normalize();
        if (!target.startsWith(dir)) {
            return Result.error("文件名非法");
        }
        file.transferTo(target.toFile());

        Map<String, Object> data = new HashMap<>();
        data.put("url", "/uploads/" + categoryPath + "/" + datePath + "/" + fileName);
        data.put("name", originalName);
        data.put("size", file.getSize());
        data.put("type", file.getContentType());
        data.put("category", categoryPath);
        return Result.success(data);
    }

    private String normalizeCategory(String category, String contentType) {
        String raw = category == null ? "" : category.trim().toLowerCase();
        return switch (raw) {
            case "chat-image", "chat-images", "image", "images" -> "chat/images";
            case "chat-file", "chat-files", "file", "files" -> "chat/files";
            case "task-submission", "task-submissions", "submission", "submissions" -> "task/submissions";
            case "daily-report", "daily-reports", "daily_report" -> "daily-report/images";
            case "banner", "banners" -> "banners";
            default -> contentType != null && contentType.startsWith("image/") ? "general/images" : "general/files";
        };
    }
}
