package com.orep.backend.service.roadshow.projection;

import java.util.ArrayList;
import java.util.List;

public final class NewsMvpFixtures {

    public static final String PAIN_TEXT = "成熟度误判导致损耗";

    private NewsMvpFixtures() {
    }

    public static ClaimCandidate pain() {
        return new ClaimCandidate(
                DeterministicSelector.PAIN_ID, PAIN_TEXT, PAIN_TEXT,
                "ready", true,
                RankFactors.of(0, 0, 0, "pain", 0), 0);
    }

    public static List<ClaimCandidate> happyNews() {
        List<ClaimCandidate> list = new ArrayList<>();
        list.add(news("N1", "某产区损耗通稿", 3, 2, 2, "loss", 30));
        list.add(news("N2", "同事件另一家媒体", 3, 2, 2, "loss", 30));
        list.add(news("N3", "设施农业政策动态", 1, 1, 0, "policy", 20));
        list.add(news("N4", "采后储运爆仓现场", 5, 5, 3, "storage", 10));
        list.add(irrelevant("N5", "无关宏观财经"));
        list.add(news("N6", "地方智慧农业试点", 1, 2, 2, "pilot", 15));
        list.add(expired("N7", "三年前旧闻"));
        list.add(news("N8", "分级误判导致损耗", 3, 3, 5, "misgrade", 12)
                .withBridge(DeterministicSelector.PAIN_ID));
        return list;
    }

    public static List<ClaimCandidate> empty() {
        return List.of();
    }

    public static List<ClaimCandidate> allLowQuality() {
        List<ClaimCandidate> list = new ArrayList<>();
        for (int i = 1; i <= 8; i++) {
            list.add(news("L" + i, "低质候选" + i, 1, 1, 0, "low", 5));
        }
        return list;
    }

    public static List<ClaimCandidate> n4Contradicts() {
        List<ClaimCandidate> list = happyNews();
        for (ClaimCandidate c : list) {
            if ("N4".equals(c.stableId())) {
                c.withContradict("NX");
            }
        }
        list.add(news("NX", "与 N4 冲突的记录", 2, 2, 1, "storage", 9));
        return list;
    }

    private static ClaimCandidate news(
            String id, String fact, int impact, int ostensible, int bridge, String cluster, int freshness
    ) {
        return new ClaimCandidate(
                id, fact, fact, "ready", true,
                RankFactors.of(impact, ostensible, bridge, cluster, freshness), 0);
    }

    private static ClaimCandidate irrelevant(String id, String fact) {
        return new ClaimCandidate(
                id, fact, fact, "ready", true,
                new RankFactors(0, 0, 0, "macro", 40, false, true, false), 0);
    }

    private static ClaimCandidate expired(String id, String fact) {
        return new ClaimCandidate(
                id, fact, fact, "ready", true,
                new RankFactors(3, 3, 3, "old", 0, true, false, false), 0);
    }
}
