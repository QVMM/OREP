package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 评分条目 → 讲稿步骤的保守对照。不新增评分里没有的扣分。
 */
public final class ScriptScoreRevisePlanner {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Set<String> STOP = Set.of(
            "我们", "评委", "老师", "这个", "可以", "一个", "没有", "不是", "进行", "问题",
            "需要", "以及", "如果", "因为", "所以", "还是", "已经", "自己", "他们", "项目",
            "今天", "一下", "一种", "部分", "内容", "方面", "情况"
    );

    private ScriptScoreRevisePlanner() {
    }

    public static List<Map<String, Object>> flattenSteps(String chaptersJson) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (chaptersJson == null || chaptersJson.isBlank()) return out;
        try {
            JsonNode root = MAPPER.readTree(chaptersJson);
            if (!root.isArray()) return out;
            for (JsonNode chapter : root) {
                JsonNode steps = chapter.get("steps");
                if (steps == null || !steps.isArray()) continue;
                for (JsonNode step : steps) {
                    if (!step.isObject()) continue;
                    String id = text(step, "id");
                    if (id.isEmpty()) continue;
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", id);
                    row.put("role", text(step, "role"));
                    row.put("focus", text(step, "focus"));
                    row.put("content", text(step, "content"));
                    out.add(row);
                }
            }
        } catch (Exception ignored) {
            return List.of();
        }
        return out;
    }

    public static List<Map<String, Object>> normalizeItems(Object raw, String reportId) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (!(raw instanceof List<?> list)) return out;
        int i = 0;
        for (Object el : list) {
            i += 1;
            Map<String, Object> src = asMap(el);
            if (src == null) {
                if (el instanceof String s && !s.isBlank()) {
                    src = Map.of("title", s);
                } else {
                    continue;
                }
            }
            String title = first(src, "title", "issue", "name", "suggestion", "description");
            String reason = first(src, "reason", "issue", "suggestion", "why", "detail");
            if (title.isEmpty() && reason.isEmpty()) continue;
            String id = first(src, "id", "itemId", "scoreItemId");
            if (id.isEmpty()) id = "score-" + (reportId == null ? "x" : reportId) + "-" + i;
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", id);
            item.put("title", title.isEmpty() ? reason : title);
            item.put("reason", reason);
            item.put("dimension", first(src, "dimension", "dimensionName"));
            out.add(item);
        }
        return out;
    }

    public static List<Map<String, Object>> plan(List<Map<String, Object>> items, List<Map<String, Object>> steps) {
        List<Map<String, Object>> diagnosis = new ArrayList<>();
        List<Map<String, Object>> safeSteps = steps == null ? List.of() : steps;
        if (items == null) return diagnosis;
        for (Map<String, Object> item : items) {
            Map<String, Object> row = new LinkedHashMap<>(item);
            Map<String, Object> hit = bestStep(item, safeSteps);
            if (hit == null) {
                row.put("mapped", false);
            } else {
                row.put("mapped", true);
                row.put("stepId", hit.get("id"));
                row.put("role", hit.get("role"));
                row.put("focus", hit.get("focus"));
                row.put("stepContent", hit.get("content"));
            }
            diagnosis.add(row);
        }
        return diagnosis;
    }

    static Map<String, Object> bestStep(Map<String, Object> item, List<Map<String, Object>> steps) {
        Set<String> tokens = tokens(String.valueOf(item.getOrDefault("title", "")) + " " + item.getOrDefault("reason", ""));
        if (tokens.size() < 2) return null;
        Map<String, Object> best = null;
        int bestScore = 0;
        int second = 0;
        for (Map<String, Object> step : steps) {
            Set<String> hay = tokens(String.valueOf(step.getOrDefault("role", ""))
                    + " " + step.getOrDefault("focus", "")
                    + " " + step.getOrDefault("content", ""));
            int score = 0;
            for (String t : tokens) {
                if (hay.contains(t)) score += 1;
            }
            if (score > bestScore) {
                second = bestScore;
                bestScore = score;
                best = step;
            } else if (score > second) {
                second = score;
            }
        }
        if (best == null || bestScore < 2 || bestScore <= second) return null;
        return best;
    }

    static Set<String> tokens(String raw) {
        String text = raw == null ? "" : raw.toLowerCase(Locale.ROOT);
        Set<String> out = new LinkedHashSet<>();
        StringBuilder latin = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (Character.isLetterOrDigit(c) && c < 128) {
                latin.append(c);
                continue;
            }
            flushLatin(latin, out);
            if (isCjk(c) && i + 1 < text.length() && isCjk(text.charAt(i + 1))) {
                String gram = text.substring(i, i + 2);
                if (!STOP.contains(gram)) out.add(gram);
            }
        }
        flushLatin(latin, out);
        return out;
    }

    private static void flushLatin(StringBuilder latin, Set<String> out) {
        if (latin.length() >= 3) out.add(latin.toString());
        latin.setLength(0);
    }

    private static boolean isCjk(char c) {
        Character.UnicodeBlock b = Character.UnicodeBlock.of(c);
        return b == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS
                || b == Character.UnicodeBlock.CJK_COMPATIBILITY_IDEOGRAPHS;
    }

    private static String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? "" : v.asText("").trim();
    }

    private static String first(Map<String, Object> src, String... keys) {
        for (String k : keys) {
            Object v = src.get(k);
            if (v != null && !String.valueOf(v).isBlank()) return String.valueOf(v).trim();
        }
        return "";
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object el) {
        if (el instanceof Map<?, ?> m) return (Map<String, Object>) m;
        return null;
    }
}
