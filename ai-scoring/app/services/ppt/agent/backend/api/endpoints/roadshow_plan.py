"""Roadshow planning artifact endpoints."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.api.auth import ensure_job_owner
from backend.orchestrator.roadshow_cards import load_cards_payload, save_cards_payload
from backend.runtime import apath_exists, aread_text
from backend.runtime.scheduler import SchedulerDraining, get_scheduler
from backend.session.manager import session_manager

router = APIRouter()


class CardsUpdateRequest(BaseModel):
    cards: list[dict[str, Any]] = Field(default_factory=list)


class ConfirmRenderRequest(BaseModel):
    cards: list[dict[str, Any]] | None = None
    render_engine: Literal["svg", "image2"] | None = None


@router.get("/roadshow/plan/{job_id}")
async def get_roadshow_plan(job_id: str, request: Request) -> dict[str, Any]:
    job = session_manager.get_job(job_id)
    if job is None or not job.project_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    project_dir = Path(job.project_dir)
    if not project_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project workspace not found.")

    return {
        "job_id": job_id,
        "status": job.status,
        "project_dir": str(project_dir),
        "material_diagnosis": await _read_json(project_dir / "material_diagnosis.json"),
        "storyline_plan": await _read_json(project_dir / "storyline_plan.json"),
        "page_content_cards": load_cards_payload(project_dir),
    }


@router.patch("/roadshow/plan/{job_id}/cards")
async def update_roadshow_cards(job_id: str, request_payload: CardsUpdateRequest, request: Request) -> dict[str, Any]:
    project_dir = _plan_project_dir(job_id, request)
    cards_payload = load_cards_payload(project_dir)
    cards_payload["cards"] = request_payload.cards
    saved = save_cards_payload(project_dir, cards_payload, confirmed=False)
    return {"job_id": job_id, "page_content_cards": saved}


@router.post("/roadshow/plan/{job_id}/confirm-render")
async def confirm_roadshow_cards_and_render(job_id: str, request_payload: ConfirmRenderRequest, request: Request) -> dict[str, Any]:
    from backend.api.endpoints.generate import _run_generation_job, _server_model_credentials
    from backend.orchestrator.pipeline import GenerationRequest

    job = session_manager.get_job(job_id)
    if job is None or not job.project_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    scheduler = get_scheduler()
    render_statuses = {"pending", "strategy", "generation", "postprocess", "export"}
    if job.status in render_statuses:
        project_dir = Path(job.project_dir)
        payload = load_cards_payload(project_dir)
        cards = payload.get("cards") or []
        return {
            "job_id": job_id,
            "status": job.status,
            "cards": len(cards),
            "already_running": True,
        }
    if scheduler.is_active(job_id):
        if job.status != "waiting_confirmation":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is already running.")
        scheduler.cancel(job_id)
        for _ in range(40):
            await asyncio.sleep(0.05)
            if not scheduler.is_active(job_id):
                break
        if scheduler.is_active(job_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="上一阶段内容卡片任务仍在收尾，请稍后再确认。",
            )

    project_dir = Path(job.project_dir)
    cards_payload = load_cards_payload(project_dir)
    if request_payload.cards is not None:
        cards_payload["cards"] = request_payload.cards
    confirmed = save_cards_payload(project_dir, cards_payload, confirmed=True)
    cards = confirmed.get("cards") or []
    if not cards:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No PageContentCards to render.")

    session = session_manager.get_session(job.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    provider = job.provider or "mimo"
    model = job.model_name or os.getenv("DEFAULT_LLM_MODEL") or "mimo-v2.5-pro"
    render_engine = request_payload.render_engine or job.render_engine or "image2"
    server_api_key, server_base_url = _server_model_credentials(provider, job.base_url)
    if not server_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API key for provider '{provider}'.",
        )

    pipeline_request = GenerationRequest(
        file_path=session.file_path,
        source_type=session.source_type,  # type: ignore[arg-type]
        deck_type="roadshow",
        provider=provider,
        model=model,
        api_key=server_api_key,
        base_url=server_base_url,
        canvas_format=job.canvas_format or "ppt169",
        style=job.style or "roadshow",
        render_engine=render_engine,
        num_pages=len(cards),
        instruction=job.instruction or "",
        language=job.language or "zh",
        detail_level=job.detail_level or "normal",
        max_critic_attempts=3,
        enable_deep_research=False,
        enable_visual_critic=render_engine != "image2",
        visual_qa_max_attempts=1,
        # image2 produces a full-slide composition and does not consume the
        # SVG executor's icon-decoration output.
        enable_icon=render_engine != "image2",
        enable_icon_rag=render_engine != "image2",
        template_id=None,
        research_config=None,
        job_id=job.id,
        resume_project_dir=job.project_dir,
        mode="render_from_cards",
        confirmed_cards_path=str(project_dir / "page_content_cards.confirmed.json"),
    )

    session_manager.update_job(
        job.id,
        status="pending",
        message="已确认内容卡片，开始页面渲染",
        render_engine=render_engine,
        error=None,
        output_path=None,
        slides_completed=0,
        total_slides=len(cards),
    )

    # Prefer DB queue when enabled so render runs on Worker (same as generate).
    import os as _os

    from backend.store.db import db_enabled, ping as db_ping
    from backend.worker.request_codec import generation_request_to_dict

    queue_mode = (
        (_os.getenv("PPT_EXECUTION_MODE") or "inline").strip().lower() in {"queue", "db", "worker"}
        and db_enabled()
        and db_ping()
    )
    if queue_mode:
        session_manager.save_job_request_payload(
            job.id,
            generation_request_to_dict(pipeline_request),
            deck_type="roadshow",
            mode="render_from_cards",
            status="queued",
            message="已确认内容卡片，排队渲染中",
        )
        return {"job_id": job.id, "status": "queued", "cards": len(cards)}

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
            message="服务正在关闭，请稍后重试",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"job_id": job.id, "status": "queued", "cards": len(cards)}


def _plan_project_dir(job_id: str, request: Request) -> Path:
    job = session_manager.get_job(job_id)
    if job is None or not job.project_dir:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    project_dir = Path(job.project_dir)
    if not project_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project workspace not found.")
    return project_dir


async def _read_json(path: Path) -> dict[str, Any]:
    if not await apath_exists(path):
        return {}
    try:
        import json

        return json.loads(await aread_text(path, encoding="utf-8"))
    except Exception:
        return {}
