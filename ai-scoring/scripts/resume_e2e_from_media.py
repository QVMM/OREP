#!/usr/bin/env python3
"""Resume scoring from a completed media-evidence result (skip ASR/video)."""

from __future__ import annotations

import json
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
from app.services.pipeline_service import (
    _apply_rule_ledger_narrative,
    _build_ai_score_payload,
    _enrich_ledger_grounded_report,
    _score_with_rule_first,
    apply_calibration_to_result,
)
from app.services.session_pipeline_service import _build_final_result


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: resume_e2e_from_media.py <result_json> [meeting_id]")
        return 2
    src = Path(sys.argv[1]).expanduser()
    data = json.loads(src.read_text(encoding="utf-8"))
    meeting_id = sys.argv[2] if len(sys.argv) > 2 else f"{src.stem}_resume_{datetime.now().strftime('%H%M%S')}"

    asr = data.get("asr") or {}
    speech = data.get("speech_quality") or {}
    fusion = data.get("fusion") or {}
    project_info = (data.get("project_info") or {}).copy()
    project_info.setdefault("track", "人工智能赛道")
    project_info.setdefault("project_name", f"Resume-{meeting_id}")
    project_info.setdefault("team_size", 4)

    fusion_context = None
    if fusion:
        fusion_context = {
            "trends": fusion.get("trends") or {},
            "contradictions": fusion.get("contradictions") or [],
            "visual_aggregates": (data.get("video_analysis") or {}).get("aggregates") or {},
            "audio_windows": fusion.get("audio_windows") or [],
            "timeline": fusion.get("timeline") or [],
            "screen_content_summary": fusion.get("screen_content_summary") or {},
        }

    result = {
        "meeting_id": meeting_id,
        "status": "processing",
        "has_video": bool(data.get("has_video")),
        "project_info": project_info,
        "asr": asr,
        "speech_quality": speech,
        "video_analysis": data.get("video_analysis") or {},
        "fusion": fusion,
        "started_at": datetime.now().isoformat(),
        "resumed_from": str(src),
    }

    print(
        json.dumps(
            {
                "event": "resume_start",
                "meeting_id": meeting_id,
                "source": str(src),
                "asr_segments": len(asr.get("segments") or []),
                "track": project_info.get("track"),
                "skip_free_core": settings.LLM_SKIP_FREE_CORE_WHEN_RULE_READY,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    started = time.time()
    try:
        result = _score_with_rule_first(
            result=result,
            asr_result=asr,
            speech_quality=speech,
            project_info=project_info,
            fusion_context=fusion_context,
            provider="deepseek",
            meeting_id=meeting_id,
            duration_note=None,
            ppt_recognition=False,
            compare_mode=False,
        )
        result = apply_calibration_to_result(result)
        result["status"] = "completed"
        result["completed_at"] = datetime.now().isoformat()
        result["elapsed_seconds"] = round(time.time() - started, 1)

        out_dir = Path(settings.UPLOAD_DIR) / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        result_path = out_dir / f"result_{meeting_id}.json"
        # Persist without huge binary fields if any
        result_path.write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")

        final_result = _build_final_result(result)
        ai = result.get("ai_score") or {}
        ext = result.get("evidence_extraction") or {}
        quality = ext.get("extractionQuality") or {}
        summary = {
            "event": "resume_completed",
            "meeting_id": meeting_id,
            "elapsed_seconds": result["elapsed_seconds"],
            "pipeline_status": result.get("status"),
            "score_authority_ai": ai.get("score_authority"),
            "narrative_source": ai.get("narrative_source"),
            "overall_score_ai": ai.get("overall_score"),
            "raw_overall_score": ai.get("raw_overall_score"),
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
            "extraction_status": ext.get("status"),
            "publicationEligible": quality.get("publicationEligible"),
            "transcriptCoverage": quality.get("transcriptCoverage"),
            "generation_meta": ai.get("generation_meta"),
            "highlights_preview": (ai.get("highlights") or [])[:5],
            "critical_preview": (ai.get("critical_issues") or [])[:5],
            "score_overview": ai.get("score_overview"),
            "result_path": str(result_path),
        }
        summary_path = out_dir / f"e2e_summary_{meeting_id}.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        failure = {
            "event": "resume_failed",
            "meeting_id": meeting_id,
            "elapsed_seconds": round(time.time() - started, 1),
            "error": str(exc),
            "traceback": traceback.format_exc()[-4000:],
        }
        print(json.dumps(failure, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
