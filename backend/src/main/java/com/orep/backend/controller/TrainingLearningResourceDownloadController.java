package com.orep.backend.controller;

import com.orep.backend.service.TrainingDayLearningResourceService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.MediaTypeFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Locale;
import java.util.Set;

@RestController
public class TrainingLearningResourceDownloadController {
    private static final Set<String> DOWNLOAD_ONLY_EXTENSIONS = Set.of("zip", "rar", "7z");
    private final TrainingDayLearningResourceService learningService;

    public TrainingLearningResourceDownloadController(
            TrainingDayLearningResourceService learningService
    ) {
        this.learningService = learningService;
    }

    @GetMapping("/uploads/training/learning/**")
    public ResponseEntity<Resource> download(HttpServletRequest request) {
        String requestedUrl = request.getRequestURI().substring(request.getContextPath().length());
        Path authorizedFile = learningService.authorizeDownload(
                (Long) request.getAttribute("tenantId"),
                (Long) request.getAttribute("userId"),
                String.valueOf(request.getAttribute("role")),
                requestedUrl
        );
        Resource resource = new FileSystemResource(authorizedFile);
        MediaType mediaType = MediaTypeFactory.getMediaType(authorizedFile.getFileName().toString())
                .orElse(MediaType.APPLICATION_OCTET_STREAM);
        String fileName = authorizedFile.getFileName().toString();
        String extension = extension(fileName);
        ContentDisposition disposition = (DOWNLOAD_ONLY_EXTENSIONS.contains(extension)
                ? ContentDisposition.attachment()
                : ContentDisposition.inline())
                .filename(authorizedFile.getFileName().toString(), StandardCharsets.UTF_8)
                .build();
        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(resource);
    }

    private String extension(String fileName) {
        int index = fileName.lastIndexOf('.');
        return index < 0 ? "" : fileName.substring(index + 1).toLowerCase(Locale.ROOT);
    }
}
