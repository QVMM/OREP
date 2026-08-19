# Stage Roadshow Multimodal Speaker Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scene-constrained, evidence-only speaker attribution system that keeps four contestant roles as a soft roster prior, supports unlimited visitors and off-screen speakers, and assigns uploaded and live ASR text to stable session people without forcing low-confidence decisions.

**Architecture:** Reuse the existing millisecond media timeline, ASR, acoustic diarization, LR-ASD, Java callback path, and report UI. Add a versioned attribution contract, a pure Python session identity graph and decision engine, then integrate it first as an upload-video shadow result before adding persistent model workers, live camera subscription, Java terminal persistence, and frontend cutover. The old audio-only speaker path remains an explicit fallback.

**Tech Stack:** Python 3.14/FastAPI/pytest, isolated Python 3.11 PyTorch LR-ASD runtime, sherpa-onnx, OpenCV, Java 17/Spring Boot/MyBatis Plus/MySQL/JUnit, Vue 3/Vite/Node test runner, LiveKit, WebSocket PCM gateway.

**Repository note:** `/Users/liuyixing/项目/OREP` and `ai-scoring` are not Git worktrees. Commit steps are replaced with named checkpoint inventories and test evidence. Do not run destructive Git commands or claim commits exist.

---

## File Map

### Python core

- Create `ai-scoring/app/services/media_evidence/speaker_attribution_contract.py`: validate `speaker-attribution-v1` snapshots.
- Create `ai-scoring/app/services/media_evidence/session_identity_graph.py`: stable people, observations, aliases, merge/split guards, revisions.
- Create `ai-scoring/app/services/media_evidence/speaker_attribution_engine.py`: candidate scoring, conflict veto, unknown/off-screen/overlap decisions.
- Create `ai-scoring/app/services/media_evidence/transcript_attributor.py`: split ASR segments against final person turns.
- Create `ai-scoring/app/services/media_evidence/speaker_attribution_shadow.py`: persist deterministic shadow snapshots and metrics.
- Create `ai-scoring/app/services/media_evidence/global_person_registrar.py`: merge fragmented face tracks into session-global visual identities with co-visibility vetoes.
- Modify `ai-scoring/app/services/media_evidence/contracts.py`: embed the attribution snapshot without score fields.
- Modify `ai-scoring/app/services/pipeline_service.py`: call the new terminal attribution path after concurrent ASR/diarization/LR-ASD branches.
- Modify `ai-scoring/app/config.py`: feature flags and configurable thresholds.

### Model runtime and live transport

- Create `ai-scoring/app/services/media_evidence/model_worker_pool.py`: bounded persistent-worker scheduling and priority queues.
- Modify `ai-scoring/app/services/media_evidence/lr_asd_client.py`: support persistent worker transport while preserving subprocess fallback.
- Create `ai-scoring/app/services/media_evidence/media_clock.py`: audio-master/video-PTS mapping and drift evidence.
- Modify `ai-scoring/app/services/media_evidence/realtime_gateway.py`: negotiate clock metadata and preserve v2 compatibility.
- Modify `frontend/user/src/utils/realtimeAudioChunkSender.js`: send shared clock metadata.
- Modify `frontend/user/src/utils/mediaRecorder.js`: produce the same clock ID for video capture and recording metadata.

### Java persistence and API

- Create `backend/src/main/resources/sql/upgrade_ai_score_speaker_attribution_v1.sql`.
- Modify `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`.
- Modify `backend/src/main/java/com/orep/backend/entity/AiScoreSpeakerIdentity.java`.
- Modify `backend/src/main/java/com/orep/backend/entity/AiScoreTranscriptSegment.java`.
- Create `backend/src/main/java/com/orep/backend/entity/AiScoreSpeakerTurn.java`.
- Create `backend/src/main/java/com/orep/backend/mapper/AiScoreSpeakerTurnMapper.java`.
- Modify `backend/src/main/java/com/orep/backend/service/AiScoreSpeakerIdentityService.java`.
- Modify `backend/src/main/java/com/orep/backend/service/AiScoreTranscriptService.java`.
- Modify `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`.

### Frontend

- Modify `frontend/user/src/utils/aiScoreMinutesPresentation.js`: prefer stable person fields and render special states.
- Modify `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue`: group contestant, visitor, off-screen, unknown, and overlap transcript rows.

---

### Task 1: Versioned Speaker Attribution Contract

**Files:**
- Create: `ai-scoring/tests/test_speaker_attribution_contract.py`
- Create: `ai-scoring/app/services/media_evidence/speaker_attribution_contract.py`
- Modify: `ai-scoring/app/services/media_evidence/contracts.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_normalizes_stable_people_turns_and_segments():
    result = normalize_speaker_attribution({
        "contractVersion": "speaker-attribution-v1",
        "revision": 2,
        "status": "FINAL",
        "clock": {"clockId": "s1", "timebase": "MILLISECONDS", "masterSource": "MEDIA_PTS"},
        "people": [{"personId": "PERSON_1", "personType": "CONTESTANT", "contestantSlot": 1,
                    "state": "STABLE", "confidence": .9, "firstSeenMs": 0, "lastSeenMs": 3000}],
        "turns": [{"turnId": "TURN_1", "startMs": 0, "endMs": 3000, "personId": "PERSON_1",
                   "speakerState": "CONFIRMED", "confidence": .9}],
        "segments": [{"segmentId": "SEG_1", "revision": 2, "startMs": 0, "endMs": 3000,
                      "text": "测试", "personId": "PERSON_1", "speakerState": "CONFIRMED",
                      "speakerConfidence": .9, "isFinal": True}],
    })
    assert result["people"][0]["personId"] == "PERSON_1"
    assert result["segments"][0]["personId"] == "PERSON_1"

def test_rejects_score_fields_unknown_person_refs_and_invalid_contestant_slot():
    with pytest.raises(SpeakerAttributionContractError):
        normalize_speaker_attribution(invalid_snapshot)
```

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_contract.py -q`  
Expected: FAIL during collection because `speaker_attribution_contract` does not exist.

- [ ] **Step 3: Implement the strict normalizer**

Implement constants for person types, states, contract version, confidence range, unique IDs, valid time ranges, referential integrity, final/provisional consistency, recursive score-field rejection, and deterministic sorting. Expose:

```python
class SpeakerAttributionContractError(ValueError): ...

def normalize_speaker_attribution(value: dict) -> dict: ...
```

- [ ] **Step 4: Embed attribution in media evidence packages**

Add optional `speakerAttribution` validation to `finalize_evidence_package`; preserve existing v1 packages when the field is absent and include it in the snapshot hash when present.

- [ ] **Step 5: Verify GREEN and regression**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_contract.py tests/test_media_evidence_contracts.py -q`  
Expected: all selected tests pass.

- [ ] **Step 6: Record Checkpoint 1A**

Record exact changed files and test output in `ai-scoring/docs/testing/speaker-attribution-checkpoints.md` under `Checkpoint 1A`.

### Task 2: Pure Session Identity Graph

**Files:**
- Create: `ai-scoring/tests/test_session_identity_graph.py`
- Create: `ai-scoring/app/services/media_evidence/session_identity_graph.py`

- [ ] **Step 1: Write failing state and identity tests**

Test that four contestant slots are created as unbound role priors; extra visitors/off-screen people are unlimited; observations do not directly become people; one person accepts multiple voice/face/body aliases; simultaneous visible tracks veto a merge; and a later visible voice match upgrades `OFFSCREEN_1` to a visitor without changing its `personId`.

```python
graph = SessionIdentityGraph(session_id="26", contestant_slots=4)
assert len(graph.contestant_slots()) == 4
visitor = graph.create_person("VISITOR", first_seen_ms=1000)
assert visitor.person_id == "PERSON_5"
```

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_session_identity_graph.py -q`  
Expected: FAIL because the graph module is missing.

- [ ] **Step 3: Implement immutable observation records and graph operations**

Implement focused dataclasses `PersonNode`, `ObservationRef`, `MergeEvidence`, and `SessionIdentityGraph`. Required public operations:

```python
create_person(person_type, *, first_seen_ms, contestant_slot=None)
attach_observation(person_id, observation)
merge_people(target_person_id, source_person_id, evidence)
split_alias(person_id, *, alias_kind, alias_id, reason)
upgrade_person_type(person_id, person_type)
snapshot(*, revision, status, clock)
```

Reject merge on co-visible conflict, overlapping distinct active voices, or insufficient independent evidence.

- [ ] **Step 4: Verify GREEN**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_session_identity_graph.py -q`  
Expected: all tests pass.

- [ ] **Step 5: Record Checkpoint 1B**

Append graph invariants and test output to the checkpoint document.

### Task 3: Evidence-Gated Attribution Decision Engine

**Files:**
- Create: `ai-scoring/tests/test_speaker_attribution_engine.py`
- Create: `ai-scoring/app/services/media_evidence/speaker_attribution_engine.py`
- Modify: `ai-scoring/app/config.py`

- [ ] **Step 1: Write failing decision-table tests**

Cover confirmed contestant, provisional candidate, unknown, confirmed off-screen, overlap, external-person-not-forced-to-contestant, and conflict-veto cases.

```python
decision = decide_turn(candidates, context, thresholds)
assert decision.speaker_state == "UNKNOWN"
assert decision.person_id is None
assert "CO_VISIBLE_CONFLICT" in decision.conflicts
```

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_engine.py -q`  
Expected: FAIL because `decide_turn` is missing.

- [ ] **Step 3: Implement validity gate, score, margin, and veto phases**

Use configured defaults `confirmed=0.85`, `provisional=0.70`, `minimum_margin=0.15`; role prior may break a near tie only after absolute evidence passes and must never create a contestant match alone. Return a structured decision containing candidates, component evidence, conflicts, and reason code.

- [ ] **Step 4: Verify GREEN and config parsing**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_engine.py tests/test_config_defaults.py -q`  
Expected: all selected tests pass; if `test_config_defaults.py` is absent, run the attribution test plus `python -c 'from app.config import settings; print(settings)'`.

- [ ] **Step 5: Record Checkpoint 1C**

Append the complete decision table and test output.

### Task 4: Person-Aware Transcript Attribution

**Files:**
- Create: `ai-scoring/tests/test_transcript_attributor.py`
- Create: `ai-scoring/app/services/media_evidence/transcript_attributor.py`

- [ ] **Step 1: Write failing segment tests**

Test stable same-person joins, contestant-to-visitor splits, unknown preservation, overlap candidates, deterministic IDs/revisions, and word-timestamp splitting when a speaker changes inside one ASR segment.

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_transcript_attributor.py -q`  
Expected: FAIL because the module is missing.

- [ ] **Step 3: Implement attribution**

Expose:

```python
def attribute_transcript(asr_result: dict, turns: list[dict], *, revision: int, is_final: bool) -> list[dict]: ...
```

Use word timestamps when available; otherwise use deterministic temporal overlap. Never replace `UNKNOWN` with the nearest contestant. Preserve original ASR text and provider confidence.

- [ ] **Step 4: Verify GREEN**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_transcript_attributor.py -q`  
Expected: all tests pass.

### Task 5: Upload-Video Shadow Integration

**Files:**
- Create: `ai-scoring/tests/test_speaker_attribution_shadow_pipeline.py`
- Create: `ai-scoring/app/services/media_evidence/speaker_attribution_shadow.py`
- Modify: `ai-scoring/app/services/pipeline_service.py`
- Modify: `ai-scoring/app/config.py`

- [ ] **Step 1: Write failing pipeline tests**

Assert that ASR, acoustic diarization, and LR-ASD remain parallel; the new engine receives their raw outputs; the existing public `asrSegments` remain unchanged while shadow mode is enabled; and attribution failure returns a named shadow failure without failing scoring.

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_shadow_pipeline.py -q`  
Expected: FAIL because no shadow branch exists.

- [ ] **Step 3: Add shadow feature flags and adapter**

Add `SPEAKER_ATTRIBUTION_ENABLED`, `SPEAKER_ATTRIBUTION_SHADOW_MODE`, and threshold settings. Build an adapter that converts existing acoustic turns and LR-ASD intervals into graph observations without treating counts as people.

- [ ] **Step 4: Persist deterministic local snapshots**

Write snapshots below `uploads/results/speaker-attribution/<meeting_id>/revision-<n>.json` using atomic replace and SHA-256. Do not include model vectors, secrets, score fields, public URLs, or OSS dependencies.

- [ ] **Step 5: Verify GREEN and existing pipeline selection**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_speaker_attribution_shadow_pipeline.py tests/test_final_asr_pipeline_selection.py tests/test_active_speaker_fusion.py -q`  
Expected: all selected tests pass.

- [ ] **Step 6: Record Checkpoint 2**

Document snapshot path, hash, counts by person type, unknown duration, runtime, and unchanged public output.

### Task 5B: Cross-Shot Global Visual Identity Registration

**Files:**
- Create: `ai-scoring/tests/test_global_person_registrar.py`
- Create: `ai-scoring/app/services/media_evidence/global_person_registrar.py`
- Modify: `ai-scoring/scripts/lr_asd_worker.py`
- Modify: `ai-scoring/app/services/media_evidence/active_speaker_contract.py`
- Modify: `ai-scoring/tests/test_lr_asd_worker_smoke.py`

- [ ] **Step 1: Write failing registry tests**

Cover fragmented tracks of one person, same-frame co-visible veto, transitive merge safety, weak/small-face rejection, deterministic global IDs, and preservation of every source track as evidence.

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_global_person_registrar.py -q`  
Expected: FAIL because `global_person_registrar` does not exist.

- [ ] **Step 3: Implement evidence-gated global registration**

Build deterministic connected components only from strict face-similarity links. Reject every proposed link when the components contain a co-visible pair. Do not use the expected four contestants as a clustering target and do not create a person from a track count.

- [ ] **Step 4: Integrate inside the isolated LR-ASD worker**

Keep compact face prototypes and co-visible pairs in memory, map raw face tracks to `visualIdentityId`, and return only IDs/link confidence/diagnostics through the score-free evidence contract. Never persist raw embeddings or force low-confidence tracks into an identity.

- [ ] **Step 5: Verify GREEN and worker regression**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_global_person_registrar.py tests/test_lr_asd_worker_smoke.py tests/test_lr_asd_client.py tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py -q`  
Expected: all selected tests pass.

- [ ] **Step 6: Record Checkpoint 2B**

Record raw track count, global visual identity count, rejected co-visible links, unresolved track count, and unchanged public attribution behavior.

### Task 6: Real-Video Terminal Validation

> **Required predecessor added after Task 5 inspection:** Real LR-ASD output can contain many fragmented face tracks for the same contestant. A face track is an observation, not a person. Complete Task 5B before this validation; otherwise a superficially successful audio/visual join would still expose unstable track IDs as people.

**Files:**
- Create: `ai-scoring/tests/fixtures/speaker_attribution/e9df_acceptance_intervals.json`
- Create: `ai-scoring/scripts/validate_speaker_attribution_video.py`
- Modify: `ai-scoring/docs/testing/speaker-attribution-checkpoints.md`

- [ ] **Step 1: Define real acceptance intervals**

Create selected intervals covering opening four-person roster, self-introductions, speaker hand-offs, small faces, occlusion, possible off-screen speech, and overlap. Store only timestamps and expected state/type; do not train on them.

- [ ] **Step 2: Run baseline against the existing result**

Run the validator against `/Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4` and record current eight acoustic clusters, two AV-bound identities, zero merged clusters, runtime, and failure metrics.

- [ ] **Step 3: Run the new shadow pipeline**

Expected acceptance: no UI-facing claim that eight clusters are eight people; stable contestant identities are not duplicated; external/unknown intervals are not assigned to contestants; all low-confidence intervals have an explicit state.

- [ ] **Step 4: Record Checkpoint 3 and stop on failure**

Do not proceed to public cutover if external-to-contestant false attribution exceeds 1% on annotated duration or high-confidence attribution is below 95%.

### Task 7: Persistent Local Model Worker Pool

**Files:**
- Create: `ai-scoring/tests/test_model_worker_pool.py`
- Create: `ai-scoring/app/services/media_evidence/model_worker_pool.py`
- Modify: `ai-scoring/app/services/media_evidence/lr_asd_client.py`
- Modify: `ai-scoring/app/config.py`

- [ ] **Step 1: Write failing scheduling tests**

Test bounded capacity, `LIVE > UPLOAD > REPAIR` priority, starvation guard, timeout, crashed-worker replacement, and subprocess fallback.

- [ ] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_model_worker_pool.py -q`  
Expected: FAIL because the worker pool is missing.

- [ ] **Step 3: Implement one persistent LR-ASD worker per configured device**

Use a bounded request queue, correlation IDs, health checks, hard request deadlines, and restart limits. Do not enable cross-session micro-batching until a separate benchmark proves unchanged accuracy.

- [ ] **Step 4: Verify GREEN and LR-ASD regression**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_model_worker_pool.py tests/test_lr_asd_client.py tests/test_lr_asd_worker_smoke.py -q`  
Expected: all tests pass.

- [ ] **Step 5: Record Checkpoint 4 performance**

Measure cold start, warm request latency, one-hour video runtime, memory, queue wait, and failure recovery.

### Task 8: Shared Live Media Clock and Provisional Revisions

**Files:**
- Create: `ai-scoring/tests/test_media_clock.py`
- Create: `ai-scoring/app/services/media_evidence/media_clock.py`
- Modify: `ai-scoring/app/services/media_evidence/realtime_gateway.py`
- Modify: `ai-scoring/app/services/media_evidence/live_finalizer.py`
- Modify: `frontend/user/src/utils/realtimeAudioChunkSender.js`
- Modify: `frontend/user/src/utils/realtimeAudioChunkSender.test.js`
- Modify: `frontend/user/src/utils/mediaRecorder.js`

- [x] **Step 1: Write failing Python and JavaScript clock tests**

Test one `clockId` across audio/video, reconnect preservation, video PTS mapping, drift recording, severe-drift downgrade, and backward-compatible `media-evidence-v2` audio sessions.

- [x] **Step 2: Verify RED**

Run Python and Node tests; expect failures for missing shared clock fields.

- [x] **Step 3: Implement shared clock metadata**

Use audio sample count as online master and media PTS as upload master. Record raw PTS, mapped milliseconds, drift, and sync status. Do not rewrite raw timestamps.

- [x] **Step 4: Add provisional segment revision rules**

Within a 10-second correction horizon, accept only increasing revisions for the same `segmentId`; final segments reject provisional overwrites.

- [x] **Step 5: Verify GREEN and gateway regression**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_media_clock.py tests/test_realtime_audio_gateway.py tests/test_realtime_asr_protocol.py tests/test_live_evidence_finalizer.py -q`  
Run: `cd frontend/user && node --test src/utils/realtimeAudioChunkSender.test.js`  
Expected: all tests pass.

### Task 9: Java Versioned Persistence and Terminal Protection

**Files:**
- Create: `backend/src/main/resources/sql/upgrade_ai_score_speaker_attribution_v1.sql`
- Modify/Create Java files listed in the File Map
- Create: `backend/src/test/java/com/orep/backend/service/AiScoreSpeakerAttributionPersistenceTest.java`

- [x] **Step 1: Write failing H2 service tests**

Test transactional replacement, idempotent same revision, rejection of older revision, final-over-provisional protection, unlimited visitor/off-screen rows, unknown transcript persistence, and rollback on invalid person references.

- [x] **Step 2: Verify RED**

Run: `cd backend && mvn -Dtest=AiScoreSpeakerAttributionPersistenceTest test`  
Expected: compilation or assertion failure because schema/entities are missing.

- [x] **Step 3: Add backward-compatible schema and DTOs**

Add nullable columns first, unique `(session_id, person_id)` and `(session_id, segment_uid)` indexes, the speaker-turn table, and attribution revision/status fields. Preserve existing raw speaker labels.

- [x] **Step 4: Implement transactional persistence**

Persist a complete attribution snapshot in one transaction. Validate all person references before deleting/replacing the previous provisional snapshot. Never let an older or provisional result overwrite a newer final snapshot.

- [x] **Step 5: Verify GREEN and callback regression**

Run: `cd backend && mvn -Dtest=AiScoreSpeakerAttributionPersistenceTest,AiScoringSessionServiceTest test`  
Expected: selected tests pass.

- [x] **Step 6: Record Checkpoint 6**

Record migration, rollback, idempotency, terminal protection, and callback replay evidence.

### Task 10: Report API and Frontend Person Presentation

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreReportUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `frontend/user/src/utils/aiScoreMinutesPresentation.js`
- Modify: `frontend/user/src/utils/aiScoreMinutesPresentation.test.js`
- Modify: `frontend/user/src/views/ai-score-report/AiScoreReportWhy.vue`

- [x] **Step 1: Write failing API and presentation tests**

Test stable `personId`, person type labels, contestant grouping, visitor/off-screen labels, unknown/overlap rendering, and absence of acoustic cluster counts from user-facing copy.

- [x] **Step 2: Verify RED**

Run selected Maven and Node tests; expect missing fields and labels.

- [x] **Step 3: Extend report API without breaking old sessions**

Return `speakerAttributionStatus`, stable people, and final segments. When new data is absent, use the existing speaker mapping adapter.

- [x] **Step 4: Update presentation**

Render contestants first, then external/off-screen people, then unknown/overlap transcript rows. Do not imply unknown is a person and do not display model cluster counts.

- [x] **Step 5: Verify GREEN and build**

Run: `cd frontend/user && node --test src/utils/aiScoreMinutesPresentation.test.js && npm run build`  
Run the selected backend report tests. Expected: tests and production build pass.

- [x] **Step 6: Record Checkpoint 7**

Capture report API fixture and screenshots for contestant, visitor, off-screen, unknown, and overlap states.

### Task 11: Live Camera Subscription and Load Shedding

**Files:**
- Create: `ai-scoring/app/services/media_evidence/live_camera_subscriber.py`
- Create: `ai-scoring/tests/test_live_camera_subscriber.py`
- Modify: `ai-scoring/app/routers/scoring_router.py`
- Modify: `ai-scoring/app/config.py`

- [x] **Step 1: Write failing subscriber tests**

Test camera-only selection, screen-share rejection, 5–8 fps sampling, PTS preservation, reconnect, bounded queue, frame dropping on backlog, and audio-only degradation.

- [x] **Step 2: Verify RED**

Run: `cd ai-scoring && .venv/bin/python -m pytest tests/test_live_camera_subscriber.py -q`  
Expected: FAIL because the subscriber is missing.

- [x] **Step 3: Implement the local LiveKit subscriber boundary**

Subscribe only to the camera track, publish frames into the shared visual queue, preserve PTS/clockId, and stop cleanly with session terminal state. Do not route media through OSS or public URLs.

- [x] **Step 4: Implement load shedding**

When visual backlog exceeds 3 seconds, discard oldest non-key frames while retaining timestamps and a dropped-frame integrity signal. Audio ASR must continue.

- [x] **Step 5: Verify GREEN and live integration**

Run subscriber, gateway, clock, and finalizer tests. Expected: all pass with no unbounded queue.

### Task 12: End-to-End Shadow Rollout and Cutover Gate

**Files:**
- Create: `ai-scoring/tests/test_speaker_attribution_end_to_end.py`
- Modify: `ai-scoring/docs/testing/speaker-attribution-checkpoints.md`
- Modify: `ai-scoring/docs/superpowers/specs/2026-07-14-stage-roadshow-multimodal-speaker-attribution-design.md` only if verified implementation decisions differ.

- [x] **Step 1: Run complete targeted suites**

Run all new Python tests plus existing media-evidence, ASR, LR-ASD, callback, Java persistence/report, and frontend presentation tests.

- [x] **Step 2: Run real upload video**

Run the provided 55-minute video and record wall time, stable people, contestant duplicates, visitors/off-screen/unknown duration, attribution confidence, and memory.

- [x] **Step 3: Run one-hour concurrency scenarios**

Measure one live session plus queued uploads, worker crash/recovery, provider ASR degradation, video interruption, and callback replay. Confirm live P95 attribution below 3 seconds and upload attribution below 12 minutes on target hardware.

- [x] **Step 4: Compare old and new outputs in shadow mode**

Old public output remains authoritative until all gates pass. Produce a machine-readable comparison; never manually hide regressions.

- [x] **Step 5: Cut over or stop**

Enable the new public attribution only if external-to-contestant false attribution is below 1%, high-confidence attribution is at least 95%, terminal and callback tests pass, and performance targets hold. Otherwise remain in shadow mode with named failure reasons.

- [x] **Step 6: Record Checkpoint 8**

Write the final go/no-go decision, exact commands, outputs, known limitations, rollback switch, and all unresolved issues.

---

## Execution Order

Implement inline in four reviewed batches:

1. **Batch A — Foundation:** Tasks 1–4.
2. **Batch B — Upload terminal shadow:** Tasks 5–7.
3. **Batch C — Live and Java persistence:** Tasks 8–9 and 11.
4. **Batch D — Product cutover:** Tasks 10 and 12.

Stop at every checkpoint if tests fail, contracts conflict, real-video false attribution exceeds the gate, or performance regresses. Do not widen thresholds to make metrics look better.

## Current Execution Status

- Batch A / Tasks 1–4: completed on 2026-07-14; 61 targeted regression tests passed.
- Batch B / Task 5: completed on 2026-07-14; 56 focused and related regression tests passed.
- Batch B / Task 5B: completed in shadow mode on 2026-07-14; 63 related tests passed and a 90-second real-video smoke run completed in 21.952 seconds.
- Batch B / Task 6: completed for shadow safety on 2026-07-14; public cutover remains blocked by role binding and labeled-accuracy gates.
- Batch B / Task 7: completed for upload shadow traffic on 2026-07-14; cold/warm real-media reuse passed and Batch B regression reached 120 tests.
- Batch B: checkpoint complete. Public attribution remains disabled.
- Batch C / Task 8: completed on 2026-07-14; shared upload/live clock, reconnect recovery, drift downgrade, and terminal transcript revisions passed 45 Python tests, 9 Node tests, and the production frontend build.
- Batch C / Task 9: completed on 2026-07-14; versioned transactional persistence, callback propagation, deployment migrations, idempotent replay, and final-state protection passed the complete 249-test backend suite plus a clean MySQL 8 migration replay.
- Batch C / Task 11: completed on 2026-07-14; private LiveKit camera-only subscription, shared server clock, 5–8 FPS sampling, reconnect handling, bounded load shedding, terminal timing-metadata fusion, and audio-only degradation passed 170 Python regressions, 11 Node tests, the frontend production build, and an isolated real WebRTC camera-track integration.
- Batch C: complete. The public attribution switch remains off.
- Batch D / Task 10: completed on 2026-07-14; stable-person API and user presentation passed 12 Java tests, 11 Node tests, production build, and a real session-26 shadow-hidden browser check.
- Batch D / Task 12: completed on 2026-07-14 with a machine-readable `NO_GO`; public attribution remains disabled because independent labels and live end-to-end latency are unavailable, and the real upload branch exceeded 12 minutes by 6.087 seconds.
- Batch D: complete for this rollout attempt. The stable report contract is ready, but the public switch remains off until a later gate run clears every named failure.
