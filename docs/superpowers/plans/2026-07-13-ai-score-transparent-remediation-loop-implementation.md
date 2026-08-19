# AI 评分全量公开、分轮执行与重新验证实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“少量行动计划”升级为可对账的完整失分账本、100% 覆盖的整改任务队列和必须复评才能改分的多轮验证闭环，同时继续只向用户展示一个 AI 分数。

**Architecture:** Python 是评分事实与提分情景的唯一生产者，先把规则引擎已有的失分账本规范化，再生成任务并执行覆盖校验；Java 保存报告快照和跨轮任务状态，对外发布解析后的 v3 报告契约；Vue 只消费正式契约，结果页展示前三项、待办页展示全量、依据页展示全部失分。多轮复评依靠稳定的 `lossKey` 和 `rootCauseKey` 比较新旧报告，用户勾选完成不会直接改分。

**Tech Stack:** Python 3.11+/pytest/FastAPI，Java 21/Spring Boot 3.2/MyBatis-Plus/MySQL，Vue 3/Vite/Node test/Playwright。

---

## 0. 执行边界与验收口径

本计划对应已批准的设计文档：
`docs/superpowers/specs/2026-07-13-ai-score-transparent-remediation-loop-design.md`。

这是一条前后依赖的交付链，不拆成相互独立的子项目：

1. Python 先证明“失分合计 = 100 - 当前分”。
2. Python 再证明“所有失分账目均被整改任务覆盖”。
3. Java 只在上述两项成立时把报告标记为完整待办组合。
4. 前端只在 `coverageSummary.status=complete` 时使用“全部待办”文案。
5. 任务完成只改变任务状态；只有新一轮评分才能改变 AI 分数和验证状态。

工作区 `/Users/liuyixing/项目/OREP` 当前不是 Git 仓库，因此计划中的每个“检查点”以测试结果和变更清单代替提交；不得为了执行本计划临时初始化 Git。

## 1. 文件结构锁定

### Python 新增文件

- `ai-scoring/app/services/scoring/loss_ledger_service.py`：把规则引擎账目补齐稳定 ID、维度、规则预算键和指纹。
- `ai-scoring/app/services/scoring/remediation_planner.py`：把行动计划映射到失分账目，并为未覆盖账目生成确定性兜底任务。
- `ai-scoring/app/services/scoring/coverage_validator.py`：校验分数对账、账目覆盖和重复预算占用。
- `ai-scoring/tests/test_loss_ledger_service.py`：失分账本规范化单测。
- `ai-scoring/tests/test_remediation_planner.py`：任务映射、合并与兜底单测。
- `ai-scoring/tests/test_coverage_validator.py`：完整/不完整发布门槛单测。
- `ai-scoring/tests/fixtures/session_26_scoring_snapshot.json`：脱敏后的会话 26 规则输入与预期 50.5 分差基线。

### Python 修改文件

- `ai-scoring/app/services/pipeline_payloads.py`：把赛道规则中的观测点定义、必需信息、证据要求和训练模板带入评分事实。
- `ai-scoring/app/services/scoring/rule_executor.py`：在源头补齐账目所需的观测点与规则元数据，不改变现有分数计算。
- `ai-scoring/app/services/scoring/score_impact_service.py`：以 `coveredLossIds` 而非文本相似度计算任务提分区间和组合预测。
- `ai-scoring/app/services/session_pipeline_service.py`：组装 v3 回调字段并执行发布门槛。
- `ai-scoring/tests/test_score_impact_service.py`：覆盖预算去重与组合重算。
- `ai-scoring/tests/test_session_authoritative_callback.py`：验证 v3 回调完整性。

### Java 新增文件

- `backend/src/main/resources/sql/migrate_ai_score_report_transparent_remediation_v3.sql`：报告快照列和三张跨轮表。
- `backend/src/main/java/com/orep/backend/entity/AiScoreRemediationTask.java`：跨轮任务实体。
- `backend/src/main/java/com/orep/backend/entity/AiScoreTaskLossLink.java`：任务与报告失分账目的关联实体。
- `backend/src/main/java/com/orep/backend/entity/AiScoreTaskVerification.java`：复评验收记录实体。
- `backend/src/main/java/com/orep/backend/mapper/AiScoreRemediationTaskMapper.java`。
- `backend/src/main/java/com/orep/backend/mapper/AiScoreTaskLossLinkMapper.java`。
- `backend/src/main/java/com/orep/backend/mapper/AiScoreTaskVerificationMapper.java`。
- `backend/src/main/java/com/orep/backend/service/AiScoreRemediationService.java`：快照入库、实时状态覆盖和跨轮匹配。
- `backend/src/test/java/com/orep/backend/service/AiScoreRemediationServiceTest.java`。

### Java 修改文件

- `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`：接收 v3 JSON 与契约版本。
- `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`：保存失分账本、覆盖摘要和契约版本。
- `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`：返回解析对象、实时任务和验收记录。
- `backend/src/main/java/com/orep/backend/service/AiScoreCallbackReconciliationService.java`：增加账本恒等式和覆盖门槛复核。
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`：事务内保存 v3 快照和标准化任务。
- `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`：增加任务状态与提交复评端点。
- `backend/src/test/java/com/orep/backend/service/AiScoreCallbackReconciliationServiceTest.java`。
- `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`。
- `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`。
- `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`。

### 前端新增文件

- `frontend/user/src/utils/aiScoreLossLedger.js`：解析和分组完整失分账本。
- `frontend/user/src/utils/aiScoreLossLedger.test.js`。
- `frontend/user/src/utils/aiScoreCoverage.js`：规范化覆盖摘要和发布状态。
- `frontend/user/src/utils/aiScoreCoverage.test.js`。
- `frontend/user/src/utils/aiScoreVerification.js`：多轮验证状态文案。
- `frontend/user/src/utils/aiScoreVerification.test.js`。

### 前端修改文件

- `frontend/user/src/composables/useAiScoreReport.js`：正式 v3 数据源和兼容降级。
- `frontend/user/src/utils/aiScoreTodosPresentation.js`：改用服务端正式任务，不再按标题猜测合并。
- `frontend/user/src/utils/aiScoreTodosPresentation.test.js`。
- `frontend/user/src/utils/aiScoreProjection.js` 与测试：加入完整组合预测语义。
- `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`：一个分数、完整差距、组合预测、前三项。
- `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`：全量队列、覆盖统计、执行状态。
- `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue`：完整失分账本与证据锚点。
- `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue`：顶部待办数使用去重后的完整队列。
- `frontend/user/tests/ai-score-hardening.spec.js`：三页端到端契约。

### v3 字段冻结

实现期间统一使用 camelCase，数据库列使用 snake_case；不得在任一层引入同义字段。核心对象固定为：

```json
{
  "lossItem": {
    "lossId": "loss-fingerprint-cause",
    "lossKey": "ruleHash:causeCode",
    "causeCode": "O01:performance_gap",
    "observationCode": "O01",
    "observationName": "操作规范性",
    "dimensionCode": "skill_level",
    "lossType": "performance_gap",
    "points": 4.0,
    "reason": "本轮表现未达到观测点要求",
    "evidenceAnchorIds": [],
    "scoreBudgetKey": "O01:performance_score",
    "actionability": "actionable",
    "ruleHash": "sha256:rule",
    "scoringFingerprint": "sha256:fingerprint"
  },
  "remediationTask": {
    "taskId": "task-root-action",
    "rootCauseKey": "root-cause",
    "priority": "P0",
    "executionGroup": "current",
    "title": "补齐操作证据并复演",
    "problem": "观测点尚未达到要求",
    "method": "按规则要求补齐材料并完成复演",
    "coveredLossIds": ["loss-fingerprint-cause"],
    "observationCodes": ["O01"],
    "coveredGapPoints": 4.0,
    "minimumAcceptance": {
      "summary": "必需信息齐全且证据可定位",
      "requiredEvidence": ["过程记录"]
    },
    "fullScoreCriteria": {
      "summary": "完整满足赛道观测点定义并形成证据闭环",
      "ruleReference": "O01"
    },
    "scoreImpact": {
      "scoreLinkStatus": "linked",
      "impactType": "performance_improvement",
      "lower": 1.0,
      "upper": 2.0,
      "scoreBudgetKeys": ["O01:performance_score"]
    },
    "dependencies": [],
    "status": "not_started"
  }
}
```

`minimumAcceptance.summary` 和 `fullScoreCriteria.summary` 是唯一文字字段名；前端、Java DTO、JSON 快照和测试全部沿用这两个名称。

## 2. 分阶段实施总览

| 阶段 | 结果 | 发布条件 |
|---|---|---|
| A | Python 产生完整可对账账本与 100% 覆盖任务 | Python 新增单测与既有评分回归全绿 |
| B | Java 保存 v3 快照、标准化任务并发布正式 API | Java 服务和控制器测试全绿，旧报告仍可读 |
| C | 用户端显示完整差距、前三优先项和全部待办 | Node 单测、构建与 Playwright 全绿 |
| D | 任务提交、复评验证、部分通过和回退 | 新旧报告匹配测试与会话级集成测试全绿 |
| E | 会话 26 回放、灰度观测与商业交付验收 | 50.5 分差、账目合计、任务覆盖率三者可核对 |

---

### Task 1: 固化会话 26 的回归事实

**Files:**
- Create: `ai-scoring/tests/fixtures/session_26_scoring_snapshot.json`
- Create: `ai-scoring/tests/test_loss_ledger_service.py`

- [x] **Step 1: 写会话 26 脱敏夹具**

夹具只保留规则计算需要的 `observations`、`deductions`、`ruleHash`、`scoringFingerprint`，并加入以下预期值：

```json
{
  "expected": {
    "currentScore": 49.5,
    "fullGap": 50.5,
    "observationCount": 15,
    "lossItemCount": 19,
    "lossTypeCounts": {
      "performance_gap": 14,
      "evidence_limited": 4,
      "hard_violation": 1
    }
  }
}
```

- [x] **Step 2: 写失败测试证明基线可重算**

```python
def test_session_26_fixture_reconciles_to_full_gap():
    fixture = load_fixture("session_26_scoring_snapshot.json")
    result = execute_rule_score(fixture["observations"], fixture["deductions"])
    assert result["finalScore"] == 49.5
    assert result["reconciliation"]["totalLoss"] == 50.5
    assert len(result["lossLedger"]) == 19
```

- [x] **Step 3: 运行测试确认夹具真实**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_loss_ledger_service.py -q`

Expected: 基线测试 PASS；若数据库导出的事实不符合 15/19/50.5，停止后续实现并修正夹具来源，不能修改期望值迁就代码。

- [x] **Step 4: 记录检查点**

记录夹具来源会话、规则哈希、指纹和测试输出；不包含转录全文、姓名或视频路径。

---

### Task 2: 规范化不可变失分账本

**Files:**
- Create: `ai-scoring/app/services/scoring/loss_ledger_service.py`
- Modify: `ai-scoring/app/services/pipeline_payloads.py`
- Modify: `ai-scoring/app/services/scoring/rule_executor.py`
- Modify: `ai-scoring/tests/test_loss_ledger_service.py`

- [x] **Step 1: 写稳定标识和字段完整性失败测试**

```python
def test_normalized_loss_items_have_stable_identity_and_budget():
    ledger = normalize_loss_ledger(
        rule_result=rule_result,
        rule_hash="rh-1",
        scoring_fingerprint="fp-1",
    )
    assert ledger[0]["lossId"].startswith("loss-")
    assert ledger[0]["lossKey"] == "rh-1:O1:performance_gap"
    assert ledger[0]["scoreBudgetKey"] == "O1:performance_score"
    assert ledger[0]["dimensionCode"] == "skill"
    assert ledger[0]["ruleHash"] == "rh-1"
    assert ledger[0]["scoringFingerprint"] == "fp-1"
```

- [x] **Step 2: 运行单测确认失败原因是服务尚不存在**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_loss_ledger_service.py -q`

Expected: FAIL，提示无法导入 `normalize_loss_ledger`。

- [x] **Step 3: 实现账本规范化入口**

```python
def normalize_loss_ledger(*, rule_result, rule_hash, scoring_fingerprint):
    observations = {
        str(row["observationCode"]): row
        for row in rule_result.get("observations", [])
    }
    normalized = []
    for index, row in enumerate(rule_result.get("lossLedger", [])):
        code = str(row.get("observationCode") or "unassigned")
        loss_type = str(row.get("lossType") or "unresolved_gap")
        cause = str(row.get("causeCode") or f"{code}:{loss_type}")
        observation = observations.get(code, {})
        normalized.append({
            **row,
            "lossId": stable_loss_id(scoring_fingerprint, cause, index),
            "lossKey": f"{rule_hash}:{cause}",
            "causeCode": cause,
            "observationCode": code,
            "dimensionCode": observation.get("dimensionCode") or "unassigned",
            "scoreBudgetKey": budget_key(code, loss_type, row),
            "actionability": "actionable",
            "ruleHash": rule_hash,
            "scoringFingerprint": scoring_fingerprint,
        })
    return normalized
```

`lossId` 对报告不可变，种子必须包含指纹；`lossKey` 跨轮稳定，不能包含本轮分数、数组下标或证据 ID。硬违规 `scoreBudgetKey` 使用 `penaltyRuleCode`，避免与表现差距共用预算。

- [x] **Step 4: 把赛道规则元数据带入观测点**

在 `pipeline_payloads.py::_build_shadow_observations` 从 `observation_rules` 复制以下只读字段：

```python
observation.update({
    "observationName": rule.get("observationName"),
    "dimensionName": rule.get("dimensionName"),
    "trackDefinition": rule.get("trackDefinition"),
    "requiredInfo": list(rule.get("requiredInfo") or []),
    "acceptableEvidence": list(rule.get("acceptableEvidence") or []),
    "trainingTaskTemplate": rule.get("trainingTaskTemplate"),
})
```

`minimumAcceptance` 从 `requiredInfo` 和 `acceptableEvidence` 构造，`fullScoreCriteria.summary` 使用 `trackDefinition`；不存在时使用观测点名称和真实评分理由降级，不能让大模型编造规则。

- [x] **Step 5: 补齐规则引擎账目源字段**

在 `rule_executor.py` 的三类账目中保留 `observationName`、`dimensionCode`、`consumedBy`；不得改变 `finalScore`、`totalLoss` 或当前单次归因算法。

- [x] **Step 6: 增加顺序变化稳定性测试**

```python
def test_loss_key_is_stable_when_evidence_anchor_order_changes():
    first = normalize_loss_ledger(rule_result=first_result, rule_hash="rh", scoring_fingerprint="fp-a")
    second = normalize_loss_ledger(rule_result=second_result, rule_hash="rh", scoring_fingerprint="fp-b")
    assert {x["lossKey"] for x in first} == {x["lossKey"] for x in second}
    assert {x["lossId"] for x in first} != {x["lossId"] for x in second}
```

- [x] **Step 7: 运行评分回归**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_loss_ledger_service.py tests/test_authoritative_rule_executor.py tests/test_pipeline_authoritative_payload.py -q`

Expected: 全部 PASS，且会话 26 仍是 49.5 分、19 条账目、50.5 分差。

---

### Task 3: 生成完整整改地图并禁止漏项

**Files:**
- Create: `ai-scoring/app/services/scoring/remediation_planner.py`
- Create: `ai-scoring/app/services/scoring/coverage_validator.py`
- Create: `ai-scoring/tests/test_remediation_planner.py`
- Create: `ai-scoring/tests/test_coverage_validator.py`

- [x] **Step 1: 写“6 条计划不能冒充全部待办”的失败测试**

```python
def test_uncovered_losses_receive_deterministic_fallback_tasks():
    tasks = build_complete_remediation_map(
        action_plan=six_model_tasks,
        loss_ledger=nineteen_loss_items,
    )
    covered = {loss_id for task in tasks for loss_id in task["coveredLossIds"]}
    assert covered == {row["lossId"] for row in nineteen_loss_items}
    assert len(tasks) >= 6
```

- [x] **Step 2: 写合并约束失败测试**

```python
def test_tasks_merge_only_when_root_cause_and_action_match():
    tasks = build_complete_remediation_map(action_plan=plans, loss_ledger=losses)
    assert task_for("O1:performance_gap")["taskId"] != task_for("O1:evidence_limited")["taskId"]
    assert task_for("O2:performance_gap")["taskId"] == task_for("O3:performance_gap")["taskId"]
```

测试数据中 O2/O3 明确共享同一个 `rootCauseKey` 和同一整改动作；O1 的表现与证据是两个不同验收动作。标题相似不得作为合并依据。

- [x] **Step 3: 实现任务规范化和确定性兜底**

```python
def build_complete_remediation_map(*, action_plan, loss_ledger):
    tasks = normalize_model_tasks(action_plan, loss_ledger)
    covered = {loss_id for task in tasks for loss_id in task["coveredLossIds"]}
    for loss in loss_ledger:
        if loss["lossId"] in covered:
            continue
        tasks.append(fallback_task_for(loss))
    return merge_by_root_cause_and_action(tasks)
```

兜底任务必须使用该账目的真实 `reason`、观测点、证据锚点、最低验收和满分标准；若规则没有给出具体改法，使用“补齐并复核该观测点要求”这种事实性动作，不能生成不存在的承诺或训练脚本。

- [x] **Step 4: 实现覆盖校验器**

```python
def validate_remediation_coverage(*, current_score, loss_ledger, tasks, rule_hash, scoring_fingerprint):
    full_gap = round1(100.0 - float(current_score))
    ledger_points = round1(sum(float(row["points"]) for row in loss_ledger))
    covered_ids = {loss_id for task in tasks for loss_id in task.get("coveredLossIds", [])}
    all_ids = {row["lossId"] for row in loss_ledger}
    uncovered = sorted(all_ids - covered_ids)
    error = round1(ledger_points - full_gap)
    status = "complete" if abs(error) <= 0.1 and not uncovered else "incomplete"
    return {
        "currentScore": round1(current_score),
        "fullGap": full_gap,
        "ledgerPoints": ledger_points,
        "lossItemCount": len(loss_ledger),
        "remediationTaskCount": len(tasks),
        "coveredLossItemCount": len(all_ids & covered_ids),
        "coveredGapPoints": round1(sum(row["points"] for row in loss_ledger if row["lossId"] in covered_ids)),
        "coverageRate": round4(len(all_ids & covered_ids) / len(all_ids)) if all_ids else 1.0,
        "uncoveredLossIds": uncovered,
        "reconciliationError": error,
        "status": status,
        "calculationVersion": "remediation-coverage-v1",
        "ruleHash": rule_hash,
        "scoringFingerprint": scoring_fingerprint,
    }
```

- [x] **Step 5: 校验重复预算不是重复覆盖**

同一 `scoreBudgetKey` 可被多个任务引用用于说明依赖，但只能由组合预测消费一次。`CoverageSummary.unresolvedDuplicateBudgetKeys` 仅记录无法判定主任务的预算冲突；存在冲突时 `status=incomplete`。

- [x] **Step 6: 运行新增测试**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_remediation_planner.py tests/test_coverage_validator.py -q`

Expected: 全部 PASS；任意正分账目没有任务时状态必须是 `incomplete`。

---

### Task 4: 用正式账目计算任务分值和组合预测

**Files:**
- Modify: `ai-scoring/app/services/scoring/score_impact_service.py`
- Modify: `ai-scoring/tests/test_score_impact_service.py`

- [x] **Step 1: 写“覆盖差距不等于承诺提分”测试**

```python
def test_covered_gap_and_score_impact_are_distinct():
    tasks, projection = build_score_impact_projection(
        tasks=[task_covering_loss_8_points],
        observations=observations,
        deductions=deductions,
        loss_ledger=loss_ledger,
    )
    assert tasks[0]["coveredGapPoints"] == 8.0
    assert tasks[0]["scoreImpact"]["upper"] < 8.0
    assert tasks[0]["scoreImpact"]["scoreLinkStatus"] == "linked"
```

- [x] **Step 2: 写组合预算去重测试**

```python
def test_portfolio_prediction_consumes_shared_budget_once():
    tasks, projection = build_score_impact_projection(...)
    assert projection["predictedGainUpper"] != sum(t["scoreImpact"]["upper"] for t in tasks)
    assert projection["scenarioScope"] == "all_known_tasks_minimum_acceptance"
```

- [x] **Step 3: 将函数入口改为显式账目映射**

```python
def build_score_impact_projection(
    action_plan,
    observations,
    deductions,
    *,
    loss_ledger,
    rule_hash=None,
    scoring_fingerprint=None,
):
    ...
```

新 v3 任务只允许通过 `coveredLossIds` 和账目中的 `observationCode`/`penaltyRuleCode` 建立分值关联。保留 `_best_text_observation` 仅用于读取旧报告，不得用于生成 v3 完整报告。

- [x] **Step 4: 为任务写入两类验收标准**

每个正式任务必须同时包含：

```python
task["minimumAcceptance"] = {
    "summary": minimum_acceptance_text,
    "requiredEvidence": evidence_requirements,
}
task["fullScoreCriteria"] = {
    "summary": full_score_rule_text,
    "ruleReference": rule_reference,
}
```

`scoreImpact` 只模拟最低验收通过后的保守区间；不能把 `coveredGapPoints` 复制为 `upper`。

- [x] **Step 5: 扩充组合预测契约**

```python
projection.update({
    "scenarioScope": "all_known_tasks_minimum_acceptance",
    "coveredGapPoints": coverage_summary["coveredGapPoints"],
    "coverageRate": coverage_summary["coverageRate"],
})
```

- [x] **Step 6: 运行分值测试和全量 Python 回归**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_score_impact_service.py tests/test_remediation_planner.py tests/test_coverage_validator.py -q`

Expected: 全部 PASS。

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_authoritative_rule_executor.py tests/test_pipeline_authoritative_payload.py tests/test_session_authoritative_callback.py tests/test_backend_callback_client.py -q`

Expected: 全部 PASS，旧回调可靠性不退化。

---

### Task 5: 发布 Python → Java v3 回调契约

**Files:**
- Modify: `ai-scoring/app/services/session_pipeline_service.py`
- Modify: `ai-scoring/tests/test_session_authoritative_callback.py`

- [x] **Step 1: 写完整回调失败测试**

```python
def test_v3_callback_contains_reconciled_ledger_tasks_and_coverage(build_payload):
    final_result = build_payload(pipeline_result)["finalResult"]
    ledger = json.loads(final_result["lossLedgerJson"])
    tasks = json.loads(final_result["actionPlanJson"])
    coverage = json.loads(final_result["coverageSummaryJson"])
    assert final_result["contractVersion"] == "ai-score-report-v3"
    assert round(sum(x["points"] for x in ledger), 1) == round(100 - final_result["overallScore"], 1)
    assert coverage["coverageRate"] == 1.0
    assert coverage["remediationTaskCount"] == len(tasks)
```

- [x] **Step 2: 在 `_build_final_result` 中按固定顺序组装**

```python
loss_ledger = normalize_loss_ledger(
    rule_result=shadow_payload,
    rule_hash=rule_hash,
    scoring_fingerprint=scoring_fingerprint,
)
action_plan = build_complete_remediation_map(
    action_plan=_normalize_action_plan_for_callback(ai_score, evidence_extraction),
    loss_ledger=loss_ledger,
)
coverage = validate_remediation_coverage(...)
action_plan, score_projection = build_score_impact_projection(
    action_plan,
    observations,
    deductions,
    loss_ledger=loss_ledger,
    rule_hash=rule_hash,
    scoring_fingerprint=scoring_fingerprint,
)
```

- [x] **Step 3: 写入 v3 字段**

```python
final_result.update({
    "contractVersion": "ai-score-report-v3",
    "lossLedgerJson": json.dumps(loss_ledger, ensure_ascii=False),
    "coverageSummaryJson": json.dumps(coverage, ensure_ascii=False),
    "actionPlanJson": json.dumps(action_plan, ensure_ascii=False),
    "scoreProjectionJson": json.dumps(score_projection, ensure_ascii=False),
})
```

- [x] **Step 4: 实施发布门槛**

若结构化评分存在但 `coverage.status != complete`，完成回调仍可保存评分事实，但必须写：

```python
final_result["todoPortfolioStatus"] = "incomplete"
final_result["publishCompleteTodoPortfolio"] = False
```

不得将会话改成评分失败，也不得丢失报告；Java/前端显示“整改清单生成不完整，已保留评分事实”。

- [x] **Step 5: 运行回调测试**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_session_authoritative_callback.py tests/test_backend_callback_client.py -q`

Expected: 全部 PASS；回调 JSON 可被标准 `json.loads` 完整解析。

---

### Task 6: Java 接收、复核并保存 v3 报告快照

**Files:**
- Create: `backend/src/main/resources/sql/migrate_ai_score_report_transparent_remediation_v3.sql`
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreCallbackReconciliationService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreCallbackReconciliationServiceTest.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`

- [x] **Step 1: 写 DTO 与持久化失败测试**

```java
@Test
void completedV3CallbackPersistsLedgerCoverageAndContractVersion() {
    PipelineFinalResult result = v3Result("49.5", "50.5", "complete");
    service.processPipelineCallback(completedCallback(26L, result));
    AiScoreReport saved = reportCaptor.getValue();
    assertThat(saved.getContractVersion()).isEqualTo("ai-score-report-v3");
    assertThat(saved.getLossLedgerJson()).contains("performance_gap");
    assertThat(saved.getCoverageSummaryJson()).contains("\"coverageRate\":1.0");
}
```

- [x] **Step 2: 扩充 DTO 与报告实体**

在 `PipelineFinalResult` 和 `AiScoreReport` 中新增同名字段：

```java
private String lossLedgerJson;
private String coverageSummaryJson;
private String contractVersion;
private String todoPortfolioStatus;
```

- [x] **Step 3: 编写幂等迁移**

迁移新增：

```sql
ALTER TABLE ai_score_report
  ADD COLUMN loss_ledger_json LONGTEXT NULL COMMENT '不可变失分账本快照',
  ADD COLUMN coverage_summary_json LONGTEXT NULL COMMENT '整改覆盖摘要',
  ADD COLUMN contract_version VARCHAR(64) NULL COMMENT '报告数据契约版本',
  ADD COLUMN todo_portfolio_status VARCHAR(32) NULL COMMENT 'complete/incomplete';
```

实际脚本沿用现有 `information_schema` + `PREPARE` 写法，使重复执行安全。

- [x] **Step 4: 增加 Java 二次对账**

```java
BigDecimal fullGap = HUNDRED.subtract(result.getOverallScore());
BigDecimal ledgerPoints = sumPoints(readList(result.getLossLedgerJson()));
if (fullGap.subtract(ledgerPoints).abs().compareTo(new BigDecimal("0.1")) > 0) {
    throw new IllegalArgumentException("loss ledger does not reconcile with official score");
}
```

当 `contractVersion=ai-score-report-v3` 时，还必须检查：所有 `lossId` 唯一、所有 `coveredLossIds` 存在、`coverageRate=1.0` 才能写 `todoPortfolioStatus=complete`。旧契约跳过 v3 检查，保持可读。

- [x] **Step 5: 在同一事务保存快照**

在 `processPipelineCallback` 已有 report upsert 中加入四个字段 setter；v3 校验失败沿用 `calculation_failed` 终态，不得先写半份任务再失败。

- [x] **Step 6: 运行 Java 定向测试**

Run: `cd backend && mvn -Dtest=AiScoreCallbackReconciliationServiceTest,AiScoringSessionServiceTest test`

Expected: BUILD SUCCESS；旧 completed 回调、重复 completed 回调和终态保护测试继续通过。

---

### Task 7: 建立跨轮任务、账目链接和验收记录

**Files:**
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreRemediationTask.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreTaskLossLink.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreTaskVerification.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreRemediationTaskMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreTaskLossLinkMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreTaskVerificationMapper.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreRemediationService.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreRemediationServiceTest.java`
- Modify: `backend/src/main/resources/sql/migrate_ai_score_report_transparent_remediation_v3.sql`

- [x] **Step 1: 写快照落标准表的失败测试**

```java
@Test
void upsertSnapshotKeepsOneTaskAndManyLossLinks() {
    remediationService.persistSnapshot(projectId, reportId, tasksJson, ledgerJson);
    assertThat(taskMapper.selectList(null)).hasSize(1);
    assertThat(linkMapper.selectList(null)).extracting(AiScoreTaskLossLink::getLossKey)
        .containsExactlyInAnyOrder("rh:O1:performance_gap", "rh:O2:performance_gap");
}
```

- [x] **Step 2: 完成三张表迁移**

```sql
CREATE TABLE ai_score_remediation_task (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  project_scope_key VARCHAR(128) NOT NULL,
  task_key VARCHAR(128) NOT NULL,
  root_cause_key VARCHAR(191) NOT NULL,
  title VARCHAR(500) NOT NULL,
  task_json LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'not_started',
  source_report_id BIGINT NOT NULL,
  latest_report_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_project_task (project_scope_key, task_key)
);
```

`ai_score_task_loss_link` 唯一键为 `(report_id, task_id, loss_key)`；`ai_score_task_verification` 唯一键为 `(task_id, report_id)`。所有表包含 `created_at/updated_at`，链接表还保存 `loss_id`、`points`、`observation_code`。

- [x] **Step 3: 实现快照入库**

```java
@Transactional
public void persistSnapshot(String projectScopeKey, Long reportId, List<Map<String, Object>> tasks,
                            List<Map<String, Object>> ledger) {
    Map<String, Map<String, Object>> losses = indexBy(ledger, "lossId");
    for (Map<String, Object> task : tasks) {
        AiScoreRemediationTask saved = upsertTask(projectScopeKey, reportId, task);
        replaceLinks(reportId, saved.getId(), task, losses);
    }
}
```

快照 `actionPlanJson` 永不被用户状态覆盖；实时状态只保存在标准表，并在查询 API 时叠加。

- [x] **Step 4: 写重放幂等测试**

同一 reportId 的完成回调重放两次，任务行数和链接行数不增加；用户已进入 `in_progress` 的状态不能被快照默认 `not_started` 覆盖。

- [x] **Step 5: 接入完成回调事务**

`AiScoringSessionService.processPipelineCallback` 保存 report 后调用 `remediationService.persistSnapshot(...)`，任何标准表失败都回滚本次 v3 报告写入。

- [x] **Step 6: 运行服务测试**

Run: `cd backend && mvn -Dtest=AiScoreRemediationServiceTest,AiScoringSessionServiceTest test`

Expected: BUILD SUCCESS。

---

### Task 8: 发布正式报告 API 和任务状态 API

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreRemediationService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`

- [x] **Step 1: 写报告响应失败测试**

```java
@Test
void reportApiReturnsParsedV3FactsAndLiveTaskOverlay() {
    AiScoreReportUserResponse response = service.reportBySession(26L);
    assertThat(response.getLossLedger()).hasSize(19);
    assertThat(response.getCoverageSummary().get("status")).isEqualTo("complete");
    assertThat(response.getRemediationTasks()).isNotEmpty();
    assertThat(response.getRemediationTasks().get(0).get("status")).isEqualTo("in_progress");
}
```

- [x] **Step 2: 扩展用户响应**

```java
private String lossLedgerJson;
private List<Map<String, Object>> lossLedger;
private String coverageSummaryJson;
private Map<String, Object> coverageSummary;
private List<Map<String, Object>> remediationTasks;
private List<Map<String, Object>> taskVerifications;
private String todoPortfolioStatus;
private String contractVersion;
```

- [x] **Step 3: 实现只读响应叠加**

`toReportResponse` 先解析不可变快照，再以 `taskId/taskKey` 叠加标准表的 `status`、`submittedAt`、`latestVerification`。任何解析失败返回空对象和 `todoPortfolioStatus=incomplete`，不能伪造完整率。

- [x] **Step 4: 增加任务状态端点**

```java
@PatchMapping("/reports/{reportId}/remediation-tasks/{taskId}/status")
public Result<Map<String, Object>> updateTaskStatus(
        @PathVariable Long reportId,
        @PathVariable Long taskId,
        @RequestBody TaskStatusRequest request) { ... }
```

只允许：`not_started -> in_progress -> submitted -> awaiting_rerun`；允许 `in_progress -> not_started`。`verified/partial/failed/not_observable/regressed/superseded` 只能由复评服务写入。

- [x] **Step 5: 写非法跳转和越权测试**

验证用户不能直接把任务设为 `verified`，不能修改其他项目任务，不能通过状态端点改变报告 `overallScore`。

- [x] **Step 6: 运行 API 测试和 Java 全量测试**

Run: `cd backend && mvn -Dtest=AiScoringSessionReportDetailTest,AiScoreSessionControllerTest,AiScoreUserApiHardeningTest test`

Expected: BUILD SUCCESS。

Run: `cd backend && mvn test`

Expected: BUILD SUCCESS。

---

### Task 9: 前端建立 v3 事实模型并移除标题猜测

**Files:**
- Create: `frontend/user/src/utils/aiScoreLossLedger.js`
- Create: `frontend/user/src/utils/aiScoreLossLedger.test.js`
- Create: `frontend/user/src/utils/aiScoreCoverage.js`
- Create: `frontend/user/src/utils/aiScoreCoverage.test.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.test.js`
- Modify: `frontend/user/src/utils/aiScoreProjection.js`
- Modify: `frontend/user/src/utils/aiScoreProjection.test.js`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`

- [x] **Step 1: 写解析与不完整状态测试**

```javascript
test('normalizes complete v3 coverage without inventing counts', () => {
  const coverage = normalizeCoverage('{"lossItemCount":19,"remediationTaskCount":11,"coverageRate":1,"status":"complete"}')
  assert.equal(coverage.lossItemCount, 19)
  assert.equal(coverage.remediationTaskCount, 11)
  assert.equal(coverage.canClaimCompleteTodos, true)
})

test('never calls incomplete portfolio complete', () => {
  const coverage = normalizeCoverage({ coverageRate: 0.95, status: 'complete' })
  assert.equal(coverage.canClaimCompleteTodos, false)
})
```

- [x] **Step 2: 实现账本和覆盖规范化**

```javascript
export function normalizeCoverage(value) {
  const data = objectFrom(value)
  const rate = Number(data.coverageRate)
  return {
    ...data,
    coverageRate: Number.isFinite(rate) ? rate : 0,
    canClaimCompleteTodos: data.status === 'complete' && rate === 1
  }
}
```

`normalizeLossLedger` 只保留有 `lossId/lossKey/points/lossType` 的账目，按规则返回顺序展示，不自行重算分数。

- [x] **Step 3: 将 v3 正式任务设为唯一主数据源**

```javascript
const remediationTasks = computed(() => arrayFrom(firstPresent(
  result.value.remediationTasks,
  result.value.remediation_tasks,
  result.value.actionPlan,
  result.value.action_plan
)))
```

当 `contractVersion=ai-score-report-v3` 时，`buildTodosPresentation` 不再合并 `trainingTasks`、deductions、work-item drafts、coaching moments；旧报告才走现有兼容分支。

- [x] **Step 4: 删除 v3 的标题去重**

v3 按服务端 `taskId` 去重，保留 `coveredLossIds`、`coveredGapPoints`、`minimumAcceptance`、`fullScoreCriteria`、`scoreImpact`、`status`。同名但不同 `taskId` 的任务必须同时显示。

- [x] **Step 5: 写 19 条账目覆盖为 N 条任务的展示测试**

断言顶部数量等于 `remediationTaskCount`，不是 lossItemCount，也不是数据源简单相加；断言只有 `scoreImpact.scoreLinkStatus=linked` 才显示提分区间。

- [x] **Step 6: 运行前端单测**

Run: `cd frontend/user && node --test src/utils/aiScoreLossLedger.test.js src/utils/aiScoreCoverage.test.js src/utils/aiScoreTodosPresentation.test.js src/utils/aiScoreProjection.test.js`

Expected: 全部 PASS。

---

### Task 10: 结果页只显示前三项但解释完整差距

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`
- Modify: `frontend/user/src/components/ai-score/report/AiScoreSummaryChrome.vue`
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.test.js`

- [x] **Step 1: 写结果页 view-model 失败测试**

```javascript
test('result page keeps 100 as goal and shows only three priorities', () => {
  const view = buildSummaryPresentation(reportWithElevenTasks)
  assert.equal(view.goalScore, 100)
  assert.equal(view.fullGap, 50.5)
  assert.equal(view.priorityTasks.length, 3)
  assert.equal(view.totalTodoCount, 11)
  assert.equal(view.lossItemCount, 19)
})
```

- [x] **Step 2: 修改顶部关键数字**

结果页固定显示：当前 AI 分数、距离 100 分的完整差距、全部整改最低验收通过后的整体预测区间、完整待办总数。删除“下一档定位线”“阶段目标”“本轮目标分数”。

- [x] **Step 3: 修改前三项区域**

```vue
<IssueQueueCard
  v-for="task in priorityTasks.slice(0, 3)"
  :key="task.taskId"
  :task="task"
/>
<RouterLink :to="report.sectionPath('todos')">
  查看全部 {{ totalTodoCount }} 项整改
</RouterLink>
```

区域标题使用“本轮优先事项”，辅助文案明确“这是执行顺序，不是最终目标；完整目标始终是 100 分”。

- [x] **Step 4: 增加完整性说明**

完整状态显示：“本报告识别 19 条失分账目，已归并为 11 项整改任务，覆盖当前全部 50.5 分差距。”数字全部来自 API。

不完整状态显示：“评分事实已保留，但整改清单生成不完整；暂不把当前列表称为全部待办。”

- [x] **Step 5: 运行单测和构建**

Run: `cd frontend/user && node --test src/utils/aiScoreSummaryPresentation.test.js`

Expected: 全部 PASS。

Run: `cd frontend/user && npm run build`

Expected: 构建成功，无 Vue 模板或导入错误。

---

### Task 11: 全部待办页展示完整队列和真实分值语义

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.test.js`

- [x] **Step 1: 写全量队列测试**

```javascript
test('todos page exposes all server tasks and all covered loss points', () => {
  const view = buildTodosPresentation(v3Report)
  assert.equal(view.items.length, v3Report.coverageSummary.remediationTaskCount)
  assert.equal(view.items.reduce((n, x) => n + x.coveredGapPoints, 0) >= 50.5, true)
  assert.equal(view.coverage.coverageRate, 1)
})
```

总和可大于完整差距是因为一个任务可能解释共享原因；页面总览只能使用 `coverageSummary.coveredGapPoints`，不得把任务值相加。

- [x] **Step 2: 增加页面总览**

页首显示四个事实：观测点数量、失分账目数量、整改任务数量、覆盖率。增加筛选：全部、P0、P1、P2、未开始、进行中、待复评、已验证。

- [x] **Step 3: 明确两种分值标签**

任务卡同时支持：

- `关联当前差距 8.0 分`：事实解释，不是承诺。
- `最低验收通过后，保守预计 +2.0～+3.5`：仅 `scoreLinkStatus=linked` 时显示。

未关联规则的诊断任务显示：“不计入提分预测”，保留验收标准。

- [x] **Step 4: 接入任务状态更新**

用户按钮只调用 Task 8 的状态 API。点击“已完成整改”后显示“待重新评分验证”，页面当前 AI 分数和组合预测保持不变。

- [x] **Step 5: 运行单测和构建**

Run: `cd frontend/user && node --test src/utils/aiScoreTodosPresentation.test.js`

Expected: 全部 PASS。

Run: `cd frontend/user && npm run build`

Expected: 构建成功。

---

### Task 12: 依据页展示全部失分账本

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue`
- Modify: `frontend/user/src/utils/aiScoreWhyPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreWhyPresentation.test.js`

- [x] **Step 1: 写失分分组测试**

```javascript
test('why groups all loss items without losing points', () => {
  const view = buildWhyPresentation({ lossLedger: nineteenLosses, evidenceAnchors })
  assert.equal(view.lossGroups.performance.items.length, 14)
  assert.equal(view.lossGroups.evidence.items.length, 4)
  assert.equal(view.lossGroups.violation.items.length, 1)
  assert.equal(view.lossTotal, 50.5)
})
```

- [x] **Step 2: 把关键帧从唯一主体改为证据视图**

页首先显示“为什么不是 100 分”的完整账本，按表现差距、证据上限、规则惩罚分组。每条显示观测点、原因、分值、关联任务和证据锚点；关键帧和转录仍在下方作为证据，不替代失分事实。

- [x] **Step 3: 增加账目到待办跳转**

通过 `coveredLossIds` 找任务，跳转携带 `?task=<taskId>&loss=<lossId>`。不能再按标题或数组位置推断对应关系。

- [x] **Step 4: 运行测试和构建**

Run: `cd frontend/user && node --test src/utils/aiScoreWhyPresentation.test.js src/utils/aiScoreLossLedger.test.js`

Expected: 全部 PASS。

Run: `cd frontend/user && npm run build`

Expected: 构建成功。

---

### Task 13: 实现重新验证和跨轮状态机

**Files:**
- Create: `frontend/user/src/utils/aiScoreVerification.js`
- Create: `frontend/user/src/utils/aiScoreVerification.test.js`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreRemediationService.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreRemediationServiceTest.java`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`

- [x] **Step 1: 写跨轮验证矩阵测试**

```java
@ParameterizedTest
@MethodSource("verificationCases")
void comparesStableLossKeys(BigDecimal oldPoints, BigDecimal newPoints, String expected) {
    assertThat(service.verificationStatus(oldPoints, newPoints)).isEqualTo(expected);
}

static Stream<Arguments> verificationCases() {
    return Stream.of(
        arguments("4.0", "0.0", "verified"),
        arguments("4.0", "1.5", "partial"),
        arguments("4.0", "4.0", "failed"),
        arguments("0.0", "2.0", "regressed")
    );
}
```

- [x] **Step 2: 实现规则版本门槛**

只有 `ruleHash` 相同才按 `lossKey` 自动比较。规则版本变化时写 `not_observable`，说明“评分规则已变化，本轮不做同口径验证”；不得把规则变更误判为进步或退步。

- [x] **Step 3: 在新报告完成后生成验收记录**

```java
@Transactional
public void verifyAwaitingTasks(Long previousReportId, Long currentReportId) {
    Map<String, BigDecimal> before = lossPoints(previousReportId);
    Map<String, BigDecimal> after = lossPoints(currentReportId);
    for (AiScoreRemediationTask task : awaitingTasks(previousReportId)) {
        TaskVerification result = compareTask(task, before, after);
        saveVerification(task, currentReportId, result);
        updateTaskStatus(task, result.status());
    }
}
```

任务覆盖多个账目时：全部归零为 `verified`；部分下降为 `partial`；均未下降为 `failed`；曾归零后再次出现为 `regressed`。

- [x] **Step 4: 前端呈现验证事实**

```javascript
export const verificationLabels = {
  verified: '复评已验证',
  partial: '部分通过，仍有差距',
  failed: '复评未通过',
  not_observable: '本轮无法同口径验证',
  regressed: '问题再次出现'
}
```

第二次及以后报告显示“已验证 / 部分通过 / 未通过 / 新增 / 回退”的数量和对应账目变化；分数仍直接来自新报告 `overallScore`。

- [x] **Step 5: 运行跨轮测试**

Run: `cd backend && mvn -Dtest=AiScoreRemediationServiceTest,AiScoringSessionServiceTest test`

Expected: BUILD SUCCESS。

Run: `cd frontend/user && node --test src/utils/aiScoreVerification.test.js`

Expected: 全部 PASS。

---

### Task 14: 端到端回放会话 26 并执行灰度验收

**Files:**
- Modify: `frontend/user/tests/ai-score-hardening.spec.js`
- Create: `docs/verification/2026-07-13-transparent-remediation-session-26.md`

- [x] **Step 1: 写 Playwright 用户验收**

```javascript
test('session 26 explains the entire 50.5 point gap', async ({ page }) => {
  await page.goto('/ai-score/report/26/result')
  await expect(page.getByText('49.5')).toBeVisible()
  await expect(page.getByText(/距离 100 分.*50.5/)).toBeVisible()
  await expect(page.getByText(/19 条失分账目/)).toBeVisible()
  await expect(page.locator('[data-testid="priority-task"]')).toHaveCount(3)
  await page.getByRole('link', { name: /查看全部/ }).click()
  await expect(page.locator('[data-testid="todo-row"]')).toHaveCount(expectedTaskCount)
})
```

测试夹具必须从实际报告 API 读取 `expectedTaskCount`，不能写死为 6、7 或 19。

- [x] **Step 2: 先重放完成回调，不重跑视频**

使用会话 26 已保存的 Python 完成结果重新构建 v3 回调并发送到既有 callback URL；确认 HTTP 状态和业务码均成功。重放只允许更新报告快照和任务标准表，不修改媒体资产、ASR 或视觉分析结果。

- [x] **Step 3: 核对数据库和 API**

必须同时成立：

```text
overallScore = 49.5
100 - overallScore = 50.5
sum(lossLedger.points) = 50.5
lossItemCount = 19
coverageRate = 1.0
coveredLossItemCount = 19
todoPortfolioStatus = complete
```

- [x] **Step 4: 执行三端全量验证**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_authoritative_rule_executor.py tests/test_loss_ledger_service.py tests/test_remediation_planner.py tests/test_coverage_validator.py tests/test_score_impact_service.py tests/test_session_authoritative_callback.py tests/test_backend_callback_client.py -q`

Expected: 全部 PASS。

Run: `cd backend && mvn test`

Expected: BUILD SUCCESS。

Run: `cd frontend/user && node --test src/utils/*.test.js`

Expected: 全部 PASS。

Run: `cd frontend/user && npm run build`

Expected: 构建成功。

Run: `cd frontend/user && npm run test:e2e:ai-score`

Expected: 全部 Playwright 用例 PASS。

- [x] **Step 5: 浏览器人工验收三页**

检查 `/ai-score/report/26/result`、`/todos`、`/why`：结果页恰好前三项；待办页为 API 的完整任务数；依据页 19 条账目合计 50.5；任何任务完成操作都不改变 49.5 分；页面没有“下一档定位线”或阶段目标。

- [x] **Step 6: 写灰度验收记录**

`docs/verification/2026-07-13-transparent-remediation-session-26.md` 记录：契约版本、规则哈希、指纹、三端测试命令与结果、API 对账字段、页面截图路径、已知兼容行为。不得记录视频、完整转录或密钥。

---

## 3. 发布顺序与回滚策略

1. 先部署 Java：新字段均可空，旧 v2 回调仍能正常保存和读取。
2. 再部署 Python：开始发送 v3；Java 二次对账失败时保留失败原因，不发布伪完整待办。
3. 最后部署前端：检测 `contractVersion`；v3 走正式完整队列，v2 走旧兼容展示并明确“历史报告”。
4. 会话 26 重放验证通过后，再将 v3 设为新报告默认。
5. 回滚 Python 时 Java/前端继续读取旧契约；回滚前端不影响 v3 数据保存；禁止回滚数据库列或删除已写入任务记录。

## 4. 关键监控

上线后至少记录以下不含用户内容的指标：

- `score_report_v3_reconciliation_failed_total`
- `score_report_v3_coverage_incomplete_total`
- `score_report_v3_callback_retried_total`
- `score_report_v3_task_count` 分布
- `score_report_v3_loss_item_count` 分布
- `score_report_v3_verification_status_total{status}`
- `score_report_v3_rule_version_changed_total`

告警条件：任一 v3 报告 `abs(sum(loss.points) - (100-score)) > 0.1`；或 `status=complete` 但 `coverageRate<1`；或前端待办数与 API `remediationTaskCount` 不一致。

## 5. 最终验收定义

本功能只有在以下条件同时满足时才算完成：

- 用户仍只看到一个 AI 分数，目标永远是 100 分。
- 当前分数与所有失分账目可在 0.1 分误差内完整对账。
- 每条正分失分账目均有至少一个正式整改任务。
- 首页只展示前三项，本轮优先不被解释为阶段目标。
- 全部待办页展示去重后的完整队列，并区分“关联差距”和“保守提分区间”。
- 无规则关联的建议没有分数承诺。
- 用户标记完成不会直接涨分。
- 新一轮评分能够给出 verified/partial/failed/not_observable/regressed 结果。
- 会话 26 无需重跑视频即可升级为 v3，并明确解释 49.5 分对应的 50.5 分完整差距。
