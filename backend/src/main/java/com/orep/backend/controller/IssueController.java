package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.IssueView;
import com.orep.backend.entity.Issue;
import com.orep.backend.entity.Meeting;
import com.orep.backend.mapper.MeetingMapper;
import com.orep.backend.service.IssueService;
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
@RequestMapping("/api/issue")
public class IssueController {

    @Autowired
    private IssueService issueService;

    @Autowired
    private MeetingMapper meetingMapper;

    @Autowired
    private PdfService pdfService;

    @GetMapping("/list")
    public Result<List<IssueView>> list(HttpServletRequest req,
                                        @RequestParam(required = false) Long meetingId,
                                        @RequestParam(required = false) String status) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(issueService.listIssueViews(tenantId, meetingId, statusValue(status), userId, role));
    }

    @GetMapping("/unresolved")
    public Result<List<Issue>> unresolved(HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(issueService.listUnresolvedIssues(tenantId, userId, role));
    }

    @PostMapping("/resolve")
    public Result<Void> resolve(@RequestBody Map<String, Long> params, HttpServletRequest req) {
        Long issueId = params.get("issueId");
        if (issueId == null) {
            issueId = params.get("id");
        }
        Long meetingId = params.get("meetingId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        issueService.resolveIssue(issueId, meetingId, userId, role);
        return Result.success();
    }

    /** 导出问题报告 PDF */
    @GetMapping("/export-pdf")
    public ResponseEntity<byte[]> exportPdf(HttpServletRequest req,
                                            @RequestParam Long meetingId) throws IOException {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        List<Issue> issues = issueService.listIssues(tenantId, meetingId, userId, role);
        Meeting meeting = meetingMapper.selectById(meetingId);
        String title = meeting != null ? meeting.getTitle() : "会议" + meetingId;

        byte[] pdf = pdfService.generateIssueReport(title, issues);
        String filename = URLEncoder.encode(title + "_问题报告.pdf", StandardCharsets.UTF_8).replace("+", "%20");

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename*=UTF-8''" + filename)
                .contentType(MediaType.APPLICATION_PDF)
                .body(pdf);
    }

    private Integer statusValue(String status) {
        if (status == null || status.isBlank()) return null;
        return "RESOLVED".equalsIgnoreCase(status) ? 1 : 0;
    }
}
