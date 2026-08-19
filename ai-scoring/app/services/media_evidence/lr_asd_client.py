"""Bounded subprocess boundary for the isolated local LR-ASD runtime."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

from .active_speaker_contract import (
    ActiveSpeakerContractError,
    normalize_active_speaker_result,
)
from .persistent_model_transport import JsonLineModelTransport


class LocalLrAsdError(RuntimeError):
    """Named failure at the local active-speaker evidence boundary."""


class PersistentLrAsdTransport:
    """LR-ASD adapter over the reusable JSON-lines process protocol."""

    def __init__(
        self,
        *,
        python_executable: str | Path,
        worker_script: str | Path,
        model_repository: str | Path,
        model_weight: str | Path,
        yunet_model: str | Path,
        sface_model: str | Path,
        global_identity_threshold: float,
        global_identity_stable_threshold: float,
        global_identity_minimum_detections: int,
        global_identity_minimum_visibility: float,
    ) -> None:
        self._transport = JsonLineModelTransport(
            [
                str(python_executable),
                str(worker_script),
                "--model-repository",
                str(model_repository),
                "--model-weight",
                str(model_weight),
                "--yunet-model",
                str(yunet_model),
                "--sface-model",
                str(sface_model),
                "--global-identity-threshold",
                str(global_identity_threshold),
                "--global-identity-stable-threshold",
                str(global_identity_stable_threshold),
                "--global-identity-minimum-detections",
                str(global_identity_minimum_detections),
                "--global-identity-minimum-visibility",
                str(global_identity_minimum_visibility),
                "--serve",
            ]
        )

    def analyze(self, video_path: Path, wav_path: Path, *, timeout_seconds: float) -> dict:
        return self._transport.request(
            {"video": str(video_path), "audio": str(wav_path)},
            timeout_seconds=timeout_seconds,
        )

    def close(self) -> None:
        self._transport.close()


class LocalLrAsdClient:
    def __init__(
        self,
        *,
        python_executable: str | Path,
        worker_script: str | Path,
        model_repository: str | Path,
        model_weight: str | Path,
        yunet_model: str | Path,
        sface_model: str | Path,
        timeout_seconds: float,
        global_identity_threshold: float = 0.60,
        global_identity_stable_threshold: float = 0.80,
        global_identity_minimum_detections: int = 3,
        global_identity_minimum_visibility: float = 0.60,
        runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        self._python_executable = Path(python_executable)
        self._worker_script = Path(worker_script)
        self._model_repository = Path(model_repository)
        self._model_weight = Path(model_weight)
        self._yunet_model = Path(yunet_model)
        self._sface_model = Path(sface_model)
        self._timeout_seconds = max(1.0, float(timeout_seconds))
        self._global_identity_threshold = max(
            0.0, min(1.0, float(global_identity_threshold))
        )
        self._global_identity_stable_threshold = max(
            self._global_identity_threshold,
            min(1.0, float(global_identity_stable_threshold)),
        )
        self._global_identity_minimum_detections = max(
            1, int(global_identity_minimum_detections)
        )
        self._global_identity_minimum_visibility = max(
            0.0, min(1.0, float(global_identity_minimum_visibility))
        )
        self._runner = runner or subprocess.run
        self._persistent_transport = None

    def set_persistent_transport(self, transport) -> None:
        if transport is not None and not callable(getattr(transport, "analyze", None)):
            raise TypeError("invalid_lr_asd_persistent_transport")
        self._persistent_transport = transport

    @staticmethod
    def _require_file(path: Path, code: str) -> None:
        if not path.is_file():
            raise LocalLrAsdError(code)

    def _validate(self, video_path: Path, wav_path: Path) -> None:
        self._require_file(self._python_executable, "lr_asd_python_missing")
        self._require_file(self._worker_script, "lr_asd_worker_missing")
        if not self._model_repository.is_dir():
            raise LocalLrAsdError("lr_asd_model_repository_missing")
        self._require_file(self._model_weight, "lr_asd_model_weight_missing")
        self._require_file(self._yunet_model, "lr_asd_yunet_model_missing")
        self._require_file(self._sface_model, "lr_asd_sface_model_missing")
        self._require_file(video_path, "lr_asd_video_missing")
        self._require_file(wav_path, "lr_asd_audio_missing")

    def analyze(self, video_path: str | Path, wav_path: str | Path) -> dict:
        video = Path(video_path)
        audio = Path(wav_path)
        self._validate(video, audio)
        if self._persistent_transport is not None:
            try:
                raw = self._persistent_transport.analyze(
                    video, audio, timeout_seconds=self._timeout_seconds
                )
                return normalize_active_speaker_result(raw)
            except (
                BrokenPipeError,
                EOFError,
                OSError,
                TimeoutError,
                ActiveSpeakerContractError,
                TypeError,
            ):
                # Preserve the proven one-shot boundary as a safe fallback.
                pass
        command = [
            str(self._python_executable),
            str(self._worker_script),
            "--model-repository",
            str(self._model_repository),
            "--model-weight",
            str(self._model_weight),
            "--yunet-model",
            str(self._yunet_model),
            "--sface-model",
            str(self._sface_model),
            "--video",
            str(video),
            "--audio",
            str(audio),
            "--global-identity-threshold",
            str(self._global_identity_threshold),
            "--global-identity-stable-threshold",
            str(self._global_identity_stable_threshold),
            "--global-identity-minimum-detections",
            str(self._global_identity_minimum_detections),
            "--global-identity-minimum-visibility",
            str(self._global_identity_minimum_visibility),
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
            raise LocalLrAsdError("lr_asd_timeout") from exc
        except OSError as exc:
            raise LocalLrAsdError(
                f"lr_asd_launch_failed:{type(exc).__name__}"
            ) from exc
        if int(completed.returncode) != 0:
            raise LocalLrAsdError(f"lr_asd_worker_failed:{completed.returncode}")
        try:
            raw = json.loads(str(completed.stdout or "").strip())
            return normalize_active_speaker_result(raw)
        except (json.JSONDecodeError, ActiveSpeakerContractError, TypeError) as exc:
            raise LocalLrAsdError("lr_asd_invalid_output") from exc
