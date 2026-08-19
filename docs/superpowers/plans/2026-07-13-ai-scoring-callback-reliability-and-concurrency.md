# AI Scoring Callback Reliability and Concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make uploaded-video scoring callbacks recoverable and type-safe, then reduce long-video processing latency through bounded concurrency without reducing analysis content.

**Architecture:** Normalize the Python callback payload at its outbound boundary, send it through a business-aware retrying callback client, and enforce a monotonic terminal-state policy in Java. Run ASR chunks and visual batches through bounded thread pools, retain every input, and merge results deterministically by original index.

**Tech Stack:** Python 3, pytest, asyncio/httpx, concurrent.futures, Java 21, Spring Boot, JUnit 5, Mockito, MySQL.

---

### Task 1: Callback Contract Normalization

**Files:**
- Modify: `ai-scoring/app/services/session_pipeline_service.py`
- Modify: `ai-scoring/tests/test_session_authoritative_callback.py`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerWebMvcTest.java`

- [ ] Add a failing Python test whose deduction contains dictionary-valued `requiredFix`.
- [ ] Verify `_build_final_result` currently returns the dictionary and the test fails.
- [ ] Add callback text normalization so `requiredFix` and `acceptanceCriteria` are always strings while retaining title/action/criteria content.
- [ ] Run the focused Python contract tests and verify they pass.
- [ ] Add a Java MVC deserialization test using the normalized string contract and verify it passes.

### Task 2: Business-Aware Callback Retry

**Files:**
- Create: `ai-scoring/app/services/backend_callback_client.py`
- Create: `ai-scoring/tests/test_backend_callback_client.py`
- Modify: `ai-scoring/app/services/session_pipeline_service.py`

- [ ] Add failing async tests for HTTP errors, `code != 200`, retry success, and retry exhaustion.
- [ ] Verify the tests fail because no business-aware client exists.
- [ ] Implement `BackendCallbackClient.send` with HTTP plus JSON business-code validation and configurable attempts/backoff.
- [ ] Replace the local `notify` transport with the callback client.
- [ ] On completed-callback exhaustion, send a minimal `result_writeback_failed` callback and do not log success.
- [ ] Run focused callback tests and verify all cases pass.

### Task 3: Java Terminal-State Protection

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java`

- [ ] Add failing tests proving completed and failed sessions ignore scoring progress.
- [ ] Add a failing test proving progress percent cannot decrease.
- [ ] Add a test proving a completed callback may recover a failed session.
- [ ] Implement the smallest terminal guard and monotonic progress update.
- [ ] Run focused Java service tests and verify they pass.

### Task 4: Bounded ASR Chunk Concurrency

**Files:**
- Modify: `ai-scoring/app/config.py`
- Modify: `ai-scoring/app/services/asr_service.py`
- Create: `ai-scoring/tests/test_asr_concurrency.py`

- [ ] Add failing tests that create multiple short chunks and prove calls overlap while returned segments remain in source order.
- [ ] Add `ASR_CHUNK_MAX_WORKERS` with default 3.
- [ ] Export all chunks, execute recognition through a bounded thread pool, and merge by chunk index.
- [ ] Preserve per-chunk failure isolation and guaranteed cleanup.
- [ ] Run focused ASR tests and verify every chunk is represented in the call record.

### Task 5: Bounded Visual Batch Concurrency

**Files:**
- Modify: `ai-scoring/app/config.py`
- Modify: `ai-scoring/app/services/video_analysis_service.py`
- Modify: `ai-scoring/tests/test_video_analysis_sampling.py`

- [ ] Add a failing test proving multiple visual batches overlap.
- [ ] Assert output remains in frame order, token totals include every batch, and final progress equals total frames.
- [ ] Add `VIDEO_ANALYSIS_MAX_WORKERS` with default 3.
- [ ] Execute existing recovery-wrapped batches through a bounded thread pool and merge by start index.
- [ ] Run focused visual tests and verify all frames remain present.

### Task 6: Replay Session 26 and Verify

**Files:**
- Read: `ai-scoring/uploads/results/result_26.json`
- Runtime: Java service on port 8080 and Python service on port 8090

- [ ] Restart Java and Python with the verified code.
- [ ] Rebuild the final result from `result_26.json` and send one completed callback through the new callback client.
- [ ] Verify the callback returns HTTP 2xx and business `code=200`.
- [ ] Query MySQL and verify session26 is completed at 100% with a report ID.
- [ ] Verify the report contains 15 observations, 1 deduction and 15 evidence anchors.
- [ ] Verify the stored score equals the locally recomputed authoritative score.

### Task 7: Regression and Runtime Evidence

**Files:**
- Test: `ai-scoring/tests`
- Test: `backend/src/test/java`

- [ ] Run the focused Python callback/concurrency tests.
- [ ] Run the executable Python scoring test suite.
- [ ] Run `mvn test` for the Java backend.
- [ ] Confirm both services listen on their configured ports.
- [ ] Record session26 recovery evidence and the unchanged input counts in the final handoff.
