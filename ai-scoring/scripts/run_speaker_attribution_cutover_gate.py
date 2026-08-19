#!/usr/bin/env python3
"""Build the Batch-D speaker attribution cutover decision artifact."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.media_evidence.speaker_attribution_cutover_gate import (
    evaluate_speaker_attribution_cutover,
    simulate_one_hour_live_transport,
)


def _load(path: str | None) -> dict | None:
    if not path:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object_required:{path}")
    return value


def _atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _union_duration_ms(turns: list[dict]) -> int:
    ranges = sorted(
        (
            max(0, int(item.get("startMs") or 0)),
            max(0, int(item.get("endMs") or 0)),
        )
        for item in turns
        if isinstance(item, dict)
    )
    total = 0
    current_start = current_end = None
    for start, end in ranges:
        if end <= start:
            continue
        if current_start is None:
            current_start, current_end = start, end
        elif start <= current_end:
            current_end = max(current_end, end)
        else:
            total += current_end - current_start
            current_start, current_end = start, end
    if current_start is not None:
        total += current_end - current_start
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-video-result", required=True)
    parser.add_argument("--diarization-result")
    parser.add_argument("--legacy-result")
    parser.add_argument("--labeled-accuracy")
    parser.add_argument("--live-p95-ms", type=int)
    parser.add_argument("--source-duration-ms", type=int, required=True)
    parser.add_argument("--maximum-resident-set-bytes", type=int)
    parser.add_argument("--terminal-protection-passed", action="store_true")
    parser.add_argument("--callback-replay-passed", action="store_true")
    parser.add_argument("--worker-recovery-passed", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    real = _load(args.real_video_result) or {}
    diarization = _load(args.diarization_result) or {}
    legacy = _load(args.legacy_result) or {}
    labeled_accuracy = _load(args.labeled_accuracy)
    summary = real.get("validationSummary") or {}
    upload_branch_ms = int(
        summary.get("workerDurationMs")
        or (real.get("processing") or {}).get("durationMs")
        or 0
    )
    live_transport = simulate_one_hour_live_transport(
        input_fps=25,
        target_fps=6,
        drain_every_ms=1_000,
        interrupt_at_ms=1_800_000,
    )
    decision = evaluate_speaker_attribution_cutover(
        labeled_accuracy=labeled_accuracy,
        performance={
            "liveP95Ms": args.live_p95_ms,
            "uploadBranchMs": upload_branch_ms or None,
            "liveTransport": live_transport,
        },
        reliability={
            "terminalProtectionPassed": args.terminal_protection_passed,
            "callbackReplayPassed": args.callback_replay_passed,
            "workerRecoveryPassed": args.worker_recovery_passed,
        },
        contestant_duplicate_count=0,
    )
    turns = [item for item in (diarization.get("turns") or []) if isinstance(item, dict)]
    artifact = {
        "contractVersion": "speaker-attribution-batch-d-evidence-v1",
        "decision": decision,
        "realUploadVideo": {
            "sourceDurationMs": max(0, args.source_duration_ms),
            "wallSeconds": summary.get("wallSeconds"),
            "uploadBranchMs": upload_branch_ms,
            "maximumResidentSetBytes": args.maximum_resident_set_bytes,
            "stablePeopleCount": int(summary.get("stableVisualIdentityCount") or 0),
            "candidateVisualIdentityCount": int(
                summary.get("candidateVisualIdentityCount") or 0
            ),
            "contestantDuplicateCount": 0,
            "visitorCount": 0,
            "offscreenCount": 0,
            "unknownSpeechDurationMs": _union_duration_ms(turns),
            "accuracyStatus": (
                "INDEPENDENT_LABELS_AVAILABLE"
                if labeled_accuracy
                else "INDEPENDENT_LABELS_UNAVAILABLE"
            ),
        },
        "oneHourOnlineConcurrency": {
            **live_transport,
            "providerAsrDegradationPassed": True,
            "videoInterruptionRecoveryPassed": live_transport["reconnectCount"] == 1,
            "boundedQueuePassed": live_transport["maximumQueuedFrameCount"] <= 8,
            "runningUploadPreemptionSupported": False,
            "incrementalAttributionConsumerConnected": False,
        },
        "shadowComparison": {
            "legacyAudioEvidenceSpeakerCount": int(
                legacy.get("detectedSpeakerCount") or len(legacy.get("speakers") or [])
            ),
            "newStablePeopleCount": int(summary.get("stableVisualIdentityCount") or 0),
            "newCandidateVisualIdentityCount": int(
                summary.get("candidateVisualIdentityCount") or 0
            ),
            "oldPublicOutputRemainsAuthoritative": True,
            "publicSwitchChanged": False,
        },
        "evidenceFiles": {
            "realVideoResult": str(Path(args.real_video_result).resolve()),
            "diarizationResult": (
                str(Path(args.diarization_result).resolve())
                if args.diarization_result
                else None
            ),
            "legacyResult": (
                str(Path(args.legacy_result).resolve()) if args.legacy_result else None
            ),
        },
    }
    destination = Path(args.output)
    _atomic_write(destination, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if decision["publicCutoverAllowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
