package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class RoadshowMemoryAnalyzerTest {

    @Test
    void buildsMemorySummaryWithPriorIssuesAndFullScoreGap() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();
        List<Map<String, Object>> rows = List.of(
                Map.of(
                        "meetingId", 1L,
                        "meetingTitle", "第一次彩排",
                        "aiScore", 80,
                        "criticalIssues", List.of("关键功能演示不完整", "技术先进性证据不足"),
                        "improvementPriorities", List.of(Map.of("issue", "固化现场演示链路", "suggestion", "3分钟内稳定跑通核心流程"))
                ),
                Map.of(
                        "meetingId", 2L,
                        "meetingTitle", "第二次彩排",
                        "aiScore", 88,
                        "criticalIssues", List.of("关键技术缺少完整测试数据"),
                        "improvementPriorities", List.of(Map.of("issue", "补充关键技术测试数据", "suggestion", "展示性能、准确率、稳定性结果")),
                        "scoreCalibration", Map.of(
                                "original_score", 96,
                                "final_score", 88,
                                "skill_score", 50,
                                "technical_ceiling_score", 88,
                                "ceiling_reasons", List.of("现场演示跑通但缺少测试数据或性能结果，暂不进入95+。")
                        )
                )
        );

        Map<String, Object> summary = analyzer.buildSummary(rows);

        assertEquals(2, ((List<?>) summary.get("rounds")).size());
        assertEquals(8.0, summary.get("improvementDelta"));
        assertEquals("88", ((Map<?, ?>) summary.get("fullScoreGap")).get("ceilingScore").toString());
        assertFalse(((List<?>) summary.get("newIssues")).isEmpty());
        assertFalse(((List<?>) summary.get("trainingPlan")).isEmpty());
        assertTrue(((List<?>) summary.get("priorIssueReview")).size() >= 2);
    }

    @Test
    void marksSingleRoundMemoryAsWaitingForComparison() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();

        Map<String, Object> summary = analyzer.buildSummary(List.of(
                Map.of(
                        "meetingId", 7L,
                        "meetingTitle", "第一次正式路演",
                        "aiScore", 82,
                        "criticalIssues", List.of("现场演示链路需要更稳定")
                )
        ));

        assertEquals("SINGLE_ROUND", summary.get("memoryStatus"));
        assertEquals("已完成1轮AI评分，下一轮评分后会自动复检本轮扣分项。", summary.get("memoryStatusText"));
        assertTrue(((List<?>) summary.get("priorIssueReview")).isEmpty());
    }

    @Test
    void attachesEvidenceAnchorsToReviewedAndNewIssues() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();

        Map<String, Object> summary = analyzer.buildSummary(List.of(
                Map.of(
                        "meetingId", 1L,
                        "meetingTitle", "第一次彩排",
                        "aiScore", 80,
                        "criticalIssues", List.of(Map.of(
                                "title", "关键功能演示不完整",
                                "description", "没有看到端到端演示"
                        )),
                        "evidenceAnchors", List.of(
                                Map.of(
                                        "type", "transcript",
                                        "summary", "评委追问演示链路，团队未能完整跑通。",
                                        "sourceRef", "00:02:10-00:02:45"
                                )
                        )
                ),
                Map.of(
                        "meetingId", 2L,
                        "meetingTitle", "第二次彩排",
                        "aiScore", 88,
                        "criticalIssues", List.of(Map.of(
                                "title", "性能测试数据不足",
                                "description", "没有展示压测数据"
                        )),
                        "evidenceAnchors", List.of(
                                Map.of(
                                        "type", "screen_ocr",
                                        "summary", "PPT展示了核心功能运行画面，但没有性能数据表。",
                                        "sourceRef", "frame-128"
                                )
                        )
                )
        ));

        Map<?, ?> reviewed = (Map<?, ?>) ((List<?>) summary.get("priorIssueReview")).get(0);
        Map<?, ?> newIssue = (Map<?, ?>) ((List<?>) summary.get("newIssues")).get(0);
        List<?> reviewedAnchors = (List<?>) reviewed.get("evidenceAnchors");
        List<?> newAnchors = (List<?>) newIssue.get("evidenceAnchors");

        assertFalse(reviewedAnchors.isEmpty());
        assertEquals("transcript", ((Map<?, ?>) reviewedAnchors.get(0)).get("type"));
        assertEquals(1, ((Map<?, ?>) reviewedAnchors.get(0)).get("roundNo"));
        assertFalse(newAnchors.isEmpty());
        assertEquals("screen_ocr", ((Map<?, ?>) newAnchors.get(0)).get("type"));
        assertEquals(2, ((Map<?, ?>) newAnchors.get(0)).get("roundNo"));
    }

    @Test
    void doesNotRepeatFirstTranscriptAnchorForUnmatchedIssues() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();

        Map<String, Object> summary = analyzer.buildSummary(List.of(
                Map.of(
                        "meetingId", 1L,
                        "meetingTitle", "第一次彩排",
                        "aiScore", 70,
                        "criticalIssues", List.of("旧问题")
                ),
                Map.of(
                        "meetingId", 2L,
                        "meetingTitle", "第二次彩排",
                        "aiScore", 65,
                        "criticalIssues", List.of(
                                Map.of("title", "AI问答模块现场演示出现故障"),
                                Map.of("title", "路演时长过长")
                        ),
                        "evidenceAnchors", List.of(
                                Map.of(
                                        "type", "transcript_segment",
                                        "summary", "大家好。",
                                        "sourceRef", "00:00.4-00:01.2"
                                ),
                                Map.of(
                                        "type", "transcript_segment",
                                        "summary", "接下来展示团队分工。",
                                        "sourceRef", "00:10.0-00:15.0"
                                )
                        )
                )
        ));

        List<?> newIssues = (List<?>) summary.get("newIssues");
        assertEquals(2, newIssues.size());
        for (Object item : newIssues) {
            Map<?, ?> issue = (Map<?, ?>) item;
            List<?> anchors = (List<?>) issue.get("evidenceAnchors");
            assertTrue(anchors.isEmpty(), "不应把报告首个转写片段兜底复制到不匹配的问题上");
        }
    }

    @Test
    void treatsSemanticallySimilarIssueTitlesAsStillUnresolvedInsteadOfResolvedAndNew() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();

        Map<String, Object> summary = analyzer.buildSummary(List.of(
                Map.of(
                        "meetingId", 1L,
                        "meetingTitle", "第四轮彩排",
                        "aiScore", 64,
                        "criticalIssues", List.of(Map.of(
                                "title", "AI问答模块演示时出现严重技术故障，需要现场修改参数，影响了技能熟练度和专业性"
                        ))
                ),
                Map.of(
                        "meetingId", 2L,
                        "meetingTitle", "第五轮彩排",
                        "aiScore", 65,
                        "criticalIssues", List.of(Map.of(
                                "title", "AI问答模块演示时出现严重技术故障，团队承认用产品后 AI 机器的参数需要调整"
                        ))
                )
        ));

        List<?> prior = (List<?>) summary.get("priorIssueReview");
        List<?> newIssues = (List<?>) summary.get("newIssues");

        assertEquals("not_resolved", ((Map<?, ?>) prior.get(0)).get("status"));
        assertTrue(newIssues.isEmpty(), "同类问题不应同时出现在已改进和本轮新增扣分里");
    }

    @Test
    void matchesSimilarIssuesAcrossCompetitionTracksWithoutDomainKeywordWhitelist() {
        RoadshowMemoryAnalyzer analyzer = new RoadshowMemoryAnalyzer();

        Map<String, Object> summary = analyzer.buildSummary(List.of(
                Map.of(
                        "meetingId", 1L,
                        "meetingTitle", "无人机赛道第一轮",
                        "aiScore", 72,
                        "criticalIssues", List.of(Map.of(
                                "title", "无人机巡检航线在复杂风场下避障失败，无法稳定绕开障碍物"
                        ))
                ),
                Map.of(
                        "meetingId", 2L,
                        "meetingTitle", "无人机赛道第二轮",
                        "aiScore", 75,
                        "criticalIssues", List.of(
                                Map.of("title", "复杂风场中的无人机避障仍不稳定，绕障轨迹多次偏离"),
                                Map.of("title", "电池续航测试数据缺少第三方记录")
                        )
                )
        ));

        List<?> prior = (List<?>) summary.get("priorIssueReview");
        List<?> newIssues = (List<?>) summary.get("newIssues");

        assertEquals("not_resolved", ((Map<?, ?>) prior.get(0)).get("status"));
        assertEquals(1, newIssues.size());
        assertTrue(String.valueOf(((Map<?, ?>) newIssues.get(0)).get("title")).contains("电池续航"));
    }
}
