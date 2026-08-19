"""Strict score-free contract for local 3D-Speaker diarization evidence."""

from __future__ import annotations

from copy import deepcopy
import math
import re


CONTRACT_VERSION = "3d-speaker-local-v1"
PROVIDER = "local_3d_speaker"
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
_FORBIDDEN_SCORE_KEYS = {
    "score",
    "overallscore",
    "dimensionscore",
    "deductedpoints",
    "maxrecoverablepoints",
    "predictedscore",
    "scoreimpact",
}


class ThreeDSpeakerContractError(ValueError):
    """Raised when local multimodal diarization output is unsafe."""


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _reject_score_fields(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalized_key(key) in _FORBIDDEN_SCORE_KEYS:
                raise ThreeDSpeakerContractError(
                    f"forbidden_score_field:{path}.{key}"
                )
            _reject_score_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_score_fields(child, f"{path}[{index}]")


def _milliseconds(value: str, *, field: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ThreeDSpeakerContractError(f"invalid_time:{field}") from exc
    if not math.isfinite(number) or number < 0:
        raise ThreeDSpeakerContractError(f"invalid_time:{field}")
    return int(round(number * 1000))


def _provider_label(value: object) -> str:
    raw = str(value or "").strip()
    if not _SAFE_LABEL.fullmatch(raw):
        raise ThreeDSpeakerContractError("invalid_speaker")
    return raw if raw.startswith("3DSPK_") else f"3DSPK_{raw}"


def _coalesce(turns: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for turn in sorted(
        turns,
        key=lambda item: (
            item["startMs"], item["endMs"], item["sourceClusterId"]
        ),
    ):
        if (
            merged
            and merged[-1]["sourceClusterId"] == turn["sourceClusterId"]
            and turn["startMs"] <= merged[-1]["endMs"]
        ):
            merged[-1]["endMs"] = max(merged[-1]["endMs"], turn["endMs"])
            continue
        merged.append(dict(turn))
    for index, turn in enumerate(merged, start=1):
        turn["turnId"] = f"3DSPK_TURN_{index}"
    return merged


def parse_rttm(text: str, *, duration_ms: int) -> list[dict]:
    """Parse one RTTM file into deterministic millisecond speaker turns."""

    if isinstance(duration_ms, bool) or int(duration_ms) < 0:
        raise ThreeDSpeakerContractError("invalid_duration")
    duration_ms = int(duration_ms)
    turns: list[dict] = []
    for line_number, raw_line in enumerate(str(text or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 8 or fields[0] != "SPEAKER":
            raise ThreeDSpeakerContractError(f"invalid_record:{line_number}")
        start_ms = _milliseconds(fields[3], field=f"line_{line_number}.start")
        length_ms = _milliseconds(fields[4], field=f"line_{line_number}.duration")
        if length_ms <= 0:
            raise ThreeDSpeakerContractError(f"invalid_time:line_{line_number}.duration")
        end_ms = start_ms + length_ms
        if end_ms > duration_ms:
            raise ThreeDSpeakerContractError(f"out_of_bounds:{line_number}")
        speaker = _provider_label(fields[7])
        turns.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "rawSpeakerId": speaker,
                "sourceClusterId": speaker,
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    return _coalesce(turns)


def normalize_three_d_speaker_result(raw: dict, *, duration_ms: int) -> dict:
    """Validate and deterministically normalize a worker result."""

    if not isinstance(raw, dict):
        raise ThreeDSpeakerContractError("invalid_result")
    result = deepcopy(raw)
    _reject_score_fields(result)
    if result.get("contractVersion") != CONTRACT_VERSION:
        raise ThreeDSpeakerContractError("invalid_contract_version")
    if result.get("provider") != PROVIDER:
        raise ThreeDSpeakerContractError("invalid_provider")
    raw_status = str(result.get("status") or "").strip().lower()
    if raw_status not in {"completed", "partial", "evidence_incomplete", "failed"}:
        raise ThreeDSpeakerContractError("invalid_status")
    normalized_turns: list[dict] = []
    for index, item in enumerate(result.get("turns") or [], start=1):
        if not isinstance(item, dict):
            raise ThreeDSpeakerContractError(f"invalid_turn:{index}")
        try:
            start_ms = int(item.get("startMs"))
            end_ms = int(item.get("endMs"))
        except (TypeError, ValueError) as exc:
            raise ThreeDSpeakerContractError(f"invalid_time:turn_{index}") from exc
        if start_ms < 0 or end_ms <= start_ms:
            raise ThreeDSpeakerContractError(f"invalid_time:turn_{index}")
        if end_ms > int(duration_ms):
            raise ThreeDSpeakerContractError(f"out_of_bounds:turn_{index}")
        source = _provider_label(
            item.get("sourceClusterId") or item.get("rawSpeakerId")
        )
        normalized_turns.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "rawSpeakerId": source,
                "sourceClusterId": source,
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    turns = _coalesce(normalized_turns)
    clusters = sorted({item["sourceClusterId"] for item in turns})
    diagnostics = result.get("diagnostics") or {}
    if not isinstance(diagnostics, dict):
        raise ThreeDSpeakerContractError("invalid_diagnostics")
    clean_diagnostics = deepcopy(diagnostics)
    clean_diagnostics.update(
        {
            "speakerClusterCount": len(clusters),
            "turnCount": len(turns),
            "speechDurationMs": sum(
                item["endMs"] - item["startMs"] for item in turns
            ),
        }
    )
    return {
        "contractVersion": CONTRACT_VERSION,
        "status": raw_status if turns else "evidence_incomplete",
        "provider": PROVIDER,
        "turns": turns,
        "diagnostics": clean_diagnostics,
    }
