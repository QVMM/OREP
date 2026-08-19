package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.ResourceCenterService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@RestController
@RequestMapping("/api/resource-center")
public class ResourceCenterController {
    private final ResourceCenterService service;

    public ResourceCenterController(ResourceCenterService service) {
        this.service = service;
    }

    @GetMapping
    public Result<Map<String, Object>> workspace(
            @RequestParam Long teamId,
            HttpServletRequest request
    ) {
        return Result.success(service.workspace(
                teamId, tenantId(request), userId(request), role(request)));
    }

    @PostMapping("/folders")
    public Result<Map<String, Object>> createFolder(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.createFolder(
                longValue(body.get("teamId")),
                tenantId(request),
                userId(request),
                role(request),
                String.valueOf(body.getOrDefault("label", ""))
        ));
    }

    @PatchMapping("/folders/{folderId}")
    public Result<Map<String, Object>> renameFolder(
            @PathVariable Long folderId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.renameFolder(
                folderId,
                longValue(body.get("teamId")),
                tenantId(request),
                userId(request),
                role(request),
                String.valueOf(body.getOrDefault("label", ""))
        ));
    }

    @DeleteMapping("/folders/{folderId}")
    public Result<Void> deleteFolder(
            @PathVariable Long folderId,
            @RequestParam Long teamId,
            HttpServletRequest request
    ) {
        service.deleteFolder(
                folderId, teamId, tenantId(request), userId(request), role(request));
        return Result.success();
    }

    @PostMapping(value = "/files", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> upload(
            @RequestParam Long teamId,
            @RequestParam(required = false) String folderKey,
            @RequestPart("file") MultipartFile file,
            HttpServletRequest request
    ) throws IOException {
        return Result.success(service.upload(
                teamId,
                tenantId(request),
                userId(request),
                role(request),
                folderKey,
                file
        ));
    }

    @PatchMapping("/files/{resourceId}/folder")
    public Result<Map<String, Object>> move(
            @PathVariable Integer resourceId,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(service.moveFile(
                resourceId,
                longValue(body.get("teamId")),
                tenantId(request),
                userId(request),
                role(request),
                body.get("folderKey") == null ? null : String.valueOf(body.get("folderKey"))
        ));
    }

    @DeleteMapping("/files/{resourceId}")
    public Result<Void> deleteFile(
            @PathVariable Integer resourceId,
            @RequestParam Long teamId,
            HttpServletRequest request
    ) {
        service.deleteFile(
                resourceId, teamId, tenantId(request), userId(request), role(request));
        return Result.success();
    }

    @GetMapping("/files/{resourceId}/preview")
    public ResponseEntity<Resource> preview(
            @PathVariable Integer resourceId,
            HttpServletRequest request
    ) throws IOException {
        return fileResponse(resourceId, request, true);
    }

    @GetMapping("/files/{resourceId}/download")
    public ResponseEntity<Resource> download(
            @PathVariable Integer resourceId,
            HttpServletRequest request
    ) throws IOException {
        return fileResponse(resourceId, request, false);
    }

    private ResponseEntity<Resource> fileResponse(
            Integer resourceId,
            HttpServletRequest request,
            boolean inline
    ) throws IOException {
        ResourceCenterService.ResolvedResource resolved = service.resolve(
                resourceId, tenantId(request), userId(request), role(request));
        String encodedName = URLEncoder.encode(
                resolved.metadata().getName(),
                StandardCharsets.UTF_8
        ).replace("+", "%20");
        String disposition = (inline ? "inline" : "attachment")
                + "; filename*=UTF-8''" + encodedName;
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition)
                .contentType(MediaType.parseMediaType(resolved.contentType()))
                .contentLength(resolved.body().contentLength())
                .body(resolved.body());
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }

    private Long longValue(Object value) {
        if (value == null) return null;
        try {
            return Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }
}
