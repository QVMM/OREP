from app.services.media_evidence.active_speaker_fusion import (
    fuse_active_speaker_evidence,
)


def _diarization():
    return {
        "turns": [
            {
                "startMs": 0,
                "endMs": 1000,
                "rawSpeakerId": "SPEAKER_0",
                "sourceClusterId": "SOURCE_4",
            },
            {
                "startMs": 2000,
                "endMs": 3000,
                "rawSpeakerId": "SPEAKER_1",
                "sourceClusterId": "SOURCE_7",
            },
        ],
        "speakers": ["SPEAKER_0", "SPEAKER_1"],
        "detectedSpeakerCount": 2,
        "source": "local_sherpa_onnx",
    }


def _active(intervals, status="completed"):
    return {
        "contractVersion": "lr-asd-evidence-v1",
        "status": status,
        "source": "local_lr_asd",
        "faceTracks": [],
        "activeIntervals": intervals,
    }


def test_merges_two_acoustic_clusters_verified_as_same_visible_person():
    fused = fuse_active_speaker_evidence(
        _diarization(),
        _active(
            [
                {
                    "faceTrackId": "FACE_8",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.94,
                    "visibleProbability": 0.96,
                },
                {
                    "faceTrackId": "FACE_8",
                    "startMs": 2000,
                    "endMs": 3000,
                    "activeProbability": 0.91,
                    "visibleProbability": 0.95,
                },
            ]
        ),
    )

    assert fused["detectedSpeakerCount"] == 1
    assert fused["speakers"] == ["SPEAKER_0"]
    assert {turn["rawSpeakerId"] for turn in fused["turns"]} == {"SPEAKER_0"}
    assert {turn["sourceClusterId"] for turn in fused["turns"]} == {
        "SOURCE_4",
        "SOURCE_7",
    }
    assert all(
        turn["speakerVerification"] == "AUDIO_VISUAL" for turn in fused["turns"]
    )
    assert fused["audioVisualStatus"] == "completed"
    assert fused["mergedAcousticClusterCount"] == 1


def test_merges_acoustic_clusters_by_global_visual_identity_not_short_track():
    fused = fuse_active_speaker_evidence(
        _diarization(),
        _active(
            [
                {
                    "faceTrackId": "FACE_12",
                    "visualIdentityId": "VISUAL_4",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.94,
                    "visibleProbability": 0.96,
                },
                {
                    "faceTrackId": "FACE_87",
                    "visualIdentityId": "VISUAL_4",
                    "startMs": 2000,
                    "endMs": 3000,
                    "activeProbability": 0.91,
                    "visibleProbability": 0.95,
                },
            ]
        ),
    )

    assert fused["detectedSpeakerCount"] == 1
    assert {turn["visualIdentityId"] for turn in fused["turns"]} == {"VISUAL_4"}
    assert [turn["faceTrackId"] for turn in fused["turns"]] == [
        "FACE_12",
        "FACE_87",
    ]
    assert fused["faceIdentityCount"] == 1


def test_does_not_merge_when_visual_votes_are_ambiguous():
    intervals = []
    for start_ms in (0, 2000):
        for face_track_id in ("FACE_0", "FACE_1"):
            intervals.append(
                {
                    "faceTrackId": face_track_id,
                    "startMs": start_ms,
                    "endMs": start_ms + 1000,
                    "activeProbability": 0.9,
                    "visibleProbability": 0.9,
                }
            )

    fused = fuse_active_speaker_evidence(_diarization(), _active(intervals))

    assert fused["detectedSpeakerCount"] == 2
    assert fused["audioVisualStatus"] == "partial"
    assert all(turn["speakerVerification"] == "AUDIO_ONLY" for turn in fused["turns"])


def test_preserves_audio_turns_when_active_speaker_evidence_is_unavailable():
    diarization = _diarization()

    fused = fuse_active_speaker_evidence(
        diarization,
        _active([], status="unavailable"),
    )

    assert fused["turns"] == diarization["turns"]
    assert fused["audioVisualStatus"] == "unavailable"
    assert fused["source"] == "local_sherpa_onnx"


def test_rejects_short_low_coverage_visual_hit_without_overwriting_audio_cluster():
    fused = fuse_active_speaker_evidence(
        _diarization(),
        _active(
            [
                {
                    "faceTrackId": "FACE_0",
                    "startMs": 0,
                    "endMs": 100,
                    "activeProbability": 0.99,
                    "visibleProbability": 0.99,
                }
            ]
        ),
        minimum_temporal_coverage=0.35,
    )

    assert fused["turns"][0]["rawSpeakerId"] == "SPEAKER_0"
    assert fused["turns"][0]["speakerVerification"] == "AUDIO_ONLY"
    assert "faceTrackId" not in fused["turns"][0]


def test_rejects_low_absolute_identity_confidence_even_when_coverage_passes():
    fused = fuse_active_speaker_evidence(
        _diarization(),
        _active(
            [
                {
                    "faceTrackId": "FACE_0",
                    "startMs": 0,
                    "endMs": 500,
                    "activeProbability": 0.7,
                    "visibleProbability": 0.7,
                }
            ]
        ),
        minimum_temporal_coverage=0.35,
        minimum_identity_confidence=0.4,
    )

    assert fused["turns"][0]["speakerVerification"] == "AUDIO_ONLY"
    assert fused["audioVisualDirectCandidateTurnCount"] == 0


def test_maps_distinct_faces_to_distinct_stable_speakers_in_first_seen_order():
    fused = fuse_active_speaker_evidence(
        _diarization(),
        _active(
            [
                {
                    "faceTrackId": "FACE_B",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.9,
                    "visibleProbability": 0.9,
                },
                {
                    "faceTrackId": "FACE_A",
                    "startMs": 2000,
                    "endMs": 3000,
                    "activeProbability": 0.9,
                    "visibleProbability": 0.9,
                },
            ]
        ),
    )

    assert [turn["faceTrackId"] for turn in fused["turns"]] == ["FACE_B", "FACE_A"]
    assert [turn["rawSpeakerId"] for turn in fused["turns"]] == [
        "SPEAKER_0",
        "SPEAKER_1",
    ]
    assert all(turn["identityConfidence"] >= 0.8 for turn in fused["turns"])


def test_single_visual_hit_cannot_be_inherited_across_an_entire_acoustic_cluster():
    diarization = {
        "turns": [
            {"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 2000, "endMs": 3000, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 4000, "endMs": 5000, "rawSpeakerId": "SPEAKER_0"},
        ],
        "speakers": ["SPEAKER_0"],
        "source": "local_sherpa_onnx",
    }
    fused = fuse_active_speaker_evidence(
        diarization,
        _active(
            [
                {
                    "faceTrackId": "FACE_0",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.95,
                    "visibleProbability": 0.95,
                }
            ]
        ),
        minimum_cluster_supporting_turns=2,
        minimum_cluster_support_ms=1500,
    )

    assert all(turn["speakerVerification"] == "AUDIO_ONLY" for turn in fused["turns"])
    assert fused["audioVisualVerifiedTurnCount"] == 0
    assert fused["audioVisualDirectCandidateTurnCount"] == 1
    assert fused["audioVisualRejectedCandidateTurnCount"] == 1


def test_inherited_identity_confidence_includes_absolute_model_evidence_quality():
    diarization = {
        "turns": [
            {"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 2000, "endMs": 3000, "rawSpeakerId": "SPEAKER_0"},
            {"startMs": 4000, "endMs": 5000, "rawSpeakerId": "SPEAKER_0"},
        ],
        "speakers": ["SPEAKER_0"],
        "source": "local_sherpa_onnx",
    }
    intervals = [
        {
            "faceTrackId": "FACE_0",
            "startMs": start_ms,
            "endMs": start_ms + 1000,
            "activeProbability": 0.7,
            "visibleProbability": 0.7,
        }
        for start_ms in (0, 2000)
    ]

    fused = fuse_active_speaker_evidence(
        diarization,
        _active(intervals),
        minimum_cluster_supporting_turns=2,
        minimum_cluster_support_ms=1500,
    )

    inherited = fused["turns"][2]
    assert inherited["speakerVerification"] == "AUDIO_INHERITED"
    assert 0.45 <= inherited["identityConfidence"] <= 0.5
    assert fused["audioVisualDirectTurnCount"] == 2
    assert fused["audioVisualInheritedTurnCount"] == 1
