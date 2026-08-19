package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.CreateMeetingRequest;
import com.orep.backend.dto.JoinMeetingRequest;
import com.orep.backend.dto.MeetingDetailVO;
import com.orep.backend.dto.MeetingHistoryVO;
import com.orep.backend.entity.*;
import com.orep.backend.mapper.*;
import com.orep.backend.security.DataScopeService;
import cn.hutool.core.util.IdUtil;
import cn.hutool.core.util.RandomUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class MeetingService {

    @Autowired
    private MeetingMapper meetingMapper;
    @Autowired
    private MeetingParticipantMapper participantMapper;
    @Autowired
    private ChatMessageMapper chatMessageMapper;
    @Autowired
    private StringRedisTemplate redisTemplate;
    @Autowired
    private ScoreRecordMapper scoreRecordMapper;
    @Autowired
    private ScoreDetailMapper scoreDetailMapper;
    @Autowired
    private ScoreItemMapper scoreItemMapper;
    @Autowired
    private IssueMapper issueMapper;
    @Autowired
    private MeetingRecordingMapper meetingRecordingMapper;
    @Autowired
    private DataScopeService dataScopeService;
    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    public Meeting createMeeting(CreateMeetingRequest request, Long creatorId, Long tenantId) {
        Meeting meeting = new Meeting();
        meeting.setTenantId(tenantId);
        meeting.setTitle(request.getTitle());
        meeting.setCreatorId(creatorId);
        // 生成 6 位纯数字会议号
        meeting.setMeetingCode(RandomUtil.randomNumbers(6));
        // 自动生成 4 位密码
        meeting.setMeetingPassword(RandomUtil.randomNumbers(4));
        meeting.setJitsiRoomId("orep-" + IdUtil.fastSimpleUUID());
        meeting.setStatus("CREATED");
        meeting.setDurationMinutes(request.getDurationMinutes() != null ? request.getDurationMinutes() : 60);
        meetingMapper.insert(meeting);
        return meeting;
    }

    public List<Meeting> listMeetings(Long tenantId, Long userId, String role) {
        List<Long> meetingIds = dataScopeService.accessibleMeetingIds(tenantId, userId, role);
        if (meetingIds.isEmpty()) {
            return List.of();
        }
        return meetingMapper.selectList(
                new LambdaQueryWrapper<Meeting>()
                        .eq(Meeting::getTenantId, tenantId)
                        .in(Meeting::getId, meetingIds)
                        .orderByDesc(Meeting::getCreatedAt)
        );
    }

    public Meeting getMeetingById(Long id, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(id);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);
        return meeting;
    }

    @Transactional
    public boolean deleteMeeting(Long id, Long tenantId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(id);
        if (meeting == null || !meeting.getTenantId().equals(tenantId)) {
            return false;
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);

        List<ScoreRecord> records = scoreRecordMapper.selectList(
                new LambdaQueryWrapper<ScoreRecord>().eq(ScoreRecord::getMeetingId, id)
        );
        List<Long> recordIds = records.stream().map(ScoreRecord::getId).toList();
        if (!recordIds.isEmpty()) {
            scoreDetailMapper.delete(new LambdaQueryWrapper<ScoreDetail>().in(ScoreDetail::getRecordId, recordIds));
        }
        scoreRecordMapper.delete(new LambdaQueryWrapper<ScoreRecord>().eq(ScoreRecord::getMeetingId, id));
        issueMapper.delete(new LambdaQueryWrapper<Issue>().eq(Issue::getMeetingId, id));
        participantMapper.delete(new LambdaQueryWrapper<MeetingParticipant>().eq(MeetingParticipant::getMeetingId, id));
        chatMessageMapper.delete(new LambdaQueryWrapper<ChatMessage>().eq(ChatMessage::getMeetingId, id));
        meetingRecordingMapper.delete(new LambdaQueryWrapper<MeetingRecording>().eq(MeetingRecording::getMeetingId, id));
        return meetingMapper.deleteById(id) > 0;
    }

    @Transactional
    public BatchDeleteResult deleteMeetings(List<Long> ids, Long tenantId, Long userId, String role) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = normalizeIds(ids);
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            if (deleteMeeting(id, tenantId, userId, role)) {
                result.addDeleted();
            } else {
                result.addFailure(id, "会议不存在、不属于当前租户或无权删除");
            }
        }
        return result;
    }

    /**
     * 通过会议号+密码入会（邀请制核心）
     */
    public Meeting joinByCode(JoinMeetingRequest request, Long userId, Long tenantId) {
        // 查找会议
        Meeting meeting = meetingMapper.selectOne(
                new LambdaQueryWrapper<Meeting>()
                        .eq(Meeting::getMeetingCode, request.getMeetingCode())
                        .eq(Meeting::getTenantId, tenantId)
        );
        if (meeting == null) {
            throw new RuntimeException("会议号不存在");
        }

        // 验证密码
        if (!meeting.getMeetingPassword().equals(request.getPassword())) {
            throw new RuntimeException("入会密码错误");
        }

        // 在 Redis 记录密码验证状态（用于后续 LiveKit token 校验，防止绕过密码）
        long ttlMinutes = meeting.getDurationMinutes() != null ? meeting.getDurationMinutes() : 60;
        redisTemplate.opsForValue().set(
                "meeting:verified:" + meeting.getId() + ":" + userId,
                "1",
                ttlMinutes,
                TimeUnit.MINUTES
        );

        // 检查会议状态
        if ("ENDED".equals(meeting.getStatus())) {
            throw new RuntimeException("会议已结束");
        }

        // 如果是 CREATED 状态，自动启动
        if ("CREATED".equals(meeting.getStatus())) {
            meeting.setStatus("RUNNING");
            meeting.setStartTime(LocalDateTime.now());
            meeting.setCountdownEndAt(LocalDateTime.now().plusMinutes(meeting.getDurationMinutes()));
            meetingMapper.updateById(meeting);
        }

        // 记录参与者（已有记录则更新，否则新建）
        MeetingParticipant existing = participantMapper.selectOne(
                new LambdaQueryWrapper<MeetingParticipant>()
                        .eq(MeetingParticipant::getMeetingId, meeting.getId())
                        .eq(MeetingParticipant::getUserId, userId)
        );
        if (existing != null) {
            existing.setJoinedAt(LocalDateTime.now());
            existing.setLeftAt(null);
            existing.setDurationSeconds(null);
            participantMapper.updateById(existing);
        } else {
            MeetingParticipant participant = new MeetingParticipant();
            participant.setMeetingId(meeting.getId());
            participant.setUserId(userId);
            participant.setJoinedAt(LocalDateTime.now());
            participantMapper.insert(participant);
        }

        return meeting;
    }

    /**
     * 检查用户是否已通过该会议的密码验证
     */
    public boolean isPasswordVerified(Long meetingId, Long userId) {
        String val = redisTemplate.opsForValue().get("meeting:verified:" + meetingId + ":" + userId);
        return "1".equals(val);
    }

    /**
     * 原有的 joinMeeting（通过 ID 直接入会，管理员用）
     */
    public Meeting joinMeeting(Long meetingId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);

        MeetingParticipant participant = new MeetingParticipant();
        participant.setMeetingId(meetingId);
        participant.setUserId(userId);
        participant.setJoinedAt(LocalDateTime.now());
        participantMapper.insert(participant);

        return meeting;
    }

    /**
     * 离开会议，记录离开时间和时长
     */
    public void leaveMeeting(Long meetingId, Long userId) {
        MeetingParticipant participant = participantMapper.selectOne(
                new LambdaQueryWrapper<MeetingParticipant>()
                        .eq(MeetingParticipant::getMeetingId, meetingId)
                        .eq(MeetingParticipant::getUserId, userId)
                        .isNull(MeetingParticipant::getLeftAt)
                        .orderByDesc(MeetingParticipant::getJoinedAt)
                        .last("LIMIT 1")
        );
        if (participant != null) {
            LocalDateTime now = LocalDateTime.now();
            participant.setLeftAt(now);
            if (participant.getJoinedAt() != null) {
                long seconds = Duration.between(participant.getJoinedAt(), now).getSeconds();
                participant.setDurationSeconds((int) seconds);
            }
            participantMapper.updateById(participant);
        }
    }

    /**
     * 获取当前用户的历史参与记录
     */
    public List<MeetingHistoryVO> getMyHistory(Long userId, Long tenantId) {
        // 获取该租户下用户参与的所有会议记录
        List<MeetingParticipant> participations = participantMapper.selectList(
                new LambdaQueryWrapper<MeetingParticipant>()
                        .eq(MeetingParticipant::getUserId, userId)
                        .orderByDesc(MeetingParticipant::getJoinedAt)
        );

        if (participations.isEmpty()) {
            return new ArrayList<>();
        }

        // 获取关联的会议信息
        List<Long> meetingIds = participations.stream()
                .map(MeetingParticipant::getMeetingId)
                .distinct()
                .collect(Collectors.toList());

        List<Meeting> meetings = meetingMapper.selectList(
                new LambdaQueryWrapper<Meeting>()
                        .in(Meeting::getId, meetingIds)
                        .eq(Meeting::getTenantId, tenantId)
        );

        // 按 meetingId 分组参与记录，取最近一次
        var participationMap = participations.stream()
                .collect(Collectors.toMap(
                        MeetingParticipant::getMeetingId,
                        p -> p,
                        (a, b) -> a.getJoinedAt().isAfter(b.getJoinedAt()) ? a : b
                ));

        List<MeetingHistoryVO> result = new ArrayList<>();
        for (Meeting m : meetings) {
            String meetingPassword = ensureMeetingPassword(m);
            MeetingHistoryVO vo = new MeetingHistoryVO();
            vo.setMeetingId(m.getId());
            vo.setTitle(m.getTitle());
            vo.setMeetingCode(m.getMeetingCode());
            vo.setMeetingPassword(meetingPassword);
            vo.setJoinCredential(meetingPassword);
            vo.setStatus(m.getStatus());
            vo.setStartTime(m.getStartTime());
            vo.setEndTime(m.getEndTime());
            vo.setMeetingCreatedAt(m.getCreatedAt());

            MeetingParticipant p = participationMap.get(m.getId());
            if (p != null) {
                vo.setJoinedAt(p.getJoinedAt());
                vo.setLeftAt(p.getLeftAt());
                vo.setDurationSeconds(p.getDurationSeconds());
            }
            result.add(vo);
        }

        // 按参与时间倒序
        result.sort((a, b) -> {
            if (a.getJoinedAt() == null) return 1;
            if (b.getJoinedAt() == null) return -1;
            return b.getJoinedAt().compareTo(a.getJoinedAt());
        });

        return result;
    }

    private String ensureMeetingPassword(Meeting meeting) {
        String password = meeting.getMeetingPassword();
        if (password != null && !password.isBlank()) {
            return password;
        }
        password = RandomUtil.randomNumbers(4);
        meeting.setMeetingPassword(password);
        meetingMapper.updateById(meeting);
        return password;
    }

    private List<Long> normalizeIds(List<Long> ids) {
        if (ids == null) return List.of();
        return ids.stream().filter(java.util.Objects::nonNull).distinct().toList();
    }

    /**
     * 获取单次会议的参与详情
     */
    public MeetingDetailVO getMeetingDetail(Long meetingId, Long userId, Long tenantId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null || !meeting.getTenantId().equals(tenantId)) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);

        MeetingDetailVO vo = new MeetingDetailVO();
        vo.setMeetingId(meeting.getId());
        vo.setTitle(meeting.getTitle());
        vo.setMeetingCode(meeting.getMeetingCode());
        vo.setStatus(meeting.getStatus());
        vo.setStartTime(meeting.getStartTime());
        vo.setEndTime(meeting.getEndTime());

        // 用户参与信息（取最近一次）
        MeetingParticipant participant = participantMapper.selectOne(
                new LambdaQueryWrapper<MeetingParticipant>()
                        .eq(MeetingParticipant::getMeetingId, meetingId)
                        .eq(MeetingParticipant::getUserId, userId)
                        .orderByDesc(MeetingParticipant::getJoinedAt)
                        .last("LIMIT 1")
        );
        if (participant != null) {
            vo.setJoinedAt(participant.getJoinedAt());
            vo.setLeftAt(participant.getLeftAt());
            vo.setDurationSeconds(participant.getDurationSeconds());
        }

        // 聊天记录
        List<ChatMessage> messages = chatMessageMapper.selectList(
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getMeetingId, meetingId)
                        .orderByAsc(ChatMessage::getCreatedAt)
        );
        vo.setChatMessages(messages.stream().map(msg -> {
            MeetingDetailVO.ChatRecord cr = new MeetingDetailVO.ChatRecord();
            cr.setId(msg.getId());
            cr.setSenderName(msg.getSenderName());
            cr.setContent(msg.getContent());
            cr.setMessageType(msg.getMessageType());
            cr.setFileName(msg.getFileName());
            cr.setCreatedAt(msg.getCreatedAt());
            return cr;
        }).collect(Collectors.toList()));

        // 评分结果
        ScoreRecord scoreRecord = scoreRecordMapper.selectOne(
                new LambdaQueryWrapper<ScoreRecord>()
                        .eq(ScoreRecord::getMeetingId, meetingId)
                        .eq(ScoreRecord::getUserId, userId)
                        .last("LIMIT 1")
        );
        if (scoreRecord != null) {
            vo.setTotalScore(scoreRecord.getTotalScore());

            List<ScoreDetail> details = scoreDetailMapper.selectList(
                    new LambdaQueryWrapper<ScoreDetail>()
                            .eq(ScoreDetail::getRecordId, scoreRecord.getId())
            );
            // 获取评分项名称
            List<Long> itemIds = details.stream()
                    .map(ScoreDetail::getItemId)
                    .filter(id -> id != null)
                    .distinct()
                    .collect(Collectors.toList());
            List<ScoreItem> items = itemIds.isEmpty() ? new ArrayList<>() :
                    scoreItemMapper.selectList(
                            new LambdaQueryWrapper<ScoreItem>()
                                    .in(ScoreItem::getId, itemIds)
                    );
            var itemMap = items.stream().collect(Collectors.toMap(ScoreItem::getId, i -> i));

            vo.setScoreDetails(details.stream().map(d -> {
                MeetingDetailVO.ScoreItemRecord sir = new MeetingDetailVO.ScoreItemRecord();
                ScoreItem item = itemMap.get(d.getItemId());
                if (item != null) {
                    sir.setCategory(item.getCategory());
                    sir.setItemName(item.getName());
                    sir.setMaxScore(item.getMaxScore());
                }
                sir.setScore(d.getScore());
                sir.setComment(d.getComment());
                return sir;
            }).collect(Collectors.toList()));
        } else {
            vo.setTotalScore(null);
            vo.setScoreDetails(new ArrayList<>());
        }

        // 存在问题
        List<Issue> issues = issueMapper.selectList(
                new LambdaQueryWrapper<Issue>()
                        .eq(Issue::getMeetingId, meetingId)
                        .orderByDesc(Issue::getCreatedAt)
        );
        vo.setIssues(issues.stream().map(issue -> {
            MeetingDetailVO.IssueRecord ir = new MeetingDetailVO.IssueRecord();
            ir.setId(issue.getId());
            ir.setCategory(issue.getCategory());
            ir.setDescription(issue.getDescription());
            ir.setStatus(issue.getStatus());
            ir.setCreatedAt(issue.getCreatedAt());
            ir.setResolvedAt(issue.getResolvedAt());
            return ir;
        }).collect(Collectors.toList()));

        return vo;
    }

    public ChatAttachmentFile getChatAttachment(Long meetingId, Long messageId, Long userId, Long tenantId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null || !meeting.getTenantId().equals(tenantId)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);

        ChatMessage message = chatMessageMapper.selectById(messageId);
        if (message == null || !meetingId.equals(message.getMeetingId())) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "附件不存在");
        }
        if (!"image".equals(message.getMessageType()) && !"file".equals(message.getMessageType())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "该消息不是附件");
        }

        Path uploadRoot = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path filePath = resolveUploadPath(uploadRoot, message.getContent());
        if (!Files.isRegularFile(filePath)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "附件文件不存在");
        }

        String fileName = safeFileName(message.getFileName());
        if (fileName.isBlank()) {
            fileName = filePath.getFileName().toString();
        }
        String contentType;
        try {
            contentType = Files.probeContentType(filePath);
        } catch (Exception e) {
            contentType = null;
        }
        return new ChatAttachmentFile(filePath, fileName, contentType != null ? contentType : "application/octet-stream");
    }

    private Path resolveUploadPath(Path uploadRoot, String content) {
        String value = content == null ? "" : content.trim();
        int uploadsIndex = value.indexOf("/uploads/");
        if (uploadsIndex >= 0) {
            value = value.substring(uploadsIndex + "/uploads/".length());
        } else if (value.startsWith("uploads/")) {
            value = value.substring("uploads/".length());
        } else {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "附件路径非法");
        }

        value = value.split("\\?", 2)[0].split("#", 2)[0];
        value = URLDecoder.decode(value, StandardCharsets.UTF_8);
        Path filePath = uploadRoot.resolve(value).normalize();
        if (!filePath.startsWith(uploadRoot)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "附件路径非法");
        }
        return filePath;
    }

    private String safeFileName(String fileName) {
        return fileName == null ? "" : fileName.replaceAll("[\\\\/:*?\"<>|]", "").trim();
    }

    public static class ChatAttachmentFile {
        private final Path path;
        private final String fileName;
        private final String contentType;

        public ChatAttachmentFile(Path path, String fileName, String contentType) {
            this.path = path;
            this.fileName = fileName;
            this.contentType = contentType;
        }

        public Path getPath() {
            return path;
        }

        public String getFileName() {
            return fileName;
        }

        public String getContentType() {
            return contentType;
        }
    }

    public Meeting startMeeting(Long meetingId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);
        meeting.setStatus("RUNNING");
        meeting.setStartTime(LocalDateTime.now());
        meeting.setCountdownEndAt(LocalDateTime.now().plusMinutes(meeting.getDurationMinutes()));
        meetingMapper.updateById(meeting);
        return meeting;
    }

    public Meeting endMeeting(Long meetingId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);
        meeting.setStatus("ENDED");
        meeting.setEndTime(LocalDateTime.now());
        meetingMapper.updateById(meeting);
        return meeting;
    }

    public List<MeetingParticipant> getParticipants(Long meetingId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);
        return participantMapper.selectList(
                new LambdaQueryWrapper<MeetingParticipant>()
                        .eq(MeetingParticipant::getMeetingId, meetingId)
        );
    }
}
