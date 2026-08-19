package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class StatisticsVO {
    private Long meetingCount;
    private Double avgScore;
    private Long issuesTotal;
    private Long issuesResolved;
    private String scopeLabel;
    private String rangeLabel;
    private Map<String, Object> scoreTrend;
    private List<DimensionStat> dimensionStats;
    private List<IssueCategoryStat> issueCategoryRanking;
    private List<RecentMeetingStat> recentMeetings;
    private ClosureAnalysis closureAnalysis;
    private PreparationInsight preparationInsight;

    @Data
    public static class DimensionStat {
        private String category;
        private BigDecimal score;
        private BigDecimal maxScore;
        private Double rate;
        private Long issueCount;
    }

    @Data
    public static class IssueCategoryStat {
        private String category;
        private Long total;
        private Long resolved;
        private Long pending;
    }

    @Data
    public static class RecentMeetingStat {
        private Long meetingId;
        private String title;
        private String status;
        private String date;
        private Double totalScore;
        private Long issueCount;
        private Long resolvedIssueCount;
        private Double improvementFromPrevious;
        private Map<String, Double> dimensionRates;
    }

    @Data
    public static class ClosureAnalysis {
        private Long resolvedCount;
        private Double avgResolveDays;
        private Long stalePendingCount;
        private Double latestImprovement;
        private List<RepeatIssueStat> repeatIssues;
        private List<String> nextActions;
    }

    @Data
    public static class RepeatIssueStat {
        private String keyword;
        private Long count;
        private Long pending;
    }

    @Data
    public static class PreparationInsight {
        private String stage;
        private String summary;
        private List<String> futureSignals;
    }
}
