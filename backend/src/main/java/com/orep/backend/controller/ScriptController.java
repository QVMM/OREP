package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.Script;
import com.orep.backend.service.PptScriptSyncService;
import com.orep.backend.service.ScriptScoreReviseService;
import com.orep.backend.service.ScriptService;
import com.orep.backend.service.PdfService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/script")
public class ScriptController {

    @Autowired
    private ScriptService scriptService;

    @Autowired
    private PptScriptSyncService pptScriptSyncService;

    @Autowired
    private PdfService pdfService;

    @Autowired
    private ScriptScoreReviseService scriptScoreReviseService;

    /** 根据ID获取讲稿 */
    @GetMapping("/{id}")
    public Result<Script> getById(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Script script = scriptService.getById(id, userId);
        if (script == null) return Result.error(404, "讲稿不存在或无权访问");
        return Result.success(script);
    }

    /** 根据 PPT 任务获取当前用户自己的讲稿 */
    @GetMapping("/from-ppt/{pptJobId}")
    public Result<Script> getByPptJobId(@PathVariable String pptJobId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Script script = scriptService.getByPptJobId(pptJobId, userId);
        if (script == null) return Result.error(404, "讲稿不存在或无权访问");
        return Result.success(script);
    }

    /** 创建或更新讲稿 */
    @PostMapping
    public Result<Script> save(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String title = body.getOrDefault("title", "路演讲稿").toString();
        String content = body.get("content") != null ? body.get("content").toString() : null;
        String roles = body.get("roles") != null ? body.get("roles").toString() : null;
        String sourceType = body.get("sourceType") != null ? body.get("sourceType").toString() : "manual";
        String pptJobId = body.get("pptJobId") != null ? body.get("pptJobId").toString() : null;

        Script script = scriptService.saveScript(title, content, roles, userId, sourceType, pptJobId);
        pptScriptSyncService.syncScriptToPages(script.getId(), userId);
        return Result.success(script);
    }

    /** 自动保存（更新内容） */
    @PutMapping("/{id}")
    public Result<Script> update(@PathVariable Long id, @RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String title = body.get("title") != null ? body.get("title").toString() : null;
        String content = body.get("content") != null ? body.get("content").toString() : null;
        String roles = body.get("roles") != null ? body.get("roles").toString() : null;

        Script script = scriptService.updateContent(id, title, content, roles, userId);
        if (script == null) return Result.error(404, "讲稿不存在或无权访问");
        pptScriptSyncService.syncScriptToPages(script.getId(), userId);
        return Result.success(script);
    }

    /** 打开或创建讲稿绑定的智能文档改稿工作台 */
    @PostMapping("/{id}/workbench-sdoc")
    public Result<Map<String, Object>> openWorkbenchSdoc(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        Object roleAttr = req.getAttribute("role");
        String role = roleAttr == null ? "STUDENT" : String.valueOf(roleAttr);
        return Result.success(scriptService.openWorkbenchSdoc(id, userId, tenantId, role));
    }

    /** 从绑定的智能文档回写步骤正文 */
    @PostMapping("/{id}/sync-from-sdoc")
    public Result<Script> syncFromSdoc(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(scriptService.syncFromSdoc(id, userId));
    }

    /** 钉住最新评分 + 讲稿，只对评分点名的步骤出对照清单 */
    @GetMapping("/{id}/score-revise-brief")
    public Result<Map<String, Object>> scoreReviseBrief(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(scriptScoreReviseService.brief(id, userId, tenantId));
    }

    /** 智能文档反查绑定讲稿 */
    @GetMapping("/from-sdoc/{documentId}")
    public Result<Script> getBySdoc(@PathVariable Long documentId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Script script = scriptService.getBySdocDocumentId(documentId, userId);
        if (script == null) return Result.error(404, "该文档没有绑定讲稿");
        return Result.success(script);
    }

    /** 启发 Office 智能文档即讲稿：打开时创建或挂上 script */
    @PostMapping("/from-sdoc/{documentId}/ensure")
    public Result<Map<String, Object>> ensureForSdoc(@PathVariable Long documentId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(scriptService.ensureForSdoc(documentId, userId));
    }

    /** 删除讲稿 */
    public Result<Void> delete(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        if (!scriptService.deleteScript(id, userId)) {
            return Result.error(404, "讲稿不存在或无权访问");
        }
        return Result.success(null);
    }

    /** 获取用户的所有讲稿 */
    @GetMapping("/my")
    public Result<List<Script>> myScripts(HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        pptScriptSyncService.ensureScriptsForUser(userId);
        return Result.success(scriptService.listByUserId(userId));
    }

    /** 导出 PDF */
    @GetMapping("/{id}/pdf")
    public ResponseEntity<byte[]> exportPdf(@PathVariable Long id, HttpServletRequest req) throws IOException {
        Long userId = (Long) req.getAttribute("userId");
        Script script = scriptService.getById(id, userId);
        if (script == null) {
            return ResponseEntity.notFound().build();
        }

        byte[] pdfBytes = pdfService.generateScriptPdf(script);

        String filename = URLEncoder.encode(script.getTitle() + ".pdf", StandardCharsets.UTF_8)
                .replace("+", "%20");

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + filename)
                .contentType(MediaType.APPLICATION_PDF)
                .body(pdfBytes);
    }
}
