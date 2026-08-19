package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 讲稿步骤补丁：只改 content / notes / transition，锁死角色与结构。
 */
public final class ScriptPatchApplier {

    public static final Set<String> ALLOWED_FIELDS = Set.of("content", "notes", "transition");
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private ScriptPatchApplier() {
    }

    public static String apply(String contentJson, List<Map<String, Object>> patches) {
        if (contentJson == null || contentJson.isBlank()) {
            throw new IllegalArgumentException("讲稿内容为空");
        }
        if (patches == null || patches.isEmpty()) {
            throw new IllegalArgumentException("没有可应用的修改");
        }
        try {
            JsonNode root = MAPPER.readTree(contentJson);
            if (!root.isArray()) throw new IllegalArgumentException("讲稿格式无效");
            for (Map<String, Object> patch : patches) {
                applyOne((ArrayNode) root, patch);
            }
            return MAPPER.writeValueAsString(root);
        } catch (IllegalArgumentException | IllegalStateException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalArgumentException("讲稿补丁失败: " + e.getMessage());
        }
    }

    public static String stepRole(String contentJson, String stepId) {
        try {
            JsonNode root = MAPPER.readTree(contentJson);
            ObjectNode step = findStep((ArrayNode) root, stepId);
            return step != null && step.has("role") ? step.get("role").asText("") : "";
        } catch (Exception e) {
            return "";
        }
    }

    private static void applyOne(ArrayNode chapters, Map<String, Object> patch) {
        if (patch == null) throw new IllegalArgumentException("补丁无效");
        String stepId = str(patch.get("stepId"));
        String field = str(patch.get("field"));
        String before = patch.get("before") == null ? "" : String.valueOf(patch.get("before"));
        String after = patch.get("after") == null ? "" : String.valueOf(patch.get("after"));
        if (stepId.isBlank()) throw new IllegalArgumentException("缺少 stepId");
        if (!ALLOWED_FIELDS.contains(field)) {
            throw new IllegalArgumentException("不允许修改字段: " + field);
        }
        ObjectNode step = findStep(chapters, stepId);
        if (step == null) throw new IllegalArgumentException("找不到步骤 " + stepId);
        String current = step.has(field) && !step.get(field).isNull() ? step.get(field).asText("") : "";
        if (!current.equals(before)) {
            throw new IllegalStateException("原文已变化，请刷新后再确认");
        }
        step.put(field, after);
    }

    private static ObjectNode findStep(ArrayNode chapters, String stepId) {
        for (JsonNode chapter : chapters) {
            JsonNode steps = chapter.get("steps");
            if (steps == null || !steps.isArray()) continue;
            for (JsonNode step : steps) {
                if (step.isObject() && stepId.equals(text(step, "id"))) {
                    return (ObjectNode) step;
                }
            }
        }
        return null;
    }

    private static String text(JsonNode node, String key) {
        return node.has(key) && !node.get(key).isNull() ? node.get(key).asText("") : "";
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v).trim();
    }
}
