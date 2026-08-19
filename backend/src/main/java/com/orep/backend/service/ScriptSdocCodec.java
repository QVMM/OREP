package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.orep.backend.entity.Script;

import java.util.List;
import java.util.Map;

/**
 * 讲稿步骤 JSON ↔ 智能文档 scriptSheet。
 */
public final class ScriptSdocCodec {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ScriptSdocCodec() {
    }

    public static String fromScript(Script script) {
        try {
            ObjectNode doc = MAPPER.createObjectNode();
            doc.put("type", "doc");
            ArrayNode content = doc.putArray("content");
            content.add(heading(script.getTitle() == null || script.getTitle().isBlank() ? "路演讲稿" : script.getTitle()));
            content.add(paragraph("分工已锁定。在正文里选中一句，点「问小启」。"));
            ObjectNode sheet = MAPPER.createObjectNode();
            sheet.put("type", "scriptSheet");
            ObjectNode attrs = sheet.putObject("attrs");
            if (script.getId() != null) attrs.put("scriptId", String.valueOf(script.getId()));
            attrs.put("contentVersion", ScriptService.currentVersion(script.getContentVersion()));
            ArrayNode steps = sheet.putArray("content");
            JsonNode chapters = parseChapters(script.getContent());
            if (chapters != null && chapters.isArray()) {
                for (JsonNode chapter : chapters) {
                    String chapterId = text(chapter, "id");
                    String chapterTitle = text(chapter, "title");
                    JsonNode stepArr = chapter.get("steps");
                    if (stepArr == null || !stepArr.isArray()) continue;
                    for (JsonNode step : stepArr) {
                        if (!step.isObject()) continue;
                        steps.add(stepNode(
                                text(step, "id"),
                                text(step, "role"),
                                text(step, "focus"),
                                text(step, "duration"),
                                text(step, "content"),
                                chapterId,
                                chapterTitle
                        ));
                    }
                }
            }
            if (steps.isEmpty()) {
                steps.add(stepNode("s1", "", "", "", "", "", ""));
            }
            content.add(sheet);
            return MAPPER.writeValueAsString(doc);
        } catch (Exception e) {
            throw new IllegalArgumentException("生成改稿文档失败: " + e.getMessage());
        }
    }

    public static String applyContentPatches(String sdocJson, List<Map<String, Object>> patches) {
        if (sdocJson == null || sdocJson.isBlank() || patches == null || patches.isEmpty()) {
            return sdocJson;
        }
        try {
            JsonNode root = MAPPER.readTree(sdocJson);
            if (!root.isObject()) return sdocJson;
            for (Map<String, Object> patch : patches) {
                if (patch == null) continue;
                if (!"content".equals(String.valueOf(patch.getOrDefault("field", "")))) continue;
                String stepId = String.valueOf(patch.getOrDefault("stepId", "")).trim();
                if (stepId.isEmpty()) continue;
                Object after = patch.get("after");
                replaceStepText((ObjectNode) root, stepId, after == null ? "" : String.valueOf(after));
            }
            return MAPPER.writeValueAsString(root);
        } catch (Exception e) {
            throw new IllegalArgumentException("回写智能文档失败: " + e.getMessage());
        }
    }

    public static String mergeIntoScript(String scriptContentJson, String sdocJson) {
        if (scriptContentJson == null || scriptContentJson.isBlank()) return scriptContentJson;
        try {
            JsonNode chapters = MAPPER.readTree(scriptContentJson);
            if (!chapters.isArray()) return scriptContentJson;
            JsonNode sdoc = sdocJson == null || sdocJson.isBlank() ? null : MAPPER.readTree(sdocJson);
            if (sdoc == null) return scriptContentJson;
            for (JsonNode chapter : chapters) {
                JsonNode steps = chapter.get("steps");
                if (steps == null || !steps.isArray()) continue;
                for (JsonNode step : steps) {
                    if (!step.isObject()) continue;
                    String id = text(step, "id");
                    String body = findStepText(sdoc, id);
                    if (body != null) {
                        ((ObjectNode) step).put("content", body);
                    }
                }
            }
            return MAPPER.writeValueAsString(chapters);
        } catch (Exception e) {
            throw new IllegalArgumentException("从文档同步讲稿失败: " + e.getMessage());
        }
    }

    public static boolean hasScriptSheet(String sdocJson) {
        try {
            JsonNode root = sdocJson == null || sdocJson.isBlank() ? null : MAPPER.readTree(sdocJson);
            if (root == null) return false;
            boolean[] found = {false};
            walk(root, node -> {
                if ("scriptSheet".equals(text(node, "type")) || "scriptStep".equals(text(node, "type"))) {
                    found[0] = true;
                }
            });
            return found[0];
        } catch (Exception e) {
            return false;
        }
    }

    public static String defaultChaptersJson(String body) {
        String text = body == null ? "" : body.trim();
        return "[{\"id\":\"c1\",\"title\":\"正文\",\"steps\":[{\"id\":\"s1\",\"role\":\"主讲人\",\"duration\":1,\"focus\":\"全文\",\"content\":"
                + jsonString(text) + ",\"notes\":\"\",\"transition\":\"\"}]}]";
    }

    public static int pageCountFromDocument(String sdocJson) {
        return pageCountFromPlain(extractPlainText(sdocJson));
    }

    /** 讲稿页数：按结构估，不靠「翻页」标记。没有标记时按场景和篇幅切开。 */
    public static int pageCountFromPlain(String plain) {
        return stepsFromPlain(plain).size();
    }

    public static String pageHealth(int pages) {
        if (pages <= 0) return "empty";
        if (pages < 38) return "low";
        if (pages > 45) return "high";
        return "ok";
    }

    public static String pageHealthLabel(int pages) {
        return switch (pageHealth(pages)) {
            case "ok" -> pages + " 页，健康";
            case "low" -> pages + " 页，偏少。健康是 38–45 页";
            case "high" -> pages + " 页，偏多。健康是 38–45 页";
            default -> "还看不出页数";
        };
    }

    public static List<Map<String, Object>> stepsFromDocument(String sdocJson) {
        String plain = extractPlainText(sdocJson);
        return stepsFromPlain(plain);
    }

    public static String chaptersFromDocument(String sdocJson) {
        List<Map<String, Object>> steps = stepsFromDocument(sdocJson);
        if (steps.isEmpty()) return null;
        try {
            ObjectNode chapter = MAPPER.createObjectNode();
            chapter.put("id", "c1");
            chapter.put("title", "正文");
            ArrayNode arr = chapter.putArray("steps");
            for (Map<String, Object> step : steps) {
                ObjectNode n = MAPPER.createObjectNode();
                n.put("id", String.valueOf(step.get("id")));
                n.put("role", String.valueOf(step.getOrDefault("role", "主讲人")));
                n.put("duration", 1);
                n.put("focus", String.valueOf(step.getOrDefault("focus", "")));
                n.put("content", String.valueOf(step.getOrDefault("content", "")));
                n.put("notes", "");
                n.put("transition", "");
                arr.add(n);
            }
            return MAPPER.writeValueAsString(new Object[]{chapter});
        } catch (Exception e) {
            return defaultChaptersJson(extractPlainText(sdocJson));
        }
    }

    public static List<Map<String, Object>> stepsFromPlain(String plain) {
        List<Map<String, Object>> out = new java.util.ArrayList<>();
        if (plain == null) return out;
        String cleaned = plain.replace("分工已锁定。在正文里选中一句，点「问小启」。", "").trim();
        if (cleaned.isBlank()) return out;
        List<String> beats = packBeats(splitUtterances(cleaned), 45);
        int i = 0;
        for (String t : beats) {
            if (t.length() < 2) continue;
            i += 1;
            if (t.length() > 400) t = t.substring(0, 400);
            java.util.Map<String, Object> row = new java.util.LinkedHashMap<>();
            row.put("id", "s" + i);
            row.put("role", firstRole(t));
            row.put("focus", "");
            row.put("content", t);
            out.add(row);
        }
        return out;
    }

    private static final String SCENE_SPLIT =
            "(?=首先进入)|(?=接下来)|(?=下面展示)|(?=针对这)|(?=我们系统的总体思路)|(?=请接收)|(?=在介绍项目之前)|(?=我们把这些烦恼)|(?=首先是硬件)|(?=接下来启用)|(?=系统功能)|(?=项目创新)|(?=应用价值)|(?=未来规划)|(?=我是本项目)|(?=项目的起点)|(?=进入第)|(?=痛点[一二三四1-4])|(?=第[一二三四五1-5]层)";

    private static List<String> splitUtterances(String cleaned) {
        List<String> raw = new java.util.ArrayList<>();
        for (String page : cleaned.split("（翻页）|\\(翻页\\)")) {
            for (String para : page.split("\\n+")) {
                String t = para.replaceAll("\\s+", " ").trim();
                if (t.startsWith("逐字稿全文")) t = t.substring("逐字稿全文".length()).trim();
                if (t.startsWith("路演讲稿")) t = t.substring("路演讲稿".length()).trim();
                if (t.length() < 2) continue;
                if (isHeading(t)) continue;
                if (looksLikeCode(t)) continue;
                if (t.length() > 180) {
                    for (String part : t.split(SCENE_SPLIT)) {
                        String one = part.trim();
                        if (one.length() >= 2 && !isHeading(one) && !looksLikeCode(one)) raw.add(one);
                    }
                } else {
                    raw.add(t);
                }
            }
        }
        return raw;
    }

    private static List<String> packBeats(List<String> raw, int max) {
        List<String> beats = new java.util.ArrayList<>();
        StringBuilder cur = new StringBuilder();
        for (String u : raw) {
            if (cur.length() > 0 && isSceneStart(u)) {
                beats.add(cur.toString().trim());
                cur.setLength(0);
            }
            if (cur.length() > 0) cur.append(' ');
            cur.append(u);
            if (cur.length() >= 160) {
                beats.add(cur.toString().trim());
                cur.setLength(0);
            }
        }
        if (cur.length() >= 2) beats.add(cur.toString().trim());
        while (beats.size() > max) mergeShortest(beats);
        return beats;
    }

    private static void mergeShortest(List<String> beats) {
        if (beats.size() < 2) return;
        int at = 0;
        int best = Integer.MAX_VALUE;
        for (int i = 0; i < beats.size() - 1; i++) {
            int n = beats.get(i).length() + beats.get(i + 1).length();
            if (n < best) {
                best = n;
                at = i;
            }
        }
        beats.set(at, (beats.get(at) + " " + beats.get(at + 1)).trim());
        beats.remove(at + 1);
    }

    private static boolean isHeading(String t) {
        return "逐字稿全文".equals(t) || "路演讲稿".equals(t);
    }

    private static boolean looksLikeCode(String t) {
        String s = t == null ? "" : t;
        if (s.contains("ustruct") || s.contains("async def") || s.contains("python复制")
                || s.contains("soil_moisture") || s.contains("= ustruct")
                || s.startsWith("temp =") || s.startsWith("\"soil_")
                || s.startsWith("\"co2\"") || s.contains("elif addr")
                || s.contains("await asyncio") || s.contains("sleep_ms")
                || s.contains("PyTorch 张量") || s.contains("raw_data")
                || s.startsWith("return ") || s.contains("# 空气传感器")) {
            return true;
        }
        int ascii = 0;
        for (int i = 0; i < s.length(); i++) if (s.charAt(i) < 128) ascii += 1;
        return s.length() >= 12 && ascii * 10 >= s.length() * 7 && (s.contains("=") || s.contains("{"));
    }

    private static boolean isSceneStart(String t) {
        return t.startsWith("首先进入") || t.startsWith("接下来") || t.startsWith("下面展示")
                || t.startsWith("针对这") || t.contains("总体思路") || t.startsWith("请接收")
                || t.startsWith("在介绍项目之前") || t.startsWith("我们把这些烦恼")
                || t.startsWith("首先是硬件") || t.startsWith("接下来启用")
                || t.contains("系统功能") || t.contains("项目创新") || t.contains("应用价值")
                || t.contains("未来规划") || t.contains("四大痛点") || t.contains("分为六个部分")
                || t.contains("我是本项目") || t.contains("项目的起点") || t.contains("五层")
                || t.contains("核心技能") || t.contains("进入第") || t.contains("痛点一")
                || t.contains("痛点二") || t.contains("痛点三") || t.contains("痛点四");
    }

    private static String firstRole(String t) {
        int colon = t.indexOf('：');
        if (colon > 0 && colon <= 12) {
            String role = t.substring(0, colon).trim();
            if (role.contains("经理") || role.contains("工程师") || role.contains("成员")) return role;
        }
        return "主讲人";
    }

    public static String extractPlainText(String sdocJson) {
        try {
            JsonNode root = sdocJson == null || sdocJson.isBlank() ? null : MAPPER.readTree(sdocJson);
            if (root == null) return "";
            return collectText(root).trim();
        } catch (Exception e) {
            return "";
        }
    }

    public static String ensureSheet(String sdocJson, Script script) {
        try {
            JsonNode parsed = sdocJson == null || sdocJson.isBlank()
                    ? MAPPER.readTree("{\"type\":\"doc\",\"content\":[]}")
                    : MAPPER.readTree(sdocJson);
            if (!parsed.isObject()) {
                return fromScript(script);
            }
            ObjectNode root = (ObjectNode) parsed;
            if (!root.has("content") || !root.get("content").isArray()) {
                root.putArray("content");
            }
            boolean[] found = {false};
            walk(root, node -> {
                if ("scriptSheet".equals(text(node, "type"))) {
                    found[0] = true;
                    ObjectNode attrs = node.has("attrs") && node.get("attrs").isObject()
                            ? (ObjectNode) node.get("attrs")
                            : node.putObject("attrs");
                    if (script.getId() != null) attrs.put("scriptId", String.valueOf(script.getId()));
                    attrs.put("contentVersion", ScriptService.currentVersion(script.getContentVersion()));
                }
            });
            if (!found[0]) {
                ArrayNode content = (ArrayNode) root.get("content");
                content.add(sheetFromScript(script));
            }
            return MAPPER.writeValueAsString(root);
        } catch (Exception e) {
            throw new IllegalArgumentException("补全讲稿表失败: " + e.getMessage());
        }
    }

    private static String jsonString(String raw) {
        try {
            return MAPPER.writeValueAsString(raw == null ? "" : raw);
        } catch (Exception e) {
            return "\"\"";
        }
    }

    private static ObjectNode sheetFromScript(Script script) {
        ObjectNode sheet = MAPPER.createObjectNode();
        sheet.put("type", "scriptSheet");
        ObjectNode attrs = sheet.putObject("attrs");
        if (script.getId() != null) attrs.put("scriptId", String.valueOf(script.getId()));
        attrs.put("contentVersion", ScriptService.currentVersion(script.getContentVersion()));
        ArrayNode steps = sheet.putArray("content");
        JsonNode chapters = parseChapters(script.getContent());
        if (chapters != null && chapters.isArray()) {
            for (JsonNode chapter : chapters) {
                String chapterId = text(chapter, "id");
                String chapterTitle = text(chapter, "title");
                JsonNode stepArr = chapter.get("steps");
                if (stepArr == null || !stepArr.isArray()) continue;
                for (JsonNode step : stepArr) {
                    if (!step.isObject()) continue;
                    steps.add(stepNode(
                            text(step, "id"),
                            text(step, "role"),
                            text(step, "focus"),
                            text(step, "duration"),
                            text(step, "content"),
                            chapterId,
                            chapterTitle
                    ));
                }
            }
        }
        if (steps.isEmpty()) {
            steps.add(stepNode("s1", "主讲人", "全文", "1", "", "c1", "正文"));
        }
        return sheet;
    }

    private static ObjectNode stepNode(
            String stepId, String role, String focus, String duration,
            String body, String chapterId, String chapterTitle
    ) {
        ObjectNode step = MAPPER.createObjectNode();
        step.put("type", "scriptStep");
        ObjectNode attrs = step.putObject("attrs");
        attrs.put("stepId", stepId == null ? "" : stepId);
        attrs.put("role", role == null ? "" : role);
        attrs.put("focus", focus == null ? "" : focus);
        attrs.put("duration", duration == null ? "" : duration);
        attrs.put("chapterId", chapterId == null ? "" : chapterId);
        attrs.put("chapterTitle", chapterTitle == null ? "" : chapterTitle);
        ArrayNode content = step.putArray("content");
        content.add(paragraph(body == null ? "" : body));
        return step;
    }

    private static ObjectNode heading(String text) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("type", "heading");
        node.putObject("attrs").put("level", 1);
        ArrayNode content = node.putArray("content");
        if (text != null && !text.isBlank()) {
            ObjectNode t = MAPPER.createObjectNode();
            t.put("type", "text");
            t.put("text", text);
            content.add(t);
        }
        return node;
    }

    private static ObjectNode paragraph(String text) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("type", "paragraph");
        if (text != null && !text.isEmpty()) {
            ObjectNode t = MAPPER.createObjectNode();
            t.put("type", "text");
            t.put("text", text);
            node.putArray("content").add(t);
        }
        return node;
    }

    private static void replaceStepText(ObjectNode root, String stepId, String after) {
        walk(root, node -> {
            if (!"scriptStep".equals(text(node, "type"))) return;
            JsonNode attrs = node.get("attrs");
            if (attrs == null || !stepId.equals(text(attrs, "stepId"))) return;
            ArrayNode content = MAPPER.createArrayNode();
            content.add(paragraph(after));
            node.set("content", content);
        });
    }

    private static String findStepText(JsonNode root, String stepId) {
        if (stepId == null || stepId.isBlank()) return null;
        String[] found = {null};
        walk(root, node -> {
            if (!"scriptStep".equals(text(node, "type"))) return;
            JsonNode attrs = node.get("attrs");
            if (attrs == null || !stepId.equals(text(attrs, "stepId"))) return;
            found[0] = collectText(node.get("content"));
        });
        return found[0];
    }

    private static void walk(JsonNode node, java.util.function.Consumer<ObjectNode> visit) {
        if (node == null) return;
        if (node.isObject()) {
            visit.accept((ObjectNode) node);
            JsonNode children = node.get("content");
            if (children != null && children.isArray()) {
                for (JsonNode child : children) walk(child, visit);
            }
        } else if (node.isArray()) {
            for (JsonNode child : node) walk(child, visit);
        }
    }

    private static String collectText(JsonNode node) {
        if (node == null) return "";
        if (node.isTextual()) return node.asText("");
        if (node.has("text")) return node.get("text").asText("");
        StringBuilder sb = new StringBuilder();
        if (node.isArray()) {
            for (JsonNode child : node) {
                String part = collectText(child);
                if (part.isEmpty()) continue;
                if (sb.length() > 0 && "paragraph".equals(text(child, "type"))) sb.append('\n');
                sb.append(part);
            }
            return sb.toString();
        }
        if (node.has("content")) return collectText(node.get("content"));
        return "";
    }

    private static JsonNode parseChapters(String content) {
        if (content == null || content.isBlank()) return null;
        try {
            return MAPPER.readTree(content);
        } catch (Exception e) {
            return null;
        }
    }

    private static String text(JsonNode node, String key) {
        if (node == null || !node.has(key) || node.get(key).isNull()) return "";
        return node.get(key).asText("");
    }
}
