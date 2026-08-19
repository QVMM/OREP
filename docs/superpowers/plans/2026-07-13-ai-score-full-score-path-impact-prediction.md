# AI 评分满分路径与提分预测实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除前端下一档目标，以 100 分展示完整差距，并由 Python 规则引擎为正式计分待办和全部整改组合生成保守提分预测区间。

**Architecture:** Python 新增独立 `score_impact_service`，基于结构化观测、独立扣分和同一规则执行器完成单项边际复算与组合复算；完成回调携带每条任务的 `scoreImpact` 和报告级 `scoreProjectionJson`。Java 只负责契约、持久化和解析，前端只负责显示后端预测，禁止自行相加或回退到 60/70/85 分档。

**Tech Stack:** Python 3.14、pytest、现有确定性 `execute_rule_score`；Java 21、Spring Boot、MyBatis-Plus、JUnit 5、MySQL；Vue 3、Node 原生测试器、Vite。

---

## 文件结构

- Create: `ai-scoring/app/services/scoring/score_impact_service.py`：任务关联、情景构造、单项与组合复算的唯一实现。
- Create: `ai-scoring/tests/test_score_impact_service.py`：情景复算、防重复计分和无关联禁分测试。
- Modify: `ai-scoring/app/services/session_pipeline_service.py`：在完成回调中组装 `scoreImpact` 和 `scoreProjectionJson`。
- Modify: `ai-scoring/app/services/scoring_prompt_contracts.py`：要求新行动计划尽量输出结构化评分关联，但不允许模型输出最终分值。
- Modify: `ai-scoring/tests/test_session_authoritative_callback.py`：回调契约测试。
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`：接收整体预测 JSON。
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`：持久化整体预测 JSON。
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`：报告 API 返回原始和解析后的整体预测。
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`：兼容建列、回调落库、报告解析。
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`：回调持久化测试。
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`：报告 API 解析与非法 JSON 测试。
- Create: `backend/src/main/resources/sql/migrate_ai_score_report_score_projection.sql`：幂等迁移。
- Modify: 四份 `create_ai_score_report_table.sql`：统一基础建表契约。
- Modify: `frontend/user/src/composables/useAiScoreReport.js`：解析并暴露 `scoreProjection`。
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.js`：保留 `scoreImpact`、生成用户端区间文案。
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.js`：固定 100 分目标，读取整体预测。
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`：顶部满分路径和整体预测。
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`：单项分值类型文案与额外建议标识。
- Modify: 对应前端测试文件：100 分完整差距、区间展示、unlinked 禁分、前三项与全量队列回归。

### Task 1: Python 分值影响服务

**Files:**
- Create: `ai-scoring/tests/test_score_impact_service.py`
- Create: `ai-scoring/app/services/scoring/score_impact_service.py`

- [ ] **Step 1: 写独立扣分、证据、表现和无关联任务的失败测试**

```python
from app.services.scoring.score_impact_service import build_score_impact_projection


def test_builds_conservative_task_ranges_and_portfolio_projection():
    observations = [
        {"observationCode": "O1", "dimensionCode": "skill", "maxScore": 10,
         "baseScore": 5, "scoreCap": 10, "performanceReason": "讲解节奏拖沓"},
        {"observationCode": "O2", "dimensionCode": "value", "maxScore": 10,
         "baseScore": 8, "scoreCap": 5, "evidenceReason": "数据缺少来源"},
    ]
    deductions = [{"deductionId": "D1", "observationCode": "O1", "deductedPoints": 2,
                   "maxRecoverablePoints": 2, "scoreEffect": "subtractive", "status": "new"}]
    tasks = [
        {"id": "t1", "title": "修复演示故障", "observationCode": "O1", "sourceIssueKey": "D1"},
        {"id": "t2", "title": "优化讲解节奏", "observationCode": "O1", "impactType": "performance_improvement"},
        {"id": "t3", "title": "补充数据来源", "observationCode": "O2", "impactType": "evidence_unlock"},
        {"id": "t4", "title": "更换队服"},
    ]

    scored_tasks, projection = build_score_impact_projection(
        tasks, observations, deductions, rule_hash="rule-1", scoring_fingerprint="fp-1"
    )

    assert scored_tasks[0]["scoreImpact"]["impactType"] == "deduction_recovery"
    assert scored_tasks[0]["scoreImpact"]["upper"] == 2.0
    assert scored_tasks[1]["scoreImpact"]["lower"] <= scored_tasks[1]["scoreImpact"]["upper"]
    assert scored_tasks[2]["scoreImpact"]["impactType"] == "evidence_unlock"
    assert scored_tasks[3]["scoreImpact"]["scoreLinkStatus"] == "unlinked"
    assert scored_tasks[3]["scoreImpact"]["upper"] is None
    assert projection["goalScore"] == 100.0
    assert projection["predictedScoreUpper"] <= 100.0
```

- [ ] **Step 2: 写相同观测点不重复计分的失败测试**

```python
def test_portfolio_replays_shared_observation_once_instead_of_summing_task_upper_bounds():
    observations = [{"observationCode": "O1", "dimensionCode": "skill", "maxScore": 10,
                     "baseScore": 5, "scoreCap": 10, "performanceReason": "讲解节奏和结构不足"}]
    tasks = [
        {"id": "a", "title": "精简讲解", "observationCode": "O1", "impactType": "performance_improvement"},
        {"id": "b", "title": "降低语速", "observationCode": "O1", "impactType": "performance_improvement"},
    ]
    scored, projection = build_score_impact_projection(tasks, observations, [], rule_hash="r", scoring_fingerprint="f")
    assert projection["predictedGainUpper"] <= max(item["scoreImpact"]["upper"] for item in scored)
```

- [ ] **Step 3: 运行测试并确认因模块不存在而失败**

Run: `.venv/bin/python -m pytest -q tests/test_score_impact_service.py`  
Expected: FAIL，`ModuleNotFoundError: app.services.scoring.score_impact_service`

- [ ] **Step 4: 实现确定性任务关联和情景复算**

实现公开入口：

```python
def build_score_impact_projection(
    action_plan,
    observations,
    deductions,
    *,
    rule_hash=None,
    scoring_fingerprint=None,
):
    """Return (scored_action_plan, report_projection)."""
```

实现约束：

- 优先使用任务显式 `observationCode(s)`；其次使用 `sourceIssueKey` 对齐 `deductionId/causeCode/penaltyRuleCode`；最后仅以高阈值文本指纹匹配观测点名称、表现理由和证据理由。
- 独立扣分情景通过 `execute_rule_score(..., recoveries=[...])` 撤销允许恢复值。
- 证据情景只提高 `scoreCap`，不提高 `baseScore`。
- 表现情景将 `baseScore/maxScore` 提升到下一离散等级，等级固定为 `0, 0.3, 0.5, 0.8, 1.0`；`scoreCap` 至少提高到新 `baseScore`，表示重新路演视频已经成为新表现证据。
- 相同观测点组合时取目标状态最大值，只修改一次；独立扣分按稳定 `deductionId` 只恢复一次。
- `lower/upper`、预测分和增量统一四舍五入到一位，限制在 `0..100`。
- 无明确关联或复算上限为 0 的任务输出 `scoreLinkStatus=unlinked`、空区间和原因，不接受模型 `expected_gain`。

- [ ] **Step 5: 运行新增测试**

Run: `.venv/bin/python -m pytest -q tests/test_score_impact_service.py`  
Expected: PASS

### Task 2: Python 完成回调集成

**Files:**
- Modify: `ai-scoring/tests/test_session_authoritative_callback.py`
- Modify: `ai-scoring/tests/test_scoring_prompt_contracts.py`
- Modify: `ai-scoring/app/services/session_pipeline_service.py`
- Modify: `ai-scoring/app/services/scoring_prompt_contracts.py`

- [ ] **Step 1: 写回调包含单项影响和整体预测的失败测试**

```python
final_result = _build_final_result(pipeline_result)
action_plan = json.loads(final_result["actionPlanJson"])
projection = json.loads(final_result["scoreProjectionJson"])

self.assertEqual(projection["goalScore"], 100.0)
self.assertEqual(projection["currentScore"], 49.5)
self.assertIn("scoreImpact", action_plan[0])
self.assertNotIn("expectedRecoverPoints", action_plan[0])
```

- [ ] **Step 2: 写提示词契约禁止模型分值、允许评分关联字段的失败测试**

```python
schema = score_output_schema()
action_item = schema["properties"]["action_plan"]["items"]
assert "observation_codes" in action_item["properties"]
assert "criterion_codes" in action_item["properties"]
assert "impact_type" in action_item["properties"]
assert "expected_gain" not in action_item["properties"]
```

- [ ] **Step 3: 运行回调和契约测试确认失败**

Run: `.venv/bin/python -m pytest -q tests/test_session_authoritative_callback.py tests/test_scoring_prompt_contracts.py`  
Expected: FAIL，缺少 `scoreProjectionJson`、`scoreImpact` 或新契约字段。

- [ ] **Step 4: 在 `_build_final_result` 调用分值影响服务**

在生成 `action_plan` 后调用：

```python
action_plan, score_projection = build_score_impact_projection(
    action_plan,
    observations,
    deductions,
    rule_hash=shadow_payload.get("ruleHash") or evidence_extraction.get("ruleHash"),
    scoring_fingerprint=shadow_payload.get("scoringFingerprint"),
)
```

回调增加：

```python
"actionPlanJson": json.dumps(action_plan, ensure_ascii=False),
"scoreProjectionJson": json.dumps(score_projection, ensure_ascii=False),
```

无结构化正式分时返回固定满分参照和空预测：`goalScore=100`，预测上下界为空，不使用 LLM 分数制造提分预测。

- [ ] **Step 5: 更新行动计划输出契约**

行动计划项允许 `observation_codes`、`criterion_codes`、`dimension_code` 和 `impact_type`，删除任何要求模型给出 `expected_gain` 的表述。保留旧输出兼容读取，但回调规范化必须删除模型分值字段。

- [ ] **Step 6: 运行 Python 相关测试**

Run: `.venv/bin/python -m pytest -q tests/test_score_impact_service.py tests/test_session_authoritative_callback.py tests/test_scoring_prompt_contracts.py tests/test_pipeline_authoritative_payload.py tests/test_pipeline_payloads_rule_shadow.py`  
Expected: PASS

### Task 3: Java 回调、数据库和报告 API

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Create: `backend/src/main/resources/sql/migrate_ai_score_report_score_projection.sql`
- Modify: `backend/src/main/resources/sql/create_ai_score_report_table.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_score_report_table.sql`
- Modify: `deploy/sql/backend-resources/create_ai_score_report_table.sql`
- Modify: `windowsrun/apps/sql/backend-resources/create_ai_score_report_table.sql`

- [ ] **Step 1: 写回调落库和 API 解析失败测试**

```java
result.setScoreProjectionJson("{\"goalScore\":100,\"predictedScoreLower\":61.0,\"predictedScoreUpper\":67.5}");
service.applyCallback(request);
assertEquals(result.getScoreProjectionJson(), savedReport.getScoreProjectionJson());

AiScoreReportUserResponse response = service.reportBySession(26L);
assertEquals(new BigDecimal("100"), new BigDecimal(response.getScoreProjection().get("goalScore").toString()));
```

另加非法 JSON 用例，期望 `scoreProjection` 为空对象且报告接口不失败。

- [ ] **Step 2: 运行目标 Java 测试确认失败**

Run: `mvn -Dtest=AiScoringSessionServiceTest,AiScoringSessionReportDetailTest test`  
Expected: FAIL，缺少 `scoreProjectionJson` 字段或 getter。

- [ ] **Step 3: 增加 DTO、实体、落库和解析**

字段契约：

```java
private String scoreProjectionJson;
private Map<String, Object> scoreProjection;
```

`AiScoringSessionService` 在运行时兼容检查、完成回调 upsert 和报告响应中分别处理 `score_projection_json`；解析失败返回 `Map.of()`。

- [ ] **Step 4: 增加幂等迁移并同步建表脚本**

迁移使用 `information_schema.columns` 检查后执行：

```sql
ALTER TABLE ai_score_report
  ADD COLUMN score_projection_json LONGTEXT DEFAULT NULL COMMENT '全部整改验收后的规则情景预测 JSON';
```

- [ ] **Step 5: 运行 Java 目标测试和全量测试**

Run: `mvn -Dtest=AiScoringSessionServiceTest,AiScoringSessionReportDetailTest test`  
Expected: PASS

Run: `mvn test`  
Expected: 0 failures、0 errors。

### Task 4: 前端满分路径与数据契约

**Files:**
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.test.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.test.js`
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.js`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`

- [ ] **Step 1: 写 100 分目标与整体预测失败测试**

```javascript
const view = buildScoreSummaryPresentation({
  overallScore: 49.5,
  scoreProjection: {
    goalScore: 100,
    predictedScoreLower: 61,
    predictedScoreUpper: 67.5,
    predictedGainLower: 11.5,
    predictedGainUpper: 18
  }
})
assert.equal(view.metrics.goalScore, 100)
assert.equal(view.metrics.fullGap, 50.5)
assert.equal(view.metrics.predictedScoreDisplay, '61.0～67.5')
assert.equal(view.metrics.predictedGainDisplay, '+11.5～+18.0')
```

另加无 `scoreProjection` 用例：目标仍为 100，完整差距存在，预测显示为空，不产生 60。

- [ ] **Step 2: 写三种影响文案与 unlinked 禁分失败测试**

```javascript
const { items } = buildTodosPresentation({
  actionPlan: [
    { id: 'a', title: '演示故障', scoreImpact: { scoreLinkStatus: 'linked', impactType: 'deduction_recovery', lower: 2, upper: 2 } },
    { id: 'b', title: '优化节奏', scoreImpact: { scoreLinkStatus: 'linked', impactType: 'performance_improvement', lower: 2, upper: 4 } },
    { id: 'c', title: '额外建议', scoreImpact: { scoreLinkStatus: 'unlinked', lower: null, upper: null } },
  ]
})
assert.equal(items[0].scoreImpactLabel, '最高可追回约 2.0 分')
assert.equal(items[1].scoreImpactLabel, '达到验收标准后，预计可提升 2.0～4.0 分')
assert.equal(items[2].scoreImpactLabel, '')
assert.equal(items[2].sourceLabel, '额外训练建议')
```

- [ ] **Step 3: 运行目标前端测试确认失败**

Run: `node --test src/utils/aiScoreSummaryPresentation.test.js src/utils/aiScoreTodosPresentation.test.js`  
Expected: FAIL，仍返回下一档目标或缺少区间字段。

- [ ] **Step 4: 删除下一档回退并读取报告级预测**

`buildScoreSummaryPresentation` 固定：

```javascript
const goalScore = 100
const fullGap = overallScore === null ? null : Math.max(0, goalScore - overallScore)
```

预测上下界仅从 `input.scoreProjection` 读取。删除 `resolveNextBandTarget`、`targetSource='band'` 以及单项任务求和后冒充整体预测的逻辑。

- [ ] **Step 5: 规范化单项 `scoreImpact`**

`buildTodosPresentation` 输出 `scoreImpactType/lower/upper/label/scoreLinked`。只有 `scoreLinkStatus=linked` 且上下界有效时生成分值文案；旧结构化扣分继续转换为 `deduction_recovery`，旧行动计划分值字段不可信且不读取。

- [ ] **Step 6: 在报告 composable 解析并传递 `scoreProjection`**

兼容读取：

```javascript
const scoreProjection = computed(() => objectFrom(firstPresent(
  result.value.scoreProjection,
  result.value.score_projection,
  parseJsonValue(result.value.scoreProjectionJson, {})
)))
```

同时将其传入结果页 view-model，不改变统一待办的完整数量和去重逻辑。

- [ ] **Step 7: 运行前端工具测试**

Run: `node --test src/utils/*.test.js`  
Expected: 0 failures。

### Task 5: Vue 页面展示

**Files:**
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`

- [ ] **Step 1: 修改结果页顶部信息**

四个关键区块改为：

```text
满分目标 100
距离满分 50.5
本轮全部通过后的预测 61.0～67.5（无预测时：待规则测算）
本轮优先事项 3
```

预测下方显示固定免责声明。删除“离目标还有一段路”“下一档定位线”“还能追”等阶段目标语言；分数主标题仍显示当前唯一 AI 分数。

- [ ] **Step 2: 修改结果页前三项和待办页单项卡片**

- 扣分恢复显示“最高可追回约 X 分”；
- 证据解锁显示“补证并核验通过后，预计可争取 X～Y 分”；
- 表现改善显示“达到验收标准后，预计可提升 X～Y 分”；
- unlinked 显示“额外训练建议”，不显示任何数字；
- 保持结果页前三项、还有 N 件、待办页完整队列。

- [ ] **Step 3: 运行生产构建**

Run: `npm run build`  
Expected: 构建成功；允许现有 chunk-size warning，不允许编译错误。

### Task 6: 数据迁移、会话 26 重放与验收

**Files:**
- Use: `backend/src/main/resources/sql/migrate_ai_score_report_score_projection.sql`
- Use: `ai-scoring/uploads/results/result_26.json`

- [ ] **Step 1: 执行幂等数据库迁移**

Run: `mysql -h127.0.0.1 -uroot -p12345678 orep < backend/src/main/resources/sql/migrate_ai_score_report_score_projection.sql`  
Expected: exit 0；`ai_score_report.score_projection_json` 存在。

- [ ] **Step 2: 重启 Java 服务以加载新字段契约**

确认 8080 端口只有一个新进程，启动日志包含 `Started OrepBackendApplication`，不影响仍运行在 8090 的 Python 服务。

- [ ] **Step 3: 用现有结果重放会话 26 完成回调**

从 `result_26.json` 调用当前 `_build_final_result` 和现有完成回调客户端，设置：

```text
NO_PROXY=127.0.0.1,localhost
no_proxy=127.0.0.1,localhost
```

Expected: HTTP 状态成功且业务响应码 200；不读取或重新处理原视频。

- [ ] **Step 4: 验证数据库**

查询并确认：

- `JSON_LENGTH(action_plan_json)` 与实际规范化任务一致；
- `score_projection_json.goalScore = 100`；
- 所有有数字的任务 `scoreLinkStatus=linked`；
- 所有 `unlinked` 任务的 `lower/upper` 均为 null；
- 组合预测分不超过 100。

- [ ] **Step 5: 用真实用户端验收**

打开 `/ai-score/report/26/result` 和 `/ai-score/report/26/todos`，确认：

- 不再出现“下一档定位线”和目标 60；
- 显示当前 49.5 / 100、满分目标 100、完整差距 50.5；
- 顶部整体预测与数据库 `scoreProjection` 一致；
- 每条正式计分待办有正确类型的保守区间；
- 额外建议没有分数；
- 顶部待办数量、结果页前三项和待办页全量一致。

- [ ] **Step 6: 完成前新鲜验证**

Run:

```bash
cd ai-scoring && .venv/bin/python -m pytest -q tests/test_score_impact_service.py tests/test_session_authoritative_callback.py tests/test_scoring_prompt_contracts.py tests/test_pipeline_authoritative_payload.py tests/test_pipeline_payloads_rule_shadow.py
cd backend && mvn test
cd frontend/user && node --test src/utils/*.test.js
cd frontend/user && npm run build
```

Expected: 所有命令 exit 0。

## 执行说明

当前 `/Users/liuyixing/项目/OREP` 根目录不是 Git 仓库，无法执行计划中的频繁提交或创建工作树。实施过程中使用测试红绿循环和文件级检查点代替提交，不执行任何提交、推送或 PR 操作。
