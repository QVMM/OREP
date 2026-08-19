import threading
import time
import inspect
import json
from pathlib import Path

import pytest

from app.services import pipeline_service
from app.services.pipeline_payloads import build_backend_callback_payload
from app.services.media_evidence.local_diarization import LocalDiarizationError
from app.services.media_evidence.lr_asd_client import LocalLrAsdError


class FakeDiarizer:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def diarize(self, wav_path, speaker_count_hint=None):
        self.calls.append((wav_path, speaker_count_hint))
        if self.error:
            raise self.error
        return self.result


class FakeActiveSpeakerClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def analyze(self, video_path, wav_path):
        self.calls.append((video_path, wav_path))
        if self.error:
            raise self.error
        return self.result


def _asr_result(source="cloud_streaming_complete_recording"):
    return {
        "transcript": "终版转写",
        "segments": [{
            "start": 0.0,
            "end": 1.0,
            "startMs": 0,
            "endMs": 1000,
            "text": "终版转写",
        }],
        "speakers": [],
        "duration": 1.0,
        "source": source,
    }


def _diarization_result():
    return {
        "turns": [{
            "startMs": 0,
            "endMs": 1000,
            "rawSpeakerId": "SPEAKER_0",
        }],
        "speakers": ["SPEAKER_0"],
        "source": "local_sherpa_onnx",
    }


def _active_speaker_result():
    return {
        "contractVersion": "lr-asd-evidence-v1",
        "status": "completed",
        "source": "local_lr_asd",
        "faceTracks": [{"faceTrackId": "FACE_0", "startMs": 0, "endMs": 1000}],
        "activeIntervals": [{
            "faceTrackId": "FACE_0",
            "startMs": 0,
            "endMs": 1000,
            "activeProbability": 0.95,
            "visibleProbability": 0.95,
        }],
    }


def test_disabled_local_diarization_still_uses_complete_recording_cloud_asr(monkeypatch):
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service,
        "_run_cloud_complete_recording_asr",
        lambda *args, **kwargs: _asr_result(),
    )
    monkeypatch.setattr(
        pipeline_service,
        "_build_local_speaker_diarizer",
        lambda: pytest.fail("local diarizer must not be built while disabled"),
        raising=False,
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav", 60, {"team_size": 4}, "26"
    )

    assert result["source"] == "cloud_streaming_complete_recording"


@pytest.mark.parametrize("source_type", ["uploaded_video", "meeting_recording"])
def test_enabled_local_diarization_uses_same_complete_recording_flow_for_both_sources(
    monkeypatch, source_type
):
    diarizer = FakeDiarizer(_diarization_result())
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(
        pipeline_service,
        "_build_local_speaker_diarizer",
        lambda: diarizer,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service,
        "_run_cloud_complete_recording_asr",
        lambda *args, **kwargs: _asr_result(),
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav",
        3600,
        {"team_size": 5, "source_type": source_type},
        "26",
    )

    assert result["source"] == "cloud_streaming_complete_recording"
    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"
    assert result["diarizationSource"] == "local_sherpa_onnx"
    assert diarizer.calls == [("/tmp/derived.wav", None)]


def test_team_roster_size_does_not_force_diarization_speaker_count(monkeypatch):
    diarizer = FakeDiarizer(_diarization_result())
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service, "_build_local_speaker_diarizer", lambda: diarizer)
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr_result())

    pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav",
        3600,
        {"team_size": 8, "speaker_count_hint": 3},
        "26",
    )

    assert diarizer.calls == [("/tmp/derived.wav", 3)]


def test_enabled_local_diarization_propagates_failure_without_fake_speaker(monkeypatch):
    diarizer = FakeDiarizer(error=LocalDiarizationError("local_diarization_model_missing"))
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service, "_build_local_speaker_diarizer", lambda: diarizer, raising=False)
    monkeypatch.setattr(
        pipeline_service,
        "_run_cloud_complete_recording_asr",
        lambda *args: _asr_result(),
    )

    with pytest.raises(LocalDiarizationError, match="local_diarization_model_missing"):
        pipeline_service._run_authoritative_asr(
            "/tmp/derived.wav", 3600, {"team_size": 4}, "26"
        )


def test_complete_recording_runs_cloud_asr_then_required_local_diarization(monkeypatch):
    """Audio evidence is sequential: ASR text first, then required diarization.

    Parallel ASR+diarization was abandoned after sherpa native crashes killed the
    shared process mid-pipeline. Quality is preserved by failing hard on diarization
    errors, not by soft-empty speaker labels.
    """
    order = []

    def asr(*args):
        order.append("asr")
        return _asr_result()

    diarizer = FakeDiarizer()
    diarizer.diarize = lambda wav_path, speaker_count_hint=None: (
        order.append("diarization") or _diarization_result()
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_TIMEOUT_SECONDS", 2, raising=False)
    monkeypatch.setattr(pipeline_service, "_build_local_speaker_diarizer", lambda: diarizer)
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", asr)

    result = pipeline_service._run_authoritative_asr("/tmp/derived.wav", 3600, {}, "26")

    assert order == ["asr", "diarization"]
    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"


def test_video_terminal_flow_fuses_local_lr_asd_and_preserves_verification_metadata(
    monkeypatch,
):
    diarizer = FakeDiarizer(_diarization_result())
    active_client = FakeActiveSpeakerClient(_active_speaker_result())
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_ENABLED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS",
        1,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS",
        0,
        raising=False,
    )
    monkeypatch.setattr(pipeline_service, "_build_local_speaker_diarizer", lambda: diarizer)
    monkeypatch.setattr(
        pipeline_service, "_build_local_active_speaker_client", lambda: active_client
    )
    monkeypatch.setattr(
        pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr_result()
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav",
        3600,
        {},
        "26",
        video_path="/tmp/camera.mp4",
    )

    assert active_client.calls == [("/tmp/camera.mp4", "/tmp/derived.wav")]
    assert result["segments"][0]["faceTrackId"] == "FACE_0"
    assert result["segments"][0]["speakerVerification"] == "AUDIO_VISUAL"
    assert result["segments"][0]["identityConfidence"] > 0.8
    assert result["audioVisualStatus"] == "completed"


def test_pipeline_passes_conservative_cluster_inheritance_thresholds(monkeypatch):
    captured = {}
    real_fusion = pipeline_service.fuse_active_speaker_evidence

    def capture_fusion(*args, **kwargs):
        captured.update(kwargs)
        return real_fusion(*args, **kwargs)

    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_ENABLED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS",
        2,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS",
        3000,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service.settings,
        "LOCAL_ACTIVE_SPEAKER_MIN_IDENTITY_CONFIDENCE",
        0.4,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service, "_build_local_speaker_diarizer", lambda: FakeDiarizer(_diarization_result())
    )
    monkeypatch.setattr(
        pipeline_service,
        "_build_local_active_speaker_client",
        lambda: FakeActiveSpeakerClient(_active_speaker_result()),
    )
    monkeypatch.setattr(
        pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr_result()
    )
    monkeypatch.setattr(pipeline_service, "fuse_active_speaker_evidence", capture_fusion)

    pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav", 3600, {}, "26", video_path="/tmp/camera.mp4"
    )

    assert captured["minimum_cluster_supporting_turns"] == 2
    assert captured["minimum_cluster_support_ms"] == 3000
    assert captured["minimum_identity_confidence"] == 0.4


def test_lr_asd_failure_explicitly_degrades_to_audio_only_without_failing_scoring(
    monkeypatch,
):
    active_client = FakeActiveSpeakerClient(error=LocalLrAsdError("lr_asd_timeout"))
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_ENABLED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_REQUIRED", False, raising=False
    )
    monkeypatch.setattr(
        pipeline_service, "_build_local_speaker_diarizer", lambda: FakeDiarizer(_diarization_result())
    )
    monkeypatch.setattr(
        pipeline_service, "_build_local_active_speaker_client", lambda: active_client
    )
    monkeypatch.setattr(
        pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr_result()
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav", 3600, {}, "26", video_path="/tmp/camera.mp4"
    )

    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"
    assert result["audioVisualStatus"] == "failed"
    assert result["activeSpeakerFailureCode"] == "lr_asd_timeout"


def test_audio_only_terminal_flow_never_launches_lr_asd(monkeypatch):
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        pipeline_service, "_build_local_speaker_diarizer", lambda: FakeDiarizer(_diarization_result())
    )
    monkeypatch.setattr(
        pipeline_service,
        "_build_local_active_speaker_client",
        lambda: pytest.fail("audio-only flow must not build LR-ASD"),
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_service, "_run_cloud_complete_recording_asr", lambda *args: _asr_result()
    )

    result = pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav", 3600, {}, "26", video_path=None
    )

    assert result["segments"][0]["rawSpeakerId"] == "SPEAKER_0"


def test_cloud_asr_local_diarization_and_lr_asd_run_in_required_order(monkeypatch):
    order = []

    def asr(*args):
        order.append("asr")
        return _asr_result()

    diarizer = FakeDiarizer()
    diarizer.diarize = lambda *args, **kwargs: (
        order.append("diarization") or _diarization_result()
    )
    active_client = FakeActiveSpeakerClient()
    active_client.analyze = lambda *args, **kwargs: (
        order.append("active_speaker") or _active_speaker_result()
    )
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_SPEAKER_DIARIZATION_ENABLED", True, raising=False
    )
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_DIARIZATION_ISOLATED_PROCESS", False, raising=False)
    monkeypatch.setattr(pipeline_service.settings, "LOCAL_3D_SPEAKER_ENABLED", False, raising=False)
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_ENABLED", True, raising=False
    )
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_DIARIZATION_TIMEOUT_SECONDS", 2, raising=False
    )
    monkeypatch.setattr(
        pipeline_service.settings, "LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS", 2, raising=False
    )
    monkeypatch.setattr(pipeline_service, "_build_local_speaker_diarizer", lambda: diarizer)
    monkeypatch.setattr(
        pipeline_service, "_build_local_active_speaker_client", lambda: active_client
    )
    monkeypatch.setattr(pipeline_service, "_run_cloud_complete_recording_asr", asr)

    pipeline_service._run_authoritative_asr(
        "/tmp/derived.wav", 3600, {}, "26", video_path="/tmp/camera.mp4"
    )

    assert order == ["asr", "diarization", "active_speaker"]


def test_complete_recording_cloud_asr_never_reuses_partial_realtime_transcript(monkeypatch):
    monkeypatch.setattr(
        pipeline_service,
        "_load_realtime_transcript",
        lambda *args: pytest.fail("terminal review must transcribe the complete recording"),
    )
    monkeypatch.setattr(
        pipeline_service.asr_service,
        "transcribe_long_audio",
        lambda wav: _asr_result("provider"),
    )

    result = pipeline_service._run_cloud_complete_recording_asr("/tmp/derived.wav", 3600)

    assert result["source"] == "cloud_streaming_complete_recording"


def test_primary_audio_and_video_evidence_branches_really_overlap():
    barrier = threading.Barrier(2)
    spans = {}

    def operation(name):
        spans[name] = [time.monotonic(), None]
        barrier.wait(timeout=1)
        time.sleep(0.04)
        spans[name][1] = time.monotonic()
        return {"name": name}

    result = pipeline_service._run_primary_evidence_branches(
        audio_operation=lambda: operation("audio"),
        video_operation=lambda: operation("video"),
        timeout_seconds=2,
    )

    assert result["audio"] == {"name": "audio"}
    assert result["video"] == {"name": "video"}
    assert spans["audio"][0] < spans["video"][1]
    assert spans["video"][0] < spans["audio"][1]


def test_dual_terminal_media_branches_run_audio_camera_and_screen_concurrently():
    barrier = threading.Barrier(3)
    spans = {}

    def operation(name):
        spans[name] = [time.monotonic(), None]
        barrier.wait(timeout=1)
        time.sleep(0.04)
        spans[name][1] = time.monotonic()
        return {"name": name}

    outputs = pipeline_service._run_terminal_media_branches(
        {
            "audio": lambda: operation("audio"),
            "camera": lambda: operation("camera"),
            "screen": lambda: operation("screen"),
        },
        max_workers=3,
        timeout_seconds=2,
    )

    assert list(outputs) == ["audio", "camera", "screen"]
    assert all(spans[name][0] < spans[other][1] for name in spans for other in spans)


def test_terminal_media_branch_timeout_is_bounded_and_names_the_stage():
    with pytest.raises(RuntimeError, match="branch_timeout:audio"):
        pipeline_service._run_terminal_media_branches(
            {"audio": lambda: time.sleep(0.2) or {}},
            max_workers=1,
            timeout_seconds=0.01,
        )


def test_parallel_branch_progress_writes_are_atomic(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline_service.settings, "UPLOAD_DIR", str(tmp_path))
    decode_errors = []
    finished = threading.Event()
    progress_path = tmp_path / "results" / "progress_26.json"

    def writer(stage):
        for index in range(80):
            pipeline_service._save_progress(
                "26", stage, f"{stage}-{index}", index, 80, progress_percent=index
            )

    def reader():
        while not finished.is_set():
            if progress_path.exists():
                try:
                    json.loads(progress_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    decode_errors.append(exc)

    reader_thread = threading.Thread(target=reader)
    workers = [threading.Thread(target=writer, args=(name,)) for name in ("audio", "video")]
    reader_thread.start()
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    finished.set()
    reader_thread.join()

    assert decode_errors == []
    assert json.loads(progress_path.read_text(encoding="utf-8"))["step"] in {"audio", "video"}
    assert list((tmp_path / "results").glob("*.tmp-*")) == []


def test_single_and_dual_terminal_pipelines_call_authoritative_asr_selector():
    single_source = inspect.getsource(pipeline_service.run_scoring_pipeline)
    dual_source = inspect.getsource(pipeline_service.run_dual_video_scoring_pipeline)

    assert "_run_authoritative_asr(" in single_source
    assert "_run_asr_with_realtime_preference(" not in single_source
    assert "_run_authoritative_asr(" in dual_source
    assert "_run_asr_with_realtime_preference(" not in dual_source
    # Dual still fans out camera/screen via terminal media branches; single runs
    # audio then video sequentially to avoid native-worker crashes under load.
    assert "_run_terminal_media_branches(" in dual_source
    assert "video_path=audio_file_path" in single_source
    assert "video_path=camera_video_path" in dual_source
    assert "video_path=screen_video_path" not in dual_source


def test_terminal_pipelines_publish_score_free_speaker_evidence_only():
    single_source = inspect.getsource(pipeline_service.run_scoring_pipeline)
    dual_source = inspect.getsource(pipeline_service.run_dual_video_scoring_pipeline)

    for source in (single_source, dual_source):
        assert "build_speaker_evidence(" in source
        assert "speaker_scores" not in source
        assert "_run_speaker_analysis(" not in source


def test_terminal_speaker_flow_has_no_oss_runtime_contract():
    project_root = Path(__file__).resolve().parents[1]
    production_text = "\n".join(
        [
            (project_root / "app" / "config.py").read_text(encoding="utf-8"),
            (project_root / "app" / "services" / "pipeline_service.py").read_text(
                encoding="utf-8"
            ),
            (project_root / "requirements.txt").read_text(encoding="utf-8"),
        ]
    )

    for forbidden in (
        "TEMP_AUDIO_OSS",
        "FINAL_RECORDED_DIARIZATION_ENABLED",
        "oss2",
        "recorded_asr_gateway",
    ):
        assert forbidden not in production_text


def test_legacy_callback_payload_does_not_publish_hidden_speaker_scores():
    payload = build_backend_callback_payload("26", {
        "status": "completed",
        "ai_score": {"overall_score": 49.5},
        "asr": {},
        "speaker_scores": [{"speakerId": "SPEAKER_0", "score": 60}],
        "speaker_evidence": [{"rawSpeakerId": "SPEAKER_0", "displayName": "1号发言人"}],
    })

    assert "speakers" not in payload
    assert payload["speakerEvidence"] == [
        {"rawSpeakerId": "SPEAKER_0", "displayName": "1号发言人"}
    ]
