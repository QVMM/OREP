package com.orep.backend.service;

import com.orep.backend.dto.CeilingGap;
import com.orep.backend.dto.ScoreGap;
import com.orep.backend.dto.SubstanceClaim;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

/**
 * Splits closureRate from officialScore. Closure 100% never lifts the official score to the track ceiling.
 * Repair bonus is capped and requires hung evidence. Change the cap only with a contractVersion bump.
 */
public final class ScoreGapCalculator {
    static final BigDecimal REPAIR_BONUS_CAP = new BigDecimal("4.00");
    private static final int MAX_GAPS = 4;
    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);

    private ScoreGapCalculator() {
    }

    public static ScoreGap evaluate(Input input) {
        Input safe = input == null ? new Input() : input;
        BigDecimal ledger = scale(safe.ledgerScore);
        BigDecimal trackCeiling = scale(safe.trackCeiling);
        ScoreGap gap = new ScoreGap();
        gap.setTrackCeiling(trackCeiling);
        BigDecimal closure = closureRate(safe.priorTasks);
        gap.setClosureRate(closure);
        BigDecimal bonus = repairBonus(safe.priorTasks);
        gap.setRepairBonus(bonus);
        BigDecimal ceiling = effectiveCeiling(safe, trackCeiling);
        BigDecimal official = ledger == null ? null : min(ledger.add(bonus), ceiling == null ? ledger.add(bonus) : ceiling);
        if (official != null && trackCeiling != null && official.compareTo(trackCeiling) >= 0 && mustStayBelowCeiling(safe)) {
            official = below(trackCeiling);
        }
        gap.setOfficialScore(official);
        gap.setModelReviewScore(scale(safe.modelReviewScore));
        gap.setTapeGrounded(safe.tapeGrounded);
        if (Boolean.TRUE.equals(safe.tapeGrounded)) {
            gap.setIdentityReason("同一录像讲稿与同一套量表，权威分按转写命中词钉死，不跟模型每次重读走");
        }
        if (safe.previousOfficialScore == null) {
            gap.setDeltaFromLast(null);
        } else if (official != null) {
            gap.setDeltaFromLast(official.subtract(scale(safe.previousOfficialScore)));
        }
        gap.setCeilingGaps(buildGaps(safe, official, trackCeiling));
        return gap;
    }

    static BigDecimal closureRate(List<PriorTask> priorTasks) {
        if (priorTasks == null || priorTasks.isEmpty()) {
            return null;
        }
        int accepted = 0;
        for (PriorTask task : priorTasks) {
            if (task != null && task.accepted && task.evidenceAttached) {
                accepted++;
            }
        }
        return BigDecimal.valueOf(accepted)
                .divide(BigDecimal.valueOf(priorTasks.size()), 4, RoundingMode.HALF_UP);
    }

    static BigDecimal repairBonus(List<PriorTask> priorTasks) {
        if (priorTasks == null || priorTasks.isEmpty()) {
            return ZERO;
        }
        BigDecimal bonus = ZERO;
        for (PriorTask task : priorTasks) {
            if (task == null || !task.accepted || !task.evidenceAttached) {
                continue;
            }
            bonus = bonus.add(task.expectedGainPoints == null ? new BigDecimal("1.00") : scale(task.expectedGainPoints));
        }
        if (bonus.compareTo(REPAIR_BONUS_CAP) > 0) {
            return REPAIR_BONUS_CAP;
        }
        return bonus;
    }

    private static BigDecimal effectiveCeiling(Input input, BigDecimal trackCeiling) {
        if (trackCeiling == null) {
            return scale(input.evidenceCap);
        }
        if (!mustStayBelowCeiling(input)) {
            return trackCeiling;
        }
        BigDecimal evidenceCap = scale(input.evidenceCap);
        if (evidenceCap != null && evidenceCap.compareTo(trackCeiling) < 0) {
            return evidenceCap;
        }
        return below(trackCeiling);
    }

    private static boolean mustStayBelowCeiling(Input input) {
        if (!input.hasStableDemoEvidence) {
            return true;
        }
        SubstanceClaim wrapper = findClaim(input.claims, SubstanceClaimEvaluator.WRAPPER);
        SubstanceClaim advancement = findClaim(input.claims, SubstanceClaimEvaluator.ADVANCEMENT);
        return isFail(wrapper) || isFail(advancement);
    }

    private static List<CeilingGap> buildGaps(Input input, BigDecimal official, BigDecimal trackCeiling) {
        List<CeilingGap> gaps = new ArrayList<>();
        addClaimGap(gaps, findClaim(input.claims, SubstanceClaimEvaluator.WRAPPER),
                "差异与仓库仍缺", "套壳或成稿差异未核验通过，技能相关维不能进满分档。", "技能水平");
        addClaimGap(gaps, findClaim(input.claims, SubstanceClaimEvaluator.ADVANCEMENT),
                "先进对照仍缺", "口头先进不能进满分档，需要可复核的对比测试。", "技能水平");
        addClaimGap(gaps, findClaim(input.claims, SubstanceClaimEvaluator.VALUE),
                "服务对象仍不清", "价值主张还不能支撑该维满分。", "应用价值");
        if (!input.hasStableDemoEvidence) {
            gaps.add(gap("运行演示仍缺", "本场没有稳定演示证据，演示/熟练度相关维封在次高档。", null, "职业素养"));
        }
        if (official != null && trackCeiling != null && official.compareTo(trackCeiling) < 0 && gaps.isEmpty()) {
            gaps.add(gap("未到赛道上限", "权威分低于赛道上限，但本场还缺可核验的满分证据。", null, null));
        }
        if (gaps.size() > MAX_GAPS) {
            return List.copyOf(gaps.subList(0, MAX_GAPS));
        }
        return List.copyOf(gaps);
    }

    private static void addClaimGap(List<CeilingGap> gaps, SubstanceClaim claim, String title, String why, String dimension) {
        if (!isFail(claim) && !isUnverifiedBlocker(claim)) {
            return;
        }
        String statement = claim.getStatement() == null || claim.getStatement().isBlank() ? why : claim.getStatement();
        gaps.add(gap(title, statement, claim.getClaimType(), dimension));
    }

    private static boolean isFail(SubstanceClaim claim) {
        return claim != null && "fail".equals(claim.getVerdict());
    }

    private static boolean isUnverifiedBlocker(SubstanceClaim claim) {
        return claim != null && "unverified".equals(claim.getClaimStatus()) && "wrapper".equals(claim.getClaimType());
    }

    private static SubstanceClaim findClaim(List<SubstanceClaim> claims, String type) {
        if (claims == null) {
            return null;
        }
        for (SubstanceClaim claim : claims) {
            if (claim != null && type.equals(claim.getClaimType())) {
                return claim;
            }
        }
        return null;
    }

    private static CeilingGap gap(String title, String why, String claimType, String dimension) {
        CeilingGap item = new CeilingGap();
        item.setTitle(title);
        item.setWhyNotFull(why);
        item.setRelatedClaimType(claimType);
        item.setRelatedDimension(dimension);
        return item;
    }

    private static BigDecimal min(BigDecimal left, BigDecimal right) {
        return left.compareTo(right) <= 0 ? left : right;
    }

    private static BigDecimal below(BigDecimal ceiling) {
        return ceiling.subtract(new BigDecimal("0.10")).max(ZERO);
    }

    private static BigDecimal scale(BigDecimal value) {
        return value == null ? null : value.setScale(2, RoundingMode.HALF_UP);
    }

    public static final class Input {
        public BigDecimal ledgerScore;
        public BigDecimal modelReviewScore;
        public Boolean tapeGrounded;
        public BigDecimal trackCeiling;
        public BigDecimal evidenceCap;
        public BigDecimal previousOfficialScore;
        public List<PriorTask> priorTasks = List.of();
        public List<SubstanceClaim> claims = List.of();
        public boolean hasStableDemoEvidence;
    }

    public static final class PriorTask {
        public boolean accepted;
        public boolean evidenceAttached;
        public BigDecimal expectedGainPoints;
    }
}
