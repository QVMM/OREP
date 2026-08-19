import pytest

from app.services.media_evidence.speaker_attribution_contract import (
    SpeakerAttributionContractError,
    normalize_speaker_attribution,
)


def _snapshot():
    return {
        "contractVersion": "speaker-attribution-v1",
        "revision": 2,
        "status": "FINAL",
        "clock": {
            "clockId": "session-26-camera-main",
            "timebase": "MILLISECONDS",
            "masterSource": "MEDIA_PTS",
            "durationMs": 3000,
            "syncStatus": "SYNCED",
            "maxObservedDriftMs": 25,
        },
        "people": [
            {
                "personId": "PERSON_1",
                "personType": "CONTESTANT",
                "contestantSlot": 1,
                "displayName": "1号选手",
                "state": "STABLE",
                "confidence": 0.9,
                "firstSeenMs": 0,
                "lastSeenMs": 3000,
                "faceTrackIds": ["FACE_2", "FACE_1"],
                "bodyTrackIds": [],
                "voiceClusterIds": ["VOICE_1"],
                "modelRevision": 2,
            }
        ],
        "turns": [
            {
                "turnId": "TURN_1",
                "startMs": 0,
                "endMs": 3000,
                "personId": "PERSON_1",
                "speakerState": "CONFIRMED",
                "confidence": 0.9,
                "candidatePersonIds": ["PERSON_1"],
                "evidence": {"activeSpeaker": 0.92, "voiceMatch": 0.88},
            }
        ],
        "segments": [
            {
                "segmentId": "SEG_1",
                "revision": 2,
                "startMs": 0,
                "endMs": 3000,
                "text": "测试",
                "personId": "PERSON_1",
                "speakerState": "CONFIRMED",
                "speakerConfidence": 0.9,
                "isFinal": True,
                "source": "fun_asr",
            }
        ],
    }


def test_normalizes_stable_people_turns_and_segments_deterministically():
    result = normalize_speaker_attribution(_snapshot())

    assert result["people"][0]["personId"] == "PERSON_1"
    assert result["people"][0]["faceTrackIds"] == ["FACE_1", "FACE_2"]
    assert result["turns"][0]["personId"] == "PERSON_1"
    assert result["segments"][0]["personId"] == "PERSON_1"


def test_allows_unknown_and_overlap_without_inventing_a_person():
    value = _snapshot()
    value["turns"] = [
        {
            "turnId": "TURN_2",
            "startMs": 100,
            "endMs": 200,
            "personId": None,
            "speakerState": "UNKNOWN",
            "confidence": 0.2,
            "candidatePersonIds": [],
        },
        {
            "turnId": "TURN_3",
            "startMs": 200,
            "endMs": 400,
            "personId": None,
            "speakerState": "OVERLAP",
            "confidence": 0.7,
            "candidatePersonIds": ["PERSON_1"],
        },
    ]
    value["segments"] = []

    result = normalize_speaker_attribution(value)

    assert [item["speakerState"] for item in result["turns"]] == [
        "UNKNOWN",
        "OVERLAP",
    ]
    assert all(item["personId"] is None for item in result["turns"])


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update({"overallScore": 99}), "forbidden_score_field"),
        (
            lambda value: value["people"][0].update({"contestantSlot": 5}),
            "invalid_contestant_slot",
        ),
        (
            lambda value: value["turns"][0].update({"personId": "PERSON_404"}),
            "unknown_person_reference",
        ),
        (
            lambda value: value["segments"][0].update({"isFinal": False}),
            "final_snapshot_contains_provisional_segment",
        ),
    ],
)
def test_rejects_unsafe_or_inconsistent_snapshots(mutate, message):
    value = _snapshot()
    mutate(value)

    with pytest.raises(SpeakerAttributionContractError, match=message):
        normalize_speaker_attribution(value)


def test_media_evidence_package_accepts_optional_attribution_snapshot():
    from app.services.media_evidence.contracts import finalize_evidence_package

    package = finalize_evidence_package(
        {
            "sessionId": "26",
            "sourceType": "UPLOADED_VIDEO",
            "speakerAttribution": _snapshot(),
        }
    )

    assert package["speakerAttribution"]["contractVersion"] == "speaker-attribution-v1"
    assert package["snapshotHash"].startswith("sha256:")
