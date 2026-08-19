import json
import subprocess
from types import SimpleNamespace

import pytest

from app.services.media_evidence.three_d_speaker_client import (
    LocalThreeDSpeakerClient,
    LocalThreeDSpeakerError,
)


def _files(tmp_path):
    python = tmp_path / "python"
    worker = tmp_path / "worker.py"
    runtime = tmp_path / "runtime"
    video = tmp_path / "video;touch PWNED.mp4"
    wav = tmp_path / "audio.wav"
    python.write_bytes(b"python")
    worker.write_text("# worker", encoding="utf-8")
    runtime.mkdir()
    video.write_bytes(b"video")
    wav.write_bytes(b"wav")
    return python, worker, runtime, video, wav


def _result():
    return {
        "contractVersion": "3d-speaker-local-v1",
        "status": "completed",
        "provider": "local_3d_speaker",
        "turns": [
            {
                "startMs": 0,
                "endMs": 1000,
                "rawSpeakerId": "3DSPK_1",
                "sourceClusterId": "3DSPK_1",
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        ],
        "diagnostics": {"processingDurationMs": 10, "peakRssBytes": 100},
    }


def test_invokes_worker_with_argument_array_and_never_uses_a_shell(tmp_path):
    python, worker, runtime, video, wav = _files(tmp_path)
    captured = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout=json.dumps(_result()), stderr="")

    client = LocalThreeDSpeakerClient(
        python_executable=python,
        worker_script=worker,
        runtime_dir=runtime,
        timeout_seconds=30,
        runner=runner,
    )

    result = client.analyze(video, wav, duration_ms=2000)

    assert isinstance(captured["command"], list)
    assert str(video) in captured["command"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 30
    assert result["diagnostics"]["speakerClusterCount"] == 1


def test_preserves_virtualenv_python_symlink_instead_of_resolving_to_base_interpreter(tmp_path):
    python, worker, runtime, video, wav = _files(tmp_path)
    target = tmp_path / "base-python"
    target.write_bytes(b"base")
    python.unlink()
    python.symlink_to(target)
    captured = {}

    def runner(command, **kwargs):
        captured["command"] = command
        return SimpleNamespace(returncode=0, stdout=json.dumps(_result()), stderr="")

    LocalThreeDSpeakerClient(
        python_executable=python,
        worker_script=worker,
        runtime_dir=runtime,
        runner=runner,
    ).analyze(video, wav, duration_ms=2000)

    assert captured["command"][0] == str(python.absolute())


@pytest.mark.parametrize(
    "missing,code",
    [
        ("python", "3d_speaker_runtime_missing"),
        ("worker", "3d_speaker_runtime_missing"),
        ("runtime", "3d_speaker_runtime_missing"),
        ("video", "3d_speaker_media_missing"),
        ("wav", "3d_speaker_media_missing"),
    ],
)
def test_rejects_missing_runtime_or_media_before_launch(tmp_path, missing, code):
    python, worker, runtime, video, wav = _files(tmp_path)
    target = {"python": python, "worker": worker, "runtime": runtime,
              "video": video, "wav": wav}[missing]
    if target.is_dir():
        target.rmdir()
    else:
        target.unlink()
    client = LocalThreeDSpeakerClient(
        python_executable=python,
        worker_script=worker,
        runtime_dir=runtime,
        runner=lambda *args, **kwargs: pytest.fail("must not launch"),
    )

    with pytest.raises(LocalThreeDSpeakerError, match=code):
        client.analyze(video, wav, duration_ms=2000)


def test_maps_timeout_nonzero_exit_and_invalid_json_to_named_failures(tmp_path):
    python, worker, runtime, video, wav = _files(tmp_path)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    client = LocalThreeDSpeakerClient(
        python_executable=python, worker_script=worker, runtime_dir=runtime,
        timeout_seconds=1, runner=timeout,
    )
    with pytest.raises(LocalThreeDSpeakerError, match="3d_speaker_timeout"):
        client.analyze(video, wav, duration_ms=2000)

    client = LocalThreeDSpeakerClient(
        python_executable=python, worker_script=worker, runtime_dir=runtime,
        runner=lambda *a, **k: SimpleNamespace(returncode=7, stdout="", stderr="private/path"),
    )
    with pytest.raises(LocalThreeDSpeakerError, match="3d_speaker_process_failed:7"):
        client.analyze(video, wav, duration_ms=2000)

    client = LocalThreeDSpeakerClient(
        python_executable=python, worker_script=worker, runtime_dir=runtime,
        runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
    )
    with pytest.raises(LocalThreeDSpeakerError, match="3d_speaker_invalid_result"):
        client.analyze(video, wav, duration_ms=2000)
