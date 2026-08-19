import pytest

from app.services.media_evidence.session_identity_graph import (
    IdentityGraphConflict,
    MergeEvidence,
    ObservationRef,
    SessionIdentityGraph,
)


def test_four_contestant_slots_are_unbound_priors_not_a_people_limit():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=4)

    assert [item.contestant_slot for item in graph.contestant_slots()] == [1, 2, 3, 4]
    visitor = graph.create_person("VISITOR", first_seen_ms=1000)
    offscreen = graph.create_person("OFFSCREEN", first_seen_ms=1200)

    assert visitor.person_id == "PERSON_5"
    assert offscreen.person_id == "PERSON_6"
    assert len(graph.people()) == 6


def test_one_person_accepts_multiple_face_body_and_voice_aliases():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=1)

    graph.attach_observation(
        "PERSON_1", ObservationRef("FACE", "FACE_1", 0, 1000, 0.9)
    )
    graph.attach_observation(
        "PERSON_1", ObservationRef("FACE", "FACE_19", 3000, 4000, 0.88)
    )
    graph.attach_observation(
        "PERSON_1", ObservationRef("VOICE", "VOICE_1", 0, 2000, 0.91)
    )
    graph.attach_observation(
        "PERSON_1", ObservationRef("VOICE", "VOICE_7", 5000, 7000, 0.86)
    )
    graph.attach_observation(
        "PERSON_1", ObservationRef("BODY", "BODY_2", 0, 7000, 0.8)
    )

    person = graph.person("PERSON_1")
    assert person.face_track_ids == {"FACE_1", "FACE_19"}
    assert person.voice_cluster_ids == {"VOICE_1", "VOICE_7"}
    assert person.body_track_ids == {"BODY_2"}


def test_merge_requires_independent_evidence_and_preserves_target_id():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=0)
    target = graph.create_person("OFFSCREEN", first_seen_ms=0)
    source = graph.create_person("VISITOR", first_seen_ms=3000)

    merged = graph.merge_people(
        target.person_id,
        source.person_id,
        MergeEvidence(
            modalities={"VOICE", "ACTIVE_SPEAKER"},
            confidence=0.91,
            reason="OFFSCREEN_BECAME_VISIBLE",
        ),
    )
    graph.upgrade_person_type(target.person_id, "VISITOR")

    assert merged.person_id == target.person_id
    assert graph.person(source.person_id).state == "MERGED"
    assert graph.person(target.person_id).person_type == "VISITOR"


def test_simultaneous_visible_tracks_veto_merge():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=0)
    left = graph.create_person("VISITOR", first_seen_ms=0)
    right = graph.create_person("VISITOR", first_seen_ms=0)
    graph.attach_observation(
        left.person_id, ObservationRef("FACE", "FACE_LEFT", 0, 2000, 0.9)
    )
    graph.attach_observation(
        right.person_id, ObservationRef("FACE", "FACE_RIGHT", 500, 1500, 0.9)
    )

    with pytest.raises(IdentityGraphConflict, match="CO_VISIBLE_CONFLICT"):
        graph.merge_people(
            left.person_id,
            right.person_id,
            MergeEvidence(
                modalities={"FACE", "VOICE"}, confidence=0.95, reason="similar"
            ),
        )


def test_single_weak_modality_cannot_merge_people():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=0)
    left = graph.create_person("VISITOR", first_seen_ms=0)
    right = graph.create_person("VISITOR", first_seen_ms=1000)

    with pytest.raises(IdentityGraphConflict, match="INSUFFICIENT_MERGE_EVIDENCE"):
        graph.merge_people(
            left.person_id,
            right.person_id,
            MergeEvidence(modalities={"VOICE"}, confidence=0.7, reason="nearest"),
        )


def test_snapshot_is_accepted_by_the_versioned_contract():
    graph = SessionIdentityGraph(session_id="26", contestant_slots=4)
    graph.attach_observation(
        "PERSON_1", ObservationRef("FACE", "FACE_1", 0, 3000, 0.9)
    )

    snapshot = graph.snapshot(
        revision=1,
        status="PROVISIONAL",
        clock={
            "clockId": "26",
            "timebase": "MILLISECONDS",
            "masterSource": "MEDIA_PTS",
            "durationMs": 3000,
        },
    )

    assert snapshot["contractVersion"] == "speaker-attribution-v1"
    assert len(snapshot["people"]) == 4
