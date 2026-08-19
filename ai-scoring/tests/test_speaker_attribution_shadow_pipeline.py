import json
from pathlib import Path

from app.services import pipeline_service
from app.services.media_evidence.speaker_attribution_shadow import (
    build_shadow_attribution,
    save_shadow_attribution,
)


def _asr():
    return {
        "source": "fun_asr",
        "segments": [{"startMs": 0, "endMs": 1000, "text": "真实转写"}],
    }


def _diarization():
    return {
        "source": "local_sherpa_onnx",
        "turns": [
            {"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_7"}
        ],
    }


def test_shadow_does_not_turn_acoustic_clusters_or_unstable_face_tracks_into_people():
    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=1000,
        contestant_slots=4,
        asr_result=_asr(),
        diarization_result=_diarization(),
        active_speaker_result={
            "status": "completed",
            "faceTracks": [
                {"faceTrackId": "FACE_1", "startMs": 0, "endMs": 1000}
            ],
            "activeIntervals": [
                {"faceTrackId": "FACE_1", "startMs": 0, "endMs": 1000,
                 "activeProbability": 0.95, "visibleProbability": 0.95}
            ],
        },
    )

    assert snapshot["people"] == []
    assert snapshot["turns"][0]["personId"] is None
    assert snapshot["segments"][0]["speakerState"] == "UNKNOWN"
    assert snapshot["diagnostics"]["acousticClusterCount"] == 1
    assert snapshot["diagnostics"]["faceTrackCount"] == 1


def test_shadow_maps_multiple_acoustic_clusters_to_four_stable_people_by_visual_evidence():
    active = {
        "status": "completed",
        "faceTracks": [
            {
                "faceTrackId": f"FACE_{index}",
                "visualIdentityId": f"VISUAL_{index}",
                "startMs": 0,
                "endMs": 4000,
                "meanCenterX": center,
                "detectionCount": 100,
            }
            for index, center in enumerate((0.15, 0.38, 0.62, 0.85), start=1)
        ],
        "visualIdentities": [
            {
                "visualIdentityId": f"VISUAL_{index}",
                "faceTrackIds": [f"FACE_{index}"],
                "firstSeenMs": 0,
                "lastSeenMs": 4000,
                "registrationState": "STABLE",
                "confidence": 0.9,
            }
            for index in range(1, 5)
        ],
        "activeIntervals": [],
    }
    diarization = {
        "turns": [
            {
                "startMs": 0,
                "endMs": 1000,
                "rawSpeakerId": "SPEAKER_0",
                "sourceClusterId": "RAW_0",
                "visualIdentityId": "VISUAL_1",
                "speakerVerification": "AUDIO_VISUAL",
                "identityConfidence": 0.93,
            },
            {
                "startMs": 1000,
                "endMs": 2000,
                "rawSpeakerId": "SPEAKER_4",
                "sourceClusterId": "RAW_4",
                "visualIdentityId": "VISUAL_1",
                "speakerVerification": "AUDIO_INHERITED",
                "identityConfidence": 0.88,
            },
            *[
                {
                    "startMs": index * 1000,
                    "endMs": (index + 1) * 1000,
                    "rawSpeakerId": f"SPEAKER_{index}",
                    "sourceClusterId": f"RAW_{index}",
                    "visualIdentityId": f"VISUAL_{index}",
                    "speakerVerification": "AUDIO_VISUAL",
                    "identityConfidence": 0.9,
                }
                for index in range(2, 5)
            ],
        ]
    }
    asr = {
        "source": "fun_asr",
        "segments": [
            {"startMs": item["startMs"], "endMs": item["endMs"], "text": f"转写{index}"}
            for index, item in enumerate(diarization["turns"], start=1)
        ],
    }

    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=5000,
        contestant_slots=4,
        asr_result=asr,
        diarization_result=diarization,
        active_speaker_result=active,
    )

    assert [item["displayName"] for item in snapshot["people"]] == [
        "1号选手", "2号选手", "3号选手", "4号选手"
    ]
    assert snapshot["people"][0]["voiceClusterIds"] == ["RAW_0", "RAW_4"]
    assert snapshot["turns"][0]["personId"] == snapshot["turns"][1]["personId"]
    assert all(item["speakerState"] in {"CONFIRMED", "PROVISIONAL"} for item in snapshot["turns"])


def test_shadow_keeps_audio_only_cluster_unknown_instead_of_publishing_a_fifth_person():
    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=1000,
        contestant_slots=4,
        asr_result=_asr(),
        diarization_result=_diarization(),
        active_speaker_result={
            "status": "completed",
            "faceTracks": [],
            "visualIdentities": [],
            "activeIntervals": [],
        },
    )

    assert snapshot["people"] == []
    assert snapshot["turns"][0]["speakerState"] == "UNKNOWN"
    assert snapshot["segments"][0]["speakerState"] == "UNKNOWN"


def test_shadow_never_turns_four_positions_into_people_when_eight_face_identities_remain():
    centers = (0.50, 0.69, 0.72, 0.83, 0.85, 0.90, 0.92, 0.84)
    active = {
        "status": "completed",
        "faceTracks": [
            {
                "faceTrackId": f"FACE_{index}",
                "visualIdentityId": f"VISUAL_{index}",
                "startMs": 0,
                "endMs": 4000,
                "meanCenterX": center,
                "detectionCount": 10 if index == 8 else 1000,
                "visibleProbability": 0.9,
            }
            for index, center in enumerate(centers, start=1)
        ],
        "visualIdentities": [
            {
                "visualIdentityId": f"VISUAL_{index}",
                "faceTrackIds": [f"FACE_{index}"],
                "firstSeenMs": 0,
                "lastSeenMs": 4000,
                "registrationState": "STABLE",
                "confidence": 0.8,
            }
            for index in range(1, 9)
        ],
        "activeIntervals": [],
    }
    diarization = {
        "turns": [
            {
                "startMs": index * 1000,
                "endMs": (index + 1) * 1000,
                "rawSpeakerId": f"SPEAKER_{index}",
                "sourceClusterId": f"RAW_{index}",
                "visualIdentityId": f"VISUAL_{index}",
                "speakerVerification": "AUDIO_VISUAL",
                "identityConfidence": 0.9,
            }
            for index in range(1, 8)
        ]
    }
    asr = {
        "source": "fun_asr",
        "segments": [
            {"startMs": turn["startMs"], "endMs": turn["endMs"], "text": f"转写{index}"}
            for index, turn in enumerate(diarization["turns"], start=1)
        ],
    }

    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=9000,
        contestant_slots=4,
        asr_result=asr,
        diarization_result=diarization,
        active_speaker_result=active,
    )

    assert snapshot["people"] == []
    assert snapshot["diagnostics"]["stableVisualIdentityCount"] == 8
    assert snapshot["diagnostics"]["publishedPersonCount"] == 0
    assert all(turn["personId"] is None for turn in snapshot["turns"])
    assert all(turn["speakerState"] == "UNKNOWN" for turn in snapshot["turns"])


def test_shadow_snapshot_is_saved_atomically_below_a_session_directory(tmp_path):
    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=1000,
        contestant_slots=4,
        asr_result=_asr(),
        diarization_result=_diarization(),
        active_speaker_result=None,
    )

    receipt = save_shadow_attribution(str(tmp_path), "session/26", snapshot)

    saved = Path(receipt["path"])
    assert saved.name == "revision-1.json"
    assert saved.parent.name == "session_26"
    assert json.loads(saved.read_text(encoding="utf-8"))["status"] == "FINAL"
    assert receipt["snapshotHash"].startswith("sha256:")
    assert list(tmp_path.rglob("*.tmp")) == []


def test_shadow_uses_requested_revision_for_snapshot_and_transcript_segments():
    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=1000,
        contestant_slots=4,
        asr_result=_asr(),
        diarization_result=_diarization(),
        active_speaker_result=None,
        revision=2,
    )

    assert snapshot["revision"] == 2
    assert snapshot["segments"][0]["revision"] == 2


def test_upload_shadow_reuses_the_recording_media_clock_contract():
    snapshot = build_shadow_attribution(
        session_id="26",
        duration_ms=1000,
        contestant_slots=4,
        asr_result=_asr(),
        diarization_result=_diarization(),
        active_speaker_result=None,
        media_clock={
            "clockId": "upload-clock-26",
            "masterSource": "MEDIA_PTS",
            "syncStatus": "SYNCED",
            "maxObservedDriftMs": 0,
        },
    )

    assert snapshot["clock"] == {
        "clockId": "upload-clock-26",
        "timebase": "MILLISECONDS",
        "masterSource": "MEDIA_PTS",
        "durationMs": 1000,
        "syncStatus": "SYNCED",
        "maxObservedDriftMs": 0,
    }


def test_pipeline_shadow_failure_is_named_and_does_not_change_public_segments(monkeypatch):
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", False)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_SHADOW_MODE", True)
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr())
    monkeypatch.setattr(pipeline_service, "_run_local_speaker_diarization", lambda *args, **kwargs: _diarization())
    monkeypatch.setattr(
        pipeline_service,
        "_build_and_save_speaker_attribution_shadow",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("disk_full")),
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/audio.wav", 1.0, {"team_size": 4}, "26"
    )

    assert result["segments"][0]["text"] == "真实转写"
    assert result["speakerAttributionShadowStatus"] == "failed"
    assert result["speakerAttributionShadowFailureCode"] == "RuntimeError"


def test_pipeline_sends_global_visual_fusion_to_shadow_snapshot(monkeypatch):
    captured = {}
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_SHADOW_MODE", True)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS", 1)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS", 0)
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr())
    monkeypatch.setattr(pipeline_service, "_run_local_speaker_diarization", lambda *args, **kwargs: _diarization())
    monkeypatch.setattr(
        pipeline_service,
        "_run_optional_local_active_speaker",
        lambda *args: {
            "contractVersion": "lr-asd-evidence-v1",
            "status": "completed",
            "source": "local_lr_asd",
            "faceTracks": [],
            "visualIdentities": [],
            "activeIntervals": [
                {
                    "faceTrackId": "FACE_9",
                    "visualIdentityId": "VISUAL_3",
                    "startMs": 0,
                    "endMs": 1000,
                    "activeProbability": 0.95,
                    "visibleProbability": 0.95,
                }
            ],
        },
    )

    def save_shadow(**kwargs):
        captured.update(kwargs)
        return {"revision": 1, "snapshotHash": "sha256:test"}

    monkeypatch.setattr(
        pipeline_service, "_build_and_save_speaker_attribution_shadow", save_shadow
    )

    pipeline_service._run_authoritative_asr(
        "/tmp/audio.wav",
        1.0,
        {"team_size": 4},
        "26",
        video_path="/tmp/video.mp4",
    )

    turn = captured["diarization_result"]["turns"][0]
    assert turn["visualIdentityId"] == "VISUAL_3"
    assert turn["speakerVerification"] == "AUDIO_VISUAL"
