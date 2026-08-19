# Local LR-ASD Speaker Identification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Deploy the Chinese LR-ASD model locally and combine its audio-visual active-speaker evidence with the existing sherpa-onnx acoustic diarization for both uploaded videos and recorded online roadshows.

**Architecture:** Keep cloud ASR, local acoustic diarization, and local LR-ASD as separate evidence branches. Run them concurrently, then fuse LR-ASD face-track evidence into acoustic turns before assigning ASR text. LR-ASD runs in an isolated Python 3.11 runtime and communicates with the Python scoring service through a versioned JSON subprocess contract, so the existing Python 3.14 service and scoring engine remain unchanged.

**Tech Stack:** Python 3.14 scoring service, Python 3.11 isolated worker, LR-ASD pinned at commit `1b6dcd2d8fc2895683de6508ec6294ec47d388ca`, PyTorch, OpenCV YuNet/SFace, FFmpeg, pytest, sherpa-onnx.

**Implementation status:** Completed on 2026-07-14. The real 55-minute video passed in conservative production mode; exact measurements, limitations, and pre-existing unrelated test-collection failures are recorded in `docs/testing/lr-asd-real-video-validation.md`.

---

## Boundaries and invariants

- LR-ASD produces evidence only. It must never emit or alter score fields.
- Raw video never leaves the local deployment. No OSS, public URL, or video cloud API is introduced.
- Cloud ASR continues to receive the existing audio stream only.
- A visual identity is anonymous and session-local. It is not matched against an external face database.
- Audio-only evidence is retained whenever the face is hidden or the LR-ASD worker is unavailable.
- A low-confidence audio-visual result must not overwrite a stable acoustic assignment.
- Uploaded videos and online-roadshow recordings share the same terminal evidence function.
- The pipeline must report explicit `completed`, `partial`, `unavailable`, or `failed` states; it must not invent a speaker.

## File map

- Create `app/services/media_evidence/active_speaker_contract.py`: validate and normalize worker JSON.
- Create `app/services/media_evidence/active_speaker_fusion.py`: merge visual identities with acoustic turns.
- Create `app/services/media_evidence/lr_asd_client.py`: bounded subprocess client and failure taxonomy.
- Create `scripts/lr_asd_worker.py`: isolated LR-ASD inference entry point.
- Create `scripts/setup_lr_asd_runtime.sh`: pinned, repeatable local installation.
- Modify `app/config.py`: LR-ASD feature flag, paths, timeout, concurrency, and thresholds.
- Modify `app/services/pipeline_service.py`: start LR-ASD beside ASR and acoustic diarization and fuse results.
- Modify `app/services/media_evidence/asr_diarization_reconciler.py`: preserve audio-visual verification metadata on transcript segments.
- Modify `requirements.txt`: no PyTorch additions; document that LR-ASD lives in its isolated runtime.
- Create `tests/test_active_speaker_contract.py`.
- Create `tests/test_active_speaker_fusion.py`.
- Create `tests/test_lr_asd_client.py`.
- Modify `tests/test_final_asr_pipeline_selection.py`.
- Create `tests/test_lr_asd_worker_smoke.py`.
- Create `docs/testing/lr-asd-real-video-validation.md`: exact real-video acceptance record.

### Task 1: Versioned active-speaker output contract

**Files:**
- Create: `tests/test_active_speaker_contract.py`
- Create: `app/services/media_evidence/active_speaker_contract.py`

- [x] **Step 1: Write failing contract tests**

```python
def test_normalizes_valid_lr_asd_result():
    result = normalize_active_speaker_result({
        "contractVersion": "lr-asd-evidence-v1",
        "status": "completed",
        "faceTracks": [{"faceTrackId": "FACE_0", "startMs": 0, "endMs": 1000}],
        "activeIntervals": [{
            "faceTrackId": "FACE_0", "startMs": 100, "endMs": 900,
            "activeProbability": 0.91, "visibleProbability": 0.98,
        }],
    })
    assert result["source"] == "local_lr_asd"
    assert result["activeIntervals"][0]["activeProbability"] == 0.91

def test_rejects_score_fields():
    with pytest.raises(ActiveSpeakerContractError, match="score_field_forbidden"):
        normalize_active_speaker_result({"overall_score": 99})
```

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_active_speaker_contract.py -q`

Expected: collection fails because `active_speaker_contract` does not exist.

- [x] **Step 3: Implement strict normalization**

Implement `normalize_active_speaker_result(value: dict) -> dict` with:

- contract version equality check;
- allowed status validation;
- integer, monotonic timestamps;
- probabilities clamped to `[0, 1]` only after finite-number validation;
- deterministic sorting;
- recursive rejection of keys containing `score` except `activeProbability`;
- source fixed to `local_lr_asd`.

- [x] **Step 4: Run tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_active_speaker_contract.py -q`

Expected: all contract tests pass.

### Task 2: Audio-visual and acoustic turn fusion

**Files:**
- Create: `tests/test_active_speaker_fusion.py`
- Create: `app/services/media_evidence/active_speaker_fusion.py`

- [x] **Step 1: Write failing fusion tests**

```python
def test_merges_two_acoustic_clusters_verified_as_same_visible_person():
    fused = fuse_active_speaker_evidence(diarization, active_speaker)
    assert fused["detectedSpeakerCount"] == 1
    assert {turn["rawSpeakerId"] for turn in fused["turns"]} == {"SPEAKER_0"}
    assert all(turn["speakerVerification"] == "AUDIO_VISUAL" for turn in fused["turns"])

def test_does_not_merge_when_visual_votes_are_ambiguous():
    fused = fuse_active_speaker_evidence(diarization, ambiguous_active_speaker)
    assert fused["detectedSpeakerCount"] == 2
    assert fused["audioVisualStatus"] == "partial"

def test_preserves_audio_turns_when_face_is_not_visible():
    fused = fuse_active_speaker_evidence(diarization, {"status": "unavailable"})
    assert fused["turns"] == diarization["turns"]
```

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_active_speaker_fusion.py -q`

Expected: collection fails because `active_speaker_fusion` does not exist.

- [x] **Step 3: Implement deterministic evidence fusion**

For every acoustic turn:

1. Compute temporal overlap with active face intervals.
2. Weight overlap by `activeProbability * visibleProbability`.
3. Require configured minimum coverage and winner dominance.
4. Vote from acoustic cluster to anonymous face identity across the complete recording.
5. Merge acoustic clusters only when both independently map to the same face identity above the confidence threshold.
6. Preserve `sourceClusterId`, add `faceTrackId`, `speakerVerification`, `identityConfidence`, and `activeSpeakerSource`.
7. Renumber stable final identities by first verified appearance.

- [x] **Step 4: Run tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_active_speaker_fusion.py -q`

Expected: all fusion tests pass.

### Task 3: Isolated LR-ASD subprocess client

**Files:**
- Create: `tests/test_lr_asd_client.py`
- Create: `app/services/media_evidence/lr_asd_client.py`

- [x] **Step 1: Write failing client tests**

```python
def test_client_sends_only_local_paths_and_parses_stdout(tmp_path):
    client = LocalLrAsdClient(..., runner=fake_runner)
    result = client.analyze(video_path, wav_path)
    assert result["source"] == "local_lr_asd"
    assert fake_runner.command[-2:] == [str(video_path), str(wav_path)]

def test_timeout_is_named_failure():
    with pytest.raises(LocalLrAsdError, match="lr_asd_timeout"):
        client.analyze(video_path, wav_path)

def test_non_json_output_is_named_failure():
    with pytest.raises(LocalLrAsdError, match="lr_asd_invalid_output"):
        client.analyze(video_path, wav_path)
```

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_lr_asd_client.py -q`

Expected: collection fails because `lr_asd_client` does not exist.

- [x] **Step 3: Implement bounded client**

The client must:

- validate local video, WAV, worker, Python executable, model repository, and weight paths;
- call `subprocess.run` without `shell=True`;
- enforce a hard timeout;
- capture stdout and stderr separately;
- parse one JSON object from stdout;
- normalize it through Task 1;
- return named errors without leaking secrets or command environment.

- [x] **Step 4: Run tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_lr_asd_client.py -q`

Expected: all client tests pass.

### Task 4: Reproducible local LR-ASD runtime

**Files:**
- Create: `scripts/setup_lr_asd_runtime.sh`
- Create: `scripts/lr_asd_worker.py`
- Create: `tests/test_lr_asd_worker_smoke.py`

- [x] **Step 1: Write failing worker smoke tests**

Test device selection, JSON-only stdout, missing-file error contract, deterministic interval sorting, and checkpoint-key loading without running a full video.

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_lr_asd_worker_smoke.py -q`

Expected: worker module does not exist.

- [x] **Step 3: Implement installer**

The installer must:

- clone the official repository at commit `1b6dcd2d8fc2895683de6508ec6294ec47d388ca`;
- verify `pretrain_AVA.model` SHA-256 `85e6c77fc981595234790d1e128ebb60352d37726b2445e0ef8891e2512fe9e3`;
- create a Python 3.11 virtual environment under `models/active-speaker/lr-asd-runtime/.venv`;
- install pinned compatible PyTorch, OpenCV, SciPy, scikit-learn, pandas, tqdm, and python-speech-features packages;
- download official OpenCV YuNet and SFace ONNX weights and verify their checksums;
- remain idempotent and fail before replacing a working installation.

- [x] **Step 4: Implement worker**

The worker must:

- select CUDA, then MPS, then CPU;
- load LR-ASD without importing the CUDA-hardcoded training wrapper;
- use YuNet for face detection and SFace for session-local identity embeddings;
- track faces over time with IoU, landmarks, and embedding similarity;
- use audio energy to skip silence and bound compute;
- create 25 fps face clips only inside candidate speech windows;
- infer active-speaking probability in bounded chunks;
- output anonymous face tracks and active intervals under `lr-asd-evidence-v1`;
- send diagnostics to stderr and JSON only to stdout.

- [x] **Step 5: Run worker tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_lr_asd_worker_smoke.py -q`

Expected: all worker smoke tests pass.

### Task 5: Shared upload and online-recording pipeline integration

**Files:**
- Modify: `app/config.py`
- Modify: `app/services/pipeline_service.py`
- Modify: `app/services/media_evidence/asr_diarization_reconciler.py`
- Modify: `tests/test_final_asr_pipeline_selection.py`

- [x] **Step 1: Write failing pipeline tests**

Add tests proving:

- uploaded video passes its video path into LR-ASD;
- dual-source online recording passes camera video, never screen-share video;
- cloud ASR, acoustic diarization, and LR-ASD overlap in wall-clock time;
- LR-ASD failure degrades explicitly to audio-only evidence and does not fail scoring;
- audio-only uploads never launch LR-ASD;
- transcript segments retain `faceTrackId`, `speakerVerification`, and `identityConfidence`.

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_final_asr_pipeline_selection.py -q`

Expected: new assertions fail because no LR-ASD branch exists.

- [x] **Step 3: Add settings**

Add:

- `LOCAL_ACTIVE_SPEAKER_ENABLED`;
- runtime Python, worker, repository, model weight, YuNet, and SFace paths;
- timeout and maximum concurrency;
- minimum visible probability, active probability, temporal coverage, and vote dominance;
- `LOCAL_ACTIVE_SPEAKER_REQUIRED=false` so evidence failure does not invalidate scoring.

- [x] **Step 4: Integrate shared terminal branch**

Change `_run_authoritative_asr` to accept `video_path: str | None`. When a camera/video path exists and LR-ASD is enabled, run three branches concurrently:

```python
{
    "cloud_asr": ...,
    "local_diarization": ...,
    "local_active_speaker": ...,
}
```

Fuse active-speaker evidence into diarization before ASR reconciliation. Pass the uploaded video path in the single-source pipeline and camera path in the dual-source pipeline.

- [x] **Step 5: Run targeted tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py tests/test_lr_asd_client.py tests/test_final_asr_pipeline_selection.py -q`

Expected: all targeted tests pass.

### Task 6: Install and verify the actual model

**Files:**
- Runtime directory: `models/active-speaker/lr-asd-runtime`

- [x] **Step 1: Run repeatable installation**

Run: `bash scripts/setup_lr_asd_runtime.sh`

Expected: `lr_asd_runtime_ready` with commit, model hashes, Python version, and selected device.

- [x] **Step 2: Verify idempotency**

Run the same command again.

Expected: it exits successfully without downloading or recreating the environment.

- [x] **Step 3: Run model-load smoke test**

Run the worker in `--health-check` mode.

Expected JSON includes `status=ready`, `model=LR-ASD`, pinned commit, and selected device.

### Task 7: Real-video validation

**Files:**
- Test input: `/Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4`
- Create: `docs/testing/lr-asd-real-video-validation.md`
- Generated result: `uploads/results/result_lr_asd_e9df_20260714.json`

- [x] **Step 1: Run a representative clip test**

Use clips covering single presenter, multiple people on stage, walking/turning, and foreground occlusion. Record face count, active-speaker intervals, runtime, peak memory, and failure states.

- [x] **Step 2: Inspect representative frames**

Verify that the selected active face corresponds to visible mouth motion at sampled timestamps. Reject a model threshold if it systematically selects seated or silent people.

- [x] **Step 3: Run complete-video terminal evidence test**

Run the shared terminal evidence function on the complete video without invoking the scoring LLM. Compare:

- original acoustic clusters;
- stable acoustic clusters;
- audio-visually verified identities;
- merged duplicate clusters;
- unknown and overlap segments;
- LR-ASD duration and total wall-clock duration.

- [x] **Step 4: Write the acceptance record**

The record must include exact commands, hashes, durations, counts, observed mistakes, confidence thresholds, and whether full rollout is accepted or remains in shadow mode.

### Task 8: Regression and completion verification

**Files:**
- Modify documentation only if verification exposes a mismatch.

- [x] **Step 1: Run media-evidence regression suite**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_local_diarization.py \
  tests/test_asr_diarization_reconciler.py \
  tests/test_active_speaker_contract.py \
  tests/test_active_speaker_fusion.py \
  tests/test_lr_asd_client.py \
  tests/test_lr_asd_worker_smoke.py \
  tests/test_final_asr_pipeline_selection.py \
  tests/test_media_evidence_speakers.py \
  tests/test_live_evidence_finalizer.py -q
```

Expected: zero failures.

- [x] **Step 2: Run full Python test suite**

Run: `.venv/bin/python -m pytest tests -q`

Expected: zero new failures. Any pre-existing unrelated failure must be recorded with its exact test name and reproduced without the LR-ASD change.

- [x] **Step 3: Verify privacy and score separation**

Search generated evidence for public URLs, OSS paths, API secrets, and score fields. Confirm the LR-ASD branch contains none.

- [x] **Step 4: Verify requirements against this plan**

Confirm local deployment, no OSS, shared upload/online terminal flow, explicit degradation, real-video evidence, concurrency, and unchanged scoring authority.

## Checkpoints

1. Baseline and architecture mapped.
2. Contract, fusion, and client tests green.
3. LR-ASD runtime installed and model-load health check green.
4. Shared upload/online terminal path tests green.
5. Representative real-video clip accepted.
6. Complete real-video evidence run measured.
7. Regression and privacy verification complete.
