package com.orep.backend.controller;

import com.orep.backend.service.ChatUploadAccessService;
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
public class ChatUploadDownloadController {

    private final ChatUploadAccessService chatUploadAccessService;

    public ChatUploadDownloadController(ChatUploadAccessService chatUploadAccessService) {
        this.chatUploadAccessService = chatUploadAccessService;
    }

    @GetMapping("/uploads/chat/**")
    public ResponseEntity<Resource> chatUploads(HttpServletRequest request) {
        return serve(request);
    }

    @GetMapping("/uploads/{year:\\d{4}}/**")
    public ResponseEntity<Resource> legacyDateUploads(HttpServletRequest request) {
        return serve(request);
    }

    private ResponseEntity<Resource> serve(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String uri = request.getRequestURI().substring(request.getContextPath().length());
        Path file = chatUploadAccessService.authorize(uri, userId);
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
