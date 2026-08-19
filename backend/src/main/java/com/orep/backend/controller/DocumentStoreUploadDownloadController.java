package com.orep.backend.controller;

import com.orep.backend.service.DocumentStoreUploadAccessService;
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
public class DocumentStoreUploadDownloadController {

    private final DocumentStoreUploadAccessService accessService;

    public DocumentStoreUploadDownloadController(DocumentStoreUploadAccessService accessService) {
        this.accessService = accessService;
    }

    @GetMapping("/uploads/resource-center/**")
    public ResponseEntity<Resource> resourceCenter(HttpServletRequest request) {
        Long userId = request.getAttribute("userId") instanceof Number n ? n.longValue() : null;
        Long tenantId = request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null;
        Object roleAttr = request.getAttribute("role");
        String role = roleAttr == null ? null : String.valueOf(roleAttr);
        String uri = request.getRequestURI().substring(request.getContextPath().length());
        return file(accessService.authorizeResourceCenter(uri, tenantId, userId, role));
    }

    @GetMapping("/uploads/office/versions/**")
    public ResponseEntity<Resource> officeVersions(HttpServletRequest request) {
        Long userId = request.getAttribute("userId") instanceof Number n ? n.longValue() : null;
        String uri = request.getRequestURI().substring(request.getContextPath().length());
        return file(accessService.authorizeOfficeVersion(uri, userId));
    }

    private ResponseEntity<Resource> file(Path path) {
        Resource resource = new FileSystemResource(path);
        MediaType mediaType = MediaTypeFactory.getMediaType(path.getFileName().toString())
                .orElse(MediaType.APPLICATION_OCTET_STREAM);
        ContentDisposition disposition = ContentDisposition.inline()
                .filename(path.getFileName().toString(), StandardCharsets.UTF_8)
                .build();
        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(HttpHeaders.CACHE_CONTROL, "private, max-age=3600")
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(resource);
    }
}
