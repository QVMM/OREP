"""Assign ASR words and segments to stable person turns without guessing."""

from __future__ import annotations

from copy import deepcopy


def _time_ms(value: dict, key: str) -> int:
    explicit = f"{key}Ms"
    if value.get(explicit) is not None:
        return max(0, int(round(float(value[explicit]))))
    return max(0, int(round(float(value.get(key) or 0) * 1000)))


def _overlap(start_ms: int, end_ms: int, turn: dict) -> int:
    return max(
        0,
        min(end_ms, int(turn.get("endMs") or 0))
        - max(start_ms, int(turn.get("startMs") or 0)),
    )


def _turn_for_range(start_ms: int, end_ms: int, turns: list[dict]) -> dict:
    ranked = sorted(
        (
            (_overlap(start_ms, end_ms, turn), index, turn)
            for index, turn in enumerate(turns)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    if not ranked or ranked[0][0] <= 0:
        return {
            "personId": None,
            "speakerState": "UNKNOWN",
            "confidence": 0.0,
            "candidatePersonIds": [],
        }
    return ranked[0][2]


def _identity_key(turn: dict) -> tuple:
    return (
        turn.get("personId"),
        str(turn.get("speakerState") or "UNKNOWN"),
        tuple(sorted(str(value) for value in (turn.get("candidatePersonIds") or []))),
    )


def _output_segment(
    *,
    segment_no: int,
    revision: int,
    is_final: bool,
    start_ms: int,
    end_ms: int,
    text: str,
    turn: dict,
    source: str,
    asr_confidence: object = None,
) -> dict:
    state = str(turn.get("speakerState") or "UNKNOWN")
    person_id = turn.get("personId")
    if state in {"UNKNOWN", "OVERLAP"}:
        person_id = None
    result = {
        "segmentId": f"SEG_{segment_no}",
        "revision": int(revision),
        "startMs": int(start_ms),
        "endMs": int(end_ms),
        "text": str(text).strip(),
        "personId": person_id,
        "speakerState": state,
        "speakerConfidence": round(float(turn.get("confidence") or 0), 6),
        "candidatePersonIds": sorted(
            {str(value) for value in (turn.get("candidatePersonIds") or [])}
        ),
        "isFinal": bool(is_final),
        "source": str(source or "asr"),
    }
    if asr_confidence is not None:
        result["asrConfidence"] = asr_confidence
    return result


def _word_groups(segment: dict, turns: list[dict]) -> list[dict]:
    groups: list[dict] = []
    for word in segment.get("words") or []:
        if not isinstance(word, dict) or not str(word.get("text") or ""):
            continue
        start_ms = _time_ms(word, "start")
        end_ms = max(start_ms, _time_ms(word, "end"))
        turn = _turn_for_range(start_ms, end_ms, turns)
        key = _identity_key(turn)
        if groups and groups[-1]["key"] == key:
            groups[-1]["endMs"] = end_ms
            groups[-1]["parts"].append(str(word["text"]))
            groups[-1]["confidences"].append(float(turn.get("confidence") or 0))
        else:
            groups.append(
                {
                    "key": key,
                    "startMs": start_ms,
                    "endMs": end_ms,
                    "parts": [str(word["text"])],
                    "turn": deepcopy(turn),
                    "confidences": [float(turn.get("confidence") or 0)],
                }
            )
    for group in groups:
        if group["confidences"]:
            group["turn"]["confidence"] = sum(group["confidences"]) / len(
                group["confidences"]
            )
    return groups


def attribute_transcript(
    asr_result: dict,
    turns: list[dict],
    *,
    revision: int,
    is_final: bool,
) -> list[dict]:
    """Return deterministic person-aware ASR segments on the shared timeline."""

    if isinstance(revision, bool) or int(revision) < 1:
        raise ValueError("INVALID_ATTRIBUTION_REVISION")
    normalized_turns = sorted(
        (deepcopy(item) for item in turns or [] if isinstance(item, dict)),
        key=lambda item: (
            int(item.get("startMs") or 0),
            int(item.get("endMs") or 0),
            str(item.get("turnId") or ""),
        ),
    )
    pending: list[dict] = []
    for segment in (asr_result or {}).get("segments") or []:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        groups = _word_groups(segment, normalized_turns)
        if groups:
            for group in groups:
                pending.append(
                    {
                        "startMs": group["startMs"],
                        "endMs": group["endMs"],
                        "text": "".join(group["parts"]),
                        "turn": group["turn"],
                        "source": segment.get("source") or asr_result.get("source") or "asr",
                        "asrConfidence": segment.get("confidence"),
                    }
                )
            continue
        start_ms = _time_ms(segment, "start")
        end_ms = max(start_ms, _time_ms(segment, "end"))
        pending.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "text": text,
                "turn": _turn_for_range(start_ms, end_ms, normalized_turns),
                "source": segment.get("source") or asr_result.get("source") or "asr",
                "asrConfidence": segment.get("confidence"),
            }
        )
    pending.sort(key=lambda item: (item["startMs"], item["endMs"], item["text"]))
    return [
        _output_segment(
            segment_no=index,
            revision=int(revision),
            is_final=is_final,
            start_ms=item["startMs"],
            end_ms=item["endMs"],
            text=item["text"],
            turn=item["turn"],
            source=item["source"],
            asr_confidence=item["asrConfidence"],
        )
        for index, item in enumerate(pending, start=1)
    ]
