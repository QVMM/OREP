"""Versioned evidence-only contract shared by upload and live roadshows."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any


CONTRACT_VERSION = "media-evidence-v1"

_EVIDENCE_COLLECTIONS = (
    "transcriptSegments",
    "speakerTurns",
    "speakerIdentities",
    "visualEvidence",
    "deliverySignals",
    "contentEvidence",
)

_FORBIDDEN_SCORE_KEYS = {
    "score",
    "overallscore",
    "dimensionscore",
    "deductedpoints",
    "maxrecoverablepoints",
    "predictedscore",
    "scoreimpact",
}

_HASH_EXCLUDED_KEYS = {
    "snapshothash",
    "processingmetrics",
    "requestid",
    "taskid",
    "signedurl",
    "temporaryurl",
    "createdat",
    "updatedat",
}


class EvidenceContractError(ValueError):
    """Raised when media evidence violates the evidence-only boundary."""


def _normalized_key(key: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def assert_no_score_fields(value: object, path: str = "$") -> None:
    """Reject score-bearing fields anywhere in a media evidence object."""

    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in _FORBIDDEN_SCORE_KEYS:
                raise EvidenceContractError(f"forbidden_score_field:{path}.{key}")
            assert_no_score_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_score_fields(child, f"{path}[{index}]")


def _as_milliseconds(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceContractError(f"invalid_time_value:{path}")
    if isinstance(value, float) and not math.isfinite(value):
        raise EvidenceContractError(f"invalid_time_value:{path}")
    milliseconds = int(round(value))
    if milliseconds < 0:
        raise EvidenceContractError(f"invalid_time_value:{path}")
    return milliseconds


def validate_time_ranges(value: object, path: str = "$") -> None:
    """Validate every explicit startMs/endMs pair recursively."""

    if isinstance(value, dict):
        has_start = "startMs" in value
        has_end = "endMs" in value
        if has_start or has_end:
            if not (has_start and has_end):
                raise EvidenceContractError(f"invalid_time_range:{path}")
            start_ms = _as_milliseconds(value.get("startMs"), f"{path}.startMs")
            end_ms = _as_milliseconds(value.get("endMs"), f"{path}.endMs")
            if end_ms < start_ms:
                raise EvidenceContractError(f"invalid_time_range:{path}")
        for key, child in value.items():
            validate_time_ranges(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_time_ranges(child, f"{path}[{index}]")


def _hash_view(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _hash_view(child)
            for key, child in value.items()
            if _normalized_key(key) not in _HASH_EXCLUDED_KEYS
        }
    if isinstance(value, list):
        return [_hash_view(child) for child in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EvidenceContractError("invalid_numeric_value")
        return round(value, 6)
    return value


def canonical_evidence_json(package: dict) -> str:
    """Return deterministic JSON used for the evidence snapshot hash."""

    if not isinstance(package, dict):
        raise EvidenceContractError("invalid_package_type")
    return json.dumps(
        _hash_view(package),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def finalize_evidence_package(package: dict) -> dict:
    """Validate, freeze and hash one evidence-only package without mutating input."""

    if not isinstance(package, dict):
        raise EvidenceContractError("invalid_package_type")

    result = copy.deepcopy(package)
    result["contractVersion"] = CONTRACT_VERSION
    result["status"] = "FINAL"
    if result.get("speakerAttribution") is not None:
        from .speaker_attribution_contract import normalize_speaker_attribution

        result["speakerAttribution"] = normalize_speaker_attribution(
            result["speakerAttribution"]
        )
    for key in _EVIDENCE_COLLECTIONS:
        result.setdefault(key, [])
        if not isinstance(result[key], list):
            raise EvidenceContractError(f"invalid_collection:{key}")

    assert_no_score_fields(result)
    validate_time_ranges(result)
    canonical = canonical_evidence_json(result)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    result["snapshotHash"] = f"sha256:{digest}"
    return result
