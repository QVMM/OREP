import json
import subprocess
from pathlib import Path

import pytest

from app.services.media_evidence.lr_asd_client import LocalLrAsdClient, LocalLrAsdError


def _files(tmp_path: Path):
    paths = {
        name: tmp_path / filename
        for name, filename in {
            "python": "python3.11",
            "worker": "lr_asd_worker.py",
            "weight": "pretrain_AVA.model",
            "video": "input.mp4",
            "audio": "input.wav",
            "yunet": "face_detection_yunet.onnx",
            "sface": "face_recognition_sface.onnx",
        }.items()
    }
    for path in paths.values():
        path.write_bytes(b"x")
    paths["repo"] = tmp_path / "LR-ASD"
    paths["repo"].mkdir()
    return paths


def _payload():
    return {
        "contractVersion": "lr-asd-evidence-v1",
        "status": "completed",
        "faceTracks": [],
        "activeIntervals": [],
    }


def _client(paths, runner, timeout=9):
    return LocalLrAsdClient(
        python_executable=paths["python"],
        worker_script=paths["worker"],
        model_repository=paths["repo"],
        model_weight=paths["weight"],
        yunet_model=paths["yunet"],
        sface_model=paths["sface"],
        timeout_seconds=timeout,
        runner=runner,
    )


def test_client_sends_local_paths_and_parses_one_json_object(tmp_path):
    paths = _files(tmp_path)
    captured = {}

    def fake_runner(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, json.dumps(_payload()), "diagnostic")

    result = _client(paths, fake_runner).analyze(paths["video"], paths["audio"])

    assert result["source"] == "local_lr_asd"
    assert captured["command"][0] == str(paths["python"])
    assert captured["command"][1] == str(paths["worker"])
    assert captured["command"][captured["command"].index("--video") + 1] == str(
        paths["video"]
    )
    assert captured["command"][captured["command"].index("--audio") + 1] == str(
        paths["audio"]
    )
    assert captured["command"][captured["command"].index("--global-identity-threshold") + 1] == "0.6"
    assert captured["command"][captured["command"].index("--global-identity-stable-threshold") + 1] == "0.8"
    assert captured["command"][captured["command"].index("--global-identity-minimum-detections") + 1] == "3"
    assert captured["command"][captured["command"].index("--global-identity-minimum-visibility") + 1] == "0.6"
    assert captured["kwargs"]["timeout"] == 9
    assert captured["kwargs"]["shell"] is False


def test_timeout_is_named_failure(tmp_path):
    paths = _files(tmp_path)

    def timeout_runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    with pytest.raises(LocalLrAsdError, match="lr_asd_timeout"):
        _client(paths, timeout_runner).analyze(paths["video"], paths["audio"])


def test_non_json_output_is_named_failure(tmp_path):
    paths = _files(tmp_path)

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "not-json", "")

    with pytest.raises(LocalLrAsdError, match="lr_asd_invalid_output"):
        _client(paths, fake_runner).analyze(paths["video"], paths["audio"])


def test_nonzero_worker_exit_is_named_and_does_not_leak_full_stderr(tmp_path):
    paths = _files(tmp_path)

    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 3, "", "secret-token worker failed")

    with pytest.raises(LocalLrAsdError) as raised:
        _client(paths, fake_runner).analyze(paths["video"], paths["audio"])

    assert str(raised.value) == "lr_asd_worker_failed:3"
    assert "secret-token" not in str(raised.value)


def test_missing_runtime_asset_fails_before_launch(tmp_path):
    paths = _files(tmp_path)
    paths["weight"].unlink()

    with pytest.raises(LocalLrAsdError, match="lr_asd_model_weight_missing"):
        _client(paths, lambda *args, **kwargs: pytest.fail("must not launch")).analyze(
            paths["video"], paths["audio"]
        )


def test_prefers_persistent_transport_without_launching_subprocess(tmp_path):
    paths = _files(tmp_path)

    class Transport:
        def analyze(self, video_path, wav_path, *, timeout_seconds):
            assert video_path == paths["video"]
            assert wav_path == paths["audio"]
            assert timeout_seconds == 9
            return _payload()

    client = _client(
        paths,
        lambda *args, **kwargs: pytest.fail("subprocess fallback must not launch"),
    )
    client.set_persistent_transport(Transport())

    assert client.analyze(paths["video"], paths["audio"])["status"] == "completed"


def test_persistent_transport_crash_falls_back_to_existing_subprocess(tmp_path):
    paths = _files(tmp_path)
    launched = []

    class Transport:
        def analyze(self, video_path, wav_path, *, timeout_seconds):
            raise BrokenPipeError("worker exited")

    def runner(command, **kwargs):
        launched.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(_payload()), "")

    client = _client(paths, runner)
    client.set_persistent_transport(Transport())

    assert client.analyze(paths["video"], paths["audio"])["status"] == "completed"
    assert len(launched) == 1
