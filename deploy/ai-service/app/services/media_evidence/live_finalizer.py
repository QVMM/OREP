"""Freeze provisional live facts into one score-free final evidence package."""

from __future__ import annotations

from typing import Any

from .contracts import finalize_evidence_package
from .media_clock import MediaClock, MediaClockError, ProvisionalSegmentLedger
from .speaker_reconciliation import normalize_asr_segments


def _final_realtime_segments(events: list[dict]) -> list[dict]:
    selected: list[dict] = []
    seen: set[tuple] = set()
    ledger = ProvisionalSegmentLedger(correction_horizon_ms=10_000)
    for event_index, event in enumerate(events or []):
        if not isinstance(event, dict):
            continue
        if event.get("type") != "transcript":
            continue
        segment_id = str(event.get("segmentId") or "").strip()
        revision = event.get("revision")
        if segment_id and isinstance(revision, int) and not isinstance(revision, bool):
            structured = dict(event)
            structured["segmentId"] = segment_id
            structured["revision"] = revision
            structured["state"] = (
                "FINAL" if event.get("is_final") is True else "PROVISIONAL"
            )
            observed_at_ms = event.get("observedAtMs")
            if not isinstance(observed_at_ms, int) or isinstance(observed_at_ms, bool):
                observed_at_ms = event_index
            try:
                ledger.accept(structured, observed_at_ms=max(0, observed_at_ms))
            except MediaClockError:
                continue
            continue
        if event.get("is_final") is not True:
            continue
        item = {
            "start": event.get("start"),
            "end": event.get("end"),
            "text": str(event.get("text") or "").strip(),
            "speaker": event.get("speaker"),
            "confidence": event.get("confidence"),
        }
        key = (
            event.get("request_id"),
            item["start"],
            item["end"],
            item["text"],
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
    for event in ledger.values():
        if event.get("state") != "FINAL":
            continue
        item = {
            "start": event.get("start"),
            "end": event.get("end"),
            "text": str(event.get("text") or "").strip(),
            "speaker": event.get("speaker"),
            "confidence": event.get("confidence"),
        }
        key = (event.get("segmentId"), item["start"], item["end"], item["text"])
        if key not in seen:
            seen.add(key)
            selected.append(item)
    selected.sort(
        key=lambda item: (
            float(item.get("start") or 0),
            float(item.get("end") or 0),
            str(item.get("text") or ""),
        )
    )
    return selected


def _visual_evidence(frames: list[dict], clock_snapshot: dict | None = None) -> list[dict]:
    result: list[dict] = []
    media_clock = None
    if isinstance(clock_snapshot, dict):
        try:
            media_clock = MediaClock.from_snapshot(clock_snapshot)
        except MediaClockError:
            media_clock = None
    valid_frames = [item for item in (frames or []) if isinstance(item, dict)]
    valid_frames.sort(
        key=lambda item: (
            float(item.get("timestamp") or 0),
            str(item.get("frame_id") or ""),
        )
    )
    for index, frame in enumerate(valid_frames, start=1):
        timestamp = frame.get("timestamp")
        timestamp_ms = (
            max(0, int(round(float(timestamp) * 1000)))
            if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool)
            else 0
        )
        frame_id = str(frame.get("frame_id") or index)
        timing = None
        if media_clock is not None and frame.get("raw_pts") is not None:
            try:
                timing = media_clock.map_video_pts(
                    raw_pts=frame.get("raw_pts"),
                    timebase_num=frame.get("pts_timebase_num"),
                    timebase_den=frame.get("pts_timebase_den"),
                    observed_audio_sample=frame.get("observed_audio_sample"),
                )
            except MediaClockError:
                timing = None
        item = {
            "evidenceId": f"live-visual-{index}",
            "type": "visual",
            "startMs": timing["mappedMs"] if timing else timestamp_ms,
            "endMs": timing["mappedMs"] if timing else timestamp_ms,
            "frameType": str(frame.get("frame_type") or "interval"),
            "changeMagnitude": frame.get("diff_score"),
            "sourceRef": f"visual-frame:{frame_id}",
            "state": "FINAL",
        }
        if timing is not None:
            item.update(timing)
        result.append(item)
    return result


def _safe_processing_metrics(value: dict | None) -> dict:
    if not isinstance(value, dict):
        return {}
    allowed = ("durationMs", "requestId", "provider", "model", "attempt")
    return {key: value.get(key) for key in allowed if key in value}


def finalize_live_evidence(
    *,
    session_id: str,
    transcript_events: list[dict],
    visual_frames: list[dict],
    gateway_summary: dict | None,
    offline_segments: list[dict] | None = None,
    processing_metrics: dict | None = None,
    **_ignored: Any,
) -> dict:
    """Prefer offline final ASR, otherwise freeze realtime final sentences."""

    gateway = gateway_summary if isinstance(gateway_summary, dict) else {}
    if offline_segments:
        raw_segments = [item for item in offline_segments if isinstance(item, dict)]
        transcript_source = "offline_final"
        normalized_source = "fun-asr"
    else:
        raw_segments = _final_realtime_segments(transcript_events)
        transcript_source = "realtime_final"
        normalized_source = "legacy_realtime"

    normalized = normalize_asr_segments(
        raw_segments,
        source=normalized_source,
        time_unit="seconds",
    )
    transcripts = normalized["segments"]
    visuals = _visual_evidence(visual_frames, gateway.get("mediaClock"))
    missing_sequences = [
        int(value)
        for value in (gateway.get("missingSequences") or [])
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
    ]
    audio_coverage = gateway.get("timelineCoverage")
    if not isinstance(audio_coverage, (int, float)) or isinstance(audio_coverage, bool):
        audio_coverage = 0.0
    audio_coverage = round(max(0.0, min(1.0, float(audio_coverage))), 6)
    gateway_complete = gateway.get("integrityStatus") == "complete" and not missing_sequences
    sync_statuses = {
        str(item.get("syncStatus"))
        for item in visuals
        if item.get("syncStatus") is not None
    }
    media_sync_status = (
        "DEGRADED"
        if "DEGRADED" in sync_statuses
        else "SYNCED"
        if "SYNCED" in sync_statuses
        else "UNAVAILABLE"
    )
    observed_drifts = [
        abs(int(item["driftMs"]))
        for item in visuals
        if isinstance(item.get("driftMs"), int)
        and not isinstance(item.get("driftMs"), bool)
    ]
    evidence_status = (
        "complete"
        if gateway_complete and bool(transcripts) and media_sync_status != "DEGRADED"
        else "evidence_incomplete"
    )

    package = {
        "sessionId": str(session_id),
        "sourceType": "LIVE_ROADSHOW",
        "transcriptSegments": transcripts,
        "speakerTurns": [],
        "speakerIdentities": [],
        "visualEvidence": visuals,
        "deliverySignals": [],
        "contentEvidence": [],
        "integrity": {
            "evidenceStatus": evidence_status,
            "audioCoverage": audio_coverage,
            "videoCoverage": 1.0 if visuals else 0.0,
            "timestampMonotonic": all(
                current["startMs"] <= following["startMs"]
                for current, following in zip(transcripts, transcripts[1:])
            ),
            "diarizationStatus": normalized["diarizationStatus"],
            "detectedSpeakerCount": normalized["detectedSpeakerCount"],
            "unresolvedSpeakerCount": normalized["unresolvedSegmentCount"],
            "overlapSegmentCount": normalized["overlapSegmentCount"],
            "missingAudioSequences": missing_sequences,
            "gatewayIntegrityStatus": str(gateway.get("integrityStatus") or "unavailable"),
            "gatewayDataHash": gateway.get("dataHash"),
            "transcriptSource": transcript_source,
            "mediaClockId": (gateway.get("mediaClock") or {}).get("clockId")
            if isinstance(gateway.get("mediaClock"), dict)
            else None,
            "mediaSyncStatus": media_sync_status,
            "maxObservedDriftMs": max(observed_drifts, default=0),
        },
        "processingMetrics": _safe_processing_metrics(processing_metrics),
    }
    return finalize_evidence_package(package)
