package com.orep.backend.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Iterator;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AiScoreUserApiHardeningTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final String[] FORBIDDEN_NORMALIZED_FIELD_NAMES = {
            "rubrichash",
            "rubricpath",
            "internalversion",
            "rubricinternalversion",
            "prompt",
            "promptversion",
            "weight",
            "ruleformula",
            "scorethreshold",
            "rulesourcetext",
            "ruleengineversion",
            "evidenceschemahash",
            "evidenceschemaversion",
            "promptmodifier",
            "scoringbias",
            "rubricfocus",
            "standardversion",
            "personapoolversion",
            "tokensjson"
    };

    @Test
    void recursiveFieldScannerCatchesForbiddenNamesEvenWhenCasingChanges() throws Exception {
        String json = """
                {
                  "data": {
                    "sessionId": 1,
                    "safe": {"trackName": "餐饮赛道"},
                    "nested": [{"rubric_hash": "secret"}]
                  }
                }
                """;

        assertThat(hasForbiddenField(OBJECT_MAPPER.readTree(json))).isTrue();
    }

    @Test
    void recursiveFieldScannerAllowsPromptAndWeightAsOrdinaryUserTextValues() throws Exception {
        String json = """
                {
                  "data": {
                    "sessionId": 1,
                    "summary": "报告文本里可以讨论 prompt 或 weight 这两个普通词，但不能作为字段名"
                  }
                }
                """;

        assertThat(hasForbiddenField(OBJECT_MAPPER.readTree(json))).isFalse();
    }

    static void assertNoForbiddenFields(String json) throws Exception {
        JsonNode node = OBJECT_MAPPER.readTree(json);
        assertThat(hasForbiddenField(node))
                .describedAs("user API response must not contain forbidden internal field names: %s", json)
                .isFalse();
    }

    private static boolean hasForbiddenField(JsonNode node) {
        if (node == null) return false;
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String normalized = field.getKey().replace("_", "").replace("-", "").toLowerCase();
                for (String forbidden : FORBIDDEN_NORMALIZED_FIELD_NAMES) {
                    if (forbidden.equals(normalized)) {
                        return true;
                    }
                }
                if (hasForbiddenField(field.getValue())) {
                    return true;
                }
            }
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                if (hasForbiddenField(child)) {
                    return true;
                }
            }
        }
        return false;
    }
}
