# OREP AI Scoring P7 Rubric And Evidence Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 AI 评分会话在用户只选择赛道时，后台同时黑盒绑定 active 评分规则和 active 赛道证据 schema，为后续 42 赛道差异化抽帧、OCR、材料解析和风险识别提供稳定配置。

**Architecture:** 在既有 `track_rubric_config` 基础上新增 `track_evidence_schema`，并用 `RubricResolverService` 统一解析 active rubric + active evidence schema。`AiScoringSessionService.createSession` 改为依赖 resolver，session 内部保存 evidence schema id/version/hash，但用户 DTO 不返回 schema 原文、规则版本、prompt 或权重。P7 不做 P8 规则引擎算分，只建立“赛道配置必须齐全才能进入正式评分”的黑盒地基。

**Tech Stack:** Spring Boot 3 + MyBatis Plus + MySQL/H2 tests；现有 `TrackRubricConfigService`、`AiScoringSessionService`、`AiScoreEvidenceBundleService`、`ai_scoring_session`。

---

## 0. Scope

本计划只做 P7：

- 新增 `track_evidence_schema` 表、实体、Mapper、Service。
- 新增 `ResolvedRubric` DTO 和 `RubricResolverService`。
- session 创建时同时绑定 active rubric 和 active evidence schema。
- evidence schema 原文仅后端内部使用，普通用户 API 不返回。
- 给三个样板赛道提供可测试 schema：新一代信息技术、医学技术、餐饮。

本计划不做：

- 不做 P8 规则引擎评分。
- 不解析 42 份 Markdown 规则全文为完整机器规则。
- 不做管理员规则配置 UI。
- 不让用户选择规则版本或 schema 版本。
- 不把 schema 原文返回给前端。

---

## 1. File Structure

### Backend Files

- Modify: `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
  - Add `evidence_schema_id` and `evidence_schema_version` to `ai_scoring_session`.
  - Add `track_evidence_schema` table.
- Modify: `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
  - Mirror SQL.
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoringSession.java`
  - Add `evidenceSchemaId`, `evidenceSchemaVersion`.
- Create: `backend/src/main/java/com/orep/backend/entity/TrackEvidenceSchema.java`
  - Stores active evidence schema JSON for one track.
- Create: `backend/src/main/java/com/orep/backend/mapper/TrackEvidenceSchemaMapper.java`
  - MyBatis Plus mapper.
- Create: `backend/src/main/java/com/orep/backend/dto/ResolvedRubric.java`
  - Internal resolver DTO containing rubric + schema metadata and JSON strings.
- Create: `backend/src/main/java/com/orep/backend/service/TrackEvidenceSchemaService.java`
  - Resolve active schema and provide sample schema builders for three tracks.
- Create: `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`
  - Resolve active rubric and active evidence schema together.
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
  - Replace direct `TrackRubricConfigService` dependency with `RubricResolverService`.
  - Persist schema id/version internally.
- Test: `backend/src/test/java/com/orep/backend/service/TrackEvidenceSchemaServiceTest.java`
- Test: `backend/src/test/java/com/orep/backend/service/RubricResolverServiceTest.java`
- Modify tests:
  - `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`
  - Any controller/service test that constructs `AiScoringSessionService` directly.

---

## 2. Data Model

### SQL Changes

Modify both SQL files:

- `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`

Add these columns to the `ai_scoring_session` create statement after `rubric_hash`:

```sql
  evidence_schema_id BIGINT NULL,
  evidence_schema_version VARCHAR(64) NULL,
```

Add this table after `track_rubric_config`:

```sql
CREATE TABLE IF NOT EXISTS track_evidence_schema (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  track_id VARCHAR(64) NOT NULL,
  track_name VARCHAR(128) NOT NULL,
  schema_version VARCHAR(64) NOT NULL,
  schema_hash VARCHAR(128) NOT NULL,
  material_types_json JSON NOT NULL,
  frame_targets_json JSON NOT NULL,
  demo_actions_json JSON NOT NULL,
  risk_patterns_json JSON NOT NULL,
  third_party_packaging_signals_json JSON NOT NULL,
  acceptable_evidence_levels_json JSON NOT NULL,
  status VARCHAR(32) NOT NULL,
  active_slot VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_track_evidence_active_slot (track_id, active_slot),
  INDEX idx_track_evidence_schema_track (track_id, status)
);
```

Do not add foreign keys in this phase. Existing SQL files use lightweight schema and H2/MySQL tests are easier to keep stable without FK migration complexity.

---

## 3. Task P7-A: Add Track Evidence Schema Table, Entity, Mapper

**Files:**

- Modify: `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoringSession.java`
- Create: `backend/src/main/java/com/orep/backend/entity/TrackEvidenceSchema.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/TrackEvidenceSchemaMapper.java`

- [ ] **Step 1: Add `TrackEvidenceSchema` entity**

Create `backend/src/main/java/com/orep/backend/entity/TrackEvidenceSchema.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("track_evidence_schema")
public class TrackEvidenceSchema {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String trackId;
    private String trackName;
    private String schemaVersion;
    private String schemaHash;
    private String materialTypesJson;
    private String frameTargetsJson;
    private String demoActionsJson;
    private String riskPatternsJson;
    private String thirdPartyPackagingSignalsJson;
    private String acceptableEvidenceLevelsJson;
    private String status;
    private String activeSlot;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

- [ ] **Step 2: Add mapper**

Create `backend/src/main/java/com/orep/backend/mapper/TrackEvidenceSchemaMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.TrackEvidenceSchema;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TrackEvidenceSchemaMapper extends BaseMapper<TrackEvidenceSchema> {
}
```

- [ ] **Step 3: Extend session entity**

Modify `backend/src/main/java/com/orep/backend/entity/AiScoringSession.java`, adding fields after `rubricHash`:

```java
private Long evidenceSchemaId;
private String evidenceSchemaVersion;
```

- [ ] **Step 4: Update SQL**

In both SQL files, add the two session columns and the `track_evidence_schema` create table exactly as shown in section 2.

- [ ] **Step 5: Compile**

Run:

```bash
cd backend && mvn test -DskipTests
```

Expected: `BUILD SUCCESS`.

---

## 4. Task P7-B: Add TrackEvidenceSchemaService Tests

**Files:**

- Create: `backend/src/test/java/com/orep/backend/service/TrackEvidenceSchemaServiceTest.java`

- [ ] **Step 1: Write failing tests**

Create `backend/src/test/java/com/orep/backend/service/TrackEvidenceSchemaServiceTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.mapper.TrackEvidenceSchemaMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class TrackEvidenceSchemaServiceTest {

    @Test
    void resolvesActiveSchemaForTrackWithoutLeakingToUserDto() {
        TrackEvidenceSchemaMapper mapper = mock(TrackEvidenceSchemaMapper.class);
        TrackEvidenceSchema active = schema("track-it", "新一代信息技术赛道", "schema-it-v1.2");
        when(mapper.selectOne(any())).thenReturn(active);

        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mapper);

        TrackEvidenceSchema resolved = service.resolveActive("track-it", null);

        assertEquals("schema-it-v1.2", resolved.getSchemaVersion());
        assertTrue(resolved.getFrameTargetsJson().contains("代码"));
        assertTrue(resolved.getRiskPatternsJson().contains("模板套壳"));
    }

    @Test
    void failsWhenNoActiveSchemaExists() {
        TrackEvidenceSchemaMapper mapper = mock(TrackEvidenceSchemaMapper.class);
        when(mapper.selectOne(any())).thenReturn(null);

        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mapper);

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> service.resolveActive("track-missing", "未知赛道"));

        assertTrue(error.getMessage().contains("该赛道证据标准尚未配置"));
    }

    @Test
    void sampleSchemasAreDifferentForThreeTracks() {
        TrackEvidenceSchemaService service = new TrackEvidenceSchemaService(mock(TrackEvidenceSchemaMapper.class));

        TrackEvidenceSchema it = service.sampleSchema("新一代信息技术赛道");
        TrackEvidenceSchema medical = service.sampleSchema("医学技术赛道");
        TrackEvidenceSchema catering = service.sampleSchema("餐饮赛道");

        assertNotEquals(it.getFrameTargetsJson(), medical.getFrameTargetsJson());
        assertNotEquals(medical.getFrameTargetsJson(), catering.getFrameTargetsJson());
        assertTrue(it.getFrameTargetsJson().contains("代码"));
        assertTrue(medical.getFrameTargetsJson().contains("质控"));
        assertTrue(catering.getFrameTargetsJson().contains("食材"));
    }

    private TrackEvidenceSchema schema(String trackId, String trackName, String version) {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setId(1L);
        schema.setTrackId(trackId);
        schema.setTrackName(trackName);
        schema.setSchemaVersion(version);
        schema.setSchemaHash("schema-secret-hash");
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
}
```

- [ ] **Step 2: Run RED test**

Run:

```bash
cd backend && mvn test -Dtest=TrackEvidenceSchemaServiceTest
```

Expected: FAIL because `TrackEvidenceSchemaService` does not exist yet.

---

## 5. Task P7-C: Implement TrackEvidenceSchemaService

**Files:**

- Create: `backend/src/main/java/com/orep/backend/service/TrackEvidenceSchemaService.java`

- [ ] **Step 1: Add service**

Create `backend/src/main/java/com/orep/backend/service/TrackEvidenceSchemaService.java`:

```java
package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.mapper.TrackEvidenceSchemaMapper;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

@Service
public class TrackEvidenceSchemaService {
    private final TrackEvidenceSchemaMapper mapper;

    public TrackEvidenceSchemaService(TrackEvidenceSchemaMapper mapper) {
        this.mapper = mapper;
    }

    public TrackEvidenceSchema resolveActive(String trackId, String trackName) {
        LambdaQueryWrapper<TrackEvidenceSchema> wrapper = new LambdaQueryWrapper<TrackEvidenceSchema>()
                .eq(TrackEvidenceSchema::getStatus, "active")
                .eq(TrackEvidenceSchema::getActiveSlot, "ACTIVE")
                .last("LIMIT 1");
        if (trackId != null && !trackId.isBlank()) {
            wrapper.eq(TrackEvidenceSchema::getTrackId, trackId);
        } else if (trackName != null && !trackName.isBlank()) {
            wrapper.eq(TrackEvidenceSchema::getTrackName, trackName);
        } else {
            throw new IllegalArgumentException("trackId 或 trackName 不能为空");
        }

        TrackEvidenceSchema active = mapper.selectOne(wrapper);
        if (active == null) {
            throw new IllegalStateException("该赛道证据标准尚未配置，请联系管理员");
        }
        return active;
    }

    public TrackEvidenceSchema sampleSchema(String trackName) {
        String name = trackName == null ? "" : trackName.trim();
        if (name.contains("医学技术")) {
            return build("track-medical-technology", "医学技术赛道",
                    List.of("SOP", "质控记录", "校准记录", "报告样张", "脱敏说明"),
                    List.of("样本编号核对", "仪器界面", "质控曲线", "报告字段", "脱敏处理"),
                    List.of("仪器操作", "结果记录", "异常复核", "报告审核"),
                    List.of("无质控记录", "报告无法对应原始数据", "越权诊断", "隐私未脱敏"),
                    List.of("设备自动输出被包装成学生能力", "医院机构能力被包装成团队项目"));
        }
        if (name.contains("餐饮")) {
            return build("track-catering", "餐饮赛道",
                    List.of("标准菜谱", "食材验收", "成本表", "温控留样", "试吃反馈"),
                    List.of("食材克重", "加工关键动作", "火候温度", "摆盘出品", "食品安全记录"),
                    List.of("切配", "烹制", "装盘", "服务", "清洁消毒"),
                    List.of("只有成品图", "预制菜冒充现场制作", "无温控留样", "成本无法对应"),
                    List.of("外购成品包装", "文化故事替代技能", "食品安全记录后补"));
        }
        return build("track-it", "新一代信息技术赛道",
                List.of("代码仓库", "架构图", "接口文档", "测试报告", "部署日志"),
                List.of("代码模块", "系统演示", "接口调用", "数据库/日志", "部署控制台"),
                List.of("登录流程", "核心业务流程", "异常处理", "数据看板", "权限验证"),
                List.of("模板套壳", "低代码包装", "第三方系统二次包装", "API 包装"),
                List.of("公开模板结构高度相似", "比赛前一次性导入大量代码", "演示功能找不到代码对应"));
    }

    private TrackEvidenceSchema build(String trackId,
                                      String trackName,
                                      List<String> materialTypes,
                                      List<String> frameTargets,
                                      List<String> demoActions,
                                      List<String> riskPatterns,
                                      List<String> thirdPartySignals) {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setTrackId(trackId);
        schema.setTrackName(trackName);
        schema.setSchemaVersion("v1.2");
        schema.setMaterialTypesJson(jsonArray(materialTypes));
        schema.setFrameTargetsJson(jsonArray(frameTargets));
        schema.setDemoActionsJson(jsonArray(demoActions));
        schema.setRiskPatternsJson(jsonArray(riskPatterns));
        schema.setThirdPartyPackagingSignalsJson(jsonArray(thirdPartySignals));
        schema.setAcceptableEvidenceLevelsJson("[\"E0\",\"E1\",\"E2\",\"E3\",\"E4\",\"E5\"]");
        schema.setSchemaHash(sha256(String.join("|", List.of(
                schema.getTrackId(),
                schema.getSchemaVersion(),
                schema.getMaterialTypesJson(),
                schema.getFrameTargetsJson(),
                schema.getDemoActionsJson(),
                schema.getRiskPatternsJson(),
                schema.getThirdPartyPackagingSignalsJson(),
                schema.getAcceptableEvidenceLevelsJson()
        ))));
        schema.setStatus("active");
        schema.setActiveSlot("ACTIVE");
        return schema;
    }

    private String jsonArray(List<String> values) {
        return values.stream()
                .map(value -> "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"")
                .collect(java.util.stream.Collectors.joining(",", "[", "]"));
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            throw new IllegalStateException("schema hash failed", e);
        }
    }
}
```

- [ ] **Step 2: Run GREEN test**

Run:

```bash
cd backend && mvn test -Dtest=TrackEvidenceSchemaServiceTest
```

Expected: PASS.

---

## 6. Task P7-D: Add ResolvedRubric And RubricResolverService

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/ResolvedRubric.java`
- Create: `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`
- Test: `backend/src/test/java/com/orep/backend/service/RubricResolverServiceTest.java`

- [ ] **Step 1: Write failing resolver test**

Create `backend/src/test/java/com/orep/backend/service/RubricResolverServiceTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.entity.TrackRubricConfig;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class RubricResolverServiceTest {

    @Test
    void resolvesRubricAndEvidenceSchemaTogether() {
        TrackRubricConfigService rubricService = mock(TrackRubricConfigService.class);
        TrackEvidenceSchemaService schemaService = mock(TrackEvidenceSchemaService.class);
        when(rubricService.resolveActive("track-it", "新一代信息技术赛道")).thenReturn(rubric());
        when(schemaService.resolveActive("track-it", "新一代信息技术赛道")).thenReturn(schema());

        RubricResolverService service = new RubricResolverService(rubricService, schemaService);

        ResolvedRubric resolved = service.resolve("track-it", "新一代信息技术赛道");

        assertEquals("track-it", resolved.getTrackId());
        assertEquals("新一代信息技术赛道", resolved.getTrackName());
        assertEquals("rubric-it-v1.2", resolved.getRubricId());
        assertEquals("schema-it-v1.2", resolved.getEvidenceSchemaVersion());
        assertEquals(88L, resolved.getEvidenceSchemaId());
        assertTrue(resolved.getFrameTargetsJson().contains("代码"));
    }

    @Test
    void failsWhenEvidenceSchemaMissingEvenIfRubricExists() {
        TrackRubricConfigService rubricService = mock(TrackRubricConfigService.class);
        TrackEvidenceSchemaService schemaService = mock(TrackEvidenceSchemaService.class);
        when(rubricService.resolveActive("track-it", "新一代信息技术赛道")).thenReturn(rubric());
        when(schemaService.resolveActive("track-it", "新一代信息技术赛道"))
                .thenThrow(new IllegalStateException("该赛道证据标准尚未配置，请联系管理员"));

        RubricResolverService service = new RubricResolverService(rubricService, schemaService);

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> service.resolve("track-it", "新一代信息技术赛道"));
        assertTrue(error.getMessage().contains("证据标准"));
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
```

- [ ] **Step 2: Run RED test**

Run:

```bash
cd backend && mvn test -Dtest=RubricResolverServiceTest
```

Expected: FAIL because `ResolvedRubric` and `RubricResolverService` do not exist.

- [ ] **Step 3: Add `ResolvedRubric` DTO**

Create `backend/src/main/java/com/orep/backend/dto/ResolvedRubric.java`:

```java
package com.orep.backend.dto;

import lombok.Data;

@Data
public class ResolvedRubric {
    private String trackId;
    private String trackName;
    private String rubricId;
    private String rubricInternalVersion;
    private String rubricHash;
    private String rubricPath;
    private Long evidenceSchemaId;
    private String evidenceSchemaVersion;
    private String evidenceSchemaHash;
    private String materialTypesJson;
    private String frameTargetsJson;
    private String demoActionsJson;
    private String riskPatternsJson;
    private String thirdPartyPackagingSignalsJson;
    private String acceptableEvidenceLevelsJson;
}
```

- [ ] **Step 4: Add resolver service**

Create `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`:

```java
package com.orep.backend.service;

import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.entity.TrackRubricConfig;
import org.springframework.stereotype.Service;

@Service
public class RubricResolverService {
    private final TrackRubricConfigService rubricConfigService;
    private final TrackEvidenceSchemaService evidenceSchemaService;

    public RubricResolverService(TrackRubricConfigService rubricConfigService,
                                 TrackEvidenceSchemaService evidenceSchemaService) {
        this.rubricConfigService = rubricConfigService;
        this.evidenceSchemaService = evidenceSchemaService;
    }

    public ResolvedRubric resolve(String trackId, String trackName) {
        TrackRubricConfig rubric = rubricConfigService.resolveActive(trackId, trackName);
        TrackEvidenceSchema schema = evidenceSchemaService.resolveActive(rubric.getTrackId(), rubric.getTrackName());

        ResolvedRubric resolved = new ResolvedRubric();
        resolved.setTrackId(rubric.getTrackId());
        resolved.setTrackName(rubric.getTrackName());
        resolved.setRubricId(rubric.getRubricId());
        resolved.setRubricInternalVersion(rubric.getInternalVersion());
        resolved.setRubricHash(rubric.getRubricHash());
        resolved.setRubricPath(rubric.getRubricPath());
        resolved.setEvidenceSchemaId(schema.getId());
        resolved.setEvidenceSchemaVersion(schema.getSchemaVersion());
        resolved.setEvidenceSchemaHash(schema.getSchemaHash());
        resolved.setMaterialTypesJson(schema.getMaterialTypesJson());
        resolved.setFrameTargetsJson(schema.getFrameTargetsJson());
        resolved.setDemoActionsJson(schema.getDemoActionsJson());
        resolved.setRiskPatternsJson(schema.getRiskPatternsJson());
        resolved.setThirdPartyPackagingSignalsJson(schema.getThirdPartyPackagingSignalsJson());
        resolved.setAcceptableEvidenceLevelsJson(schema.getAcceptableEvidenceLevelsJson());
        return resolved;
    }
}
```

- [ ] **Step 5: Run GREEN test**

Run:

```bash
cd backend && mvn test -Dtest=RubricResolverServiceTest
```

Expected: PASS.

---

## 7. Task P7-E: Bind Resolved Rubric And Evidence Schema In Scoring Session

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`

- [ ] **Step 1: Update session service constructor dependency**

In `AiScoringSessionService`, replace:

```java
private final TrackRubricConfigService rubricConfigService;
```

with:

```java
private final RubricResolverService rubricResolverService;
```

Change constructor parameter from `TrackRubricConfigService rubricConfigService` to `RubricResolverService rubricResolverService`.

- [ ] **Step 2: Update `createSession` to use resolver**

Replace:

```java
TrackRubricConfig rubric = rubricConfigService.resolveActive(request.getTrackId(), request.getTrackName());
```

with:

```java
ResolvedRubric rubric = rubricResolverService.resolve(request.getTrackId(), request.getTrackName());
```

Then keep existing rubric fields, but use DTO getters:

```java
session.setTrackId(rubric.getTrackId());
session.setTrackName(rubric.getTrackName());
session.setRubricId(rubric.getRubricId());
session.setRubricInternalVersion(rubric.getRubricInternalVersion());
session.setRubricHash(rubric.getRubricHash());
session.setEvidenceSchemaId(rubric.getEvidenceSchemaId());
session.setEvidenceSchemaVersion(rubric.getEvidenceSchemaVersion());
```

Update `toFingerprintInput` signature from `TrackRubricConfig rubric` to `ResolvedRubric rubric`.

- [ ] **Step 3: Update imports**

Remove:

```java
import com.orep.backend.entity.TrackRubricConfig;
```

Add:

```java
import com.orep.backend.dto.ResolvedRubric;
```

- [ ] **Step 4: Update test helper**

In `AiScoringSessionServiceTest`, replace mocked `TrackRubricConfigService` with mocked `RubricResolverService`.

Add helper:

```java
private ResolvedRubric activeResolvedRubric() {
    ResolvedRubric rubric = new ResolvedRubric();
    rubric.setTrackId("track-it");
    rubric.setTrackName("新一代信息技术赛道");
    rubric.setRubricId("rubric-it-v1");
    rubric.setRubricInternalVersion("v1.2-internal");
    rubric.setRubricHash("secret-hash");
    rubric.setRubricPath("/secret/rubric.md");
    rubric.setEvidenceSchemaId(88L);
    rubric.setEvidenceSchemaVersion("schema-it-v1.2");
    rubric.setEvidenceSchemaHash("schema-secret-hash");
    rubric.setFrameTargetsJson("[\"代码模块\",\"系统演示\"]");
    return rubric;
}
```

Assert inserted session stores schema metadata:

```java
assertEquals(88L, inserted.getEvidenceSchemaId());
assertEquals("schema-it-v1.2", inserted.getEvidenceSchemaVersion());
```

- [ ] **Step 5: Run session tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoringSessionServiceTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest
```

Expected: PASS.

---

## 8. Task P7-F: User API Redaction And No-Schema-Leak Regression

**Files:**

- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`

- [ ] **Step 1: Add redaction assertions to session controller test**

In the session creation JSON assertions, add:

```java
.andExpect(jsonPath("$.data.evidenceSchemaId").doesNotExist())
.andExpect(jsonPath("$.data.evidenceSchemaVersion").doesNotExist())
.andExpect(jsonPath("$.data.frameTargetsJson").doesNotExist())
.andExpect(jsonPath("$.data.riskPatternsJson").doesNotExist())
.andExpect(jsonPath("$.data.thirdPartyPackagingSignalsJson").doesNotExist())
```

- [ ] **Step 2: Add redaction assertions to upload controller test**

In `uploadsVideoCreatesSessionAndReturnsRedactedResponse`, add:

```java
.andExpect(jsonPath("$.data.evidenceSchemaId").doesNotExist())
.andExpect(jsonPath("$.data.evidenceSchemaVersion").doesNotExist())
.andExpect(jsonPath("$.data.frameTargetsJson").doesNotExist())
.andExpect(jsonPath("$.data.riskPatternsJson").doesNotExist())
```

- [ ] **Step 3: Run redaction tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreSessionControllerTest,AiScoreUploadControllerTest
```

Expected: PASS.

---

## 9. Task P7-G: Verification And Main Plan Update

**Files:**

- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [ ] **Step 1: Run P7 narrow tests**

Run:

```bash
cd backend && mvn test -Dtest=TrackEvidenceSchemaServiceTest,RubricResolverServiceTest,AiScoringSessionServiceTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest
```

Expected: PASS.

- [ ] **Step 2: Run backend full regression**

Run:

```bash
cd backend && mvn test
```

Expected: PASS.

- [ ] **Step 3: Update P7 board row**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`, update P7 row:

```markdown
| P7 | 已完成 | v1.2 规则加载与赛道证据 schema | 已完成 | `cd backend && mvn test` 通过；新增 active evidence schema、rubric/schema resolver，session 创建时后台黑盒绑定 |
```

- [ ] **Step 4: Append completion record**

Append:

```markdown
### 本轮完成记录：P7 v1.2 规则加载与赛道证据 schema

- 完成时间：2026-06-23 Asia/Shanghai
- 修改文件：
  - `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
  - `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
  - `backend/src/main/java/com/orep/backend/entity/AiScoringSession.java`
  - `backend/src/main/java/com/orep/backend/entity/TrackEvidenceSchema.java`
  - `backend/src/main/java/com/orep/backend/mapper/TrackEvidenceSchemaMapper.java`
  - `backend/src/main/java/com/orep/backend/dto/ResolvedRubric.java`
  - `backend/src/main/java/com/orep/backend/service/TrackEvidenceSchemaService.java`
  - `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
  - `backend/src/test/java/com/orep/backend/service/TrackEvidenceSchemaServiceTest.java`
  - `backend/src/test/java/com/orep/backend/service/RubricResolverServiceTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`
  - `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`
  - `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`
- 后端验证：
  - `cd backend && mvn test -Dtest=TrackEvidenceSchemaServiceTest,RubricResolverServiceTest,AiScoringSessionServiceTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest` 通过。
  - `cd backend && mvn test` 通过。
- 前端验证：
  - 本轮无前端改动。
- 手工验证：
  - 未启动浏览器；本轮以后端自动化测试验证为准。
- 已知风险：
  - 本轮只提供 schema 地基和三个样板 schema builder，42 赛道 schema 初始化/管理仍需后续导入脚本或管理端。
  - 本轮不做 P8 规则引擎，schema 暂不直接改变分数。
- 下一步：
  - 进入 P8：规则引擎评分与扣分项结构化，让模型提取证据，规则引擎计算分数和扣分。
```

---

## 10. Self-Review

Spec coverage:

- Active evidence schema table: Task P7-A.
- Three sample schemas: Task P7-B/C.
- Active rubric + schema resolver: Task P7-D.
- Session creation binds both: Task P7-E.
- User API does not leak schema: Task P7-F.
- Plan board update: Task P7-G.

Placeholder scan:

- No `TBD`, `TODO`, `implement later`, or undefined file paths.
- Code blocks define all new Java classes and test assertions referenced later.

Type consistency:

- `TrackEvidenceSchema` field names match SQL snake_case via MyBatis Plus camelCase mapping.
- `ResolvedRubric` getters used by `AiScoringSessionService` match DTO field names.
- Session fields `evidenceSchemaId` and `evidenceSchemaVersion` match SQL columns.

