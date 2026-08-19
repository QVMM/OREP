"""Generation API endpoint.

The HTTP handler does the cheap synchronous work (validate session, derive
the pipeline request, register a Job row) and then enqueues the actual
generation through the scheduler. Submitting through the scheduler is what
makes ``POST /generate`` return in milliseconds even when an earlier job is
still in its parsing/research stage on a busy server.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from backend.api.auth import ensure_job_owner, ensure_session_owner
from backend.api.schemas import GenerateRequest, GenerateResponse
from backend.runtime.scheduler import QueueFull, SchedulerDraining, get_scheduler
from backend.session.manager import session_manager
from backend.session.progress import payloads_from_progress_event
from backend.store.db import db_enabled, ping as db_ping
from backend.worker.request_codec import generation_request_to_dict

logger = logging.getLogger(__name__)

router = APIRouter()


def _queue_mode_enabled() -> bool:
    """When true, API only enqueues; Worker claims from MySQL."""
    mode = (os.getenv("PPT_EXECUTION_MODE") or "inline").strip().lower()
    if mode in {"queue", "db", "worker"}:
        return True
    return False

_PIPELINE_STATUS_STAGES = {
    "parsing",
    "research",
    "content_cards",
    "waiting_confirmation",
    "strategy",
    "generation",
    "postprocess",
    "export",
}


def _server_model_credentials(provider: str, base_url: str | None) -> tuple[str, str | None]:
    """Resolve server-owned model credentials so browser clients never see keys."""
    normalized = provider.lower()
    if normalized == "mimo":
        return os.getenv("MIMO_API_KEY", ""), base_url or os.getenv("MIMO_BASE_URL")
    if normalized == "qwen":
        return os.getenv("DASHSCOPE_API_KEY", ""), base_url or os.getenv("DASHSCOPE_BASE_URL")
    if normalized == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY", ""), base_url or os.getenv("DEEPSEEK_BASE_URL")
    if normalized == "openai":
        return os.getenv("OPENAI_API_KEY", ""), base_url or os.getenv("OPENAI_BASE_URL")
    if normalized == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY", ""), base_url or os.getenv("ANTHROPIC_BASE_URL")
    if normalized == "gemini":
        return os.getenv("GEMINI_API_KEY", ""), base_url or os.getenv("GEMINI_BASE_URL")
    return "", base_url


async def _iterate_pipeline(job_id: str, request: Any) -> None:
    from backend.orchestrator.pipeline import run_pipeline
    from backend.usage.tracker import set_usage_context

    set_usage_context(job_id=job_id)

    async for event in run_pipeline(request):
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        for payload, updates in payloads_from_progress_event(job_id, current_job, event):
            session_manager.record_event(job_id, payload, **updates)


def _cleanup_partial_workspace(job_id: str) -> None:
    """Preserve the workspace of a cancelled/failed job.

    Failed runs often still contain useful parse output, manuscript drafts,
    or partially generated SVGs. Keeping the project directory lets the result
    page preview whatever exists and allows a later re-export when SVGs were
    already produced.
    """
    job = session_manager.get_job(job_id)
    if job is not None and job.project_dir:
        session_manager.update_job(job_id, project_dir=job.project_dir)


async def _run_generation_job(job_id: str, request: Any) -> None:
    from backend.orchestrator.pipeline import ProgressEvent

    job = session_manager.get_job(job_id)
    if job is None:
        return

    timeout = getattr(request, "timeout_seconds", None)
    cleanup_needed = False
    try:
        if timeout and timeout > 0:
            await asyncio.wait_for(_iterate_pipeline(job_id, request), timeout=timeout)
        else:
            await _iterate_pipeline(job_id, request)
    except asyncio.TimeoutError:
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        msg = f"Job exceeded timeout of {timeout}s"
        stage = current_job.status if current_job.status in _PIPELINE_STATUS_STAGES else "error"
        error_event = ProgressEvent(stage, "error", msg, current_job.progress)
        for payload, updates in payloads_from_progress_event(job_id, current_job, error_event):
            session_manager.record_event(job_id, payload, **updates)
        cleanup_needed = True
    except asyncio.CancelledError:
        session_manager.mark_job_cancelled(job_id)
        cleanup_needed = True
        raise
    except Exception as exc:
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        stage = current_job.status if current_job.status in _PIPELINE_STATUS_STAGES else "error"
        error_event = ProgressEvent(stage, "error", str(exc), current_job.progress)
        for payload, updates in payloads_from_progress_event(job_id, current_job, error_event):
            session_manager.record_event(job_id, payload, **updates)
        cleanup_needed = True
    finally:
        if cleanup_needed:
            _cleanup_partial_workspace(job_id)


@router.post("/generate", response_model=GenerateResponse)
async def generate_presentation(payload: GenerateRequest, request: Request) -> GenerateResponse:
    from backend.orchestrator.pipeline import GenerationRequest

    session = session_manager.get_session(payload.session_id)
    ensure_session_owner(session, request)

    job = session_manager.create_job(payload.session_id)
    render_engine_was_provided = "render_engine" in getattr(payload.options, "model_fields_set", set())
    render_engine = (
        payload.options.render_engine if render_engine_was_provided else "image2"
    ) if payload.options.deck_type == "roadshow" else "svg"
    session_manager.update_job(
        job.id,
        status="pending",
        message="Queued for generation",
        provider=payload.model_settings.provider,
        model_name=payload.model_settings.model,
        base_url=payload.model_settings.base_url,
        canvas_format=payload.options.canvas_format,
        style=payload.options.style,
        render_engine=render_engine,
        language=payload.options.language,
        detail_level=payload.options.detail_level,
        instruction=payload.instruction,
    )

    server_api_key, server_base_url = _server_model_credentials(
        payload.model_settings.provider,
        payload.model_settings.base_url,
    )
    effective_api_key = payload.model_settings.api_key or server_api_key
    if not effective_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API key for provider '{payload.model_settings.provider}'.",
        )

    pipeline_request = GenerationRequest(
        file_path=session.file_path,
        source_type=session.source_type,  # type: ignore[arg-type]
        deck_type=payload.options.deck_type,
        provider=payload.model_settings.provider,
        model=payload.model_settings.model,
        api_key=effective_api_key,
        base_url=server_base_url,
        canvas_format=payload.options.canvas_format,
        style=payload.options.style,
        render_engine=render_engine,
        num_pages=payload.options.num_pages,
        instruction=payload.instruction,
        language=payload.options.language,
        detail_level=payload.options.detail_level,
        timeout_seconds=payload.options.timeout_seconds,
        max_critic_attempts=payload.options.max_critic_attempts,
        style_overrides=(
            payload.options.style_overrides.model_dump(exclude_none=True)
            if payload.options.style_overrides
            else None
        ),
        enable_deep_research=payload.options.enable_deep_research,
        icon_library=payload.options.icon_library,
        deepseek_settings=(
            payload.model_settings.deepseek_settings.model_dump()
            if payload.model_settings.provider == "deepseek"
            and payload.model_settings.deepseek_settings
            else None
        ),
        openai_settings=(
            payload.model_settings.openai_settings.model_dump()
            if payload.model_settings.provider == "openai"
            and payload.model_settings.openai_settings
            else None
        ),
        enable_visual_critic=payload.options.enable_visual_critic,
        visual_qa_max_attempts=payload.options.visual_qa_max_attempts,
        enable_icon=payload.options.enable_icon,
        enable_icon_rag=payload.options.enable_icon_rag,
        gemini_api_key=payload.options.gemini_api_key,
        template_id=payload.options.template_id,
        research_config=payload.options.research_config,
        job_id=job.id,
        mode=payload.options.mode,
    )

    # Always persist request for recovery / worker claim (no-op if DB off).
    request_payload = generation_request_to_dict(pipeline_request)
    use_queue = _queue_mode_enabled() and db_enabled() and db_ping()
    if use_queue:
        session_manager.save_job_request_payload(
            job.id,
            request_payload,
            deck_type=payload.options.deck_type,
            mode=payload.options.mode,
            status="queued",
            message="已入队，等待 Worker 执行",
        )
        logger.info("PPT job %s enqueued for DB worker", job.id)
        return GenerateResponse(job_id=job.id, status="queued")

    # Inline mode (default): run in API process; still dual-write DB when available.
    session_manager.save_job_request_payload(
        job.id,
        request_payload,
        deck_type=payload.options.deck_type,
        mode=payload.options.mode,
        status="pending",
        message="Queued for generation",
    )

    scheduler = get_scheduler()

    async def _runner() -> None:
        await _run_generation_job(job.id, pipeline_request)

    try:
        await scheduler.submit(job.id, _runner)
    except QueueFull as exc:
        session_manager.update_job(
            job.id,
            status="error",
            error="Server is busy: too many jobs queued.",
            message="Server is busy: too many jobs queued.",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except SchedulerDraining as exc:
        session_manager.update_job(
            job.id,
            status="error",
            error="Server is shutting down.",
            message="Server is shutting down.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return GenerateResponse(job_id=job.id, status="queued")


@router.post("/generate/{job_id}/resume", response_model=GenerateResponse)
async def resume_generation(job_id: str, request: Request) -> GenerateResponse:
    """Resume an interrupted generation job from its existing workspace."""
    from backend.orchestrator.pipeline import GenerationRequest

    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    if not job.project_dir or not Path(job.project_dir).exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has no resumable workspace.",
        )
    if session_manager.is_job_running(job_id):
        return GenerateResponse(job_id=job_id, status="running")

    session = session_manager.get_session(job.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    provider = job.provider or "mimo"
    model = job.model_name or os.getenv("DEFAULT_LLM_MODEL") or "mimo-v2.5-pro"
    server_api_key, server_base_url = _server_model_credentials(provider, job.base_url)
    if not server_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API key for provider '{provider}'.",
        )

    deck_type = "roadshow" if "roadshow" in Path(job.project_dir).name else "paper"
    render_engine = job.render_engine if deck_type == "roadshow" else "svg"
    pipeline_request = GenerationRequest(
        file_path=session.file_path,
        source_type=session.source_type,  # type: ignore[arg-type]
        deck_type=deck_type,  # type: ignore[arg-type]
        provider=provider,
        model=model,
        api_key=server_api_key,
        base_url=server_base_url,
        canvas_format=job.canvas_format or "ppt169",
        style=job.style or ("roadshow" if deck_type == "roadshow" else "academic"),
        render_engine=render_engine or "svg",
        num_pages=job.total_slides or None,
        instruction=job.instruction or "",
        language=job.language or "zh",
        detail_level=job.detail_level or "normal",
        max_critic_attempts=2,
        enable_deep_research=False,
        enable_visual_critic=False,
        visual_qa_max_attempts=0,
        enable_icon=True,
        enable_icon_rag=True,
        template_id=None,
        research_config=None,
        job_id=job.id,
        resume_project_dir=job.project_dir,
        mode="full",
    )

    session_manager.update_job(
        job.id,
        status="pending",
        message="Queued for resume from cached slides",
        render_engine=render_engine or "svg",
        error=None,
        output_path=None,
    )

    scheduler = get_scheduler()

    async def _runner() -> None:
        await _run_generation_job(job.id, pipeline_request)

    try:
        await scheduler.submit(job.id, _runner)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SchedulerDraining as exc:
        session_manager.update_job(
            job.id,
            status="error",
            error="Server is shutting down.",
            message="Server is shutting down.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return GenerateResponse(job_id=job.id, status="queued")
