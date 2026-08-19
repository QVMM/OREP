# Local Diarization Without OSS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the OSS-backed recorded-ASR diarization path with local, complete-recording speaker diarization while retaining direct cloud WebSocket transcription for both uploads and online meetings.

**Architecture:** A local sherpa-onnx adapter returns score-free speaker turns from the complete 16 kHz WAV. Cloud ASR and local diarization execute concurrently, then a deterministic overlap reconciler applies global speaker labels to unchanged ASR segments. Model assets are provisioned before service startup and never downloaded by request handling.

**Tech Stack:** Python 3.14, sherpa-onnx 1.13.4, ONNX models, DashScope WebSocket ASR, pytest, Spring Boot.

---

## Task 1: Local diarization contract

**Files:**
- Create: `ai-scoring/app/services/media_evidence/local_diarization.py`
- Test: `ai-scoring/tests/test_local_diarization.py`

- [x] Write a failing test for model validation, 16 kHz mono loading, unknown speaker count, sorted turns and named failures.
- [x] Run `.venv/bin/pytest -q tests/test_local_diarization.py` and confirm RED.
- [x] Implement an injectable sherpa-onnx adapter without importing sherpa at module import time.
- [x] Require local model files and never download inside the service.
- [x] Run the focused test and confirm GREEN.

## Task 2: ASR/diarization reconciliation

**Files:**
- Create: `ai-scoring/app/services/media_evidence/asr_diarization_reconciler.py`
- Test: `ai-scoring/tests/test_asr_diarization_reconciler.py`

- [x] Write failing tests for majority overlap, ambiguous overlap, no overlap, unchanged text/timestamps and no score fields.
- [x] Run the tests and confirm RED.
- [x] Implement deterministic millisecond overlap assignment with 35% coverage and 60% dominance gates.
- [x] Run the tests and confirm GREEN.

## Task 3: Main-flow replacement and bounded concurrency

**Files:**
- Modify: `ai-scoring/app/config.py`
- Modify: `ai-scoring/app/services/pipeline_service.py`
- Modify: `ai-scoring/requirements.txt`
- Modify: `ai-scoring/tests/test_final_asr_pipeline_selection.py`

- [x] Write failing tests proving OSS is not selected, direct cloud ASR and local diarization overlap, and both source types share the same finalizer.
- [x] Confirm the tests fail against the OSS-backed selector.
- [x] Add local model configuration and one-process concurrency control.
- [x] Execute ASR and diarization concurrently inside the audio branch; preserve existing audio/video parallelism.
- [x] Remove `oss2` and all required `TEMP_AUDIO_OSS_*` production settings.
- [x] Run pipeline, callback and media-evidence regressions.

## Task 4: Deployment assets

**Files:**
- Create: `ai-scoring/scripts/setup_local_diarization_models.sh`
- Modify: `ai-scoring/.gitignore` or repository ignore rules as applicable.
- Test: `ai-scoring/tests/test_local_diarization_assets.py`

- [x] Validate fixed official URLs, expected filenames and SHA256 output during installation.
- [x] Implement an idempotent setup script that downloads to a temporary file, validates ONNX files and installs them.
- [x] Add `sherpa-onnx==1.13.4` to requirements.
- [x] Run shell syntax, idempotency and model-load checks.

## Task 5: Real video verification

**Input:** `/Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4`

- [x] Verify the input has one AAC audio track and record duration/size.
- [x] Install the locked local runtime and model assets.
- [x] Run the local diarization calibration on a 10-minute extracted clip.
- [x] Run complete-recording diarization and record elapsed time, turn count, speaker count and duration totals.
- [x] Run the full scoring pipeline using the real new-generation-information-technology track name.
- [x] Confirm callback/report persistence and inspect speaker evidence without exposing hidden scores.

## Task 6: Regression and handoff

- [x] Run the complete scoring-related Python suite (281 passed; 5 removed-PPT-module tests excluded).
- [x] Run `mvn test` (242 passed before the additional unresolved-bucket test; targeted speaker suite passed after it).
- [x] Run the user frontend production build.
- [x] Scan production paths for OSS dependencies and hidden speaker scores.
- [x] Write a real-video checkpoint report separating proven timings from estimates and listing the first-run compatibility failure exactly.
