import threading
import time

from app.services import pipeline_service
from app.config import settings


def _asr(text="我是一号选手"):
    return {
        "transcript": text,
        "segments": [{"startMs": 0, "endMs": 1000, "text": text}],
        "duration": 1.0,
        "source": "cloud_streaming_complete_recording",
    }


def _diarization():
    return {
        "turns": [{"startMs": 0, "endMs": 1000, "rawSpeakerId": "SPEAKER_0"}],
        "speakers": ["SPEAKER_0"],
        "source": "local_sherpa_onnx",
    }


def _joint(status="completed", turns=None):
    return {
        "contractVersion": "3d-speaker-local-v1",
        "provider": "local_3d_speaker",
        "status": status,
        "turns": turns if turns is not None else [{
            "startMs": 0,
            "endMs": 1000,
            "rawSpeakerId": "3DSPK_A",
            "sourceClusterId": "3DSPK_A",
            "speakerVerification": "JOINT_AUDIO_VISUAL",
        }],
        "diagnostics": {},
    }


def _enable(monkeypatch):
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_ENABLED", True, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_REQUIRED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_3D_SPEAKER_PUBLICATION_ENABLED",
        True,
        raising=False,
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_TIMEOUT_SECONDS", 2, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_ENABLED", True)
    monkeypatch.setattr(pipeline_service.settings, "SPEAKER_ATTRIBUTION_SHADOW_MODE", False)
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr())
    monkeypatch.setattr(pipeline_service, "_run_local_speaker_diarization", lambda *args, **kwargs: _diarization())


def test_formal_speaker_publication_is_enabled_by_default():
    """Fresh local deployments must publish the validated joint attribution flow."""
    assert settings.SPEAKER_ATTRIBUTION_ENABLED is True
    assert settings.SPEAKER_ATTRIBUTION_SHADOW_MODE is False
    assert settings.LOCAL_3D_SPEAKER_ENABLED is True
    assert settings.LOCAL_3D_SPEAKER_PUBLICATION_ENABLED is True


def test_enabled_joint_pipeline_is_authoritative_and_never_launches_old_lr_asd(monkeypatch, tmp_path):
    _enable(monkeypatch)
    captured = {}
    monkeypatch.setattr(pipeline_service, "_run_optional_three_d_speaker", lambda *args: _joint())
    monkeypatch.setattr(
        pipeline_service,
        "_run_optional_local_active_speaker",
        lambda *args: (_ for _ in ()).throw(AssertionError("old LR-ASD must not run")),
    )

    def save_final(**kwargs):
        captured.update(kwargs)
        return {
            "revision": 2,
            "snapshotHash": "sha256:test",
            "snapshot": {"status": "FINAL", "people": [{"displayName": "1号选手"}]},
        }

    monkeypatch.setattr(pipeline_service, "_build_and_save_final_speaker_attribution", save_final)

    result = pipeline_service._run_authoritative_asr(
        str(tmp_path / "audio.wav"), 1.0, {"team_size": 4}, "26",
        video_path=str(tmp_path / "video.mp4"),
    )

    assert captured["three_d_speaker_result"]["provider"] == "local_3d_speaker"
    assert captured["asr_result"]["transcript"] == "我是一号选手"
    assert result["speakerAttribution"]["people"][0]["displayName"] == "1号选手"
    assert result["speakerAttributionStatus"] == "completed"
    assert result["speakerAttributionRevision"] == 2


def test_joint_snapshot_stays_private_without_explicit_publication_gate(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_3D_SPEAKER_PUBLICATION_ENABLED",
        False,
        raising=False,
    )
    monkeypatch.setattr(pipeline_service, "_run_optional_three_d_speaker", lambda *args: _joint())
    monkeypatch.setattr(
        pipeline_service,
        "_build_and_save_final_speaker_attribution",
        lambda **kwargs: {
            "revision": 2,
            "snapshotHash": "sha256:private",
            "snapshot": {"status": "FINAL", "people": [{"displayName": "1号选手"}]},
        },
    )

    result = pipeline_service._run_authoritative_asr(
        str(tmp_path / "audio.wav"), 1.0, {}, "26",
        video_path=str(tmp_path / "video.mp4"),
    )

    assert result["speakerAttributionStatus"] == "completed"
    assert result["speakerAttributionHash"] == "sha256:private"
    assert "speakerAttribution" not in result


def test_joint_failure_publishes_safe_unknown_revision_not_legacy_people(monkeypatch, tmp_path):
    _enable(monkeypatch)
    monkeypatch.setattr(
        pipeline_service,
        "_run_optional_three_d_speaker",
        lambda *args: _joint(status="evidence_incomplete", turns=[]),
    )
    monkeypatch.setattr(
        pipeline_service,
        "_build_and_save_final_speaker_attribution",
        lambda **kwargs: {
            "revision": 4,
            "snapshotHash": "sha256:safe",
            "snapshot": {
                "status": "FINAL",
                "people": [],
                "segments": [{"text": "我是一号选手", "speakerState": "UNKNOWN"}],
            },
        },
    )

    result = pipeline_service._run_authoritative_asr(
        str(tmp_path / "audio.wav"), 1.0, {}, "26",
        video_path=str(tmp_path / "video.mp4"),
    )

    assert result["speakerAttribution"]["people"] == []
    assert result["speakerAttribution"]["segments"][0]["speakerState"] == "UNKNOWN"
    assert result["speakerAttributionProviderStatus"] == "evidence_incomplete"


def test_cloud_asr_acoustic_diarization_and_joint_video_analysis_overlap(monkeypatch, tmp_path):
    _enable(monkeypatch)
    started = []

    def operation(name, value):
        started.append(name)
        return value

    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", lambda *args, **kwargs: operation("asr", _asr()))
    monkeypatch.setattr(pipeline_service, "_run_local_speaker_diarization", lambda *args, **kwargs: operation("diarization", _diarization()))
    monkeypatch.setattr(pipeline_service, "_run_optional_three_d_speaker", lambda *args, **kwargs: operation("joint", _joint()))
    monkeypatch.setattr(
        pipeline_service,
        "_build_and_save_final_speaker_attribution",
        lambda **kwargs: {"revision": 1, "snapshotHash": "sha256:x", "snapshot": {"status": "FINAL"}},
    )

    pipeline_service._run_authoritative_asr(
        str(tmp_path / "audio.wav"), 1.0, {}, "26",
        video_path=str(tmp_path / "video.mp4"),
    )

    assert started == ["asr", "diarization", "joint"]


def test_audio_only_flow_does_not_launch_joint_video_runtime(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(
        pipeline_service,
        "_run_optional_three_d_speaker",
        lambda *args: (_ for _ in ()).throw(AssertionError("video runtime must not run")),
        raising=False,
    )

    result = pipeline_service._run_authoritative_asr("/tmp/audio.wav", 1.0, {}, "26")

    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"
    assert "speakerAttribution" not in result
