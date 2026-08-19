package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegacyAlignerTest {

    @Test
    void moduleWallCannotHoldNumber() {
        List<Map<String, Object>> rows = LegacyAligner.align(
                List.of(prop("problem", 3, "损耗发生在入库前", "23%", "三个试点大棚量过损耗 23%")),
                List.of(page(6, "partial", "系统主要模块 损耗治理 物联网 视觉 RAG 区块链 驾驶舱"))
        );
        assertEquals("replace", rows.get(0).get("action"));
        assertEquals(6, rows.get(0).get("page"));
        assertTrue(String.valueOf(rows.get(0).get("say")).contains("换成"));
    }

    @Test
    void leftoverPagesStayPut() {
        List<Map<String, Object>> rows = LegacyAligner.align(
                List.of(prop("hook", 1, "慧眼识株", "", "各位评委好")),
                List.of(
                        page(1, "partial", "慧眼识株 智培鲜果 番茄种植"),
                        page(18, "editable", "展望未来 谢谢观看")
                )
        );
        assertTrue(rows.stream().anyMatch(r -> "hold".equals(r.get("action")) && Integer.valueOf(18).equals(r.get("page"))));
        assertTrue(rows.stream().noneMatch(r -> "drop".equals(r.get("action"))));
    }

    @Test
    void matchingClaimOnlyAddsNumber() {
        List<Map<String, Object>> rows = LegacyAligner.align(
                List.of(prop("method", 8, "识土、识图、使谱", "96%", "识土、识图、使谱，精度稳定在 96%")),
                List.of(page(12, "partial", "用“识土、识图、使谱”建立精准管控闭环 感知、分析、决策一体化"))
        );
        assertEquals("edit", rows.get(0).get("action"));
        assertEquals(12, rows.get(0).get("page"));
    }

    @Test
    void twoBeatsDoNotShareOnePage() {
        List<Map<String, Object>> rows = LegacyAligner.align(
                List.of(
                        prop("team", 1, "岗位分工", "", "我是本项目的项目经理兼溯源工程师"),
                        prop("method", 2, "这场分六个部分", "", "我们的项目分为六个部分，分别是项目介绍")
                ),
                List.of(
                        page(2, "partial", "团队角色与岗位分工 TEAM COLLABORATION 项目经理"),
                        page(3, "partial", "目录 项目介绍 总体思路 六个部分")
                )
        );
        List<Object> used = rows.stream().filter(r -> r.get("page") != null).map(r -> r.get("page")).toList();
        assertEquals(2, used.size());
        assertEquals(2, used.stream().distinct().count());
    }

    @Test
    void spokenOnlyGetsNoPage() {
        List<Map<String, Object>> rows = LegacyAligner.align(
                List.of(prop("logistics", null, "交给下一位", "", "接下来交给下一位，请回工位。")),
                List.of(page(2, "editable", "团队分工"))
        );
        assertTrue(rows.stream().noneMatch(r -> "logistics".equals(r.get("act")) && r.get("page") != null && !"hold".equals(r.get("action"))));
    }

    private static Map<String, Object> prop(String act, Integer page, String title, String number, String spoken) {
        return Map.of(
                "act", act,
                "printPage", page == null ? "" : page,
                "spoken", spoken,
                "onSlide", number.isBlank() ? Map.of("title", title) : Map.of("title", title, "number", number)
        );
    }

    private static Map<String, Object> page(int n, String grade, String excerpt) {
        return Map.of("page", n, "grade", grade, "label", grade, "excerpt", excerpt, "searchText", excerpt);
    }
}
