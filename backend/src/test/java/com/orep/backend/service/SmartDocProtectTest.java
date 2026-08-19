package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SmartDocProtectTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final String DOC = """
            {"type":"doc","content":[
              {"type":"paragraph","content":[{"type":"text","text":"公开"}]},
              {"type":"protectedRegion","attrs":{"id":"p1","minRole":"TEACHER","label":"仅教师可见","sealed":false},
               "content":[{"type":"paragraph","content":[{"type":"text","text":"答案"}]}]}
            ]}
            """;

    @Test
    void teacherCanSeeProtectedRegion() {
        assertTrue(SmartDocProtect.canEditProtected("TEACHER"));
        assertTrue(SmartDocProtect.canEditProtected("ADMIN"));
        assertFalse(SmartDocProtect.canEditProtected("STUDENT"));
        assertFalse(SmartDocProtect.canAccess("STUDENT", "TEACHER"));
    }

    @Test
    void redactHidesTeacherOnlyBodyFromStudents() throws Exception {
        String redacted = SmartDocProtect.redact(DOC, "STUDENT");
        JsonNode root = MAPPER.readTree(redacted);
        JsonNode region = root.get("content").get(1);
        assertEquals("protectedRegion", region.get("type").asText());
        assertTrue(region.get("attrs").get("sealed").asBoolean());
        assertEquals(SmartDocProtect.PLACEHOLDER, region.get("content").get(0).get("content").get(0).get("text").asText());
        assertFalse(redacted.contains("答案"));
        assertTrue(SmartDocProtect.redact(DOC, "TEACHER").contains("答案"));
    }

    @Test
    void studentSaveCannotOverwriteOrDeleteProtectedRegion() throws Exception {
        String incoming = """
                {"type":"doc","content":[
                  {"type":"paragraph","content":[{"type":"text","text":"学生改过"}]},
                  {"type":"protectedRegion","attrs":{"id":"p1","minRole":"TEACHER","sealed":true},
                   "content":[{"type":"paragraph","content":[{"type":"text","text":"此段仅教师可见"}]}]}
                ]}
                """;
        String merged = SmartDocProtect.mergeSealed(DOC, incoming, "STUDENT");
        assertTrue(merged.contains("学生改过"));
        assertTrue(merged.contains("答案"));
        assertFalse(MAPPER.readTree(merged).toString().contains("\"sealed\":true"));
    }

    @Test
    void studentDeletingProtectedRegionPutsItBack() {
        String incoming = """
                {"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"只剩公开"}]}]}
                """;
        String merged = SmartDocProtect.mergeSealed(DOC, incoming, "STUDENT");
        assertTrue(merged.contains("答案"));
        assertTrue(merged.contains("只剩公开"));
    }
}
