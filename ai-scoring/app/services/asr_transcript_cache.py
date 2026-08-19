"""Internal same-file ASR transcript cache.

Keyed by video sha256 + ASR recipe. Stores only transcript text and timed
segments. Never stores sessionId, speaker labels, or filesystem paths.
Not a user-facing lookup.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_FORMAT = "asr-cache-v1"
ASR_ENGINE_ID = "fun-asr-realtime-2026-02-28"
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_SEGMENT_KEYS = ("start", "end", "startMs", "endMs", "text")


def recipe_id() -> str:
    engine = str(getattr(settings, "ASR_TRANSCRIPT_ENGINE_ID", "") or ASR_ENGINE_ID).strip()
    return f"{CACHE_FORMAT}:{engine}"


def normalize_video_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    if not _SHA256_RE.fullmatch(text):
        return None
    return text


def resolve_video_sha256(project_info: dict | None, video_path: str | None = None) -> str | None:
    info = project_info or {}
    for key in ("videoSha256", "video_sha256", "fileHash", "file_hash"):
        found = normalize_video_sha256(info.get(key) if isinstance(info.get(key), str) else None)
        if found:
            return found
    path = video_path or info.get("video_path") or info.get("videoFilePath")
    if path and os.path.isfile(path):
        return hash_file_sha256(path)
    return None


def hash_file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def cache_root() -> Path:
    root = Path(getattr(settings, "UPLOAD_DIR", "uploads")) / "asr-cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_dir(video_sha256: str, recipe: str | None = None) -> Path:
    sha = normalize_video_sha256(video_sha256)
    if not sha:
        raise ValueError("invalid_video_sha256")
    recipe_key = re.sub(r"[^a-zA-Z0-9._-]+", "_", recipe or recipe_id())
    path = cache_root() / sha / recipe_key
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_payload(asr_result: dict, *, video_sha256: str, recipe: str | None = None) -> dict[str, Any]:
    """Strip anything that could leak another session."""
    segments = []
    for item in asr_result.get("segments") or []:
        if not isinstance(item, dict):
            continue
        row = {key: item.get(key) for key in _SEGMENT_KEYS if item.get(key) is not None}
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        row["text"] = text
        segments.append(row)
    transcript = str(asr_result.get("transcript") or "").strip()
    if not transcript:
        transcript = "".join(str(seg.get("text") or "") for seg in segments)
    return {
        "status": "ready",
        "recipe": recipe or recipe_id(),
        "videoSha256": normalize_video_sha256(video_sha256),
        "duration": asr_result.get("duration") or 0,
        "transcript": transcript,
        "segments": segments,
        "source": f"asr_cache:{recipe or recipe_id()}",
    }


def to_asr_result(payload: dict) -> dict[str, Any]:
    return {
        "transcript": payload.get("transcript") or "",
        "segments": list(payload.get("segments") or []),
        "duration": payload.get("duration") or 0,
        "speakers": [],
        "source": payload.get("source") or f"asr_cache:{payload.get('recipe') or recipe_id()}",
    }


def load_ready(video_sha256: str, recipe: str | None = None) -> dict[str, Any] | None:
    sha = normalize_video_sha256(video_sha256)
    if not sha:
        return None
    path = cache_dir(sha, recipe) / "transcript.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("status") != "ready":
        return None
    if payload.get("videoSha256") != sha:
        return None
    if "sessionId" in payload or "session_id" in payload:
        logger.warning("asr cache rejected: payload contains session id")
        return None
    if not (payload.get("transcript") or payload.get("segments")):
        return None
    return payload


def store_ready(video_sha256: str, asr_result: dict, recipe: str | None = None) -> Path:
    sha = normalize_video_sha256(video_sha256)
    if not sha:
        raise ValueError("invalid_video_sha256")
    recipe_name = recipe or recipe_id()
    directory = cache_dir(sha, recipe_name)
    payload = public_payload(asr_result, video_sha256=sha, recipe=recipe_name)
    final_path = directory / "transcript.json"
    temporary_path = directory / f".transcript.{uuid4().hex}.tmp"
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, final_path)
        _clear_pending(directory)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return final_path


def mark_pending(video_sha256: str, recipe: str | None = None) -> None:
    sha = normalize_video_sha256(video_sha256)
    if not sha:
        return
    directory = cache_dir(sha, recipe)
    path = directory / "pending.json"
    path.write_text(
        json.dumps({"status": "pending", "startedAt": time.time()}, ensure_ascii=False),
        encoding="utf-8",
    )


def pending_age_seconds(video_sha256: str, recipe: str | None = None) -> float | None:
    sha = normalize_video_sha256(video_sha256)
    if not sha:
        return None
    path = cache_dir(sha, recipe) / "pending.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        started = float(payload.get("startedAt") or path.stat().st_mtime)
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return None
    return max(0.0, time.time() - started)


def wait_for_ready(
    video_sha256: str,
    recipe: str | None = None,
    *,
    timeout_seconds: float | None = None,
    poll_seconds: float = 1.0,
) -> dict[str, Any] | None:
    deadline = time.time() + float(
        timeout_seconds
        if timeout_seconds is not None
        else getattr(settings, "ASR_CACHE_WAIT_SECONDS", 0) or 0
    )
    while time.time() < deadline:
        ready = load_ready(video_sha256, recipe)
        if ready:
            return ready
        age = pending_age_seconds(video_sha256, recipe)
        if age is None:
            return None
        time.sleep(max(0.05, poll_seconds))
    return load_ready(video_sha256, recipe)


def should_force_retranscribe(project_info: dict | None) -> bool:
    info = project_info or {}
    value = info.get("forceRetranscribe")
    if value is None:
        value = info.get("force_retranscribe")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def get_or_transcribe(
    *,
    project_info: dict | None,
    video_path: str | None,
    transcribe,
) -> dict[str, Any]:
    """Reuse a ready cache or run transcribe() and store the public payload."""
    sha = resolve_video_sha256(project_info, video_path)
    recipe = recipe_id()
    force = should_force_retranscribe(project_info)
    if sha and not force:
        cached = load_ready(sha, recipe)
        if cached:
            logger.info("asr cache hit sha=%s recipe=%s", sha[:12], recipe)
            return to_asr_result(cached)
        wait_seconds = float(getattr(settings, "ASR_CACHE_WAIT_SECONDS", 0) or 0)
        if wait_seconds > 0 and pending_age_seconds(sha, recipe) is not None:
            cached = wait_for_ready(sha, recipe, timeout_seconds=wait_seconds)
            if cached:
                logger.info("asr cache wait-hit sha=%s recipe=%s", sha[:12], recipe)
                return to_asr_result(cached)
        mark_pending(sha, recipe)
    result = transcribe()
    if sha and isinstance(result, dict) and (result.get("transcript") or result.get("segments")):
        try:
            store_ready(sha, result, recipe)
        except Exception as exc:
            logger.warning("asr cache store failed sha=%s err=%s", sha[:12], exc)
    return result


def _clear_pending(directory: Path) -> None:
    pending = directory / "pending.json"
    pending.unlink(missing_ok=True)
