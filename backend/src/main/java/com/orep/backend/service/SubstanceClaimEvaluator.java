package com.orep.backend.service;

import com.orep.backend.dto.SubstanceClaim;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Deterministic substance claims. Retrieval is off unless explicitly enabled.
 * Unverified statements always contain 本场未核验 and never use booster words.
 */
public final class SubstanceClaimEvaluator {
    public static final String WRAPPER = "wrapper";
    public static final String ADVANCEMENT = "advancement";
    public static final String VALUE = "value";

    private static final Pattern BOOSTER = Pattern.compile("赋能|领先|填补空白|已验证|已联网审查");
    private static final Pattern PACKAGING = Pattern.compile("开源|套壳|改了改|chatgpt|muso|ollama|现成|成稿", Pattern.CASE_INSENSITIVE);
    private static final Pattern DEMO = Pattern.compile("演示|运行画面|蓝牙|设备|真机|联调|现场展示");
    private static final Pattern REPO = Pattern.compile("仓库|github|gitlab|ide|提交记录|代码仓", Pattern.CASE_INSENSITIVE);
    private static final Pattern DIFF = Pattern.compile("差异|自己写|二次开发|改造点|不是套");
    private static final Pattern ORAL_ADVANCE = Pattern.compile("先进|领先|一流|填补空白");
    private static final Pattern HARD_ADVANCE = Pattern.compile("对比|测试数|指标|并发|响应时间|基准|准确率|真实调用|设备联动");
    private static final Pattern VALUE_WHO = Pattern.compile("农户|用户|学校|医院|工厂|园区|老师|学生|服务谁");
    private static final Pattern VALUE_REPLACE = Pattern.compile("替代|痛点|解决|节省|人工");
    private static final Pattern SLOGAN = Pattern.compile("赋能|数字化转型|智慧未来");

    private SubstanceClaimEvaluator() {
    }

    public static List<SubstanceClaim> evaluate(ClaimEvidence evidence) {
        ClaimEvidence safe = evidence == null ? new ClaimEvidence() : evidence;
        String corpus = safe.corpus();
        List<SubstanceClaim> claims = new ArrayList<>();
        claims.add(wrapper(safe, corpus));
        claims.add(advancement(safe, corpus));
        claims.add(value(safe, corpus));
        if (!safe.retrievalEnabled) {
            for (SubstanceClaim claim : claims) {
                if ("retrieved_cited".equals(claim.getClaimStatus())) {
                    downgradeUnverified(claim, "本场未核验公开对照，检索未开启。");
                }
            }
        }
        for (SubstanceClaim claim : claims) {
            sanitize(claim);
        }
        return claims;
    }

    private static SubstanceClaim wrapper(ClaimEvidence evidence, String corpus) {
        SubstanceClaim claim = base(WRAPPER);
        boolean packaging = mentions(PACKAGING, corpus);
        boolean demo = mentions(DEMO, corpus);
        boolean repo = mentions(REPO, corpus);
        boolean diff = mentions(DIFF, corpus);
        if (packaging && !demo && !repo) {
            return failSeenOrUnverified(claim, evidence, false,
                    "本场只提到成稿或开源改写，没有运行或代码证据，不能算通过。");
        }
        if (packaging && demo && !repo && !diff) {
            claim.setVerdict("fail");
            claim.setClaimStatus("seen_in_session");
            claim.setStatement("本场有运行演示，但未说明与公开成稿的差异，也没有仓库证据。");
            claim.setEvidenceRefs(copyRefs(evidence.evidenceRefs));
            claim.setScoreCapHint(new BigDecimal("12"));
            return claim;
        }
        if (diff && (demo || repo) && !evidence.evidenceRefs.isEmpty()) {
            claim.setVerdict("insufficient");
            claim.setClaimStatus("seen_in_session");
            claim.setStatement("本场讲了差异并有现场证据，但仍不足以判通过。");
            claim.setEvidenceRefs(copyRefs(evidence.evidenceRefs));
            return claim;
        }
        return unverified(claim, "本场未核验是否开源或成稿改写。");
    }

    private static SubstanceClaim advancement(ClaimEvidence evidence, String corpus) {
        SubstanceClaim claim = base(ADVANCEMENT);
        boolean oral = mentions(ORAL_ADVANCE, corpus);
        boolean hard = mentions(HARD_ADVANCE, corpus);
        if (oral && !hard) {
            return failSeenOrUnverified(claim, evidence, !evidence.evidenceRefs.isEmpty() || oral,
                    "本场只口头说先进，没有对比、测试数或真实调用证据，不能算通过。");
        }
        if (hard && !evidence.evidenceRefs.isEmpty()) {
            claim.setVerdict("insufficient");
            claim.setClaimStatus("seen_in_session");
            claim.setStatement("本场有对比或测试线索，但仍缺可跳转的完整核验链。");
            claim.setEvidenceRefs(copyRefs(evidence.evidenceRefs));
            return claim;
        }
        if (hard && evidence.evidenceRefs.isEmpty()) {
            return unverified(claim, "本场提到指标，但本场未核验可跳转证据。");
        }
        return unverified(claim, "本场未核验先进性对照。");
    }

    private static SubstanceClaim value(ClaimEvidence evidence, String corpus) {
        SubstanceClaim claim = base(VALUE);
        boolean who = mentions(VALUE_WHO, corpus);
        boolean replace = mentions(VALUE_REPLACE, corpus);
        boolean slogan = mentions(SLOGAN, corpus);
        if (slogan && !who && !replace) {
            return unverified(claim, "本场未核验服务对象和替代关系，只有口号。");
        }
        if (who && replace && !evidence.evidenceRefs.isEmpty()) {
            claim.setVerdict("insufficient");
            claim.setClaimStatus("seen_in_session");
            claim.setStatement("本场说清了服务谁、要解决什么，但仍缺可核对的公开对照。");
            claim.setEvidenceRefs(copyRefs(evidence.evidenceRefs));
            return claim;
        }
        if (who || replace) {
            return unverified(claim, "本场提到使用对象或痛点，但本场未核验替代关系。");
        }
        return unverified(claim, "本场未核验对行业或区域是否有用。");
    }

    private static SubstanceClaim failSeenOrUnverified(SubstanceClaim claim, ClaimEvidence evidence, boolean seen, String statement) {
        claim.setVerdict("fail");
        if (seen && !evidence.evidenceRefs.isEmpty()) {
            claim.setClaimStatus("seen_in_session");
            claim.setStatement(statement);
            claim.setEvidenceRefs(copyRefs(evidence.evidenceRefs));
        } else {
            claim.setClaimStatus("unverified");
            claim.setStatement(ensureUnverified(statement));
            claim.setEvidenceRefs(new ArrayList<>());
        }
        claim.setScoreCapHint(new BigDecimal("12"));
        return claim;
    }

    private static SubstanceClaim unverified(SubstanceClaim claim, String statement) {
        claim.setVerdict("insufficient");
        claim.setClaimStatus("unverified");
        claim.setStatement(ensureUnverified(statement));
        claim.setEvidenceRefs(new ArrayList<>());
        claim.setSources(new ArrayList<>());
        return claim;
    }

    private static void downgradeUnverified(SubstanceClaim claim, String statement) {
        claim.setClaimStatus("unverified");
        if ("pass".equals(claim.getVerdict())) {
            claim.setVerdict("insufficient");
        }
        claim.setStatement(ensureUnverified(statement));
        claim.setSources(new ArrayList<>());
        claim.setEvidenceRefs(new ArrayList<>());
    }

    private static void sanitize(SubstanceClaim claim) {
        if ("unverified".equals(claim.getClaimStatus())) {
            claim.setEvidenceRefs(new ArrayList<>());
            claim.setSources(new ArrayList<>());
            claim.setStatement(ensureUnverified(claim.getStatement()));
            if (BOOSTER.matcher(claim.getStatement()).find()) {
                claim.setStatement("本场未核验。");
            }
        }
        if ("retrieved_cited".equals(claim.getClaimStatus()) && (claim.getSources() == null || claim.getSources().isEmpty())) {
            downgradeUnverified(claim, "本场未核验公开来源。");
        }
        if ("pass".equals(claim.getVerdict()) && (claim.getEvidenceRefs() == null || claim.getEvidenceRefs().isEmpty())) {
            claim.setVerdict("insufficient");
            if (!"retrieved_cited".equals(claim.getClaimStatus())) {
                claim.setClaimStatus("unverified");
                claim.setStatement(ensureUnverified(claim.getStatement()));
            }
        }
    }

    private static String ensureUnverified(String statement) {
        String text = statement == null ? "" : statement.trim();
        if (text.isEmpty()) {
            return "本场未核验。";
        }
        if (!text.contains("本场未核验")) {
            return "本场未核验。" + text;
        }
        return text;
    }

    private static SubstanceClaim base(String type) {
        SubstanceClaim claim = new SubstanceClaim();
        claim.setClaimType(type);
        claim.setVerdict("insufficient");
        claim.setClaimStatus("unverified");
        claim.setStatement("本场未核验。");
        return claim;
    }

    private static boolean mentions(Pattern pattern, String corpus) {
        if (corpus == null || corpus.isBlank()) {
            return false;
        }
        var matcher = pattern.matcher(corpus);
        while (matcher.find()) {
            String before = corpus.substring(Math.max(0, matcher.start() - 16), matcher.start());
            if (before.contains("无") || before.contains("没") || before.contains("未") || before.contains("不") || before.contains("缺")) {
                continue;
            }
            return true;
        }
        return false;
    }

    private static List<String> copyRefs(List<String> refs) {
        return refs == null ? new ArrayList<>() : new ArrayList<>(refs);
    }

    public static final class ClaimEvidence {
        public String transcript = "";
        public String observations = "";
        public List<String> evidenceRefs = new ArrayList<>();
        public boolean retrievalEnabled;

        public String corpus() {
            return ((transcript == null ? "" : transcript) + "\n" + (observations == null ? "" : observations))
                    .toLowerCase(Locale.ROOT);
        }
    }
}
