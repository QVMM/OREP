package com.orep.backend.service.roadshow;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class JudgePathGates {

    private static final Pattern NUM = Pattern.compile("\\d+(?:\\.\\d+)?%?|\\d+万|\\d+元");

    private JudgePathGates() {
    }

    public static boolean speakRatioOk(String spoken, String onSlide) {
        int a = hanLen(onSlide);
        int b = Math.max(1, hanLen(spoken));
        return (a * 1.0 / b) < 0.35;
    }

    public static boolean slideAllowed(Map<String, Object> path, Map<String, Object> onSlide) {
        if (path == null || onSlide == null) return false;
        String blob = String.valueOf(onSlide.values());
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> holes = (List<Map<String, Object>>) path.get("holes");
        if (holes != null) {
            for (Map<String, Object> h : holes) {
                Object raw = h.get("forbiddenOnSlide");
                if (raw instanceof Collection<?> c) {
                    for (Object w : c) {
                        if (blob.contains(String.valueOf(w))) return false;
                    }
                } else if (raw != null && blob.contains(String.valueOf(raw))) {
                    return false;
                }
            }
        }
        Matcher m = NUM.matcher(blob);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> tokens = (List<Map<String, Object>>) path.get("tokens");
        while (m.find()) {
            String n = m.group();
            boolean ok = tokens != null && tokens.stream().anyMatch(t -> String.valueOf(t.get("surface")).contains(n));
            if (!ok && (n.contains("万") || n.contains("元"))) return false;
        }
        return true;
    }

    @SuppressWarnings("unchecked")
    public static boolean problemPayoffOk(Map<String, Object> path) {
        List<Map<String, Object>> tokens = (List<Map<String, Object>>) path.get("tokens");
        List<Map<String, Object>> props = (List<Map<String, Object>>) path.get("propositions");
        if (props == null) return true;
        boolean hasProblemMetric = props.stream().anyMatch(p -> "problem".equals(p.get("act"))
                && String.valueOf(p.get("onSlide")).contains("%"));
        if (!hasProblemMetric) return true;
        return tokens != null && tokens.stream().anyMatch(t -> "contrast".equals(t.get("kind")));
    }

    @SuppressWarnings("unchecked")
    public static boolean canPrint(Map<String, Object> path) {
        if (path == null) return false;
        List<Map<String, Object>> holes = (List<Map<String, Object>>) path.get("holes");
        if (holes != null && !holes.isEmpty()) {
            boolean allAcked = holes.stream().allMatch(h -> Boolean.TRUE.equals(h.get("acked")));
            if (!allAcked) return false;
        }
        return problemPayoffOk(path);
    }

    static int hanLen(String s) {
        if (s == null) return 0;
        return s.replaceAll("\\s+", "").length();
    }
}
