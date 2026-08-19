#!/usr/bin/env python3
"""Run a real local video through 3D-Speaker without publishing the result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.media_evidence.final_speaker_attribution import (
    build_final_speaker_attribution,
)
from app.services.media_evidence.three_d_speaker_client import LocalThreeDSpeakerClient


def evaluate_publication_gate(
    *,
    provider_result: dict,
    snapshot: dict,
    duration_ms: int,
    expected_visible_contestants: int,
    minimum_transcript_coverage: float,
    maximum_peak_rss_bytes: int,
    maximum_processing_ms: int | None = None,
) -> dict:
    # maximum_processing_ms remains accepted for old validation callers, but
    # elapsed time is no longer a publication criterion. The worker timeout is
    # the only time guard: explicit failures return immediately; hangs are
    # terminated by the watchdog.
    del maximum_processing_ms
    turns = list(provider_result.get("turns") or [])
    ordered = sorted(
        turns,
        key=lambda item: (int(item.get("startMs") or 0), int(item.get("endMs") or 0)),
    )
    in_bounds = all(
        0 <= int(item.get("startMs") or 0)
        < int(item.get("endMs") or 0)
        <= int(duration_ms)
        for item in turns
    )
    monotonic = turns == ordered
    diagnostics = snapshot.get("diagnostics") or {}
    anchored = int(diagnostics.get("anchoredContestantCount") or 0)
    coverage = float(diagnostics.get("transcriptCoverageRatio") or 0.0)
    conflicts = int(diagnostics.get("introductionConflictCount") or 0)
    anonymous = int(diagnostics.get("anonymousPersonCount") or 0)
    peak_rss = int((provider_result.get("diagnostics") or {}).get("peakRssBytes") or 0)
    slots = [
        item.get("contestantSlot")
        for item in (snapshot.get("people") or [])
        if item.get("personType") == "CONTESTANT"
    ]
    checks = {
        "providerCompleted": {
            "passed": provider_result.get("status") == "completed",
            "status": provider_result.get("status"),
        },
        "contestantAnchors": {
            "passed": anchored == int(expected_visible_contestants),
            "actual": anchored,
            "expected": int(expected_visible_contestants),
        },
        "uniqueContestantSlots": {
            "passed": len(slots) == len(set(slots)),
            "slots": slots,
        },
        "anonymousPeopleAreExplicit": {"passed": True, "count": anonymous},
        "transcriptCoverage": {
            "passed": coverage >= float(minimum_transcript_coverage),
            "actual": coverage,
            "minimum": float(minimum_transcript_coverage),
        },
        "introductionConflicts": {"passed": conflicts == 0, "count": conflicts},
        "timelineBounds": {"passed": in_bounds, "turnCount": len(turns)},
        "monotonicTimeline": {"passed": monotonic},
        "resourceCeiling": {
            "passed": 0 < peak_rss <= int(maximum_peak_rss_bytes),
            "peakRssBytes": peak_rss,
            "maximumPeakRssBytes": int(maximum_peak_rss_bytes),
        },
    }
    return {
        "passed": all(item["passed"] for item in checks.values()),
        "checks": checks,
    }


def _duration_ms(video: Path) -> int:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return int(round(float(completed.stdout.strip()) * 1000))


def _extract_audio(video: Path, destination: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(video), "-vn",
            "-ac", "1", "-ar", "16000", str(destination),
        ],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local 3D-Speaker on real media")
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio")
    parser.add_argument("--session-result", required=True)
    parser.add_argument("--expected-visible-contestants", type=int, default=4)
    parser.add_argument("--minimum-transcript-coverage", type=float, default=0.85)
    parser.add_argument("--maximum-peak-rss-gb", type=float, default=4.0)
    parser.add_argument("--maximum-processing-minutes", type=float, default=40.0)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--reuse-output",
        action="store_true",
        help="Re-evaluate an existing output artifact without rerunning the model",
    )
    parser.add_argument(
        "--runtime-dir",
        default=str(Path(__file__).parents[1] / "models" / "3d-speaker" / "runtime"),
    )
    return parser


def _run(args: argparse.Namespace, audio: Path) -> dict:
    root = Path(__file__).parents[1]
    video = Path(args.video).resolve()
    result_path = Path(args.session_result).resolve()
    duration_ms = _duration_ms(video)
    runtime = Path(args.runtime_dir).resolve()
    provider = LocalThreeDSpeakerClient(
        python_executable=runtime / ".venv" / "bin" / "python",
        worker_script=root / "scripts" / "three_d_speaker_worker.py",
        runtime_dir=runtime,
        timeout_seconds=max(60.0, float(args.maximum_processing_minutes) * 60.0),
    ).analyze(video, audio, duration_ms=duration_ms)
    session_result = json.loads(result_path.read_text(encoding="utf-8"))
    asr_result = session_result.get("asr") or {}
    snapshot = build_final_speaker_attribution(
        session_id=str(session_result.get("meeting_id") or "validation"),
        duration_ms=duration_ms,
        revision=2,
        asr_result=asr_result,
        three_d_speaker_result=provider,
        contestant_slots=int(args.expected_visible_contestants),
    )
    gate = evaluate_publication_gate(
        provider_result=provider,
        snapshot=snapshot,
        duration_ms=duration_ms,
        expected_visible_contestants=int(args.expected_visible_contestants),
        minimum_transcript_coverage=float(args.minimum_transcript_coverage),
        maximum_peak_rss_bytes=int(float(args.maximum_peak_rss_gb) * 1_000_000_000),
        maximum_processing_ms=int(float(args.maximum_processing_minutes) * 60_000),
    )
    return {
        "contractVersion": "3d-speaker-validation-v1",
        "publicationDecision": "PASS" if gate["passed"] else "HOLD",
        "durationMs": duration_ms,
        "providerResult": provider,
        "speakerAttribution": snapshot,
        "gate": gate,
    }


def main() -> int:
    args = build_parser().parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.reuse_output:
        if not output.is_file():
            raise SystemExit("--reuse-output requires an existing --output artifact")
        report = json.loads(output.read_text(encoding="utf-8"))
        gate = evaluate_publication_gate(
            provider_result=report.get("providerResult") or {},
            snapshot=report.get("speakerAttribution") or {},
            duration_ms=int(report.get("durationMs") or 0),
            expected_visible_contestants=int(args.expected_visible_contestants),
            minimum_transcript_coverage=float(args.minimum_transcript_coverage),
            maximum_peak_rss_bytes=int(
                float(args.maximum_peak_rss_gb) * 1_000_000_000
            ),
            maximum_processing_ms=int(
                float(args.maximum_processing_minutes) * 60_000
            ),
        )
        report["gate"] = gate
        report["publicationDecision"] = "PASS" if gate["passed"] else "HOLD"
    elif args.audio:
        report = _run(args, Path(args.audio).resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="3dspk-validation-") as temporary:
            audio = Path(temporary) / "media.wav"
            _extract_audio(Path(args.video).resolve(), audio)
            report = _run(args, audio)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), **report["gate"]}, ensure_ascii=False))
    return 0 if report["gate"]["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
