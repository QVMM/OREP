"""Allow-list adapter from current analysis results to score-free evidence."""

from __future__ import annotations

from typing import Any, Iterable

from .contracts import finalize_evidence_package
from .speaker_reconciliation import normalize_asr_segments


_DELIVERY_FIELDS = ("gesture", "posture", "eye_contact", "expression")


def _legacy_asr_source(value: Any) -> str:
    source = str(value or "file").strip().lower()
    if source in {"file", "upload", "video_file"}:
        return "legacy_file"
    if source in {"realtime", "live", "online"}:
        return "legacy_realtime"
    return source


def _covered_ratio(segments: Iterable[dict], duration_ms: int) -> float:
    if duration_ms <= 0:
        return 0.0

    intervals = sorted(
        (max(0, item["startMs"]), min(duration_ms, item["endMs"]))
        for item in segments
        if item["endMs"] > item["startMs"] and item["startMs"] < duration_ms
    )
    if not intervals:
        return 0.0

    covered = 0
    current_start, current_end = intervals[0]
    for start_ms, end_ms in intervals[1:]:
        if start_ms <= current_end:
            current_end = max(current_end, end_ms)
        else:
            covered += current_end - current_start
            current_start, current_end = start_ms, end_ms
    covered += current_end - current_start
    return round(min(1.0, covered / duration_ms), 6)


def _frame_time_ms(frame: dict) -> int:
    if isinstance(frame.get("timestamp_ms"), (int, float)):
        return max(0, int(round(frame["timestamp_ms"])))
    if isinstance(frame.get("timestamp_sec"), (int, float)):
        return max(0, int(round(float(frame["timestamp_sec"]) * 1000)))
    if isinstance(frame.get("timestamp_min"), (int, float)):
        return max(0, int(round(float(frame["timestamp_min"]) * 60_000)))
    return 0


def _visual_items(video_analysis: dict) -> tuple[list[dict], list[dict], list[dict]]:
    visual_evidence: list[dict] = []
    delivery_signals: list[dict] = []
    content_evidence: list[dict] = []

    frames = video_analysis.get("per_frame") or []
    ordered_frames = sorted(
        (item for item in frames if isinstance(item, dict)),
        key=lambda item: (_frame_time_ms(item), int(item.get("frame") or 0)),
    )
    for index, frame in enumerate(ordered_frames, start=1):
        timestamp_ms = _frame_time_ms(frame)
        source_ref = f"legacy-frame:{frame.get('frame', index)}"
        visual_evidence.append(
            {
                "evidenceId": f"visual-{index}",
                "type": "visual",
                "startMs": timestamp_ms,
                "endMs": timestamp_ms,
                "sourceRef": source_ref,
                "frameNo": frame.get("frame"),
                "provider": str(video_analysis.get("source") or "legacy_video"),
            }
        )

        for signal_name in _DELIVERY_FIELDS:
            raw_signal = frame.get(signal_name)
            if not isinstance(raw_signal, dict):
                continue
            delivery_signals.append(
                {
                    "signal": signal_name,
                    "startMs": timestamp_ms,
                    "endMs": timestamp_ms,
                    "description": str(
                        raw_signal.get("desc") or raw_signal.get("description") or ""
                    ).strip(),
                    "signalValue": raw_signal.get("score"),
                    "confidence": raw_signal.get("confidence"),
                    "sourceRef": source_ref,
                }
            )

        screen = frame.get("screen_content")
        if isinstance(screen, dict):
            screen_type = str(screen.get("screen_type") or "").strip()
            key_text = str(screen.get("key_text") or "").strip()
            if screen_type or key_text:
                content_evidence.append(
                    {
                        "evidenceId": f"screen-{index}",
                        "type": "screen_content",
                        "startMs": timestamp_ms,
                        "endMs": timestamp_ms,
                        "text": key_text,
                        "screenType": screen_type,
                        "sourceRef": source_ref,
                    }
                )

    return visual_evidence, delivery_signals, content_evidence


def _speech_delivery_signals(speech_quality: dict) -> list[dict]:
    result: list[dict] = []
    speech_rate = speech_quality.get("speech_rate")
    if isinstance(speech_rate, dict):
        result.append(
            {
                "signal": "speech_rate",
                "signalValue": speech_rate.get("value"),
                "description": str(speech_rate.get("rating") or "").strip(),
                "sourceRef": "legacy-speech-quality:speech-rate",
            }
        )

    for key in ("pauses", "fillers", "prosody"):
        value = speech_quality.get(key)
        if not isinstance(value, dict):
            continue
        item = {
            "signal": key,
            "sourceRef": f"legacy-speech-quality:{key}",
        }
        if key == "pauses":
            item.update(
                {
                    "signalValue": value.get("count"),
                    "averageDuration": value.get("average_duration"),
                }
            )
        elif key == "fillers":
            item.update(
                {
                    "signalValue": value.get("count"),
                    "examples": list(value.get("words") or []),
                }
            )
        else:
            item.update(
                {
                    "signalValue": value.get("variation"),
                    "enabled": bool(value.get("enabled")),
                }
            )
        result.append(item)
    return result


def _contradiction_evidence(fusion: dict) -> list[dict]:
    result: list[dict] = []
    for index, item in enumerate(fusion.get("contradictions") or [], start=1):
        if not isinstance(item, dict):
            continue
        time_ms = 0
        if isinstance(item.get("time_ms"), (int, float)):
            time_ms = max(0, int(round(item["time_ms"])))
        elif isinstance(item.get("time_sec"), (int, float)):
            time_ms = max(0, int(round(float(item["time_sec"]) * 1000)))
        elif isinstance(item.get("time_min"), (int, float)):
            time_ms = max(0, int(round(float(item["time_min"]) * 60_000)))
        result.append(
            {
                "evidenceId": f"contradiction-{index}",
                "type": "contradiction",
                "startMs": time_ms,
                "endMs": time_ms,
                "text": str(item.get("description") or item.get("text") or "").strip(),
                "sourceRef": f"legacy-fusion:contradiction:{index}",
            }
        )
    return result


def build_legacy_evidence_package(
    *,
    session_id: str,
    source_type: str,
    asr_result: dict | None,
    speech_quality: dict | None,
    video_analysis: dict | None,
    fusion: dict | None,
    processing_metrics: dict | None = None,
    **_ignored: Any,
) -> dict:
    """Build a final package by copying only explicitly approved evidence fields."""

    asr = asr_result if isinstance(asr_result, dict) else {}
    speech = speech_quality if isinstance(speech_quality, dict) else {}
    video = video_analysis if isinstance(video_analysis, dict) else {}
    fused = fusion if isinstance(fusion, dict) else {}

    normalized = normalize_asr_segments(
        asr.get("segments") or [],
        source=_legacy_asr_source(asr.get("source")),
        time_unit="seconds",
    )
    transcript_segments = normalized["segments"]
    visual_evidence, video_signals, screen_evidence = _visual_items(video)

    duration_seconds = asr.get("duration")
    duration_ms = (
        max(0, int(round(float(duration_seconds) * 1000)))
        if isinstance(duration_seconds, (int, float)) and not isinstance(duration_seconds, bool)
        else 0
    )
    timestamp_monotonic = all(
        current["startMs"] <= following["startMs"]
        for current, following in zip(transcript_segments, transcript_segments[1:])
    )

    package = {
        "sessionId": str(session_id),
        "sourceType": str(source_type),
        "transcriptSegments": transcript_segments,
        "speakerTurns": [],
        "speakerIdentities": [],
        "visualEvidence": visual_evidence,
        "deliverySignals": sorted(
            _speech_delivery_signals(speech) + video_signals,
            key=lambda item: (int(item.get("startMs") or 0), str(item.get("signal") or "")),
        ),
        "contentEvidence": sorted(
            screen_evidence + _contradiction_evidence(fused),
            key=lambda item: (item["startMs"], item["evidenceId"]),
        ),
        "integrity": {
            "audioCoverage": _covered_ratio(transcript_segments, duration_ms),
            "videoCoverage": 1.0 if visual_evidence else 0.0,
            "timestampMonotonic": timestamp_monotonic,
            "diarizationStatus": normalized["diarizationStatus"],
            "detectedSpeakerCount": normalized["detectedSpeakerCount"],
            "unresolvedSpeakerCount": normalized["unresolvedSegmentCount"],
            "overlapSegmentCount": normalized["overlapSegmentCount"],
            "frameCount": len(visual_evidence),
            "videoSource": str(video.get("source") or "legacy_video"),
        },
        "processingMetrics": dict(processing_metrics or {}),
    }
    return finalize_evidence_package(package)
