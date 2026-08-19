package com.orep.backend.service;

import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class RoadshowMemoryAnalyzer {

    public Map<String, Object> buildSummary(List<Map<String, Object>> rows) {
        List<Map<String, Object>> rounds = new ArrayList<>(rows == null ? List.of() : rows);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("rounds", rounds);
        result.put("priorIssueReview", priorIssueReview(rounds));
        result.put("newIssues", newIssues(rounds));
        result.put("fullScoreGap", fullScoreGap(rounds));
        result.put("trainingPlan", trainingPlan(rounds));
        result.put("timeline", timeline(rounds));
        result.put("improvementDelta", improvementDelta(rounds));
        result.putAll(memoryStatus(rounds));
        return result;
    }

    private Map<String, Object> memoryStatus(List<Map<String, Object>> rounds) {
        if (rounds.isEmpty()) {
            return Map.of(
                    "memoryStatus", "EMPTY",
                    "memoryStatusText", "暂无已完成的AI评分，完成一次路演评分后开始建立记忆。"
            );
        }
        if (rounds.size() == 1) {
            return Map.of(
                    "memoryStatus", "SINGLE_ROUND",
                    "memoryStatusText", "已完成1轮AI评分，下一轮评分后会自动复检本轮扣分项。"
            );
        }
        return Map.of(
                "memoryStatus", "MULTI_ROUND",
                "memoryStatusText", "已形成多轮AI评分记忆，本轮会对比历史扣分项与新增问题。"
        );
    }

    private List<Map<String, Object>> priorIssueReview(List<Map<String, Object>> rounds) {
        if (rounds.size() < 2) return List.of();
        Set<String> currentIssues = issueTitles(rounds.get(rounds.size() - 1));
        List<Map<String, Object>> review = new ArrayList<>();
        Map<String, Object> previousRound = rounds.get(rounds.size() - 2);
        for (String title : issueTitles(rounds.get(rounds.size() - 2))) {
            boolean stillExists = containsSimilarIssue(currentIssues, title);
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("title", title);
            item.put("status", stillExists ? "not_resolved" : "resolved");
            item.put("conclusion", stillExists ? "本轮仍出现同类问题，需要继续训练。" : "本轮未再次出现，初步判断已修复。");
            item.put("recoveredScore", stillExists ? 0 : 1);
            item.put("evidenceAnchors", evidenceAnchorsFor(previousRound, title, rounds.size() - 1));
            review.add(item);
        }
        return review;
    }

    private List<Map<String, Object>> newIssues(List<Map<String, Object>> rounds) {
        if (rounds.isEmpty()) return List.of();
        Set<String> previous = new LinkedHashSet<>();
        for (int i = 0; i < rounds.size() - 1; i++) previous.addAll(issueTitles(rounds.get(i)));
        List<Map<String, Object>> issues = new ArrayList<>();
        for (String title : issueTitles(rounds.get(rounds.size() - 1))) {
            if (!containsSimilarIssue(previous, title)) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("title", title);
                item.put("status", "new");
                item.put("conclusion", "本轮新暴露的问题，不能被上轮修复奖励抵消。");
                item.put("evidenceAnchors", evidenceAnchorsFor(rounds.get(rounds.size() - 1), title, rounds.size()));
                issues.add(item);
            }
        }
        return issues;
    }

    private Map<String, Object> fullScoreGap(List<Map<String, Object>> rounds) {
        if (rounds.isEmpty()) return Map.of("reasons", List.of());
        Map<String, Object> latest = rounds.get(rounds.size() - 1);
        Map<String, Object> calibration = mapValue(latest.get("scoreCalibration"));
        Object ceiling = firstNonNull(calibration.get("technical_ceiling_score"), calibration.get("competition_ceiling_score"), latest.get("aiScore"));
        Object skill = firstNonNull(calibration.get("skill_score"), "-");
        Object raw = firstNonNull(calibration.get("original_score"), latest.get("aiScore"));
        List<Object> reasons = listValue(calibration.get("ceiling_reasons"));
        if (reasons.isEmpty()) reasons = List.of("本轮暂无技术校准原因，建议补充现场演示与测试证据。");
        return Map.of(
                "rawScore", raw,
                "ceilingScore", ceiling,
                "skillScore", skill,
                "reasons", reasons
        );
    }

    private List<Map<String, Object>> trainingPlan(List<Map<String, Object>> rounds) {
        if (rounds.isEmpty()) return List.of();
        Map<String, Object> latest = rounds.get(rounds.size() - 1);
        List<Object> priorities = listValue(latest.get("improvementPriorities"));
        List<Map<String, Object>> plan = new ArrayList<>();
        int index = 1;
        for (Object item : priorities) {
            Map<String, Object> map = mapValue(item);
            String issue = text(firstNonNull(map.get("issue"), map.get("title"), map.get("dimension"), item), "训练任务");
            String suggestion = text(firstNonNull(map.get("suggestion"), map.get("action"), map.get("description")), "下一轮彩排复检该问题。");
            plan.add(Map.of(
                    "priority", index++,
                    "issue", issue,
                    "suggestion", suggestion,
                    "acceptance", acceptanceFor(issue)
            ));
        }
        return plan;
    }

    private List<Map<String, Object>> timeline(List<Map<String, Object>> rounds) {
        List<Map<String, Object>> timeline = new ArrayList<>();
        for (int i = 0; i < rounds.size(); i++) {
            Map<String, Object> row = rounds.get(i);
            timeline.add(Map.of(
                    "roundNo", i + 1,
                    "meetingId", row.getOrDefault("meetingId", ""),
                    "title", row.getOrDefault("meetingTitle", "第" + (i + 1) + "轮路演"),
                    "score", number(row.get("aiScore")),
                    "issueCount", issueTitles(row).size()
            ));
        }
        return timeline;
    }

    private double improvementDelta(List<Map<String, Object>> rounds) {
        if (rounds.size() < 2) return 0;
        return number(rounds.get(rounds.size() - 1).get("aiScore")) - number(rounds.get(0).get("aiScore"));
    }

    private Set<String> issueTitles(Map<String, Object> row) {
        Set<String> titles = new LinkedHashSet<>();
        for (Object item : listValue(row.get("criticalIssues"))) {
            Map<String, Object> map = mapValue(item);
            titles.add(text(firstNonNull(map.get("title"), map.get("issue"), map.get("problem"), item), ""));
        }
        titles.remove("");
        return titles;
    }

    private boolean containsSimilarIssue(Set<String> candidates, String title) {
        for (String candidate : candidates) {
            if (sameIssue(candidate, title)) return true;
        }
        return false;
    }

    private boolean sameIssue(String left, String right) {
        String a = normalizeIssueTitle(left);
        String b = normalizeIssueTitle(right);
        if (a.isBlank() || b.isBlank()) return false;
        if (a.equals(b) || a.contains(b) || b.contains(a)) return true;
        if (longestCommonSubstringLength(a, b) >= 6) return true;
        Set<String> leftBigrams = ngrams(a, 2);
        Set<String> rightBigrams = ngrams(b, 2);
        double dice = diceSimilarity(leftBigrams, rightBigrams);
        if (dice >= 0.34 && overlapSize(leftBigrams, rightBigrams) >= 5) return true;
        double trigramDice = diceSimilarity(ngrams(a, 3), ngrams(b, 3));
        return trigramDice >= 0.36 || characterCoverage(a, b) >= 0.72;
    }

    private int overlapSize(Set<String> left, Set<String> right) {
        Set<String> overlap = new LinkedHashSet<>(left);
        overlap.retainAll(right);
        return overlap.size();
    }

    private String normalizeIssueTitle(String value) {
        if (value == null) return "";
        return value
                .replaceAll("[\\s，。,.!！?？:：；;（）()【】\\[\\]“”\"'、]+", "")
                .replace("本轮", "")
                .replace("上轮", "")
                .replace("需要", "")
                .replace("导致", "")
                .replace("出现", "")
                .replace("问题", "")
                .replace("严重", "")
                .replace("仍然", "")
                .replace("仍", "")
                .replace("无法", "")
                .trim();
    }

    private double diceSimilarity(Set<String> left, Set<String> right) {
        if (left.isEmpty() || right.isEmpty()) return 0;
        Set<String> overlap = new LinkedHashSet<>(left);
        overlap.retainAll(right);
        return overlap.size() * 2.0 / (left.size() + right.size());
    }

    private double characterCoverage(String left, String right) {
        Set<String> leftChars = characterSet(left);
        Set<String> rightChars = characterSet(right);
        if (leftChars.isEmpty() || rightChars.isEmpty()) return 0;
        Set<String> overlap = new LinkedHashSet<>(leftChars);
        overlap.retainAll(rightChars);
        return overlap.size() / (double) Math.min(leftChars.size(), rightChars.size());
    }

    private Set<String> ngrams(String value, int size) {
        Set<String> tokens = new LinkedHashSet<>();
        if (value == null) return tokens;
        String text = normalizeIssueTitle(value);
        if (text.length() < size) {
            if (!text.isBlank()) tokens.add(text);
            return tokens;
        }
        for (int i = 0; i <= text.length() - size; i++) {
            tokens.add(text.substring(i, i + size));
        }
        return tokens;
    }

    private int longestCommonSubstringLength(String left, String right) {
        int best = 0;
        int[][] dp = new int[left.length() + 1][right.length() + 1];
        for (int i = 1; i <= left.length(); i++) {
            for (int j = 1; j <= right.length(); j++) {
                if (left.charAt(i - 1) == right.charAt(j - 1)) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                    best = Math.max(best, dp[i][j]);
                }
            }
        }
        return best;
    }

    private Set<String> characterSet(String value) {
        Set<String> chars = new LinkedHashSet<>();
        for (int i = 0; i < value.length(); i++) {
            chars.add(String.valueOf(value.charAt(i)));
        }
        return chars;
    }

    private List<Map<String, Object>> evidenceAnchorsFor(Map<String, Object> row, String issueTitle, int roundNo) {
        List<Map<String, Object>> matched = new ArrayList<>();
        List<Map<String, Object>> fallback = new ArrayList<>();
        String needle = issueTitle == null ? "" : issueTitle.trim();
        for (Object item : listValue(row.get("evidenceAnchors"))) {
            Map<String, Object> raw = mapValue(item);
            if (raw.isEmpty()) continue;
            String summary = text(firstNonNull(raw.get("summary"), raw.get("text"), raw.get("description"), raw.get("evidence")), "");
            String sourceRef = text(firstNonNull(raw.get("sourceRef"), raw.get("source_ref"), raw.get("timestamp"), raw.get("frameId"), raw.get("frame_id")), "");
            String type = text(firstNonNull(raw.get("type"), raw.get("anchorType"), raw.get("anchor_type")), "evidence");
            if (isLowValueTranscript(type, summary)) continue;
            Map<String, Object> anchor = new LinkedHashMap<>();
            anchor.put("type", type);
            anchor.put("summary", summary.isBlank() ? "该轮评分存在相关证据，可回看会议材料复核。" : summary);
            anchor.put("sourceRef", sourceRef);
            anchor.put("roundNo", roundNo);
            anchor.put("meetingId", row.getOrDefault("meetingId", ""));
            if (anchorMatchesIssue(needle, summary)) {
                matched.add(anchor);
            } else if (!isTranscriptAnchor(type)) {
                fallback.add(anchor);
            }
            if (matched.size() >= 3) break;
        }
        if (!matched.isEmpty()) return matched.stream().limit(3).toList();
        return fallback.stream().limit(1).toList();
    }

    private boolean anchorMatchesIssue(String issueTitle, String summary) {
        if (issueTitle == null || issueTitle.isBlank() || summary == null || summary.isBlank()) return false;
        if (summary.contains(issueTitle) || issueTitle.contains(summary)) return true;
        String issue = normalizeIssueTitle(issueTitle);
        String evidence = normalizeIssueTitle(summary);
        if (issue.isBlank() || evidence.isBlank()) return false;
        if (longestCommonSubstringLength(issue, evidence) >= 5) return true;
        Set<String> issueBigrams = ngrams(issue, 2);
        Set<String> evidenceBigrams = ngrams(evidence, 2);
        return overlapSize(issueBigrams, evidenceBigrams) >= 2 || diceSimilarity(issueBigrams, evidenceBigrams) >= 0.28;
    }

    private boolean isTranscriptAnchor(String type) {
        return type != null && type.toLowerCase(Locale.ROOT).contains("transcript");
    }

    private boolean isLowValueTranscript(String type, String summary) {
        if (!isTranscriptAnchor(type)) return false;
        String text = summary == null ? "" : summary.replaceAll("[\\s，。,.!！?？]+", "");
        if (text.length() <= 6) return true;
        return Set.of("大家好", "各位评委大家好", "老师好", "收到", "好的", "谢谢").contains(text);
    }

    private String acceptanceFor(String issue) {
        if (issue.contains("演示")) return "下一轮现场演示需稳定跑通核心流程，并提供关键结果画面。";
        if (issue.contains("测试") || issue.contains("数据")) return "下一轮需展示性能、准确率、稳定性或日志等可复核数据。";
        if (issue.contains("技术")) return "下一轮需用口头、PPT、现场演示和运行证据交叉印证。";
        return "下一轮评分时应能找到明确转写、关键帧或演示证据。";
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> converted = new LinkedHashMap<>();
            map.forEach((key, item) -> converted.put(String.valueOf(key), item));
            return converted;
        }
        return new LinkedHashMap<>();
    }

    @SuppressWarnings("unchecked")
    private List<Object> listValue(Object value) {
        if (value instanceof List<?> list) return (List<Object>) list;
        if (value == null) return List.of();
        return List.of(value);
    }

    private Object firstNonNull(Object... values) {
        for (Object value : values) if (value != null) return value;
        return null;
    }

    private String text(Object value, String fallback) {
        if (value == null) return fallback;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? fallback : text;
    }

    private double number(Object value) {
        if (value instanceof Number number) return number.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (Exception ignored) {
            return 0;
        }
    }
}
