#!/usr/bin/env python3
"""Isolated wrapper around the pinned official 3D-Speaker video recipe."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.media_evidence.three_d_speaker_contract import (
    CONTRACT_VERSION,
    PROVIDER,
    parse_rttm,
)


UPSTREAM_COMMIT = "065629c313eaf1a01c65c640c46d77e61e9607b4"
MODEL_NAMES = (
    "version-RFB-320.onnx",
    "asd.onnx",
    "fqa.onnx",
    "face_recog_ir101.onnx",
)


def _platform_name() -> str:
    return f"{platform.system().lower()}-{platform.machine().lower()}"


def _available_providers() -> list[str]:
    try:
        import onnxruntime

        return list(onnxruntime.get_available_providers())
    except Exception:
        return []


def _paths(runtime_dir: Path) -> tuple[Path, Path]:
    recipe = (
        runtime_dir
        / "repository"
        / "egs"
        / "3dspeaker"
        / "speaker-diarization"
    )
    models = runtime_dir / "models" / "onnx"
    return recipe, models


def build_health_report(
    runtime_dir: str | Path,
    *,
    providers: list[str] | None = None,
    platform_name: str | None = None,
) -> dict:
    runtime = Path(runtime_dir)
    recipe, models = _paths(runtime)
    assets = {
        "recipe": (recipe / "run_video.sh").is_file(),
        **{name: (models / name).is_file() for name in MODEL_NAMES},
    }
    execution_providers = list(
        _available_providers() if providers is None else providers
    )
    return {
        "status": "ready" if all(assets.values()) and execution_providers else "unavailable",
        "platform": platform_name or _platform_name(),
        "executionProviders": execution_providers,
        "runtimeCommit": UPSTREAM_COMMIT,
        "assets": assets,
    }


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _process_tree_rss_bytes(ps_output: str, *, root_pid: int) -> int:
    """Sum resident memory for a process and every transitive child."""
    rows: dict[int, tuple[int, int]] = {}
    for line in str(ps_output or "").splitlines():
        fields = line.split()
        if len(fields) != 3:
            continue
        try:
            pid, parent_pid, rss_kib = (int(value) for value in fields)
        except ValueError:
            continue
        if pid > 0 and parent_pid >= 0 and rss_kib >= 0:
            rows[pid] = (parent_pid, rss_kib)
    descendants = {int(root_pid)}
    changed = True
    while changed:
        changed = False
        for pid, (parent_pid, _) in rows.items():
            if parent_pid in descendants and pid not in descendants:
                descendants.add(pid)
                changed = True
    return sum(rows.get(pid, (0, 0))[1] for pid in descendants) * 1024


def _terminate_process_group(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            process.terminate()
        except OSError:
            return
    try:
        process.wait(timeout=0.5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        try:
            process.kill()
        except OSError:
            return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        return


def _run_parallel_subprocesses_fail_fast(
    named_commands: dict[str, list[str]],
    *,
    cwd: str | Path,
    env: dict[str, str],
    log_dir: str | Path,
    poll_interval_seconds: float = 0.05,
) -> dict[str, int]:
    """Run independent official stages and stop every sibling on first failure."""
    if not named_commands:
        return {}
    logs = Path(log_dir)
    logs.mkdir(parents=True, exist_ok=True)
    processes: dict[str, subprocess.Popen] = {}
    handles = {}
    started: dict[str, float] = {}
    timings: dict[str, int] = {}
    pending = set(named_commands)
    try:
        for name, command in named_commands.items():
            handle = (logs / f"{name}.log").open("wb")
            handles[name] = handle
            started[name] = time.monotonic()
            processes[name] = subprocess.Popen(
                command,
                cwd=str(cwd),
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                shell=False,
                start_new_session=True,
            )
        interval = max(0.01, float(poll_interval_seconds))
        while pending:
            for name in tuple(pending):
                return_code = processes[name].poll()
                if return_code is None:
                    continue
                pending.remove(name)
                timings[name] = int(
                    round((time.monotonic() - started[name]) * 1000)
                )
                if int(return_code) != 0:
                    for sibling in tuple(pending):
                        _terminate_process_group(processes[sibling])
                    raise RuntimeError(
                        f"official_recipe_failed:{name}:{int(return_code)}"
                    )
            if pending:
                time.sleep(interval)
        return timings
    except Exception:
        for process in processes.values():
            _terminate_process_group(process)
        raise
    finally:
        for handle in handles.values():
            handle.close()


class _ProcessTreeRssMonitor:
    """Low-frequency aggregate RSS sampler for concurrent local stages."""

    def __init__(self, *, root_pid: int | None = None, interval_seconds: float = 1.0):
        self._root_pid = int(root_pid or os.getpid())
        self._interval_seconds = max(0.25, float(interval_seconds))
        self._stop = threading.Event()
        self._peak_bytes = 0
        self._thread = threading.Thread(
            target=self._run,
            name="3dspk-rss-monitor",
            daemon=True,
        )

    def _sample(self) -> None:
        try:
            completed = subprocess.run(
                ["ps", "-axo", "pid=,ppid=,rss="],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                shell=False,
            )
            if completed.returncode == 0:
                self._peak_bytes = max(
                    self._peak_bytes,
                    _process_tree_rss_bytes(
                        completed.stdout,
                        root_pid=self._root_pid,
                    ),
                )
        except (OSError, subprocess.TimeoutExpired):
            return

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sample()
            self._stop.wait(self._interval_seconds)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> int:
        self._stop.set()
        self._thread.join(timeout=6)
        self._sample()
        return max(self._peak_bytes, _peak_rss_bytes())


def _run_analysis_impl(
    *,
    runtime_dir: str | Path,
    video_path: str | Path,
    audio_path: str | Path,
    duration_ms: int,
    runner=subprocess.run,
) -> dict:
    started = time.monotonic()
    runtime = Path(runtime_dir).resolve()
    video = Path(video_path).resolve()
    audio = Path(audio_path).resolve()
    health = build_health_report(
        runtime,
        providers=_available_providers() or ["CPUExecutionProvider"],
    )
    if health["status"] != "ready":
        raise RuntimeError("runtime_assets_missing")
    if not video.is_file() or not audio.is_file():
        raise RuntimeError("media_missing")
    recipe, models = _paths(runtime)
    jobs = runtime / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="3dspk-", dir=jobs) as temporary:
        job = Path(temporary)
        input_dir = job / "input"
        examples = job / "examples"
        raw = job / "exp" / "raw"
        input_dir.mkdir()
        examples.mkdir()
        raw.mkdir(parents=True)
        input_video = input_dir / "media.mp4"
        raw_video = raw / "media.mp4"
        raw_audio = raw / "media.wav"
        input_video.symlink_to(video)
        raw_audio.symlink_to(audio)
        (examples / "video.list").write_text(
            str(input_video) + "\n", encoding="utf-8"
        )
        (raw / "video.list").write_text(str(raw_video) + "\n", encoding="utf-8")
        (raw / "wav.list").write_text(str(raw_audio) + "\n", encoding="utf-8")
        environment = os.environ.copy()
        # Venv console scripts (torchrun, funasr, …) may carry host shebangs like
        # #!/data/orep-storage/.../venv/bin/python while the container mounts the
        # same tree at /app/models/.... Prefer the live interpreter and a PATH
        # shim so recipe stages never depend on absolute host shebangs.
        venv_bin = Path(sys.executable).parent
        if not (venv_bin / "python").exists() and (runtime / ".venv" / "bin").is_dir():
            venv_bin = runtime / ".venv" / "bin"
        shim_dir = job / "bin"
        shim_dir.mkdir(parents=True, exist_ok=True)
        torchrun_shim = shim_dir / "torchrun"
        torchrun_shim.write_text(
            "#!/bin/bash\n"
            f'exec "{sys.executable}" -m torch.distributed.run "$@"\n',
            encoding="utf-8",
        )
        torchrun_shim.chmod(0o755)
        environment["PATH"] = (
            f"{shim_dir}:{venv_bin}:{environment.get('PATH', '')}"
        )
        environment["PYTHONPATH"] = (
            f"{runtime / 'repository'}:{environment.get('PYTHONPATH', '')}"
        )
        environment["MODELSCOPE_CACHE"] = str(models.parent / "modelscope-cache")
        environment["MODELSCOPE_OFFLINE"] = "1"
        environment["THREED_SPEAKER_CAMPPLUS"] = str(
            models.parent / "campplus_cn_en_common.pt"
        )
        environment["THREED_SPEAKER_VAD_MODEL"] = str(models.parent / "vad")
        environment["THREED_SPEAKER_OMP_NUM_THREADS"] = str(
            max(1, min(4, (os.cpu_count() or 4) // 3))
        )
        exp = job / "exp"
        stage_timings: dict[str, int] = {}

        # The official video processor uses a 25 fps audio/video clock. Normalize
        # every source locally so 24/30/variable-fps recordings cannot accumulate
        # speaker drift over a long roadshow. Width is capped but never upscaled.
        normalize_started = time.monotonic()
        normalized = runner(
            [
                "ffmpeg", "-nostdin", "-y", "-i", str(video),
                "-vf", "scale='min(960,iw)':-2,fps=25",
                "-an", "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "24", "-pix_fmt", "yuv420p", str(raw_video),
            ],
            cwd=str(recipe),
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )
        stage_timings["video_normalization"] = int(
            round((time.monotonic() - normalize_started) * 1000)
        )
        if int(normalized.returncode) != 0 or not raw_video.is_file():
            raise RuntimeError(
                f"video_normalization_failed:{int(normalized.returncode)}"
            )

        def audio_command(stage: int, stop_stage: int) -> list[str]:
            return [
                "bash", "run_audio.sh",
                "--stage", str(stage), "--stop_stage", str(stop_stage),
                "--examples", str(raw), "--exp", str(exp),
                "--nj", "1", "--gpus", "0",
            ]

        def video_command(stage: int, stop_stage: int) -> list[str]:
            return [
                "bash", "run_video.sh",
                "--stage", str(stage), "--stop_stage", str(stop_stage),
                "--examples", str(examples), "--exp", str(exp),
                "--onnx_dir", str(models), "--nj", "1", "--gpus", "0",
            ]

        def invoke(name: str, command: list[str]) -> None:
            stage_started = time.monotonic()
            completed = runner(
                command,
                cwd=str(recipe),
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )
            stage_timings[name] = int(round((time.monotonic() - stage_started) * 1000))
            if int(completed.returncode) != 0:
                raise RuntimeError(
                    f"official_recipe_failed:{name}:{int(completed.returncode)}"
                )

        # VAD is the only shared dependency. Once ready, CPU-heavy audio and
        # visual embeddings use independent files and can safely overlap.
        invoke("vad", audio_command(2, 2))
        if runner is subprocess.run:
            stage_timings.update(
                _run_parallel_subprocesses_fail_fast(
                    {
                        "audio_embeddings": audio_command(3, 4),
                        "visual_embeddings": video_command(4, 4),
                    },
                    cwd=recipe,
                    env=environment,
                    log_dir=job / "logs",
                )
            )
        else:
            # Injected runners are used only by deterministic unit tests. Real
            # stages use the process supervisor above so a failed branch kills
            # its still-running sibling instead of waiting for it.
            with ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="3dspk",
            ) as executor:
                audio_future = executor.submit(
                    invoke, "audio_embeddings", audio_command(3, 4)
                )
                visual_future = executor.submit(
                    invoke, "visual_embeddings", video_command(4, 4)
                )
                audio_future.result()
                visual_future.result()
        invoke("joint_clustering", video_command(5, 5))
        rttm_files = sorted((job / "exp" / "rttm").glob("*.rttm"))
        if len(rttm_files) != 1:
            raise RuntimeError(f"invalid_rttm_count:{len(rttm_files)}")
        turns = parse_rttm(
            rttm_files[0].read_text(encoding="utf-8"),
            duration_ms=int(duration_ms),
        )
        elapsed_ms = int(round((time.monotonic() - started) * 1000))
        return {
            "contractVersion": CONTRACT_VERSION,
            "status": "completed" if turns else "evidence_incomplete",
            "provider": PROVIDER,
            "turns": turns,
            "diagnostics": {
                "processingDurationMs": elapsed_ms,
                "peakRssBytes": _peak_rss_bytes(),
                "runtimeCommit": UPSTREAM_COMMIT,
                "platform": health["platform"],
                "executionProviders": health["executionProviders"],
                "stageDurationMs": stage_timings,
            },
        }


def run_analysis(
    *,
    runtime_dir: str | Path,
    video_path: str | Path,
    audio_path: str | Path,
    duration_ms: int,
    runner=subprocess.run,
) -> dict:
    rss_monitor = _ProcessTreeRssMonitor()
    rss_monitor.start()
    result: dict | None = None
    try:
        result = _run_analysis_impl(
            runtime_dir=runtime_dir,
            video_path=video_path,
            audio_path=audio_path,
            duration_ms=duration_ms,
            runner=runner,
        )
        return result
    finally:
        aggregate_peak = rss_monitor.stop()
        if result is not None:
            result.setdefault("diagnostics", {})["peakRssBytes"] = aggregate_peak


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local 3D-Speaker worker")
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--video")
    parser.add_argument("--audio")
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--health-check", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.health_check:
            print(json.dumps(build_health_report(args.runtime_dir), ensure_ascii=False))
            return 0
        if not args.video or not args.audio or not args.duration_ms:
            raise RuntimeError("media_arguments_missing")
        result = run_analysis(
            runtime_dir=args.runtime_dir,
            video_path=args.video,
            audio_path=args.audio,
            duration_ms=args.duration_ms,
        )
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        # Always surface the named failure: operators need recipe stage codes
        # (e.g. visual_embeddings:127) without flipping a debug env var.
        print(
            f"3d_speaker_worker_failed:{type(exc).__name__}:{exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
