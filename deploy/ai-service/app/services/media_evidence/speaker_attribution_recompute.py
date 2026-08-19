"""One-click recompute of final speaker attribution for an existing session.

Does not re-run ASR or 3D-Speaker. Rebuilds the FINAL identity snapshot from:
1. Stored scoring result ASR segments (preferred), or prior attribution segments
2. Prior attribution turns, else reconstructed turns from ASR cluster labels

Used when the identity policy (contestant auto-assignment) changes and old
sessions still show VISITOR/外部人员 labels that the new policy would fix.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.media_evidence.final_speaker_attribution import (
    build_final_speaker_attribution,
)
from app.services.media_evidence.speaker_attribution_shadow import (
    save_shadow_attribution,
)
from app.services.media_evidence.three_d_speaker_contract import (
    CONTRACT_VERSION as THREE_D_CONTRACT,
    PROVIDER as THREE_D_PROVIDER,
)

logger = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]")


class SpeakerAttributionRecomputeError(ValueError):
    """Raised when a session cannot be recomputed without re-scoring."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _safe_session_dir_name(session_id: str) -> str:
    return _SAFE_ID.sub("_", str(session_id))[:160]


def _result_path(session_id: str) -> Path:
    return Path(settings.UPLOAD_DIR) / "results" / f"result_{session_id}.json"


def _attribution_dir(session_id: str) -> Path:
    return (
        Path(settings.UPLOAD_DIR)
        / "results"
        / "speaker-attribution"
        / _safe_session_dir_name(session_id)
    )


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("failed to load %s: %s", path, exc)
        return None
    return payload if isinstance(payload, dict) else None


def _next_revision(session_id: str) -> int:
    result_dir = _attribution_dir(session_id)
    highest = 0
    if result_dir.is_dir():
        for name in os.listdir(result_dir):
            if name.startswith("revision-") and name.endswith(".json"):
                try:
                    highest = max(highest, int(name[9:-5]))
                except ValueError:
                    continue
    return highest + 1


def _load_latest_prior_snapshot(session_id: str) -> dict | None:
    result_dir = _attribution_dir(session_id)
    if not result_dir.is_dir():
        return None
    best_rev = 0
    best_path: Path | None = None
    for name in os.listdir(result_dir):
        if not (name.startswith("revision-") and name.endswith(".json")):
            continue
        try:
            rev = int(name[9:-5])
        except ValueError:
            continue
        if rev > best_rev:
            best_rev = rev
            best_path = result_dir / name
    if best_path is None:
        return None
    return _load_json(best_path)


def _segment_time_ms(segment: dict, key: str) -> int:
    explicit = segment.get(f"{key}Ms")
    if explicit is not None:
        try:
            return max(0, int(round(float(explicit))))
        except (TypeError, ValueError):
            pass
    try:
        return max(0, int(round(float(segment.get(key) or 0) * 1000)))
    except (TypeError, ValueError):
        return 0


def _cluster_label(segment: dict) -> str | None:
    for key in ("sourceClusterId", "rawSpeakerId", "speaker", "raw_speaker"):
        value = segment.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _asr_from_result(result: dict) -> dict:
    asr = result.get("asr") if isinstance(result.get("asr"), dict) else {}
    segments = asr.get("segments") if isinstance(asr.get("segments"), list) else []
    cleaned: list[dict] = []
    for item in segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        start_ms = _segment_time_ms(item, "start")
        end_ms = max(start_ms, _segment_time_ms(item, "end"))
        row = {
            "text": text,
            "startMs": start_ms,
            "endMs": end_ms,
            "start": start_ms / 1000.0,
            "end": end_ms / 1000.0,
        }
        cluster = _cluster_label(item)
        if cluster:
            row["sourceClusterId"] = cluster
            row["rawSpeakerId"] = cluster
            row["speaker"] = cluster
        if item.get("confidence") is not None:
            row["confidence"] = item["confidence"]
        if item.get("source") is not None:
            row["source"] = item["source"]
        cleaned.append(row)
    duration = asr.get("duration")
    try:
        duration_s = float(duration) if duration is not None else 0.0
    except (TypeError, ValueError):
        duration_s = 0.0
    if duration_s <= 0 and cleaned:
        duration_s = max(item["endMs"] for item in cleaned) / 1000.0
    return {
        "source": asr.get("source") or "recompute",
        "transcript": asr.get("transcript") or "",
        "duration": duration_s,
        "segments": cleaned,
    }


def _asr_from_prior_snapshot(snapshot: dict) -> dict:
    segments = snapshot.get("segments") if isinstance(snapshot.get("segments"), list) else []
    cleaned: list[dict] = []
    max_end = 0
    for item in segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        try:
            start_ms = max(0, int(item.get("startMs") or 0))
            end_ms = max(start_ms, int(item.get("endMs") or 0))
        except (TypeError, ValueError):
            continue
        max_end = max(max_end, end_ms)
        row = {
            "text": text,
            "startMs": start_ms,
            "endMs": end_ms,
            "start": start_ms / 1000.0,
            "end": end_ms / 1000.0,
        }
        # Prior FINAL segments may lack cluster; recover from person voice maps later
        raw = item.get("rawSpeakerId") or item.get("sourceClusterId")
        if raw:
            row["sourceClusterId"] = str(raw)
            row["rawSpeakerId"] = str(raw)
            row["speaker"] = str(raw)
        cleaned.append(row)
    clock = snapshot.get("clock") if isinstance(snapshot.get("clock"), dict) else {}
    try:
        duration_ms = int(clock.get("durationMs") or max_end)
    except (TypeError, ValueError):
        duration_ms = max_end
    return {
        "source": "prior_speaker_attribution",
        "duration": max(0, duration_ms) / 1000.0,
        "segments": cleaned,
    }


def _turns_from_prior_snapshot(snapshot: dict) -> list[dict]:
    turns = snapshot.get("turns") if isinstance(snapshot.get("turns"), list) else []
    out: list[dict] = []
    for item in turns:
        if not isinstance(item, dict):
            continue
        cluster = item.get("sourceClusterId") or item.get("rawSpeakerId")
        if not cluster:
            continue
        try:
            start_ms = int(item.get("startMs"))
            end_ms = int(item.get("endMs"))
        except (TypeError, ValueError):
            continue
        if end_ms <= start_ms:
            continue
        out.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "sourceClusterId": str(cluster),
                "rawSpeakerId": str(cluster),
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    return out


def _turns_from_asr_segments(asr_result: dict) -> list[dict]:
    out: list[dict] = []
    for item in asr_result.get("segments") or []:
        if not isinstance(item, dict):
            continue
        cluster = _cluster_label(item)
        if not cluster:
            continue
        try:
            start_ms = int(item.get("startMs") or 0)
            end_ms = int(item.get("endMs") or 0)
        except (TypeError, ValueError):
            continue
        if end_ms <= start_ms:
            continue
        out.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "sourceClusterId": cluster,
                "rawSpeakerId": cluster,
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    return out


def _turns_from_people_voice_map(snapshot: dict, asr_result: dict) -> list[dict]:
    """If prior turns empty but people have voiceClusterIds and segments have personId."""
    people = snapshot.get("people") if isinstance(snapshot.get("people"), list) else []
    person_to_cluster: dict[str, str] = {}
    for person in people:
        if not isinstance(person, dict):
            continue
        person_id = str(person.get("personId") or "").strip()
        clusters = person.get("voiceClusterIds") or []
        if person_id and isinstance(clusters, list) and clusters:
            person_to_cluster[person_id] = str(clusters[0])
    if not person_to_cluster:
        return []
    out: list[dict] = []
    segments = snapshot.get("segments") if isinstance(snapshot.get("segments"), list) else []
    for item in segments:
        if not isinstance(item, dict):
            continue
        person_id = str(item.get("personId") or "").strip()
        cluster = person_to_cluster.get(person_id)
        if not cluster:
            continue
        try:
            start_ms = int(item.get("startMs") or 0)
            end_ms = int(item.get("endMs") or 0)
        except (TypeError, ValueError):
            continue
        if end_ms <= start_ms:
            continue
        out.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "sourceClusterId": cluster,
                "rawSpeakerId": cluster,
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    if out:
        return out
    # last resort: stamp ASR segments that have matching person maps already via cluster labels
    return _turns_from_asr_segments(asr_result)


def _build_three_d_provider(turns: list[dict], *, duration_ms: int, source: str) -> dict:
    # Clamp turn ends so contract validation accepts recompute artifacts.
    clamped: list[dict] = []
    for turn in turns:
        start_ms = max(0, int(turn["startMs"]))
        end_ms = min(int(duration_ms), max(start_ms + 1, int(turn["endMs"])))
        if end_ms <= start_ms:
            continue
        clamped.append(
            {
                "startMs": start_ms,
                "endMs": end_ms,
                "sourceClusterId": turn["sourceClusterId"],
                "rawSpeakerId": turn.get("rawSpeakerId") or turn["sourceClusterId"],
                "speakerVerification": "JOINT_AUDIO_VISUAL",
            }
        )
    return {
        "contractVersion": THREE_D_CONTRACT,
        "provider": THREE_D_PROVIDER,
        "status": "completed" if clamped else "evidence_incomplete",
        "turns": clamped,
        "diagnostics": {
            "recomputeSource": source,
            "inputTurnCount": len(turns),
        },
    }


def _contestant_slots(project_info: dict | None, override: int | None) -> int:
    if override is not None:
        try:
            return max(0, min(4, int(override)))
        except (TypeError, ValueError):
            pass
    configured = (project_info or {}).get(
        "expected_contestant_count", (project_info or {}).get("team_size", 4)
    )
    try:
        return max(0, min(4, int(configured)))
    except (TypeError, ValueError):
        return 4


def recompute_final_speaker_attribution(
    session_id: str,
    *,
    contestant_slots: int | None = None,
) -> dict[str, Any]:
    """Rebuild FINAL speaker attribution and persist a new local revision.

    Returns receipt + snapshot suitable for Java persistence.
    """
    sid = str(session_id or "").strip()
    if not sid:
        raise SpeakerAttributionRecomputeError("EMPTY_SESSION_ID", "sessionId 不能为空")

    result = _load_json(_result_path(sid))
    prior = _load_latest_prior_snapshot(sid)

    asr_result: dict
    evidence_source: str
    if result and isinstance(result.get("asr"), dict) and (result["asr"].get("segments") or []):
        asr_result = _asr_from_result(result)
        evidence_source = "result_asr"
    elif prior and (prior.get("segments") or []):
        asr_result = _asr_from_prior_snapshot(prior)
        evidence_source = "prior_snapshot_segments"
    else:
        raise SpeakerAttributionRecomputeError(
            "NO_ASR_EVIDENCE",
            "找不到可用转写证据（result_*.json 或历史 speaker-attribution 快照）",
        )

    if not asr_result.get("segments"):
        raise SpeakerAttributionRecomputeError(
            "EMPTY_TRANSCRIPT",
            "转写段落为空，无法重算人物归属",
        )

    turns = _turns_from_prior_snapshot(prior) if prior else []
    turn_source = "prior_snapshot_turns"
    if not turns:
        turns = _turns_from_asr_segments(asr_result)
        turn_source = "asr_cluster_labels"
    if not turns and prior:
        turns = _turns_from_people_voice_map(prior, asr_result)
        turn_source = "prior_people_voice_map"
    if not turns:
        raise SpeakerAttributionRecomputeError(
            "NO_SPEAKER_CLUSTERS",
            "找不到说话人聚类证据（无 3D turns / ASR speaker 标签），请完整重评",
        )

    duration_s = float(asr_result.get("duration") or 0)
    max_seg_end = max(int(s["endMs"]) for s in asr_result["segments"])
    max_turn_end = max(int(t["endMs"]) for t in turns)
    duration_ms = max(int(round(duration_s * 1000)), max_seg_end, max_turn_end, 1)

    project_info = {}
    if result and isinstance(result.get("project_info"), dict):
        project_info = result["project_info"]
    slots = _contestant_slots(project_info, contestant_slots)
    media_clock = project_info.get("media_clock") if isinstance(project_info, dict) else None
    if prior and isinstance(prior.get("clock"), dict) and not media_clock:
        media_clock = prior["clock"]

    three_d = _build_three_d_provider(
        turns, duration_ms=duration_ms, source=f"{evidence_source}+{turn_source}"
    )
    revision = _next_revision(sid)
    snapshot = build_final_speaker_attribution(
        session_id=sid,
        duration_ms=duration_ms,
        revision=revision,
        asr_result=asr_result,
        three_d_speaker_result=three_d,
        contestant_slots=slots,
        media_clock=media_clock if isinstance(media_clock, dict) else None,
    )
    # Surface recompute provenance in diagnostics for ops.
    diagnostics = snapshot.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics = {
            **diagnostics,
            "recompute": True,
            "recomputeEvidenceSource": evidence_source,
            "recomputeTurnSource": turn_source,
            "previousRevision": (prior or {}).get("revision"),
        }
        snapshot = {**snapshot, "diagnostics": diagnostics}

    receipt = save_shadow_attribution(settings.UPLOAD_DIR, sid, snapshot)

    # Keep local result_*.json in sync so subsequent recomputes and AI result views see head.
    if result is not None:
        asr_block = result.get("asr") if isinstance(result.get("asr"), dict) else {}
        asr_block = {**asr_block, "speakerAttribution": snapshot}
        result = {
            **result,
            "asr": asr_block,
            "speakerAttributionStatus": "completed",
            "speakerAttributionRevision": receipt["revision"],
            "speakerAttributionHash": receipt["snapshotHash"],
        }
        try:
            _result_path(sid).write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("failed to update result json for %s: %s", sid, exc)

    contestants = [
        p
        for p in (snapshot.get("people") or [])
        if isinstance(p, dict) and p.get("personType") == "CONTESTANT"
    ]
    return {
        **receipt,
        "sessionId": sid,
        "snapshot": snapshot,
        "contestantCount": len(contestants),
        "personCount": len(snapshot.get("people") or []),
        "segmentCount": len(snapshot.get("segments") or []),
        "evidenceSource": evidence_source,
        "turnSource": turn_source,
    }
