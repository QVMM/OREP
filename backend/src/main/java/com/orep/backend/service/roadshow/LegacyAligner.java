package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 讲稿段对旧页。只给建议，不改文件。
 */
public final class LegacyAligner {

    private LegacyAligner() {
    }

    public static List<Map<String, Object>> align(List<Map<String, Object>> propositions, List<Map<String, Object>> pages) {
        List<Map<String, Object>> rows = new ArrayList<>();
        if (pages == null) pages = List.of();
        Set<Integer> used = new HashSet<>();

        int lastPage = 0;
        if (propositions != null) {
            for (Map<String, Object> prop : propositions) {
                String act = String.valueOf(prop.getOrDefault("act", ""));
                if ("logistics".equals(act) || prop.get("printPage") == null || "".equals(prop.get("printPage"))) {
                    rows.add(row("hold", null, prop, null, "这段是交接或现场，不配新页。PPT 停在当前页。"));
                    continue;
                }
                String needle = hay(prop);
                Map<String, Object> best = null;
                int bestScore = 0;
                int second = 0;
                for (Map<String, Object> page : pages) {
                    Integer n = asInt(page.get("page"));
                    if (n != null && used.contains(n)) continue;
                    int s = overlap(needle, search(page));
                    if (lastPage > 0 && n != null && n < lastPage) s = Math.max(0, s - 3);
                    if (s > bestScore) {
                        second = bestScore;
                        bestScore = s;
                        best = page;
                    } else if (s > second) {
                        second = s;
                    }
                }
                if (best == null || bestScore < 2) {
                    rows.add(row("add", null, prop, null, "讲稿有这段，这份 PPT 里对不上。后面要补一页。"));
                    continue;
                }
                Integer chosen = asInt(best.get("page"));
                if (chosen != null) {
                    used.add(chosen);
                    lastPage = chosen;
                }
                String grade = String.valueOf(best.getOrDefault("grade", ""));
                String number = onSlide(prop).getOrDefault("number", "").toString();
                boolean numberClash = !number.isBlank() && number.contains("%")
                        && search(best).length() > 24 && !search(best).contains(number);
                String title = onSlide(prop).getOrDefault("title", "");
                String titleHead = title.length() <= 4 ? title : title.substring(0, 4);
                boolean sameClaim = titleHead.length() >= 2 && search(best).contains(titleHead);
                boolean unsure = bestScore - second < 2 || search(best).length() < 8
                        || "picture".equals(grade);
                if ("picture".equals(grade)) {
                    rows.add(row("replace", best, prop, unsure, "这页基本是图，改不了上面的字。要换成能改字的一页，或先不动。"));
                } else if (numberClash && sameClaim) {
                    rows.add(row("edit", best, prop, false, "这页已经在讲这件事，只缺讲稿里的数。补上数字就行。"));
                } else if (numberClash) {
                    rows.add(row("replace", best, prop, true, "页上是一堆模块名，嘴里在讲一个数。改几个字不够，要换成另一张。"));
                } else if (unsure) {
                    rows.add(row("hold", best, prop, true, "吃不准这页是不是在讲这件事，请你看一眼。"));
                } else if ("partial".equals(grade)) {
                    rows.add(row("hold", best, prop, false, "这页已经有标题和结构，先留着。字对得上就不用换。"));
                } else {
                    rows.add(row("edit", best, prop, false, "只改这页上的字，样子不变。"));
                }
            }
        }

        for (Map<String, Object> page : pages) {
            Integer n = asInt(page.get("page"));
            if (n == null || used.contains(n)) continue;
            String text = search(page);
            rows.add(row("hold", page, null, true, "暂时对不上讲稿。这份页数不动，先留着。"));
        }
        return rows;
    }

    private static Map<String, Object> row(String action, Map<String, Object> page, Map<String, Object> prop, Boolean unsure, String say) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("action", action);
        row.put("say", say);
        row.put("unsure", Boolean.TRUE.equals(unsure));
        if (page != null) {
            row.put("page", page.get("page"));
            row.put("grade", page.get("grade"));
            row.put("excerpt", page.get("excerpt"));
        }
        if (prop != null) {
            row.put("act", prop.get("act"));
            Map<String, String> on = onSlide(prop);
            String spoken = String.valueOf(prop.getOrDefault("spoken", ""));
            String title = firstNonBlank(on.get("title"), SlideClaim.title(String.valueOf(prop.getOrDefault("act", "")), spoken));
            row.put("title", title);
            row.put("spoken", spoken);
            row.put("willTitle", title);
            row.put("willNumber", on.getOrDefault("number", ""));
            row.put("willLine", firstNonBlank(on.get("line"), SlideClaim.line(spoken)));
        }
        row.put("actionLabel", actionLabel(action));
        row.put("why", say);
        row.put("aiWill", aiWill(action));
        return row;
    }

    static String actionLabel(String action) {
        return switch (action) {
            case "edit" -> "改几个字";
            case "replace" -> "换成另一页";
            case "drop" -> "拿掉这页";
            case "add" -> "补一页";
            default -> "先不动";
        };
    }

    static String aiWill(String action) {
        return switch (action) {
            case "edit" -> "按讲稿改这页上的字，这一页的样子尽量不动。";
            case "replace" -> "按讲稿做成新的一页，换掉现在这张。";
            case "drop" -> "从台上这份里拿掉，原件还在。";
            case "add" -> "按讲稿补一页进去。";
            default -> "先不改。";
        };
    }

    static int overlap(String a, String b) {
        if (a == null || b == null || a.isBlank() || b.isBlank()) return 0;
        Set<String> left = grams(a);
        Set<String> right = grams(b);
        int n = 0;
        for (String g : left) if (right.contains(g)) n++;
        return n;
    }

    private static Set<String> grams(String s) {
        String t = s.replaceAll("\\s+", "");
        Set<String> out = new HashSet<>();
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c > 127) out.add(String.valueOf(c));
            if (i + 1 < t.length()) out.add(t.substring(i, i + 2));
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, String> onSlide(Map<String, Object> prop) {
        Object raw = prop.get("onSlide");
        if (raw instanceof Map<?, ?> m) {
            Map<String, String> out = new LinkedHashMap<>();
            m.forEach((k, v) -> out.put(String.valueOf(k), v == null ? "" : String.valueOf(v)));
            return out;
        }
        return Map.of();
    }

    private static String hay(Map<String, Object> prop) {
        Map<String, String> on = onSlide(prop);
        String spoken = SlideClaim.clean(String.valueOf(prop.getOrDefault("spoken", "")));
        return String.join(" ", List.of(
                on.getOrDefault("title", ""),
                on.getOrDefault("number", ""),
                on.getOrDefault("line", ""),
                clip(spoken, 72)
        ));
    }

    private static String search(Map<String, Object> page) {
        Object s = page.get("searchText");
        if (s == null || String.valueOf(s).isBlank()) s = page.get("excerpt");
        return s == null ? "" : String.valueOf(s);
    }

    private static String firstNonBlank(String a, String b) {
        return a == null || a.isBlank() ? b : a;
    }

    private static String clip(String s, int n) {
        if (s == null) return "";
        return s.length() <= n ? s : s.substring(0, n);
    }

    private static Integer asInt(Object v) {
        if (v == null || "".equals(v)) return null;
        if (v instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(v));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
