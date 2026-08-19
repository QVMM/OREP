# OREP AI评分 P8 规则引擎评分与扣分项结构化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AI 评分从“模型直接给分”升级为“模型只提交结构化观察点，后端规则引擎稳定计算分数、扣分项和报告校准信息”。

**Architecture:** P8 不接真实大模型，不重构前端报告页；先在后端建立可测试的确定性规则引擎。模型输出用 DTO 表达并做字段/证据锚点校验，规则引擎根据 observation、score cap、deduction、recovery 计算 `finalScore`，扣分项落入 `ai_score_deduction`，观察点落入 `ai_score_observation`，报告继续写入现有 `ai_score_report` 的 JSON 字段并补充结构化校准 JSON。

**Tech Stack:** Spring Boot 3 + MyBatis Plus + MySQL/H2-compatible SQL + JUnit 5 + Mockito + Jackson。

---

## 1. Scope

P8 只做评分可信度地基：

- 规则引擎纯函数：输入结构化观察点和可选历史追回项，输出分数、扣分项、追回分、校准说明。
- 结构化模型输出校验：缺字段、非法分值、引用不存在证据锚点时拒绝进入规则引擎。
- 扣分项结构化存储：记录 deductionId、observationCode、evidenceLevel、acceptanceCriteria、maxRecoverablePoints。
- 报告桥接：把规则引擎结果写入 `ai_score_report` 可展示 JSON，便于 P10 报告页使用。

P8 不做：

- 不接真实 LLM 调用。
- 不实现 P9 连续评分记忆恢复流程的完整查询，只预留 recovery 输入 DTO。
- 不重构前端报告面板。
- 不新增用户可选择规则版本。

---

## 2. File Map

**Create backend entities and mappers**

- `backend/src/main/java/com/orep/backend/entity/AiScoreObservation.java`
- `backend/src/main/java/com/orep/backend/entity/AiScoreDeduction.java`
- `backend/src/main/java/com/orep/backend/mapper/AiScoreObservationMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/AiScoreDeductionMapper.java`

**Create DTOs**

- `backend/src/main/java/com/orep/backend/dto/AiScoreModelObservation.java`
- `backend/src/main/java/com/orep/backend/dto/AiScoreModelDeduction.java`
- `backend/src/main/java/com/orep/backend/dto/AiScoreModelOutput.java`
- `backend/src/main/java/com/orep/backend/dto/AiScoreRecoveryInput.java`
- `backend/src/main/java/com/orep/backend/dto/AiScoreRuleEngineResult.java`

**Create services**

- `backend/src/main/java/com/orep/backend/service/AiScoreModelOutputValidator.java`
- `backend/src/main/java/com/orep/backend/service/AiScoreRuleEngine.java`
- `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`

**Modify existing**

- `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- `backend/src/main/resources/sql/create_ai_score_report_table.sql`
- `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
- `dockerrun/sql/backend-resources/create_ai_score_report_table.sql`
- `dockerrun/sql/backend-resources/upgrade_ai_scoring_session_p7_schema.sql`

**Create tests**

- `backend/src/test/java/com/orep/backend/service/AiScoreModelOutputValidatorTest.java`
- `backend/src/test/java/com/orep/backend/service/AiScoreRuleEngineTest.java`
- `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`
- `backend/src/test/java/com/orep/backend/controller/AiScoreStructuredResultControllerTest.java`

---

## 3. Data Model

### Table `ai_score_observation`

```sql
CREATE TABLE IF NOT EXISTS ai_score_observation (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  dimension_name VARCHAR(128) NOT NULL,
  raw_score DECIMAL(6,2) NOT NULL,
  score_cap DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  validity_status VARCHAR(32) NOT NULL,
  model_reason TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_observation_session (session_id),
  INDEX idx_ai_score_observation_report (report_id),
  INDEX idx_ai_score_observation_code (observation_code)
);
```

### Table `ai_score_deduction`

```sql
CREATE TABLE IF NOT EXISTS ai_score_deduction (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  report_id BIGINT NULL,
  deduction_id VARCHAR(128) NOT NULL,
  observation_code VARCHAR(128) NOT NULL,
  dimension_code VARCHAR(64) NOT NULL,
  deducted_points DECIMAL(6,2) NOT NULL,
  recovered_points DECIMAL(6,2) NOT NULL DEFAULT 0,
  reason TEXT NOT NULL,
  required_fix TEXT NOT NULL,
  acceptance_criteria TEXT NOT NULL,
  max_recoverable_points DECIMAL(6,2) NOT NULL,
  evidence_level VARCHAR(16) NOT NULL,
  confidence DECIMAL(5,4) NOT NULL,
  evidence_anchor_ids_json JSON NOT NULL,
  recovery_source_deduction_id VARCHAR(128) NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_deduction_session_id (session_id, deduction_id),
  INDEX idx_ai_score_deduction_report (report_id),
  INDEX idx_ai_score_deduction_observation (observation_code)
);
```

### `ai_score_report` additions

```sql
ALTER TABLE ai_score_report ADD COLUMN rule_engine_version VARCHAR(64) NULL;
ALTER TABLE ai_score_report ADD COLUMN structured_result_json TEXT NULL;
ALTER TABLE ai_score_report ADD COLUMN current_score_cap DECIMAL(6,2) NULL;
ALTER TABLE ai_score_report ADD COLUMN recovered_score DECIMAL(6,2) NULL;
```

For existing databases, add these columns in an idempotent upgrade script if they are missing.

---

## 4. Task P8-A: Tables, Entities, Mappers

**Files:**

- Modify: `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
- Modify: `backend/src/main/resources/sql/create_ai_score_report_table.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_score_report_table.sql`
- Create: `backend/src/main/resources/sql/upgrade_ai_scoring_p8_rule_engine.sql`
- Create: `dockerrun/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql`
- Modify: `dockerrun/docker-compose.offline.yml`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreObservation.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreDeduction.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreObservationMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreDeductionMapper.java`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`

- [ ] **Step 1: Write mapper/entity compile test**

Create `backend/src/test/java/com/orep/backend/service/AiScoreStructuredEntityCompileTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AiScoreStructuredEntityCompileTest {
    @Test
    void structuredEntitiesExposeExpectedFields() {
        AiScoreObservation observation = new AiScoreObservation();
        observation.setSessionId(101L);
        observation.setObservationCode("tech_demo_stability");
        observation.setScoreCap(new BigDecimal("85.00"));
        observation.setEvidenceAnchorIdsJson("[1,2]");

        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setSessionId(101L);
        deduction.setDeductionId("TECH_DEMO_FAILURE_001");
        deduction.setDeductedPoints(new BigDecimal("6.00"));
        deduction.setMaxRecoverablePoints(new BigDecimal("6.00"));

        AiScoreReport report = new AiScoreReport();
        report.setRuleEngineVersion("rule-engine-v1");
        report.setCurrentScoreCap(new BigDecimal("85.00"));
        report.setRecoveredScore(new BigDecimal("0.00"));

        assertEquals("tech_demo_stability", observation.getObservationCode());
        assertEquals("TECH_DEMO_FAILURE_001", deduction.getDeductionId());
        assertEquals("rule-engine-v1", report.getRuleEngineVersion());
    }
}
```

- [ ] **Step 2: Run failing compile test**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredEntityCompileTest
```

Expected: FAIL because `AiScoreObservation` and `AiScoreDeduction` do not exist, and `AiScoreReport` lacks P8 fields.

- [ ] **Step 3: Add entity and mapper classes**

Create `backend/src/main/java/com/orep/backend/entity/AiScoreObservation.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_observation")
public class AiScoreObservation {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long reportId;
    private String observationCode;
    private String dimensionCode;
    private String dimensionName;
    private BigDecimal rawScore;
    private BigDecimal scoreCap;
    private String evidenceLevel;
    private BigDecimal confidence;
    private String evidenceAnchorIdsJson;
    private String validityStatus;
    private String modelReason;
    private LocalDateTime createdAt;
}
```

Create `backend/src/main/java/com/orep/backend/entity/AiScoreDeduction.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_deduction")
public class AiScoreDeduction {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long reportId;
    private String deductionId;
    private String observationCode;
    private String dimensionCode;
    private BigDecimal deductedPoints;
    private BigDecimal recoveredPoints;
    private String reason;
    private String requiredFix;
    private String acceptanceCriteria;
    private BigDecimal maxRecoverablePoints;
    private String evidenceLevel;
    private BigDecimal confidence;
    private String evidenceAnchorIdsJson;
    private String recoverySourceDeductionId;
    private String status;
    private LocalDateTime createdAt;
}
```

Create `backend/src/main/java/com/orep/backend/mapper/AiScoreObservationMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiScoreObservation;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiScoreObservationMapper extends BaseMapper<AiScoreObservation> {
}
```

Create `backend/src/main/java/com/orep/backend/mapper/AiScoreDeductionMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiScoreDeduction;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiScoreDeductionMapper extends BaseMapper<AiScoreDeduction> {
}
```

Modify `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java` and add:

```java
private String ruleEngineVersion;
private String structuredResultJson;
private BigDecimal currentScoreCap;
private BigDecimal recoveredScore;
```

- [ ] **Step 4: Add SQL and compose mount**

Append `ai_score_observation` and `ai_score_deduction` tables to both `create_ai_scoring_session_tables.sql` copies.

Add P8 columns to both `create_ai_score_report_table.sql` copies:

```sql
`rule_engine_version` VARCHAR(64) DEFAULT NULL COMMENT '规则引擎版本',
`structured_result_json` TEXT COMMENT '规则引擎结构化结果 JSON',
`current_score_cap` DECIMAL(6,2) DEFAULT NULL COMMENT '本轮证据上限',
`recovered_score` DECIMAL(6,2) DEFAULT NULL COMMENT '本轮追回分',
```

Create `backend/src/main/resources/sql/upgrade_ai_scoring_p8_rule_engine.sql` and mirror to `dockerrun/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql`.

The upgrade script must:

- `CREATE TABLE IF NOT EXISTS ai_score_observation (...)`
- `CREATE TABLE IF NOT EXISTS ai_score_deduction (...)`
- conditionally add report columns using `information_schema.COLUMNS` checks.

Modify `dockerrun/docker-compose.offline.yml` and mount:

```yaml
- ./sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql:/docker-entrypoint-initdb.d/19-ai-scoring-p8-rule-engine-upgrade.sql:ro
```

- [ ] **Step 5: Run test**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredEntityCompileTest
```

Expected: PASS.

---

## 5. Task P8-B: Model Output DTO And Validator

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreModelObservation.java`
- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreModelDeduction.java`
- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreModelOutput.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreModelOutputValidator.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreModelOutputValidatorTest.java`

- [ ] **Step 1: Write validator tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreModelOutputValidatorTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.dto.AiScoreModelDeduction;
import com.orep.backend.dto.AiScoreModelObservation;
import com.orep.backend.dto.AiScoreModelOutput;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AiScoreModelOutputValidatorTest {
    private final AiScoreModelOutputValidator validator = new AiScoreModelOutputValidator();

    @Test
    void acceptsCompleteOutputWithExistingEvidenceAnchors() {
        AiScoreModelOutput output = validOutput();

        assertDoesNotThrow(() -> validator.validate(output, Set.of(1L, 2L, 3L)));
    }

    @Test
    void rejectsMissingDeductionId() {
        AiScoreModelOutput output = validOutput();
        output.getObservations().get(0).getDeductions().get(0).setDeductionId(null);

        assertThrows(IllegalArgumentException.class,
                () -> validator.validate(output, Set.of(1L, 2L, 3L)));
    }

    @Test
    void rejectsMissingObservationCode() {
        AiScoreModelOutput output = validOutput();
        output.getObservations().get(0).setObservationCode(" ");

        assertThrows(IllegalArgumentException.class,
                () -> validator.validate(output, Set.of(1L, 2L, 3L)));
    }

    @Test
    void rejectsHallucinatedEvidenceAnchor() {
        AiScoreModelOutput output = validOutput();
        output.getObservations().get(0).setEvidenceAnchorIds(List.of(999L));

        assertThrows(IllegalArgumentException.class,
                () -> validator.validate(output, Set.of(1L, 2L, 3L)));
    }

    @Test
    void rejectsInvalidConfidenceAndNegativeDeductions() {
        AiScoreModelOutput output = validOutput();
        output.getObservations().get(0).setConfidence(new BigDecimal("1.50"));
        output.getObservations().get(0).getDeductions().get(0).setDeductedPoints(new BigDecimal("-1"));

        assertThrows(IllegalArgumentException.class,
                () -> validator.validate(output, Set.of(1L, 2L, 3L)));
    }

    private AiScoreModelOutput validOutput() {
        AiScoreModelDeduction deduction = new AiScoreModelDeduction();
        deduction.setDeductionId("TECH_DEMO_FAILURE_001");
        deduction.setObservationCode("tech_demo_stability");
        deduction.setDimensionCode("technical");
        deduction.setDeductedPoints(new BigDecimal("6"));
        deduction.setReason("核心演示流程出现中断");
        deduction.setRequiredFix("完成稳定现场演示");
        deduction.setAcceptanceCriteria("本轮视频中能连续展示核心流程，且无明显报错或中断");
        deduction.setMaxRecoverablePoints(new BigDecimal("6"));
        deduction.setEvidenceLevel("E3");
        deduction.setConfidence(new BigDecimal("0.72"));
        deduction.setEvidenceAnchorIds(List.of(1L, 2L));

        AiScoreModelObservation observation = new AiScoreModelObservation();
        observation.setObservationCode("tech_demo_stability");
        observation.setDimensionCode("technical");
        observation.setDimensionName("技术能力");
        observation.setRawScore(new BigDecimal("82"));
        observation.setScoreCap(new BigDecimal("85"));
        observation.setEvidenceLevel("E3");
        observation.setConfidence(new BigDecimal("0.80"));
        observation.setEvidenceAnchorIds(List.of(1L, 2L));
        observation.setModelReason("现场演示存在中断");
        observation.setDeductions(List.of(deduction));

        AiScoreModelOutput output = new AiScoreModelOutput();
        output.setBaseScore(new BigDecimal("100"));
        output.setCurrentScoreCap(new BigDecimal("85"));
        output.setObservations(List.of(observation));
        return output;
    }
}
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreModelOutputValidatorTest
```

Expected: FAIL because DTO and validator classes do not exist.

- [ ] **Step 3: Add DTOs**

Create `AiScoreModelDeduction`, `AiScoreModelObservation`, `AiScoreModelOutput` with Lombok `@Data`.

`AiScoreModelDeduction` fields:

```java
private String deductionId;
private String observationCode;
private String dimensionCode;
private BigDecimal deductedPoints;
private String reason;
private String requiredFix;
private String acceptanceCriteria;
private BigDecimal maxRecoverablePoints;
private String evidenceLevel;
private BigDecimal confidence;
private List<Long> evidenceAnchorIds;
```

`AiScoreModelObservation` fields:

```java
private String observationCode;
private String dimensionCode;
private String dimensionName;
private BigDecimal rawScore;
private BigDecimal scoreCap;
private String evidenceLevel;
private BigDecimal confidence;
private List<Long> evidenceAnchorIds;
private String modelReason;
private List<AiScoreModelDeduction> deductions;
```

`AiScoreModelOutput` fields:

```java
private BigDecimal baseScore;
private BigDecimal currentScoreCap;
private List<AiScoreModelObservation> observations;
```

- [ ] **Step 4: Implement validator**

Create `backend/src/main/java/com/orep/backend/service/AiScoreModelOutputValidator.java`.

Required behavior:

- reject null output.
- reject missing `baseScore`, `currentScoreCap`, `observations`.
- reject empty `observationCode`, `dimensionCode`, `dimensionName`, `evidenceLevel`.
- reject confidence outside `[0, 1]`.
- reject negative `rawScore`, `scoreCap`, `deductedPoints`, `maxRecoverablePoints`.
- reject evidence anchor ids not included in `existingAnchorIds`.
- reject deduction with missing `deductionId`, `observationCode`, `reason`, `requiredFix`, `acceptanceCriteria`.
- reject deduction whose `observationCode` differs from parent observation.

- [ ] **Step 5: Run validator tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreModelOutputValidatorTest
```

Expected: PASS.

---

## 6. Task P8-C: Rule Engine Pure Function

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreRecoveryInput.java`
- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreRuleEngineResult.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreRuleEngine.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreRuleEngineTest.java`

- [ ] **Step 1: Write rule engine tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreRuleEngineTest.java`.

Include tests:

```java
@Test
void capsFinalScoreAtCurrentEvidenceCap() {
    AiScoreRuleEngineResult result = engine.score(output(100, 85, deduction("D1", 6)), List.of());
    assertEquals(new BigDecimal("85.00"), result.getFinalScore());
    assertEquals(new BigDecimal("94.00"), result.getRawScore());
}

@Test
void recoversOnlyWithinPreviousMaxRecoverablePoints() {
    AiScoreRecoveryInput recovery = recovery("OLD_D1", "fixed", "10", "6");
    AiScoreRuleEngineResult result = engine.score(output(90, 100, deduction("NEW_D1", 4)), List.of(recovery));
    assertEquals(new BigDecimal("86.00"), result.getRawScore());
    assertEquals(new BigDecimal("6.00"), result.getRecoveredScore());
    assertEquals(new BigDecimal("92.00"), result.getFinalScore());
}

@Test
void recoveryCannotOffsetNewDeductionBeyondCap() {
    AiScoreRecoveryInput recovery = recovery("OLD_D1", "fixed", "20", "20");
    AiScoreRuleEngineResult result = engine.score(output(100, 85, deduction("NEW_D1", 8)), List.of(recovery));
    assertEquals(new BigDecimal("85.00"), result.getFinalScore());
}

@Test
void notEnoughEvidenceCapPreventsPerfectScoreEvenIfNoCurrentDeduction() {
    AiScoreRecoveryInput recovery = recovery("OLD_D1", "fixed", "20", "20");
    AiScoreRuleEngineResult result = engine.score(output(100, 85), List.of(recovery));
    assertEquals(new BigDecimal("85.00"), result.getFinalScore());
}
```

Use helper methods in the test class to build `AiScoreModelOutput`, `AiScoreModelDeduction`, and `AiScoreRecoveryInput`.

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreRuleEngineTest
```

Expected: FAIL because rule engine classes do not exist.

- [ ] **Step 3: Add recovery/result DTOs**

`AiScoreRecoveryInput` fields:

```java
private String sourceDeductionId;
private String recoveryStatus;
private BigDecimal requestedRecoverPoints;
private BigDecimal maxRecoverablePoints;
private String acceptanceEvidence;
```

`AiScoreRuleEngineResult` fields:

```java
private String ruleEngineVersion;
private BigDecimal baseScore;
private BigDecimal currentDeductions;
private BigDecimal rawScore;
private BigDecimal recoveredScore;
private BigDecimal currentScoreCap;
private BigDecimal finalScore;
private List<AiScoreModelObservation> observations;
private List<AiScoreModelDeduction> deductions;
private List<AiScoreRecoveryInput> acceptedRecoveries;
private String calibrationJson;
```

- [ ] **Step 4: Implement `AiScoreRuleEngine`**

Rules:

```text
currentDeductions = sum(current deductions)
rawScore = max(0, baseScore - currentDeductions)
acceptedRecoveries = recoveryStatus == "fixed"
recoveredScore = sum(min(requestedRecoverPoints, maxRecoverablePoints))
finalScore = min(currentScoreCap, rawScore + recoveredScore)
```

Use `BigDecimal` scale 2 and `RoundingMode.HALF_UP`.

`calibrationJson` must include:

```json
{
  "baseScore": 100,
  "currentDeductions": 8,
  "rawScore": 92,
  "recoveredScore": 6,
  "currentScoreCap": 85,
  "finalScore": 85,
  "ruleEngineVersion": "rule-engine-v1",
  "whyNotHundred": "本轮受证据上限限制，无法进入满分档"
}
```

- [ ] **Step 5: Run rule engine tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreRuleEngineTest
```

Expected: PASS.

---

## 7. Task P8-D: Structured Result Persistence

**Files:**

- Create: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`

- [ ] **Step 1: Write persistence tests**

Create `AiScoreStructuredResultServiceTest` using mocks for:

- `AiScoreObservationMapper`
- `AiScoreDeductionMapper`
- `AiScoreReportMapper`
- `AiScoringSessionMapper`
- `AiScoreEvidenceAnchorMapper`

Tests:

- `storesObservationsDeductionsAndUpdatesReport`
- `rejectsModelOutputWithHallucinatedEvidenceAnchor`
- `marksSessionPartialReportReadyWhenValidationFails`

Expected assertions:

- valid output inserts observations and deductions.
- report gets `overallScore = finalScore`, `scoreCalibrationJson = result.calibrationJson`, `structuredResultJson` non-empty, `ruleEngineVersion = rule-engine-v1`, `currentScoreCap`, `recoveredScore`.
- session `status` becomes `completed`, `currentStage` becomes `rule_engine_completed`, `reportId` set.
- invalid evidence anchor id throws or marks failed according to method contract.

- [ ] **Step 2: Run failing tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultServiceTest
```

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement service**

Create `AiScoreStructuredResultService`.

Constructor dependencies:

```java
AiScoreModelOutputValidator validator
AiScoreRuleEngine ruleEngine
AiScoreObservationMapper observationMapper
AiScoreDeductionMapper deductionMapper
AiScoreReportMapper reportMapper
AiScoringSessionMapper sessionMapper
AiScoreEvidenceAnchorMapper evidenceAnchorMapper
ObjectMapper objectMapper
```

Method:

```java
@Transactional
public AiScoreRuleEngineResult applyStructuredResult(Long sessionId,
                                                     AiScoreModelOutput output,
                                                     List<AiScoreRecoveryInput> recoveries)
```

Implementation:

1. Load valid evidence anchor ids for `sessionId`.
2. Validate `output`.
3. Run rule engine.
4. Create or update one `AiScoreReport` for session meeting/report.
5. Insert observations and deductions with report id.
6. Update session report id/status/current stage.
7. Return result.

For P8, if no `meetingId` exists, allow `AiScoreReport.meetingId = 0` only if existing report table requires not null; document this as a temporary bridge until `ai_score_report` is fully session-native in P10.

- [ ] **Step 4: Run persistence tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultServiceTest
```

Expected: PASS.

---

## 8. Task P8-E: Controller Test Endpoint For Structured Result

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- Create: `backend/src/test/java/com/orep/backend/controller/AiScoreStructuredResultControllerTest.java`

P8 adds an internal/testable endpoint first:

```text
POST /api/ai-score/sessions/{sessionId}/structured-result
```

This endpoint accepts `AiScoreModelOutput` JSON and applies the rule engine. It is not a final production model callback; it is a deterministic integration point for P8 testing and future AI service callback.

- [ ] **Step 1: Write controller test**

Create `AiScoreStructuredResultControllerTest`.

Test:

- POST valid structured result returns `finalScore`, `rawScore`, `currentScoreCap`.
- response does not contain rubric hash/path/internal rule details.
- invalid result returns non-200 `Result` code or throws through existing handler pattern.

- [ ] **Step 2: Run failing controller test**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultControllerTest
```

Expected: FAIL because endpoint does not exist.

- [ ] **Step 3: Add controller endpoint**

Inject `AiScoreStructuredResultService` into `AiScoreController`.

Add:

```java
@PostMapping("/sessions/{sessionId}/structured-result")
public Result<AiScoreRuleEngineResult> applyStructuredResult(
        @PathVariable Long sessionId,
        @RequestBody AiScoreModelOutput output) {
    return Result.success(structuredResultService.applyStructuredResult(sessionId, output, List.of()));
}
```

If constructor changes break existing tests, update all `new AiScoreController(...)` calls to pass a mock `AiScoreStructuredResultService`.

- [ ] **Step 4: Run controller tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultControllerTest,AiScoreSessionControllerTest,AiScoreEvidenceBundleControllerTest,AiScoreResponseRedactionTest
```

Expected: PASS.

---

## 9. Task P8-F: Verification And Main Plan Update

**Files:**

- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [ ] **Step 1: Run P8 targeted tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredEntityCompileTest,AiScoreModelOutputValidatorTest,AiScoreRuleEngineTest,AiScoreStructuredResultServiceTest,AiScoreStructuredResultControllerTest
```

Expected: PASS.

- [ ] **Step 2: Run regression tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoringSessionServiceTest,AiScoreResponseRedactionTest,AiScoreSessionControllerTest,AiScoreEvidenceBundleControllerTest
```

Expected: PASS.

- [ ] **Step 3: Run full backend tests**

Run:

```bash
cd backend && mvn test
```

Expected: PASS.

- [ ] **Step 4: Update main execution board**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`:

- Set P8 status to `已完成`.
- Add completion record with:
  - modified files
  - targeted test count
  - full backend test count
  - known risks
  - next step P9

Known risks to record:

- P8 deterministic endpoint is a backend integration point, not real model callback.
- P8 accepts recovery inputs but does not query previous round memory; P9 owns that.
- `ai_score_report` remains meeting-oriented; P10/P12 should migrate fully to session-native report.

---

## 10. Self-Review

**Spec coverage:**

- Rule engine formula is covered in Task P8-C.
- Deduction structure is covered by `AiScoreModelDeduction`, `AiScoreDeduction`, and persistence tests.
- LLM output schema validation is covered by Task P8-B.
- Hallucinated evidence anchors are rejected by validator and service tests.
- Report bridge is covered by Task P8-D and P8-E.
- Black-box redaction remains covered by existing P7 tests and P8 controller regression.

**Placeholder scan:** No `TBD`, no “implement later”, no unbounded “add validation” steps. Each task has exact files, test commands, and expected outcomes.

**Type consistency:** DTO names and fields are consistent across validator, rule engine, persistence, and controller tasks.

**Execution choice:** Use Subagent-Driven execution. P8 tasks are mostly independent and can be reviewed task-by-task.
