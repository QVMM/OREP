package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.service.HomeService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/home")
public class HomeController {
    private final HomeService homeService;

    public HomeController(HomeService homeService) {
        this.homeService = homeService;
    }

    @GetMapping("/dashboard")
    public Result<Map<String, Object>> dashboard(HttpServletRequest request) {
        return Result.success(homeService.userHome(tenantId(request), userId(request), role(request)));
    }

    @GetMapping("/admin/banners")
    public Result<Map<String, Object>> adminBanners(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int pageSize,
            HttpServletRequest request
    ) {
        return Result.success(homeService.adminBanners(tenantId(request), role(request), page, pageSize));
    }

    @PostMapping("/admin/banners")
    public Result<Map<String, Object>> createBanner(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(homeService.createBanner(tenantId(request), userId(request), role(request), body));
    }

    @PutMapping("/admin/banners/{id}")
    public Result<Map<String, Object>> updateBanner(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        return Result.success(homeService.updateBanner(tenantId(request), id, role(request), body));
    }

    @DeleteMapping("/admin/banners/{id}")
    public Result<Void> deleteBanner(@PathVariable Long id, HttpServletRequest request) {
        homeService.deleteBanner(tenantId(request), id, role(request));
        return Result.success();
    }

    @PostMapping("/admin/banners/batch-delete")
    public Result<BatchDeleteResult> batchDeleteBanners(
            @RequestBody BatchDeleteRequest body,
            HttpServletRequest request
    ) {
        return Result.success(homeService.deleteBanners(tenantId(request), body.getIds(), role(request)));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }
}
