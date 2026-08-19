package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JudgePathCompilerTest {

    @Test
    void problemPropositionFromLossAndUsefulnessGap() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s4", "主讲A", "三个试点大棚，从采到入库平均损耗 23%。")),
                List.of(item("score-1", "应用价值/实用性", "问题不具体，看不出是不是真量过")),
                EvidenceTokenizer.extract(List.of(step("s4", "主讲A", "三个试点大棚，从采到入库平均损耗 23%。")))
        );
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> props = (List<Map<String, Object>>) path.get("propositions");
        assertTrue(props.stream().anyMatch(p -> "problem".equals(p.get("act"))
                && String.valueOf(p.get("onSlide")).contains("23%")));
    }

    @Test
    void moneyGapBecomesHole() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s1", "主讲A", "我们做的是智慧大棚损耗治理。")),
                List.of(item("score-7", "应用价值/经济性", "没有成本账")),
                List.of()
        );
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> holes = (List<Map<String, Object>>) path.get("holes");
        assertFalse(holes.isEmpty());
        assertTrue(String.valueOf(holes.get(0).get("forbiddenOnSlide")).contains("万"));
    }

    @Test
    void inventedMoneyFailsGate() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s1", "主讲A", "我们做智慧大棚。")),
                List.of(item("score-7", "应用价值/经济性", "没有成本账")),
                List.of()
        );
        assertFalse(JudgePathGates.canPrint(path));
        assertFalse(JudgePathGates.slideAllowed(path, Map.of("title", "节约 12 万")));
    }

    @Test
    void logisticsHasNoPrintPage() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s2", "主讲B", "接下来交给下一位，请回工位。")),
                List.of(),
                List.of()
        );
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> props = (List<Map<String, Object>>) path.get("propositions");
        assertTrue(props.stream().noneMatch(p -> p.get("printPage") != null
                && "logistics".equals(p.get("act"))));
    }

    @Test
    void missingPayoffFailsProblemPrint() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s4", "主讲A", "损耗 23%，发生在入库前。")),
                List.of(),
                EvidenceTokenizer.extract(List.of(step("s4", "主讲A", "损耗 23%，发生在入库前。")))
        );
        assertFalse(JudgePathGates.problemPayoffOk(path));
    }

    @Test
    void speakRatioMustStayUnder35() {
        assertFalse(JudgePathGates.speakRatioOk("评委老师我们量过损耗。", "损耗发生在入库前23%三个试点采摘到入库平均损耗很高"));
        assertTrue(JudgePathGates.speakRatioOk("评委老师，我们在三个试点大棚量过，从采到入库平均损耗 23%，钱主要耗在这一段。", "损耗发生在入库前23%"));
    }

    @Test
    void ackedHolesAllowPrintWhenPayoffOk() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s11", "主讲A", "损耗从 23% 降到 9%。")),
                List.of(item("score-7", "应用价值/经济性", "没有成本账")),
                EvidenceTokenizer.extract(List.of(step("s11", "主讲A", "损耗从 23% 降到 9%。")))
        );
        assertFalse(JudgePathGates.canPrint(path));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> holes = (List<Map<String, Object>>) path.get("holes");
        holes.get(0).put("acked", true);
        assertTrue(JudgePathGates.canPrint(path));
    }

    @Test
    void slideTitleIsNotSpokenPrefix() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s2", "主讲人", "项目经理： 我是本项目的项目经理兼溯源工程师，主要负责团队任务安排。")),
                List.of(),
                List.of()
        );
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> props = (List<Map<String, Object>>) path.get("propositions");
        String title = String.valueOf(((Map<?, ?>) props.get(0).get("onSlide")).get("title"));
        assertEquals("岗位分工", title);
    }

    @Test
    void codeSnippetDoesNotInventPercent() {
        List<Map<String, Object>> toks = EvidenceTokenizer.extract(List.of(
                step("s12", "嵌入式", "下面展示核心代码。 python复制async def sensor_data_send 5095.2%")
        ));
        assertTrue(toks.stream().noneMatch(t -> String.valueOf(t.get("surface")).contains("5095")));
    }

    @Test
    void noScoreIsUnpinned() {
        Map<String, Object> path = JudgePathCompiler.compile(
                List.of(step("s1", "主讲A", "各位评委好，我们汇报智慧农业。")),
                List.of(),
                List.of()
        );
        assertEquals("unpinned", path.get("coverage"));
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> props = (List<Map<String, Object>>) path.get("propositions");
        assertFalse(props.isEmpty());
    }

    private static Map<String, Object> step(String id, String role, String content) {
        return Map.of("id", id, "role", role, "content", content, "focus", "");
    }

    private static Map<String, Object> item(String id, String dimension, String reason) {
        return Map.of("id", id, "title", reason, "reason", reason, "dimension", dimension);
    }
}
