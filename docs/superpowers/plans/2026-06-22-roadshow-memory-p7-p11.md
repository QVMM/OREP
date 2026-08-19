# Roadshow Memory P7-P11 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the P7-P11 continuous roadshow scoring memory loop so OREP can show prior issue rechecks, new issues, full-score gaps, jury-ready evidence, training plan status, and long-term project evolution.

**Architecture:** Reuse existing `project_roadshow_binding`, `ai_score_report`, and `project_review_issue` as the first memory ledger. Add a backend memory analyzer and a project-team endpoint that aggregates completed AI reports by team. Later phases can replace heuristics with dedicated memory tables without changing the front-end contract.

**Tech Stack:** Spring Boot Java 21, JdbcTemplate, existing project team API, Vue 3 AI score/project team screens, Python AI scoring payloads already producing `score_calibration`.

---

## Task 1: Backend Memory Analyzer ✅

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/RoadshowMemoryAnalyzer.java`
- Test: `backend/src/test/java/com/orep/backend/service/RoadshowMemoryAnalyzerTest.java`

Build a pure Java analyzer that accepts ordered AI report rows and returns:
- `rounds`
- `priorIssueReview`
- `newIssues`
- `fullScoreGap`
- `trainingPlan`
- `timeline`

## Task 2: Project Team Memory Endpoint ✅

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/ProjectTeamController.java`

Expose:

```text
GET /api/project-teams/{teamId}/roadshow-memory
```

The endpoint should:
- Sync AI review issues from completed reports.
- Query bound roadshow meetings for the team.
- Parse `critical_issues_json`, `improvement_priorities_json`, `score_calibration_json`.
- Return the analyzer contract.

## Task 3: Frontend Project Team Memory Panel ✅

**Files:**
- Modify project team dashboard view after locating the active page.

Show:
- 上轮问题复检
- 本轮新增问题
- 为什么不是100
- 下一轮训练计划
- 长期成长时间线

## Task 4: Jury-Ready Evidence Contract ✅

**Files:**
- Modify `ai-scoring/app/services/jury/snapshot_service.py`
- Modify `ai-scoring/app/services/jury/scoring_service.py`

Pass memory summary into jury snapshots without leaking official final score as an anchoring input.

## Task 5: Long-Term Timeline Upgrade ✅

**Files:**
- Add SQL only after Task 1-4 stabilize.

Introduce dedicated tables only if existing ledger is insufficient:
- `project_assessment`
- `score_memory_item`
- `score_evidence_anchor`
- `improvement_task`

---

## Current Execution Slice

This session completed Task 1-5 as the first P7-P11 implementation slice:
- Backend now exposes a continuous roadshow memory contract from existing ledgers.
- Project team dashboard shows prior issue rechecks, new issues, full-score gap reasons, training acceptance, and timeline.
- AI jury snapshot v2 can receive sanitized memory context without leaking score anchors.
- Long-term memory tables are available as SQL resources but are not yet wired into runtime writes.

## Follow-Up Backlog

- Wire `project_assessment`, `score_memory_item`, `score_evidence_anchor`, and `improvement_task` into backend writes after the current ledger contract is stable in real data.
- Add deeper backend integration tests for `/api/project-teams/{teamId}/roadshow-memory` with incomplete reports and permission-denied boundaries.
- Expand evidence anchors from raw AI result JSON into precise transcript timestamps, key frames, screen OCR, and uploaded local recording playback links.
- Add per-memory-item confidence and dispute status so teachers can override AI conclusions before they affect training tasks.
- Build a nightly reconciliation job that backfills memory tables from historical `ai_score_report` and `project_roadshow_binding` rows.

## 2026-06-22 Continuation

Completed:
- Added analyzer status fields: `EMPTY`, `SINGLE_ROUND`, `MULTI_ROUND`.
- Added a single-round frontend empty state so schools see “下一轮会复检本轮扣分项” instead of an ambiguous empty panel.
- Added controller-level coverage for `/api/project-teams/{teamId}/roadshow-memory`.
- Added AI jury support for manual `roadshow_memory` input on `POST /api/ai/jury/{meeting_id}/start`; the snapshot keeps issue continuity but strips score anchors.
- Added first-pass evidence anchors for memory items:
  - Backend roadshow memory now emits anchors from AI critical issues, highlights, transcript, speech quality, and result file path.
  - Analyzer attaches anchors to prior issue rechecks and new issues.
  - Project team dashboard displays compact evidence chips below memory items.
  - AI jury snapshot keeps sanitized evidence anchors while stripping score-like fields.

Verified:
- `mvn -q -Dtest=RoadshowMemoryAnalyzerTest,ProjectTeamControllerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`
- `npm run build` in `frontend/user`

Remaining:
- Persist anchors into `score_evidence_anchor` once long-term memory tables are wired into runtime writes.
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.

## 2026-06-22 Precision Anchor Continuation

Completed:
- Added `AiResultEvidenceAnchorExtractor` to parse raw AI result JSON into precise anchors:
  - `transcript_segment` from `asr.segments`
  - `key_frame` from `video_analysis.per_frame`
  - `screen_ocr` from `video_analysis.aggregates.screen_content_summary` and `fusion.screen_content_summary`
  - `fusion_timeline` from `fusion.timeline`
- `ProjectTeamService` now tries precise raw-result anchors first when `ai_score_report.result_path` exists, then falls back to report-level anchors.
- Project team UI recognizes the new anchor types: 转写片段、关键帧、屏幕识别、融合时间线.

Verified:
- `mvn -q -Dtest=AiResultEvidenceAnchorExtractorTest,RoadshowMemoryAnalyzerTest,ProjectTeamControllerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`
- `npm run build` in `frontend/user`

## 2026-06-22 Local Recording Anchor Continuation

Completed:
- Added `RecordingEvidenceAnchorBuilder` to convert READY meeting recordings into playback anchors:
  - `recording_video` -> `/api/recording/{id}/stream?file=video`
  - `recording_camera` -> `/api/recording/{id}/stream?file=camera`
  - `recording_screen` -> `/api/recording/{id}/stream?file=screen`
  - `recording_audio` -> `/api/recording/{id}/stream?file=audio`
- `ProjectTeamService` now queries recent READY recordings for each roadshow meeting and appends playback anchors to the memory evidence list.
- Project team UI recognizes the new recording anchor types: 完整录制、摄像头、屏幕录制、音频.

Verified:
- `mvn -q -Dtest=RecordingEvidenceAnchorBuilderTest,AiResultEvidenceAnchorExtractorTest,RoadshowMemoryAnalyzerTest,ProjectTeamControllerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`
- `npm run build` in `frontend/user`

Remaining:
- Persist generated anchors into `score_evidence_anchor` for audit history instead of recomputing on every dashboard load.
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.

## 2026-06-22 Clickable Evidence Continuation

Completed:
- Evidence chips in the project team memory panel are now clickable.
- Recording chips fetch `/api/recording/{id}/stream?file=...` through the authenticated request client, convert the response to a Blob URL, and open it in `FilePreview`.
- `FilePreview` now supports audio playback, so `recording_audio` anchors can be inspected directly.
- Non-recording anchors open a lightweight evidence detail dialog showing type, meeting id, source reference, and summary.

Verified:
- `npm run build` in `frontend/user`
- `mvn -q -Dtest=RecordingEvidenceAnchorBuilderTest,AiResultEvidenceAnchorExtractorTest,RoadshowMemoryAnalyzerTest,ProjectTeamControllerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`

Remaining:
- Add a dedicated AI-result excerpt viewer for key-frame, OCR, and fusion timeline anchors.
- Persist generated anchors into `score_evidence_anchor` for audit history instead of recomputing on every dashboard load.
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.

## 2026-06-22 AI Result Excerpt Continuation

Completed:
- Added `AiResultEvidenceAnchorExtractor.extractExcerpt(...)` to read raw AI result snippets by evidence `sourceRef`.
- Added `GET /api/project-teams/{teamId}/evidence-excerpt` with team access checks and report/team binding validation.
- Project team evidence dialog now loads AI raw excerpts for non-recording anchors and shows the matched summary plus raw JSON.
- Existing recording/timestamp behavior remains the primary path when a sibling recording is available.

Verified:
- `mvn -q -Dtest=AiResultEvidenceAnchorExtractorTest,ProjectTeamControllerTest,RecordingEvidenceAnchorBuilderTest,RoadshowMemoryAnalyzerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`
- `npm run build` in `frontend/user`

Remaining:
- Persist generated anchors into `score_evidence_anchor` for audit history instead of recomputing on every dashboard load.
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.
- Consider key-frame image preview if raw result files expose frame image paths.

## 2026-06-22 Evidence Anchor Persistence Continuation

Completed:
- Added `ScoreEvidenceAnchorStore` to persist generated evidence anchors into long-term memory tables.
- `ProjectTeamService` now initializes `create_roadshow_memory_tables.sql` during schema setup.
- Continuous roadshow memory now syncs each completed AI roadshow into `project_assessment`.
- Evidence anchors are attached to a system memory item `ROUND_EVIDENCE / AI评分证据快照` and written to `score_evidence_anchor`.
- Repeated loads reuse persisted anchors and do not duplicate old rows.
- If new anchors appear later, such as local recording becoming READY after AI result anchors were already stored, the store appends only the new anchors.
- If persistence fails or tables are unavailable, the UI still receives generated anchors as a safe fallback.

Verified:
- `mvn -q -Dtest=ScoreEvidenceAnchorStoreTest,AiResultEvidenceAnchorExtractorTest,ProjectTeamControllerTest,RecordingEvidenceAnchorBuilderTest,RoadshowMemoryAnalyzerTest test && mvn -q -DskipTests compile`

Remaining:
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.
- Consider key-frame image preview if raw result files expose frame image paths.

## 2026-06-22 Timestamp Seek Continuation

Completed:
- `FilePreview` now accepts `startTime` and seeks video/audio previews after metadata loads.
- Project team evidence chips parse anchor references such as `00:12.3-00:18.8`, `00:00:32`, and `frame-001@00:31.5`.
- Clicking a transcript/fusion/key-frame anchor will open a sibling recording anchor from the same memory item and seek to the parsed timestamp when one is available.
- If no sibling recording is available, the anchor still opens the lightweight evidence detail dialog.

Verified:
- `npm run build` in `frontend/user`
- `mvn -q -Dtest=RecordingEvidenceAnchorBuilderTest,AiResultEvidenceAnchorExtractorTest,RoadshowMemoryAnalyzerTest,ProjectTeamControllerTest test && mvn -q -DskipTests compile`
- `python -m pytest tests/test_ai_jury_services.py tests/test_competition_calibration_service.py -q`

Remaining:
- Add a dedicated AI-result excerpt viewer for key-frame, OCR, and fusion timeline anchors.
- Persist generated anchors into `score_evidence_anchor` for audit history instead of recomputing on every dashboard load.
- Add teacher override/dispute flow for AI conclusions before recovered score affects training tasks.
