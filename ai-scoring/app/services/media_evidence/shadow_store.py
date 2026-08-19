"""Atomic local persistence for media-evidence shadow snapshots."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import uuid4


def _save_named_package(upload_dir: str, file_name: str, package: dict) -> str:
    result_dir = Path(upload_dir) / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    final_path = result_dir / file_name
    temporary_path = result_dir / f".{final_path.name}.{uuid4().hex}.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(package, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, final_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return str(final_path)


def save_shadow_package(upload_dir: str, meeting_id: str, package: dict) -> str:
    """Atomically replace one upload shadow snapshot."""

    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(meeting_id))[:160]
    return _save_named_package(
        upload_dir, f"evidence_shadow_{safe_id}.json", package
    )


def save_live_evidence_package(upload_dir: str, session_id: str, package: dict) -> str:
    """Atomically replace one finalized live evidence snapshot."""

    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(session_id))[:160]
    return _save_named_package(upload_dir, f"evidence_live_{safe_id}.json", package)
