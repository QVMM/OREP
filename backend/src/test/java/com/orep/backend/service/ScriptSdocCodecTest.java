package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ScriptSdocCodecTest {

    @Test
    void proseSdocBecomesSpokenSteps() {
        String sdoc = """
                {"type":"doc","content":[
                  {"type":"heading","content":[{"type":"text","text":"逐字稿全文"}]},
                  {"type":"paragraph","content":[{"type":"text","text":"各位评委好，我们做的是番茄精准种植。"}]},
                  {"type":"paragraph","content":[{"type":"text","text":"（翻页）三个试点大棚，从采到入库平均损耗 23%。"}]}
                ]}
                """;
        List<Map<String, Object>> steps = ScriptSdocCodec.stepsFromDocument(sdoc);
        assertFalse(steps.isEmpty());
        String blob = steps.stream().map(s -> String.valueOf(s.get("content"))).reduce("", (a, b) -> a + b);
        assertTrue(blob.contains("番茄"));
        assertTrue(blob.contains("23%"));
        assertFalse(blob.contains("分工已锁定"));
    }

    @Test
    void longTranscriptCoversLaterBeatsAndDropsHeading() {
        StringBuilder sb = new StringBuilder();
        sb.append("逐字稿全文\n");
        sb.append("项目经理： 尊敬的各位专家评委，大家好！\n");
        sb.append("项目经理： 我是本项目的项目经理兼溯源工程师。\n");
        sb.append("项目经理： 我们的项目分为六个部分。\n");
        sb.append("在介绍项目之前，从一颗番茄的产业说起。\n");
        sb.append("我们把这些烦恼带到调研中，归纳出四大痛点。\n");
        sb.append("针对这四大痛点，我们设计了番茄精准生长智控系统。\n");
        sb.append("我们系统的总体思路是识土、识图、使谱。\n");
        sb.append("请接收任务，开始传感器数据采集。\n");
        sb.append("首先是硬件连接。我们使用ESP32。\n");
        sb.append("接下来启用训练好的模型进行成熟度识别。\n");
        sb.append("系统功能展示从驾驶舱到设备控制。\n");
        sb.append("项目创新与主要成果已经沉淀。\n");
        sb.append("应用价值与未来规划沿三条线扩展。\n");
        List<Map<String, Object>> steps = ScriptSdocCodec.stepsFromPlain(sb.toString());
        assertTrue(steps.size() >= 6);
        assertTrue(steps.size() <= 45);
        String blob = steps.stream().map(s -> String.valueOf(s.get("content"))).reduce("", (a, b) -> a + " " + b);
        assertFalse(blob.startsWith("逐字稿全文"));
        assertTrue(blob.contains("四大痛点"));
        assertTrue(blob.contains("未来规划") || blob.contains("驾驶舱"));
    }

    @Test
    void pageCountUsesStructureWhenNoFlipMarks() {
        String unmarked = """
                尊敬的各位评委，大家好！我们带来番茄智控系统。
                我是本项目的项目经理兼溯源工程师。
                我们的项目分为六个部分。
                在介绍项目之前，从一颗番茄的产业说起。
                针对这四大痛点，我们做了智控系统。
                我们系统的总体思路是识土、识图、使谱。
                系统功能展示从驾驶舱到设备控制。
                项目创新与主要成果已经沉淀。
                应用价值与未来规划沿三条线扩展。
                """;
        int pages = ScriptSdocCodec.pageCountFromPlain(unmarked);
        assertTrue(pages >= 6, "unmarked pages=" + pages);
        assertTrue(ScriptSdocCodec.pageCountFromPlain("开场（翻页）问题（翻页）方案") >= 1);
        assertEquals("low", ScriptSdocCodec.pageHealth(15));
        assertEquals("ok", ScriptSdocCodec.pageHealth(38));
        assertEquals("ok", ScriptSdocCodec.pageHealth(45));
        assertEquals("high", ScriptSdocCodec.pageHealth(46));
        assertTrue(ScriptSdocCodec.pageHealthLabel(38).contains("健康"));
        assertTrue(ScriptSdocCodec.pageHealthLabel(15).contains("38–45"));
    }
}
