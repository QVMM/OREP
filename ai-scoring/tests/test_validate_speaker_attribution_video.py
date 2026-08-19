import json

from scripts.validate_speaker_attribution_video import (
    atomic_write_json,
    summarize_registration,
)


def _result():
    return {
        "status": "completed",
        "faceTracks": [
            {
                "faceTrackId": "FACE_1",
                "visualIdentityId": "VISUAL_1",
                "registrationState": "STABLE",
            },
            {
                "faceTrackId": "FACE_NOISE",
                "visualIdentityId": None,
                "registrationState": "UNRESOLVED",
            },
        ],
        "activeIntervals": [{"faceTrackId": "FACE_1"}],
        "visualIdentities": [
            {"visualIdentityId": "VISUAL_1", "registrationState": "STABLE"},
            {"visualIdentityId": "VISUAL_2", "registrationState": "CANDIDATE"},
        ],
        "registrationDiagnostics": {
            "sourceTrackCount": 2,
            "eligibleTrackCount": 1,
            "acceptedLinkCount": 1,
            "rejectedCoVisibleLinkCount": 3,
            "unresolvedTrackCount": 1,
        },
        "processing": {"durationMs": 1234},
    }


def test_summary_does_not_call_tracks_or_visual_candidates_people():
    summary = summarize_registration(_result(), wall_seconds=1.5)

    assert summary == {
        "status": "completed",
        "wallSeconds": 1.5,
        "workerDurationMs": 1234,
        "rawTrackletCount": 2,
        "eligibleTrackletCount": 1,
        "stableVisualIdentityCount": 1,
        "candidateVisualIdentityCount": 1,
        "unresolvedTrackletCount": 1,
        "activeIntervalCount": 1,
        "acceptedVisualLinkCount": 1,
        "rejectedCoVisibleLinkCount": 3,
    }
    assert "personCount" not in summary


def test_atomic_result_write_leaves_no_temporary_file(tmp_path):
    destination = tmp_path / "nested" / "result.json"

    atomic_write_json(destination, _result())

    assert json.loads(destination.read_text(encoding="utf-8"))["status"] == "completed"
    assert list(tmp_path.rglob("*.tmp")) == []
