package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentHomeService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/student")
public class StudentHomeController {
    private final StudentHomeService studentHomeService;

    public StudentHomeController(StudentHomeService studentHomeService) {
        this.studentHomeService = studentHomeService;
    }

    @GetMapping("/home")
    public Result<Map<String, Object>> home(HttpServletRequest request) {
        return Result.success(studentHomeService.home(tenantId(request), userId(request)));
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private Long tenantId(HttpServletRequest request) {
        return (Long) request.getAttribute("tenantId");
    }
}
