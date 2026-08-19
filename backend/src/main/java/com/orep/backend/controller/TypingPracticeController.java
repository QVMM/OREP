package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.TypingCoachService;
import com.orep.backend.service.TypingPracticeService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/typing")
public class TypingPracticeController {

    private final TypingPracticeService typingPracticeService;
    private final TypingCoachService typingCoachService;

    public TypingPracticeController(
            TypingPracticeService typingPracticeService,
            TypingCoachService typingCoachService
    ) {
        this.typingPracticeService = typingPracticeService;
        this.typingCoachService = typingCoachService;
    }

    @PostMapping("/sessions")
    public Result<Map<String, Object>> saveSession(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return Result.success(typingPracticeService.saveSession(tenantId(request), userId(request), body));
    }

    @GetMapping("/leaderboard")
    public Result<Map<String, Object>> leaderboard(
            @RequestParam(required = false) String textVersion,
            @RequestParam(required = false) Integer limit,
            HttpServletRequest request
    ) {
        return Result.success(typingPracticeService.leaderboard(tenantId(request), userId(request), textVersion, limit));
    }

    @GetMapping("/me/stats")
    public Result<Map<String, Object>> myStats(HttpServletRequest request) {
        return Result.success(typingPracticeService.myStats(tenantId(request), userId(request)));
    }

    /** AI 教练点评（规则引擎，结构稳定可扩展 LLM） */
    @PostMapping("/coach")
    public Result<Map<String, Object>> coach(@RequestBody Map<String, Object> body) {
        return Result.success(typingCoachService.coach(body));
    }

    // --- 账户级自定义文案 ---

    @GetMapping("/custom-texts")
    public Result<List<Map<String, Object>>> listCustomTexts(HttpServletRequest request) {
        try {
            return Result.success(typingPracticeService.listCustomTexts(userId(request)));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PostMapping("/custom-texts")
    public Result<Map<String, Object>> createCustomText(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        try {
            return Result.success(typingPracticeService.saveCustomText(tenantId(request), userId(request), body));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PutMapping("/custom-texts/{id}")
    public Result<Map<String, Object>> updateCustomText(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request
    ) {
        try {
            return Result.success(typingPracticeService.updateCustomText(userId(request), id, body));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @DeleteMapping("/custom-texts/{id}")
    public Result<Void> deleteCustomText(@PathVariable Long id, HttpServletRequest request) {
        try {
            typingPracticeService.deleteCustomText(userId(request), id);
            return Result.success(null);
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }
}
