package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.mapper.TrackEvidenceSchemaMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TrackEvidenceSchemaServiceTest {

    @Test
    void resolvesActiveSchemaByTrackId() {
        TrackEvidenceSchemaMapper mapper = mock(TrackEvidenceSchemaMapper.class);
        TrackEvidenceSchema active = schema("track-it", "新一代信息技术赛道", "schema-it-v1.2", "stable-schema-hash");
        when(mapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(active);

        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mapper);

        TrackEvidenceSchema resolved = service.resolveActive("track-it", null);

        assertEquals("schema-it-v1.2", resolved.getSchemaVersion());
        assertEquals("stable-schema-hash", resolved.getSchemaHash());
    }

    @Test
    void failsWhenNoActiveSchemaExists() {
        TrackEvidenceSchemaMapper mapper = mock(TrackEvidenceSchemaMapper.class);
        when(mapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mapper);

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> service.resolveActive("track-missing", "未知赛道"));

        assertTrue(error.getMessage().contains("未找到启用证据结构"));
    }

    @Test
    void sampleSchemasAreTrackSpecificAndNonEmpty() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));

        TrackEvidenceSchema it = service.sampleSchema("新一代信息技术赛道");
        TrackEvidenceSchema medical = service.sampleSchema("医学技术赛道");
        TrackEvidenceSchema catering = service.sampleSchema("餐饮赛道");
        TrackEvidenceSchema commerce = service.sampleSchema("商贸赛道");

        assertNotEquals(it.getSchemaHash(), medical.getSchemaHash());
        assertNotEquals(medical.getSchemaHash(), catering.getSchemaHash());
        assertNotEquals(catering.getSchemaHash(), commerce.getSchemaHash());
        assertEquals(it.getSchemaHash(), service.sampleSchema("新一代信息技术赛道").getSchemaHash());
        assertNotEquals(it.getFrameTargetsJson(), medical.getFrameTargetsJson());
        assertNotEquals(medical.getFrameTargetsJson(), catering.getFrameTargetsJson());
        assertNotEquals(catering.getFrameTargetsJson(), commerce.getFrameTargetsJson());

        assertSchemaComplete(it);
        assertSchemaComplete(medical);
        assertSchemaComplete(catering);
        assertSchemaComplete(commerce);

        assertTrue(it.getFrameTargetsJson().contains("代码"));
        assertTrue(it.getFrameTargetsJson().contains("系统演示"));
        assertTrue(it.getMaterialTypesJson().contains("技术架构"));
        assertTrue(it.getDemoActionsJson().contains("现场演示稳定性"));

        assertTrue(medical.getFrameTargetsJson().contains("临床"));
        assertTrue(medical.getRiskPatternsJson().contains("伦理合规"));
        assertTrue(medical.getMaterialTypesJson().contains("实验验证"));
        assertTrue(medical.getAcceptableEvidenceLevelsJson().contains("安全风险"));
        assertTrue(medical.getDemoActionsJson().contains("转化路径"));

        assertTrue(catering.getFrameTargetsJson().contains("产品制作流程"));
        assertTrue(catering.getRiskPatternsJson().contains("食品安全"));
        assertTrue(catering.getMaterialTypesJson().contains("成本毛利"));
        assertTrue(catering.getDemoActionsJson().contains("服务运营"));
        assertTrue(catering.getAcceptableEvidenceLevelsJson().contains("现场出品一致性"));

        assertTrue(commerce.getFrameTargetsJson().contains("交易流程"));
        assertTrue(commerce.getRiskPatternsJson().contains("订单"));
        assertTrue(commerce.getMaterialTypesJson().contains("商业模式"));
        assertTrue(commerce.getDemoActionsJson().contains("获客"));
        assertTrue(commerce.getAcceptableEvidenceLevelsJson().contains("供应链"));
    }

    @Test
    void sampleSchemaHashesMatchSeedSqlValues() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));

        assertEquals("5ab131370721a52aaf82b40bf938abe61393e9aba5c2b96bc6529c9f2cd90cbe",
                service.sampleSchema("新一代信息技术赛道").getSchemaHash());
        assertEquals("892447bfcb876448a41802eabe8370754d56f818eb8a02da3b30e6f5a778586b",
                service.sampleSchema("医学技术赛道").getSchemaHash());
        assertEquals("1a86b4e7dd35b4ee03f79c8c5a25530c21aab56389dfbbb6228f3e51f7e247d2",
                service.sampleSchema("餐饮赛道").getSchemaHash());
        assertEquals("491dcb2f8f0f2d9389fc2fbd44e30bd58ab6cf198d2df20561d7fe3a8aaf3c1a",
                service.sampleSchema("商贸赛道").getSchemaHash());
    }

    @Test
    void generatedSchemaSupportsAnyResolvedTrackIdentity() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));

        TrackEvidenceSchema agriculture = service.generatedSchema("track-a00c6482aa3e", "现代农业赛道");
        TrackEvidenceSchema food = service.generatedSchema("track-f0734338087e", "食品与粮食赛道");
        TrackEvidenceSchema generatedId = service.generatedSchema(null, "人工智能赛道");

        assertEquals("track-a00c6482aa3e", agriculture.getTrackId());
        assertEquals("现代农业赛道", agriculture.getTrackName());
        assertEquals("食品与粮食赛道", food.getTrackName());
        assertTrue(generatedId.getTrackId().startsWith("track-generated-"));
        assertEquals(agriculture.getSchemaHash(),
                service.generatedSchema("track-a00c6482aa3e", "现代农业赛道").getSchemaHash());
        assertNotEquals(agriculture.getSchemaHash(), food.getSchemaHash());
        assertTrue(agriculture.getMaterialTypesJson().contains("现代农业赛道"));
        assertTrue(food.getMaterialTypesJson().contains("食品与粮食赛道"));
        assertTrue(generatedId.getMaterialTypesJson().contains("人工智能赛道"));

        assertSchemaComplete(agriculture);
        assertSchemaComplete(food);
        assertSchemaComplete(generatedId);
    }

    @Test
    void generatedSchemaUsesSafeDefaultsWhenTrackIdentityIsBlank() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));

        TrackEvidenceSchema schema = service.generatedSchema(" ", " ");

        assertTrue(schema.getTrackId().startsWith("track-generated-"));
        assertEquals("未指定赛道", schema.getTrackName());
        assertSchemaComplete(schema);
    }

    @Test
    void hashChangesWhenVersionOrTrackIdentityChanges() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));
        TrackEvidenceSchema base = service.sampleSchema("新一代信息技术赛道");

        TrackEvidenceSchema changedVersion = copy(base);
        changedVersion.setSchemaVersion(base.getSchemaVersion() + "-next");

        TrackEvidenceSchema changedTrackId = copy(base);
        changedTrackId.setTrackId(base.getTrackId() + "-alt");

        TrackEvidenceSchema changedTrackName = copy(base);
        changedTrackName.setTrackName(base.getTrackName() + "-备用");

        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedVersion));
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedTrackId));
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedTrackName));
    }

    @Test
    void hashChangesWhenAnySchemaContentFieldChanges() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));
        TrackEvidenceSchema base = service.sampleSchema("新一代信息技术赛道");

        TrackEvidenceSchema changedMaterialTypes = copy(base);
        changedMaterialTypes.setMaterialTypesJson("[\"新增材料类型\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedMaterialTypes));

        TrackEvidenceSchema changedFrameTargets = copy(base);
        changedFrameTargets.setFrameTargetsJson("[\"新增证据框架\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedFrameTargets));

        TrackEvidenceSchema changedDemoActions = copy(base);
        changedDemoActions.setDemoActionsJson("[\"新增演示动作\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedDemoActions));

        TrackEvidenceSchema changedRiskPatterns = copy(base);
        changedRiskPatterns.setRiskPatternsJson("[\"新增风险模式\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedRiskPatterns));

        TrackEvidenceSchema changedThirdPartySignals = copy(base);
        changedThirdPartySignals.setThirdPartyPackagingSignalsJson("[\"新增第三方包装信号\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedThirdPartySignals));

        TrackEvidenceSchema changedAcceptableEvidenceLevels = copy(base);
        changedAcceptableEvidenceLevels.setAcceptableEvidenceLevelsJson("[\"新增可接受证据等级\"]");
        assertNotEquals(base.getSchemaHash(), service.calculateSchemaHash(changedAcceptableEvidenceLevels));
    }

    private void assertSchemaComplete(TrackEvidenceSchema schema) {
        assertNotBlank(schema.getMaterialTypesJson());
        assertNotBlank(schema.getFrameTargetsJson());
        assertNotBlank(schema.getDemoActionsJson());
        assertNotBlank(schema.getRiskPatternsJson());
        assertNotBlank(schema.getThirdPartyPackagingSignalsJson());
        assertNotBlank(schema.getAcceptableEvidenceLevelsJson());
        assertNotBlank(schema.getSchemaHash());
        assertDoesNotThrow(() -> HexFormatValidator.requireSha256(schema.getSchemaHash()));
    }

    private void assertNotBlank(String value) {
        assertFalse(value == null || value.isBlank());
    }

    private TrackEvidenceSchema schema(String trackId, String trackName, String version, String hash) {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setId(1L);
        schema.setTrackId(trackId);
        schema.setTrackName(trackName);
        schema.setSchemaVersion(version);
        schema.setSchemaHash(hash);
        schema.setMaterialTypesJson("[\"PPT\",\"测试报告\"]");
        schema.setFrameTargetsJson("[\"代码仓库\",\"系统演示\"]");
        schema.setDemoActionsJson("[\"现场运行核心流程\"]");
        schema.setRiskPatternsJson("[\"模板套壳\",\"第三方包装\"]");
        schema.setThirdPartyPackagingSignalsJson("[\"公开模板结构高度相似\"]");
        schema.setAcceptableEvidenceLevelsJson("[\"E3\",\"E4\",\"E5\"]");
        schema.setStatus("active");
        schema.setActiveSlot("ACTIVE");
        return schema;
    }

    private TrackEvidenceSchema copy(TrackEvidenceSchema source) {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setId(source.getId());
        schema.setTrackId(source.getTrackId());
        schema.setTrackName(source.getTrackName());
        schema.setSchemaVersion(source.getSchemaVersion());
        schema.setSchemaHash(source.getSchemaHash());
        schema.setMaterialTypesJson(source.getMaterialTypesJson());
        schema.setFrameTargetsJson(source.getFrameTargetsJson());
        schema.setDemoActionsJson(source.getDemoActionsJson());
        schema.setRiskPatternsJson(source.getRiskPatternsJson());
        schema.setThirdPartyPackagingSignalsJson(source.getThirdPartyPackagingSignalsJson());
        schema.setAcceptableEvidenceLevelsJson(source.getAcceptableEvidenceLevelsJson());
        schema.setStatus(source.getStatus());
        schema.setActiveSlot(source.getActiveSlot());
        return schema;
    }

    private static class HexFormatValidator {
        private static void requireSha256(String value) {
            if (!value.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException("not sha-256 hex");
            }
        }
    }
}
