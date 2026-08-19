package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.StudentProfileService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/student/profile")
public class StudentProfileController {

    private final StudentProfileService studentProfileService;

    public StudentProfileController(StudentProfileService studentProfileService) {
        this.studentProfileService = studentProfileService;
    }

    @GetMapping("/dashboard")
    public Result<Map<String, Object>> dashboard(HttpServletRequest request) {
        return Result.success(studentProfileService.dashboard(tenantId(request), userId(request)));
    }

    private Long tenantId(HttpServletRequest request) {
        Object value = request.getAttribute("tenantId");
        return value instanceof Number number ? number.longValue() : Long.valueOf(String.valueOf(value));
    }

    private Long userId(HttpServletRequest request) {
        Object value = request.getAttribute("userId");
        return value instanceof Number number ? number.longValue() : Long.valueOf(String.valueOf(value));
    }
}
