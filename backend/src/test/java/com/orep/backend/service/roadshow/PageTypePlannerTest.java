package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PageTypePlannerTest {

    @Test
    void skipsLogisticsAndMapsProblem() {
        List<Map<String, Object>> pages = PageTypePlanner.plan(List.of(
                prop("logistics", null, "请回工位", Map.of("title", "交接")),
                prop("problem", 3, "损耗 23%", Map.of("title", "损耗发生在入库前", "number", "23%"))
        ));
        assertEquals(1, pages.size());
        assertEquals("problem", pages.get(0).get("pageType"));
        assertEquals("23%", pages.get(0).get("number"));
        assertEquals(3, pages.get(0).get("page"));
    }

    @Test
    void contrastWhenArrowInNumber() {
        List<Map<String, Object>> pages = PageTypePlanner.plan(List.of(
                prop("evidence", 10, "降到 9%", Map.of("title", "同一套秤", "number", "23% → 9%"))
        ));
        assertEquals("contrast", pages.get(0).get("pageType"));
    }

    @Test
    void hookBecomesCover() {
        List<Map<String, Object>> pages = PageTypePlanner.plan(List.of(
                prop("hook", 1, "各位评委好", Map.of("title", "智慧大棚损耗治理", "line", "田间称 · 边算 · 入账"))
        ));
        assertEquals("cover", pages.get(0).get("pageType"));
        assertEquals("智慧大棚损耗治理", pages.get(0).get("title"));
    }

    @Test
    void skipsWhenPrintPageMissing() {
        List<Map<String, Object>> pages = PageTypePlanner.plan(List.of(
                prop("problem", null, "损耗 23%", Map.of("title", "损耗发生在入库前", "number", "23%")),
                prop("close", 14, "请评委提问", Map.of("title", "问题 · 能做 · 有效"))
        ));
        assertEquals(1, pages.size());
        assertEquals("close", pages.get(0).get("pageType"));
    }

    @Test
    void mapsEachActToPageType() {
        assertEquals("architecture", PageTypePlanner.pageType("method", ""));
        assertEquals("process", PageTypePlanner.pageType("cause", ""));
        assertEquals("demo", PageTypePlanner.pageType("demo", ""));
        assertEquals("evidence", PageTypePlanner.pageType("evidence", "9%"));
        assertEquals("list", PageTypePlanner.pageType("craft", ""));
        assertEquals("list", PageTypePlanner.pageType("team", ""));
        assertEquals("close", PageTypePlanner.pageType("close", ""));
        assertEquals("contrast", PageTypePlanner.pageType("problem", "23% → 9%"));
    }

    @Test
    void compiledContrastBecomesContrastPage() {
        List<Map<String, Object>> steps = List.of(Map.of(
                "id", "s11", "role", "主讲A", "content", "损耗从 23% 降到 9%。", "focus", ""
        ));
        Map<String, Object> path = JudgePathCompiler.compile(steps, List.of(), EvidenceTokenizer.extract(steps));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> pages = PageTypePlanner.plan(
                (List<Map<String, Object>>) path.get("propositions"));
        assertEquals(1, pages.size());
        assertEquals("contrast", pages.get(0).get("pageType"));
        assertTrue(String.valueOf(pages.get(0).get("number")).contains("23%"));
        assertTrue(String.valueOf(pages.get(0).get("number")).contains("9%"));
    }

    private static Map<String, Object> prop(String act, Integer page, String spoken, Map<String, Object> onSlide) {
        java.util.Map<String, Object> p = new java.util.LinkedHashMap<>();
        p.put("act", act);
        p.put("printPage", page);
        p.put("spoken", spoken);
        p.put("onSlide", onSlide);
        return p;
    }
}
