# AI Scoring P0 Authoritative Score Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Python structured rule result the only user-facing AI score and require Java to recompute the same normalized inputs before publishing a completed report.

**Architecture:** Python will convert evidence extraction into a canonical score contract and calculate the authoritative result. Java will receive that contract, recompute it with the existing deterministic engine, reject mismatches, and persist only reconciled results. The legacy LLM score remains as audit metadata and never becomes the report's `overallScore`.

**Tech Stack:** Python 3, pytest, FastAPI scoring service, Java 21/Spring Boot, JUnit 5, MyBatis Plus, Vue 3.

---

### Task 1: Lock the Python score contract with tests

**Status:** Completed 2026-07-13. The local Python environment has no pytest, so the new focused suite is also runnable through `unittest`.

**Files:**
- Create: `ai-scoring/app/services/scoring/__init__.py`
- Create: `ai-scoring/app/services/scoring/rule_executor.py`
- Create: `ai-scoring/tests/test_authoritative_rule_executor.py`

- [ ] Write failing tests covering base score, deductions, evidence cap, invalid/recovered deduction exclusion, clamping, dimension totals, and reconciliation totals.
- [ ] Run `cd ai-scoring && .venv/bin/python -m pytest tests/test_authoritative_rule_executor.py -q`; expect failures because `execute_rule_score` does not exist.
- [ ] Implement `execute_rule_score(observations, deductions, recoveries=None)` with the formula `max(0, min(baseScore - deductions + recoveries, scoreCap))` and a canonical result payload.
- [ ] Run the focused pytest file and confirm all cases pass.

### Task 2: Convert evidence extraction into canonical observations and deductions

**Status:** Completed 2026-07-13, including a separate categorical achievement assessment so evidence strength is not treated as base score.

**Files:**
- Modify: `ai-scoring/app/services/pipeline_payloads.py`
- Create: `ai-scoring/tests/test_pipeline_authoritative_payload.py`

- [ ] Write failing tests asserting that canonical observations contain distinct `baseScore`, `maxScore`, and `scoreCap`, and that deduction IDs are deterministic rather than `shadow-D-N`.
- [ ] Run `cd ai-scoring && .venv/bin/python -m pytest tests/test_pipeline_authoritative_payload.py -q`; expect contract failures.
- [ ] Replace the shadow-only calculation with canonical payload construction and call `execute_rule_score`.
- [ ] Preserve `llmRawScore`, `scoreDiff`, rule hash, evidence anchors, and legacy field aliases for audit compatibility.
- [ ] Run both new Python test files.

### Task 3: Publish the Python authoritative score in session callbacks

**Status:** Completed 2026-07-13. Structured callbacks publish the rule result; fallbacks are explicitly labeled `legacy_llm`.

**Files:**
- Modify: `ai-scoring/app/services/session_pipeline_service.py`
- Create: `ai-scoring/tests/test_session_authoritative_callback.py`

- [ ] Write a failing callback test proving `overallScore` equals `ruleEngineScore`, not `ai_score.overall_score`, whenever a canonical structured result exists.
- [ ] Add a failing fallback test proving legacy LLM scoring is used only when no structured rule result can be built, and the payload is explicitly marked `scoreAuthority=legacy_llm`.
- [ ] Update callback assembly to send `scoreAuthority`, canonical observations, deductions, reconciliation totals, and authoritative `overallScore`.
- [ ] Run the focused callback tests and the existing session pipeline tests.

### Task 4: Add Java authoritative-score reconciliation gate

**Status:** Completed 2026-07-13. Mismatches move the session to `calculation_failed` and do not insert a report.

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoringSessionReportDetailTest.java`

- [ ] Write failing Java tests for a matching Python/Java score, a mismatch, missing canonical observations, and an invalid evidence-anchor reference.
- [ ] Run the focused Maven tests and verify the new cases fail.
- [ ] Map Python `baseScore` explicitly into the Java structured contract without treating an already-deducted score as raw input.
- [ ] Recompute with `AiScoreRuleEngine`; reject authoritative callbacks whose score differs beyond decimal rounding tolerance.
- [ ] Persist `overallScore` only after reconciliation succeeds; otherwise mark the session `calculation_failed` and do not publish the report.
- [ ] Run the focused Java tests.

### Task 5: Add report-level accounting assertions

**Status:** Partially completed 2026-07-13. Total-score recomputation and dimension-total production are enforced; dedicated persisted-report assertions remain.

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreReportReconciliationService.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreReportReconciliationServiceTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`

- [ ] Write failing tests for dimension-total mismatch, deduction-total mismatch, score-cap overflow, and a valid report.
- [ ] Implement a focused reconciliation service returning structured failure codes.
- [ ] Invoke it before changing a session to `completed`.
- [ ] Run the focused reconciliation and session tests.

### Task 6: Keep one user-visible score

**Status:** Completed 2026-07-13. Reconciled report score has precedence and recoverable wording is explicitly a maximum, not a promise.

**Files:**
- Modify: `frontend/user/src/composables/useAiScoreReport.js`
- Modify: `frontend/user/src/utils/aiScoreRuleEngineReport.js`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportResult.vue`
- Test: relevant `frontend/user/src/utils/*.test.js`

- [ ] Add tests proving the main score comes from reconciled `overallScore` and audit-only LLM/shadow values are not selected as fallbacks.
- [ ] Hide raw model score and score-difference diagnostics from the ordinary result view while retaining data parsing for administrative use.
- [ ] Keep deductions, evidence cap, and maximum recoverable wording visible and reconcilable.
- [ ] Run Node utility tests and the AI-score E2E test.

### Task 7: Verification and compatibility audit

**Status:** Completed 2026-07-13. A real 39-minute commerce-track video completed through the authenticated upload endpoint as session 24/report 36. Python authoritative score, Java acceptance, persisted dimension totals, deduction accounting, and the user report API all reconcile to 39.10. The run also drove follow-up fixes for recoverable-score totals and specific training-task wording.

**Files:**
- Modify only files required by failures found during verification.

- [x] Run all new Python tests plus existing evidence extraction and payload tests.
- [x] Run the backend AI scoring service/controller test subset.
- [x] Run frontend utility tests and the production build; use the real authenticated upload flow as the runtime E2E verification.
- [x] Inspect the generated callback/report and confirm `overallScore == ruleEngineScore == Java recomputed score == 39.10`.
- [x] Confirm legacy meeting reports still load and are labeled as legacy rather than silently presented as reconciled authoritative scores.
