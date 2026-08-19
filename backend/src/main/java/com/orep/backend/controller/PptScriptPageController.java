package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.PptScriptPage;
import com.orep.backend.service.PptScriptSyncService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/slide-script")
public class PptScriptPageController {

    @Autowired
    private PptScriptSyncService syncService;

    @GetMapping("/{jobId}")
    public Result<Map<String, Object>> list(@PathVariable String jobId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(syncService.listBundle(jobId, userId));
    }

    @GetMapping("/{jobId}/pages/{pageIndex}")
    public Result<PptScriptPage> getPage(
            @PathVariable String jobId,
            @PathVariable Integer pageIndex,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(syncService.getPageForUser(jobId, pageIndex, userId));
    }

    @PutMapping("/{jobId}/pages/{pageIndex}")
    public Result<PptScriptPage> savePage(
            @PathVariable String jobId,
            @PathVariable Integer pageIndex,
            @RequestBody Map<String, Object> body,
            HttpServletRequest req
    ) {
        Long userId = (Long) req.getAttribute("userId");
        String pageName = stringValue(body.get("pageName"));
        String pageTitle = stringValue(body.get("pageTitle"));
        String notes = stringValue(body.get("notes"));
        String documentJson = stringValue(body.get("documentJson"));
        String source = stringValue(body.get("source"));
        Boolean manualEdited = body.get("manualEdited") instanceof Boolean value ? value : Boolean.TRUE;
        PptScriptPage saved = syncService.savePageAndSync(jobId, pageIndex, pageName, pageTitle, notes, documentJson, source, manualEdited, userId);
        if (saved == null) return Result.error(400, "讲稿保存参数不完整");
        return Result.success(saved);
    }

    @DeleteMapping("/{jobId}/pages/{pageIndex}")
    public Result<Void> deletePage(@PathVariable String jobId, @PathVariable Integer pageIndex, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        if (!syncService.deletePageAndSync(jobId, pageIndex, userId)) {
            return Result.error(404, "讲稿不存在或无权删除");
        }
        return Result.success(null);
    }

    private String stringValue(Object value) {
        return value == null ? null : value.toString();
    }
}
