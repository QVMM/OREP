import json
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import threading
import time

import pytest

import scripts.three_d_speaker_worker as worker_module
from scripts.three_d_speaker_worker import (
    _process_tree_rss_bytes,
    build_health_report,
    run_analysis,
)


def _runtime(tmp_path):
    runtime = tmp_path / "runtime"
    recipe = runtime / "repository" / "egs" / "3dspeaker" / "speaker-diarization"
    recipe.mkdir(parents=True)
    (recipe / "run_video.sh").write_text("#!/bin/bash", encoding="utf-8")
    models = runtime / "models" / "onnx"
    models.mkdir(parents=True)
    for name in ("version-RFB-320.onnx", "asd.onnx", "fqa.onnx", "face_recog_ir101.onnx"):
        (models / name).write_bytes(name.encode())
    return runtime


def test_health_report_names_platform_provider_and_required_assets(tmp_path):
    runtime = _runtime(tmp_path)

    report = build_health_report(
        runtime,
        providers=["CPUExecutionProvider"],
        platform_name="darwin-arm64",
    )

    assert report["status"] == "ready"
    assert report["platform"] == "darwin-arm64"
    assert report["executionProviders"] == ["CPUExecutionProvider"]
    assert report["runtimeCommit"] == "065629c313eaf1a01c65c640c46d77e61e9607b4"


def test_process_tree_rss_includes_children_and_grandchildren_only():
    ps_output = """\
10 1 100
11 10 200
12 11 300
20 1 900
"""

    assert _process_tree_rss_bytes(ps_output, root_pid=10) == 600 * 1024


def test_parallel_official_processes_stop_the_sibling_on_first_failure(tmp_path):
    fail_fast = getattr(
        worker_module,
        "_run_parallel_subprocesses_fail_fast",
        None,
    )
    assert callable(fail_fast), "parallel stages need a fail-fast process supervisor"
    marker = tmp_path / "slow-stage-finished"
    started = time.monotonic()

    with pytest.raises(
        RuntimeError,
        match="official_recipe_failed:audio_embeddings:7",
    ):
        fail_fast(
            {
                "audio_embeddings": [
                    sys.executable,
                    "-c",
                    "import sys; sys.exit(7)",
                ],
                "visual_embeddings": [
                    sys.executable,
                    "-c",
                    (
                        "import pathlib,time; time.sleep(2); "
                        f"pathlib.Path({str(marker)!r}).write_text('finished')"
                    ),
                ],
            },
            cwd=tmp_path,
            env=os.environ.copy(),
            log_dir=tmp_path,
            poll_interval_seconds=0.01,
        )

    assert time.monotonic() - started < 1.0
    time.sleep(0.15)
    assert marker.exists() is False


def test_analysis_uses_isolated_job_and_returns_one_normalized_rttm(tmp_path):
    runtime = _runtime(tmp_path)
    video = tmp_path / "source.mp4"
    audio = tmp_path / "source.wav"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    observed = {"commands": []}

    def runner(command, **kwargs):
        observed["commands"].append(command)
        observed["cwd"] = kwargs["cwd"]
        observed["omp_threads"] = kwargs["env"]["THREED_SPEAKER_OMP_NUM_THREADS"]
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"normalized-video")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        exp = Path(command[command.index("--exp") + 1])
        rttm_dir = exp / "rttm"
        rttm_dir.mkdir(parents=True, exist_ok=True)
        (rttm_dir / "source.rttm").write_text(
            "SPEAKER source 0 0.000 1.000 <NA> <NA> 0 <NA> <NA>\n",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = run_analysis(
        runtime_dir=runtime,
        video_path=video,
        audio_path=audio,
        duration_ms=2000,
        runner=runner,
    )

    assert result["status"] == "completed"
    assert result["turns"][0]["rawSpeakerId"] == "3DSPK_0"
    assert observed["commands"][0][0] == "ffmpeg"
    assert any("fps=25" in value for value in observed["commands"][0])
    recipe_commands = observed["commands"][1:]
    assert all(command[0] == "bash" for command in recipe_commands)
    stages = [command[command.index("--stage") + 1] for command in recipe_commands]
    assert stages[0] == "2"
    assert set(stages[1:3]) == {"3", "4"}
    assert stages[3] == "5"
    assert all(command[command.index("--nj") + 1] == "1" for command in recipe_commands)
    assert int(observed["omp_threads"]) >= 1
    assert Path(observed["cwd"]).name == "speaker-diarization"
    assert list((runtime / "jobs").glob("*")) == []


def test_audio_embedding_and_visual_embedding_stages_really_overlap(tmp_path):
    runtime = _runtime(tmp_path)
    video = tmp_path / "source.mp4"
    audio = tmp_path / "source.wav"
    video.write_bytes(b"video")
    audio.write_bytes(b"audio")
    barrier = threading.Barrier(2)
    spans = {}

    def runner(command, **kwargs):
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"normalized-video")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        stage = command[command.index("--stage") + 1]
        if stage in {"3", "4"}:
            spans[stage] = [time.monotonic(), None]
            barrier.wait(timeout=1)
            time.sleep(0.03)
            spans[stage][1] = time.monotonic()
        exp = Path(command[command.index("--exp") + 1])
        if stage == "5":
            rttm_dir = exp / "rttm"
            rttm_dir.mkdir(parents=True, exist_ok=True)
            (rttm_dir / "source.rttm").write_text(
                "SPEAKER source 0 0.000 1.000 <NA> <NA> 0 <NA> <NA>\n",
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    run_analysis(
        runtime_dir=runtime,
        video_path=video,
        audio_path=audio,
        duration_ms=2000,
        runner=runner,
    )

    assert spans["3"][0] < spans["4"][1]
    assert spans["4"][0] < spans["3"][1]


def test_two_independent_jobs_never_share_workspaces_or_rttm(tmp_path):
    runtime = _runtime(tmp_path)
    inputs = []
    for index in (1, 2):
        video = tmp_path / f"source-{index}.mp4"
        audio = tmp_path / f"source-{index}.wav"
        video.write_bytes(b"video")
        audio.write_bytes(b"audio")
        inputs.append((video, audio))

    stage_two_barrier = threading.Barrier(2)
    observed_jobs = set()
    observed_lock = threading.Lock()

    def runner(command, **kwargs):
        if command[0] == "ffmpeg":
            Path(command[-1]).write_bytes(b"normalized-video")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        stage = command[command.index("--stage") + 1]
        exp = Path(command[command.index("--exp") + 1])
        with observed_lock:
            observed_jobs.add(exp.parent)
        if stage == "2":
            stage_two_barrier.wait(timeout=1)
        if stage == "5":
            rttm_dir = exp / "rttm"
            rttm_dir.mkdir(parents=True, exist_ok=True)
            label = exp.parent.name.replace("3dspk-", "")
            (rttm_dir / "media.rttm").write_text(
                f"SPEAKER media 0 0.000 1.000 <NA> <NA> {label} <NA> <NA>\n",
                encoding="utf-8",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                run_analysis,
                runtime_dir=runtime,
                video_path=video,
                audio_path=audio,
                duration_ms=2000,
                runner=runner,
            )
            for video, audio in inputs
        ]
        results = [future.result() for future in futures]

    assert len(observed_jobs) == 2
    assert results[0]["turns"][0]["rawSpeakerId"] != results[1]["turns"][0]["rawSpeakerId"]
    assert list((runtime / "jobs").glob("*")) == []
