package com.orep.backend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoringSessionRedactionMappingTest {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private static final String[] FORBIDDEN_FIELD_NAMES = {
            "rubricHash",
            "rubric_hash",
            "rubricPath",
            "rubric_path",
            "internalVersion",
            "internal_version",
            "rubricInternalVersion",
            "rubric_internal_version",
            "ruleEngineVersion",
            "rule_engine_version",
            "prompt",
            "weight",
            "evidenceSchemaId",
            "evidence_schema_id",
            "evidenceSchemaVersion",
            "evidence_schema_version",
            "evidenceSchemaHash",
            "evidence_schema_hash",
            "materialTypesJson",
            "frameTargetsJson",
            "demoActionsJson",
            "riskPatternsJson",
            "thirdPartyPackagingSignalsJson",
            "acceptableEvidenceLevelsJson"
    };

    private static final String[] FORBIDDEN_SECRET_VALUES = {
            "secret-rubric-hash",
            "/secret/rubric.md",
            "schema-secret-hash"
    };

    @Test
    void toUserResponseDropsInternalRubricAndEvidenceSchemaFieldsFromSessionEntity() throws Exception {
        AiScoringSession session = new AiScoringSession();
        session.setId(101L);
        session.setSessionNo("SC-20260623120000001");
        session.setStatus("created");
        session.setCurrentStage("created");
        session.setProgressPercent(0);
        session.setTrackName("新一代信息技术赛道");
        session.setSourceType("meeting_recording");
        session.setUseHistoryMemory(true);
        session.setJuryEnabled(false);
        session.setReportId(55L);
        session.setMeetingId(12L);
        session.setRubricInternalVersion("internal-v1");
        session.setRubricHash("secret-rubric-hash");
        session.setEvidenceSchemaId(999L);
        session.setEvidenceSchemaVersion("schema-secret-hash");
        session.setScoringFingerprint("fingerprint-secret");

        AiScoringSessionUserResponse response = service().toUserResponse(session);
        String responseJson = OBJECT_MAPPER.writeValueAsString(response);

        assertThat(responseJson).contains("\"sessionId\":101");
        assertNoForbiddenFieldNames(OBJECT_MAPPER.readTree(responseJson), responseJson);
        for (String token : FORBIDDEN_SECRET_VALUES) {
            assertThat(responseJson)
                    .describedAs("user response mapping should not serialize internal secret value <%s>: %s", token, responseJson)
                    .doesNotContain(token);
        }
    }

    @Test
    void reportBySessionRedactsInternalRuleEngineVersionFromCalibrationJson() throws Exception {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(101L);
        session.setSessionNo("SC-20260623120000001");
        session.setReportId(55L);
        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setSessionId(101L);
        report.setOverallScore(new BigDecimal("82.50"));
        report.setScoreCalibrationJson("{\"ruleEngineVersion\":\"p8-c\",\"finalScore\":\"82.50\"}");
        report.setStatus("completed");
        when(sessionMapper.selectById(101L)).thenReturn(session);
        when(reportMapper.selectById(55L)).thenReturn(report);

        AiScoreReportUserResponse response = service(sessionMapper, reportMapper).reportBySession(101L);
        String responseJson = OBJECT_MAPPER.writeValueAsString(response);

        assertThat(responseJson).contains("finalScore");
        assertThat(responseJson).doesNotContain("ruleEngineVersion");
        assertNoForbiddenFieldNames(OBJECT_MAPPER.readTree(responseJson), responseJson);
    }

    private static final String[] P11_JURY_FORBIDDEN_FIELDS = {
            "rubric_hash",
            "rubric_path",
            "internal_version",
            "prompt",
            "prompt_modifier",
            "weight",
            "scoring_bias",
            "rubric_focus",
            "standard_version",
            "persona_pool_version",
            "tokens_json",
            "provider",
            "model"
    };

    @Test
    void juryReviewUserResponseDoesNotExposeInternalFields() throws Exception {
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setSessionId(77L);
        response.setStatus("completed");
        response.setReviewMode("复核层");
        response.setOfficialScore(new BigDecimal("82.00"));
        AiJuryReviewUserResponse.MemberReview member = new AiJuryReviewUserResponse.MemberReview();
        member.setPersonaCode("INTJ");
        member.setDisplayName("系统架构评委");
        member.setRoleLabel("重系统性");
        member.setReferenceScore(new BigDecimal("80.00"));
        member.setPerspectiveQuestions(List.of("演示证据是否足够支撑技术能力？"));
        member.setTrainingSuggestions(List.of("补充真实运行演示和关键日志。"));
        response.setMembers(List.of(member));
        String json = OBJECT_MAPPER.writeValueAsString(response);

        for (String forbidden : P11_JURY_FORBIDDEN_FIELDS) {
            assertThat(json)
                    .describedAs("jury review response should not contain forbidden field: %s", forbidden)
                    .doesNotContain(forbidden);
        }
        assertNoForbiddenFieldNames(OBJECT_MAPPER.readTree(json), json);
    }

    private AiScoringSessionService service() {
        return service(mock(AiScoringSessionMapper.class), mock(AiScoreReportMapper.class));
    }

    private AiScoringSessionService service(AiScoringSessionMapper sessionMapper, AiScoreReportMapper reportMapper) {
        return new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class));
    }

    private void assertNoForbiddenFieldNames(JsonNode node, String responseJson) {
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                for (String forbiddenFieldName : FORBIDDEN_FIELD_NAMES) {
                    assertThat(field.getKey())
                            .describedAs("user response mapping should not serialize internal field name <%s>: %s", forbiddenFieldName, responseJson)
                            .isNotEqualTo(forbiddenFieldName);
                }
                assertNoForbiddenFieldNames(field.getValue(), responseJson);
            }
            return;
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                assertNoForbiddenFieldNames(child, responseJson);
            }
        }
    }
}
