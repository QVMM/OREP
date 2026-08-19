"""Bounded local-process client for the isolated 3D-Speaker runtime."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Callable

from .three_d_speaker_contract import (
    ThreeDSpeakerContractError,
    normalize_three_d_speaker_result,
)


class LocalThreeDSpeakerError(RuntimeError):
    """Named failure at the local audio-visual diarization boundary."""


class LocalThreeDSpeakerClient:
    def __init__(
        self,
        *,
        python_executable: str | Path,
        worker_script: str | Path,
        runtime_dir: str | Path,
        timeout_seconds: float = 1800,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        self._python = Path(python_executable)
        self._worker = Path(worker_script)
        self._runtime = Path(runtime_dir)
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._runner = runner or subprocess.run

    def _validate(self, video: Path, wav: Path) -> None:
        if (
            not self._python.is_file()
            or not self._worker.is_file()
            or not self._runtime.is_dir()
        ):
            raise LocalThreeDSpeakerError("3d_speaker_runtime_missing")
        if not video.is_file() or not wav.is_file():
            raise LocalThreeDSpeakerError("3d_speaker_media_missing")

    def analyze(
        self,
        video_path: str | Path,
        wav_path: str | Path,
        *,
        duration_ms: int,
    ) -> dict:
        video = Path(video_path).resolve()
        wav = Path(wav_path).resolve()
        self._validate(video, wav)
        if isinstance(duration_ms, bool) or int(duration_ms) <= 0:
            raise LocalThreeDSpeakerError("3d_speaker_media_invalid_duration")
        command = [
            # Do not resolve a venv's python symlink: the symlink location is
            # how CPython discovers pyvenv.cfg and isolated site-packages.
            str(self._python.absolute()),
            str(self._worker.resolve()),
            "--runtime-dir",
            str(self._runtime.resolve()),
            "--video",
            str(video),
            "--audio",
            str(wav),
            "--duration-ms",
            str(int(duration_ms)),
        ]
        try:
            completed = self._runner(
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LocalThreeDSpeakerError("3d_speaker_timeout") from exc
        except OSError as exc:
            raise LocalThreeDSpeakerError(
                f"3d_speaker_launch_failed:{type(exc).__name__}"
            ) from exc
        if int(completed.returncode) != 0:
            detail = " ".join(
                part
                for part in (
                    str(completed.stderr or "").strip(),
                    str(completed.stdout or "").strip(),
                )
                if part
            ).replace("\n", " ")
            if len(detail) > 400:
                detail = detail[-400:]
            suffix = f":{detail}" if detail else ""
            raise LocalThreeDSpeakerError(
                f"3d_speaker_process_failed:{int(completed.returncode)}{suffix}"
            )
        try:
            raw = json.loads(str(completed.stdout or "").strip())
            return normalize_three_d_speaker_result(raw, duration_ms=int(duration_ms))
        except (json.JSONDecodeError, ThreeDSpeakerContractError, TypeError) as exc:
            raise LocalThreeDSpeakerError("3d_speaker_invalid_result") from exc
