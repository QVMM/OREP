from app.services.media_evidence.speaker_attribution_engine import (
    AttributionCandidate,
    AttributionContext,
    AttributionThresholds,
    decide_turn,
)


THRESHOLDS = AttributionThresholds(
    confirmed=0.85,
    provisional=0.70,
    minimum_margin=0.15,
)


def test_confirms_contestant_only_when_absolute_multimodal_evidence_passes():
    decision = decide_turn(
        [
            AttributionCandidate(
                person_id="PERSON_1",
                person_type="CONTESTANT",
                voice_match=0.94,
                active_speaker=0.95,
                visual_identity=0.92,
                temporal_continuity=0.9,
                role_prior=1.0,
            )
        ],
        AttributionContext(),
        THRESHOLDS,
    )

    assert decision.person_id == "PERSON_1"
    assert decision.speaker_state == "CONFIRMED"


def test_four_person_role_prior_cannot_absorb_an_external_voice():
    decision = decide_turn(
        [
            AttributionCandidate(
                person_id="PERSON_1",
                person_type="CONTESTANT",
                voice_match=0.42,
                active_speaker=None,
                visual_identity=None,
                temporal_continuity=0.4,
                role_prior=1.0,
            )
        ],
        AttributionContext(no_visible_active_speaker=True),
        THRESHOLDS,
    )

    assert decision.person_id is None
    assert decision.speaker_state == "UNKNOWN"
    assert decision.reason_code == "INSUFFICIENT_ABSOLUTE_EVIDENCE"


def test_returns_provisional_when_winner_passes_floor_but_not_confirmation():
    decision = decide_turn(
        [
            AttributionCandidate(
                person_id="PERSON_5",
                person_type="VISITOR",
                voice_match=0.76,
                active_speaker=0.79,
                visual_identity=0.73,
                temporal_continuity=0.75,
            )
        ],
        AttributionContext(),
        THRESHOLDS,
    )

    assert decision.person_id == "PERSON_5"
    assert decision.speaker_state == "PROVISIONAL"


def test_conflict_veto_returns_unknown_even_for_high_scores():
    decision = decide_turn(
        [
            AttributionCandidate(
                person_id="PERSON_2",
                person_type="CONTESTANT",
                voice_match=0.96,
                active_speaker=0.96,
                visual_identity=0.96,
                temporal_continuity=0.96,
            )
        ],
        AttributionContext(conflicts={"CO_VISIBLE_CONFLICT"}),
        THRESHOLDS,
    )

    assert decision.person_id is None
    assert decision.speaker_state == "UNKNOWN"
    assert decision.conflicts == ["CO_VISIBLE_CONFLICT"]


def test_overlap_never_forces_a_single_person():
    decision = decide_turn(
        [
            AttributionCandidate("PERSON_1", "CONTESTANT", voice_match=0.9),
            AttributionCandidate("PERSON_2", "CONTESTANT", voice_match=0.88),
        ],
        AttributionContext(overlap=True),
        THRESHOLDS,
    )

    assert decision.person_id is None
    assert decision.speaker_state == "OVERLAP"
    assert decision.candidate_person_ids == ["PERSON_1", "PERSON_2"]


def test_confirms_enrolled_offscreen_voice_without_a_visible_face():
    decision = decide_turn(
        [
            AttributionCandidate(
                person_id="PERSON_6",
                person_type="OFFSCREEN",
                voice_match=0.94,
                temporal_continuity=0.9,
            )
        ],
        AttributionContext(no_visible_active_speaker=True),
        THRESHOLDS,
    )

    assert decision.person_id == "PERSON_6"
    assert decision.speaker_state == "OFFSCREEN_CONFIRMED"


def test_small_winner_margin_downgrades_to_unknown():
    decision = decide_turn(
        [
            AttributionCandidate("PERSON_1", "CONTESTANT", voice_match=0.91, active_speaker=0.9),
            AttributionCandidate("PERSON_2", "CONTESTANT", voice_match=0.89, active_speaker=0.88),
        ],
        AttributionContext(),
        THRESHOLDS,
    )

    assert decision.person_id is None
    assert decision.speaker_state == "UNKNOWN"
    assert decision.reason_code == "INSUFFICIENT_WINNER_MARGIN"
