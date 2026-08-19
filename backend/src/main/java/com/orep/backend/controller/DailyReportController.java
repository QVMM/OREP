package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.DailyReportService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/daily-reports")
public class DailyReportController {

    private final DailyReportService dailyReportService;

    public DailyReportController(DailyReportService dailyReportService) {
        this.dailyReportService = dailyReportService;
    }

    @GetMapping("/today")
    public Result<Map<String, Object>> today(HttpServletRequest request) {
        return Result.success(dailyReportService.today(tenantId(request), userId(request)));
    }

    @GetMapping("/for-date")
    public Result<Map<String, Object>> forDate(
            @RequestParam(value = "date", required = false) String date,
            HttpServletRequest request
    ) {
        return Result.success(dailyReportService.forDate(tenantId(request), userId(request), date));
    }

    @GetMapping("/stats")
    public Result<Map<String, Object>> stats(HttpServletRequest request) {
        return Result.success(dailyReportService.stats(tenantId(request), userId(request)));
    }

    @GetMapping("/{id}")
    public Result<Map<String, Object>> detail(@PathVariable Long id, HttpServletRequest request) {
        return Result.success(dailyReportService.getById(tenantId(request), userId(request), id));
    }

    @GetMapping
    public Result<List<Map<String, Object>>> history(
            @RequestParam(required = false) Integer limit,
            HttpServletRequest request
    ) {
        return Result.success(dailyReportService.history(tenantId(request), userId(request), limit));
    }

    @PostMapping
    public Result<Map<String, Object>> save(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return Result.success(dailyReportService.save(tenantId(request), userId(request), body));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }
}
