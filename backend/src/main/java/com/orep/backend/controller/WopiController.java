package com.orep.backend.controller;

import com.orep.backend.service.InspireOfficeService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.NoSuchElementException;

/**
 * WOPI Host（供 Collabora Online 拉取/保存文件）。
 * 鉴权：query access_token（WOPI JWT），不走用户 Bearer。
 */
@RestController
@RequestMapping("/api/wopi")
public class WopiController {

    private final InspireOfficeService inspireOfficeService;

    public WopiController(InspireOfficeService inspireOfficeService) {
        this.inspireOfficeService = inspireOfficeService;
    }

    /** CheckFileInfo */
    @GetMapping("/files/{fileId}")
    public ResponseEntity<?> checkFileInfo(
            @PathVariable String fileId,
            @RequestParam("access_token") String accessToken
    ) {
        try {
            Map<String, Object> info = inspireOfficeService.wopiCheckFileInfo(fileId, accessToken);
            return ResponseEntity.ok()
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(info);
        } catch (SecurityException e) {
            return ResponseEntity.status(401).body(Map.of("error", e.getMessage()));
        } catch (NoSuchElementException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 用户头像（与系统侧栏一致的首字圆形图）。
     * Collabora 协同列表通过 CheckFileInfo.UserExtraInfo.avatar 引用；浏览器直接拉图，无需 access_token。
     */
    @GetMapping(value = "/avatars/{userId}", produces = "image/svg+xml")
    public ResponseEntity<String> userAvatar(@PathVariable long userId) {
        try {
            String svg = inspireOfficeService.buildUserAvatarSvg(userId);
            return ResponseEntity.ok()
                    .header(HttpHeaders.CACHE_CONTROL, "public, max-age=3600")
                    .contentType(MediaType.parseMediaType("image/svg+xml"))
                    .body(svg);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    /** GetFile */
    @GetMapping("/files/{fileId}/contents")
    public ResponseEntity<Resource> getFile(
            @PathVariable String fileId,
            @RequestParam("access_token") String accessToken
    ) {
        try {
            Path path = inspireOfficeService.wopiGetFilePath(fileId, accessToken);
            if (!Files.isRegularFile(path)) {
                return ResponseEntity.notFound().build();
            }
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_OCTET_STREAM_VALUE)
                    .contentLength(Files.size(path))
                    .body(new FileSystemResource(path));
        } catch (SecurityException e) {
            return ResponseEntity.status(401).build();
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        } catch (Exception e) {
            return ResponseEntity.internalServerError().build();
        }
    }

    /** PutFile */
    @PostMapping("/files/{fileId}/contents")
    public ResponseEntity<?> putFile(
            @PathVariable String fileId,
            @RequestParam("access_token") String accessToken,
            @RequestBody byte[] body
    ) {
        try {
            inspireOfficeService.wopiPutFile(fileId, accessToken, body == null ? new byte[0] : body);
            return ResponseEntity.ok().build();
        } catch (SecurityException e) {
            return ResponseEntity.status(401).body(Map.of("error", e.getMessage()));
        } catch (NoSuchElementException e) {
            return ResponseEntity.status(404).body(Map.of("error", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }
}
