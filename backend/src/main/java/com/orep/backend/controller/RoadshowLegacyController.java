package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.roadshow.LegacyDeckService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.net.URLEncoder;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/roadshow/legacy")
public class RoadshowLegacyController {

    private final LegacyDeckService service;

    public RoadshowLegacyController(LegacyDeckService service) {
        this.service = service;
    }

    @GetMapping("/mine")
    public Result<List<Map<String, Object>>> mine(HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.mine(userId));
    }

    @GetMapping("/candidates")
    public Result<List<Map<String, Object>>> candidates(HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.candidates(userId));
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> upload(@RequestParam("file") MultipartFile file, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.ingestUpload(userId, file));
    }

    @GetMapping("/{id}/pages")
    public Result<Map<String, Object>> pages(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.pages(id, userId));
    }

    @PostMapping("/{id}/apply")
    public Result<Map<String, Object>> apply(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        int page = body == null || body.get("page") == null ? 0 : asInt(body.get("page"));
        if (page < 1) return Result.error(400, "请选一页");
        String action = body.get("action") == null ? "edit" : String.valueOf(body.get("action"));
        return Result.success(service.applyPage(
                id,
                userId,
                page,
                action,
                body.get("title") == null ? "" : String.valueOf(body.get("title")),
                body.get("number") == null ? "" : String.valueOf(body.get("number")),
                body.get("line") == null ? "" : String.valueOf(body.get("line"))
        ));
    }

    @GetMapping("/{id}/slide/{page}")
    public ResponseEntity<byte[]> slide(
            @PathVariable Long id,
            @PathVariable int page,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        byte[] body = service.previewPage(id, userId, page);
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .header(HttpHeaders.CACHE_CONTROL, "private, max-age=30")
                .body(body);
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<byte[]> download(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        byte[] body = service.downloadWork(id, userId);
        String name = service.downloadName(id, userId);
        String encoded = URLEncoder.encode(name, java.nio.charset.StandardCharsets.UTF_8).replace("+", "%20");
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encoded)
                .contentType(MediaType.parseMediaType(
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"))
                .body(body);
    }

    @PostMapping("/from-document")
    public Result<Map<String, Object>> fromDocument(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long documentId = asLong(body == null ? null : body.get("documentId"));
        if (documentId == null) return Result.error(400, "请选择一份 PPT");
        return Result.success(service.ingestDocument(userId, documentId));
    }

    private static int asInt(Object v) {
        if (v instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(v));
        } catch (NumberFormatException e) {
            return 0;
        }
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
