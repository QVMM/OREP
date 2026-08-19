package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.StatisticsVO;
import com.orep.backend.entity.*;
import com.orep.backend.mapper.*;
import com.orep.backend.security.DataScopeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class StatisticsService {

    @Autowired
    private MeetingMapper meetingMapper;
    @Autowired
    private MeetingParticipantMapper participantMapper;
    @Autowired
    private ScoreRecordMapper recordMapper;
    @Autowired
    private ScoreDetailMapper detailMapper;
    @Autowired
    private ScoreItemMapper itemMapper;
    @Autowired
    private IssueMapper issueMapper;
    @Autowired
    private DataScopeService dataScopeService;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    public StatisticsVO getOverview(Long tenantId, Long userId, String role, Integer days,
                                    LocalDate startDate, LocalDate endDate, String scope) {
        DateWindow window = resolveWindow(days, startDate, endDate);
        // scope=team must stay team-membership scoped (not whole-tenant teacher view).
        boolean teamScope = isTeamScope(scope);
        boolean participantScope = !teamScope && (
                isParticipantScope(scope) || !dataScopeService.canUseOrgDashboardScope(role));
        List<Meeting> meetings = teamScope
                ? listTeamMeetings(tenantId, userId, window)
                : listMeetings(tenantId, userId, role, window, participantScope);
        List<Long> meetingIds = meetings.stream().map(Meeting::getId).toList();

        List<ScoreRecord> records = listScoreRecords(tenantId, meetingIds);
        List<Issue> issues = listIssues(tenantId, meetingIds);

        StatisticsVO vo = new StatisticsVO();
        vo.setScopeLabel(teamScope ? "我的队伍视角" : (participantScope ? "个人参与视角" : resolveScopeLabel(role)));
        vo.setRangeLabel(window.label());
        vo.setMeetingCount((long) meetings.size());
        vo.setAvgScore(round(records.stream().mapToDouble(r -> r.getTotalScore().doubleValue()).average().orElse(0)));
        vo.setIssuesTotal((long) issues.size());
        vo.setIssuesResolved(issues.stream().filter(i -> Objects.equals(i.getStatus(), 1)).count());
        vo.setScoreTrend(buildScoreTrend(meetings, records));
        vo.setDimensionStats(buildDimensionStats(records, issues));
        vo.setIssueCategoryRanking(buildIssueCategoryRanking(issues));
        vo.setRecentMeetings(buildRecentMeetings(meetings, records, issues));
        vo.setClosureAnalysis(buildClosureAnalysis(issues, vo.getRecentMeetings()));
        vo.setPreparationInsight(buildPreparationInsight());
        return vo;
    }

    private List<Meeting> listMeetings(Long tenantId, Long userId, String role, DateWindow window, boolean participantScope) {
        LambdaQueryWrapper<Meeting> wrapper = new LambdaQueryWrapper<Meeting>()
                .eq(Meeting::getTenantId, tenantId)
                .orderByAsc(Meeting::getCreatedAt);
        if (window.start() != null) wrapper.ge(Meeting::getCreatedAt, window.start());
        if (window.end() != null) wrapper.lt(Meeting::getCreatedAt, window.end());
        if (participantScope) {
            List<Long> participantMeetingIds = participantMapper.selectList(
                            new LambdaQueryWrapper<MeetingParticipant>()
                                    .eq(MeetingParticipant::getUserId, userId)
                    )
                    .stream()
                    .map(MeetingParticipant::getMeetingId)
                    .filter(Objects::nonNull)
                    .distinct()
                    .toList();
            if (participantMeetingIds.isEmpty()) {
                return new ArrayList<>();
            }
            wrapper.in(Meeting::getId, participantMeetingIds);
        } else {
            List<Long> scopedMeetingIds = dataScopeService.accessibleMeetingIds(tenantId, userId, role);
            if (scopedMeetingIds.isEmpty()) {
                return new ArrayList<>();
            }
            wrapper.in(Meeting::getId, scopedMeetingIds);
        }
        return meetingMapper.selectList(wrapper);
    }

    private boolean isParticipantScope(String scope) {
        if (scope == null || scope.isBlank()) return false;
        String normalized = scope.trim().toLowerCase(Locale.ROOT);
        return "participant".equals(normalized) || "mine".equals(normalized) || "personal".equals(normalized);
    }

    private boolean isTeamScope(String scope) {
        if (scope == null || scope.isBlank()) return false;
        String normalized = scope.trim().toLowerCase(Locale.ROOT);
        return "team".equals(normalized) || "teams".equals(normalized) || "my_team".equals(normalized);
    }

    /**
     * Meetings bound to teams where the user is a member or mentor only.
     */
    private List<Meeting> listTeamMeetings(Long tenantId, Long userId, DateWindow window) {
        List<Long> meetingIds = jdbcTemplate.query("""
                SELECT DISTINCT m.id
                FROM meeting m
                INNER JOIN project_roadshow_binding b ON b.meeting_id = m.id
                WHERE m.tenant_id = ?
                  AND (
                    EXISTS (
                        SELECT 1 FROM project_team_member tm
                        WHERE tm.team_id = b.team_id AND tm.user_id = ?
                    )
                    OR EXISTS (
                        SELECT 1 FROM project_team t
                        WHERE t.id = b.team_id AND t.mentor_id = ?
                    )
                  )
                """,
                (rs, rowNum) -> rs.getLong(1),
                tenantId, userId, userId);
        if (meetingIds.isEmpty()) {
            return new ArrayList<>();
        }
        LambdaQueryWrapper<Meeting> wrapper = new LambdaQueryWrapper<Meeting>()
                .eq(Meeting::getTenantId, tenantId)
                .in(Meeting::getId, meetingIds)
                .orderByAsc(Meeting::getCreatedAt);
        if (window.start() != null) wrapper.ge(Meeting::getCreatedAt, window.start());
        if (window.end() != null) wrapper.lt(Meeting::getCreatedAt, window.end());
        return meetingMapper.selectList(wrapper);
    }

    private List<ScoreRecord> listScoreRecords(Long tenantId, List<Long> meetingIds) {
        if (meetingIds.isEmpty()) return new ArrayList<>();
        return recordMapper.selectList(new LambdaQueryWrapper<ScoreRecord>()
                .eq(ScoreRecord::getTenantId, tenantId)
                .in(ScoreRecord::getMeetingId, meetingIds));
    }

    private List<Issue> listIssues(Long tenantId, List<Long> meetingIds) {
        LambdaQueryWrapper<Issue> wrapper = new LambdaQueryWrapper<Issue>()
                .eq(Issue::getTenantId, tenantId)
                .orderByDesc(Issue::getCreatedAt);
        if (meetingIds.isEmpty()) return new ArrayList<>();
        wrapper.in(Issue::getMeetingId, meetingIds);
        return issueMapper.selectList(wrapper);
    }

    private Map<String, Object> buildScoreTrend(List<Meeting> meetings, List<ScoreRecord> records) {
        Map<Long, Double> avgByMeeting = records.stream()
                .collect(Collectors.groupingBy(
                        ScoreRecord::getMeetingId,
                        LinkedHashMap::new,
                        Collectors.averagingDouble(r -> r.getTotalScore().doubleValue())
                ));

        List<String> dates = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        List<Double> scores = new ArrayList<>();
        List<Long> meetingIds = new ArrayList<>();
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("MM-dd");

        for (Meeting meeting : meetings) {
            labels.add(meeting.getTitle());
            meetingIds.add(meeting.getId());
            LocalDateTime time = Optional.ofNullable(meeting.getStartTime()).orElse(meeting.getCreatedAt());
            dates.add(time != null ? time.format(fmt) : "未开始");
            scores.add(round(avgByMeeting.getOrDefault(meeting.getId(), 0.0)));
        }

        Map<String, Object> trend = new LinkedHashMap<>();
        trend.put("dates", dates);
        trend.put("labels", labels);
        trend.put("scores", scores);
        trend.put("meetingIds", meetingIds);
        return trend;
    }

    private List<StatisticsVO.DimensionStat> buildDimensionStats(List<ScoreRecord> records, List<Issue> issues) {
        if (records.isEmpty()) return new ArrayList<>();

        List<Long> recordIds = records.stream().map(ScoreRecord::getId).toList();
        List<ScoreDetail> details = detailMapper.selectList(new LambdaQueryWrapper<ScoreDetail>()
                .in(ScoreDetail::getRecordId, recordIds));
        if (details.isEmpty()) return new ArrayList<>();

        Map<Long, ScoreItem> itemMap = itemMapper.selectList(new LambdaQueryWrapper<ScoreItem>())
                .stream()
                .collect(Collectors.toMap(ScoreItem::getId, Function.identity()));
        Map<String, Long> issueCountByCategory = issues.stream()
                .collect(Collectors.groupingBy(i -> normalizeCategory(i.getCategory()), Collectors.counting()));

        Map<String, BigDecimal> scoreByCategory = new LinkedHashMap<>();
        Map<String, BigDecimal> maxByCategory = new LinkedHashMap<>();

        for (ScoreDetail detail : details) {
            ScoreItem item = itemMap.get(detail.getItemId());
            if (item == null) continue;
            String category = normalizeCategory(item.getCategory());
            scoreByCategory.merge(category, safe(detail.getScore()), BigDecimal::add);
            maxByCategory.merge(category, safe(item.getMaxScore()), BigDecimal::add);
        }

        return scoreByCategory.keySet().stream().map(category -> {
            BigDecimal score = scoreByCategory.getOrDefault(category, BigDecimal.ZERO);
            BigDecimal max = maxByCategory.getOrDefault(category, BigDecimal.ZERO);
            StatisticsVO.DimensionStat stat = new StatisticsVO.DimensionStat();
            stat.setCategory(category);
            stat.setScore(score.setScale(2, RoundingMode.HALF_UP));
            stat.setMaxScore(max.setScale(2, RoundingMode.HALF_UP));
            stat.setRate(max.compareTo(BigDecimal.ZERO) > 0
                    ? round(score.multiply(BigDecimal.valueOf(100)).divide(max, 4, RoundingMode.HALF_UP).doubleValue())
                    : 0.0);
            stat.setIssueCount(issueCountByCategory.getOrDefault(category, 0L));
            return stat;
        }).sorted(Comparator.comparing(StatisticsVO.DimensionStat::getRate)).toList();
    }

    private List<StatisticsVO.IssueCategoryStat> buildIssueCategoryRanking(List<Issue> issues) {
        Map<String, List<Issue>> grouped = issues.stream()
                .collect(Collectors.groupingBy(i -> normalizeCategory(i.getCategory()), LinkedHashMap::new, Collectors.toList()));
        return grouped.entrySet().stream().map(entry -> {
            StatisticsVO.IssueCategoryStat stat = new StatisticsVO.IssueCategoryStat();
            stat.setCategory(entry.getKey());
            stat.setTotal((long) entry.getValue().size());
            stat.setResolved(entry.getValue().stream().filter(i -> Objects.equals(i.getStatus(), 1)).count());
            stat.setPending(stat.getTotal() - stat.getResolved());
            return stat;
        }).sorted(Comparator.comparing(StatisticsVO.IssueCategoryStat::getTotal).reversed()).limit(8).toList();
    }

    private List<StatisticsVO.RecentMeetingStat> buildRecentMeetings(List<Meeting> meetings, List<ScoreRecord> records, List<Issue> issues) {
        Map<Long, List<ScoreRecord>> recordsByMeeting = records.stream()
                .collect(Collectors.groupingBy(ScoreRecord::getMeetingId));
        Map<Long, List<Issue>> issuesByMeeting = issues.stream()
                .collect(Collectors.groupingBy(Issue::getMeetingId));

        List<Meeting> recent = meetings.stream()
                .sorted(Comparator.comparing((Meeting m) -> Optional.ofNullable(m.getStartTime()).orElse(m.getCreatedAt()),
                        Comparator.nullsLast(Comparator.naturalOrder())).reversed())
                .limit(5)
                .toList();

        List<StatisticsVO.RecentMeetingStat> result = new ArrayList<>();
        Double previousScore = null;
        for (int i = recent.size() - 1; i >= 0; i--) {
            Meeting meeting = recent.get(i);
            List<ScoreRecord> meetingRecords = recordsByMeeting.getOrDefault(meeting.getId(), List.of());
            Double totalScore = meetingRecords.isEmpty()
                    ? null
                    : meetingRecords.stream().mapToDouble(r -> r.getTotalScore().doubleValue()).average().orElse(0);
            List<Issue> meetingIssues = issuesByMeeting.getOrDefault(meeting.getId(), List.of());

            StatisticsVO.RecentMeetingStat stat = new StatisticsVO.RecentMeetingStat();
            stat.setMeetingId(meeting.getId());
            stat.setTitle(meeting.getTitle());
            stat.setStatus(meeting.getStatus());
            stat.setDate(formatDate(Optional.ofNullable(meeting.getStartTime()).orElse(meeting.getCreatedAt())));
            stat.setTotalScore(totalScore == null ? null : round(totalScore));
            stat.setIssueCount((long) meetingIssues.size());
            stat.setResolvedIssueCount(meetingIssues.stream().filter(issue -> Objects.equals(issue.getStatus(), 1)).count());
            if (previousScore != null && totalScore != null) {
                stat.setImprovementFromPrevious(round(totalScore - previousScore));
            } else {
                stat.setImprovementFromPrevious(null);
            }
            stat.setDimensionRates(buildMeetingDimensionRates(meetingRecords));
            if (totalScore != null) {
                previousScore = totalScore;
            }
            result.add(0, stat);
        }
        return result;
    }

    private Map<String, Double> buildMeetingDimensionRates(List<ScoreRecord> records) {
        if (records.isEmpty()) return new LinkedHashMap<>();
        List<Long> recordIds = records.stream().map(ScoreRecord::getId).toList();
        List<ScoreDetail> details = detailMapper.selectList(new LambdaQueryWrapper<ScoreDetail>()
                .in(ScoreDetail::getRecordId, recordIds));
        Map<Long, ScoreItem> itemMap = itemMapper.selectList(new LambdaQueryWrapper<ScoreItem>())
                .stream()
                .collect(Collectors.toMap(ScoreItem::getId, Function.identity()));

        Map<String, BigDecimal> scores = new LinkedHashMap<>();
        Map<String, BigDecimal> maxes = new LinkedHashMap<>();
        for (ScoreDetail detail : details) {
            ScoreItem item = itemMap.get(detail.getItemId());
            if (item == null) continue;
            String category = normalizeCategory(item.getCategory());
            scores.merge(category, safe(detail.getScore()), BigDecimal::add);
            maxes.merge(category, safe(item.getMaxScore()), BigDecimal::add);
        }

        Map<String, Double> rates = new LinkedHashMap<>();
        for (String category : scores.keySet()) {
            BigDecimal max = maxes.getOrDefault(category, BigDecimal.ZERO);
            rates.put(category, max.compareTo(BigDecimal.ZERO) > 0
                    ? round(scores.get(category).multiply(BigDecimal.valueOf(100)).divide(max, 4, RoundingMode.HALF_UP).doubleValue())
                    : 0.0);
        }
        return rates;
    }

    private StatisticsVO.ClosureAnalysis buildClosureAnalysis(List<Issue> issues, List<StatisticsVO.RecentMeetingStat> recentMeetings) {
        StatisticsVO.ClosureAnalysis analysis = new StatisticsVO.ClosureAnalysis();
        List<Issue> resolved = issues.stream()
                .filter(i -> Objects.equals(i.getStatus(), 1) && i.getResolvedAt() != null && i.getCreatedAt() != null)
                .toList();
        analysis.setResolvedCount((long) resolved.size());
        analysis.setAvgResolveDays(round(resolved.stream()
                .mapToDouble(i -> Duration.between(i.getCreatedAt(), i.getResolvedAt()).toHours() / 24.0)
                .average().orElse(0)));
        LocalDateTime staleLine = LocalDateTime.now().minusDays(7);
        analysis.setStalePendingCount(issues.stream()
                .filter(i -> Objects.equals(i.getStatus(), 0) && i.getCreatedAt() != null && i.getCreatedAt().isBefore(staleLine))
                .count());
        analysis.setRepeatIssues(buildRepeatIssues(issues));
        analysis.setLatestImprovement(recentMeetings.stream()
                .map(StatisticsVO.RecentMeetingStat::getImprovementFromPrevious)
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null));
        analysis.setNextActions(buildNextActions(issues, analysis.getRepeatIssues(), recentMeetings));
        return analysis;
    }

    private List<StatisticsVO.RepeatIssueStat> buildRepeatIssues(List<Issue> issues) {
        Map<String, List<Issue>> grouped = issues.stream()
                .collect(Collectors.groupingBy(i -> issueKeyword(i.getDescription(), i.getCategory())));
        return grouped.entrySet().stream()
                .filter(e -> e.getValue().size() >= 2)
                .map(e -> {
                    StatisticsVO.RepeatIssueStat stat = new StatisticsVO.RepeatIssueStat();
                    stat.setKeyword(e.getKey());
                    stat.setCount((long) e.getValue().size());
                    stat.setPending(e.getValue().stream().filter(i -> Objects.equals(i.getStatus(), 0)).count());
                    return stat;
                })
                .sorted(Comparator.comparing(StatisticsVO.RepeatIssueStat::getCount).reversed())
                .limit(5)
                .toList();
    }

    private List<String> buildNextActions(List<Issue> issues, List<StatisticsVO.RepeatIssueStat> repeatIssues,
                                          List<StatisticsVO.RecentMeetingStat> recentMeetings) {
        List<String> actions = new ArrayList<>();
        Optional<StatisticsVO.IssueCategoryStat> topPending = buildIssueCategoryRanking(issues).stream()
                .filter(i -> i.getPending() > 0)
                .findFirst();
        topPending.ifPresent(stat -> actions.add("优先处理「" + stat.getCategory() + "」下的 " + stat.getPending() + " 个待解决问题。"));
        repeatIssues.stream().findFirst().ifPresent(stat ->
                actions.add("复盘反复出现的「" + stat.getKeyword() + "」，下一次路演前做一次针对性演练。"));
        recentMeetings.stream().filter(m -> m.getTotalScore() != null && m.getTotalScore() > 0).findFirst().ifPresent(meeting -> {
            if (meeting.getImprovementFromPrevious() != null && meeting.getImprovementFromPrevious() < 0) {
                actions.add("最近一次分数回落 " + Math.abs(meeting.getImprovementFromPrevious()) + " 分，建议先对照会议详情恢复失分项。");
            }
        });
        if (actions.isEmpty()) {
            actions.add("继续完成一次带评分的路演，系统会自动生成更具体的改进清单。");
        }
        return actions.stream().limit(3).toList();
    }

    private StatisticsVO.PreparationInsight buildPreparationInsight() {
        StatisticsVO.PreparationInsight insight = new StatisticsVO.PreparationInsight();
        insight.setStage("reserved");
        insight.setSummary("PPT 质量、评分点覆盖和 AI 音视频画像将在后续版本接入，形成准备质量到现场表现再到评分结果的链路。");
        insight.setFutureSignals(List.of("PPT评分点覆盖率", "实操演示完整度", "AI表达画像", "音视频融合趋势"));
        return insight;
    }

    private DateWindow resolveWindow(Integer days, LocalDate startDate, LocalDate endDate) {
        if (startDate != null || endDate != null) {
            LocalDateTime start = startDate == null ? null : startDate.atStartOfDay();
            LocalDateTime end = endDate == null ? null : endDate.plusDays(1).atStartOfDay();
            return new DateWindow(start, end, "自定义范围");
        }
        if (days != null && days > 0) {
            return new DateWindow(LocalDateTime.now().minusDays(days), LocalDateTime.now().plusSeconds(1), "近 " + days + " 天");
        }
        return new DateWindow(null, null, "全部数据");
    }

    private String normalizeCategory(String category) {
        if (category == null || category.isBlank()) return "未分类";
        String clean = category.replaceAll("（.*?）", "").replaceAll("\\(.*?\\)", "").trim();
        clean = clean.replaceFirst("^[一二三四五六七八九十]+、", "");
        return clean.isBlank() ? "未分类" : clean;
    }

    private String issueKeyword(String description, String category) {
        String text = description == null || description.isBlank() ? normalizeCategory(category) : description;
        text = text.replaceAll("【|】", "").replaceAll("\\s+", "");
        int slash = text.indexOf("得分");
        if (slash > 0) text = text.substring(0, slash);
        return text.length() > 14 ? text.substring(0, 14) : text;
    }

    private String resolveScopeLabel(String role) {
        if ("ADMIN".equals(role)) return "平台全局";
        if ("SCHOOL_ADMIN".equals(role)) return "学校全局";
        if ("TEACHER".equals(role)) return "本院/校视角";
        if ("EXPERT".equals(role)) return "教学评审视角";
        return "个人参与视角";
    }

    private String formatDate(LocalDateTime time) {
        return time == null ? "-" : time.format(DateTimeFormatter.ofPattern("MM-dd HH:mm"));
    }

    private BigDecimal safe(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private double round(double value) {
        return BigDecimal.valueOf(value).setScale(2, RoundingMode.HALF_UP).doubleValue();
    }

    private record DateWindow(LocalDateTime start, LocalDateTime end, String label) {}
}
