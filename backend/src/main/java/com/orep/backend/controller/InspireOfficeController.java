package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.InspireOfficeDocument;
import com.orep.backend.service.InspireOfficeService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.NoSuchElementException;

@RestController
@RequestMapping("/api/inspire-office")
public class InspireOfficeController {

    private final InspireOfficeService inspireOfficeService;
    private final com.orep.backend.service.SdocCollabService sdocCollabService;

    public InspireOfficeController(
            InspireOfficeService inspireOfficeService,
            com.orep.backend.service.SdocCollabService sdocCollabService
    ) {
        this.inspireOfficeService = inspireOfficeService;
        this.sdocCollabService = sdocCollabService;
    }

    @GetMapping("/status")
    public Result<Map<String, Object>> status() {
        return Result.success(inspireOfficeService.status());
    }

    @GetMapping("/documents")
    public Result<List<Map<String, Object>>> list(
            @RequestParam(value = "scope", required = false) String scope,
            @RequestParam(value = "teamId", required = false) Long teamId,
            @RequestParam(value = "q", required = false) String q,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.listDocuments(userId, scope, teamId, q));
        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName();
            return Result.error(500, "加载文档列表失败: " + msg);
        }
    }

    @GetMapping("/sdoc/{id}")
    public Result<Map<String, Object>> getSmartDoc(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.getSmartDoc(id, userId));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PutMapping("/sdoc/{id}")
    public Result<Map<String, Object>> saveSmartDoc(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Object content = body == null ? null : body.get("content");
            String json = content instanceof String s ? s : (content == null ? null : String.valueOf(content));
            // 若前端传的是对象，转回 JSON 字符串
            if (content instanceof Map || content instanceof List) {
                json = new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(content);
            }
            String updatedAt = body != null && body.get("updatedAt") != null
                    ? String.valueOf(body.get("updatedAt")) : null;
            return Result.success(inspireOfficeService.saveSmartDoc(id, userId, json, updatedAt));
        } catch (IllegalStateException e) {
            return Result.error(409, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "保存智能文档失败: " + e.getMessage());
        }
    }

    @GetMapping("/documents/{id}")
    public Result<Map<String, Object>> get(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.getDocumentView(id, userId));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    /**
     * 在线/编辑时长心跳：学生打开启发 Office 编辑器后由前端周期上报。
     * 写入 student_learning_session，计入总学习时长；教师端可按文档查看在线/编辑时长。
     */
    @PostMapping("/documents/{id}/presence")
    public Result<Map<String, Object>> presence(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            Map<String, Object> b = body != null ? body : Map.of();
            return Result.success(inspireOfficeService.recordPresence(
                    tenantId,
                    userId,
                    id,
                    String.valueOf(b.getOrDefault("sessionId", "")),
                    bool(b.get("visible"), true),
                    bool(b.get("active"), true),
                    bool(b.get("editing"), false),
                    bool(b.get("reset"), false)
            ));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "上报学习时长失败: " + e.getMessage());
        }
    }

    @PostMapping("/sdoc/{id}/collab/join")
    public Result<Map<String, Object>> collabJoin(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            String sessionId = String.valueOf((body == null ? Map.of() : body).getOrDefault("sessionId", ""));
            return Result.success(sdocCollabService.join(id, userId, sessionId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    @PostMapping("/sdoc/{id}/collab/state")
    public Result<Map<String, Object>> collabState(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Map<String, Object> b = body != null ? body : Map.of();
            return Result.success(sdocCollabService.heartbeat(
                    id,
                    userId,
                    String.valueOf(b.getOrDefault("sessionId", "")),
                    intVal(b.get("from")),
                    intVal(b.get("to")),
                    intVal(b.get("block"), -1),
                    intVal(b.get("offset")),
                    intVal(b.get("endOffset")),
                    b.get("preview") == null ? "" : String.valueOf(b.get("preview")),
                    bool(b.get("inProtect"), false),
                    bool(b.get("editing"), false)
            ));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    @GetMapping("/sdoc/{id}/collab/snapshot")
    public Result<Map<String, Object>> collabSnapshot(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(sdocCollabService.snapshotContent(id, userId));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PostMapping("/sdoc/{id}/collab/sync")
    @SuppressWarnings("unchecked")
    public Result<Map<String, Object>> collabSync(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Map<String, Object> b = body != null ? body : Map.of();
            List<Map<String, Object>> changes = null;
            if (b.get("changes") instanceof List<?> list) {
                changes = new java.util.ArrayList<>();
                for (Object item : list) {
                    if (item instanceof Map<?, ?> map) {
                        changes.add((Map<String, Object>) map);
                    }
                }
            }
            Integer blockCount = b.get("blockCount") instanceof Number n ? n.intValue() : null;
            List<Object> snapshot = b.get("snapshot") instanceof List<?> list ? new java.util.ArrayList<>(list) : null;
            return Result.success(sdocCollabService.syncContent(
                    id,
                    userId,
                    String.valueOf(b.getOrDefault("sessionId", "")),
                    changes,
                    blockCount,
                    snapshot
            ));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(409, e.getMessage());
        }
    }

    @PostMapping("/sdoc/{id}/collab/leave")
    public Result<Map<String, Object>> collabLeave(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            String sessionId = String.valueOf((body == null ? Map.of() : body).getOrDefault("sessionId", ""));
            return Result.success(sdocCollabService.leave(id, userId, sessionId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    @GetMapping("/sdoc/{id}/collab/peers")
    public Result<Map<String, Object>> collabPeers(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(sdocCollabService.peers(id, userId));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    private static int intVal(Object value) {
        return intVal(value, 0);
    }

    private static int intVal(Object value, int defaultValue) {
        if (value instanceof Number n) return n.intValue();
        if (value == null) return defaultValue;
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private static boolean bool(Object value, boolean defaultValue) {
        if (value == null) return defaultValue;
        if (value instanceof Boolean b) return b;
        String s = String.valueOf(value).trim();
        if (s.isEmpty()) return defaultValue;
        return "1".equals(s) || "true".equalsIgnoreCase(s) || "yes".equalsIgnoreCase(s);
    }

    @PostMapping("/documents/blank")
    public Result<Map<String, Object>> createBlank(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            String role = roleOf(req);
            String title = body.get("title") != null ? body.get("title").toString() : null;
            String ext = body.get("ext") != null ? body.get("ext").toString() : "docx";
            String scope = body.get("scope") != null ? body.get("scope").toString() : "personal";
            Long teamId = body.get("teamId") != null && !body.get("teamId").toString().isBlank()
                    ? Long.valueOf(body.get("teamId").toString()) : null;
            return Result.success(inspireOfficeService.createBlank(userId, tenantId, role, title, ext, scope, teamId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "新建文档失败: " + e.getMessage());
        }
    }

    @PostMapping(value = "/documents", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> upload(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "scope", required = false, defaultValue = "personal") String scope,
            @RequestParam(value = "teamId", required = false) Long teamId,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            String role = roleOf(req);
            return Result.success(inspireOfficeService.upload(userId, tenantId, role, file, title, scope, teamId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "上传失败: " + e.getMessage());
        }
    }

    private static String roleOf(HttpServletRequest req) {
        Object role = req.getAttribute("role");
        return role == null ? "" : String.valueOf(role);
    }

    @PutMapping("/documents/{id}")
    public Result<Map<String, Object>> rename(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            String title = body.get("title") != null ? body.get("title").toString() : null;
            return Result.success(inspireOfficeService.rename(id, userId, title));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    /** 迁移归属：个人 / 项目 / 团队 */
    @PatchMapping("/documents/{id}/location")
    public Result<Map<String, Object>> moveLocation(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            String role = roleOf(req);
            String scope = body.get("scope") != null ? body.get("scope").toString() : "personal";
            Long teamId = body.get("teamId") != null && !body.get("teamId").toString().isBlank()
                    ? Long.valueOf(body.get("teamId").toString()) : null;
            boolean syncResource = body.get("syncResource") == null
                    || Boolean.parseBoolean(String.valueOf(body.get("syncResource")));
            return Result.success(inspireOfficeService.moveLocation(
                    id, userId, tenantId, role, scope, teamId, syncResource));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "迁移失败: " + e.getMessage());
        }
    }

    /** 手动同步当前内容到资源中心（项目/团队） */
    @PostMapping("/documents/{id}/sync-resource")
    public Result<Map<String, Object>> syncResource(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            String role = roleOf(req);
            return Result.success(inspireOfficeService.syncToResourceCenter(id, userId, tenantId, role));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "同步资源中心失败: " + e.getMessage());
        }
    }

    /** 复制文档 */
    @PostMapping("/documents/{id}/duplicate")
    public Result<Map<String, Object>> duplicate(
            @PathVariable Long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            Long tenantId = (Long) req.getAttribute("tenantId");
            String role = roleOf(req);
            Map<String, Object> b = body != null ? body : Map.of();
            String title = b.get("title") != null ? b.get("title").toString() : null;
            String scope = b.get("scope") != null ? b.get("scope").toString() : "personal";
            Long teamId = b.get("teamId") != null && !b.get("teamId").toString().isBlank()
                    ? Long.valueOf(b.get("teamId").toString()) : null;
            return Result.success(inspireOfficeService.duplicate(
                    id, userId, tenantId, role, title, scope, teamId));
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "复制失败: " + e.getMessage());
        }
    }

    /** 下载当前文件 */
    @GetMapping("/documents/{id}/download")
    public ResponseEntity<Resource> download(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            InspireOfficeService.DownloadFile file = inspireOfficeService.prepareDownload(id, userId);
            InspireOfficeDocument doc = file.document();
            String baseName = doc.getTitle() != null ? doc.getTitle().trim() : "document";
            String ext = doc.getExt() != null ? doc.getExt() : "bin";
            if (!baseName.toLowerCase().endsWith("." + ext.toLowerCase())) {
                baseName = baseName + "." + ext;
            }
            String encoded = URLEncoder.encode(baseName, StandardCharsets.UTF_8).replace("+", "%20");
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + encoded)
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .body(new FileSystemResource(file.path()));
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        } catch (SecurityException e) {
            return ResponseEntity.status(403).build();
        }
    }

    @DeleteMapping("/documents/{id}")
    public Result<Void> delete(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            inspireOfficeService.softDelete(id, userId);
            return Result.success(null);
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        }
    }

    /** 获取 Collabora 编辑会话（editorUrl + access_token 已嵌入）。 */
    @GetMapping("/documents/{id}/editor-session")
    public Result<Map<String, Object>> editorSession(
            @PathVariable Long id,
            @RequestParam(value = "mode", required = false, defaultValue = "edit") String mode,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.buildEditorSession(id, userId, mode));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (IllegalStateException e) {
            return Result.error(503, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "打开编辑器失败: " + e.getMessage());
        }
    }

    @GetMapping("/documents/{id}/versions")
    public Result<List<Map<String, Object>>> versions(@PathVariable Long id, HttpServletRequest req) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.listVersions(id, userId));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "加载版本失败: " + e.getMessage());
        }
    }

    @PostMapping("/documents/{id}/versions")
    public Result<Map<String, Object>> manualSnapshot(
            @PathVariable Long id,
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            String label = body != null && body.get("label") != null ? body.get("label").toString() : null;
            return Result.success(inspireOfficeService.createManualSnapshot(id, userId, label));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "存档失败: " + e.getMessage());
        }
    }

    @PostMapping("/documents/{id}/versions/{versionNo}/restore")
    public Result<Map<String, Object>> restore(
            @PathVariable Long id,
            @PathVariable int versionNo,
            HttpServletRequest req
    ) {
        try {
            Long userId = (Long) req.getAttribute("userId");
            return Result.success(inspireOfficeService.restoreVersion(id, userId, versionNo));
        } catch (NoSuchElementException e) {
            return Result.error(404, e.getMessage());
        } catch (SecurityException e) {
            return Result.error(403, e.getMessage());
        } catch (Exception e) {
            return Result.error(500, "恢复失败: " + e.getMessage());
        }
    }

}
