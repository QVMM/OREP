#!/usr/bin/env python3
"""Run private real-video LR-ASD registration validation and persist evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pipeline_service import _build_local_active_speaker_client


def summarize_registration(result: dict, *, wall_seconds: float) -> dict:
    diagnostics = result.get("registrationDiagnostics") or {}
    identities = [
        item for item in (result.get("visualIdentities") or []) if isinstance(item, dict)
    ]
    return {
        "status": str(result.get("status") or "unknown"),
        "wallSeconds": round(float(wall_seconds), 3),
        "workerDurationMs": int((result.get("processing") or {}).get("durationMs") or 0),
        "rawTrackletCount": int(
            diagnostics.get("sourceTrackCount", len(result.get("faceTracks") or []))
        ),
        "eligibleTrackletCount": int(diagnostics.get("eligibleTrackCount") or 0),
        "stableVisualIdentityCount": sum(
            item.get("registrationState") == "STABLE" for item in identities
        ),
        "candidateVisualIdentityCount": sum(
            item.get("registrationState") == "CANDIDATE" for item in identities
        ),
        "unresolvedTrackletCount": int(diagnostics.get("unresolvedTrackCount") or 0),
        "activeIntervalCount": len(result.get("activeIntervals") or []),
        "acceptedVisualLinkCount": int(diagnostics.get("acceptedLinkCount") or 0),
        "rejectedCoVisibleLinkCount": int(
            diagnostics.get("rejectedCoVisibleLinkCount") or 0
        ),
    }


def atomic_write_json(destination: str | Path, value: dict) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    started = time.monotonic()
    result = _build_local_active_speaker_client().analyze(args.video, args.audio)
    summary = summarize_registration(
        result, wall_seconds=time.monotonic() - started
    )
    output = dict(result)
    output["validationSummary"] = summary
    atomic_write_json(args.output, output)
    sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
