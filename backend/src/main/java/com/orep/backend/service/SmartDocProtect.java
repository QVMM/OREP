package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 智能文档内容保护区：按角色剥离正文，学生保存时把教师段合并回去。
 */
public final class SmartDocProtect {

    public static final String TYPE = "protectedRegion";
    public static final String PLACEHOLDER = "此段仅教师可见";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private SmartDocProtect() {
    }

    public static boolean canAccess(String role, String minRole) {
        return rank(role) >= rank(blankToTeacher(minRole));
    }

    public static boolean canEditProtected(String role) {
        return canAccess(role, "TEACHER");
    }

    public static String redact(String json, String role) {
        JsonNode root = read(json);
        if (root == null) return json;
        redactNode(root, role);
        return write(root);
    }

    public static String mergeSealed(String storedJson, String incomingJson, String role) {
        if (canEditProtected(role)) return incomingJson;
        JsonNode stored = read(storedJson);
        JsonNode incoming = read(incomingJson);
        if (incoming == null) return storedJson;
        Map<String, ObjectNode> kept = new LinkedHashMap<>();
        collect(stored, kept);
        mergeNode(incoming, kept);
        appendMissing(incoming, kept);
        return write(incoming);
    }

    static int rank(String role) {
        return switch (normalize(role)) {
            case "ADMIN" -> 50;
            case "SCHOOL_ADMIN" -> 40;
            case "TEACHER" -> 30;
            case "EXPERT" -> 20;
            case "REVIEWER" -> 10;
            default -> 0;
        };
    }

    private static void redactNode(JsonNode node, String role) {
        if (node == null || !node.isObject()) {
            if (node != null && node.isArray()) {
                for (JsonNode child : node) redactNode(child, role);
            }
            return;
        }
        ObjectNode obj = (ObjectNode) node;
        if (TYPE.equals(text(obj, "type")) && !canAccess(role, attr(obj, "minRole"))) {
            ObjectNode attrs = attrsOf(obj);
            attrs.put("sealed", true);
            obj.set("attrs", attrs);
            obj.set("content", placeholderContent());
            return;
        }
        JsonNode content = obj.get("content");
        if (content != null && content.isArray()) {
            for (JsonNode child : content) redactNode(child, role);
        }
    }

    private static void collect(JsonNode node, Map<String, ObjectNode> out) {
        if (node == null) return;
        if (node.isArray()) {
            for (JsonNode child : node) collect(child, out);
            return;
        }
        if (!node.isObject()) return;
        ObjectNode obj = (ObjectNode) node;
        if (TYPE.equals(text(obj, "type"))) {
            String id = attr(obj, "id");
            if (id != null && !id.isBlank()) {
                out.put(id, obj.deepCopy());
            }
        }
        JsonNode content = obj.get("content");
        if (content != null && content.isArray()) {
            for (JsonNode child : content) collect(child, out);
        }
    }

    private static void mergeNode(JsonNode node, Map<String, ObjectNode> kept) {
        if (node == null || !node.isObject()) {
            if (node != null && node.isArray()) {
                ArrayNode arr = (ArrayNode) node;
                for (int i = 0; i < arr.size(); i++) {
                    JsonNode child = arr.get(i);
                    if (child != null && child.isObject() && TYPE.equals(text((ObjectNode) child, "type"))) {
                        ObjectNode region = (ObjectNode) child;
                        String id = attr(region, "id");
                        ObjectNode stored = id == null ? null : kept.remove(id);
                        if (stored != null) {
                            arr.set(i, stored);
                        } else {
                            arr.remove(i);
                            i--;
                        }
                    } else {
                        mergeNode(child, kept);
                    }
                }
            }
            return;
        }
        JsonNode content = node.get("content");
        if (content != null) mergeNode(content, kept);
    }

    private static void appendMissing(JsonNode incoming, Map<String, ObjectNode> leftover) {
        if (leftover.isEmpty() || incoming == null || !incoming.isObject()) return;
        ObjectNode doc = (ObjectNode) incoming;
        ArrayNode content = doc.has("content") && doc.get("content").isArray()
                ? (ArrayNode) doc.get("content")
                : doc.putArray("content");
        for (ObjectNode region : leftover.values()) {
            content.add(region);
        }
    }

    private static ArrayNode placeholderContent() {
        ObjectNode text = MAPPER.createObjectNode();
        text.put("type", "text");
        text.put("text", PLACEHOLDER);
        ObjectNode paragraph = MAPPER.createObjectNode();
        paragraph.put("type", "paragraph");
        paragraph.set("content", MAPPER.createArrayNode().add(text));
        return MAPPER.createArrayNode().add(paragraph);
    }

    private static ObjectNode attrsOf(ObjectNode obj) {
        JsonNode attrs = obj.get("attrs");
        if (attrs instanceof ObjectNode o) return o;
        return MAPPER.createObjectNode();
    }

    private static String attr(ObjectNode obj, String key) {
        JsonNode attrs = obj.get("attrs");
        if (attrs == null || !attrs.has(key) || attrs.get(key).isNull()) return null;
        return attrs.get(key).asText();
    }

    private static Boolean attrBool(ObjectNode obj, String key) {
        JsonNode attrs = obj.get("attrs");
        if (attrs == null || !attrs.has(key) || attrs.get(key).isNull()) return null;
        return attrs.get(key).asBoolean();
    }

    private static String text(ObjectNode obj, String key) {
        JsonNode n = obj.get(key);
        return n == null || n.isNull() ? null : n.asText();
    }

    private static JsonNode read(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return MAPPER.readTree(json);
        } catch (Exception e) {
            return null;
        }
    }

    private static String write(JsonNode node) {
        try {
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            return String.valueOf(node);
        }
    }

    private static String blankToTeacher(String minRole) {
        String n = normalize(minRole);
        return n.isEmpty() ? "TEACHER" : n;
    }

    private static String normalize(String role) {
        return role == null ? "" : role.trim().toUpperCase();
    }
}
