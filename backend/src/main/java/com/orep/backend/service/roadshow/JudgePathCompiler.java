package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class JudgePathCompiler {

    private JudgePathCompiler() {
    }

    public static Map<String, Object> compile(
            List<Map<String, Object>> steps,
            List<Map<String, Object>> scoreItems,
            List<Map<String, Object>> tokens
    ) {
        List<Map<String, Object>> safeSteps = steps == null ? List.of() : steps;
        List<Map<String, Object>> items = scoreItems == null ? List.of() : scoreItems;
        List<Map<String, Object>> toks = tokens == null ? List.of() : tokens;

        List<Map<String, Object>> holes = new ArrayList<>();
        List<Map<String, Object>> props = new ArrayList<>();

        for (Map<String, Object> item : items) {
            String dim = String.valueOf(item.getOrDefault("dimension", ""));
            if (dim.contains("经济")) {
                holes.add(hole(item, List.of("万", "节约", "回本", "万元")));
            }
        }

        int page = 1;
        for (Map<String, Object> step : safeSteps) {
            String content = String.valueOf(step.getOrDefault("content", ""));
            String focus = String.valueOf(step.getOrDefault("focus", ""));
            String act = StepActClassifier.classify(content, focus);
            Map<String, Object> p = new LinkedHashMap<>();
            p.put("id", "p_" + step.get("id"));
            p.put("act", act);
            p.put("stepId", step.get("id"));
            p.put("role", step.get("role"));
            p.put("spoken", content);
            if ("logistics".equals(act) || ("demo".equals(act) && content.contains("拔掉")) || isCodeNoise(content)) {
                p.put("printPage", null);
                p.put("status", "spoken_only");
            } else {
                p.put("printPage", page++);
                p.put("status", "bound");
            }
            String contrast = firstContrast(toks, String.valueOf(step.get("id")));
            String slideNum = firstSurface(toks, String.valueOf(step.get("id")));
            Map<String, Object> onSlide = new LinkedHashMap<>();
            onSlide.put("title", SlideClaim.title(act, content));
            onSlide.put("line", SlideClaim.line(content));
            if (contrast != null) onSlide.put("number", contrast);
            else if (slideNum != null) onSlide.put("number", slideNum);
            p.put("onSlide", onSlide);
            if ("problem".equals(act)) {
                items.stream().filter(it -> String.valueOf(it.getOrDefault("dimension", "")).contains("实用"))
                        .findFirst()
                        .ifPresent(it -> p.put("scoreItemId", it.get("id")));
            }
            props.add(p);
        }

        if (props.isEmpty() && !safeSteps.isEmpty()) {
            Map<String, Object> p = new LinkedHashMap<>();
            p.put("id", "p_hook");
            p.put("act", "hook");
            p.put("printPage", 1);
            p.put("onSlide", Map.of("title", "开场"));
            props.add(p);
        }

        Map<String, Object> path = new LinkedHashMap<>();
        path.put("propositions", props);
        path.put("holes", holes);
        path.put("tokens", toks);
        path.put("coverage", items.isEmpty() ? "unpinned" : "pinned");
        return path;
    }

    private static Map<String, Object> hole(Map<String, Object> item, List<String> forbid) {
        Map<String, Object> h = new LinkedHashMap<>();
        h.put("id", "h_" + item.get("id"));
        h.put("scoreItemId", item.get("id"));
        h.put("scoreDimension", item.get("dimension"));
        h.put("why", item.get("reason"));
        h.put("forbiddenOnSlide", forbid);
        h.put("acked", false);
        return h;
    }

    private static boolean isCodeNoise(String content) {
        if (content == null) return false;
        return content.contains("raw_data") || content.contains("await asyncio")
                || content.contains("ustruct") || content.contains("async def")
                || content.startsWith("if ") || content.startsWith("temp =")
                || content.startsWith("return ") || content.contains("# 空气传感器");
    }

    private static String firstContrast(List<Map<String, Object>> toks, String stepId) {
        return toks.stream()
                .filter(t -> stepId.equals(String.valueOf(t.get("stepId"))) && "contrast".equals(t.get("kind")))
                .map(t -> String.valueOf(t.get("surface")))
                .findFirst()
                .orElse(null);
    }

    private static String firstSurface(List<Map<String, Object>> toks, String stepId) {
        return toks.stream()
                .filter(t -> stepId.equals(String.valueOf(t.get("stepId"))) && "metric".equals(t.get("kind")))
                .map(t -> String.valueOf(t.get("surface")))
                .findFirst()
                .orElse(null);
    }

}
