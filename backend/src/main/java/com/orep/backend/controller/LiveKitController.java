package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.LiveKitService;
import com.orep.backend.service.MeetingService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/livekit")
public class LiveKitController {

    @Autowired
    private LiveKitService liveKitService;

    @Autowired
    private MeetingService meetingService;

    /**
     * 获取加入会议的 LiveKit token
     * 必须先通过 join-by-code 验证密码，否则拒绝
     */
    @GetMapping("/token")
    public Result<Map<String, String>> getToken(
            @RequestParam String meetingId,
            HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String username = (String) request.getAttribute("username");
        String role = (String) request.getAttribute("role");

        // 检查是否已通过密码验证（防止直接访问绕过密码）
        if (!meetingService.isPasswordVerified(Long.parseLong(meetingId), userId)) {
            return Result.error(403, "请先输入会议密码");
        }

        String token = liveKitService.generateToken(meetingId, userId, username, role);
        return Result.success(Map.of(
                "token", token,
                "wsUrl", liveKitService.getWsUrl()
        ));
    }
}
