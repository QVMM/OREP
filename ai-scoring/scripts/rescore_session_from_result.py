#!/usr/bin/env python3
"""Re-run only LLM scoring from a saved pipeline result JSON.

Usage (inside ai-scoring container):
  PYTHONPATH=/app python scripts/rescore_session_from_result.py \\
    --result /app/uploads/results/result_33.json \\
    --callback-url http://backend:8080/api/ai-score/callback
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services import llm_scoring_service
from app.services.competition_calibration_service import apply_calibration_to_result
from app.services.pipeline_payloads import build_backend_callback_payload
from app.services.pipeline_service import (
    _attach_evidence_extraction,
    _build_ai_score_payload,
    _ensure_llm_result_complete,
)
from app.services.speaker_evidence_service import build_speaker_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rescore")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rescore(result: dict, *, provider: str = "deepseek") -> dict:
    asr = result.get("asr") or {}
    speech = result.get("speech_quality") or {}
    project = result.get("project_info") or {}
    video = result.get("video_analysis") or {}
    fusion = result.get("fusion") or {}

    fusion_context = None
    if fusion:
        fusion_context = {
            "trends": fusion.get("trends") or {},
            "contradictions": fusion.get("contradictions") or [],
            "visual_aggregates": (video.get("aggregates") or {}) if video else {},
            "audio_windows": fusion.get("audio_windows") or [],
            "timeline": fusion.get("timeline") or [],
            "screen_content_summary": fusion.get("screen_content_summary") or {},
        }

    duration_note = result.get("duration_note")
    ppt_recognition = bool(result.get("ppt_recognition"))

    logger.info(
        "rescoring meeting=%s segments=%s provider=%s",
        result.get("meeting_id"),
        len(asr.get("segments") or []),
        provider,
    )
    llm_result = llm_scoring_service.score_roadshow(
        asr,
        speech,
        project,
        provider=provider,
        fusion_context=fusion_context,
        duration_note=duration_note,
        ppt_recognition=ppt_recognition,
    )
    result["ai_score"] = _build_ai_score_payload(llm_result)
    _ensure_llm_result_complete(llm_result)
    result = apply_calibration_to_result(result)
    _attach_evidence_extraction(result, asr, project, fusion_context, provider)

    # Keep speaker evidence consistent if missing.
    if not result.get("speaker_evidence"):
        result["speaker_evidence"] = build_speaker_evidence(asr)

    result["status"] = "completed"
    result["error"] = None
    result.pop("error_message", None)
    logger.info(
        "rescore complete overall=%s model=%s",
        (result.get("ai_score") or {}).get("overall_score"),
        (result.get("ai_score") or {}).get("model"),
    )
    return result


async def _callback(url: str, meeting_id: str, result: dict) -> None:
    import httpx

    payload = build_backend_callback_payload(meeting_id, result)
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as http:
        response = await http.post(url, json=payload)
        logger.info("callback status=%s body=%s", response.status_code, response.text[:300])
        response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--callback-url", default="")
    parser.add_argument("--write", action="store_true", help="Overwrite result file")
    args = parser.parse_args()

    path = Path(args.result)
    result = _load(path)
    meeting_id = str(result.get("meeting_id") or path.stem.replace("result_", ""))
    try:
        result = rescore(result, provider=args.provider)
    except Exception as exc:
        logger.exception("rescore failed: %s", exc)
        result["status"] = "failed"
        result["error"] = str(exc)
        if args.write:
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2

    if args.write:
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("wrote %s", path)

    if args.callback_url:
        asyncio.run(_callback(args.callback_url, meeting_id, result))

    print(
        json.dumps(
            {
                "meeting_id": meeting_id,
                "status": result.get("status"),
                "overall_score": (result.get("ai_score") or {}).get("overall_score"),
                "model": (result.get("ai_score") or {}).get("model"),
                "error": result.get("error"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
