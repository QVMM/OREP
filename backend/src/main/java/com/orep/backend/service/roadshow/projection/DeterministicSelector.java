package com.orep.backend.service.roadshow.projection;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * V1 选择器：无 LLM、无温度。同一输入同一选择。
 */
public final class DeterministicSelector {

    public static final String PAIN_ID = "P1";

    private DeterministicSelector() {
    }

    public record Outcome(
            List<ClaimCandidate> hardPassed,
            List<ClaimCandidate> profilePassed,
            ClaimCandidate selected,
            CompactDecision decision
    ) {
    }

    public static Outcome select(
            PageIntentSpec intent,
            List<ClaimCandidate> pool,
            Set<String> alreadySelected,
            Set<String> alreadyClusters
    ) {
        CompactDecision d = new CompactDecision();
        List<ClaimCandidate> hard = new ArrayList<>();
        for (ClaimCandidate c : pool) {
            String fail = hardFail(c, intent, alreadySelected);
            if (fail == null) {
                hard.add(c);
            } else if (d.eliminatedKey.size() < 2 && notableFail(fail)) {
                d.eliminatedKey.add(Map.of("claim_id", c.stableId(), "constraint", fail));
            }
        }
        d.traceSteps.add("filter:" + pool.size() + "→" + hard.size());

        List<ClaimCandidate> profile = new ArrayList<>();
        for (ClaimCandidate c : hard) {
            if (meetsProfile(c, intent)) {
                profile.add(c);
            }
        }
        d.traceSteps.add("profile:" + hard.size() + "→" + profile.size());

        if (profile.isEmpty()) {
            d.traceSteps.add("pick:none");
            return new Outcome(hard, profile, null, d);
        }

        Comparator<ClaimCandidate> cmp = comparator(intent, alreadyClusters);
        List<ClaimCandidate> ranked = new ArrayList<>(profile);
        ranked.sort(cmp);
        d.traceSteps.add("rank:" + intent.role());

        ClaimCandidate pick = ranked.getFirst();
        d.traceSteps.add("pick:" + pick.stableId());
        d.selected = factorRow(pick, List.of());

        for (int i = 1; i < ranked.size() && d.runnerUp.size() < 2; i++) {
            ClaimCandidate u = ranked.get(i);
            d.runnerUp.add(factorRow(u, List.of(whyNot(intent, pick, u))));
        }

        if ("urgency".equals(intent.role())) {
            hard.stream()
                    .filter(c -> !c.stableId().equals(pick.stableId()))
                    .max(Comparator.comparingInt(c -> c.factors().bridgeValue()))
                    .filter(c -> c.factors().bridgeValue() >= 4)
                    .ifPresent(c -> {
                        d.reservedNext.add(Map.of(
                                "claim_id", c.stableId(),
                                "for_intent_id", "intent_bridge",
                                "bridge_value", c.factors().bridgeValue()));
                        d.traceSteps.add("reserve:" + c.stableId());
                    });
        }

        fillReasons(d, intent, pick);
        return new Outcome(hard, profile, pick, d);
    }

    static String hardFail(ClaimCandidate c, PageIntentSpec intent, Set<String> alreadySelected) {
        if (!"ready".equals(c.status())) return "not_ready";
        if (!c.evidenceVerified()) return "evidence_unverified";
        if (c.factors().expired()) return "expired";
        if (c.factors().irrelevant()) return "irrelevant";
        if (!c.contradictIds().isEmpty()) return "contradicts";
        if (intent.forbidTech() && c.factors().tech()) return "forbidden_tech";
        if ("bridge".equals(intent.role()) && alreadySelected.contains(c.stableId())) {
            return "already_on_prev_page";
        }
        return null;
    }

    static boolean meetsProfile(ClaimCandidate c, PageIntentSpec intent) {
        if (c.factors().impact() < intent.requiredImpactMin()) return false;
        if (c.factors().ostensible() < intent.requiredOstensibleMin()) return false;
        if (intent.requireBridge() && !c.bridgesTo().contains(PAIN_ID)) return false;
        return true;
    }

    static Comparator<ClaimCandidate> comparator(PageIntentSpec intent, Set<String> alreadyClusters) {
        return (a, b) -> {
            int role = roleCompare(intent, a, b);
            if (role != 0) return role;
            int da = diversityScore(a, alreadyClusters);
            int db = diversityScore(b, alreadyClusters);
            if (db != da) return Integer.compare(db, da);
            if (b.chi() != a.chi()) return Integer.compare(b.chi(), a.chi());
            if (b.factors().freshness() != a.factors().freshness()) {
                return Integer.compare(b.factors().freshness(), a.factors().freshness());
            }
            return a.stableId().compareTo(b.stableId());
        };
    }

    private static int roleCompare(PageIntentSpec intent, ClaimCandidate a, ClaimCandidate b) {
        if ("bridge".equals(intent.role())) {
            int br = Integer.compare(b.factors().bridgeValue(), a.factors().bridgeValue());
            if (br != 0) return br;
            return Integer.compare(b.factors().impact(), a.factors().impact());
        }
        int im = Integer.compare(b.factors().impact(), a.factors().impact());
        if (im != 0) return im;
        return Integer.compare(b.factors().ostensible(), a.factors().ostensible());
    }

    private static int diversityScore(ClaimCandidate c, Set<String> alreadyClusters) {
        if (alreadyClusters == null || alreadyClusters.isEmpty()) return 1;
        return alreadyClusters.contains(c.factors().cluster()) ? 0 : 1;
    }

    private static boolean notableFail(String fail) {
        return "contradicts".equals(fail) || "expired".equals(fail) || "irrelevant".equals(fail)
                || "already_on_prev_page".equals(fail);
    }

    private static Map<String, Object> factorRow(ClaimCandidate c, List<String> whyNot) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("claim_id", c.stableId());
        m.put("impact", c.factors().impact());
        m.put("ostensible", c.factors().ostensible());
        m.put("bridge_value", c.factors().bridgeValue());
        m.put("chi", c.chi());
        m.put("freshness", c.factors().freshness());
        m.put("cluster", c.factors().cluster());
        m.put("bridges_to", c.bridgesTo().contains(PAIN_ID));
        if (!whyNot.isEmpty()) m.put("why_not", whyNot.getFirst());
        return m;
    }

    private static String whyNot(PageIntentSpec intent, ClaimCandidate pick, ClaimCandidate other) {
        if ("urgency".equals(intent.role()) && other.factors().bridgeValue() >= 4
                && other.factors().impact() < pick.factors().impact()) {
            return "bridge_value";
        }
        if (other.factors().cluster().equals(pick.factors().cluster())) return "diversity";
        if (other.factors().impact() < pick.factors().impact()) return "impact";
        if (other.factors().bridgeValue() < pick.factors().bridgeValue()) return "bridge_value";
        return "ostensible";
    }

    private static void fillReasons(CompactDecision d, PageIntentSpec intent, ClaimCandidate pick) {
        if ("urgency".equals(intent.role())) {
            d.reasons.add("选 " + pick.stableId() + "：impact");
            d.reasons.add("选 " + pick.stableId() + "：ostensible");
        } else {
            d.reasons.add("选 " + pick.stableId() + "：bridge_value");
            d.reasons.add("选 " + pick.stableId() + "：bridges_to");
        }
        if (!d.reservedNext.isEmpty()) {
            d.reasons.add("不选 " + d.reservedNext.getFirst().get("claim_id") + "：bridge_value");
        }
        if (!d.runnerUp.isEmpty()) {
            Map<String, Object> u = d.runnerUp.getFirst();
            d.reasons.add("不选 " + u.get("claim_id") + "：" + u.getOrDefault("why_not", "impact"));
        }
    }
}
