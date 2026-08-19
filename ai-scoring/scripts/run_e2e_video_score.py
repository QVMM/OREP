#!/usr/bin/env python3
"""End-to-end scoring run against a local roadshow video."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.config import settings
from app.services.pipeline_service import run_scoring_pipeline
from app.services.session_pipeline_service import _build_final_result


def main() -> int:
    video = Path(sys.argv[1] if len(sys.argv) > 1 else "").expanduser()
    if not video.is_file():
        print(f"VIDEO_NOT_FOUND: {video}")
        return 2

    meeting_id = sys.argv[2] if len(sys.argv) > 2 else f"e2e_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    track = sys.argv[3] if len(sys.argv) > 3 else "人工智能赛道"
    out_dir = Path(settings.UPLOAD_DIR) / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"e2e_summary_{meeting_id}.json"

    project_info = {
        "project_name": f"E2E评分流验证-{meeting_id}",
        "track": track,
        "team_size": 4,
        "has_screen_share": True,
        "audio_source_count": 2,
        "expected_contestant_count": 4,
    }

    print(
        json.dumps(
            {
                "event": "start",
                "meeting_id": meeting_id,
                "video": str(video),
                "track": track,
                "upload_dir": settings.UPLOAD_DIR,
                "skip_free_core": settings.LLM_SKIP_FREE_CORE_WHEN_RULE_READY,
                "ledger_report": settings.LLM_LEDGER_GROUNDED_REPORT_ENABLED,
                "started_at": datetime.now().isoformat(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    started = time.time()
    try:
        result = asyncio.run(
            run_scoring_pipeline(
                str(video),
                meeting_id,
                project_info,
                callback_url=None,
                provider="deepseek",
                compare_mode=False,
                ppt_recognition=False,
                start_jury_review=False,
            )
        )
        elapsed = round(time.time() - started, 1)
        final_result = _build_final_result(result)
        ai_score = result.get("ai_score") or {}
        extraction = result.get("evidence_extraction") or {}
        quality = extraction.get("extractionQuality") or {}
        summary = {
            "event": "completed",
            "meeting_id": meeting_id,
            "elapsed_seconds": elapsed,
            "pipeline_status": result.get("status"),
            "has_video": result.get("has_video"),
            "asr_duration": (result.get("asr") or {}).get("duration"),
            "asr_segment_count": len((result.get("asr") or {}).get("segments") or []),
            "diarizationStatus": (result.get("asr") or {}).get("diarizationStatus"),
            "speakerAttributionStatus": (result.get("asr") or {}).get("speakerAttributionStatus"),
            "score_authority_ai": ai_score.get("score_authority"),
            "narrative_source": ai_score.get("narrative_source"),
            "overall_score_ai": ai_score.get("overall_score"),
            "raw_overall_score": ai_score.get("raw_overall_score"),
            "final_overallScore": final_result.get("overallScore"),
            "final_scoreAuthority": final_result.get("scoreAuthority"),
            "reviewReason": final_result.get("reviewReason"),
            "contractVersion": final_result.get("contractVersion"),
            "todoPortfolioStatus": final_result.get("todoPortfolioStatus"),
            "lossLedgerCount": len(final_result.get("lossLedger") or []),
            "actionPlanCount": len(json.loads(final_result.get("actionPlanJson") or "[]")),
            "coverage": json.loads(final_result.get("coverageSummaryJson") or "{}"),
            "scoringFingerprint": final_result.get("scoringFingerprint"),
            "ruleFingerprint": final_result.get("ruleFingerprint"),
            "evidenceSnapshotHash": final_result.get("evidenceSnapshotHash"),
            "scoreInstanceId": final_result.get("scoreInstanceId"),
            "extraction_status": extraction.get("status"),
            "publicationEligible": quality.get("publicationEligible"),
            "transcriptCoverage": quality.get("transcriptCoverage"),
            "generation_meta": ai_score.get("generation_meta"),
            "highlights_preview": (ai_score.get("highlights") or [])[:3],
            "critical_preview": (ai_score.get("critical_issues") or [])[:3],
            "score_overview": ai_score.get("score_overview"),
            "result_path": str(out_dir / f"result_{meeting_id}.json"),
            "summary_path": str(summary_path),
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 0 if result.get("status") not in {"failed", None} else 1
    except Exception as exc:
        elapsed = round(time.time() - started, 1)
        failure = {
            "event": "failed",
            "meeting_id": meeting_id,
            "elapsed_seconds": elapsed,
            "error": str(exc),
            "traceback": traceback.format_exc()[-4000:],
        }
        summary_path.write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(failure, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
