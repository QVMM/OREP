"""Run the scoring pipeline in an isolated process.

Uvicorn multi-worker + in-process native libs (sherpa-onnx / dashscope / opencv)
was silently killing workers mid-job ("Child process died"), leaving sessions
stuck at asr_processing ~18% with no failed callback.

This entrypoint is invoked via subprocess so a native crash cannot take down
the HTTP worker that accepted the job.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import traceback
from pathlib import Path

logger = logging.getLogger("pipeline_job_runner")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    parser = argparse.ArgumentParser(description="Isolated OREP scoring pipeline job")
    parser.add_argument("--config", required=True, help="Path to job config JSON")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("invalid_config: %s", exc)
        return 2

    result_path = Path(config["result_path"])
    try:
        from app.services.pipeline_service import run_scoring_pipeline

        result = asyncio.run(
            run_scoring_pipeline(
                audio_file_path=config["audio_file_path"],
                meeting_id=str(config["meeting_id"]),
                project_info=config.get("project_info") or {},
                callback_url=None,
                provider=config.get("provider") or "deepseek",
                compare_mode=bool(config.get("compare_mode") or False),
                ppt_recognition=bool(config.get("ppt_recognition", True)),
                start_jury_review=bool(config.get("start_jury_review") or False),
            )
        )
        if not isinstance(result, dict):
            result = {"status": "failed", "error": "pipeline_result_not_object"}
        result_path.write_text(json.dumps(result, ensure_ascii=False, default=str), encoding="utf-8")
        status = str(result.get("status") or "")
        return 0 if status != "failed" and not result.get("error") else 3
    except Exception as exc:
        logger.error("pipeline_job_failed: %s", exc)
        logger.error(traceback.format_exc())
        payload = {
            "status": "failed",
            "error": f"pipeline_job_exception:{type(exc).__name__}:{exc}",
            "meeting_id": config.get("meeting_id"),
        }
        try:
            result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
