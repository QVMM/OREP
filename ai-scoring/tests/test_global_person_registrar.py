from app.services.media_evidence.global_person_registrar import (
    register_global_visual_identities,
)


def _track(face_id, start, end, *, detections=12, visible=0.9):
    return {
        "faceTrackId": face_id,
        "startMs": start,
        "endMs": end,
        "detectionCount": detections,
        "visibleProbability": visible,
    }


def _link(left, right, similarity):
    return {
        "leftFaceTrackId": left,
        "rightFaceTrackId": right,
        "similarity": similarity,
    }


def test_fragmented_tracks_of_one_person_receive_one_global_visual_identity():
    result = register_global_visual_identities(
        [_track("FACE_7", 9000, 12000), _track("FACE_2", 0, 3000)],
        [_link("FACE_2", "FACE_7", 0.91)],
        co_visible_pairs=[],
        minimum_similarity=0.8,
    )

    assert result["identities"] == [
        {
            "visualIdentityId": "VISUAL_1",
            "faceTrackIds": ["FACE_2", "FACE_7"],
            "firstSeenMs": 0,
            "lastSeenMs": 12000,
            "registrationState": "STABLE",
            "confidence": 0.91,
        }
    ]
    assert {
        item["faceTrackId"]: item["visualIdentityId"]
        for item in result["trackAssignments"]
    } == {"FACE_2": "VISUAL_1", "FACE_7": "VISUAL_1"}


def test_same_frame_people_veto_direct_and_transitive_merges():
    result = register_global_visual_identities(
        [
            _track("FACE_A", 0, 1000),
            _track("FACE_B", 0, 1000),
            _track("FACE_C", 2000, 3000),
        ],
        [
            _link("FACE_A", "FACE_C", 0.95),
            _link("FACE_B", "FACE_C", 0.94),
            _link("FACE_A", "FACE_B", 0.99),
        ],
        co_visible_pairs=[("FACE_A", "FACE_B")],
        minimum_similarity=0.8,
    )

    groups = [set(item["faceTrackIds"]) for item in result["identities"]]
    assert {"FACE_A", "FACE_C"} in groups
    assert {"FACE_B"} in groups
    assert result["diagnostics"]["rejectedCoVisibleLinkCount"] == 2


def test_weak_or_tiny_tracks_are_kept_as_unresolved_evidence():
    result = register_global_visual_identities(
        [
            _track("FACE_GOOD", 0, 1000),
            _track("FACE_TINY", 1500, 1600, detections=1, visible=0.95),
            _track("FACE_BLUR", 2000, 3000, detections=20, visible=0.3),
        ],
        [
            _link("FACE_GOOD", "FACE_TINY", 0.99),
            _link("FACE_GOOD", "FACE_BLUR", 0.99),
        ],
        co_visible_pairs=[],
        minimum_similarity=0.8,
        minimum_detection_count=3,
        minimum_visible_probability=0.6,
    )

    assignments = {
        item["faceTrackId"]: item for item in result["trackAssignments"]
    }
    assert assignments["FACE_GOOD"]["registrationState"] == "CANDIDATE"
    assert assignments["FACE_TINY"] == {
        "faceTrackId": "FACE_TINY",
        "visualIdentityId": None,
        "registrationState": "UNRESOLVED",
        "reason": "INSUFFICIENT_TRACK_QUALITY",
    }
    assert assignments["FACE_BLUR"]["visualIdentityId"] is None
    assert result["diagnostics"]["unresolvedTrackCount"] == 2
    assert result["diagnostics"]["sourceTrackCount"] == 3


def test_registration_is_deterministic_under_input_reordering():
    tracks = [_track("FACE_B", 5000, 6000), _track("FACE_A", 0, 1000)]
    links = [_link("FACE_B", "FACE_A", 0.88)]

    first = register_global_visual_identities(
        tracks, links, co_visible_pairs=[], minimum_similarity=0.8
    )
    second = register_global_visual_identities(
        list(reversed(tracks)),
        list(reversed(links)),
        co_visible_pairs=[],
        minimum_similarity=0.8,
    )

    assert first == second


def test_medium_similarity_merge_remains_candidate_until_independent_evidence():
    result = register_global_visual_identities(
        [_track("FACE_1", 0, 1000), _track("FACE_2", 2000, 3000)],
        [_link("FACE_1", "FACE_2", 0.66)],
        co_visible_pairs=[],
        minimum_similarity=0.60,
        stable_similarity=0.80,
    )

    assert result["identities"][0]["faceTrackIds"] == ["FACE_1", "FACE_2"]
    assert result["identities"][0]["registrationState"] == "CANDIDATE"
    assert all(
        item["registrationState"] == "CANDIDATE"
        for item in result["trackAssignments"]
    )


def test_four_co_visible_anchors_prevent_cross_person_chain_contamination():
    tracks = [
        _track("A0", 0, 1000, detections=100),
        _track("B0", 0, 1000, detections=100),
        _track("C0", 0, 1000, detections=100),
        _track("D0", 0, 1000, detections=100),
        _track("A1", 2000, 3000, detections=80),
        _track("B1", 2000, 3000, detections=80),
        _track("OUTSIDER", 2000, 3000, detections=40),
    ]
    co_visible = [
        (left, right)
        for index, left in enumerate(("A0", "B0", "C0", "D0"))
        for right in ("A0", "B0", "C0", "D0")[index + 1 :]
    ] + [
        ("A1", "B1"),
        ("OUTSIDER", "A1"),
        ("OUTSIDER", "B1"),
    ]
    result = register_global_visual_identities(
        tracks,
        [
            _link("A0", "A1", 0.91),
            _link("B0", "B1", 0.90),
            # This misleading bridge contaminated the old unseeded union graph.
            _link("A1", "B0", 0.89),
            _link("OUTSIDER", "A0", 0.20),
            _link("OUTSIDER", "B0", 0.18),
        ],
        co_visible_pairs=co_visible,
        anchor_track_ids=["A0", "B0", "C0", "D0"],
        minimum_similarity=0.80,
        stable_similarity=0.85,
    )

    stable = [
        set(item["faceTrackIds"])
        for item in result["identities"]
        if item["registrationState"] == "STABLE"
    ]
    assert stable == [
        {"A0", "A1"},
        {"B0", "B1"},
        {"C0"},
        {"D0"},
    ]
    outsider = next(
        item for item in result["trackAssignments"]
        if item["faceTrackId"] == "OUTSIDER"
    )
    assert outsider["registrationState"] == "UNRESOLVED"
    assert outsider["reason"] == "OPEN_SET_NO_IDENTITY_MATCH"
