package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.ScoreResultVO;
import com.orep.backend.dto.ScoreSubmitRequest;
import com.orep.backend.entity.*;
import com.orep.backend.mapper.*;
import com.orep.backend.security.DataScopeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class ScoreService {

    @Autowired
    private ScoreRecordMapper recordMapper;
    @Autowired
    private ScoreDetailMapper detailMapper;
    @Autowired
    private ScoreItemMapper itemMapper;
    @Autowired
    private ScoreTemplateMapper templateMapper;
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private MeetingMapper meetingMapper;
    @Autowired
    private IssueService issueService;
    @Autowired
    private DataScopeService dataScopeService;

    public List<ScoreItem> getScoreItems(Long templateId) {
        if (templateId == null) {
            // 获取默认模板
            ScoreTemplate template = templateMapper.selectById(1L);
            templateId = template != null ? template.getId() : 1L;
        }
        return itemMapper.selectList(
                new LambdaQueryWrapper<ScoreItem>()
                        .eq(ScoreItem::getTemplateId, templateId)
                        .orderByAsc(ScoreItem::getSortOrder)
        );
    }

    @Transactional
    public void submitScore(ScoreSubmitRequest request, Long userId, Long tenantId) {
        Long meetingId = request.getMeetingId();

        // 检查是否已提交过
        ScoreRecord existing = recordMapper.selectOne(
                new LambdaQueryWrapper<ScoreRecord>()
                        .eq(ScoreRecord::getMeetingId, meetingId)
                        .eq(ScoreRecord::getUserId, userId)
        );
        if (existing != null) {
            throw new RuntimeException("您已提交过评分，请勿重复提交");
        }

        // 计算总分
        BigDecimal totalScore = BigDecimal.ZERO;
        for (ScoreSubmitRequest.ScoreItemRequest item : request.getScores()) {
            totalScore = totalScore.add(BigDecimal.valueOf(item.getScore()));
        }

        // 保存评分记录
        ScoreRecord record = new ScoreRecord();
        record.setTenantId(tenantId);
        record.setMeetingId(meetingId);
        record.setUserId(userId);
        record.setTotalScore(totalScore);
        record.setSubmittedAt(LocalDateTime.now());
        recordMapper.insert(record);

        // 保存评分详情并生成问题
        List<ScoreItem> scoreItems = getScoreItems(null);
        Map<Long, ScoreItem> itemMap = scoreItems.stream()
                .collect(Collectors.toMap(ScoreItem::getId, s -> s));

        for (ScoreSubmitRequest.ScoreItemRequest item : request.getScores()) {
            ScoreDetail detail = new ScoreDetail();
            detail.setRecordId(record.getId());
            detail.setItemId(item.getItemId());
            detail.setScore(BigDecimal.valueOf(item.getScore()));
            detail.setComment(item.getComment());
            detailMapper.insert(detail);

            // 智慧跟踪：扣分项或有评论 → 生成问题
            ScoreItem scoreItem = itemMap.get(item.getItemId());
            if (scoreItem != null) {
                boolean hasIssue = false;
                StringBuilder desc = new StringBuilder();

                if (item.getScore() < scoreItem.getMaxScore().doubleValue()) {
                    hasIssue = true;
                    desc.append("【").append(scoreItem.getName()).append("】")
                       .append("得分 ").append(item.getScore()).append("/").append(scoreItem.getMaxScore());
                }
                if (item.getComment() != null && !item.getComment().trim().isEmpty()) {
                    hasIssue = true;
                    if (desc.length() > 0) desc.append(" - ");
                    desc.append(item.getComment());
                }

                if (hasIssue) {
                    issueService.createIssue(tenantId, meetingId, detail.getId(),
                            scoreItem.getCategory(), desc.toString(), userId);
                }
            }
        }
    }

    public ScoreResultVO getScoreResult(Long meetingId, Long userId, String role) {
        Meeting meeting = meetingMapper.selectById(meetingId);
        if (meeting == null) {
            throw new RuntimeException("会议不存在");
        }
        dataScopeService.assertMeetingAccess(userId, role, meeting);

        List<ScoreRecord> records = recordMapper.selectList(
                new LambdaQueryWrapper<ScoreRecord>()
                        .eq(ScoreRecord::getMeetingId, meetingId)
                        .orderByDesc(ScoreRecord::getTotalScore)
        );

        List<ScoreItem> scoreItems = getScoreItems(null);
        Map<Long, ScoreItem> itemMap = scoreItems.stream()
                .collect(Collectors.toMap(ScoreItem::getId, s -> s));

        ScoreResultVO result = new ScoreResultVO();
        result.setMeetingId(meetingId);
        result.setMeetingTitle(meeting.getTitle());

        List<ScoreResultVO.ScoreRecordVO> recordVOs = new ArrayList<>();
        for (ScoreRecord record : records) {
            ScoreResultVO.ScoreRecordVO vo = new ScoreResultVO.ScoreRecordVO();
            vo.setUserId(record.getUserId());
            vo.setTotalScore(record.getTotalScore());
            vo.setSubmittedAt(record.getSubmittedAt());

            User user = userMapper.selectById(record.getUserId());
            if (user != null) {
                vo.setUsername(user.getUsername());
                vo.setRole(user.getRole());
            }

            List<ScoreDetail> details = detailMapper.selectList(
                    new LambdaQueryWrapper<ScoreDetail>()
                            .eq(ScoreDetail::getRecordId, record.getId())
            );

            List<ScoreResultVO.ScoreDetailVO> detailVOs = new ArrayList<>();
            for (ScoreDetail detail : details) {
                ScoreResultVO.ScoreDetailVO dvo = new ScoreResultVO.ScoreDetailVO();
                ScoreItem item = itemMap.get(detail.getItemId());
                if (item != null) {
                    dvo.setCategory(item.getCategory());
                    dvo.setItemName(item.getName());
                    dvo.setMaxScore(item.getMaxScore());
                }
                dvo.setScore(detail.getScore());
                dvo.setComment(detail.getComment());
                detailVOs.add(dvo);
            }
            vo.setDetails(detailVOs);
            recordVOs.add(vo);
        }
        result.setRecords(recordVOs);

        return result;
    }
}
