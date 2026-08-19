package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.AiJudgePersona;
import com.orep.backend.mapper.AiJudgePersonaMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AiJudgePersonaService {
    private final AiJudgePersonaMapper personaMapper;
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiJudgePersonaService(AiJudgePersonaMapper personaMapper, JdbcTemplate jdbc) {
        this.personaMapper = personaMapper;
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void ensureSchemaAndDefaults() {
        if (jdbc == null) return;
        ensureSchema();
        seedMissingDefaults();
    }

    public List<Map<String, Object>> listPersonaPayloads() {
        return listAdminPersonaPayloads();
    }

    public List<Map<String, Object>> listUserPersonaPayloads() {
        return listAllPersonas().stream()
                .filter(item -> item.getEnabled() == null || item.getEnabled())
                .map(this::toUserPayload)
                .toList();
    }

    public List<Map<String, Object>> listAdminPersonaPayloads() {
        return listAllPersonas().stream().map(this::toPayload).toList();
    }

    public List<Map<String, Object>> defaultPersonaPayloads() {
        try (InputStream in = new ClassPathResource("ai_judge_personas_seed.json").getInputStream()) {
            return objectMapper.readValue(in, new TypeReference<>() {});
        } catch (Exception e) {
            throw new IllegalStateException("默认AI评委画像读取失败", e);
        }
    }

    public AiJudgePersona updatePersona(String code, Map<String, Object> patch) {
        String normalizedCode = normalizeCode(code);
        AiJudgePersona persona = personaMapper.selectOne(
                new LambdaQueryWrapper<AiJudgePersona>().eq(AiJudgePersona::getCode, normalizedCode)
        );
        if (persona == null) {
            throw new IllegalArgumentException("评委画像不存在: " + normalizedCode);
        }

        applyPatch(persona, patch == null ? Map.of() : patch);
        persona.setCode(normalizedCode);
        persona.setUpdatedAt(LocalDateTime.now());
        personaMapper.updateById(persona);
        return persona;
    }

    public List<Map<String, Object>> resetDefaults() {
        for (Map<String, Object> payload : defaultPersonaPayloads()) {
            upsertDefault(payload, true);
        }
        return listPersonaPayloads();
    }

    public Map<String, Object> toPayload(AiJudgePersona persona) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", persona.getId());
        payload.put("code", persona.getCode());
        payload.put("name", persona.getName());
        payload.put("short_label", persona.getShortLabel());
        payload.put("focus_dimensions", readJson(persona.getFocusDimensionsJson(), List.class, List.of()));
        payload.put("prompt_modifier", persona.getPromptModifier());
        payload.put("description", persona.getDescription());
        payload.put("enabled", persona.getEnabled() == null || persona.getEnabled());
        payload.put("judge_profile", readJson(persona.getJudgeProfileJson(), Map.class, Map.of()));
        payload.put("rubric_focus", readJson(persona.getRubricFocusJson(), Map.class, Map.of()));
        payload.put("scoring_bias", readJson(persona.getScoringBiasJson(), Map.class, Map.of()));
        return payload;
    }

    public Map<String, Object> toUserPayload(AiJudgePersona persona) {
        Map<String, Object> profile = readJson(persona.getJudgeProfileJson(), Map.class, Map.of());
        Map<String, Object> personaView = new LinkedHashMap<>();
        personaView.put("core_traits", sanitizeUserValue(profile.getOrDefault("core_traits", List.of())));
        personaView.put("scoring_style", sanitizeUserValue(profile.getOrDefault("scoring_style", "")));
        personaView.put("evidence_preference", sanitizeUserValue(profile.getOrDefault("evidence_preference", "")));
        personaView.put("top_concerns", sanitizeUserValue(profile.getOrDefault("top_concerns", profile.getOrDefault("sensitive_risks", List.of()))));
        personaView.put("feedback_style", sanitizeUserValue(profile.getOrDefault("feedback_style", "")));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", persona.getId());
        payload.put("code", sanitizeUserValue(persona.getCode()));
        payload.put("name", sanitizeUserValue(persona.getName()));
        payload.put("short_label", sanitizeUserValue(persona.getShortLabel()));
        payload.put("focus_dimensions", sanitizeUserValue(readJson(persona.getFocusDimensionsJson(), List.class, List.of())));
        payload.put("description", sanitizeUserValue(persona.getDescription()));
        payload.put("enabled", persona.getEnabled() == null || persona.getEnabled());
        payload.put("persona_view", personaView);
        return payload;
    }

    private void ensureSchema() {
        try (InputStream in = new ClassPathResource("sql/create_ai_jury_tables.sql").getInputStream()) {
            String sql = new String(in.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                String trimmed = statement.trim();
                if (!trimmed.isBlank()) jdbc.execute(trimmed);
            }
        } catch (Exception e) {
            throw new IllegalStateException("AI评审团表初始化失败", e);
        }
        ensureJurySchemaCompatibility();
    }

    void ensureJurySchemaCompatibility() {
        addColumnIfMissing("ai_jury_session", "scoring_session_id",
                "ALTER TABLE ai_jury_session ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID'");
        addColumnIfMissing("ai_judge_report", "scoring_session_id",
                "ALTER TABLE ai_judge_report ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID'");
        addColumnIfMissing("ai_jury_aggregate", "scoring_session_id",
                "ALTER TABLE ai_jury_aggregate ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID'");

        executeQuietly("ALTER TABLE ai_jury_session MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空'");
        executeQuietly("ALTER TABLE ai_judge_report MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空'");
        executeQuietly("ALTER TABLE ai_jury_aggregate MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空'");

        createIndexIfMissing("ai_jury_session", "idx_jury_session_scoring_session_status",
                "CREATE INDEX idx_jury_session_scoring_session_status ON ai_jury_session (scoring_session_id, status)");
        createIndexIfMissing("ai_judge_report", "idx_judge_report_scoring_session",
                "CREATE INDEX idx_judge_report_scoring_session ON ai_judge_report (scoring_session_id)");
        createIndexIfMissing("ai_jury_aggregate", "idx_jury_aggregate_scoring_session",
                "CREATE INDEX idx_jury_aggregate_scoring_session ON ai_jury_aggregate (scoring_session_id)");
    }

    private void addColumnIfMissing(String tableName, String columnName, String sql) {
        if (!columnExists(tableName, columnName)) {
            jdbc.execute(sql);
        }
    }

    private void createIndexIfMissing(String tableName, String indexName, String sql) {
        if (!indexExists(tableName, indexName)) {
            executeQuietly(sql);
        }
    }

    private boolean columnExists(String tableName, String columnName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (ResultSet columns = connection.getMetaData().getColumns(null, null, tableName, null)) {
                while (columns.next()) {
                    if (columnName.equalsIgnoreCase(columns.getString("COLUMN_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private boolean indexExists(String tableName, String indexName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (ResultSet indexes = connection.getMetaData().getIndexInfo(null, null, tableName, false, false)) {
                while (indexes.next()) {
                    String existingName = indexes.getString("INDEX_NAME");
                    if (existingName != null && indexName.equalsIgnoreCase(existingName)) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private void executeQuietly(String sql) {
        try {
            jdbc.execute(sql);
        } catch (Exception ignored) {
            // Schema compatibility is best-effort across MySQL and H2 MySQL mode.
        }
    }

    private void seedMissingDefaults() {
        for (Map<String, Object> payload : defaultPersonaPayloads()) {
            upsertDefault(payload, false);
        }
    }

    private List<AiJudgePersona> listAllPersonas() {
        List<AiJudgePersona> personas = personaMapper.selectList(
                new LambdaQueryWrapper<AiJudgePersona>().orderByAsc(AiJudgePersona::getCode)
        );
        if (personas == null) {
            return List.of();
        }
        if (personas.isEmpty() && jdbc != null) {
            seedMissingDefaults();
            personas = personaMapper.selectList(
                    new LambdaQueryWrapper<AiJudgePersona>().orderByAsc(AiJudgePersona::getCode)
            );
            if (personas == null) {
                return List.of();
            }
        }
        return personas;
    }

    private Object sanitizeUserValue(Object value) {
        if (value == null) return null;
        if (value instanceof String text) {
            return containsSensitiveToken(text) ? "" : text;
        }
        if (value instanceof List<?> list) {
            return list.stream().map(this::sanitizeUserValue).toList();
        }
        if (value instanceof Map<?, ?> map) {
            Map<String, Object> sanitized = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() == null) continue;
                String key = String.valueOf(entry.getKey());
                if (containsSensitiveToken(key)) continue;
                sanitized.put(key, sanitizeUserValue(entry.getValue()));
            }
            return sanitized;
        }
        return value;
    }

    private boolean containsSensitiveToken(String text) {
        String normalized = text.toLowerCase();
        return normalized.contains("prompt")
                || normalized.contains("rubric")
                || normalized.contains("weight")
                || normalized.contains("internal")
                || normalized.contains("version")
                || normalized.contains("hash")
                || normalized.contains("scoring_bias")
                || normalized.contains("rubric_focus")
                || normalized.contains("prompt_modifier")
                || normalized.contains("内部");
    }

    private void upsertDefault(Map<String, Object> payload, boolean overwrite) {
        String code = normalizeCode(String.valueOf(payload.get("code")));
        AiJudgePersona existing = personaMapper.selectOne(
                new LambdaQueryWrapper<AiJudgePersona>().eq(AiJudgePersona::getCode, code)
        );
        if (existing != null && !overwrite && hasDetailedProfile(existing)) return;

        AiJudgePersona persona = existing == null ? new AiJudgePersona() : existing;
        persona.setCode(code);
        applyPatch(persona, payload);
        persona.setUpdatedAt(LocalDateTime.now());
        if (persona.getId() == null) {
            persona.setCreatedAt(LocalDateTime.now());
            personaMapper.insert(persona);
        } else {
            personaMapper.updateById(persona);
        }
    }

    private void applyPatch(AiJudgePersona persona, Map<String, Object> patch) {
        if (patch.containsKey("name")) persona.setName(str(patch.get("name")));
        if (patch.containsKey("short_label")) persona.setShortLabel(str(patch.get("short_label")));
        if (patch.containsKey("focus_dimensions")) persona.setFocusDimensionsJson(writeJson(patch.get("focus_dimensions")));
        if (patch.containsKey("prompt_modifier")) persona.setPromptModifier(str(patch.get("prompt_modifier")));
        if (patch.containsKey("description")) persona.setDescription(str(patch.get("description")));
        if (patch.containsKey("enabled")) persona.setEnabled(Boolean.parseBoolean(String.valueOf(patch.get("enabled"))));
        if (patch.containsKey("scoring_bias")) persona.setScoringBiasJson(writeJson(patch.get("scoring_bias")));
        if (patch.containsKey("judge_profile")) {
            persona.setJudgeProfileJson(writeJson(mergeJsonMap(persona.getJudgeProfileJson(), patch.get("judge_profile"))));
        }
        if (patch.containsKey("rubric_focus")) {
            persona.setRubricFocusJson(writeJson(mergeJsonMap(persona.getRubricFocusJson(), patch.get("rubric_focus"))));
        }
    }

    private boolean hasDetailedProfile(AiJudgePersona persona) {
        return persona.getJudgeProfileJson() != null && !persona.getJudgeProfileJson().isBlank()
                && persona.getRubricFocusJson() != null && !persona.getRubricFocusJson().isBlank();
    }

    private Map<String, Object> mergeJsonMap(String currentJson, Object patchValue) {
        Map<String, Object> merged = new LinkedHashMap<>(readJson(currentJson, Map.class, Map.of()));
        if (patchValue instanceof Map<?, ?> patchMap) {
            for (Map.Entry<?, ?> entry : patchMap.entrySet()) {
                if (entry.getKey() != null) merged.put(String.valueOf(entry.getKey()), entry.getValue());
            }
        }
        return merged;
    }

    private String writeJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? new ArrayList<>() : value);
        } catch (Exception e) {
            throw new IllegalArgumentException("画像JSON序列化失败", e);
        }
    }

    @SuppressWarnings("unchecked")
    private <T> T readJson(String json, Class<?> type, T fallback) {
        if (json == null || json.isBlank()) return fallback;
        try {
            if (Map.class.equals(type)) {
                return (T) objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
            }
            if (List.class.equals(type)) {
                return (T) objectMapper.readValue(json, new TypeReference<List<Object>>() {});
            }
            return fallback;
        } catch (Exception e) {
            return fallback;
        }
    }

    private String normalizeCode(String code) {
        return code == null ? "" : code.trim().toUpperCase();
    }

    private String str(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
