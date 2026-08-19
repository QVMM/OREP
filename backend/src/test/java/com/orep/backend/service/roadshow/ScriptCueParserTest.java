package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ScriptCueParserTest {

    private static final String TOMATO = """
            项目经理： 尊敬的各位专家评委，大家好！
            全体成员： 大家好！
            项目经理： 首先，我们团队先向各位评委老师介绍一下岗位分工。（翻页）
            项目经理： 我是本项目的项目经理兼溯源工程师。
            【动作】PPT 同步展示团队分工表：四角色 × 职责。
            项目经理： 请团队成员回到工位开始准备工作。（翻页）
            项目经理： 番茄是全球消费量最大的蔬菜之一。河南省十五五规划。项目的起点在我家的菜园。我校工程中心。（翻页）
            嵌入式工程师： 下面展示核心代码。
            【运行ESP32程序，展示串口输出】
            嵌入式工程师： 我拔掉了土壤传感器的通信线。当前共检测到番茄【现场结果】颗。（翻页）
            AI视觉工程师： 在开始训练前，我先说明模型选型的依据。（PPT展示对比表）
            """;

    @Test
    void capturesFlipsAndPptShowAndLive() {
        List<Map<String, Object>> spans = ScriptCueParser.parse(TOMATO);
        assertTrue(spans.size() >= 4);
        assertTrue(spans.stream().anyMatch(s -> "ppt_show".equals(s.get("cueType"))
                && String.valueOf(s.get("cueRaw")).contains("分工表")));
        assertTrue(spans.stream().anyMatch(s -> "live".equals(s.get("cueType"))));
        long flips = spans.stream().filter(s -> "flip".equals(s.get("cueType"))).count();
        assertTrue(flips >= 3);
    }

    @Test
    void marksFatIndustrySpan() {
        List<Map<String, Object>> spans = ScriptCueParser.parse(TOMATO);
        assertTrue(spans.stream().anyMatch(s -> Boolean.TRUE.equals(s.get("fat"))
                && String.valueOf(s.get("text")).contains("菜园")));
    }

    @Test
    void liveSpanGetsNoPage() {
        List<Map<String, Object>> spans = ScriptCueParser.parse(TOMATO);
        assertTrue(spans.stream().anyMatch(s -> "live".equals(s.get("cueType")) && Boolean.TRUE.equals(s.get("hold"))));
        assertTrue(spans.stream().anyMatch(s ->
                String.valueOf(s.get("text")).contains("拔掉") || String.valueOf(s.get("text")).contains("现场结果")));
    }
}
