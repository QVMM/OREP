# AI Scoring Single-Attribution Python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python authoritative scoring path with a deterministic single-attribution policy, block unconfirmed track bindings from official publication, and rerun the supplied video as an explicitly non-official diagnostic when the real track is still unknown.

**Architecture:** Keep LLM output limited to performance/evidence observations and candidate events. Adapt legacy candidates into mutually exclusive diagnostic or hard-violation effects, then calculate the official score and a complete loss ledger in the deterministic rule executor. Add a track-binding gate at the Python session entry so guessed/default tracks cannot publish official scores.

**Tech Stack:** Python 3.14, FastAPI/Pydantic, pytest/unittest, Decimal arithmetic, existing OREP scoring pipeline.

---

## File map

- Modify `ai-scoring/app/services/scoring/rule_executor.py`: policy-v2 formula, hard-violation filtering, loss ledger, reconciliation invariants.
- Modify `ai-scoring/app/services/pipeline_payloads.py`: classify legacy deductions and emit only effective hard violations as subtractive deductions.
- Create `ai-scoring/app/services/scoring/track_binding.py`: validate official versus diagnostic track bindings.
- Modify `ai-scoring/app/routers/session_scoring_router.py`: accept binding metadata and reject invalid official starts before queuing.
- Modify `ai-scoring/app/services/session_pipeline_service.py`: propagate binding and official/diagnostic publication state into the result.
- Modify `ai-scoring/app/services/evidence_extraction_service.py`: constrain performance reasons to observable behavior and stop asking the LLM to turn evidence gaps into deductions.
- Test `ai-scoring/tests/test_authoritative_rule_executor.py`.
- Test `ai-scoring/tests/test_pipeline_authoritative_payload.py` and `ai-scoring/tests/test_pipeline_payloads_rule_shadow.py`.
- Create `ai-scoring/tests/test_track_binding_gate.py`.
- Test `ai-scoring/tests/test_session_authoritative_callback.py` and `ai-scoring/tests/test_achievement_assessment.py`.

### Task 1: Deterministic single-attribution rule executor

- [ ] **Step 1: Write failing policy-v2 tests**

Add tests proving `final = min(performance, cap) - effective hard violation`, evidence-gap deductions are diagnostic-only, duplicate cause codes fail, and `maxScore = final + performanceGap + evidenceLimitedGap + hardViolation` for every observation.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_authoritative_rule_executor.py -q`

Expected: FAIL because `lossLedger`, `performanceGap`, `evidenceLimitedGap`, and score-effect filtering do not exist.

- [ ] **Step 3: Implement the minimal Decimal-based policy**

Keep existing compatibility fields (`baseScore`, `scoreCap`, `deductedScore`) but add `performanceScore`, `performanceGap`, `evidenceLimitedGap`, `effectiveHardPenalty`, `lossLedger`, and `scorePolicyVersion=score-policy-v2-single-attribution`. Reject out-of-range scores rather than silently clipping them.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all tests pass.

### Task 2: Legacy deduction migration at the payload boundary

- [ ] **Step 1: Write failing payload tests**

Add cases where `D-33-O04-evidence-gap` remains a diagnostic item with zero subtractive effect, an explicitly configured `penaltyType=hard_violation` event subtracts once, and an unclassified legacy candidate defaults to diagnostic-only.

- [ ] **Step 2: Run payload tests and verify RED**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_pipeline_authoritative_payload.py tests/test_pipeline_payloads_rule_shadow.py -q`

Expected: FAIL because current code subtracts every candidate.

- [ ] **Step 3: Implement deterministic classification**

Map evidence-gap IDs/types to `scoreEffect=diagnostic_only`, performance-gap to `scoreEffect=included_in_performance`, and only explicit event-backed hard violations to `scoreEffect=subtractive`. Pass only subtractive items to the executor; retain diagnostics under `diagnosticDeductions` for improvement guidance.

- [ ] **Step 4: Run payload tests and verify GREEN**

Run the command from Step 2. Expected: all tests pass and the legacy missing-proof example no longer removes points twice.

### Task 3: Track binding and official-publication gate

- [ ] **Step 1: Write failing gate tests**

Cover missing track, a plain track name without confirmation, valid `user_selected` binding, and `diagnostic_override` allowed only when `publishOfficialScore=false`.

- [ ] **Step 2: Run gate tests and verify RED**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_track_binding_gate.py -q`

Expected: FAIL because the gate module and request fields do not exist.

- [ ] **Step 3: Implement binding validation and router rejection**

Return `accepted=false`, `message=track_confirmation_required` before a background task is queued for invalid official requests. Include the normalized binding in the scoring fingerprint inputs and callback metadata.

- [ ] **Step 4: Run gate tests and verify GREEN**

Run the command from Step 2. Expected: all tests pass.

### Task 4: Separate performance language from evidence language

- [ ] **Step 1: Write failing extraction-prompt tests**

Require the prompt to forbid external-evidence absence in `achievementReason`, forbid evidence-gap candidates from becoming subtractive deductions, and require hard violations to include an event fact and rule code.

- [ ] **Step 2: Run extraction tests and verify RED**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_achievement_assessment.py -q`

Expected: FAIL on the new boundary language.

- [ ] **Step 3: Implement prompt and normalization safeguards**

Rename the internal semantic output to performance while keeping old achievement aliases for backward compatibility. If a performance reason contains only missing external evidence semantics, move it to evidence explanation and mark the performance assessment for review instead of reducing performance again.

- [ ] **Step 4: Run extraction tests and verify GREEN**

Run the command from Step 2. Expected: all tests pass.

### Task 5: Callback contract, regression suite, and video rerun

- [ ] **Step 1: Add failing callback tests**

Assert that policy-v2 results expose the single official score, ledger totals reconcile to the rule maximum, and diagnostic runs cannot claim `structured_rule_engine` official authority.

- [ ] **Step 2: Run callback tests and verify RED**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_session_authoritative_callback.py -q`

- [ ] **Step 3: Implement callback metadata and publication status**

Emit `scorePolicyVersion`, `lossLedger`, `diagnosticDeductions`, `competitionBinding`, and `publishOfficialScore`. For diagnostics use `scoreAuthority=diagnostic_rule_engine` and never label the score official.

- [ ] **Step 4: Run the complete affected test suite**

Run: `cd ai-scoring && ./.venv/bin/python -m pytest tests/test_authoritative_rule_executor.py tests/test_pipeline_authoritative_payload.py tests/test_pipeline_payloads_rule_shadow.py tests/test_track_binding_gate.py tests/test_achievement_assessment.py tests/test_session_authoritative_callback.py -q`

Expected: zero failures.

- [ ] **Step 5: Restart the Python service and run the supplied video**

Run the video with `selectionSource=diagnostic_override` and `publishOfficialScore=false` if the actual competition binding is still unknown. Use the existing “商贸赛道” only as a labeled regression assumption, never as a user-facing official result.

- [ ] **Step 6: Verify the rerun artifact**

Check: one score authority, no evidence-gap subtractive deductions, ledger equality within 0.01, rule/binding fingerprint present, and diagnostic status clearly set. If the real track is confirmed before this step, rerun officially with that binding instead.

## Self-review

- Spec coverage: single attribution, three loss types, conservative recovery language, track gate, deterministic replay, and non-official diagnostic rerun are all assigned to tasks.
- Placeholder scan: no deferred implementation placeholders are present.
- Type consistency: Python uses `performanceScore` as the new canonical name while preserving `baseScore`/achievement aliases only at compatibility boundaries.
