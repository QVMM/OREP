# Local 3D-Speaker Authoritative Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the public LR-ASD/SFace identity chain with a pinned, local 3D-Speaker audio-visual finalization path shared by uploaded videos and completed live roadshows, while preserving FunASR text and the official scoring result.

**Architecture:** A dedicated local runtime executes the official 3D-Speaker video recipe inside a per-job workspace and returns normalized RTTM turns. Python aligns those turns to the existing ASR timeline, anchors only explicit numbered introductions, freezes a monotonic speaker-attribution revision, and sends it through the existing Java callback contract. Live labels remain provisional until the same final provider processes the complete local recording.

**Tech Stack:** Python 3.11, pytest, ModelScope 3D-Speaker pinned at `065629c313eaf1a01c65c640c46d77e61e9607b4`, CAM++/TalkNet/IR101 ONNX, FFmpeg, Spring Boot/MyBatis, Vue 3.

---

## File Structure

**Create:**

- `ai-scoring/app/services/media_evidence/three_d_speaker_contract.py` — strict provider result and RTTM normalization.
- `ai-scoring/app/services/media_evidence/three_d_speaker_client.py` — safe bounded local subprocess API.
- `ai-scoring/app/services/media_evidence/final_speaker_attribution.py` — transcript alignment, explicit slot anchors and final snapshot.
- `ai-scoring/scripts/three_d_speaker_worker.py` — per-job official recipe wrapper and resource receipt.
- `ai-scoring/scripts/setup_3d_speaker_runtime.sh` — pinned runtime and model installation.
- `ai-scoring/scripts/validate_3d_speaker_video.py` — real-video accuracy/resource gate.
- `ai-scoring/tests/test_three_d_speaker_contract.py`.
- `ai-scoring/tests/test_three_d_speaker_client.py`.
- `ai-scoring/tests/test_final_speaker_attribution.py`.
- `ai-scoring/tests/test_three_d_speaker_pipeline_selection.py`.
- `docs/superpowers/reports/2026-07-15-3d-speaker-final-verification.md`.

**Modify:**

- `ai-scoring/app/config.py` — local provider paths, timeout, capacity and shadow/public flags.
- `ai-scoring/app/services/pipeline_service.py` — run final ASR and local multimodal diarization concurrently for upload and live finalization.
- `ai-scoring/app/services/media_evidence/speaker_attribution_shadow.py` — accept monotonic revisions and never materialize raw acoustic clusters.
- `ai-scoring/app/services/media_evidence/active_speaker_contract.py` — retain old evidence as diagnostics only.
- Existing Java callback/report code only if the normalized provider field is not already persisted by the current speaker-attribution contract.

## Task 1: Strict 3D-Speaker Contract

- [ ] **Step 1: Write failing RTTM parser tests**

Test valid lines, comments, adjacent same-speaker coalescing, non-monotonic input sorting, negative/NaN/overflow rejection, malicious speaker labels, and empty output.

- [ ] **Step 2: Verify red**

Run:

```bash
cd ai-scoring && .venv/bin/pytest -q tests/test_three_d_speaker_contract.py
```

Expected: collection failure because `three_d_speaker_contract` does not exist.

- [ ] **Step 3: Implement normalization**

Expose:

```python
parse_rttm(text: str, *, duration_ms: int) -> list[dict]
normalize_three_d_speaker_result(raw: dict, *, duration_ms: int) -> dict
```

Only `SPEAKER` RTTM records are accepted. Provider labels become deterministic `3DSPK_<label>` values; confidence is omitted when not supplied.

- [ ] **Step 4: Verify green**

Run the focused tests and `tests/test_active_speaker_contract.py`.

## Task 2: Safe Local Client And Worker Boundary

- [ ] **Step 1: Write failing client tests**

Test missing runtime, local-file validation, argument-array invocation, timeout termination, nonzero exit, invalid JSON, resource diagnostics and no `shell=True`.

- [ ] **Step 2: Verify red**

Run `pytest -q tests/test_three_d_speaker_client.py`; require failure from missing client.

- [ ] **Step 3: Implement client**

Expose `LocalThreeDSpeakerClient.analyze(video_path, wav_path, duration_ms)` and named `LocalThreeDSpeakerError` codes. Inject the subprocess runner for tests.

- [ ] **Step 4: Write worker protocol tests**

Test health check JSON, per-job directory isolation, generated `video.list/wav.list`, RTTM discovery, cleanup on success/failure and peak RSS receipt.

- [ ] **Step 5: Implement worker**

The worker runs the pinned repository with `bash run_video.sh --stage 3 --stop_stage 5 --nj 1`, pre-populates normalized video/WAV files, and reads exactly one generated RTTM. No business path or transcript is printed to stderr.

- [ ] **Step 6: Verify green**

Run client and worker smoke tests plus `python -m compileall` for the new modules.

## Task 3: Transcript Alignment And Explicit Identity Anchors

- [ ] **Step 1: Write failing alignment tests**

Cover dominant-overlap assignment, ambiguous overlap to `UNKNOWN`, audio-visual cluster to anonymous person, four explicit self-introductions to slots 1–4, duplicate/conflicting introductions, extra outsider cluster and revision propagation.

- [ ] **Step 2: Verify red**

Run `pytest -q tests/test_final_speaker_attribution.py`; require failure from missing builder.

- [ ] **Step 3: Implement final snapshot builder**

Expose:

```python
build_final_speaker_attribution(
    *, session_id, duration_ms, revision, asr_result,
    three_d_speaker_result, contestant_slots
) -> dict
```

Use the existing `SessionIdentityGraph`, transcript segment contract and snapshot normalizer. Never use face position or raw acoustic count as contestant identity.

- [ ] **Step 4: Verify green**

Run final attribution tests together with current shadow/contract/transcript suites.

## Task 4: Pipeline Selection, Concurrency And Safe Fallback

- [ ] **Step 1: Write failing pipeline tests**

Prove both upload and completed-live sources select the same local final provider; ASR and 3D-Speaker overlap in time; disabled mode launches no worker; provider failure retains all ASR text as `UNKNOWN`; old LR-ASD visual identities are never public final people.

- [ ] **Step 2: Verify red**

Run `pytest -q tests/test_three_d_speaker_pipeline_selection.py`; require the provider-selection assertion to fail.

- [ ] **Step 3: Add configuration**

Add explicit settings with safe defaults:

```text
LOCAL_3D_SPEAKER_ENABLED=false
LOCAL_3D_SPEAKER_PUBLICATION_ENABLED=false
LOCAL_3D_SPEAKER_RUNTIME_DIR=...
LOCAL_3D_SPEAKER_TIMEOUT_SECONDS=1800
LOCAL_3D_SPEAKER_MAX_CONCURRENCY=1
```

- [ ] **Step 4: Integrate bounded concurrent branch**

Start the local provider beside authoritative ASR after WAV creation. Fuse only after both complete. A local provider failure is evidence degradation, not scoring failure; callback remains completed with a final UNKNOWN attribution revision.

- [ ] **Step 5: Verify green**

Run final ASR selection, ASR concurrency, active-speaker fusion, shadow, callback payload and new pipeline tests.

## Task 5: Reproducible Runtime Setup

- [ ] **Step 1: Write setup manifest tests**

Static tests require the pinned commit, Apache notices, exact visual model SHA-256 values, Python/OS checks, local-only downloads, health check and no OSS/cloud upload configuration.

- [ ] **Step 2: Verify red**

Run the manifest test and require failure because the setup script is absent.

- [ ] **Step 3: Implement setup script**

Use `uv venv --python 3.11`, clone the pinned upstream commit, install a Mac/Linux-compatible lock, download the four ONNX files and CAM++ checkpoint, verify hashes, then execute worker `--health-check`.

- [ ] **Step 4: Install on the current Apple M4 machine**

Run:

```bash
cd ai-scoring && bash scripts/setup_3d_speaker_runtime.sh
```

Expected: local health JSON reports `platform=darwin-arm64`, `executionProvider=CPUExecutionProvider`, every model hash valid.

## Task 6: Real 55-Minute Video Gate

- [ ] **Step 1: Run provider without publication**

Use:

```bash
cd ai-scoring
.venv/bin/python scripts/validate_3d_speaker_video.py \
  --video /Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4 \
  --session-result uploads/results/result_26.json \
  --expected-visible-contestants 4 \
  --output uploads/results/result_3d_speaker_e9df_20260715.json
```

- [ ] **Step 2: Inspect objective gates**

Require completed status, four stable contestant clusters or an explicit outsider explanation, transcript coverage at least 85%, 0 duplicate slots, monotonic timeline, no out-of-range turns and peak RSS below the configured resource ceiling.

- [ ] **Step 3: Inspect sampled accuracy**

Verify all four opening introductions, each presenter change, ten deterministic middle timestamps and the ending. Record assigned/unknown/wrong counts; do not publish if wrong-speaker rate exceeds 10% on the sampled set.

- [ ] **Step 4: Persist only a passing revision**

If the gate passes, build revision 2+, replay the completed callback and verify score remains 49.5. If it fails, retain revision 1 UNKNOWN and save diagnostics only.

## Task 7: Java, API And Frontend Verification

- [ ] **Step 1: Database assertions**

Verify session revision, transcript row count, final flags, people count, unique slot constraints and unchanged report score directly from MySQL.

- [ ] **Step 2: Callback replay and terminal protection**

Replay the same revision and a lower revision; neither may duplicate rows or overwrite the newer final snapshot.

- [ ] **Step 3: Report API assertions**

Require report API transcript count equals final database segment count and exposes unknown/anonymous states honestly.

- [ ] **Step 4: Browser verification**

Open `/ai-score/report/26/why`, select人物转写, verify content, timestamps, speaker labels, seeking behavior and no invented eight-person summary.

- [ ] **Step 5: Regression suites**

Run focused Python media tests, Java target tests, frontend transcript tests and production build.

## Task 8: Resource And Concurrency Gate

- [ ] **Step 1: Record single-task resource profile**

Capture wall time, CPU time, peak RSS, output size and temporary disk high-water mark for the real video.

- [ ] **Step 2: Run bounded concurrency**

Run two short real clips through independent job directories. Require no file collision, no model download race, no cross-session RTTM and capacity timeout to be named.

- [ ] **Step 3: Online finalization simulation**

Feed the same completed recording through the live-finalization source adapter. Require byte-identical normalized turns and the same snapshot hash as upload mode.

## Task 9: Audit Report And Cutover

- [ ] **Step 1: Requirement-by-requirement audit**

For every design gate, cite command output, database row, API field, screenshot or diagnostic JSON. Missing evidence is a failed gate.

- [ ] **Step 2: Static safety scans**

Require no `overall_score/deducted_points/predicted_score` in the provider package, no `shell=True`, no OSS URL, no exported biometric vector and no public use of LR-ASD visual identity as final people.

- [ ] **Step 3: Write final report**

Write `docs/superpowers/reports/2026-07-15-3d-speaker-final-verification.md` with passed, failed, measured resources, limitations and publication decision.

- [ ] **Step 4: Final verification**

Run all scoped commands fresh. Only after zero required gaps call the goal complete.

