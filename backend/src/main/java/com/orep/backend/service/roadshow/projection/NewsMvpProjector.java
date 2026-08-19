package com.orep.backend.service.roadshow.projection;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 一次 run：按需建 Assessment，两页顺序投影。不发明句子，不接 LLM。
 */
public final class NewsMvpProjector {

    public static final String RUBRIC = "实用性";
    public static final String JUDGE_UNDERSTOOD = "评委已理解";

    public record RunResult(
            long runId,
            List<ProjectionPageResult> pages,
            List<AssessmentRecord> assessments
    ) {
        public ProjectionPageResult page(int index) {
            return pages.stream().filter(p -> p.pageIndex() == index).findFirst().orElseThrow();
        }
    }

    private NewsMvpProjector() {
    }

    public static RunResult project(long runId, List<ClaimCandidate> pool, String painProposition) {
        return project(runId, pool, painProposition, PageIntentSpec.urgency(), PageIntentSpec.bridge());
    }

    public static RunResult project(
            long runId,
            List<ClaimCandidate> pool,
            String painProposition,
            PageIntentSpec first,
            PageIntentSpec second
    ) {
        for (ClaimCandidate c : pool) {
            int strength = Math.min(3, Math.max(0, c.factors().impact() / 2 + 1));
            int ver = c.factors().ostensible() >= 4 ? 1 : 0;
            c.setChi(defaultMu(strength, ver));
        }
        Map<String, AssessmentRecord> assessments = new LinkedHashMap<>();
        List<ProjectionPageResult> pages = new ArrayList<>();
        Set<String> selected = new HashSet<>();
        Set<String> clusters = new HashSet<>();

        pages.add(projectOne(runId, first, pool, painProposition, selected, clusters, assessments));
        pages.add(projectOne(runId, second, pool, painProposition, selected, clusters, assessments));
        return new RunResult(runId, pages, List.copyOf(assessments.values()));
    }

    private static ProjectionPageResult projectOne(
            long runId,
            PageIntentSpec intent,
            List<ClaimCandidate> pool,
            String painProposition,
            Set<String> selected,
            Set<String> clusters,
            Map<String, AssessmentRecord> assessments
    ) {
        DeterministicSelector.Outcome out = DeterministicSelector.select(intent, pool, selected, clusters);
        for (ClaimCandidate c : out.hardPassed()) {
            ensureAssessment(runId, intent, c, assessments);
        }

        if (out.selected() == null) {
            return new ProjectionPageResult(
                    intent.pageIndex(), intent.id(), intent.role(),
                    List.of(), "", "", null,
                    false, "pending", "blocked",
                    out.hardPassed().isEmpty() ? "empty_or_filtered" : "required_unmet",
                    out.decision().toMap()
            );
        }

        ClaimCandidate pick = out.selected();
        TaskExpression.Text expr = TaskExpression.render(intent, pick, painProposition);
        boolean hard = hardSuccess(intent, pick, selected);
        selected.add(pick.stableId());
        clusters.add(pick.factors().cluster());

        return new ProjectionPageResult(
                intent.pageIndex(), intent.id(), intent.role(),
                List.of(pick.stableId()),
                expr.slide(), expr.speaking(), expr.taskFocus(),
                hard, "pending", "ok", null,
                out.decision().toMap()
        );
    }

    private static void ensureAssessment(
            long runId,
            PageIntentSpec intent,
            ClaimCandidate c,
            Map<String, AssessmentRecord> assessments
    ) {
        for (String rubric : intent.relatedRubrics()) {
            String key = c.stableId() + "|" + rubric;
            if (assessments.containsKey(key)) continue;
            int strength = Math.min(3, Math.max(0, c.factors().impact() / 2 + 1));
            int ver = c.factors().ostensible() >= 4 ? 1 : 0;
            assessments.put(key, new AssessmentRecord(
                    c.stableId(), rubric, strength, ver, c.chi(),
                    runId, intent.id(), rubric
            ));
        }
    }

    static int defaultMu(int strength, int ver) {
        int[][] table = {
                {0, 0, 1},
                {1, 1, 2},
                {2, 3, 4},
                {4, 4, 5}
        };
        return table[clamp(strength, 0, 3)][clamp(ver, 0, 2)];
    }

    private static int clamp(int v, int lo, int hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    static boolean hardSuccess(PageIntentSpec intent, ClaimCandidate pick, Set<String> alreadySelected) {
        if (intent.forbidTech() && pick.factors().tech()) return false;
        if ("bridge".equals(intent.role())) {
            return pick.bridgesTo().contains(DeterministicSelector.PAIN_ID)
                    && !alreadySelected.contains(pick.stableId());
        }
        return true;
    }

    public static long assessmentCountFor(RunResult run, String stableId) {
        return run.assessments().stream().filter(a -> a.claimStableId().equals(stableId)).count();
    }
}
