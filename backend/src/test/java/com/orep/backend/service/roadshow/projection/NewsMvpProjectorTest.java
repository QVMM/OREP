package com.orep.backend.service.roadshow.projection;

import org.junit.jupiter.api.Test;

import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class NewsMvpProjectorTest {

    @Test
    void happyPathSelectsN4ThenN8() {
        NewsMvpProjector.RunResult run = projectHappy();
        assertEquals(List.of("N4"), run.page(4).selectedStableIds());
        assertEquals(List.of("N8"), run.page(5).selectedStableIds());
        assertEquals("urgency", run.page(4).taskFocus());
        assertEquals("bridge", run.page(5).taskFocus());
        assertTrue(run.page(4).slideText().contains("当下"));
        assertTrue(run.page(5).slideText().contains(NewsMvpFixtures.PAIN_TEXT));
        assertTrue(run.page(4).hardSuccessPass());
        assertTrue(run.page(5).hardSuccessPass());
        assertEquals("pending", run.page(4).softSuccessStatus());
    }

    @Test
    void sameInputSameSelection() {
        NewsMvpProjector.RunResult a = projectHappy();
        NewsMvpProjector.RunResult b = projectHappy();
        assertEquals(a.page(4).selectedStableIds(), b.page(4).selectedStableIds());
        assertEquals(a.page(5).selectedStableIds(), b.page(5).selectedStableIds());
        assertEquals(a.page(4).decision(), b.page(4).decision());
    }

    @Test
    void t1SlideFactsComeFromSelectedClaim() {
        NewsMvpProjector.RunResult run = projectHappy();
        ClaimCandidate n4 = find(NewsMvpFixtures.happyNews(), "N4");
        ClaimCandidate n8 = find(NewsMvpFixtures.happyNews(), "N8");
        assertTrue(run.page(4).slideText().contains(n4.extractedFact())
                || run.page(4).speaking().contains(n4.extractedFact()));
        assertFalse(run.page(4).slideText().contains(n8.extractedFact()));
        assertFalse(run.page(4).speaking().contains("采用人工智能"));
    }

    @Test
    void t2DifferentIntentDifferentSelection() {
        NewsMvpProjector.RunResult run = projectHappy();
        assertNotEquals(run.page(4).selectedStableIds(), run.page(5).selectedStableIds());
        assertNotEquals(run.page(4).taskFocus(), run.page(5).taskFocus());
    }

    @Test
    void t3ChangingOnlyRoleChangesSelection() {
        List<ClaimCandidate> pool = NewsMvpFixtures.happyNews();
        DeterministicSelector.Outcome urgency = DeterministicSelector.select(
                PageIntentSpec.urgency(), pool, Set.of(), Set.of());
        DeterministicSelector.Outcome bridge = DeterministicSelector.select(
                PageIntentSpec.bridge(), pool, Set.of(), Set.of());
        assertEquals("N4", urgency.selected().stableId());
        assertEquals("N8", bridge.selected().stableId());
    }

    @Test
    void sameClaimDifferentRoleChangesTaskFocusNotJustPunctuation() {
        ClaimCandidate n4 = find(NewsMvpFixtures.happyNews(), "N4");
        TaskExpression.Text u = TaskExpression.render(PageIntentSpec.urgency(), n4, NewsMvpFixtures.PAIN_TEXT);
        TaskExpression.Text b = TaskExpression.render(PageIntentSpec.bridge(), n4, NewsMvpFixtures.PAIN_TEXT);
        assertEquals("urgency", u.taskFocus());
        assertEquals("bridge", b.taskFocus());
        assertTrue(u.slide().contains("当下"));
        assertTrue(b.slide().contains(NewsMvpFixtures.PAIN_TEXT));
        assertNotEquals(stripPunct(u.slide()), stripPunct(b.slide()));
    }

    @Test
    void t4ReasonsUseOnlyTraceFactors() {
        NewsMvpProjector.RunResult run = projectHappy();
        assertReasonsFromTrace(run.page(4));
        assertReasonsFromTrace(run.page(5));
    }

    @Test
    void t5InterfaceKeepsTopN() {
        Map<String, Object> d = projectHappy().page(4).decision();
        assertTrue(((List<?>) d.get("runner_up")).size() <= 2);
        assertTrue(((List<?>) d.get("eliminated_key")).size() <= 2);
        assertTrue(((List<?>) d.get("reserved_next")).size() <= 1);
        assertTrue(((List<?>) d.get("reasons")).size() <= 4);
    }

    @Test
    void t6AssessmentsOnlyForCandidatesNeverForPainOrFiltered() {
        NewsMvpProjector.RunResult run = projectHappy();
        Set<String> assessed = new HashSet<>();
        for (AssessmentRecord a : run.assessments()) {
            assessed.add(a.claimStableId());
            assertEquals("实用性", a.createdForRubricId());
            assertFalse(a.createdByPageIntentId().isBlank());
        }
        assertFalse(assessed.contains(DeterministicSelector.PAIN_ID));
        assertEquals(0, NewsMvpProjector.assessmentCountFor(run, "N5"));
        assertEquals(0, NewsMvpProjector.assessmentCountFor(run, "N7"));
        assertEquals(0, NewsMvpProjector.assessmentCountFor(run, DeterministicSelector.PAIN_ID));
        assertTrue(assessed.contains("N4"));
        int candidateCap = 6;
        assertTrue(run.assessments().size() <= candidateCap);
    }

    @Test
    void t7EmptyLibraryBlocksAndInventNothing() {
        NewsMvpProjector.RunResult run = NewsMvpProjector.project(
                2L, NewsMvpFixtures.empty(), NewsMvpFixtures.PAIN_TEXT);
        assertTrue(run.page(4).blocked());
        assertTrue(run.page(5).blocked());
        assertEquals("", run.page(4).slideText());
        assertEquals("", run.page(4).speaking());
        assertTrue(run.page(4).selectedStableIds().isEmpty());
    }

    @Test
    void negBAllLowQualityBlocks() {
        NewsMvpProjector.RunResult run = NewsMvpProjector.project(
                3L, NewsMvpFixtures.allLowQuality(), NewsMvpFixtures.PAIN_TEXT);
        assertTrue(run.page(4).blocked());
        assertEquals("required_unmet", run.page(4).blockReason());
        assertEquals("", run.page(4).slideText());
    }

    @Test
    void negCCannotSneakSelectContradictingN4() {
        NewsMvpProjector.RunResult run = NewsMvpProjector.project(
                4L, NewsMvpFixtures.n4Contradicts(), NewsMvpFixtures.PAIN_TEXT);
        assertFalse(run.page(4).selectedStableIds().contains("N4"));
        if (!run.page(4).blocked()) {
            assertNotEquals(List.of("N4"), run.page(4).selectedStableIds());
        }
    }

    @Test
    void t8NeverClaimsJudgeUnderstood() {
        NewsMvpProjector.RunResult run = projectHappy();
        String blob = run.page(4).slideText() + run.page(4).speaking()
                + run.page(5).slideText() + run.page(5).speaking()
                + run.page(4).softSuccessStatus() + run.page(5).softSuccessStatus()
                + run.page(4).decision() + run.page(5).decision();
        assertFalse(blob.contains(NewsMvpProjector.JUDGE_UNDERSTOOD));
        assertFalse(blob.contains("AI 已经理解叙事"));
        assertEquals("pending", run.page(5).softSuccessStatus());
    }

    @Test
    void reservedN8OnUrgencyPage() {
        Map<String, Object> d = projectHappy().page(4).decision();
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> reserved = (List<Map<String, Object>>) d.get("reserved_next");
        assertEquals("N8", reserved.getFirst().get("claim_id"));
    }

    private static NewsMvpProjector.RunResult projectHappy() {
        return NewsMvpProjector.project(1L, NewsMvpFixtures.happyNews(), NewsMvpFixtures.PAIN_TEXT);
    }

    private static ClaimCandidate find(List<ClaimCandidate> pool, String id) {
        return pool.stream().filter(c -> id.equals(c.stableId())).findFirst().orElseThrow();
    }

    private static void assertReasonsFromTrace(ProjectionPageResult page) {
        @SuppressWarnings("unchecked")
        List<String> reasons = (List<String>) page.decision().get("reasons");
        Set<String> allowed = new HashSet<>();
        collectKeys(page.decision().get("selected"), allowed);
        collectKeys(page.decision().get("runner_up"), allowed);
        collectKeys(page.decision().get("reserved_next"), allowed);
        collectKeys(page.decision().get("eliminated_key"), allowed);
        allowed.add("why_not");
        for (String reason : reasons) {
            int colon = reason.lastIndexOf('：');
            assertTrue(colon > 0, reason);
            String factor = reason.substring(colon + 1);
            assertTrue(allowed.contains(factor), reason + " not in " + allowed);
        }
    }

    @SuppressWarnings("unchecked")
    private static void collectKeys(Object node, Set<String> keys) {
        if (node instanceof Map<?, ?> map) {
            for (Object k : map.keySet()) keys.add(String.valueOf(k));
            for (Object v : map.values()) collectKeys(v, keys);
        } else if (node instanceof Collection<?> col) {
            for (Object v : col) collectKeys(v, keys);
        }
    }

    private static String stripPunct(String s) {
        return s.replaceAll("[\\p{Punct}\\s—]", "");
    }
}
