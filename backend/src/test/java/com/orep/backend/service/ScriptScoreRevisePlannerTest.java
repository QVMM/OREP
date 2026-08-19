package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ScriptScoreRevisePlannerTest {

    private static final String DOC = """
            [{"id":"c1","title":"开场","steps":[
              {"id":"s1","role":"主讲人A","focus":"封面（P01）","content":"各位评委好，今天汇报智慧农业项目"},
              {"id":"s2","role":"项目经理","focus":"分工（P03）","content":"我们的协作机制如下：由我制定任务计划"}
            ]}]
            """;

    @Test
    void mapsNamedItemsAndLeavesUnmapped() {
        List<Map<String, Object>> items = ScriptScoreRevisePlanner.normalizeItems(List.of(
                Map.of("id", "sp-1", "title", "协作机制太书面", "reason", "任务计划写成制度说明"),
                Map.of("id", "sp-2", "title", "数据证据不足", "reason", "没有仓库提交记录")
        ), "45");
        List<Map<String, Object>> steps = ScriptScoreRevisePlanner.flattenSteps(DOC);
        List<Map<String, Object>> plan = ScriptScoreRevisePlanner.plan(items, steps);
        assertEquals(2, plan.size());
        assertEquals("sp-1", plan.get(0).get("id"));
        assertTrue(Boolean.TRUE.equals(plan.get(0).get("mapped")));
        assertEquals("s2", plan.get(0).get("stepId"));
        assertEquals("项目经理", plan.get(0).get("role"));
        assertFalse(Boolean.TRUE.equals(plan.get(1).get("mapped")));
        assertEquals("sp-2", plan.get(1).get("id"));
    }

    @Test
    void doesNotInventExtraDeductions() {
        List<Map<String, Object>> items = ScriptScoreRevisePlanner.normalizeItems(
                List.of(Map.of("title", "开场补项目名")), "9");
        List<Map<String, Object>> plan = ScriptScoreRevisePlanner.plan(items, ScriptScoreRevisePlanner.flattenSteps(DOC));
        assertEquals(1, plan.size());
        assertEquals("score-9-1", plan.get(0).get("id"));
    }

    @Test
    void emptyScoreStaysEmpty() {
        assertTrue(ScriptScoreRevisePlanner.plan(List.of(), ScriptScoreRevisePlanner.flattenSteps(DOC)).isEmpty());
    }
}
