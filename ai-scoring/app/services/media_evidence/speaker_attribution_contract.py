"""Versioned, score-free contract for stable session speaker attribution."""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any


CONTRACT_VERSION = "speaker-attribution-v1"
PERSON_TYPES = {"CONTESTANT", "VISITOR", "OFFSCREEN"}
PERSON_STATES = {"OBSERVED", "CANDIDATE", "STABLE", "MERGED", "RETIRED"}
SPEAKER_STATES = {
    "CONFIRMED",
    "PROVISIONAL",
    "OFFSCREEN_CONFIRMED",
    "UNKNOWN",
    "OVERLAP",
}
SNAPSHOT_STATUSES = {"PROVISIONAL", "FINAL"}
TIMEBASES = {"MILLISECONDS"}
MASTER_SOURCES = {"AUDIO_SAMPLE_CLOCK", "MEDIA_PTS"}
SYNC_STATUSES = {"SYNCED", "DRIFTED", "DEGRADED", "UNAVAILABLE"}
_FORBIDDEN_SCORE_KEYS = {
    "score",
    "overallscore",
    "dimensionscore",
    "deductedpoints",
    "maxrecoverablepoints",
    "predictedscore",
    "scoreimpact",
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")


class SpeakerAttributionContractError(ValueError):
    """Raised when a speaker-attribution snapshot is unsafe or inconsistent."""


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _reject_score_fields(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in _FORBIDDEN_SCORE_KEYS:
                raise SpeakerAttributionContractError(
                    f"forbidden_score_field:{path}.{key}"
                )
            _reject_score_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_score_fields(child, f"{path}[{index}]")


def _object(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise SpeakerAttributionContractError(f"invalid_object:{field}")
    return deepcopy(value)


def _collection(value: Any, field: str) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SpeakerAttributionContractError(f"invalid_collection:{field}")
    return [deepcopy(item) for item in value]


def _identifier(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    text = str(value or "").strip()
    if not _SAFE_ID.fullmatch(text):
        raise SpeakerAttributionContractError(f"invalid_identifier:{field}")
    return text


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SpeakerAttributionContractError(f"invalid_integer:{field}")
    return value


def _confidence(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SpeakerAttributionContractError(f"invalid_confidence:{field}")
    result = float(value)
    if not math.isfinite(result) or result < 0 or result > 1:
        raise SpeakerAttributionContractError(f"invalid_confidence:{field}")
    return round(result, 6)


def _enum(value: Any, allowed: set[str], field: str) -> str:
    result = str(value or "").strip().upper()
    if result not in allowed:
        raise SpeakerAttributionContractError(f"invalid_enum:{field}:{result}")
    return result


def _time_range(item: dict, field: str, start_key: str, end_key: str) -> tuple[int, int]:
    start = _integer(item.get(start_key), f"{field}.{start_key}")
    end = _integer(item.get(end_key), f"{field}.{end_key}")
    if end < start:
        raise SpeakerAttributionContractError(f"invalid_time_range:{field}")
    return start, end


def _unique_ids(items: list[dict], key: str, field: str) -> set[str]:
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_id = _identifier(item.get(key), f"{field}[{index}].{key}")
        if item_id in seen:
            raise SpeakerAttributionContractError(f"duplicate_identifier:{field}:{item_id}")
        seen.add(item_id)
    return seen


def _normalize_clock(value: Any) -> dict:
    clock = _object(value, "clock")
    clock["clockId"] = _identifier(clock.get("clockId"), "clock.clockId")
    clock["timebase"] = _enum(clock.get("timebase"), TIMEBASES, "clock.timebase")
    clock["masterSource"] = _enum(
        clock.get("masterSource"), MASTER_SOURCES, "clock.masterSource"
    )
    if clock.get("durationMs") is not None:
        clock["durationMs"] = _integer(clock["durationMs"], "clock.durationMs")
    if clock.get("syncStatus") is not None:
        clock["syncStatus"] = _enum(
            clock["syncStatus"], SYNC_STATUSES, "clock.syncStatus"
        )
    if clock.get("maxObservedDriftMs") is not None:
        clock["maxObservedDriftMs"] = _integer(
            clock["maxObservedDriftMs"], "clock.maxObservedDriftMs"
        )
    return clock


def _normalize_people(items: list[dict]) -> tuple[list[dict], set[str]]:
    person_ids = _unique_ids(items, "personId", "people")
    contestant_slots: set[int] = set()
    for index, item in enumerate(items):
        field = f"people[{index}]"
        item["personId"] = _identifier(item.get("personId"), f"{field}.personId")
        item["personType"] = _enum(item.get("personType"), PERSON_TYPES, f"{field}.personType")
        item["state"] = _enum(item.get("state"), PERSON_STATES, f"{field}.state")
        item["confidence"] = _confidence(item.get("confidence"), f"{field}.confidence")
        first, last = _time_range(item, field, "firstSeenMs", "lastSeenMs")
        item["firstSeenMs"], item["lastSeenMs"] = first, last
        if item["personType"] == "CONTESTANT":
            slot = item.get("contestantSlot")
            if isinstance(slot, bool) or not isinstance(slot, int) or not 1 <= slot <= 4:
                raise SpeakerAttributionContractError(f"invalid_contestant_slot:{field}")
            if slot in contestant_slots:
                raise SpeakerAttributionContractError(f"duplicate_contestant_slot:{slot}")
            contestant_slots.add(slot)
        elif item.get("contestantSlot") is not None:
            raise SpeakerAttributionContractError(f"invalid_contestant_slot:{field}")
        for key in ("faceTrackIds", "bodyTrackIds", "voiceClusterIds"):
            values = item.get(key) or []
            if not isinstance(values, list):
                raise SpeakerAttributionContractError(f"invalid_collection:{field}.{key}")
            item[key] = sorted({_identifier(value, f"{field}.{key}") for value in values})
        if item.get("modelRevision") is not None:
            item["modelRevision"] = _integer(
                item["modelRevision"], f"{field}.modelRevision", minimum=1
            )
    items.sort(key=lambda item: (item["firstSeenMs"], item["personId"]))
    return items, person_ids


def _normalize_turns(items: list[dict], person_ids: set[str]) -> list[dict]:
    _unique_ids(items, "turnId", "turns")
    for index, item in enumerate(items):
        field = f"turns[{index}]"
        item["turnId"] = _identifier(item.get("turnId"), f"{field}.turnId")
        item["startMs"], item["endMs"] = _time_range(item, field, "startMs", "endMs")
        item["speakerState"] = _enum(
            item.get("speakerState"), SPEAKER_STATES, f"{field}.speakerState"
        )
        item["confidence"] = _confidence(item.get("confidence"), f"{field}.confidence")
        item["personId"] = _identifier(item.get("personId"), f"{field}.personId", nullable=True)
        candidates = item.get("candidatePersonIds") or []
        if not isinstance(candidates, list):
            raise SpeakerAttributionContractError(f"invalid_collection:{field}.candidatePersonIds")
        item["candidatePersonIds"] = sorted(
            {_identifier(value, f"{field}.candidatePersonIds") for value in candidates}
        )
        refs = ([item["personId"]] if item["personId"] else []) + item["candidatePersonIds"]
        unknown = [value for value in refs if value not in person_ids]
        if unknown:
            raise SpeakerAttributionContractError(
                f"unknown_person_reference:{field}:{unknown[0]}"
            )
        if item["speakerState"] in {"UNKNOWN", "OVERLAP"} and item["personId"] is not None:
            raise SpeakerAttributionContractError(f"state_requires_null_person:{field}")
    items.sort(key=lambda item: (item["startMs"], item["endMs"], item["turnId"]))
    return items


def _normalize_segments(
    items: list[dict], person_ids: set[str], *, snapshot_revision: int, status: str
) -> list[dict]:
    _unique_ids(items, "segmentId", "segments")
    for index, item in enumerate(items):
        field = f"segments[{index}]"
        item["segmentId"] = _identifier(item.get("segmentId"), f"{field}.segmentId")
        item["revision"] = _integer(item.get("revision"), f"{field}.revision", minimum=1)
        if item["revision"] > snapshot_revision:
            raise SpeakerAttributionContractError(f"segment_revision_ahead:{field}")
        item["startMs"], item["endMs"] = _time_range(item, field, "startMs", "endMs")
        item["text"] = str(item.get("text") or "").strip()
        if not item["text"]:
            raise SpeakerAttributionContractError(f"empty_transcript_text:{field}")
        item["speakerState"] = _enum(
            item.get("speakerState"), SPEAKER_STATES, f"{field}.speakerState"
        )
        item["personId"] = _identifier(item.get("personId"), f"{field}.personId", nullable=True)
        if item["personId"] is not None and item["personId"] not in person_ids:
            raise SpeakerAttributionContractError(
                f"unknown_person_reference:{field}:{item['personId']}"
            )
        if item.get("speakerConfidence") is not None:
            item["speakerConfidence"] = _confidence(
                item["speakerConfidence"], f"{field}.speakerConfidence"
            )
        if not isinstance(item.get("isFinal"), bool):
            raise SpeakerAttributionContractError(f"invalid_boolean:{field}.isFinal")
        if status == "FINAL" and not item["isFinal"]:
            raise SpeakerAttributionContractError(
                f"final_snapshot_contains_provisional_segment:{field}"
            )
        if item["speakerState"] in {"UNKNOWN", "OVERLAP"} and item["personId"] is not None:
            raise SpeakerAttributionContractError(f"state_requires_null_person:{field}")
    items.sort(key=lambda item: (item["startMs"], item["endMs"], item["segmentId"]))
    return items


def normalize_speaker_attribution(value: dict) -> dict:
    """Validate and deterministically normalize one attribution snapshot."""

    result = _object(value, "speakerAttribution")
    _reject_score_fields(result)
    if result.get("contractVersion") != CONTRACT_VERSION:
        raise SpeakerAttributionContractError("invalid_contract_version")
    result["revision"] = _integer(result.get("revision"), "revision", minimum=1)
    result["status"] = _enum(result.get("status"), SNAPSHOT_STATUSES, "status")
    result["clock"] = _normalize_clock(result.get("clock"))
    result["people"], person_ids = _normalize_people(
        _collection(result.get("people"), "people")
    )
    result["turns"] = _normalize_turns(
        _collection(result.get("turns"), "turns"), person_ids
    )
    result["segments"] = _normalize_segments(
        _collection(result.get("segments"), "segments"),
        person_ids,
        snapshot_revision=result["revision"],
        status=result["status"],
    )
    return result
