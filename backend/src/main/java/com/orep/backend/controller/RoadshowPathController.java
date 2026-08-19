package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.roadshow.JudgePathService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@RestController
@RequestMapping("/api/roadshow/path")
public class RoadshowPathController {

    private final JudgePathService service;
    private final com.orep.backend.service.roadshow.LegacyDeckService decks;

    public RoadshowPathController(
            JudgePathService service,
            com.orep.backend.service.roadshow.LegacyDeckService decks
    ) {
        this.service = service;
        this.decks = decks;
    }

    @GetMapping("/script/{scriptId}/meter")
    public Result<Map<String, Object>> meter(@PathVariable Long scriptId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.scriptMeter(scriptId, userId));
    }

    @PostMapping("/compile")
    public Result<Map<String, Object>> compile(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long scriptId = asLong(body.get("scriptId"));
        if (scriptId == null) return Result.error(400, "请选择讲稿");
        return Result.success(service.compile(scriptId, userId, tenantId));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> get(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.get(id, userId));
    }

    @PostMapping("/{id}/ack-hole")
    public Result<Map<String, Object>> ack(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.ackHole(id, userId, body == null ? null : String.valueOf(body.get("holeId"))));
    }

    @PostMapping("/{id}/attach-deck")
    public Result<Map<String, Object>> attachDeck(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        Long deckId = asLong(body == null ? null : body.get("deckId"));
        if (deckId == null) return Result.error(400, "请先选一份 PPT");
        return Result.success(service.attachDeck(id, userId, deckId, decks));
    }

    @GetMapping("/{id}/align")
    public Result<Map<String, Object>> align(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.align(id, userId, decks));
    }

    @PostMapping("/{id}/confirm")
    public Result<Map<String, Object>> confirm(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.confirm(id, userId));
    }

    @PostMapping("/{id}/print")
    public Result<Map<String, Object>> print(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.print(id, userId));
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<byte[]> download(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Map<String, Object> path = service.get(id, userId);
        byte[] body = service.download(id, userId);
        String name = service.downloadName(path);
        String encoded = URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20");
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encoded)
                .contentType(MediaType.parseMediaType(
                        "application/vnd.openxmlformats-officedocument.presentationml.presentation"))
                .body(body);
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
