package com.orep.backend.service;

import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.entity.TrackRubricConfig;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class RubricResolverServiceTest {

    @Test
    void resolveCombinesRubricInternalVersionAndEvidenceSchema() {
        TrackRubricConfigService rubricService = mock(TrackRubricConfigService.class);
        TrackEvidenceSchemaService schemaService = mock(TrackEvidenceSchemaService.class);
        TrackRubricConfig rubric = rubric();
        TrackEvidenceSchema schema = schema();
        when(rubricService.resolveActive("request-track-id", "请求赛道名")).thenReturn(rubric);
        when(schemaService.resolveActive("track-it", "新一代信息技术赛道")).thenReturn(schema);

        RubricResolverService service = new RubricResolverService(rubricService, schemaService);

        ResolvedRubric resolved = service.resolve("request-track-id", "请求赛道名");

        assertEquals("rubric-it-v1.2", resolved.getRubricId());
        assertEquals("v1.2-internal", resolved.getRubricInternalVersion());
        assertEquals("rubric-secret-hash", resolved.getRubricHash());
        assertEquals("42赛道梯度评分规则v1.2-证据审查版/新一代信息技术赛道.md", resolved.getRubricPath());
        assertEquals("track-it", resolved.getTrackId());
        assertEquals("新一代信息技术赛道", resolved.getTrackName());
        assertEquals(88L, resolved.getEvidenceSchemaId());
        assertEquals("schema-it-v1.2", resolved.getEvidenceSchemaVersion());
        assertEquals("schema-secret-hash", resolved.getEvidenceSchemaHash());
        verify(schemaService).resolveActive("track-it", "新一代信息技术赛道");
    }

    @Test
    void missingEvidenceSchemaFallsBackToGeneratedSchemaForActiveRubric() {
        TrackRubricConfigService rubricService = mock(TrackRubricConfigService.class);
        TrackEvidenceSchemaService schemaService = mock(TrackEvidenceSchemaService.class);
        IllegalStateException missingSchema = new IllegalStateException("未找到启用证据结构，请联系管理员");
        when(rubricService.resolveActive("track-it", "新一代信息技术赛道")).thenReturn(rubric());
        when(schemaService.resolveActive("track-it", "新一代信息技术赛道")).thenThrow(missingSchema);
        TrackEvidenceSchema generated = schema();
        generated.setId(null);
        generated.setSchemaVersion("v1.2");
        generated.setSchemaHash("generated-schema-hash");
        when(schemaService.generatedSchema("track-it", "新一代信息技术赛道")).thenReturn(generated);

        RubricResolverService service = new RubricResolverService(rubricService, schemaService);

        ResolvedRubric resolved = service.resolve("track-it", "新一代信息技术赛道");

        assertEquals("generated-schema-hash", resolved.getEvidenceSchemaHash());
        assertEquals("v1.2", resolved.getEvidenceSchemaVersion());
        verify(schemaService).generatedSchema("track-it", "新一代信息技术赛道");
    }

    private TrackRubricConfig rubric() {
        TrackRubricConfig rubric = new TrackRubricConfig();
        rubric.setTrackId("track-it");
        rubric.setTrackName("新一代信息技术赛道");
        rubric.setRubricId("rubric-it-v1.2");
        rubric.setInternalVersion("v1.2-internal");
        rubric.setRubricHash("rubric-secret-hash");
        rubric.setRubricPath("42赛道梯度评分规则v1.2-证据审查版/新一代信息技术赛道.md");
        rubric.setStatus("active");
        rubric.setActiveSlot("ACTIVE");
        return rubric;
    }

    private TrackEvidenceSchema schema() {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setId(88L);
        schema.setTrackId("track-it");
        schema.setTrackName("新一代信息技术赛道");
        schema.setSchemaVersion("schema-it-v1.2");
        schema.setSchemaHash("schema-secret-hash");
        schema.setMaterialTypesJson("[\"代码仓库\"]");
        schema.setFrameTargetsJson("[\"代码模块\",\"系统演示\"]");
        schema.setDemoActionsJson("[\"现场运行核心流程\"]");
        schema.setRiskPatternsJson("[\"模板套壳\"]");
        schema.setThirdPartyPackagingSignalsJson("[\"公开模板结构高度相似\"]");
        schema.setAcceptableEvidenceLevelsJson("[\"E3\",\"E4\",\"E5\"]");
        schema.setStatus("active");
        schema.setActiveSlot("ACTIVE");
        return schema;
    }
}
