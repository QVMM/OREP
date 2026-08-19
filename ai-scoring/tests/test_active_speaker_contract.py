import math

import pytest

from app.services.media_evidence.active_speaker_contract import (
    ActiveSpeakerContractError,
    normalize_active_speaker_result,
)


def test_normalizes_valid_lr_asd_result_deterministically():
    result = normalize_active_speaker_result(
        {
            "contractVersion": "lr-asd-evidence-v1",
            "status": "completed",
            "faceTracks": [
                {"faceTrackId": "FACE_1", "startMs": 500, "endMs": 1000},
                {"faceTrackId": "FACE_0", "startMs": 0, "endMs": 500},
            ],
            "activeIntervals": [
                {
                    "faceTrackId": "FACE_1",
                    "startMs": 500,
                    "endMs": 900,
                    "activeProbability": 0.91,
                    "visibleProbability": 0.98,
                },
                {
                    "faceTrackId": "FACE_0",
                    "startMs": 100,
                    "endMs": 400,
                    "activeProbability": 0.81,
                    "visibleProbability": 0.88,
                },
            ],
            "processing": {"device": "mps", "durationMs": 123},
        }
    )

    assert result["source"] == "local_lr_asd"
    assert [item["faceTrackId"] for item in result["faceTracks"]] == [
        "FACE_0",
        "FACE_1",
    ]
    assert result["activeIntervals"][1]["activeProbability"] == 0.91
    assert result["processing"] == {"device": "mps", "durationMs": 123}


def test_normalizes_global_visual_identities_and_references():
    result = normalize_active_speaker_result(
        {
            "contractVersion": "lr-asd-evidence-v1",
            "status": "completed",
            "faceTracks": [
                {
                    "faceTrackId": "FACE_1",
                    "startMs": 0,
                    "endMs": 1000,
                    "visibleProbability": 0.9,
                    "visualIdentityId": "VISUAL_1",
                    "registrationState": "STABLE",
                }
            ],
            "activeIntervals": [
                {
                    "faceTrackId": "FACE_1",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.9,
                    "visibleProbability": 0.9,
                    "visualIdentityId": "VISUAL_1",
                }
            ],
            "visualIdentities": [
                {
                    "visualIdentityId": "VISUAL_1",
                    "faceTrackIds": ["FACE_1"],
                    "firstSeenMs": 0,
                    "lastSeenMs": 1000,
                    "registrationState": "CANDIDATE",
                    "confidence": 0.0,
                }
            ],
            "registrationDiagnostics": {"sourceTrackCount": 1},
        }
    )

    assert result["visualIdentities"][0]["visualIdentityId"] == "VISUAL_1"
    assert result["faceTracks"][0]["visualIdentityId"] == "VISUAL_1"
    assert result["activeIntervals"][0]["visualIdentityId"] == "VISUAL_1"


def test_rejects_unknown_global_visual_identity_reference():
    with pytest.raises(ActiveSpeakerContractError, match="unknown_visual_identity"):
        normalize_active_speaker_result(
            {
                "contractVersion": "lr-asd-evidence-v1",
                "status": "completed",
                "faceTracks": [
                    {
                        "faceTrackId": "FACE_1",
                        "startMs": 0,
                        "endMs": 1000,
                        "visualIdentityId": "VISUAL_MISSING",
                    }
                ],
                "activeIntervals": [],
                "visualIdentities": [],
            }
        )


@pytest.mark.parametrize("forbidden_key", ["overall_score", "score", "scoreAuthority"])
def test_rejects_score_fields_at_any_depth(forbidden_key):
    with pytest.raises(ActiveSpeakerContractError, match="score_field_forbidden"):
        normalize_active_speaker_result(
            {
                "contractVersion": "lr-asd-evidence-v1",
                "status": "completed",
                "processing": {forbidden_key: 99},
            }
        )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "0.9"])
def test_rejects_non_finite_or_non_numeric_probabilities(value):
    with pytest.raises(ActiveSpeakerContractError, match="invalid_probability"):
        normalize_active_speaker_result(
            {
                "contractVersion": "lr-asd-evidence-v1",
                "status": "completed",
                "activeIntervals": [
                    {
                        "faceTrackId": "FACE_0",
                        "startMs": 0,
                        "endMs": 1000,
                        "activeProbability": value,
                        "visibleProbability": 0.9,
                    }
                ],
            }
        )


def test_rejects_unknown_contract_version_and_reversed_timestamps():
    with pytest.raises(ActiveSpeakerContractError, match="unsupported_contract_version"):
        normalize_active_speaker_result(
            {"contractVersion": "lr-asd-evidence-v0", "status": "completed"}
        )

    with pytest.raises(ActiveSpeakerContractError, match="invalid_timestamp_range"):
        normalize_active_speaker_result(
            {
                "contractVersion": "lr-asd-evidence-v1",
                "status": "partial",
                "faceTracks": [
                    {"faceTrackId": "FACE_0", "startMs": 1000, "endMs": 100}
                ],
            }
        )


def test_unavailable_result_may_omit_tracks_but_keeps_explicit_reason():
    result = normalize_active_speaker_result(
        {
            "contractVersion": "lr-asd-evidence-v1",
            "status": "unavailable",
            "reason": "no_visible_face",
        }
    )

    assert result["faceTracks"] == []
    assert result["activeIntervals"] == []
    assert result["reason"] == "no_visible_face"
