package com.orep.backend.service;

import com.orep.backend.entity.AiJudgePersona;
import com.orep.backend.mapper.AiJudgePersonaMapper;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiJudgePersonaServiceTest {

    @Test
    void defaultPersonasContainDetailedProfilesAndRubricFocus() {
        AiJudgePersonaService service = new AiJudgePersonaService(mock(AiJudgePersonaMapper.class), null);

        List<Map<String, Object>> personas = service.defaultPersonaPayloads();

        assertThat(personas).hasSize(16);
        Map<String, Object> intj = personas.stream()
                .filter(item -> "INTJ".equals(item.get("code")))
                .findFirst()
                .orElseThrow();
        assertThat((Map<String, Object>) intj.get("judge_profile"))
                .containsKeys("core_traits", "scoring_style", "evidence_preference", "sensitive_risks",
                        "likely_high_score_reason", "likely_low_score_reason", "feedback_style");
        assertThat((Map<String, Object>) intj.get("rubric_focus"))
                .containsKeys("primary_dimensions", "primary_items", "secondary_dimensions");
    }

    @Test
    void updatePersonaKeepsCodeAndSerializesEditableProfile() {
        AiJudgePersonaMapper mapper = mock(AiJudgePersonaMapper.class);
        AiJudgePersona existing = new AiJudgePersona();
        existing.setId(7L);
        existing.setCode("INTJ");
        existing.setName("战略架构评委");
        existing.setShortLabel("重系统性");
        existing.setFocusDimensionsJson("[\"skill_level\"]");
        existing.setPromptModifier("关注架构边界");
        existing.setJudgeProfileJson("{\"core_traits\":[\"系统化\"],\"scoring_style\":\"偏严格\"}");
        existing.setRubricFocusJson("{\"primary_dimensions\":[\"skill_level\"],\"primary_items\":[\"技术先进性\"],\"secondary_dimensions\":[\"innovation\"]}");
        existing.setEnabled(true);
        when(mapper.selectOne(any())).thenReturn(existing);

        AiJudgePersonaService service = new AiJudgePersonaService(mapper, null);
        AiJudgePersona updated = service.updatePersona("INTJ", Map.of(
                "code", "ENTP",
                "name", "系统战略评委",
                "judge_profile", Map.of("scoring_style", "更关注长期路线"),
                "rubric_focus", Map.of("primary_items", List.of("系统架构图", "技术选型对比"))
        ));

        assertThat(updated.getCode()).isEqualTo("INTJ");
        assertThat(updated.getName()).isEqualTo("系统战略评委");
        assertThat(updated.getJudgeProfileJson()).contains("更关注长期路线");
        assertThat(updated.getRubricFocusJson()).contains("技术选型对比");
        verify(mapper).updateById(updated);
    }

    @Test
    void userPersonaPayloadDoesNotExposePromptBiasOrInternalRubricFocus() {
        AiJudgePersona persona = new AiJudgePersona();
        persona.setId(1L);
        persona.setCode("ENTP");
        persona.setName("创新挑战评委");
        persona.setShortLabel("爱追问创新闭环");
        persona.setFocusDimensionsJson("[\"innovation\",\"application_value\"]");
        persona.setJudgeProfileJson("{\"core_traits\":[\"质疑假设\"],\"scoring_style\":\"关注创新证据\",\"top_concerns\":[\"包装风险\"]}");
        persona.setRubricFocusJson("{\"primary_dimensions\":[\"innovation\"],\"primary_items\":[\"内部观察点A\"]}");
        persona.setScoringBiasJson("{\"risk_weight\":0.3}");
        persona.setPromptModifier("内部prompt片段");
        persona.setDescription("从创新性和真实性角度复核");
        persona.setEnabled(true);

        AiJudgePersonaService service = new AiJudgePersonaService(mock(AiJudgePersonaMapper.class), null);

        Map<String, Object> payload = service.toUserPayload(persona);
        String json = String.valueOf(payload);

        assertThat(payload).containsKeys("id", "code", "name", "short_label", "focus_dimensions", "description", "enabled", "persona_view");
        assertThat(payload.get("id")).isEqualTo(1L);
        assertThat(json)
                .doesNotContain("prompt")
                .doesNotContain("Prompt")
                .doesNotContain("prompt_modifier")
                .doesNotContain("scoring_bias")
                .doesNotContain("rubric_focus")
                .doesNotContain("内部观察点A")
                .doesNotContain("risk_weight")
                .doesNotContain("内部prompt片段");
    }

    @Test
    void listUserPersonaPayloadsFiltersDisabledPersonasWhileAdminKeepsDisabledPersonas() {
        AiJudgePersona enabled = new AiJudgePersona();
        enabled.setId(1L);
        enabled.setCode("ENTP");
        enabled.setName("创新挑战评委");
        enabled.setEnabled(true);

        AiJudgePersona disabled = new AiJudgePersona();
        disabled.setId(2L);
        disabled.setCode("INTJ");
        disabled.setName("战略架构评委");
        disabled.setEnabled(false);

        AiJudgePersonaMapper mapper = mock(AiJudgePersonaMapper.class);
        when(mapper.selectList(any())).thenReturn(List.of(enabled, disabled));
        AiJudgePersonaService service = new AiJudgePersonaService(mapper, null);

        List<Map<String, Object>> userPayloads = service.listUserPersonaPayloads();
        List<Map<String, Object>> adminPayloads = service.listAdminPersonaPayloads();

        assertThat(userPayloads).extracting(item -> item.get("code")).containsExactly("ENTP");
        assertThat(adminPayloads).extracting(item -> item.get("code")).containsExactly("ENTP", "INTJ");
    }

    @Test
    void toUserPayloadSanitizesSensitiveLookingWhitelistedProfileValues() {
        AiJudgePersona persona = new AiJudgePersona();
        persona.setCode("ENTP");
        persona.setName("创新挑战评委");
        persona.setShortLabel("爱追问创新闭环");
        persona.setFocusDimensionsJson("[\"innovation\"]");
        persona.setJudgeProfileJson("""
                {
                  "core_traits":["追问 rubric_focus 细节","关注真实证据"],
                  "scoring_style":"根据 scoring_bias weight 调整",
                  "evidence_preference":{"safe":"用户证据","internal":"prompt_modifier 规则"},
                  "top_concerns":["version hash 泄露","包装风险"],
                  "feedback_style":"直接反馈"
                }
                """);
        persona.setDescription("从创新性和真实性角度复核");
        persona.setEnabled(true);

        AiJudgePersonaService service = new AiJudgePersonaService(mock(AiJudgePersonaMapper.class), null);

        Map<String, Object> payload = service.toUserPayload(persona);
        String json = String.valueOf(payload);

        assertThat(json)
                .doesNotContain("rubric_focus")
                .doesNotContain("scoring_bias")
                .doesNotContain("weight")
                .doesNotContain("prompt_modifier")
                .doesNotContain("version")
                .doesNotContain("hash");
        assertThat(json).contains("关注真实证据", "用户证据", "包装风险", "直接反馈");
    }

    @Test
    void listPersonaPayloadsHandleNullSelectListAsEmpty() {
        AiJudgePersonaMapper mapper = mock(AiJudgePersonaMapper.class);
        when(mapper.selectList(any())).thenReturn(null);
        AiJudgePersonaService service = new AiJudgePersonaService(mapper, null);

        assertThat(service.listUserPersonaPayloads()).isEmpty();
        assertThat(service.listAdminPersonaPayloads()).isEmpty();
        assertThat(service.listPersonaPayloads()).isEmpty();
    }

    @Test
    void ensureJurySchemaCompatibilityAddsSessionNativeColumnsToExistingTables() {
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:ai_jury_schema_compat;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("""
                CREATE TABLE ai_jury_session (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  meeting_id BIGINT NOT NULL,
                  status VARCHAR(32) NOT NULL DEFAULT 'processing',
                  PRIMARY KEY (id)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_judge_report (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  meeting_id BIGINT NOT NULL,
                  PRIMARY KEY (id)
                )
                """);
        jdbc.execute("""
                CREATE TABLE ai_jury_aggregate (
                  id BIGINT NOT NULL AUTO_INCREMENT,
                  meeting_id BIGINT NOT NULL,
                  PRIMARY KEY (id)
                )
                """);
        AiJudgePersonaService service = new AiJudgePersonaService(mock(AiJudgePersonaMapper.class), jdbc);

        service.ensureJurySchemaCompatibility();

        assertThat(hasColumn(jdbc, "ai_jury_session", "scoring_session_id")).isTrue();
        assertThat(hasColumn(jdbc, "ai_judge_report", "scoring_session_id")).isTrue();
        assertThat(hasColumn(jdbc, "ai_jury_aggregate", "scoring_session_id")).isTrue();
    }

    private boolean hasColumn(JdbcTemplate jdbc, String tableName, String columnName) {
        return Boolean.TRUE.equals(jdbc.execute((ConnectionCallback<Boolean>) connection -> {
            try (var columns = connection.getMetaData().getColumns(null, null, tableName, null)) {
                while (columns.next()) {
                    if (columnName.equalsIgnoreCase(columns.getString("COLUMN_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }
}
