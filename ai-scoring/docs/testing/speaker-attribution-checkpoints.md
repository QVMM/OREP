# Speaker Attribution Implementation Checkpoints

## Checkpoint 1A — Versioned Contract

**Date:** 2026-07-14  
**Status:** passed

Changed files:

- `app/services/media_evidence/speaker_attribution_contract.py`
- `app/services/media_evidence/contracts.py`
- `tests/test_speaker_attribution_contract.py`

Verified invariants:

- `speaker-attribution-v1` is score-free and deterministic.
- People, turns, and segments have unique identifiers and valid millisecond ranges.
- All person references resolve to a stable person in the same snapshot.
- Contestant slots are limited to role slots 1–4 without limiting visitor/off-screen counts.
- `UNKNOWN` and `OVERLAP` never invent a person ID.
- Final snapshots cannot contain provisional transcript segments.
- Existing media evidence packages remain valid when no attribution snapshot is present.

Verification command:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_contract.py tests/test_media_evidence_contracts.py -q
```

Result:

```text
14 passed in 0.03s
```

## Checkpoint 1B — Session Identity Graph

**Date:** 2026-07-14  
**Status:** passed

Changed files:

- `app/services/media_evidence/session_identity_graph.py`
- `tests/test_session_identity_graph.py`

Verified invariants:

- Four contestant slots are unbound role priors, not a total-person cap.
- Visitor and off-screen people can be created beyond the four role slots.
- One stable person can own multiple face, body, and voice aliases.
- Merges require two independent modalities or one strict face identity.
- Simultaneous visible faces veto a merge.
- An off-screen person can become a visitor without changing `personId`.
- Graph snapshots pass the `speaker-attribution-v1` contract.

Regression command:

```text
.venv/bin/python -m pytest tests/test_session_identity_graph.py tests/test_speaker_attribution_contract.py tests/test_media_evidence_contracts.py tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py -q
```

Result:

```text
38 passed in 0.07s
```

## Checkpoint 1C — Evidence-Gated Decision Engine

**Date:** 2026-07-14  
**Status:** passed

Changed files:

- `app/services/media_evidence/speaker_attribution_engine.py`
- `app/config.py`
- `tests/test_speaker_attribution_engine.py`

Verified decision rules:

- A contestant role prior cannot turn weak evidence into a match.
- Confirmed and provisional decisions use separate configurable thresholds.
- The leading candidate must have an explicit minimum margin.
- Co-visible and cross-modal conflicts veto otherwise high scores.
- Overlap never forces a single person.
- A previously enrolled off-screen voice can be confirmed without a visible face.

Regression command:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_engine.py tests/test_session_identity_graph.py tests/test_speaker_attribution_contract.py tests/test_media_evidence_contracts.py tests/test_active_speaker_fusion.py -q
```

Result:

```text
35 passed in 0.04s
```

## Checkpoint 1D — Person-Aware Transcript Attribution

**Date:** 2026-07-14  
**Status:** passed

Changed files:

- `app/services/media_evidence/transcript_attributor.py`
- `tests/test_transcript_attributor.py`

Verified behavior:

- A confirmed person turn assigns the matching ASR text.
- Word timestamps split one provider segment at a real person boundary.
- A visitor interruption is not absorbed into the preceding contestant segment.
- Unknown speech keeps its text and a null person ID.
- Overlap keeps sorted candidates and never chooses one person.
- Identical inputs produce deterministic segment IDs and revisions.

Batch A regression command:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_contract.py tests/test_session_identity_graph.py tests/test_speaker_attribution_engine.py tests/test_transcript_attributor.py tests/test_media_evidence_contracts.py tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py tests/test_asr_diarization_reconciler.py tests/test_media_evidence_speakers.py -q
```

Result:

```text
61 passed in 0.06s
```

## Checkpoint 2 — Upload Shadow Integration

**Date:** 2026-07-14  
**Status:** passed (safe-unbound shadow)

Changed files:

- `app/services/media_evidence/speaker_attribution_shadow.py`
- `app/services/pipeline_service.py`
- `tests/test_speaker_attribution_shadow_pipeline.py`

Verified behavior:

- The existing cloud ASR, acoustic diarization, and optional LR-ASD branches remain concurrent.
- Shadow attribution is terminal evidence only and does not participate in the score.
- Acoustic clusters and face tracks remain observations; neither is promoted to a person.
- Exactly the configured 0–4 contestant role slots are created as unbound priors.
- Until global person registration is ready, transcript turns remain explicitly `UNKNOWN`.
- Snapshot writes are private, deterministic, SHA-256 identified, and atomically replaced.
- A shadow failure is named and cannot fail scoring or mutate the public ASR segments.

Focused verification command:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_shadow_pipeline.py -q
```

Result:

```text
3 passed in 0.76s
```

Related regression command:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_shadow_pipeline.py tests/test_final_asr_pipeline_selection.py tests/test_speaker_attribution_contract.py tests/test_session_identity_graph.py tests/test_speaker_attribution_engine.py tests/test_transcript_attributor.py tests/test_active_speaker_fusion.py -q
```

Result:

```text
56 passed in 0.81s
```

Safety finding and next gate:

- The supplied real-video LR-ASD run produced fragmented face tracks; those track IDs are not reliable person IDs.
- Task 5B (cross-shot global visual identity registration) is now mandatory before real-video identity acceptance or public cutover.

## Checkpoint 2B — Cross-Shot Global Visual Registration

**Date:** 2026-07-14  
**Status:** passed for shadow evidence; public person cutover remains blocked

Changed files:

- `app/services/media_evidence/global_person_registrar.py`
- `app/services/media_evidence/active_speaker_contract.py`
- `app/services/media_evidence/lr_asd_client.py`
- `app/services/pipeline_service.py`
- `app/config.py`
- `scripts/lr_asd_worker.py`
- `tests/test_global_person_registrar.py`
- `tests/test_lr_asd_worker_smoke.py`
- `tests/test_lr_asd_client.py`
- `tests/test_active_speaker_contract.py`

Verified invariants:

- Continuous spatial tracklets and cross-shot face registration are separate layers.
- Distant faces never reuse a track ID merely because their embeddings are similar.
- Every proposed direct or transitive merge is vetoed if its components contain a same-frame pair.
- Tracks below the detection/visibility gate remain `UNRESOLVED` evidence.
- Similarity from 0.60 to below 0.80 can form only a `CANDIDATE`; it is not a stable person.
- Raw face vectors never leave the isolated LR-ASD worker.
- Pairwise registration work is restricted to quality-eligible tracks.

Regression command:

```text
.venv/bin/python -m pytest tests/test_global_person_registrar.py tests/test_lr_asd_worker_smoke.py tests/test_lr_asd_client.py tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py tests/test_speaker_attribution_shadow_pipeline.py tests/test_final_asr_pipeline_selection.py -q
```

Result:

```text
63 passed in 1.03s
```

Real-video smoke input:

```text
uploads/real-video-tests/lr-asd/e9df_start_90s.mp4
uploads/real-video-tests/lr-asd/e9df_start_90s.wav
```

Observed result:

- Wall time: 21.952 seconds.
- Raw spatial tracklets: 102.
- Quality-eligible tracklets: 27.
- Global visual candidates: 6.
- Stable visual identities (similarity at least 0.80): 2.
- Candidate visual identities requiring audio/other evidence: 4.
- Unresolved low-quality tracklets: 75.
- No raw track count is exposed as a person count.

Interpretation:

- The opening scene visibly contains four contestants, but visual evidence alone does not yet justify binding every candidate to a contestant.
- The result therefore stays in shadow mode. Acoustic-cluster and active-speaker evidence must perform the next merge/confirmation step; uncertain fragments remain unknown.

## Checkpoint 3 — Full Real-Video Terminal Validation

**Date:** 2026-07-14  
**Status:** shadow safety passed; public person cutover blocked

Input:

- Video: `/Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4`
- Duration: 3270.792 seconds.
- Audio: `uploads/real-video-tests/e9df998256bca0a6cbba604c1390330e.wav`
- Acceptance fixture: `tests/fixtures/speaker_attribution/e9df_acceptance_intervals.json`

Full LR-ASD/global-registration command:

```text
.venv/bin/python scripts/validate_speaker_attribution_video.py --video /Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4 --audio uploads/real-video-tests/e9df998256bca0a6cbba604c1390330e.wav --output uploads/results/result_lr_asd_global_registration_e9df_20260714.json
```

Observed result:

- Wall time: 704.032 seconds (11 minutes 44 seconds).
- Previous LR-ASD baseline: 682.493 seconds; overhead was about 3.2%.
- Raw spatial tracklets: 768.
- Quality-eligible tracklets: 310.
- Unresolved low-quality tracklets: 458.
- Global visual candidates: 11; no visual candidate alone was promoted to a person.
- Active-speaker intervals: 577.
- Accepted visual links: 299.
- Rejected co-visible links: 4631.

Acoustic threshold validation:

- Official sherpa-onnx behavior is that a larger clustering threshold yields fewer clusters and requires scenario-specific tuning.
- On the first 10 minutes, thresholds `1.2` and `1.4` collapsed the audio to one speaker and were rejected.
- Thresholds `1.05` and `1.10` preserved three main speakers in the first 10 minutes.
- Full-video threshold `1.10` produced six retained acoustic clusters in 269.580 seconds.
- Four main acoustic clusters mapped one-to-one to four distinct visual identities and covered 342 turns.
- The remaining two acoustic-only clusters totalled 14.394 seconds and 8.892 seconds; they remain off-screen/unknown candidates.
- The scene-profile default is therefore `1.10`, never a forced four-speaker count.

Regression after integration:

```text
.venv/bin/python -m pytest tests/test_speaker_attribution_shadow_pipeline.py tests/test_final_asr_pipeline_selection.py tests/test_active_speaker_fusion.py tests/test_global_person_registrar.py tests/test_lr_asd_worker_smoke.py tests/test_lr_asd_client.py tests/test_active_speaker_contract.py tests/test_validate_speaker_attribution_video.py tests/test_local_diarization.py -q
```

Result:

```text
73 passed in 0.79s
```

Gate decision:

- Passed: track counts are not person counts; low-quality evidence is unresolved; same-frame conflicts veto merges; runtime remains below 12 minutes for the 54.5-minute sample.
- Blocked: four stable session people are not yet bound to contestant roles; external/off-screen validation lacks a labeled gold set; high-confidence public attribution cannot yet be claimed.
- Action: remain in shadow mode and proceed to bounded persistent workers, live clock integration, and versioned persistence before UI cutover.

## Checkpoint 4 — Persistent LR-ASD Worker and Bounded Scheduling

**Date:** 2026-07-14  
**Status:** passed for upload shadow traffic

Changed files:

- `app/services/media_evidence/model_worker_pool.py`
- `app/services/media_evidence/persistent_model_transport.py`
- `app/services/media_evidence/lr_asd_client.py`
- `app/services/pipeline_service.py`
- `app/config.py`
- `scripts/lr_asd_worker.py`
- `tests/test_model_worker_pool.py`
- `tests/test_persistent_model_transport.py`
- `tests/test_lr_asd_client.py`
- `tests/test_lr_asd_worker_smoke.py`

Verified behavior:

- The queue is bounded and rejects overflow instead of growing memory without limit.
- Priority is `LIVE > UPLOAD > REPAIR`, with a starvation guard for waiting uploads.
- A request whose queue deadline expires never enters the model worker.
- A crashed worker is closed and recreated before the next request.
- The JSON-lines protocol correlates every request/response and terminates a timed-out or mismatched process.
- LR-ASD loads once in `--serve` mode and accepts multiple private local-path requests.
- Client transport failure falls back to the proven one-shot subprocess boundary.
- Pool shutdown closes persistent child processes.

Real 90-second repeated-request result:

- Cold request wall time: 21.197 seconds; worker duration 19.757 seconds.
- Warm request wall time: 18.648 seconds; worker duration 18.643 seconds.
- Warm improvement: approximately 12%.
- Both requests returned exactly 102 raw tracklets and 6 global visual candidates.
- No analysis content or thresholds were reduced for the warm request.

Batch B regression command:

```text
.venv/bin/python -m pytest tests/test_model_worker_pool.py tests/test_persistent_model_transport.py tests/test_lr_asd_client.py tests/test_lr_asd_worker_smoke.py tests/test_validate_speaker_attribution_video.py tests/test_global_person_registrar.py tests/test_active_speaker_contract.py tests/test_active_speaker_fusion.py tests/test_speaker_attribution_shadow_pipeline.py tests/test_final_asr_pipeline_selection.py tests/test_local_diarization.py tests/test_speaker_attribution_contract.py tests/test_session_identity_graph.py tests/test_speaker_attribution_engine.py tests/test_transcript_attributor.py tests/test_asr_diarization_reconciler.py tests/test_media_evidence_speakers.py -q
```

Result:

```text
120 passed in 1.03s
```

Remaining gate:

- Upload shadow transport is complete.
- Live traffic priority exists in the scheduler, but live camera subscription/shared media-clock work is Batch C and is not yet enabled.

## Checkpoint 5 — Shared Upload/Live Media Clock and Transcript Revisions

**Date:** 2026-07-14  
**Status:** Task 8 passed; evidence-only shadow boundary preserved

Implemented behavior:

- Online sessions use the 16 kHz PCM sample count as the authoritative clock; client-declared milliseconds are retained only as drift observations.
- Uploaded recordings use media PTS as the authoritative clock and pass the same recording `clockId` into the upload speaker-attribution shadow.
- One browser recording shares its clock identity across realtime PCM, captured video frames, socket reconnects, and the terminal recording upload.
- Every clocked audio chunk persists `startSample`, `sampleCount`, canonical milliseconds, declared drift, and sync status in the durable journal.
- Clock identity and sample cursor survive process/journal recovery; a reconnect with a different clock ID is rejected.
- Video evidence retains raw PTS/timebase and separately records mapped milliseconds and drift. Drift at or above 500 ms degrades evidence integrity instead of silently rewriting raw evidence.
- Legacy `media-evidence-v2` sessions without clock fields remain accepted and keep their original response shape.
- Realtime transcript segments use stable segment IDs and increasing revisions. Provisional corrections are bounded to 10 seconds; `FINAL` is terminal and rejects later provisional overwrites.
- These media facts remain evidence-only and do not calculate or mutate any score.

Verification:

```text
cd ai-scoring
.venv/bin/python -m py_compile app/services/media_evidence/media_clock.py app/services/media_evidence/realtime_gateway.py app/services/media_evidence/live_finalizer.py app/services/media_evidence/speaker_attribution_shadow.py app/routers/scoring_router.py app/services/pipeline_service.py
.venv/bin/pytest -q tests/test_media_clock.py tests/test_realtime_audio_gateway.py tests/test_realtime_asr_protocol.py tests/test_live_evidence_finalizer.py tests/test_speaker_attribution_shadow_pipeline.py
```

Result:

```text
45 passed in 0.71s
```

Frontend verification:

```text
cd frontend/user
node --test src/utils/realtimeAudioChunkSender.test.js
npm run build
```

Result:

```text
9 passed
vite production build succeeded (3711 modules transformed)
```

Remaining gate:

- Shared timing and revision contracts are complete.
- Public speaker attribution remains disabled until Java versioned persistence, terminal-state protection, and the live camera subscriber/finalizer in Tasks 9 and 11 are complete.

## Checkpoint 6 — Java Versioned Persistence and Terminal Protection

**Date:** 2026-07-14  
**Status:** passed; Java callback storage is ready for shadow snapshots

Implemented behavior:

- Python terminal results now carry the complete score-free `speakerAttribution` snapshot through `finalResult`, instead of returning only a private file receipt.
- Java validates the contract version, snapshot/segment revisions, person types, contestant slots, time ranges, confidence bounds, and every person reference before changing stored rows.
- Stable people, speaker turns, and final transcript segments are replaced inside one transaction.
- Visitors and off-screen people are not capped by the four contestant slots.
- Unknown and overlap rows retain a null `person_id`; raw acoustic labels remain available for audit and fallback.
- An identical revision is idempotent, an older revision is ignored, and no provisional snapshot can overwrite a stored final snapshot even when its numeric revision is higher.
- Invalid references fail before deletion; H2 rollback verification confirmed the prior valid revision remains intact.
- Completed callback replay invokes the new persistence path after legacy transcript/speaker evidence adapters, preserving compatibility with old callbacks that omit `speakerAttribution`.
- Fresh installs receive the columns/tables in the base schema. Existing installations receive an idempotent migration, mirrored into offline and deployment SQL assets and mounted as init step 21.

Java verification:

```text
cd backend
mvn test
```

Result:

```text
249 tests passed; 0 failures; 0 errors
```

Python callback verification:

```text
cd ai-scoring
.venv/bin/pytest -q tests/test_speaker_attribution_shadow_pipeline.py tests/test_session_authoritative_callback.py tests/test_pipeline_authoritative_payload.py tests/test_media_clock.py tests/test_realtime_audio_gateway.py tests/test_realtime_asr_protocol.py tests/test_live_evidence_finalizer.py
```

Result:

```text
58 passed in 0.88s
```

MySQL 8 migration replay:

- Initialized an isolated temporary MySQL 8.0.43 data directory.
- Executed the full fresh-install scoring schema.
- Executed `upgrade_ai_score_speaker_attribution_v1.sql` twice.
- Both executions succeeded; `ai_score_speaker_turn`, nullable raw/person identity columns, and both unique versioned indexes were present.
- The temporary server and data directory were shut down and removed; no business database was touched.

Remaining gate:

- Task 9 is complete and still shadow-only.
- Task 11 must subscribe live camera evidence to the bounded queue and freeze the final multimodal snapshot before any public speaker-attribution cutover.

## Batch C Verification — Live Camera Subscription and Load Shedding

**Date:** 2026-07-14  
**Status:** passed; online camera evidence transport is implemented and remains shadow-only

Implemented behavior:

- Each scoring session now receives one server-generated `media_clock_id`; browser PCM chunks, browser visual evidence, final media upload, and the Python LiveKit subscriber reuse that identity.
- The Python service mints a hidden, subscribe-only LiveKit token scoped to one meeting room and connects directly through the private deployment address `ws://livekit:7880`.
- Only `SOURCE_CAMERA` video publications are subscribed. Screen-share and audio tracks are rejected at this boundary.
- Incoming frames are sampled at a configurable 5–8 FPS, preserve raw PTS/timebase, and enter a bounded shared visual queue.
- Each accepted frame also writes payload-free timing metadata. When the PCM clock is available, the metadata samples its authoritative audio cursor; session finish merges those references into the immutable live evidence snapshot without storing an hour of JPEG files.
- Backlog over three seconds drops the oldest non-key visual evidence first, records exact drop ranges, and marks visual integrity degraded. Audio capture/ASR is explicitly allowed to continue.
- Reconnects retain the original clock identity. A conflicting clock is rejected. Session stop is terminal and idempotent.
- Missing credentials, missing camera, connection failure, and visual overload degrade to `AUDIO_ONLY`/`DEGRADED`; they do not fail or pause official scoring.
- The feature is configured in local/offline/cloud deployment manifests without OSS or public media URLs and remains disabled by default pending Batch D gates.

Real WebRTC integration:

- The pre-existing long-running local LiveKit process advertised stale `node_ip: 172.168.1.173`, so its PeerConnection timed out before media transport.
- `livekit.yaml` was corrected to the documented local default `127.0.0.1`; the already-running process must be restarted before it picks up that change.
- To avoid interrupting the existing service, an isolated LiveKit 1.9.12 process was started on test ports and a synthetic `SOURCE_CAMERA` VP8 track was published through the official Python SDK.
- The subscriber received 7 frames from a 1.6-second 15 FPS source at a 6 FPS target; every frame was `CAMERA`, all used the same clock, the queue stayed bounded, the connection resolved to a real `RM_...` room ID, and shutdown reached `FINAL`.

Verification:

```text
cd ai-scoring
.venv/bin/pytest -q <media evidence, realtime, speaker attribution, LR-ASD, callback suites>
```

Result:

```text
170 passed in 1.33s
```

Frontend verification:

```text
cd frontend/user
node --test src/utils/mediaRecorder.test.js src/utils/realtimeAudioChunkSender.test.js
npm run build
```

Result:

```text
11 passed
vite production build succeeded (3711 modules transformed)
```

Deployment verification:

- `docker compose -f deploy/docker-compose.yml config -q` passed.
- Offline, cloud, development, production, release, LiveKit local, and isolated-test YAML files parsed successfully.

Remaining gate:

- Batch C is complete, but no public person labels are changed.
- Batch D must complete the report presentation contract and the real-video/concurrency/accuracy cutover gates before `SPEAKER_ATTRIBUTION_SHADOW_MODE` can be disabled.

## Checkpoint 7 — Stable Report Person Presentation

**Date:** 2026-07-14  
**Status:** passed; final-person presentation is implemented, while current shadow results remain private

Implemented behavior:

- The Java report contract now exposes `speakerAttributionStatus`, the snapshot revision, stable people, and final versioned transcript segments.
- Stable people are ordered as contestants, visitors, then off-screen people. Contestants use their slot and role where available.
- `UNKNOWN` and `OVERLAP` remain segment states and render as “发言人待确认” and “多人同时发言”; neither state creates a fake person.
- The user report does not render raw acoustic cluster IDs, face-track counts, or a user-side cluster correction control.
- Legacy sessions continue through the existing ASR/speaker-mapping adapter when no final stable-person snapshot exists.
- The report page consumes final speaker segments only when the persisted attribution state is `FINAL`.

Contract fixture coverage:

- `AiScoringSessionReportDetailTest.reportExposesFinalStablePeopleAndSafeUnknownOverlapSegments` verifies final API people and segments.
- `aiScoreMinutesPresentation.test.js` verifies contestant/visitor/off-screen ordering and safe unknown/overlap rendering.
- `AiScoreReportWhy.source.test.js` prevents raw cluster labels or correction controls from returning to the user report.

Verification:

```text
cd backend
mvn -Dtest=AiScoringSessionReportDetailTest,AiScoreSessionControllerTest test
```

Result: `12 tests passed; 0 failures; 0 errors`.

```text
cd frontend/user
node --test src/views/ai-score-report/AiScoreReportWhy.source.test.js src/utils/aiScoreMinutesPresentation.test.js
npm run build
```

Result: `11 tests passed`; Vite production build succeeded with 3711 modules transformed.

Real public-state browser check:

- Session 26 currently has no approved final-person snapshot in its report API.
- The user page correctly rendered `人物转写 0` and `尚无可用转写`, rather than leaking the existing shadow acoustic/AV identities.
- Evidence: `docs/testing/artifacts/checkpoint-7-session-26-shadow-hidden.png`.

Remaining gate:

- Stable-person UI readiness does not authorize publication.
- Task 12 must pass the real-video performance, live concurrency, labeled-accuracy, terminal, and callback gates; otherwise the public switch remains off.

## Checkpoint 8 — End-to-End Shadow Rollout and Cutover Gate

**Date:** 2026-07-14  
**Status:** `NO_GO`; shadow remains private and the public switch was not changed

### Gate implementation

- Added a machine-readable, duration-weighted gate that treats missing independent labels as failure.
- Required thresholds are: external/off-screen speech misattributed to a contestant below 1%, high-confidence accuracy at least 95%, high-confidence coverage at least 50%, at least 600,000 ms of independently labeled material, no duplicate contestant people, live end-to-end P95 at most 3,000 ms, and upload branch at most 720,000 ms.
- Terminal protection, callback replay, and worker crash recovery must all pass.
- The evaluator reports rejection coverage and cannot turn model confidence into ground-truth accuracy.
- The evaluator only reports a decision; `switchMutationPerformed` is always false.

### Complete regression

```text
cd ai-scoring
.venv/bin/python -m pytest -q <30 speaker/media/live/callback suites>
```

Result after the live sampler correction: `203 passed in 1.71s`.

```text
cd backend
mvn test
```

Result: `250 tests passed; 0 failures; 0 errors`.

```text
cd frontend/user
node --test src/utils/*.test.js src/views/ai-score-report/*.test.js
npm run build
```

Result: `78 tests passed`; Vite production build succeeded with 3711 modules transformed.

### Real 55-minute upload result

Command:

```text
cd ai-scoring
/usr/bin/time -l .venv/bin/python scripts/validate_speaker_attribution_video.py \
  --video /Users/liuyixing/Movies/Videos/e9df998256bca0a6cbba604c1390330e.mp4 \
  --audio uploads/real-video-tests/e9df998256bca0a6cbba604c1390330e.wav \
  --output docs/testing/artifacts/checkpoint-8-real-video-e9df-20260714.json
```

Measured result:

- Source: 3,270.792 seconds, 473 MB.
- Worker time: 726,087 ms; wall time: 727.639 seconds.
- Performance gate: failed by 6,087 ms against the 720,000 ms threshold.
- Maximum resident set size: 946,094,080 bytes (about 0.95 GB).
- 768 raw tracklets, 310 eligible tracklets, 11 candidate visual identities, 0 stable visual identities, and 458 unresolved tracklets.
- 577 active intervals, 299 accepted visual links, and 4,631 co-visible links rejected as unsafe.
- Candidate visual identities are not people and were not sent to Java or the user report.
- The existing fused acoustic timeline contains 1,119,034 ms of speech evidence that remains unknown in the safe shadow snapshot.

### One-hour online/concurrency gate

The deterministic one-hour media-clock run processed 90,000 source frames at 25 fps, accepted exactly 21,600 frames at the configured 6 fps, kept the queue at at most 7 frames, dropped 0 frames, recovered one video interruption, and kept audio available.

The run exposed and fixed a sampler drift bug: the old “time since last accepted frame” algorithm produced only 18,000 frames (5 fps) from a 25 fps source. Sampling now advances on fixed target slots and the one-hour regression passes.

Reliability scenarios passed in the targeted suites:

- live work is ordered ahead of queued upload/repair work;
- the queue is bounded and starvation-protected;
- a crashed persistent worker is replaced before the next request;
- provider ASR degradation and video interruption preserve audio/evidence terminal behavior;
- callback replay is idempotent and old progress/revisions cannot overwrite a terminal result.

However, this is a transport/scheduler gate, not a fabricated model-latency result. The current online path has no connected incremental person-attribution consumer, and the default LR-ASD pool has one non-preemptive upload worker. Therefore live end-to-end attribution P95 is correctly recorded as unavailable rather than estimated.

### Shadow comparison and decision

Machine-readable artifact: `docs/testing/artifacts/checkpoint-8-cutover-decision-20260714.json`.

The comparison records 8 legacy acoustic evidence speakers, 11 new visual candidates, and 0 new stable people. The old public output remains authoritative and the switch was not changed.

The final failure reasons are:

1. `LABELED_ACCURACY_UNAVAILABLE` — no independent labeled timeline exists, so 95% accuracy and <1% external-to-contestant error cannot be truthfully measured.
2. `LIVE_P95_UNAVAILABLE` — the incremental online attribution consumer is not connected, so no real end-to-end P95 exists.
3. `UPLOAD_BRANCH_EXCEEDS_720000_MS` — the real 55-minute upload branch measured 726,087 ms.

Current runtime defaults were rechecked as `SPEAKER_ATTRIBUTION_ENABLED=false`, `SPEAKER_ATTRIBUTION_SHADOW_MODE=true`, and one local active-speaker worker. No public flag, Java report data, or user-visible person label was changed by this gate run.

### Required work before the next gate run

- Connect an actual incremental online attribution consumer and isolate its compute from non-preemptive uploads, then measure real P95 under concurrent load.
- Reduce the upload branch by at least 6.087 seconds with margin; target below 10.5 minutes to avoid hardware variance at the 12-minute boundary.
- Build a small, independent, time-coded acceptance set of at least 10 minutes covering contestant turns, visitors, off-screen speech, overlap, occlusion, and unknown rejection. It is a release test asset, not a user correction workflow or a large golden dataset.
- Rerun the same machine gate without changing thresholds. Only a clean `GO` may authorize a separate, explicit public-switch change.
