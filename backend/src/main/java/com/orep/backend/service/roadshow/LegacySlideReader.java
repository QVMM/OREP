package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 按页分档：能改字 / 部分 / 图 / 空。不猜图上的字。
 */
public final class LegacySlideReader {

    private static final Pattern TEXT = Pattern.compile("<a:t[^>]*>(.*?)</a:t>", Pattern.DOTALL);
    private static final Pattern BLIP = Pattern.compile("<a:blip\\b");

    private LegacySlideReader() {
    }

    public static List<Map<String, Object>> grade(List<String> slideXml) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (slideXml == null) return out;
        List<List<String>> all = new ArrayList<>();
        int i = 1;
        for (String xml : slideXml) {
            List<String> texts = textsOf(xml);
            all.add(texts);
            out.add(gradeOne(i++, xml == null ? "" : xml, texts));
        }
        java.util.Map<String, Integer> freq = new java.util.HashMap<>();
        for (List<String> texts : all) {
            for (String t : new java.util.LinkedHashSet<>(texts)) {
                if (t.length() >= 2 && t.length() <= 8) freq.merge(t, 1, Integer::sum);
            }
        }
        int threshold = Math.max(3, (int) Math.ceil(out.size() * 0.35));
        java.util.Set<String> chrome = new java.util.HashSet<>();
        freq.forEach((k, v) -> {
            if (v >= threshold) chrome.add(k);
        });
        for (int p = 0; p < out.size(); p++) {
            List<String> unique = new ArrayList<>();
            for (String t : all.get(p)) {
                if (!chrome.contains(t)) unique.add(t);
            }
            if (unique.isEmpty()) unique = all.get(p);
            List<String> lines = unique.subList(0, Math.min(unique.size(), 8));
            String excerpt = unique.isEmpty() ? "" : String.join(" ", unique.subList(0, Math.min(unique.size(), 4)));
            if (excerpt.length() > 72) excerpt = excerpt.substring(0, 72) + "…";
            out.get(p).put("excerpt", excerpt);
            out.get(p).put("lines", new ArrayList<>(lines));
            out.get(p).put("searchText", String.join(" ", unique));
        }
        return out;
    }

    static Map<String, Object> gradeOne(int page, String xml, List<String> texts) {
        boolean hasPic = BLIP.matcher(xml).find();
        String grade;
        String label;
        if (texts.isEmpty() && !hasPic) {
            grade = "empty";
            label = "空页";
        } else if (texts.isEmpty()) {
            grade = "picture";
            label = "这页是图";
        } else if (hasPic) {
            grade = "partial";
            label = "只能改一部分";
        } else {
            grade = "editable";
            label = "能改字";
        }
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("page", page);
        row.put("grade", grade);
        row.put("label", label);
        row.put("excerpt", texts.isEmpty() ? "" : String.join(" ", texts.subList(0, Math.min(texts.size(), 3))));
        row.put("searchText", String.join(" ", texts));
        row.put("textCount", texts.size());
        return row;
    }

    static List<String> textsOf(String xml) {
        List<String> texts = new ArrayList<>();
        if (xml == null) return texts;
        Matcher m = TEXT.matcher(xml);
        while (m.find()) {
            String t = unescape(m.group(1)).trim();
            if (t.isBlank() || t.contains("<") || t.contains(">") || t.length() > 80) continue;
            if (junkLine(t)) continue;
            texts.add(t);
        }
        return texts;
    }

    static String unescape(String raw) {
        if (raw == null) return "";
        return raw.replace("&quot;", "\"")
                .replace("&apos;", "'")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&");
    }

    static boolean junkLine(String t) {
        if ("按讲稿".equals(t) || "本次不讲".equals(t) || "这页台上不翻".equals(t) || "原件里还在".equals(t)) {
            return true;
        }
        if (t.contains("nitrogen") || t.contains("raw_data") || t.contains("ustruct") || t.contains("async def")) {
            return true;
        }
        return t.startsWith("\"") && t.contains(":");
    }
}
