package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CompetitionReadinessAnalyzerTest {

    private final CompetitionReadinessAnalyzer analyzer = new CompetitionReadinessAnalyzer();

    @Test
    void prioritizesOpenHighRiskAndMissingRoadshowEvidence() {
        var snapshot = new CompetitionReadinessAnalyzer.Snapshot(
                List.of(new CompetitionReadinessAnalyzer.MaterialFact(
                        "PPT", "智慧养老项目路演稿.pptx", "项目方案", "APPROVED")),
                List.of("评估表", "照护记录", "安全演练"),
                List.of(new CompetitionReadinessAnalyzer.IssueFact(
                        "隐私授权证据不足", "缺少服务对象授权记录", "HIGH", "OPEN")),
                0,
                false
        );

        var gaps = analyzer.analyze(snapshot);

        assertEquals(3, gaps.size());
        assertEquals("review-risk", gaps.get(0).key());
        assertEquals("roadshow", gaps.get(1).key());
        assertTrue(gaps.stream().anyMatch(item -> item.title().contains("评估表")));
        assertTrue(gaps.stream().allMatch(item -> !item.source().isBlank()));
    }

    @Test
    void doesNotInventMaterialGapWhenTrackEvidenceExists() {
        var snapshot = new CompetitionReadinessAnalyzer.Snapshot(
                List.of(
                        new CompetitionReadinessAnalyzer.MaterialFact("PPT", "项目路演稿.pptx", "", "APPROVED"),
                        new CompetitionReadinessAnalyzer.MaterialFact("DOC", "老年人能力评估表", "含对象、时间和结果", "APPROVED"),
                        new CompetitionReadinessAnalyzer.MaterialFact("DOC", "照护记录", "过程记录", "APPROVED"),
                        new CompetitionReadinessAnalyzer.MaterialFact("VIDEO", "安全演练视频", "现场演练", "APPROVED"),
                        new CompetitionReadinessAnalyzer.MaterialFact("SCRIPT", "答辩问答库", "常见追问", "APPROVED")
                ),
                List.of("评估表", "照护记录", "安全演练"),
                List.of(),
                2,
                true
        );

        var gaps = analyzer.analyze(snapshot);

        assertTrue(gaps.isEmpty());
    }

    @Test
    void reportsUnapprovedPresentationAndQuestionBankFromRealMaterialState() {
        var snapshot = new CompetitionReadinessAnalyzer.Snapshot(
                List.of(new CompetitionReadinessAnalyzer.MaterialFact(
                        "PPT", "初稿.pptx", "", "PENDING_REVIEW")),
                List.of(),
                List.of(),
                1,
                true
        );

        var gaps = analyzer.analyze(snapshot);

        assertFalse(gaps.isEmpty());
        assertEquals("presentation", gaps.get(0).key());
        assertTrue(gaps.stream().anyMatch(item -> "qa-script".equals(item.key())));
        assertTrue(gaps.stream().noneMatch(item -> "roadshow".equals(item.key())));
    }
}
