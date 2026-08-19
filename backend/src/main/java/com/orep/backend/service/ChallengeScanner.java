package com.orep.backend.service;

import com.orep.backend.dto.Challenge;
import com.orep.backend.dto.ChallengeSet;
import com.orep.backend.dto.SubstanceClaim;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Rule-first challenge scan. LLM is not used and timestamps are never invented.
 * A failed scan still leaves the draft standing and must keep 「本场未完成质询」.
 */
public final class ChallengeScanner {
    public static final String SCORE_WITHOUT_ANCHOR = "score_without_anchor";
    public static final String ANCHOR_MISMATCH = "anchor_mismatch";
    public static final String CLAUSE_MISMATCH = "clause_mismatch";
    public static final String EMPTY_NOTE = "本场未发现可核验争议";
    public static final String STATUS_PENDING = "pending";
    public static final String STATUS_ACCEPTED = "accepted";
    public static final String STATUS_REJECTED = "rejected";
    public static final int MAX_ITEMS = 4;
    public static final String SCAN_VERSION = "challenge-scan-v2";

    private static final Pattern SOURCE_TIME = Pattern.compile("@(\\d{1,2}):(\\d{2})(?::(\\d{2}))?");
    private static final Pattern LATIN = Pattern.compile("[a-z0-9]{2,}");
    private static final Pattern CJK = Pattern.compile("[\\p{IsHan}]{2,}");
    private static final Set<String> STOP = Set.of(
            "的", "了", "在", "和", "与", "是", "没有", "缺少", "不足", "现场", "只", "展示",
            "证据", "本场", "不能", "没有可"
    );
    private static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);

    private ChallengeScanner() {
    }

    public static ChallengeSet scan(Input input) {
        Input safe = input == null ? new Input() : input;
        ChallengeSet set = new ChallengeSet();
        if (safe.failed) {
            set.setScanned(false);
            set.setNote(DeliberationStageMachine.CHALLENGE_NOTE);
            set.setItems(new ArrayList<>());
            return set;
        }
        Map<Long, Anchor> anchors = indexAnchors(safe.anchors);
        List<Challenge> type1 = new ArrayList<>();
        List<Challenge> type2 = new ArrayList<>();
        List<Challenge> type3 = new ArrayList<>();
        for (Deduction deduction : safe.deductions == null ? List.<Deduction>of() : safe.deductions) {
            if (deduction == null || !positive(deduction.deductedPoints)) {
                continue;
            }
            List<Long> ids = copyIds(deduction.anchorIds);
            if (ids.isEmpty()) {
                type1.add(scoreWithoutAnchor(deduction));
                continue;
            }
            List<Anchor> cited = new ArrayList<>();
            boolean anyUsable = false;
            boolean anyBad = false;
            Long firstTime = null;
            for (Long id : ids) {
                Anchor anchor = anchors.get(id);
                if (anchor == null || !usable(anchor, safe.durationMs)) {
                    anyBad = true;
                    if (anchor != null && firstTime == null) {
                        firstTime = existingTime(anchor);
                    }
                } else {
                    anyUsable = true;
                    cited.add(anchor);
                    if (firstTime == null) {
                        firstTime = existingTime(anchor);
                    }
                }
            }
            if (anyBad) {
                type2.add(anchorMismatch(deduction, ids, firstTime));
            }
            if (anyUsable && clauseMismatch(deduction.reason, cited)) {
                type3.add(clauseMismatchItem(deduction, ids, firstTime));
            }
        }
        for (SubstanceClaim claim : safe.claims == null ? List.<SubstanceClaim>of() : safe.claims) {
            if (claim == null || !"fail".equals(claim.getVerdict())) {
                continue;
            }
            if (!claimHasSeekable(claim, anchors, safe.durationMs)) {
                type1.add(claimWithoutAnchor(claim));
            }
        }
        Set<String> observedDimensions = new LinkedHashSet<>();
        for (Observation observation : safe.observations == null ? List.<Observation>of() : safe.observations) {
            if (observation == null || !positive(observation.rawScore)) {
                continue;
            }
            String dimensionKey = dimension(observation.targetDimension);
            if (!observedDimensions.add(dimensionKey)) {
                continue;
            }
            if (!hasUsableAnchor(observation.anchorIds, anchors, safe.durationMs)) {
                type1.add(observationWithoutAnchor(observation));
            }
        }
        List<Challenge> merged = new ArrayList<>();
        addCapped(merged, type1);
        addCapped(merged, type2);
        addCapped(merged, type3);
        assignIds(merged);
        set.setScanVersion(SCAN_VERSION);
        set.setScanned(true);
        set.setItems(merged);
        set.setNote(merged.isEmpty() ? EMPTY_NOTE : "");
        decorate(set, null);
        return set;
    }

    public static ChallengeSet applyTeacherDecision(
            ChallengeSet current,
            String challengeId,
            String action,
            String reason,
            Long teacherUserId
    ) {
        if (current == null || !current.isScanned()) {
            throw new IllegalArgumentException("本场质询尚未完成扫描");
        }
        String normalized = action == null ? "" : action.trim().toLowerCase(Locale.ROOT);
        if (!"accept".equals(normalized) && !"reject".equals(normalized)) {
            throw new IllegalArgumentException("质询只能采纳或驳回");
        }
        String id = challengeId == null ? "" : challengeId.trim();
        ChallengeSet next = copy(current);
        for (Challenge item : next.getItems()) {
            if (item == null || !id.equals(item.getChallengeId())) {
                continue;
            }
            item.setStatus("accept".equals(normalized) ? STATUS_ACCEPTED : STATUS_REJECTED);
            item.setTeacherReason(reason == null ? "" : reason.trim());
            item.setResolvedBy(teacherUserId);
            item.setResolvedAt(LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME));
            return next;
        }
        throw new IllegalArgumentException("找不到这条质询");
    }

    public static boolean needsRescan(ChallengeSet set) {
        if (set == null || !set.isScanned()) {
            return true;
        }
        if (SCAN_VERSION.equals(set.getScanVersion())) {
            return false;
        }
        if (set.getItems() == null) {
            return true;
        }
        for (Challenge item : set.getItems()) {
            if (item != null && item.getStatus() != null && !STATUS_PENDING.equals(item.getStatus())) {
                return false;
            }
        }
        return true;
    }

    public static void decorate(ChallengeSet set, BigDecimal officialScore) {
        if (set == null) {
            return;
        }
        BigDecimal adjustment = ZERO;
        if (set.getItems() != null) {
            for (Challenge item : set.getItems()) {
                if (item == null || !STATUS_ACCEPTED.equals(item.getStatus())) {
                    continue;
                }
                if (item.getProposedRestorePoints() != null) {
                    adjustment = adjustment.add(item.getProposedRestorePoints());
                }
            }
        }
        set.setAcceptedAdjustment(adjustment.setScale(2, RoundingMode.HALF_UP));
        if (officialScore == null) {
            set.setAdjustedDraftScore(null);
            return;
        }
        set.setAdjustedDraftScore(officialScore.add(adjustment).setScale(2, RoundingMode.HALF_UP));
    }

    private static Challenge scoreWithoutAnchor(Deduction deduction) {
        Challenge item = base(SCORE_WITHOUT_ANCHOR, deduction.lossId, deduction.targetDimension, copyIds(deduction.anchorIds));
        item.setSeekable(false);
        item.setProposedRestorePoints(scale(deduction.deductedPoints));
        item.setStatement(dimension(deduction.targetDimension) + "扣了 " + plain(deduction.deductedPoints) + " 分，但没有可跳转的证据。");
        return item;
    }

    private static Challenge observationWithoutAnchor(Observation observation) {
        Challenge item = base(
                SCORE_WITHOUT_ANCHOR,
                firstNonBlank(observation.lossId, "observation:" + observation.targetDimension),
                observation.targetDimension,
                copyIds(observation.anchorIds)
        );
        item.setSeekable(false);
        item.setStatement(dimension(observation.targetDimension) + "给了分，但没有可跳转的证据。");
        return item;
    }

    private static Challenge claimWithoutAnchor(SubstanceClaim claim) {
        String type = claim.getClaimType() == null ? "claim" : claim.getClaimType();
        Challenge item = base(SCORE_WITHOUT_ANCHOR, "claim:" + type, claimLabel(type), List.of());
        item.setSeekable(false);
        item.setStatement(claimLabel(type) + "判定未通过，但没有可跳转的证据。");
        return item;
    }

    private static Challenge anchorMismatch(Deduction deduction, List<Long> ids, Long startMs) {
        Challenge item = base(ANCHOR_MISMATCH, deduction.lossId, deduction.targetDimension, ids);
        item.setStartMs(startMs);
        item.setSeekable(startMs != null && startMs >= 0);
        item.setStatement(dimension(deduction.targetDimension) + "引用的证据锚点无法跳转或超出录像时长。");
        return item;
    }

    private static Challenge clauseMismatchItem(Deduction deduction, List<Long> ids, Long startMs) {
        Challenge item = base(CLAUSE_MISMATCH, deduction.lossId, deduction.targetDimension, ids);
        item.setStartMs(startMs);
        item.setSeekable(startMs != null && startMs >= 0);
        item.setStatement(dimension(deduction.targetDimension) + "的量表条款与现场证据对不上。");
        return item;
    }

    private static Challenge base(String type, String lossId, String dimension, List<Long> ids) {
        Challenge item = new Challenge();
        item.setType(type);
        item.setLossId(firstNonBlank(lossId, type));
        item.setTargetDimension(dimension(dimension));
        item.setAnchorIds(ids);
        item.setStatus(STATUS_PENDING);
        return item;
    }

    private static boolean clauseMismatch(String reason, List<Anchor> cited) {
        Set<String> reasonTokens = tokens(reason);
        if (reasonTokens.isEmpty()) {
            return false;
        }
        StringBuilder evidence = new StringBuilder();
        for (Anchor anchor : cited) {
            if (anchor != null) {
                evidence.append(' ').append(anchor.evidenceText == null ? "" : anchor.evidenceText);
            }
        }
        Set<String> evidenceTokens = tokens(evidence.toString());
        if (evidenceTokens.isEmpty()) {
            return true;
        }
        for (String token : reasonTokens) {
            if (evidenceTokens.contains(token)) {
                return false;
            }
        }
        return true;
    }

    private static Set<String> tokens(String text) {
        Set<String> tokens = new LinkedHashSet<>();
        if (text == null || text.isBlank()) {
            return tokens;
        }
        String lower = text.toLowerCase(Locale.ROOT);
        Matcher latin = LATIN.matcher(lower);
        while (latin.find()) {
            tokens.add(latin.group());
        }
        Matcher cjk = CJK.matcher(text);
        while (cjk.find()) {
            String block = cjk.group();
            if (block.length() == 2 && !STOP.contains(block)) {
                tokens.add(block);
                continue;
            }
            for (int i = 0; i < block.length() - 1; i++) {
                String gram = block.substring(i, i + 2);
                if (!STOP.contains(gram)) {
                    tokens.add(gram);
                }
            }
        }
        return tokens;
    }

    private static boolean claimHasSeekable(SubstanceClaim claim, Map<Long, Anchor> anchors, Long durationMs) {
        if (claim.getEvidenceRefs() == null) {
            return false;
        }
        for (String ref : claim.getEvidenceRefs()) {
            Long id = parseAnchorRef(ref);
            if (id != null && usable(anchors.get(id), durationMs)) {
                return true;
            }
        }
        return false;
    }

    private static boolean hasUsableAnchor(List<Long> ids, Map<Long, Anchor> anchors, Long durationMs) {
        for (Long id : copyIds(ids)) {
            if (usable(anchors.get(id), durationMs)) {
                return true;
            }
        }
        return false;
    }

    private static boolean usable(Anchor anchor, Long durationMs) {
        if (anchor == null || invalid(anchor.validityStatus) || !seekable(anchor)) {
            return false;
        }
        Long start = existingTime(anchor);
        if (start == null) {
            return false;
        }
        if (durationMs != null && durationMs > 0 && start > durationMs) {
            return false;
        }
        if (anchor.endMs != null && start >= 0 && anchor.endMs < start) {
            return false;
        }
        return true;
    }

    private static boolean seekable(Anchor anchor) {
        return existingTime(anchor) != null;
    }

    private static Long existingTime(Anchor anchor) {
        if (anchor == null) {
            return null;
        }
        if (anchor.startMs != null && anchor.startMs >= 0) {
            return anchor.startMs;
        }
        if (anchor.sourceRef == null) {
            return null;
        }
        Matcher matcher = SOURCE_TIME.matcher(anchor.sourceRef);
        if (!matcher.find()) {
            return null;
        }
        int hours = matcher.group(3) == null ? 0 : Integer.parseInt(matcher.group(1));
        int minutes = matcher.group(3) == null ? Integer.parseInt(matcher.group(1)) : Integer.parseInt(matcher.group(2));
        int seconds = matcher.group(3) == null ? Integer.parseInt(matcher.group(2)) : Integer.parseInt(matcher.group(3));
        return ((hours * 60L + minutes) * 60L + seconds) * 1000L;
    }

    private static boolean invalid(String status) {
        if (status == null || status.isBlank()) {
            return false;
        }
        String value = status.trim().toLowerCase(Locale.ROOT);
        return "invalid".equals(value) || "rejected".equals(value) || "broken".equals(value);
    }

    private static boolean positive(BigDecimal value) {
        return value != null && value.compareTo(BigDecimal.ZERO) > 0;
    }

    private static Map<Long, Anchor> indexAnchors(List<Anchor> anchors) {
        Map<Long, Anchor> index = new LinkedHashMap<>();
        if (anchors == null) {
            return index;
        }
        for (Anchor anchor : anchors) {
            if (anchor != null && anchor.id != null) {
                index.put(anchor.id, anchor);
            }
        }
        return index;
    }

    private static List<Long> copyIds(List<Long> ids) {
        List<Long> copy = new ArrayList<>();
        if (ids == null) {
            return copy;
        }
        for (Long id : ids) {
            if (id != null) {
                copy.add(id);
            }
        }
        return copy;
    }

    private static void addCapped(List<Challenge> merged, List<Challenge> extra) {
        for (Challenge item : extra) {
            if (merged.size() >= MAX_ITEMS) {
                return;
            }
            merged.add(item);
        }
    }

    private static void assignIds(List<Challenge> items) {
        Set<String> used = new LinkedHashSet<>();
        for (Challenge item : items) {
            String base = "c-" + item.getType() + "-" + sanitize(item.getLossId());
            String id = base;
            int n = 2;
            while (!used.add(id)) {
                id = base + "-" + n;
                n++;
            }
            item.setChallengeId(id);
        }
    }

    private static String sanitize(String value) {
        String text = firstNonBlank(value, "item").replaceAll("[^a-zA-Z0-9:_-]", "-");
        return text.isBlank() ? "item" : text;
    }

    private static Long parseAnchorRef(String ref) {
        if (ref == null) {
            return null;
        }
        Matcher matcher = Pattern.compile("(\\d+)").matcher(ref);
        return matcher.find() ? Long.parseLong(matcher.group(1)) : null;
    }

    private static String claimLabel(String type) {
        if ("wrapper".equals(type)) {
            return "套壳";
        }
        if ("advancement".equals(type)) {
            return "先进";
        }
        if ("value".equals(type)) {
            return "价值";
        }
        return "核验";
    }

    private static String dimension(String value) {
        return firstNonBlank(value, "本场");
    }

    private static String firstNonBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private static String plain(BigDecimal value) {
        if (value == null) {
            return "0";
        }
        return value.stripTrailingZeros().toPlainString();
    }

    private static BigDecimal scale(BigDecimal value) {
        return value == null ? null : value.setScale(2, RoundingMode.HALF_UP);
    }

    private static ChallengeSet copy(ChallengeSet current) {
        ChallengeSet next = new ChallengeSet();
        next.setScanVersion(current.getScanVersion());
        next.setScanned(current.isScanned());
        next.setNote(current.getNote());
        next.setAcceptedAdjustment(current.getAcceptedAdjustment());
        next.setAdjustedDraftScore(current.getAdjustedDraftScore());
        List<Challenge> items = new ArrayList<>();
        if (current.getItems() != null) {
            for (Challenge item : current.getItems()) {
                if (item == null) {
                    continue;
                }
                Challenge copy = new Challenge();
                copy.setChallengeId(item.getChallengeId());
                copy.setType(item.getType());
                copy.setTargetDimension(item.getTargetDimension());
                copy.setLossId(item.getLossId());
                copy.setAnchorIds(item.getAnchorIds() == null ? new ArrayList<>() : new ArrayList<>(item.getAnchorIds()));
                copy.setStatement(item.getStatement());
                copy.setSeekable(item.isSeekable());
                copy.setStartMs(item.getStartMs());
                copy.setStatus(item.getStatus());
                copy.setProposedRestorePoints(item.getProposedRestorePoints());
                copy.setTeacherReason(item.getTeacherReason());
                copy.setResolvedBy(item.getResolvedBy());
                copy.setResolvedAt(item.getResolvedAt());
                items.add(copy);
            }
        }
        next.setItems(items);
        return next;
    }

    public static final class Input {
        public boolean failed;
        public Long durationMs;
        public List<Deduction> deductions = new ArrayList<>();
        public List<Observation> observations = new ArrayList<>();
        public List<Anchor> anchors = new ArrayList<>();
        public List<SubstanceClaim> claims = new ArrayList<>();
    }

    public static final class Deduction {
        public String lossId;
        public String targetDimension;
        public BigDecimal deductedPoints;
        public List<Long> anchorIds = new ArrayList<>();
        public String reason;
    }

    public static final class Observation {
        public String lossId;
        public String targetDimension;
        public BigDecimal rawScore;
        public List<Long> anchorIds = new ArrayList<>();
    }

    public static final class Anchor {
        public Long id;
        public Long startMs;
        public Long endMs;
        public String sourceRef;
        public String evidenceText;
        public String validityStatus;
    }
}
