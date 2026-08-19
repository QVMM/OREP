package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 从讲稿抽可上页的数。金额没有材料来源时不建令牌。
 */
public final class EvidenceTokenizer {

    private static final Pattern PERCENT = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*%");
    private static final Pattern UNIT = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*(万|千|元|秒|分钟|毫秒|项|个|步|层|园|棚|颗)");
    private static final Pattern MONEY = Pattern.compile("万|元|回本|节约");
    private static final Pattern CONTRAST = Pattern.compile("从\\s*(\\d+(?:\\.\\d+)?\\s*%)\\s*降到\\s*(\\d+(?:\\.\\d+)?\\s*%)");

    private EvidenceTokenizer() {
    }

    public static List<Map<String, Object>> extract(List<Map<String, Object>> steps) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (steps == null) return out;
        int i = 0;
        for (Map<String, Object> step : steps) {
            String id = String.valueOf(step.getOrDefault("id", "s" + i));
            String content = String.valueOf(step.getOrDefault("content", ""));
            i += 1;
            Matcher contrast = CONTRAST.matcher(content);
            if (contrast.find()) {
                out.add(token("c_" + id, "contrast",
                        contrast.group(1).replaceAll("\\s+", "") + " → " + contrast.group(2).replaceAll("\\s+", ""),
                        "对比", id));
            }
            if (looksLikeCode(content)) {
                continue;
            }
            Matcher pct = PERCENT.matcher(content);
            while (pct.find()) {
                String surface = pct.group(1) + "%";
                if (!plausiblePercent(pct.group(1))) continue;
                out.add(token("m_" + id + "_" + surface, "metric", surface, nounNear(content, pct.start()), id));
            }
            Matcher unit = UNIT.matcher(content);
            while (unit.find()) {
                String u = unit.group(2);
                if (u.equals("万") || u.equals("元") || u.equals("千")) {
                    continue;
                }
                if (MONEY.matcher(content).find() && (u.equals("个") || u.equals("项"))) {
                    // keep counts even if 节约 appears elsewhere
                }
                String surface = unit.group(1) + u;
                if (out.stream().anyMatch(t -> surface.equals(t.get("surface")) && id.equals(t.get("stepId")))) {
                    continue;
                }
                out.add(token("u_" + id + "_" + surface, "metric", surface, nounNear(content, unit.start()), id));
            }
        }
        return out;
    }

    private static boolean looksLikeCode(String content) {
        return content.contains("async def") || content.contains("python复制")
                || content.contains("UART") || content.contains("Modbus");
    }

    private static boolean plausiblePercent(String raw) {
        try {
            double n = Double.parseDouble(raw);
            return n > 0 && n <= 100;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    private static String nounNear(String content, int at) {
        int from = Math.max(0, at - 8);
        String window = content.substring(from, Math.min(content.length(), at));
        if (window.contains("损耗")) return "损耗";
        if (window.contains("精度") || window.contains("精确")) return "精度";
        if (window.contains("试点") || window.contains("棚")) return "试点";
        return "";
    }

    private static Map<String, Object> token(String id, String kind, String surface, String noun, String stepId) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", id);
        row.put("kind", kind);
        row.put("surface", surface);
        row.put("noun", noun);
        row.put("stepId", stepId);
        return row;
    }
}
