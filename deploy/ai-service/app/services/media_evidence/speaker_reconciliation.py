"""Normalize ASR speaker facts without inventing identities."""

from __future__ import annotations

import re
from typing import Any, Iterable

from .contracts import EvidenceContractError


_LEGACY_UNTRUSTED_SPEAKER_SOURCES = {
    "legacy_realtime",
    "legacy_file",
    "fun-asr-realtime-2026-02-28",
}
_MIN_SPEAKER_AUDIO_MS = 250


def _milliseconds(value: Any, *, time_unit: str, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceContractError(f"invalid_time_value:{field}")
    if time_unit == "ms":
        milliseconds = int(round(value))
    elif time_unit == "seconds":
        milliseconds = int(round(float(value) * 1000))
    else:
        raise EvidenceContractError(f"unsupported_time_unit:{time_unit}")
    if milliseconds < 0:
        raise EvidenceContractError(f"invalid_time_value:{field}")
    return milliseconds


def _time_value(segment: dict, *keys: str) -> Any:
    for key in keys:
        if key in segment and segment[key] is not None:
            return segment[key]
    return None


def _speaker_label(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return f"SPEAKER_{value}"
    if isinstance(value, float) and value.is_integer():
        return f"SPEAKER_{int(value)}"

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return f"SPEAKER_{int(text)}"
    match = re.fullmatch(r"speaker[_\s-]?(\d+)", text, flags=re.IGNORECASE)
    if match:
        return f"SPEAKER_{int(match.group(1))}"
    return text


def _display_speaker(raw_speaker_id: str | None) -> str:
    if raw_speaker_id is None:
        return "发言人待确认"
    match = re.fullmatch(r"SPEAKER_(\d+)", raw_speaker_id)
    if match:
        return f"{int(match.group(1)) + 1}号发言人"
    return raw_speaker_id


def _raw_speaker_value(segment: dict, source: str) -> Any:
    if "speaker_id" in segment:
        return segment.get("speaker_id")
    if "speakerId" in segment:
        return segment.get("speakerId")
    if source not in _LEGACY_UNTRUSTED_SPEAKER_SOURCES:
        return segment.get("speaker")
    return None


def _speaker_candidates(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    labels = {_speaker_label(item) for item in value}
    return sorted(item for item in labels if item)


def normalize_asr_segments(
    segments: Iterable[dict],
    *,
    source: str,
    time_unit: str = "seconds",
) -> dict:
    """Return deterministic evidence segments and explicit diarization quality."""

    normalized: list[dict] = []
    known_speakers: set[str] = set()
    unresolved_count = 0
    overlap_count = 0

    for original_index, raw in enumerate(segments or []):
        if not isinstance(raw, dict):
            raise EvidenceContractError(f"invalid_segment:{original_index}")

        start_value = _time_value(raw, "startMs", "begin_time", "start_time", "start")
        end_value = _time_value(raw, "endMs", "end_time", "finish_time", "end")
        if start_value is None or end_value is None:
            raise EvidenceContractError(f"missing_segment_time:{original_index}")

        start_ms = _milliseconds(start_value, time_unit=time_unit, field="start")
        end_ms = _milliseconds(end_value, time_unit=time_unit, field="end")
        if end_ms < start_ms:
            raise EvidenceContractError(f"invalid_time_range:segment:{original_index}")

        speaker_value = _raw_speaker_value(raw, source)
        candidates = _speaker_candidates(speaker_value)
        is_overlap = len(candidates) > 1
        raw_speaker_id = None if is_overlap else _speaker_label(speaker_value)
        if raw_speaker_id:
            known_speakers.add(raw_speaker_id)
        elif not is_overlap:
            unresolved_count += 1

        duration_ms = end_ms - start_ms
        if is_overlap:
            speaker_state = "OVERLAP"
            overlap_count += 1
        elif duration_ms < _MIN_SPEAKER_AUDIO_MS:
            speaker_state = "INSUFFICIENT_AUDIO"
        elif raw_speaker_id:
            speaker_state = "IDENTIFIED_CLUSTER"
        else:
            speaker_state = "UNKNOWN"

        item = {
            "segmentNo": 0,
            "startMs": start_ms,
            "endMs": end_ms,
            "text": str(raw.get("text") or "").strip(),
            "rawSpeakerId": raw_speaker_id,
            "displaySpeaker": _display_speaker(raw_speaker_id),
            "speakerState": speaker_state,
            "speakerCandidates": candidates,
            "source": source,
            "confidence": raw.get("confidence"),
            "_originalIndex": original_index,
        }
        normalized.append(item)

    normalized.sort(key=lambda item: (item["startMs"], item["endMs"], item["_originalIndex"]))
    for segment_no, item in enumerate(normalized, start=1):
        item["segmentNo"] = segment_no
        item.pop("_originalIndex", None)

    if not normalized or (not known_speakers and overlap_count == 0):
        diarization_status = "unavailable"
    elif unresolved_count or overlap_count:
        diarization_status = "partial"
    else:
        diarization_status = "completed"

    return {
        "segments": normalized,
        "speakers": sorted(known_speakers),
        "detectedSpeakerCount": len(known_speakers),
        "unresolvedSegmentCount": unresolved_count,
        "overlapSegmentCount": overlap_count,
        "diarizationStatus": diarization_status,
    }
