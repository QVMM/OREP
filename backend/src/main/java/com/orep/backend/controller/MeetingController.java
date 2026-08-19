package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.CreateMeetingRequest;
import com.orep.backend.dto.JoinMeetingRequest;
import com.orep.backend.dto.MeetingDetailVO;
import com.orep.backend.dto.MeetingHistoryVO;
import com.orep.backend.entity.Meeting;
import com.orep.backend.entity.MeetingParticipant;
import com.orep.backend.service.MeetingService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.UrlResource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/meeting")
public class MeetingController {

    @Autowired
    private MeetingService meetingService;

    @PostMapping("/create")
    public Result<Meeting> create(@Valid @RequestBody CreateMeetingRequest request, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        // 全员可创建路演室：生成会议号后发给队友加入
        return Result.success(meetingService.createMeeting(request, userId, tenantId));
    }

    @GetMapping("/list")
    public Result<List<Meeting>> list(HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.listMeetings(tenantId, userId, role));
    }

    @GetMapping("/{id}")
    public Result<Meeting> getById(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.getMeetingById(id, userId, role));
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        if (!meetingService.deleteMeeting(id, tenantId, userId, role)) {
            return Result.error(404, "会议不存在或无权删除");
        }
        return Result.success();
    }

    @PostMapping("/batch-delete")
    public Result<BatchDeleteResult> batchDelete(@RequestBody BatchDeleteRequest request, HttpServletRequest req) {
        Long tenantId = (Long) req.getAttribute("tenantId");
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.deleteMeetings(request.getIds(), tenantId, userId, role));
    }

    /**
     * 邀请制入会：通过会议号+密码
     */
    @PostMapping("/join-by-code")
    public Result<Map<String, Object>> joinByCode(@Valid @RequestBody JoinMeetingRequest request, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        Meeting meeting = meetingService.joinByCode(request, userId, tenantId);
        return Result.success(Map.of(
                "meetingId", meeting.getId(),
                "title", meeting.getTitle(),
                "jitsiRoomId", meeting.getJitsiRoomId(),
                "status", meeting.getStatus()
        ));
    }

    /**
     * 离开会议
     */
    @PostMapping("/{id}/leave")
    public Result<Void> leave(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        meetingService.leaveMeeting(id, userId);
        return Result.success();
    }

    /**
     * 当前用户的历史参与记录
     */
    @GetMapping("/my-history")
    public Result<List<MeetingHistoryVO>> myHistory(HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        return Result.success(meetingService.getMyHistory(userId, tenantId));
    }

    /**
     * 单次会议的参与详情（时长、聊天、评分、问题）
     */
    @GetMapping("/{id}/detail")
    public Result<MeetingDetailVO> detail(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.getMeetingDetail(id, userId, tenantId, role));
    }

    @GetMapping("/{id}/chat-attachment/{messageId}")
    public ResponseEntity<UrlResource> chatAttachment(@PathVariable Long id,
                                                      @PathVariable Long messageId,
                                                      HttpServletRequest req) throws Exception {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        String role = (String) req.getAttribute("role");
        MeetingService.ChatAttachmentFile file = meetingService.getChatAttachment(id, messageId, userId, tenantId, role);
        UrlResource resource = new UrlResource(file.getPath().toUri());
        MediaType mediaType = MediaType.parseMediaType(file.getContentType());
        ContentDisposition disposition = ContentDisposition.attachment()
                .filename(file.getFileName(), StandardCharsets.UTF_8)
                .build();
        if (mediaType.getType().equals("image")) {
            disposition = ContentDisposition.inline()
                    .filename(file.getFileName(), StandardCharsets.UTF_8)
                    .build();
        }
        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(HttpHeaders.CONTENT_DISPOSITION, disposition.toString())
                .body(resource);
    }

    @PostMapping("/{id}/join")
    public Result<Meeting> join(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.joinMeeting(id, userId, role));
    }

    @PostMapping("/{id}/start")
    public Result<Meeting> start(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.startMeeting(id, userId, role));
    }

    @PostMapping("/{id}/end")
    public Result<Meeting> end(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.endMeeting(id, userId, role));
    }

    @GetMapping("/{id}/participants")
    public Result<List<MeetingParticipant>> participants(@PathVariable Long id, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(meetingService.getParticipants(id, userId, role));
    }
}
