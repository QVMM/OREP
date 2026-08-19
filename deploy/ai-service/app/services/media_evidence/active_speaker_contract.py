"""Versioned, score-free contract for local audio-visual speaker evidence."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any


CONTRACT_VERSION = "lr-asd-evidence-v1"
ALLOWED_STATUSES = {"completed", "partial", "unavailable", "failed"}


class ActiveSpeakerContractError(ValueError):
    """Raised when the local active-speaker worker returns unsafe evidence."""


def _assert_score_free(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if "score" in str(key).lower():
                raise ActiveSpeakerContractError(
                    f"score_field_forbidden:{path}.{key}"
                )
            _assert_score_free(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_score_free(child, f"{path}[{index}]")


def _timestamp_ms(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActiveSpeakerContractError(f"invalid_timestamp:{field}")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ActiveSpeakerContractError(f"invalid_timestamp:{field}")
    return int(round(number))


def _probability(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ActiveSpeakerContractError(f"invalid_probability:{field}")
    number = float(value)
    if not math.isfinite(number):
        raise ActiveSpeakerContractError(f"invalid_probability:{field}")
    return round(max(0.0, min(1.0, number)), 6)


def _track_id(value: Any, *, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ActiveSpeakerContractError(f"invalid_face_track_id:{field}")
    return result


def _normalize_range(item: dict, *, index: int, kind: str) -> tuple[int, int]:
    start_ms = _timestamp_ms(item.get("startMs"), field=f"{kind}[{index}].startMs")
    end_ms = _timestamp_ms(item.get("endMs"), field=f"{kind}[{index}].endMs")
    if end_ms < start_ms:
        raise ActiveSpeakerContractError(f"invalid_timestamp_range:{kind}[{index}]")
    return start_ms, end_ms


def normalize_active_speaker_result(value: dict) -> dict:
    """Validate one LR-ASD result and return a deterministic evidence object."""

    if not isinstance(value, dict):
        raise ActiveSpeakerContractError("active_speaker_result_must_be_object")
    _assert_score_free(value)
    if value.get("contractVersion") != CONTRACT_VERSION:
        raise ActiveSpeakerContractError("unsupported_contract_version")
    status = str(value.get("status") or "").strip()
    if status not in ALLOWED_STATUSES:
        raise ActiveSpeakerContractError("invalid_active_speaker_status")

    tracks = []
    for index, raw in enumerate(value.get("faceTracks") or []):
        if not isinstance(raw, dict):
            raise ActiveSpeakerContractError(f"invalid_face_track:faceTracks[{index}]")
        start_ms, end_ms = _normalize_range(raw, index=index, kind="faceTracks")
        item = deepcopy(raw)
        item["faceTrackId"] = _track_id(
            raw.get("faceTrackId"), field=f"faceTracks[{index}]"
        )
        item["startMs"] = start_ms
        item["endMs"] = end_ms
        if raw.get("visibleProbability") is not None:
            item["visibleProbability"] = _probability(
                raw.get("visibleProbability"),
                field=f"faceTracks[{index}].visibleProbability",
            )
        if raw.get("meanCenterX") is not None:
            item["meanCenterX"] = _probability(
                raw.get("meanCenterX"),
                field=f"faceTracks[{index}].meanCenterX",
            )
        tracks.append(item)

    intervals = []
    for index, raw in enumerate(value.get("activeIntervals") or []):
        if not isinstance(raw, dict):
            raise ActiveSpeakerContractError(
                f"invalid_active_interval:activeIntervals[{index}]"
            )
        start_ms, end_ms = _normalize_range(raw, index=index, kind="activeIntervals")
        item = deepcopy(raw)
        item["faceTrackId"] = _track_id(
            raw.get("faceTrackId"), field=f"activeIntervals[{index}]"
        )
        item["startMs"] = start_ms
        item["endMs"] = end_ms
        item["activeProbability"] = _probability(
            raw.get("activeProbability"),
            field=f"activeIntervals[{index}].activeProbability",
        )
        item["visibleProbability"] = _probability(
            raw.get("visibleProbability"),
            field=f"activeIntervals[{index}].visibleProbability",
        )
        intervals.append(item)

    tracks.sort(key=lambda item: (item["startMs"], item["endMs"], item["faceTrackId"]))
    intervals.sort(
        key=lambda item: (item["startMs"], item["endMs"], item["faceTrackId"])
    )
    track_ids = {item["faceTrackId"] for item in tracks}
    identities = []
    visual_identity_ids: set[str] = set()
    for index, raw in enumerate(value.get("visualIdentities") or []):
        if not isinstance(raw, dict):
            raise ActiveSpeakerContractError(
                f"invalid_visual_identity:visualIdentities[{index}]"
            )
        identity_id = str(raw.get("visualIdentityId") or "").strip()
        if not identity_id or identity_id in visual_identity_ids:
            raise ActiveSpeakerContractError(
                f"invalid_visual_identity_id:visualIdentities[{index}]"
            )
        state = str(raw.get("registrationState") or "").strip()
        if state not in {"STABLE", "CANDIDATE"}:
            raise ActiveSpeakerContractError(
                f"invalid_registration_state:visualIdentities[{index}]"
            )
        face_ids = sorted(
            {
                str(face_id).strip()
                for face_id in (raw.get("faceTrackIds") or [])
                if str(face_id).strip()
            }
        )
        if not face_ids or any(face_id not in track_ids for face_id in face_ids):
            raise ActiveSpeakerContractError(
                f"unknown_face_track:visualIdentities[{index}]"
            )
        start_ms = _timestamp_ms(
            raw.get("firstSeenMs"),
            field=f"visualIdentities[{index}].firstSeenMs",
        )
        end_ms = _timestamp_ms(
            raw.get("lastSeenMs"),
            field=f"visualIdentities[{index}].lastSeenMs",
        )
        if end_ms < start_ms:
            raise ActiveSpeakerContractError(
                f"invalid_timestamp_range:visualIdentities[{index}]"
            )
        visual_identity_ids.add(identity_id)
        identities.append(
            {
                "visualIdentityId": identity_id,
                "faceTrackIds": face_ids,
                "firstSeenMs": start_ms,
                "lastSeenMs": end_ms,
                "registrationState": state,
                "confidence": _probability(
                    raw.get("confidence"),
                    field=f"visualIdentities[{index}].confidence",
                ),
            }
        )
    identities.sort(
        key=lambda item: (item["firstSeenMs"], item["visualIdentityId"])
    )
    for collection_name, collection in (
        ("faceTracks", tracks),
        ("activeIntervals", intervals),
    ):
        for index, item in enumerate(collection):
            visual_id = str(item.get("visualIdentityId") or "").strip()
            if visual_id and visual_id not in visual_identity_ids:
                raise ActiveSpeakerContractError(
                    f"unknown_visual_identity:{collection_name}[{index}]"
                )
            if visual_id:
                item["visualIdentityId"] = visual_id
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": status,
        "source": "local_lr_asd",
        "reason": str(value.get("reason") or "").strip() or None,
        "faceTracks": tracks,
        "activeIntervals": intervals,
        "visualIdentities": identities,
        "registrationDiagnostics": deepcopy(value.get("registrationDiagnostics"))
        if isinstance(value.get("registrationDiagnostics"), dict)
        else {},
        "processing": deepcopy(value.get("processing"))
        if isinstance(value.get("processing"), dict)
        else {},
    }
