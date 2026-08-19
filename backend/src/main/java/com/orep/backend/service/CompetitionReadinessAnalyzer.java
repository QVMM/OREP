package com.orep.backend.service;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * 把项目事实转换为用户可执行的“上场前缺项”。
 * 这里不读取数据库，确保判定规则可单测、可复用，且不把内部评分权重暴露给用户。
 */
@Component
public class CompetitionReadinessAnalyzer {
    private static final Set<String> READY_STATUSES = Set.of("APPROVED", "DONE", "ACCEPTED");
    private static final Set<String> CLOSED_STATUSES = Set.of("DONE", "CLOSED", "RESOLVED");

    public List<Gap> analyze(Snapshot snapshot) {
        if (snapshot == null) return List.of();
        List<RankedGap> candidates = new ArrayList<>();
        List<MaterialFact> readyMaterials = safe(snapshot.materials()).stream()
                .filter(this::isReady)
                .toList();

        safe(snapshot.issues()).stream()
                .filter(issue -> !CLOSED_STATUSES.contains(upper(issue.status())))
                .filter(issue -> "HIGH".equals(upper(issue.severity())))
                .findFirst()
                .ifPresent(issue -> candidates.add(new RankedGap(100, new Gap(
                        "review-risk",
                        clean(issue.title(), "高风险复盘项待闭环"),
                        clean(issue.description(), "最近一轮评分仍有高风险问题，需补证并完成复核。"),
                        "high",
                        "/statistics",
                        "最近一轮评分与复盘问题"
                ))));

        if (!snapshot.roadshowCompleted() || snapshot.rehearsalCount() <= 0) {
            candidates.add(new RankedGap(90, new Gap(
                    "roadshow",
                    "完成一次计时路演并生成评分",
                    snapshot.rehearsalCount() > 0
                            ? "已有彩排记录，但还没有完成可用于复盘的评分。"
                            : "当前项目尚无已绑定彩排，无法验证讲解、演示和现场节奏。",
                    "high",
                    "/online-meeting",
                    "路演绑定与 AI 评分记录"
            )));
        }

        if (!hasPresentation(readyMaterials)) {
            boolean pending = safe(snapshot.materials()).stream().anyMatch(this::looksLikePresentation);
            candidates.add(new RankedGap(85, new Gap(
                    "presentation",
                    pending ? "完成路演材料审核" : "补齐可上场的项目路演材料",
                    pending
                            ? "已找到 PPT/项目方案，但尚未通过团队审核。"
                            : "材料库中未找到已审核的 PPT 或项目方案。",
                    "high",
                    "/script-editor?tab=ppt",
                    "项目材料与成果审核状态"
            )));
        }

        safe(snapshot.trackEvidenceRequirements()).stream()
                .filter(requirement -> !requirement.isBlank())
                .filter(requirement -> !materialMatches(readyMaterials, requirement))
                .limit(2)
                .forEach(requirement -> candidates.add(new RankedGap(75, new Gap(
                        "track-evidence-" + Integer.toHexString(requirement.hashCode()),
                        "补齐赛道证据：" + requirement,
                        "当前已审核材料中未找到可对应此赛道要求的证据，请上传后由团队复核。",
                        "medium",
                        "/script-editor?tab=materials",
                        "当前评分会话绑定的赛道证据结构"
                ))));

        if (!hasQuestionScript(readyMaterials)) {
            candidates.add(new RankedGap(60, new Gap(
                    "qa-script",
                    "整理答辩问答库与讲稿",
                    "材料库中未找到已审核的讲稿或答辩问答材料。",
                    "medium",
                    "/script-editor?tab=script",
                    "项目材料与成果审核状态"
            )));
        }

        return candidates.stream()
                .sorted(Comparator.comparingInt(RankedGap::rank).reversed())
                .map(RankedGap::gap)
                .limit(3)
                .toList();
    }

    private boolean isReady(MaterialFact material) {
        return material != null && READY_STATUSES.contains(upper(material.reviewStatus()));
    }

    private boolean hasPresentation(List<MaterialFact> materials) {
        return materials.stream().anyMatch(this::looksLikePresentation);
    }

    private boolean looksLikePresentation(MaterialFact material) {
        String type = upper(material == null ? "" : material.type());
        String text = searchable(material);
        return "PPT".equals(type) || "PRESENTATION".equals(type)
                || text.contains("ppt") || text.contains("路演稿") || text.contains("项目方案");
    }

    private boolean hasQuestionScript(List<MaterialFact> materials) {
        return materials.stream().anyMatch(material -> {
            String type = upper(material.type());
            String text = searchable(material);
            return "SCRIPT".equals(type) || text.contains("讲稿") || text.contains("逐字稿")
                    || text.contains("问答") || text.contains("答辩题");
        });
    }

    private boolean materialMatches(List<MaterialFact> materials, String requirement) {
        String needle = normalize(requirement);
        if (needle.isBlank()) return true;
        return materials.stream().map(this::searchable).anyMatch(text -> text.contains(needle));
    }

    private String searchable(MaterialFact material) {
        if (material == null) return "";
        return normalize(String.join(" ", clean(material.type(), ""), clean(material.name(), ""), clean(material.description(), "")));
    }

    private String normalize(String value) {
        return clean(value, "").toLowerCase(Locale.ROOT).replaceAll("[\\s\\p{Punct}，。；：、（）【】《》]+", "");
    }

    private String upper(String value) {
        return clean(value, "").toUpperCase(Locale.ROOT);
    }

    private String clean(String value, String fallback) {
        String text = value == null ? "" : value.trim();
        return text.isBlank() ? fallback : text;
    }

    private <T> List<T> safe(List<T> values) {
        return values == null ? List.of() : values;
    }

    public record Snapshot(
            List<MaterialFact> materials,
            List<String> trackEvidenceRequirements,
            List<IssueFact> issues,
            int rehearsalCount,
            boolean roadshowCompleted
    ) {}

    public record MaterialFact(String type, String name, String description, String reviewStatus) {}
    public record IssueFact(String title, String description, String severity, String status) {}
    public record Gap(String key, String title, String description, String severity, String actionPath, String source) {}
    private record RankedGap(int rank, Gap gap) {}
}
