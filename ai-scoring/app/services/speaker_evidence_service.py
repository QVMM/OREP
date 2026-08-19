"""Build score-free speaker evidence from the authoritative final ASR result."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any


def _milliseconds(segment: dict, key: str) -> int:
    millisecond_key = f"{key}Ms"
    if segment.get(millisecond_key) is not None:
        return int(round(float(segment[millisecond_key])))
    return int(round(float(segment.get(key) or 0) * 1000))


def _speaker_label(raw_speaker_id: str | None, ordinal: int) -> str:
    if raw_speaker_id is None:
        return "发言人待确认"
    try:
        return f"{int(raw_speaker_id.rsplit('_', 1)[1]) + 1}号发言人"
    except (IndexError, ValueError):
        pass
    return f"{ordinal}号发言人"


def _speaker_sort_key(item: dict[str, Any]) -> tuple[int, int | str]:
    raw_speaker_id = item.get("rawSpeakerId")
    if raw_speaker_id is None:
        return (2, "")
    try:
        return (0, int(str(raw_speaker_id).rsplit("_", 1)[1]))
    except (IndexError, ValueError):
        return (1, str(raw_speaker_id))


def build_speaker_evidence(asr_result: dict | None) -> list[dict[str, Any]]:
    """Group transcript evidence only by the ASR provider's speaker cluster.

    This function deliberately does not infer identities from transition phrases and
    does not create any numerical ability or performance score.
    """
    grouped: OrderedDict[str | None, dict[str, Any]] = OrderedDict()
    for raw_segment in (asr_result or {}).get("segments") or []:
        if not isinstance(raw_segment, dict):
            continue
        raw_speaker = raw_segment.get("rawSpeakerId", raw_segment.get("speaker"))
        if raw_speaker is not None:
            raw_speaker = str(raw_speaker).strip() or None

        start_ms = _milliseconds(raw_segment, "start")
        end_ms = max(start_ms, _milliseconds(raw_segment, "end"))
        if raw_speaker not in grouped:
            ordinal = sum(key is not None for key in grouped) + 1
            grouped[raw_speaker] = {
                "rawSpeakerId": raw_speaker,
                "displayName": _speaker_label(raw_speaker, ordinal),
                "roleName": None,
                "matchedName": None,
                "status": "AUTO" if raw_speaker is not None else "UNRESOLVED",
                "source": "final_asr",
                "confidence": None,
                "durationSec": 0.0,
                "evidenceQuotes": [],
                "segments": [],
                "_confidences": [],
            }

        item = grouped[raw_speaker]
        item["durationSec"] += (end_ms - start_ms) / 1000.0
        item["segments"].append({"startMs": start_ms, "endMs": end_ms})
        text = str(raw_segment.get("text") or "").strip()
        if text and len(item["evidenceQuotes"]) < 3:
            item["evidenceQuotes"].append(text)
        confidence = raw_segment.get("confidence")
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            item["_confidences"].append(float(confidence))

    evidence: list[dict[str, Any]] = []
    for item in grouped.values():
        confidences = item.pop("_confidences")
        if confidences:
            item["confidence"] = round(sum(confidences) / len(confidences), 4)
        item["durationSec"] = round(item["durationSec"], 3)
        evidence.append(item)
    evidence.sort(key=_speaker_sort_key)
    return evidence
