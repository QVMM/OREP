"""Evidence-gated person decision engine for one speech turn."""

from __future__ import annotations

from dataclasses import dataclass, field


PERSON_TYPES = {"CONTESTANT", "VISITOR", "OFFSCREEN"}
HARD_CONFLICTS = {
    "CO_VISIBLE_CONFLICT",
    "OVERLAPPING_DISTINCT_VOICES",
    "CLOCK_DRIFT_SEVERE",
    "CROSS_MODAL_IDENTITY_CONFLICT",
}


@dataclass(frozen=True)
class AttributionThresholds:
    confirmed: float = 0.85
    provisional: float = 0.70
    minimum_margin: float = 0.15
    offscreen_voice_confirmed: float = 0.90

    def __post_init__(self) -> None:
        values = (
            self.confirmed,
            self.provisional,
            self.minimum_margin,
            self.offscreen_voice_confirmed,
        )
        if any(not 0 <= float(value) <= 1 for value in values):
            raise ValueError("INVALID_ATTRIBUTION_THRESHOLD")
        if self.confirmed < self.provisional:
            raise ValueError("CONFIRMED_THRESHOLD_BELOW_PROVISIONAL")


@dataclass(frozen=True)
class AttributionCandidate:
    person_id: str
    person_type: str
    voice_match: float | None = None
    active_speaker: float | None = None
    visual_identity: float | None = None
    temporal_continuity: float | None = None
    role_prior: float = 0.0

    def __post_init__(self) -> None:
        if not str(self.person_id).strip():
            raise ValueError("EMPTY_PERSON_ID")
        normalized_type = str(self.person_type).upper()
        if normalized_type not in PERSON_TYPES:
            raise ValueError(f"INVALID_PERSON_TYPE:{normalized_type}")
        object.__setattr__(self, "person_type", normalized_type)
        for field_name in (
            "voice_match",
            "active_speaker",
            "visual_identity",
            "temporal_continuity",
            "role_prior",
        ):
            value = getattr(self, field_name)
            if value is not None and not 0 <= float(value) <= 1:
                raise ValueError(f"INVALID_CANDIDATE_VALUE:{field_name}")


@dataclass(frozen=True)
class AttributionContext:
    overlap: bool = False
    no_visible_active_speaker: bool = False
    conflicts: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class AttributionDecision:
    person_id: str | None
    speaker_state: str
    confidence: float
    candidate_person_ids: list[str]
    component_evidence: dict[str, float]
    conflicts: list[str]
    reason_code: str


def _component_values(candidate: AttributionCandidate) -> dict[str, tuple[float, float]]:
    configured = {
        "voiceMatch": (candidate.voice_match, 0.35),
        "activeSpeaker": (candidate.active_speaker, 0.30),
        "visualIdentity": (candidate.visual_identity, 0.25),
        "temporalContinuity": (candidate.temporal_continuity, 0.10),
    }
    return {
        key: (float(value), weight)
        for key, (value, weight) in configured.items()
        if value is not None
    }


def _score(candidate: AttributionCandidate, thresholds: AttributionThresholds) -> tuple[float, dict[str, float]]:
    components = _component_values(candidate)
    total_weight = sum(weight for _, weight in components.values())
    if total_weight <= 0:
        return 0.0, {}
    base = sum(value * weight for value, weight in components.values()) / total_weight
    # A role prior may stabilize an already credible decision, but can never
    # create a contestant match from weak evidence.
    role_bonus = (
        min(0.03, float(candidate.role_prior) * 0.03)
        if base >= thresholds.provisional
        else 0.0
    )
    evidence = {key: round(value, 6) for key, (value, _) in components.items()}
    if role_bonus:
        evidence["rolePriorBonus"] = round(role_bonus, 6)
    return round(min(1.0, base + role_bonus), 6), evidence


def _has_absolute_evidence(
    candidate: AttributionCandidate,
    score: float,
    thresholds: AttributionThresholds,
) -> bool:
    if candidate.person_type == "OFFSCREEN":
        return (
            candidate.voice_match is not None
            and candidate.voice_match >= thresholds.offscreen_voice_confirmed
        )
    biometric_count = sum(
        value is not None
        for value in (
            candidate.voice_match,
            candidate.active_speaker,
            candidate.visual_identity,
        )
    )
    return score >= thresholds.provisional and biometric_count >= 2


def decide_turn(
    candidates: list[AttributionCandidate],
    context: AttributionContext,
    thresholds: AttributionThresholds | None = None,
) -> AttributionDecision:
    """Choose a person only after validity, margin, and conflict gates pass."""

    thresholds = thresholds or AttributionThresholds()
    unique_candidates = {candidate.person_id: candidate for candidate in candidates}
    candidate_ids = sorted(unique_candidates)
    if context.overlap:
        return AttributionDecision(
            None,
            "OVERLAP",
            0.0,
            candidate_ids,
            {},
            sorted(context.conflicts),
            "OVERLAPPING_SPEECH",
        )
    hard_conflicts = sorted(set(context.conflicts) & HARD_CONFLICTS)
    if hard_conflicts:
        return AttributionDecision(
            None,
            "UNKNOWN",
            0.0,
            candidate_ids,
            {},
            hard_conflicts,
            "CONFLICT_VETO",
        )
    ranked = []
    for candidate in unique_candidates.values():
        score, evidence = _score(candidate, thresholds)
        ranked.append((score, candidate.person_id, candidate, evidence))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    if not ranked:
        return AttributionDecision(
            None, "UNKNOWN", 0.0, [], {}, [], "NO_PERSON_CANDIDATE"
        )
    winner_score, _, winner, winner_evidence = ranked[0]
    if not _has_absolute_evidence(winner, winner_score, thresholds):
        return AttributionDecision(
            None,
            "UNKNOWN",
            winner_score,
            [item[1] for item in ranked],
            winner_evidence,
            [],
            "INSUFFICIENT_ABSOLUTE_EVIDENCE",
        )
    second_score = ranked[1][0] if len(ranked) > 1 else 0.0
    if len(ranked) > 1 and winner_score - second_score < thresholds.minimum_margin:
        return AttributionDecision(
            None,
            "UNKNOWN",
            winner_score,
            [item[1] for item in ranked],
            winner_evidence,
            [],
            "INSUFFICIENT_WINNER_MARGIN",
        )
    if winner.person_type == "OFFSCREEN" and context.no_visible_active_speaker:
        state = "OFFSCREEN_CONFIRMED"
    elif winner_score >= thresholds.confirmed:
        state = "CONFIRMED"
    else:
        state = "PROVISIONAL"
    return AttributionDecision(
        winner.person_id,
        state,
        winner_score,
        [item[1] for item in ranked],
        winner_evidence,
        [],
        f"{state}_BY_EVIDENCE",
    )
