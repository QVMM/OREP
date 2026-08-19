package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ScriptPatchApplierTest {

    private static final String DOC = """
            [{"id":"c1","title":"开场","steps":[
              {"id":"s1","role":"主讲人A","duration":0.5,"focus":"封面（P01）","content":"各位评委好","notes":"自信","transition":"接下来看背景"},
              {"id":"s2","role":"角色B","duration":1,"focus":"架构（P09）","content":"这是架构","notes":"","transition":""}
            ]}]
            """;

    @Test
    void appliesContentAndKeepsRole() throws Exception {
        Map<String, Object> patch = new java.util.LinkedHashMap<>();
        patch.put("stepId", "s1");
        patch.put("field", "content");
        patch.put("before", "各位评委好");
        patch.put("after", "各位评委老师好，我们汇报智慧农业项目");
        patch.put("reason", "开场缺少项目名");
        String out = ScriptPatchApplier.apply(DOC, List.of(patch));
        assertTrue(out.contains("我们汇报智慧农业项目"));
        assertTrue(out.contains("\"role\":\"主讲人A\""));
        assertTrue(out.contains("\"role\":\"角色B\""));
        assertEquals("主讲人A", ScriptPatchApplier.stepRole(out, "s1"));
    }

    @Test
    void rejectsRoleField() {
        Map<String, Object> patch = new java.util.LinkedHashMap<>();
        patch.put("stepId", "s1");
        patch.put("field", "role");
        patch.put("before", "主讲人A");
        patch.put("after", "角色B");
        patch.put("reason", "换人");
        assertThrows(IllegalArgumentException.class, () -> ScriptPatchApplier.apply(DOC, List.of(patch)));
    }

    @Test
    void rejectsStaleBefore() {
        Map<String, Object> patch = new java.util.LinkedHashMap<>();
        patch.put("stepId", "s1");
        patch.put("field", "content");
        patch.put("before", "过期原文");
        patch.put("after", "新稿");
        patch.put("reason", "润色");
        assertThrows(IllegalStateException.class, () -> ScriptPatchApplier.apply(DOC, List.of(patch)));
    }
}
