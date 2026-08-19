"""Refine endpoint — iterate on an existing generation with user feedback."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from backend.api.auth import ensure_job_owner
from backend.api.schemas import RefineRequest, RefineResponse
from backend.runtime.scheduler import QueueFull, SchedulerDraining, get_scheduler
from backend.session.manager import session_manager
from backend.session.progress import payloads_from_progress_event

logger = logging.getLogger(__name__)

router = APIRouter()

_PIPELINE_STATUS_STAGES = {
    "parsing",
    "research",
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


async def _iterate_refine_pipeline(job_id: str, request: Any) -> None:
    from backend.orchestrator.pipeline import run_refine_pipeline
    from backend.usage.tracker import set_usage_context

    set_usage_context(job_id=job_id)

    async for event in run_refine_pipeline(request):
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        for payload, updates in payloads_from_progress_event(job_id, current_job, event):
            session_manager.record_event(job_id, payload, **updates)


def _cleanup_refine_workspace(job_id: str) -> None:
    """Preserve a failed/cancelled refine workspace for inspection.

    Refine jobs run in isolated clones. Keeping the clone makes partial SVGs,
    archives, and diagnostics available from the result page after failures.
    """
    job = session_manager.get_job(job_id)
    if job is not None and job.project_dir:
        session_manager.update_job(job_id, project_dir=job.project_dir)


async def _run_refine_job(job_id: str, request: Any) -> None:
    from backend.orchestrator.pipeline import ProgressEvent

    job = session_manager.get_job(job_id)
    if job is None:
        return

    timeout = getattr(request, "timeout_seconds", None)
    cleanup_needed = False
    try:
        if timeout and timeout > 0:
            await asyncio.wait_for(_iterate_refine_pipeline(job_id, request), timeout=timeout)
        else:
            await _iterate_refine_pipeline(job_id, request)
    except asyncio.TimeoutError:
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        msg = f"Refine job exceeded timeout of {timeout}s"
        stage = current_job.status if current_job.status in _PIPELINE_STATUS_STAGES else "error"
        error_event = ProgressEvent(stage, "error", msg, current_job.progress)
        for payload, updates in payloads_from_progress_event(job_id, current_job, error_event):
            session_manager.record_event(job_id, payload, **updates)
        cleanup_needed = True
    except asyncio.CancelledError:
        session_manager.mark_job_cancelled(job_id, "Refine job cancelled")
        cleanup_needed = True
        raise
    except Exception as exc:
        current_job = session_manager.get_job(job_id)
        if current_job is None:
            return
        stage = current_job.status if current_job.status in _PIPELINE_STATUS_STAGES else "error"
        error_event = ProgressEvent(stage, "error", str(exc), current_job.progress)
        for payload, updates in payloads_from_progress_event(
            job_id, current_job, error_event
        ):
            session_manager.record_event(job_id, payload, **updates)
        cleanup_needed = True
    finally:
        if cleanup_needed:
            _cleanup_refine_workspace(job_id)


@router.post("/refine", response_model=RefineResponse)
async def refine_presentation(payload: RefineRequest, request: Request) -> RefineResponse:
    """Start a refine iteration on an existing completed job.

    The refine pipeline reuses the project directory of the parent job —
    it skips PDF/LaTeX parsing, the research agent, and the strategist,
    and re-runs only SVG generation (with updated feedback), finalization,
    and PPTX export.
    """
    parent_job = session_manager.get_job(payload.job_id)
    if parent_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{payload.job_id}' not found.",
        )
    ensure_job_owner(parent_job, request)
    if not parent_job.project_dir:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent job has no project directory — cannot refine.",
        )
    if parent_job.status not in ("complete", "error", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parent job status is '{parent_job.status}'; refine requires a finished job.",
        )

    job = session_manager.create_refine_job(
        parent_job_id=payload.job_id,
        feedback=payload.feedback,
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refine job.",
        )

    from pathlib import Path as _Path

    from backend.generator.project_manager import clone_project_for_refine

    try:
        refine_project_dir = clone_project_for_refine(
            _Path(parent_job.project_dir), job.id
        )
    except Exception as exc:
        session_manager.update_job(
            job.id,
            status="error",
            message="Failed to prepare refine workspace",
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare refine workspace: {exc}",
        ) from exc

    options = payload.options
    parent_is_roadshow = (
        parent_job.style == "roadshow"
        or parent_job.render_engine == "image2"
        or "roadshow" in _Path(parent_job.project_dir).name
    )
    render_engine_was_provided = "render_engine" in getattr(options, "model_fields_set", set())
    requested_render_engine = (
        options.render_engine
        if render_engine_was_provided
        else (parent_job.render_engine or "svg")
    )
    render_engine = requested_render_engine if parent_is_roadshow else "svg"
    session_manager.update_job(
        job.id,
        status="pending",
        message="Queued for refinement",
        project_dir=str(refine_project_dir),
        provider=payload.model_settings.provider,
        model_name=payload.model_settings.model,
        base_url=payload.model_settings.base_url,
        canvas_format=options.canvas_format or parent_job.canvas_format,
        style=options.style or parent_job.style,
        render_engine=render_engine,
        language=options.language or parent_job.language,
        detail_level=options.detail_level or parent_job.detail_level,
        instruction=parent_job.instruction,
    )

    # Build a lightweight request object for the refine pipeline
    from backend.orchestrator.pipeline import RefineRequest as PipelineRefineRequest

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

    pipeline_request = PipelineRefineRequest(
        project_dir=str(refine_project_dir),
        feedback=payload.feedback,
        feedback_history=job.feedback_history,
        job_id=job.id,
        parent_job_id=payload.job_id,
        provider=payload.model_settings.provider,
        model=payload.model_settings.model,
        api_key=effective_api_key,
        base_url=server_base_url,
        canvas_format=options.canvas_format or parent_job.canvas_format or "ppt169",
        style=options.style or parent_job.style or "academic",
        render_engine=render_engine,
        language=options.language or parent_job.language or "zh",
        detail_level=options.detail_level or parent_job.detail_level or "normal",
        timeout_seconds=options.timeout_seconds,
        max_critic_attempts=options.max_critic_attempts,
        target_pages=payload.target_pages,
        allow_structure_changes=payload.allow_structure_changes,
        style_overrides=(
            options.style_overrides.model_dump(exclude_none=True)
            if options.style_overrides
            else None
        ),
        icon_library=options.icon_library,
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
        enable_visual_critic=options.enable_visual_critic,
        visual_qa_max_attempts=options.visual_qa_max_attempts,
        enable_icon=options.enable_icon,
        enable_icon_rag=options.enable_icon_rag,
        gemini_api_key=options.gemini_api_key,
        template_id=options.template_id,
    )

    scheduler = get_scheduler()

    async def _runner() -> None:
        await _run_refine_job(job.id, pipeline_request)

    try:
        # Refines run *after* a successful generate of the same session, so
        # they get a slight priority boost (lower numeric value) — users
        # iterating on a result feel snappier than a fresh paper queued at
        # the same moment.
        await scheduler.submit(job.id, _runner, priority=5)
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

    return RefineResponse(job_id=job.id, status="queued")
