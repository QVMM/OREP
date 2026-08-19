"""Competition binding gate for official and diagnostic scoring runs."""

from __future__ import annotations

from typing import Any


OFFICIAL_SELECTION_SOURCES = {
    "user_selected",
    "registration_binding",
    "project_binding",
}
DIAGNOSTIC_SELECTION_SOURCE = "diagnostic_override"


class TrackConfirmationRequired(ValueError):
    """Raised when a run cannot safely select an official scoring rubric."""


def validate_competition_binding(
    binding: dict[str, Any] | None,
    *,
    publish_official_score: bool,
) -> dict[str, Any]:
    normalized = _normalized_binding(binding or {})
    source = normalized.get("selectionSource")

    if not publish_official_score:
        if source != DIAGNOSTIC_SELECTION_SOURCE:
            raise TrackConfirmationRequired("track_confirmation_required")
        if not normalized.get("trackName") or not normalized.get("ruleVersion") or not normalized.get("ruleHash"):
            raise TrackConfirmationRequired("track_confirmation_required")
        normalized["bindingStatus"] = "diagnostic_assumption"
        normalized["publicationMode"] = "diagnostic"
        return normalized

    if source not in OFFICIAL_SELECTION_SOURCES:
        raise TrackConfirmationRequired("track_confirmation_required")
    required = (
        _has_any(normalized, "competitionId", "competitionName"),
        _has_any(normalized, "trackId", "trackName"),
        _has_any(normalized, "groupId", "groupName"),
        bool(normalized.get("ruleVersion")),
        bool(normalized.get("ruleHash")),
        bool(normalized.get("confirmedAt")),
        bool(normalized.get("confirmedBy")),
    )
    if not all(required):
        raise TrackConfirmationRequired("track_confirmation_required")
    normalized["bindingStatus"] = "confirmed"
    normalized["publicationMode"] = "official"
    return normalized


def _normalized_binding(binding: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "competitionId",
        "competitionName",
        "trackId",
        "trackName",
        "groupId",
        "groupName",
        "ruleVersion",
        "ruleHash",
        "selectionSource",
        "confirmedAt",
        "confirmedBy",
    )
    normalized = {}
    for field in fields:
        value = binding.get(field)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            normalized[field] = text
    return normalized


def _has_any(binding: dict[str, Any], *fields: str) -> bool:
    return any(bool(binding.get(field)) for field in fields)
