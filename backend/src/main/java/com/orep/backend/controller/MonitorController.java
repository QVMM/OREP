package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.MonitorTrackRequest;
import com.orep.backend.service.MonitorService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
public class MonitorController {

    private final MonitorService monitorService;

    public MonitorController(MonitorService monitorService) {
        this.monitorService = monitorService;
    }

    @PostMapping("/api/monitor/track")
    public Result<Void> track(@RequestBody(required = false) MonitorTrackRequest body, HttpServletRequest request) {
        monitorService.trackFrontend(
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "username"),
                attrString(request, "role"),
                body,
                request
        );
        return Result.success();
    }

    @PostMapping("/api/monitor/heartbeat")
    public Result<Void> heartbeat(@RequestBody(required = false) MonitorTrackRequest body, HttpServletRequest request) {
        monitorService.heartbeat(
                attrLong(request, "tenantId"),
                attrLong(request, "userId"),
                attrString(request, "username"),
                attrString(request, "role"),
                body,
                request
        );
        return Result.success();
    }

    @GetMapping("/api/admin/monitor/dashboard")
    public Result<Map<String, Object>> dashboard(HttpServletRequest request) {
        monitorService.assertAdminRole(attrString(request, "role"));
        return Result.success(monitorService.dashboard(attrLong(request, "tenantId")));
    }

    @GetMapping("/api/admin/monitor/users")
    public Result<List<Map<String, Object>>> users(
            @RequestParam(required = false) String keyword,
            HttpServletRequest request
    ) {
        monitorService.assertAdminRole(attrString(request, "role"));
        return Result.success(monitorService.listUserStatuses(attrLong(request, "tenantId"), keyword));
    }

    @GetMapping("/api/admin/monitor/logs")
    public Result<List<Map<String, Object>>> logs(
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String source,
            @RequestParam(required = false) String actionType,
            @RequestParam(required = false) Integer limit,
            HttpServletRequest request
    ) {
        monitorService.assertAdminRole(attrString(request, "role"));
        return Result.success(monitorService.listLogs(attrLong(request, "tenantId"), userId, source, actionType, limit));
    }

    private Long attrLong(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value instanceof Long ? (Long) value : null;
    }

    private String attrString(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value == null ? "" : String.valueOf(value);
    }
}
