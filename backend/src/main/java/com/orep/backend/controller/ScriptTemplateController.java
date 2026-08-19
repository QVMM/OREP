package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.ScriptTemplate;
import com.orep.backend.service.ScriptTemplateService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/script-template")
public class ScriptTemplateController {

    @Autowired
    private ScriptTemplateService service;

    /** 获取可用模板列表 */
    @GetMapping
    public Result<List<ScriptTemplate>> list(HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        return Result.success(service.listAvailable(userId));
    }

    /** 根据ID获取模板 */
    @GetMapping("/{id}")
    public Result<ScriptTemplate> getById(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        ScriptTemplate template = service.getById(id, userId);
        if (template == null) return Result.error(404, "模板不存在或无权访问");
        return Result.success(template);
    }

    /** 创建模板 */
    @PostMapping
    public Result<ScriptTemplate> create(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String name = body.get("name").toString();
        String description = body.getOrDefault("description", "").toString();
        String content = body.get("content") != null ? body.get("content").toString() : null;
        String roles = body.get("roles") != null ? body.get("roles").toString() : null;
        return Result.success(service.create(name, description, content, roles, userId));
    }

    /** 更新模板 */
    @PutMapping("/{id}")
    public Result<ScriptTemplate> update(@PathVariable Long id, @RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String name = body.get("name").toString();
        String description = body.getOrDefault("description", "").toString();
        String content = body.get("content") != null ? body.get("content").toString() : null;
        String roles = body.get("roles") != null ? body.get("roles").toString() : null;
        ScriptTemplate t = service.update(id, name, description, content, roles, userId);
        if (t == null) return Result.error(404, "模板不存在或无权修改");
        return Result.success(t);
    }

    /** 删除模板 */
    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        if (!service.delete(id, userId)) return Result.error(403, "无法删除");
        return Result.success(null);
    }

    /** 从讲稿另存为模板 */
    @PostMapping("/from-script")
    public Result<ScriptTemplate> fromScript(@RequestBody Map<String, Object> body, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String name = body.get("name").toString();
        String description = body.getOrDefault("description", "").toString();
        String content = body.get("content") != null ? body.get("content").toString() : null;
        String roles = body.get("roles") != null ? body.get("roles").toString() : null;
        return Result.success(service.saveFromScript(name, description, content, roles, userId));
    }
}
