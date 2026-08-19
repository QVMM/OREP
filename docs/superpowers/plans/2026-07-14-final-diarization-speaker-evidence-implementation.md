# Final Diarization And Score-Free Speaker Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make upload video and online-meeting finalization use the same complete-recording Fun-ASR diarization path, persist global speaker labels in Java, and remove the hidden per-speaker numeric scoring system.

**Architecture:** A private temporary-object boundary exposes only a derived WAV through a short-lived signed URL. A single recorded-ASR gateway turns the provider result into the existing scoring transcript shape and becomes authoritative for both sources when explicitly enabled. Speaker post-processing emits identity evidence only; the 42-track structured rule engine remains the sole official score authority.

**Tech Stack:** Python 3.14, DashScope SDK, Alibaba OSS Python SDK, pytest, Spring Boot/MyBatis-Plus, JUnit/Mockito, Vue 3.

**Implementation status (2026-07-14):** Tasks 1–6 are code-complete and the scoped regression gates in Task 7 pass. Production enablement remains gated on private OSS credentials and real 60-minute validation; see [checkpoint 4D](../reports/2026-07-14-final-diarization-checkpoint-4d.md).

---

## File Structure

**Create:**

- `ai-scoring/app/services/media_evidence/temporary_audio_object.py` — private OSS upload, signed URL, guaranteed deletion and redacted audit.
- `ai-scoring/app/services/media_evidence/recorded_asr_gateway.py` — one authoritative final-ASR entry point and legacy transcript adapter.
- `ai-scoring/app/services/speaker_evidence_service.py` — score-free aggregation and optional role/name evidence.
- `ai-scoring/tests/test_temporary_audio_object.py`.
- `ai-scoring/tests/test_recorded_asr_gateway.py`.
- `ai-scoring/tests/test_speaker_evidence_service.py`.
- `ai-scoring/tests/test_final_asr_pipeline_selection.py`.
- `backend/src/test/java/com/orep/backend/service/AiScoreSpeakerIdentityCallbackTest.java`.

**Modify:**

- `ai-scoring/requirements.txt` — add OSS SDK.
- `ai-scoring/app/config.py` — strict feature flag and OSS settings.
- `ai-scoring/app/services/pipeline_service.py` — select authoritative final ASR, remove speaker scoring call, parallelize audio/video branches.
- `ai-scoring/app/services/session_pipeline_service.py` — include score-free speaker evidence in final callback.
- `ai-scoring/app/services/pipeline_payloads.py` — stop legacy `speakers` score payload.
- `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java` — add speaker evidence DTO.
- `backend/src/main/java/com/orep/backend/service/AiScoreSpeakerIdentityService.java` — upsert AUTO mappings without overwriting human decisions.
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` — persist transcript and identity evidence in the completed transaction.
- `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java` — stop consuming legacy speaker dimensions in ability profiles.

## Task 1: Private Temporary Audio Object

**Tests first:**

- [ ] Create a fake object client test proving only an existing `.wav` is accepted.
- [ ] Verify the test fails because `temporary_audio_object` does not exist.
- [ ] Test object keys contain a UUID but no session/project/name input.
- [ ] Test signed URL is yielded and delete runs after success.
- [ ] Test delete still runs when the caller raises.
- [ ] Test delete retries a bounded number of times and audit data contains only an object-key hash.
- [ ] Implement `TemporaryAudioObjectStore`, `temporary_audio_url()` and lazy `OssTemporaryAudioClient`.
- [ ] Run `.venv/bin/pytest -q tests/test_temporary_audio_object.py` and require green.

## Task 2: Authoritative Recorded ASR Gateway

**Tests first:**

- [ ] Test the gateway calls temporary object creation once and calls `DashScopeRecordedAsrProvider.transcribe_url` with `diarization_enabled` already enforced by that provider.
- [ ] Test provider `speaker_id=2` becomes legacy `speaker="SPEAKER_2"` while preserving `rawSpeakerId`.
- [ ] Test timestamps convert from milliseconds to seconds exactly once.
- [ ] Test no speaker IDs produces `diarizationStatus="evidence_incomplete"`, never `SPEAKER_0`.
- [ ] Test provider failure propagates a named final-ASR error and never invokes legacy ASR fallback when strict mode is enabled.
- [ ] Implement the gateway and run its tests with the existing recorded-ASR parser tests.

## Task 3: Main Pipeline Selection And Concurrency

**Tests first:**

- [ ] Test `FINAL_RECORDED_DIARIZATION_ENABLED=false` calls no temporary-object or recorded provider code.
- [ ] Test the enabled upload-video path calls the final gateway and does not prefer realtime transcript.
- [ ] Test the enabled online-meeting path also calls the same gateway with the complete WAV.
- [ ] Test a provider error stops the terminal pipeline instead of assigning all segments to one speaker.
- [ ] Test ASR and video branch functions overlap using barriers/events and results retain chronological order.
- [ ] Add configuration validation and a provider factory using `Transcription.async_call`, `Transcription.wait`, and bounded HTTP result download.
- [ ] Replace `_run_asr_with_realtime_preference` selection with `_run_authoritative_asr`.
- [ ] Execute ASR/speech and video analysis with a bounded executor after WAV creation; fusion still waits for both.
- [ ] Apply the same ASR selection to dual-source roadshows.
- [ ] Run pipeline selection, ASR, video payload and callback regression tests.

## Task 4: Remove Hidden Speaker Numeric Scoring

**Tests first:**

- [ ] Test the score-free service groups only by provider raw speaker labels and never invents additional speakers from transition phrases.
- [ ] Test unknown speaker remains `rawSpeakerId=null` and `displayName="发言人待确认"`.
- [ ] Test output contains no `dimensions`, `score`, `speaker_scores` or default 60 values at any nesting level.
- [ ] Test duration, quotes and time ranges remain available.
- [ ] Replace pipeline `_run_speaker_analysis` with score-free evidence construction.
- [ ] Rename result field to `speaker_evidence` and remove legacy callback `speakers` numeric payload.
- [ ] Stop PDF personal-training score rendering unless a future explicit diagnostic contract exists.
- [ ] Add a static regression scan forbidding `result["speaker_scores"]` in the production scoring pipeline.

## Task 5: Java Callback And Identity Persistence

**Tests first:**

- [ ] Add a callback test where two raw speaker labels create two AUTO identity rows.
- [ ] Add a replay test proving the same callback does not duplicate identities.
- [ ] Add a human-protection test proving CONFIRMED/REJECTED rows are not overwritten by AUTO evidence.
- [ ] Extend `PipelineFinalResult` with `speakerEvidence` user-safe fields.
- [ ] Add `upsertAutoEvidence(sessionId, evidence)` and invoke it after transcript replacement in the completed transaction.
- [ ] Keep raw labels immutable and expose the existing report mapping DTO.
- [ ] Run focused Java tests and then `mvn -q test`.

## Task 6: Stop Legacy Scores Affecting Ability Profiles

**Tests first:**

- [ ] Add a ProjectTeamService test proving legacy `dimensions_json` is ignored for new ability evidence.
- [ ] Replace personal numeric dimension consumption with non-scoring participation/role/quote evidence, or zero-weight context where a score is required by the old schema.
- [ ] Keep historical rows readable for audit and teacher reassignment but stop all new numeric writes.
- [ ] Verify official team score and report dimensions are unchanged.

## Task 7: Cross-Layer Verification

- [ ] Run all new Python tests plus media-evidence, ASR concurrency and session callback suites.
- [ ] Run the full Java test suite.
- [ ] Run frontend transcript tests and production build.
- [ ] Scan evidence and speaker production modules for forbidden official-score fields and hidden personal-score fields.
- [ ] Verify both new feature flags default to false and no credential or signed URL is logged.
- [ ] Write checkpoint 4 report with code-complete gates and clearly separate real OSS/DashScope/one-hour tests that cannot be claimed from mocks.

## Execution Checkpoints

1. **Checkpoint 4A:** Temporary object and recorded-ASR gateway green; no main-flow switch yet.
2. **Checkpoint 4B:** Upload and online terminal paths use the common gateway behind the strict flag; concurrency green.
3. **Checkpoint 4C:** Hidden speaker scoring removed; Java AUTO identity persistence and human protection green.
4. **Checkpoint 4D:** Full regressions green; production flags remain off until real credentials and long-run validation pass.
