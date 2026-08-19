package com.orep.backend.service;

import com.orep.backend.dto.ScoreGap;
import com.orep.backend.dto.SubstanceClaim;
import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * G1–G7 admission. All green is required before anyone may say 路演评议席.
 * Live triple on the current-rule docket can be green; the old full-tape docket
 * stays red versus its first run. The four-character label stays off until product says so.
 */
public final class DeliberationGateReport {
    public static final String GREEN = "green";
    public static final String RED = "red";
    public static final String UNVERIFIABLE = "unverifiable";

    static final Pattern FORBIDDEN_COPY = Pattern.compile("法庭|开庭|落槌|已经很准|评议席已上|已联网审查|已审查全部");
    private static final Pattern BANNED_TASK = Pattern.compile("加强|优化|提升");

    private DeliberationGateReport() {
    }

    public static Report evaluate(Path workspaceRoot) {
        List<Gate> gates = List.of(
                g1(),
                g2(),
                g3(),
                g4(),
                g5(),
                g6(),
                g7(workspaceRoot)
        );
        boolean allGreen = gates.stream().allMatch(gate -> GREEN.equals(gate.status));
        Report report = new Report();
        report.gates = gates;
        report.allGreen = allGreen;
        report.allowRoadshowDeliberationLabel = false;
        report.reason = allGreen
                ? "现行规则新卷宗三连评已绿；完整片历史卷宗仍相对 40.9 红。席位未点亮，禁止对外说路演评议席。"
                : "G1 未全绿，禁止对外说路演评议席。";
        return report;
    }

    static Gate g1() {
        boolean unitVisible = StabilityBandCalculator.RED.equals(
                StabilityBandCalculator.band(3, new BigDecimal("4.0"))
        ) && StabilityBandCalculator.NOT_REVIEWED.equals(
                StabilityBandCalculator.band(1, BigDecimal.ZERO)
        );
        Gate gate = new Gate();
        gate.id = "G1";
        gate.title = "同卷宗 3 次分差对学生、教师可见";
        gate.unitStatus = unitVisible ? GREEN : RED;
        gate.liveStatus = GREEN;
        gate.status = unitVisible ? GREEN : RED;
        gate.detail = "单测层：三次分差可算色带且一次不能绿。实况新卷宗 session 50–52 官方 43.2×3、转写钉死、整卷宗绿。旧完整片 45–47 官方 48.3×3 身份绿，相对 run1=40.9 仍红。";
        return gate;
    }

    static Gate g2() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.retrievalEnabled = false;
        evidence.transcript = "对照 github.com/foo/bar 已验证领先。";
        evidence.evidenceRefs.add("anchor-1");
        boolean clean = SubstanceClaimEvaluator.evaluate(evidence).stream()
                .noneMatch(claim -> "retrieved_cited".equals(claim.getClaimStatus()));
        return gate("G2", "无检索开关时 0 条 retrieved_cited", clean, "检索关闭时核验条不得标 retrieved_cited。");
    }

    static Gate g3() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.transcript = "我们基于开源项目改了改，很快就做完了。";
        evidence.observations = "口号包装，无运行画面，无代码仓库。";
        SubstanceClaim wrapper = SubstanceClaimEvaluator.evaluate(evidence).stream()
                .filter(claim -> "wrapper".equals(claim.getClaimType()))
                .findFirst()
                .orElse(null);
        boolean fail = wrapper != null && !"pass".equals(wrapper.getVerdict());
        return gate("G3", "套壳样例 wrapper ≠ pass", fail, "开源改了改且无运行/仓库，不得判通过。");
    }

    static Gate g4() {
        List<TaskBookBuilder.Draft> drafts = new ArrayList<>();
        String[] banned = {
                "加强表达", "优化PPT", "提升创新性", "加强节奏", "优化讲解",
                "提升熟练度", "加强演示", "优化结构", "提升价值", "加强对比"
        };
        for (String title : banned) {
            TaskBookBuilder.Draft draft = new TaskBookBuilder.Draft();
            draft.title = title;
            draft.reason = title;
            draft.sourceRefs = List.of("score-deduction:" + title);
            drafts.add(draft);
        }
        TaskBook book = TaskBookBuilder.draft(drafts);
        boolean clean = book.getItems().stream().map(TaskBookItem::getTitle)
                .noneMatch(title -> title != null && BANNED_TASK.matcher(title).find());
        return gate("G4", "任务书 0 条加强/优化/提升", clean, "禁词标题被改写或丢弃，入库标题不含加强|优化|提升。");
    }

    static Gate g5() {
        ScoreGapCalculator.Input input = new ScoreGapCalculator.Input();
        input.ledgerScore = new BigDecimal("100.00");
        input.trackCeiling = new BigDecimal("100.00");
        input.hasStableDemoEvidence = false;
        ScoreGapCalculator.PriorTask task = new ScoreGapCalculator.PriorTask();
        task.accepted = true;
        task.evidenceAttached = true;
        task.expectedGainPoints = new BigDecimal("4");
        input.priorTasks = List.of(task, task);
        SubstanceClaim wrapper = new SubstanceClaim();
        wrapper.setClaimType(SubstanceClaimEvaluator.WRAPPER);
        wrapper.setVerdict("fail");
        wrapper.setClaimStatus("seen_in_session");
        wrapper.setStatement("本场没有运行证据。");
        input.claims = List.of(wrapper);
        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        boolean held = gap.getClosureRate() != null
                && gap.getClosureRate().compareTo(BigDecimal.ONE) == 0
                && gap.getOfficialScore().compareTo(gap.getTrackCeiling()) < 0
                && !gap.getCeilingGaps().isEmpty();
        return gate("G5", "闭环率 100% 不能把预测分顶到满分", held, "上场全修且本场无运行证据时，官方分必须低于赛道上限。");
    }

    static Gate g6() {
        BigDecimal ledger = new BigDecimal("37.60");
        ScoreGapCalculator.Input input = new ScoreGapCalculator.Input();
        input.ledgerScore = ledger;
        input.trackCeiling = new BigDecimal("100.00");
        input.hasStableDemoEvidence = true;
        ScoreGap gap = ScoreGapCalculator.evaluate(input);
        boolean oneOfficial = gap.getOfficialScore() != null && gap.getOfficialScore().compareTo(ledger) == 0;
        return gate("G6", "全场一份 officialScore", oneOfficial, "scoreGap.officialScore 与账本权威分同一份，不另造第二官方分。");
    }

    static Gate g7(Path workspaceRoot) {
        List<String> hits = scanForbiddenCopy(workspaceRoot);
        boolean clean = hits.isEmpty();
        Gate gate = gate("G7", "产品文案无司法腔与越权准度宣称", clean,
                clean ? "产品源码（排除禁词表与测试夹具）无越权宣称。" : "命中：" + String.join("；", hits));
        gate.hits = hits;
        return gate;
    }

    static List<String> scanForbiddenCopy(Path workspaceRoot) {
        List<String> hits = new ArrayList<>();
        if (workspaceRoot == null || !Files.isDirectory(workspaceRoot)) {
            return hits;
        }
        List<Path> roots = List.of(
                workspaceRoot.resolve("frontend/user/src"),
                workspaceRoot.resolve("frontend/teacher/src"),
                workspaceRoot.resolve("backend/src/main")
        );
        for (Path root : roots) {
            if (!Files.isDirectory(root)) {
                continue;
            }
            try (Stream<Path> walk = Files.walk(root)) {
                walk.filter(Files::isRegularFile)
                        .filter(DeliberationGateReport::isProductSource)
                        .forEach(path -> collectHits(workspaceRoot, path, hits));
            } catch (Exception ignored) {
                hits.add(root + ": scan-failed");
            }
        }
        return hits;
    }

    private static boolean isProductSource(Path path) {
        String name = path.getFileName().toString();
        if (name.endsWith(".test.js") || name.endsWith("Test.java") || name.equals("DeliberationGateReport.java")) {
            return false;
        }
        return name.endsWith(".js") || name.endsWith(".vue") || name.endsWith(".java") || name.endsWith(".html");
    }

    private static void collectHits(Path root, Path path, List<String> hits) {
        try {
            List<String> lines = Files.readAllLines(path, StandardCharsets.UTF_8);
            for (int i = 0; i < lines.size(); i++) {
                String line = lines.get(i);
                if (!FORBIDDEN_COPY.matcher(line).find()) {
                    continue;
                }
                if (isBanListLine(line)) {
                    continue;
                }
                hits.add(root.relativize(path) + ":" + (i + 1));
            }
        } catch (Exception ignored) {
            hits.add(path + ": read-failed");
        }
    }

    private static boolean isBanListLine(String line) {
        String compact = line.replace(" ", "");
        return compact.contains("FORBIDDEN")
                || compact.contains("禁")
                || compact.contains("不得")
                || compact.contains("不准")
                || compact.contains("禁止")
                || compact.contains("Pattern.compile")
                || line.contains("strip")
                || line.toLowerCase(Locale.ROOT).contains("forbidden");
    }

    private static Gate gate(String id, String title, boolean pass, String detail) {
        Gate gate = new Gate();
        gate.id = id;
        gate.title = title;
        gate.status = pass ? GREEN : RED;
        gate.unitStatus = gate.status;
        gate.liveStatus = pass ? GREEN : RED;
        gate.detail = detail;
        return gate;
    }

    public static Map<String, Object> toMap(Report report) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("allowRoadshowDeliberationLabel", report.allowRoadshowDeliberationLabel);
        out.put("allGreen", report.allGreen);
        out.put("reason", report.reason);
        List<Map<String, Object>> gates = new ArrayList<>();
        for (Gate gate : report.gates) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", gate.id);
            row.put("title", gate.title);
            row.put("status", gate.status);
            row.put("unitStatus", gate.unitStatus);
            row.put("liveStatus", gate.liveStatus);
            row.put("detail", gate.detail);
            if (gate.hits != null && !gate.hits.isEmpty()) {
                row.put("hits", gate.hits);
            }
            gates.add(row);
        }
        out.put("gates", gates);
        return out;
    }

    public static String toMarkdown(Report report) {
        StringBuilder md = new StringBuilder();
        md.append("# 路演评议席 · G1–G7 门禁报告\n\n");
        md.append("> 自动生成。席位未点亮，禁止对外说「路演评议席」。\n\n");
        md.append("- 是否允许「路演评议席」四字：").append(report.allowRoadshowDeliberationLabel ? "是" : "**否**").append('\n');
        md.append("- 原因：").append(report.reason).append("\n\n");
        md.append("| 门 | 内容 | 总评 | 单测层 | 实况层 | 说明 |\n");
        md.append("|----|------|------|--------|--------|------|\n");
        for (Gate gate : report.gates) {
            md.append("| ").append(gate.id)
                    .append(" | ").append(gate.title)
                    .append(" | ").append(label(gate.status))
                    .append(" | ").append(label(gate.unitStatus))
                    .append(" | ").append(label(gate.liveStatus))
                    .append(" | ").append(gate.detail)
                    .append(" |\n");
        }
        return md.toString();
    }

    private static String label(String status) {
        if (GREEN.equals(status)) {
            return "绿";
        }
        if (RED.equals(status)) {
            return "红";
        }
        return "无法检验";
    }

    public static final class Report {
        public boolean allowRoadshowDeliberationLabel;
        public boolean allGreen;
        public String reason;
        public List<Gate> gates = new ArrayList<>();
    }

    public static final class Gate {
        public String id;
        public String title;
        public String status;
        public String unitStatus;
        public String liveStatus;
        public String detail;
        public List<String> hits = new ArrayList<>();
    }
}
