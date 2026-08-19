# Unified Media Evidence Core And Upload Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared evidence contract, score-field firewall, deterministic snapshot, speaker-safe ASR normalization, limited-parallel evidence orchestrator, and an upload-video shadow package without changing the published score.

**Architecture:** Add a focused `media_evidence` Python package beneath the existing scoring service. Existing ASR, speech, video, and fusion results are adapted into a versioned `EvidencePackage`; a strict contract rejects score-bearing media outputs, freezes deterministic hashes, and records unavailable diarization instead of fabricating one speaker. The current scoring pipeline remains authoritative and the new package is produced only behind a disabled-by-default shadow flag in this checkpoint.

**Tech Stack:** Python 3.14, pytest, standard-library dataclasses/json/hashlib/concurrent.futures, DashScope SDK, existing FastAPI scoring service.

---

## File Structure

**Create:**

- `ai-scoring/app/services/media_evidence/__init__.py` — public exports for the package.
- `ai-scoring/app/services/media_evidence/contracts.py` — versioned evidence validation, score firewall, canonical JSON and snapshot hash.
- `ai-scoring/app/services/media_evidence/speaker_reconciliation.py` — ASR segment normalization that preserves unknown speakers and raw labels.
- `ai-scoring/app/services/media_evidence/orchestrator.py` — bounded parallel branch runner with deterministic output order.
- `ai-scoring/app/services/media_evidence/legacy_adapter.py` — converts current ASR/speech/video/fusion dictionaries to `media-evidence-v1`.
- `ai-scoring/app/services/media_evidence/shadow_store.py` — atomic local shadow snapshot persistence.
- `ai-scoring/app/services/media_evidence/dashscope_recorded.py` — offline Fun-ASR result parsing and injectable task client.
- `ai-scoring/tests/test_media_evidence_contracts.py`.
- `ai-scoring/tests/test_media_evidence_speakers.py`.
- `ai-scoring/tests/test_media_evidence_orchestrator.py`.
- `ai-scoring/tests/test_media_evidence_legacy_adapter.py`.
- `ai-scoring/tests/test_dashscope_recorded_asr.py`.

**Modify:**

- `ai-scoring/app/config.py` — disabled-by-default evidence shadow and offline ASR settings.
- `ai-scoring/app/services/pipeline_service.py` — write a shadow evidence package after evidence preparation and before official scoring.
- `ai-scoring/tests/test_pipeline_video_payload.py` — verify shadow mode does not alter official score payload fields.

## Task 1: Evidence Contract And Score Firewall

**Files:**

- Create: `ai-scoring/tests/test_media_evidence_contracts.py`
- Create: `ai-scoring/app/services/media_evidence/__init__.py`
- Create: `ai-scoring/app/services/media_evidence/contracts.py`

- [ ] **Step 1: Write failing contract tests**

Cover these exact behaviors:

```python
def test_finalize_package_rejects_nested_official_score_fields():
    package = minimal_package()
    package["visualEvidence"] = [{"text": "画面", "deductedPoints": 2}]
    with pytest.raises(EvidenceContractError, match="forbidden_score_field"):
        finalize_evidence_package(package)


def test_snapshot_hash_ignores_runtime_metrics_but_changes_with_evidence():
    first = finalize_evidence_package(minimal_package(processingMetrics={"durationMs": 10}))
    second = finalize_evidence_package(minimal_package(processingMetrics={"durationMs": 999}))
    changed = minimal_package()
    changed["transcriptSegments"][0]["text"] = "不同证据"
    third = finalize_evidence_package(changed)
    assert first["snapshotHash"] == second["snapshotHash"]
    assert first["snapshotHash"] != third["snapshotHash"]


def test_final_package_requires_monotonic_timestamps():
    package = minimal_package()
    package["transcriptSegments"][0]["startMs"] = 2000
    package["transcriptSegments"][0]["endMs"] = 1000
    with pytest.raises(EvidenceContractError, match="invalid_time_range"):
        finalize_evidence_package(package)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd ai-scoring
.venv/bin/python -m pytest -q tests/test_media_evidence_contracts.py
```

Expected: import failure because `media_evidence.contracts` does not exist.

- [ ] **Step 3: Implement minimal contract**

Implement:

```python
import copy
import hashlib
import json
import re

CONTRACT_VERSION = "media-evidence-v1"
FORBIDDEN_SCORE_KEYS = {
    "score", "overallscore", "dimensionscore", "deductedpoints",
    "maxrecoverablepoints", "predictedscore", "scoreimpact",
}
HASH_EXCLUDED_KEYS = {
    "snapshothash", "processingmetrics", "requestid", "taskid",
    "signedurl", "temporaryurl", "createdat", "updatedat",
}

class EvidenceContractError(ValueError):
    pass

def _normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())

def assert_no_score_fields(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in FORBIDDEN_SCORE_KEYS:
                raise EvidenceContractError(f"forbidden_score_field:{path}.{key}")
            assert_no_score_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_score_fields(child, f"{path}[{index}]")

def validate_time_ranges(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        if "startMs" in value or "endMs" in value:
            start = value.get("startMs")
            end = value.get("endMs")
            if start is None or end is None or int(start) < 0 or int(end) < int(start):
                raise EvidenceContractError(f"invalid_time_range:{path}")
        for key, child in value.items():
            validate_time_ranges(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_time_ranges(child, f"{path}[{index}]")

def _hash_view(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _hash_view(child)
            for key, child in value.items()
            if _normalized_key(key) not in HASH_EXCLUDED_KEYS
        }
    if isinstance(value, list):
        return [_hash_view(child) for child in value]
    if isinstance(value, float):
        return round(value, 6)
    return value

def canonical_evidence_json(package: dict) -> str:
    return json.dumps(
        _hash_view(package), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )

def finalize_evidence_package(package: dict) -> dict:
    result = copy.deepcopy(package)
    result["contractVersion"] = CONTRACT_VERSION
    result["status"] = "FINAL"
    for key in (
        "transcriptSegments", "speakerTurns", "speakerIdentities",
        "visualEvidence", "deliverySignals", "contentEvidence",
    ):
        result.setdefault(key, [])
        if not isinstance(result[key], list):
            raise EvidenceContractError(f"invalid_collection:{key}")
    assert_no_score_fields(result)
    validate_time_ranges(result)
    canonical = canonical_evidence_json(result)
    result["snapshotHash"] = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return result
```

Requirements:

- Normalize snake/camel field names before comparing against forbidden score keys.
- Traverse nested dictionaries and lists.
- Exclude `snapshotHash`, `processingMetrics`, provider request IDs, signed URLs, and timestamps created by the runtime from the hash input.
- Preserve list order because transcript and frames are chronological.
- Use UTF-8 canonical JSON with sorted dictionary keys and compact separators.
- Add `contractVersion`, `status=FINAL`, and `snapshotHash` only after validation.

- [ ] **Step 4: Run tests and verify GREEN**

Run the Task 1 command. Expected: all Task 1 tests pass.

## Task 2: Speaker-Safe Segment Normalization

**Files:**

- Create: `ai-scoring/tests/test_media_evidence_speakers.py`
- Create: `ai-scoring/app/services/media_evidence/speaker_reconciliation.py`

- [ ] **Step 1: Write failing speaker tests**

```python
def test_missing_speaker_id_remains_unknown_instead_of_speaker_zero():
    result = normalize_asr_segments([
        {"start": 1.0, "end": 2.0, "text": "你好", "speaker_id": None}
    ], source="legacy_realtime")
    assert result["segments"][0]["rawSpeakerId"] is None
    assert result["segments"][0]["displaySpeaker"] == "发言人待确认"
    assert result["diarizationStatus"] == "unavailable"


def test_provider_speaker_id_is_preserved_as_raw_fact():
    result = normalize_asr_segments([
        {"begin_time": 1000, "end_time": 2500, "text": "技术介绍", "speaker_id": 2}
    ], source="dashscope_fun_asr", time_unit="ms")
    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_2"
    assert result["segments"][0]["startMs"] == 1000
    assert result["detectedSpeakerCount"] == 1


def test_overlap_is_not_forced_to_one_identity():
    result = normalize_asr_segments([
        {"start": 3.0, "end": 4.0, "text": "同时发言", "speaker_id": [1, 2]}
    ], source="local_diarization")
    assert result["segments"][0]["speakerState"] == "OVERLAP"
    assert result["segments"][0]["rawSpeakerId"] is None
```

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_media_evidence_speakers.py
```

Expected: module import failure.

- [ ] **Step 3: Implement normalization**

Implement `normalize_asr_segments(segments, *, source, time_unit="seconds")` with:

- seconds/milliseconds input support and millisecond output;
- immutable `rawSpeakerId` formatting;
- `displaySpeaker=发言人待确认` when unknown;
- explicit `AVAILABLE/UNAVAILABLE/PARTIAL` diarization status;
- overlap and insufficient-audio states;
- deterministic chronological sorting and segment numbering;
- no fallback to `SPEAKER_0`.

- [ ] **Step 4: Verify GREEN**

Run Task 2 tests and Task 1 tests together. Expected: pass.

## Task 3: Bounded Parallel Evidence Orchestrator

**Files:**

- Create: `ai-scoring/tests/test_media_evidence_orchestrator.py`
- Create: `ai-scoring/app/services/media_evidence/orchestrator.py`

- [ ] **Step 1: Write failing concurrency tests**

Test that two blocking branch functions overlap in time, results are returned in configured branch order, one branch timeout has a named stage error, and a branch containing `overallScore` is rejected by the contract firewall.

The public API is:

```python
result = run_evidence_branches(
    {
        "audio": lambda: {"transcriptSegments": []},
        "visual": lambda: {"visualEvidence": []},
    },
    max_workers=2,
    timeout_seconds=1,
)
```

Expected result:

```python
{
    "branchOrder": ["audio", "visual"],
    "outputs": {
        "audio": {"transcriptSegments": []},
        "visual": {"visualEvidence": []},
    },
    "metrics": {
        "audio": {"durationMs": 24},
        "visual": {"durationMs": 31},
    },
}
```

- [ ] **Step 2: Verify RED**

Run the single test file. Expected: module import failure.

- [ ] **Step 3: Implement bounded executor**

Use `ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(branches))))`.

Requirements:

- preserve input branch order when constructing output;
- validate every branch result with `assert_no_score_fields`;
- cancel pending futures after timeout;
- raise `EvidenceStageError(stage_key, code, message)` with the exact branch;
- record duration without including it in snapshot hash;
- never mutate branch return dictionaries.

- [ ] **Step 4: Verify GREEN**

Run Tasks 1–3 tests. Expected: pass.

## Task 4: Legacy Result Adapter And Quality Gate

**Files:**

- Create: `ai-scoring/tests/test_media_evidence_legacy_adapter.py`
- Create: `ai-scoring/app/services/media_evidence/legacy_adapter.py`

- [ ] **Step 1: Write failing adapter tests**

Tests must prove:

- current ASR segments become normalized transcript segments;
- absent speaker IDs remain unknown;
- video `gesture.score` becomes `signalValue`, with no nested `score` key;
- transcript, visual, speech and fusion arrays are chronologically stable;
- the package has `sourceType`, integrity fields and deterministic hash;
- official score dictionaries passed accidentally to the adapter are ignored, not copied.

Public API:

```python
package = build_legacy_evidence_package(
    session_id="26",
    source_type="UPLOAD_VIDEO",
    asr_result=asr_result,
    speech_quality=speech_quality,
    video_analysis=video_analysis,
    fusion=fusion,
    processing_metrics={"source": "shadow"},
)
```

- [ ] **Step 2: Verify RED**

Run the adapter tests. Expected: module import failure.

- [ ] **Step 3: Implement adapter**

Map only allow-listed fields. Do not recursively copy legacy service dictionaries. Create explicit mappers for transcript, delivery, visual and contradiction evidence. Compute:

- audio coverage from the union of valid transcript intervals divided by expected duration;
- `timestampMonotonic`;
- detected and unresolved speaker counts;
- diarization status from normalized segments;
- video frame count and source.

Then call `finalize_evidence_package`.

- [ ] **Step 4: Verify GREEN**

Run Tasks 1–4 tests. Expected: pass.

## Task 5: Atomic Shadow Snapshot Store

**Files:**

- Extend: `ai-scoring/tests/test_media_evidence_legacy_adapter.py`
- Create: `ai-scoring/app/services/media_evidence/shadow_store.py`

- [ ] **Step 1: Write failing store tests**

Test that `save_shadow_package(upload_dir, meeting_id, package)` writes `uploads/results/evidence_shadow_<meeting>.json`, replaces the prior file atomically, and a failed serialization leaves the prior valid snapshot intact.

- [ ] **Step 2: Verify RED**

Run the store tests. Expected: import failure.

- [ ] **Step 3: Implement atomic save**

Write UTF-8 JSON to a sibling temporary file, flush and `os.fsync`, then `os.replace`. Delete the temporary file on failure. Return the final path without logging full transcript content.

- [ ] **Step 4: Verify GREEN**

Run adapter/store tests. Expected: pass.

## Task 6: DashScope Offline Fun-ASR Parser And Client Boundary

**Files:**

- Create: `ai-scoring/tests/test_dashscope_recorded_asr.py`
- Create: `ai-scoring/app/services/media_evidence/dashscope_recorded.py`

- [ ] **Step 1: Write failing parser/client tests**

Use fixture dictionaries rather than the network. Cover:

- `transcripts[].sentences[]` parsing;
- speaker ID, begin/end time and text preservation;
- missing speaker ID remains unknown;
- non-200 SDK response raises `RecordedAsrError`;
- completed task without a transcription URL fails explicitly;
- downloaded invalid JSON fails explicitly;
- `speaker_count` is omitted when unknown and clamped to the supported 2–100 range when present.

Public boundary:

```python
provider = DashScopeRecordedAsrProvider(
    submit=submit_callable,
    wait=wait_callable,
    download_json=download_callable,
    model="fun-asr",
)
result = provider.transcribe_url(file_url, speaker_count_hint=4)
```

- [ ] **Step 2: Verify RED**

Run the test file. Expected: module import failure.

- [ ] **Step 3: Implement provider boundary**

Requirements:

- provider accepts only HTTP/HTTPS URLs;
- call submission with `diarization_enabled=True` and timestamp alignment enabled;
- validate SDK HTTP status and task status;
- download result JSON through injected callable;
- normalize with `normalize_asr_segments`;
- return provider/model/request/task metadata outside the canonical hash payload;
- never fall back silently to the realtime model.

- [ ] **Step 4: Verify GREEN**

Run Tasks 1–6 tests. Expected: pass.

## Task 7: Disabled-By-Default Shadow Integration

**Files:**

- Modify: `ai-scoring/app/config.py`
- Modify: `ai-scoring/app/services/pipeline_service.py`
- Modify: `ai-scoring/tests/test_pipeline_video_payload.py`

- [ ] **Step 1: Write failing pipeline tests**

Add tests that monkeypatch `settings.UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED`:

- false: no shadow package is written and existing result fields are unchanged;
- true: after ASR/speech/video/fusion preparation, a shadow package is written;
- shadow adapter failure logs a named shadow error but does not alter official score status;
- shadow package contains no official score fields.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_pipeline_video_payload.py -k evidence_shadow
```

Expected: failure because the setting and integration do not exist.

- [ ] **Step 3: Add configuration**

Add:

```python
UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED = env_bool("UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED", False)
EVIDENCE_CONTRACT_VERSION = os.getenv("EVIDENCE_CONTRACT_VERSION", "media-evidence-v1")
UPLOAD_RECORDED_ASR_MODEL = os.getenv("UPLOAD_RECORDED_ASR_MODEL", "fun-asr")
UPLOAD_RECORDED_ASR_TIMEOUT_SECONDS = int(os.getenv("UPLOAD_RECORDED_ASR_TIMEOUT_SECONDS", "480"))
```

Use the configuration module's existing boolean style; if adding `env_bool`, cover it with tests or keep the existing expression pattern.

- [ ] **Step 4: Integrate shadow save**

After evidence preparation and before official scoring, call an isolated helper `_write_evidence_shadow_if_enabled`. Pass only ASR, speech, video and fusion inputs. Catch `EvidenceContractError` and I/O errors as shadow-only failures. Do not add shadow output to the Java final callback in this checkpoint.

- [ ] **Step 5: Verify GREEN**

Run the Task 7 tests and the six-file baseline suite. Expected: all pass.

## Task 8: Checkpoint Verification

**Files:** none beyond previous tasks.

- [ ] **Step 1: Run focused new tests**

```bash
cd ai-scoring
.venv/bin/python -m pytest -q \
  tests/test_media_evidence_contracts.py \
  tests/test_media_evidence_speakers.py \
  tests/test_media_evidence_orchestrator.py \
  tests/test_media_evidence_legacy_adapter.py \
  tests/test_dashscope_recorded_asr.py
```

Expected: all pass.

- [ ] **Step 2: Run scoring regression tests**

```bash
.venv/bin/python -m pytest -q \
  tests/test_asr_concurrency.py \
  tests/test_video_analysis_sampling.py \
  tests/test_backend_callback_client.py \
  tests/test_llm_scoring_staged_output.py \
  tests/test_pipeline_staged_scoring_gate.py \
  tests/test_pipeline_video_payload.py \
  tests/test_session_authoritative_callback.py
```

Expected: all pass with no score payload changes when shadow mode is false.

- [ ] **Step 3: Static contract scan**

```bash
rg -n "overall_score|dimension_score|deducted_points|max_recoverable_points|predicted_score" \
  app/services/media_evidence
```

Expected: occurrences only in the forbidden-key definition, comments, or error messages; never in output construction.

- [ ] **Step 4: Checkpoint report**

Record test counts, changed files, known external-integration blockers, and confirm that the production flag remains false. Because this workspace is not a Git repository, do not run commit commands; preserve the exact file list and test output in the task handoff.

## Deferred Plans After Checkpoint 1

The following are separate implementation plans because they involve independent failure domains and release gates:

1. Online media gateway, Tingwu realtime diarization, Omni evidence stream, connection rotation and end-of-meeting finalization.
2. Temporary private OSS transport, actual upload-video provider activation, hedged fallback and real one-hour performance runs.
3. Java `speaker_identity`/stage-job persistence, evidence-ready callback, report API, frontend correction, shadow rollout and rollback.

No deferred subsystem may bypass the contract and score firewall implemented in this plan.
