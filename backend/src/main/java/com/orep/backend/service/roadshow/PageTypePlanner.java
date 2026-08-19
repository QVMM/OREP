package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class PageTypePlanner {

    private PageTypePlanner() {
    }

    @SuppressWarnings("unchecked")
    public static List<Map<String, Object>> plan(List<Map<String, Object>> propositions) {
        List<Map<String, Object>> pages = new ArrayList<>();
        if (propositions == null) return pages;
        for (Map<String, Object> prop : propositions) {
            if (prop.get("printPage") == null) continue;
            if ("logistics".equals(prop.get("act"))) continue;
            Map<String, Object> on = prop.get("onSlide") instanceof Map<?, ?> m
                    ? (Map<String, Object>) m : Map.of();
            String act = String.valueOf(prop.getOrDefault("act", "hook"));
            String number = str(on.get("number"));
            String title = firstNonBlank(str(on.get("title")), clip(str(prop.get("spoken")), 16));
            String line = firstNonBlank(str(on.get("line")), "");
            String type = pageType(act, number);
            Map<String, Object> page = new LinkedHashMap<>();
            page.put("page", prop.get("printPage"));
            page.put("pageType", type);
            page.put("kicker", kicker(type));
            page.put("title", title);
            page.put("number", number);
            page.put("line", line);
            page.put("blocks", blocks(type, line, str(prop.get("spoken"))));
            page.put("stepId", prop.get("stepId"));
            page.put("role", prop.get("role"));
            pages.add(page);
        }
        return pages;
    }

    static String pageType(String act, String number) {
        if (number.contains("→") || number.contains("->")) return "contrast";
        return switch (act) {
            case "problem" -> "problem";
            case "cause" -> "process";
            case "method" -> "architecture";
            case "demo" -> "demo";
            case "evidence" -> "evidence";
            case "craft", "team" -> "list";
            case "close" -> "close";
            default -> "cover";
        };
    }

    static String kicker(String type) {
        return switch (type) {
            case "problem" -> "问题";
            case "contrast" -> "对比";
            case "architecture" -> "架构";
            case "process" -> "流程";
            case "demo" -> "实操";
            case "evidence" -> "证据";
            case "list" -> "要点";
            case "close" -> "收束";
            default -> "封面";
        };
    }

    static List<String> blocks(String type, String line, String spoken) {
        if ("architecture".equals(type) || "process".equals(type) || "list".equals(type)) {
            String raw = !line.isBlank() ? line : spoken;
            String[] parts = raw.split("[/·、→]|\\s+");
            List<String> out = new ArrayList<>();
            for (String p : parts) {
                String t = p.trim();
                if (t.length() >= 1 && t.length() <= 8) out.add(t);
                if (out.size() >= 6) break;
            }
            return out;
        }
        return List.of();
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }

    private static String firstNonBlank(String a, String b) {
        return a == null || a.isBlank() ? b : a;
    }

    private static String clip(String s, int n) {
        if (s == null) return "";
        return s.length() <= n ? s : s.substring(0, n);
    }
}
