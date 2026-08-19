# AI Score Action Plan Todos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every Python `action_plan` item through the Java report contract and merge it with score-linked training tasks into one deduplicated user todo queue.

**Architecture:** Python normalizes the full action plan, assigns stable IDs, and aligns legacy items to deduction candidates by observation code before serializing `actionPlanJson`. Java stores the JSON, exposes both raw and parsed forms, and preserves `trainingTasks` as the only score-recovery authority. The frontend creates one merged queue keyed by observation code, source issue key, then normalized issue fingerprint; result and todo pages consume that same queue.

**Tech Stack:** Python 3/unittest, Spring Boot 3/MyBatis-Plus/MySQL/JUnit 5/Mockito, Vue 3/Node test runner.

---

### Task 1: Python callback action-plan contract

**Files:**
- Modify: `ai-scoring/tests/test_session_authoritative_callback.py`
- Modify: `ai-scoring/app/services/session_pipeline_service.py`
- Modify: `ai-scoring/app/services/scoring_prompt_contracts.py`

- [ ] **Step 1: Write failing callback tests**

Add tests that pass six action-plan entries to `_build_final_result`, assert `json.loads(final_result["actionPlanJson"])` contains all six in order, and assert the AI failure action receives `observationCode == "O02"` from a matching `evidence_extraction.deductionCandidates` trigger fact. Add a second test proving empty plans serialize as `[]` and no plan-provided recovery field is introduced.

- [ ] **Step 2: Run the focused Python test and verify RED**

Run: `python -m pytest tests/test_session_authoritative_callback.py -q`

Expected: FAIL because `actionPlanJson` is absent.

- [ ] **Step 3: Implement deterministic normalization**

In `session_pipeline_service.py`, add a focused helper that:

```python
def _normalize_action_plan_for_callback(ai_score: dict, evidence_extraction: dict) -> list[dict]:
    ...
```

It must preserve every dictionary item, normalize camel-case fields, generate a stable SHA-256-based `id` when absent, preserve explicit `observationCode`/`sourceIssueKey`, and align missing observation codes to deduction candidates only when normalized trigger/problem similarity passes a conservative threshold. It must never copy `expected_gain` or any recoverable-score claim into the action-plan contract.

Serialize the normalized list with `ensure_ascii=False` into `final_result["actionPlanJson"]`.

Extend the prompt action-plan schema with optional `observation_code` and `source_issue_key` fields so future model results require less inference.

- [ ] **Step 4: Run Python tests and verify GREEN**

Run: `python -m pytest tests/test_session_authoritative_callback.py tests/test_scoring_prompt_contracts.py -q`

Expected: PASS.

### Task 2: Java persistence and report API contract

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- Modify: `backend/src/main/java/com/orep/backend/entity/AiScoreReport.java`
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/resources/sql/create_ai_score_report_table.sql`
- Create: `backend/src/main/resources/sql/migrate_ai_score_report_action_plan.sql`

- [ ] **Step 1: Write failing persistence test**

Extend the completed-callback upsert test with:

```java
result.setActionPlanJson("[{\"id\":\"action-1\",\"title\":\"加固AI演示\"}]");
assertEquals(result.getActionPlanJson(), existingReport.getActionPlanJson());
```

Expected initial compile failure because the DTO/entity accessors do not exist.

- [ ] **Step 2: Write failing report mapping tests**

Add report-detail assertions that valid JSON is returned in both `actionPlanJson` and `actionPlan`, malformed JSON becomes an empty `actionPlan` without failing the response, and a generated training task exposes its `observationCode` and deduction-derived `sourceIssueKey`.

- [ ] **Step 3: Run focused Java tests and verify RED**

Run: `./mvnw -q -Dtest=AiScoringSessionServiceTest,AiScoringSessionReportDetailTest test` (use `mvn` if the wrapper is absent).

Expected: compilation/test failure for missing action-plan fields.

- [ ] **Step 4: Implement schema and DTO fields**

Add:

```java
private String actionPlanJson;
```

to callback/result persistence types, and:

```java
private String actionPlanJson;
private List<Map<String, Object>> actionPlan;
```

to the user response. Add `observationCode` and `sourceIssueKey` to `TrainingTask`.

Add `action_plan_json LONGTEXT` to the base schema, an idempotent migration, and `ensureReportSchemaCompatibility()` runtime compatibility for existing installations.

- [ ] **Step 5: Implement persistence and safe API parsing**

Persist `result.getActionPlanJson()` during completed callback upsert. Map raw JSON to the user response and parse it with the existing `parseMapList`; invalid or missing JSON must yield `List.of()`. Populate training-task observation/source keys from the deduction row.

- [ ] **Step 6: Run focused Java tests and verify GREEN**

Run: `./mvnw -q -Dtest=AiScoringSessionServiceTest,AiScoringSessionReportDetailTest test` (or `mvn`).

Expected: PASS.

### Task 3: Frontend normalization and unified todo merge

**Files:**
- Modify: `frontend/user/src/utils/aiScoreTrainingTasks.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreTodosPresentation.test.js`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`

- [ ] **Step 1: Write failing merge tests**

Add a fixture containing six `actionPlan` entries and one training task sharing `observationCode: "O02"`. Assert:

```js
assert.equal(view.items.length, 6)
assert.equal(view.items.filter(item => item.recoverPoints !== null).length, 1)
assert.equal(view.items.find(item => item.observationCode === 'O02').recoverPoints, 2)
```

Also test `sourceIssueKey` dedupe, fallback issue-fingerprint dedupe, distinct problems remaining distinct, action-plan recovery claims being ignored, and Python coaching payloads under `training_tasks` being recognized.

- [ ] **Step 2: Run frontend unit test and verify RED**

Run: `node --test src/utils/aiScoreTodosPresentation.test.js`

Expected: FAIL because formal action plans and `training_tasks` are not merged/recognized.

- [ ] **Step 3: Expose normalized report action plan**

In `normalizeLegacyResult`, parse `data.actionPlan`, `data.actionPlanJson`, then legacy `data.ai_score.action_plan`. Add an `actionPlan` computed value to the report context and preserve all entries.

Update training-task normalization to retain `observationCode`, `sourceIssueKey`, and a score-linked marker.

- [ ] **Step 4: Implement source-aware merge**

Update `buildTodosPresentation` to accept formal `actionPlan` separately from optional coaching. Normalize action-plan `problem/method/acceptance/owner/timebox` fields without accepting any recovery score. Replace title-only dedupe with merge precedence:

1. identical observation code;
2. identical source issue key;
3. conservative normalized issue fingerprint;
4. exact normalized title for legacy compatibility.

When merging, keep the score-linked item as the base so recovery points survive only from a structured deduction, while richer action method/owner/timebox/acceptance fields fill blanks.

- [ ] **Step 5: Run frontend unit test and verify GREEN**

Run: `node --test src/utils/aiScoreTodosPresentation.test.js src/utils/aiScoreTrainingTasks.test.js`

Expected: PASS.

### Task 4: Make result page, nav count, and todo page consume the same queue

**Files:**
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreSummaryPresentation.test.js`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue`
- Modify: `frontend/user/src/composables/useAiScoreReport.js`

- [ ] **Step 1: Write failing presentation/count tests**

Add summary tests proving a six-item unified queue yields `prescriptionCount == 6`, `topPrescriptions.length == 3`, and `morePrescriptionCount == 3`. Keep the full six available to the todo presentation.

- [ ] **Step 2: Run tests and verify RED**

Run: `node --test src/utils/aiScoreSummaryPresentation.test.js src/utils/aiScoreTodosPresentation.test.js`

Expected: FAIL because summary currently returns early on `trainingTasks`.

- [ ] **Step 3: Wire one computed unified queue everywhere**

Create a single `unifiedTodos` computed value in `useAiScoreReport`. Derive report work-item drafts and nav count from it. Pass the same list or the same full source snapshot to result and todo views; result slices to three only for rendering, while the todo page renders all entries. Remove the early-return behavior that lets one training task suppress action plans and improvement fallbacks.

- [ ] **Step 4: Run frontend tests and build**

Run:

```bash
node --test src/utils/aiScoreSummaryPresentation.test.js src/utils/aiScoreTodosPresentation.test.js src/utils/aiScoreTrainingTasks.test.js
npm run build
```

Expected: all tests PASS and Vite build exits 0.

### Task 5: Replay session 26 callback and verify real data

**Files:**
- Use: `ai-scoring/uploads/results/result_26.json`
- Verify: MySQL `orep.ai_score_report` report 40

- [ ] **Step 1: Run focused and regression suites**

Run:

```bash
cd ai-scoring && python -m pytest tests/test_session_authoritative_callback.py tests/test_scoring_prompt_contracts.py -q
cd backend && mvn -q test
cd frontend/user && node --test src/utils/*.test.js && npm run build
```

Expected: all executable suites PASS.

- [ ] **Step 2: Apply the idempotent schema migration**

Run the migration against the local `orep` database and confirm `SHOW COLUMNS FROM ai_score_report LIKE 'action_plan_json'` returns one LONGTEXT column.

- [ ] **Step 3: Replay completion without reprocessing video**

Build the completed callback from the existing `result_26.json` through `_build_final_result` and send it with session ID 26 to the Java callback endpoint. Confirm HTTP success and business response code success.

- [ ] **Step 4: Verify persistence and API semantics**

Confirm report 40 has `JSON_LENGTH(action_plan_json) = 6`. Fetch the report API and verify six parsed action-plan items, one training task, and observation linkage for the overlapping item.

- [ ] **Step 5: Verify UI behavior**

Open `/ai-score/report/26/result` and confirm:

- top navigation shows the deduplicated total, not `1` or `7`;
- the result page shows exactly three highest-priority items;
- only the score-linked item displays `最高可追回约 2.0`;
- the todo page shows the entire deduplicated queue and every diagnostic action shows its acceptance standard.

## Repository Note

`/Users/liuyixing/项目/OREP` is not a Git repository, so the commit steps normally required by this planning workflow cannot be performed here. Changes must remain scoped to the files above and be reported explicitly at handoff.

