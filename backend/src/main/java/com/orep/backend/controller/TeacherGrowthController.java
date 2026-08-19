package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.TeacherGrowthService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/teacher/student-growth")
public class TeacherGrowthController {

    private final TeacherGrowthService teacherGrowthService;

    public TeacherGrowthController(TeacherGrowthService teacherGrowthService) {
        this.teacherGrowthService = teacherGrowthService;
    }

    @GetMapping("/certificates")
    public Result<List<Map<String, Object>>> listCertificates(
            @RequestParam(required = false) Long teamId,
            HttpServletRequest request
    ) {
        assertTeacher(request);
        return Result.success(teacherGrowthService.listCertificates(tenantId(request), teamId));
    }

    @PostMapping("/certificates")
    public Result<Map<String, Object>> createCertificate(
        @RequestBody Map<String, Object> body,
        HttpServletRequest request
    ) {
        assertTeacher(request);
        return Result.success(teacherGrowthService.createCertificate(tenantId(request), userId(request), body));
    }

    @PostMapping(value = "/certificates/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> uploadCertificate(
            @RequestPart("file") MultipartFile file,
            @RequestParam String title,
            @RequestParam String recipientType,
            @RequestParam String recipientIds,
            @RequestParam(required = false) String description,
            @RequestParam(required = false) String awardLevel,
            @RequestParam(required = false) String issuerName,
            @RequestParam(required = false) String issuedAt,
            @RequestParam(required = false) String certificateNo,
            HttpServletRequest request
    ) {
        assertTeacher(request);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("title", title);
        body.put("recipientType", recipientType);
        body.put("recipientIds", recipientIds);
        body.put("description", description);
        body.put("awardLevel", awardLevel);
        body.put("issuerName", issuerName);
        body.put("issuedAt", issuedAt);
        body.put("certificateNo", certificateNo);
        body.put("sourceType", "UPLOADED");
        return Result.success(teacherGrowthService.uploadCertificate(tenantId(request), userId(request), file, body));
    }

    @PostMapping("/certificates/{certificateId}/revoke")
    public Result<Map<String, Object>> revokeCertificate(
            @PathVariable Long certificateId,
            HttpServletRequest request
    ) {
        assertTeacher(request);
        return Result.success(teacherGrowthService.revokeCertificate(tenantId(request), certificateId));
    }

    @PostMapping("/rectifications")
    public Result<Map<String, Object>> createRectification(
        @RequestBody Map<String, Object> body,
        HttpServletRequest request
    ) {
        assertTeacher(request);
        return Result.success(teacherGrowthService.createRectification(tenantId(request), userId(request), body));
    }

    private void assertTeacher(HttpServletRequest request) {
        String role = String.valueOf(request.getAttribute("role")).toUpperCase();
        if (!role.equals("TEACHER") && !role.equals("ADMIN")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有老师或管理员可以发布奖状和整改");
        }
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
