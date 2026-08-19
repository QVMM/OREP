package com.orep.backend.controller;

import com.orep.backend.service.AssistantUploadAccessService;
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

@RestController
public class AssistantUploadDownloadController {

    private final AssistantUploadAccessService assistantUploadAccessService;

    public AssistantUploadDownloadController(AssistantUploadAccessService assistantUploadAccessService) {
        this.assistantUploadAccessService = assistantUploadAccessService;
    }

    @GetMapping("/uploads/assistant/**")
    public ResponseEntity<Resource> download(HttpServletRequest request) {
        Long userId = request.getAttribute("userId") instanceof Number n ? n.longValue() : null;
        Long tenantId = request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null;
        String uri = request.getRequestURI().substring(request.getContextPath().length());
        Path file = assistantUploadAccessService.authorize(uri, tenantId, userId);
        Resource resource = new FileSystemResource(file);
        MediaType mediaType = MediaTypeFactory.getMediaType(file.getFileName().toString())
                .orElse(MediaType.APPLICATION_OCTET_STREAM);
        ContentDisposition disposition = ContentDisposition.inline()
                .filename(file.getFileName().toString(), StandardCharsets.UTF_8)
                .build();
        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(HttpHeaders.CACHE_CONTROL, "private, max-age=3600")
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(resource);
    }
}
