# OREP Rule Engine Authority And Active Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 OREP AI 评分流水线从当前 `pilot_ready_not_active` 的影子/演练状态，推进到“Java 规则引擎可作为正式分权威入口，并且 active 准入只能由真实原始样本门禁放行”的可上线结构。

**Architecture:** 保持 LLM 只负责证据抽取，Java 规则引擎负责观测点、维度和总分计算。Python 继续提供证据结构和 shadow 对照，但正式分切换必须受赛道状态、真实样本质量报告、人工审计和灰度开关共同约束。

**Tech Stack:** Java Spring Boot backend, Python ai-scoring services, Vue user frontend, MySQL/H2 SQL migrations, pytest, Maven, Node test runner.

---

## Current Baseline

- 阶段0-8已完成。
- 42个赛道均有结构化规则文件。
- 2个试点赛道为 `pilot_completed`。
- 40个生成赛道为 `pilot_generated`，均 `activeAllowed=false`。
- 阶段8总账状态为 `pilot_ready_not_active`。
- 当前正式 `overallScore` 仍主要来自旧 LLM/校准链路，规则引擎分仍作为 shadow 展示。
- active 前必须替换真实原始样本并复跑候选门禁。

## Optimized Development Order

1. **先做权威计算入口**：没有 Java 规则引擎正式入口，真实样本门禁即使通过也不能安全 active。
2. **再补结构化落库字段**：让报告、复核、监控都能按15观测点追溯，而不是只看 JSON 摘要。
3. **再接真实样本准入**：把 synthetic 样本与 real raw 样本明确拆开，避免生成样本误上 production。
4. **再做人工审计/校准后台**：让规则变更、样本标注、active 审批有记录。
5. **最后做灰度、回滚、监控**：规则引擎正式接管必须可按赛道开关、可回滚、可告警。

---

### Task 1: Java Rule Engine Authoritative Score Gate

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java` or nearest existing callback test
- Reference: `backend/src/main/java/com/orep/backend/service/AiScoreRuleEngine.java`
- Reference: `ai-scoring/app/services/pipeline_payloads.py`

- [ ] **Step 1: Write failing backend callback test**

Create or extend a callback test asserting:

```java
@Test
void callbackUsesRuleEngineScoreAsOfficialOnlyWhenTrackIsActiveRuleEngineAuthority() {
    PipelineCallbackRequest request = new PipelineCallbackRequest();
    request.setOverallScore(new BigDecimal("91.00"));
    request.setLlmRawScore(new BigDecimal("91.00"));
    request.setRuleEngineScore(new BigDecimal("78.00"));
    request.setRuleEngineMode("authoritative");
    request.setTrackRuleStatus("active");
    request.setStructuredResult(Map.of(
            "ruleEngineScore", 78.00,
            "llmRawScore", 91.00,
            "status", "completed"
    ));

    // Existing helper should create a session/report, invoke callback, then reload report.
    AiScoreReportUserResponse report = invokeCallbackAndReloadReport(request);

    assertThat(report.getOverallScore()).isEqualByComparingTo("78.00");
    assertThat(report.getRuleEngineShadow().getLlmRawScore()).isEqualByComparingTo("91.00");
    assertThat(report.getRuleEngineShadow().getRuleEngineScore()).isEqualByComparingTo("78.00");
}
```

- [ ] **Step 2: Verify red**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=AiScoringSessionServiceTest test
```

Expected: FAIL because callback still stores old `overallScore` as official score or lacks `ruleEngineMode/trackRuleStatus` contract.

- [ ] **Step 3: Implement minimal authoritative gate**

Add callback decision logic:

```java
private BigDecimal chooseOfficialScore(PipelineCallbackRequest.Result result) {
    if (result == null) {
        return null;
    }
    boolean authoritative = "authoritative".equalsIgnoreCase(result.getRuleEngineMode())
            && "active".equalsIgnoreCase(result.getTrackRuleStatus())
            && result.getRuleEngineScore() != null;
    return authoritative ? result.getRuleEngineScore() : result.getOverallScore();
}
```

Use this helper only at the point where `ai_score_report.overall_score` is written. Keep `llmRawScore`, `ruleEngineScore`, `scoreDiff`, and `diffReasons` in `structuredResultJson`.

- [ ] **Step 4: Verify green**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=AiScoringSessionServiceTest,AiScoreRuleEngineTest test
```

Expected: PASS.

---

### Task 2: Active Boundary Blocks Generated Pilot Tracks

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/RubricResolverService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/RubricResolverServiceTest.java`
- Modify: `ai-scoring/app/services/track_expansion_plan_service.py`
- Modify: `ai-scoring/tests/test_stage8_final_readiness_summary.py`

- [ ] **Step 1: Write failing tests**

Backend test:

```java
@Test
void generatedPilotTrackCannotResolveAsActiveRuleEngineAuthority() {
    assertThatThrownBy(() -> rubricResolverService.resolveActiveRuleEngineConfig("track_26"))
            .hasMessageContaining("activeAllowed=false");
}
```

Python test:

```python
def test_stage8_summary_blocks_authoritative_mode_for_generated_assets():
    plan = load_track_expansion_plan(PLAN_PATH)
    summary = summarize_stage8_final_readiness(plan, RUBRIC_DIR, ADMISSION_DIR, MARKDOWN_DIR)

    assert summary["status"] == "pilot_ready_not_active"
    assert summary["activeReadyCount"] == 0
    assert summary["activeBlockedCount"] == 40
```

- [ ] **Step 2: Verify red**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RubricResolverServiceTest test
python -m pytest ai-scoring/tests/test_stage8_final_readiness_summary.py -q
```

Expected: Java test FAILS until resolver has an explicit active-boundary method.

- [ ] **Step 3: Implement active boundary**

Add a resolver method that refuses generated pilot tracks unless all active gates pass:

```java
public TrackRuleConfig resolveActiveRuleEngineConfig(String trackId) {
    TrackRuleConfig config = findLatestRuleEngineConfig(trackId);
    if (config == null || !"active".equalsIgnoreCase(config.getStatus())) {
        throw new IllegalStateException("track rule is not active");
    }
    if (!Boolean.TRUE.equals(config.getActiveAllowed())) {
        throw new IllegalStateException("track rule activeAllowed=false");
    }
    return config;
}
```

If current entity lacks `activeAllowed`, add it in Task 3 before using this in production code.

- [ ] **Step 4: Verify green**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RubricResolverServiceTest test
python -m pytest ai-scoring/tests/test_stage8_final_readiness_summary.py -q
```

Expected: PASS.

---

### Task 3: Structured Observation Persistence Expansion

**Files:**
- Modify: `backend/src/main/resources/sql/upgrade_ai_scoring_p8_rule_engine.sql`
- Modify: `deploy/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql`
- Modify: `dockerrun/sql/backend-resources/upgrade_ai_scoring_p8_rule_engine.sql`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreObservation.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`

- [ ] **Step 1: Write failing persistence test**

```java
@Test
void storesObservationNameMaxScoreAndFinalScoreForRuleEngineReports() {
    AiScoreStructuredResultRequest.ObservationInput observation = new AiScoreStructuredResultRequest.ObservationInput();
    observation.setObservationCode("TECH_DEMO_VALIDATION");
    observation.setObservationName("技术演示可验证性");
    observation.setMaxScore(new BigDecimal("6.00"));
    observation.setFinalScore(new BigDecimal("4.50"));

    service.saveStructuredResult(sessionId, reportId, requestWith(observation));

    AiScoreObservation saved = observationRepository.findByReportId(reportId).get(0);
    assertThat(saved.getObservationName()).isEqualTo("技术演示可验证性");
    assertThat(saved.getMaxScore()).isEqualByComparingTo("6.00");
    assertThat(saved.getFinalScore()).isEqualByComparingTo("4.50");
}
```

- [ ] **Step 2: Verify red**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=AiScoreStructuredResultServiceTest test
```

Expected: FAIL because table/entity does not persist the full fields.

- [ ] **Step 3: Add migration fields**

Add columns:

```sql
ALTER TABLE ai_score_observation
  ADD COLUMN observation_name VARCHAR(128) DEFAULT NULL COMMENT '观测点名称',
  ADD COLUMN max_score DECIMAL(6,2) DEFAULT NULL COMMENT '观测点满分',
  ADD COLUMN final_score DECIMAL(6,2) DEFAULT NULL COMMENT '规则引擎最终观测点分',
  ADD COLUMN source_type VARCHAR(64) DEFAULT NULL COMMENT '证据来源类型';
```

Use idempotent stored procedure style consistent with existing SQL files.

- [ ] **Step 4: Persist fields**

Map request fields into entity fields in `AiScoreStructuredResultService`.

- [ ] **Step 5: Verify green**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=AiScoreStructuredResultServiceTest,AiScoreStructuredEntityCompileTest test
```

Expected: PASS.

---

### Task 4: Real Raw Sample Admission Manifests

**Files:**
- Create: `ai-scoring/app/evaluation/real_sample_manifest.template.json`
- Create: `ai-scoring/tests/test_real_sample_admission_service.py`
- Create: `ai-scoring/app/services/real_sample_admission_service.py`
- Modify: `ai-scoring/app/services/track_expansion_plan_service.py`
- Modify: `docs/OREP_AI评分规则引擎主导改造执行记录.md`

- [ ] **Step 1: Write failing real-sample gate test**

```python
def test_generated_samples_do_not_satisfy_real_sample_active_gate():
    manifest = {
        "trackId": "26",
        "sourceMode": "synthetic_from_local_markdown",
        "samples": [{"sampleId": f"s{i}", "rawVideoPath": None} for i in range(30)],
    }

    result = validate_real_sample_manifest(manifest)

    assert result["status"] == "not_ready"
    assert "real raw sample sourceMode is required" in result["blockingReasons"]
```

```python
def test_real_sample_manifest_requires_30_samples_and_two_reviewers():
    manifest = {
        "trackId": "26",
        "sourceMode": "real_raw_competition_sample",
        "samples": [
            {
                "sampleId": f"real-{i}",
                "rawVideoPath": f"samples/track_26/real-{i}.mp4",
                "transcriptPath": f"samples/track_26/real-{i}.json",
                "humanScore": 80,
                "reviewers": ["expert-a", "expert-b"],
            }
            for i in range(30)
        ],
    }

    result = validate_real_sample_manifest(manifest)

    assert result["status"] == "ready"
    assert result["sampleCount"] == 30
```

- [ ] **Step 2: Verify red**

Run:

```bash
python -m pytest ai-scoring/tests/test_real_sample_admission_service.py -q
```

Expected: ERROR because service does not exist.

- [ ] **Step 3: Implement manifest validator**

Implement:

```python
def validate_real_sample_manifest(manifest: dict | None) -> dict:
    source = manifest or {}
    samples = source.get("samples") if isinstance(source.get("samples"), list) else []
    reasons = []
    if source.get("sourceMode") != "real_raw_competition_sample":
        reasons.append("real raw sample sourceMode is required")
    if len(samples) < 30:
        reasons.append("at least 30 real samples are required before active")
    for sample in samples:
        if not sample.get("rawVideoPath"):
            reasons.append("each sample must include rawVideoPath")
            break
        if len(sample.get("reviewers") or []) < 2:
            reasons.append("each sample must have at least 2 reviewers")
            break
    return {
        "status": "ready" if not reasons else "not_ready",
        "sampleCount": len(samples),
        "blockingReasons": reasons,
    }
```

- [ ] **Step 4: Verify green**

Run:

```bash
python -m pytest ai-scoring/tests/test_real_sample_admission_service.py -q
```

Expected: PASS.

---

### Task 5: Rule Admission Audit Persistence

**Files:**
- Create: `backend/src/main/resources/sql/create_rule_admission_audit_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/entity/RuleAdmissionAudit.java`
- Create: `backend/src/main/java/com/orep/backend/service/RuleAdmissionAuditService.java`
- Create: `backend/src/test/java/com/orep/backend/service/RuleAdmissionAuditServiceTest.java`

- [ ] **Step 1: Write failing audit service test**

```java
@Test
void rejectsActiveDecisionWithoutTwoHumanReviewersAndReadyQualityReport() {
    RuleAdmissionDecision decision = new RuleAdmissionDecision();
    decision.setTrackId("26");
    decision.setTargetStatus("active");
    decision.setReviewerIds(List.of("expert-a"));
    decision.setQualityStatus("ready");
    decision.setRealSampleStatus("ready");

    RuleAdmissionResult result = service.evaluate(decision);

    assertThat(result.getStatus()).isEqualTo("not_ready");
    assertThat(result.getBlockingReasons()).contains("at least 2 human reviewers are required");
}
```

- [ ] **Step 2: Verify red**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RuleAdmissionAuditServiceTest test
```

Expected: FAIL because audit service/table does not exist.

- [ ] **Step 3: Implement audit table and service**

Minimum table fields:

```sql
CREATE TABLE IF NOT EXISTS rule_admission_audit (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  track_id VARCHAR(64) NOT NULL,
  rule_version VARCHAR(64) NOT NULL,
  target_status VARCHAR(32) NOT NULL,
  decision_status VARCHAR(32) NOT NULL,
  reviewer_ids_json TEXT NOT NULL,
  quality_status VARCHAR(32) NOT NULL,
  real_sample_status VARCHAR(32) NOT NULL,
  blocking_reasons_json TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- [ ] **Step 4: Verify green**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RuleAdmissionAuditServiceTest test
```

Expected: PASS.

---

### Task 6: Gray Release, Rollback, And Monitoring

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Create: `backend/src/main/java/com/orep/backend/service/RuleEngineReleaseGuardService.java`
- Create: `backend/src/test/java/com/orep/backend/service/RuleEngineReleaseGuardServiceTest.java`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportOverview.vue`
- Modify: `frontend/user/src/utils/aiScoreRuleEngineReport.js`

- [ ] **Step 1: Write failing guard test**

```java
@Test
void fallsBackToShadowWhenRuleEngineFailsDuringGrayRelease() {
    RuleEngineReleaseDecision decision = service.decide(
            "track_26",
            "gray",
            RuleEngineHealth.failed("calculation exception")
    );

    assertThat(decision.getOfficialScoreMode()).isEqualTo("llm_fallback");
    assertThat(decision.getUserVisibleWarning()).contains("规则引擎复核中");
}
```

- [ ] **Step 2: Verify red**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RuleEngineReleaseGuardServiceTest test
```

Expected: FAIL because guard service does not exist.

- [ ] **Step 3: Implement release modes**

Modes:

- `shadow`: old LLM official, rule engine displayed as comparison.
- `gray`: rule engine official only when health is ready and track audit is active.
- `authoritative`: rule engine official by default; fallback only on configured rollback.
- `disabled`: do not run rule engine.

- [ ] **Step 4: Frontend display rule engine mode**

`aiScoreRuleEngineReport.js` should expose:

```js
{
  officialScoreMode: 'shadow' | 'gray' | 'authoritative' | 'llm_fallback',
  warningText: ''
}
```

Overview page should show a compact status text without changing the existing visual style.

- [ ] **Step 5: Verify green**

Run:

```bash
/opt/homebrew/bin/mvn -Dtest=RuleEngineReleaseGuardServiceTest,AiScoringSessionServiceTest test
cd frontend/user && node --test src/utils/aiScoreRuleEngineReport.test.js && npm run build
```

Expected: PASS.

---

## Final Verification Pack

Run these before claiming the next milestone complete:

```bash
/opt/homebrew/bin/mvn test
python -m pytest ai-scoring/tests/test_competition_calibration_service.py ai-scoring/tests/test_evidence_extraction_service.py ai-scoring/tests/test_track_rule_pilot_assets.py ai-scoring/tests/test_ai_jury_services.py ai-scoring/tests/test_stability_evaluation_service.py ai-scoring/tests/test_track_expansion_plan_service.py ai-scoring/tests/test_stage8_final_readiness_summary.py ai-scoring/tests/test_real_sample_admission_service.py -q
cd frontend/user && node --test src/utils/aiScoreRuleEngineReport.test.js src/utils/aiScoreTrainingTasks.test.js src/utils/aiScoreFrameMatching.test.js && npm run build
```

Expected:

- Maven backend tests pass.
- Python scoring tests pass.
- Frontend utility tests pass.
- Frontend build passes.
- No `pilot_generated`赛道可进入 active unless real sample manifest, quality report, audit table, and release guard all pass.

## Milestone Decision Gates

- **M9A：权威入口完成**：Java callback 能按赛道状态决定正式分来源。
- **M9B：结构化落库完成**：15观测点名称、满分、最终分可持久化和展示。
- **M9C：真实样本准入完成**：生成样本不能 active，真实原始样本30条以上且2名复核者才可 active。
- **M9D：审计后台完成**：active 决策有审计记录和阻断理由。
- **M9E：灰度上线完成**：shadow/gray/authoritative/disabled 四种模式可控，可回滚，可展示。

## Self-Review

- Spec coverage: 覆盖方案中的规则引擎主导、上线准入、真实样本、人工复核、灰度上线与回滚要求。
- Placeholder scan: 无 TBD/TODO/implement later。
- Type consistency: 计划中新函数名保持一致：`summarize_stage8_final_readiness`、`validate_real_sample_manifest`、`RuleEngineReleaseGuardService`。
