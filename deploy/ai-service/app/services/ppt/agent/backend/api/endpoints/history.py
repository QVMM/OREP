"""History endpoints for generated PPT jobs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.api.auth import can_claim_legacy_jobs, ensure_job_owner, filter_owned_for_owner, owner_from_request
from backend.generator.project_manager import get_svg_files
from backend.session.manager import Job, Session, session_manager

router = APIRouter()


class HistoryFile(BaseModel):
    session_id: str
    name: str
    size: int
    source_type: str
    path: str


class HistoryJobItem(BaseModel):
    job_id: str
    session_id: str
    file: HistoryFile | None = None
    status: str
    progress: float
    message: str = ""
    slides_completed: int = 0
    total_slides: int = 0
    slide_count: int = 0
    output_path: str | None = None
    project_dir: str | None = None
    provider: str | None = None
    model_name: str | None = None
    deck_type: str = "unknown"
    render_engine: str | None = None
    instruction: str | None = None
    parent_job_id: str | None = None
    feedback_rounds: int = 0
    created_at: float = 0
    updated_at: float = 0
    last_event: str = ""


class HistoryListResponse(BaseModel):
    jobs: list[HistoryJobItem] = Field(default_factory=list)


class HistoryDetailResponse(BaseModel):
    job: HistoryJobItem
    events: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/history", response_model=HistoryListResponse)
async def list_history(request: Request, limit: int = 50) -> HistoryListResponse:
    owner = owner_from_request(request)
    all_sessions = session_manager.list_sessions()
    all_jobs = session_manager.list_jobs()
    has_owned_records = any(session.owner_key for session in all_sessions) or any(job.owner_key for job in all_jobs)
    if can_claim_legacy_jobs(owner, has_owned_records=has_owned_records):
        session_manager.claim_legacy_owner(
            owner_key=owner.owner_key,
            owner_user_id=owner.user_id,
            owner_name=owner.username,
            owner_tenant_id=owner.tenant_id,
        )

    # Prefer memory/sidecars, then merge MySQL-backed jobs for this owner.
    try:
        from backend.store.job_store import job_store

        for row in job_store.list_job_rows_for_owner(owner.owner_key, limit=max(1, min(limit, 200))):
            if session_manager.get_job(row["id"]) is None:
                session_manager.get_job(row["id"])  # hydrate from DB via get_job
    except Exception:
        pass

    sessions = {session.id: session for session in session_manager.list_sessions()}
    jobs = [
        _job_to_history_item(job, sessions.get(job.session_id), include_slide_count=False)
        for job in filter_owned_for_owner(session_manager.list_jobs(), owner)
    ]
    jobs.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
    return HistoryListResponse(jobs=jobs[: max(1, min(limit, 200))])


@router.get("/history/{job_id}", response_model=HistoryDetailResponse)
async def get_history_detail(job_id: str, request: Request) -> HistoryDetailResponse:
    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    sessions = {session.id: session for session in session_manager.list_sessions()}
    events = session_manager.get_events_after(job_id, 0)[-160:]
    return HistoryDetailResponse(
        job=_job_to_history_item(job, sessions.get(job.session_id)),
        events=events,
    )


def _job_to_history_item(job: Job, session: Session | None, include_slide_count: bool = True) -> HistoryJobItem:
    events = list(job.events or [])
    created_at = _event_ts(events[0]) if events else _path_time(job.project_dir, job.output_path)
    updated_at = _event_ts(events[-1]) if events else created_at
    last_event = ""
    if events:
        last_event = str(events[-1].get("message") or events[-1].get("status") or events[-1].get("type") or "")

    return HistoryJobItem(
        job_id=job.id,
        session_id=job.session_id,
        file=_session_to_history_file(session),
        status=job.status,
        progress=job.progress,
        message=job.message,
        slides_completed=job.slides_completed,
        total_slides=job.total_slides,
        slide_count=_slide_count(job.project_dir) if include_slide_count else _known_slide_count(job),
        output_path=job.output_path,
        project_dir=job.project_dir,
        provider=job.provider,
        model_name=job.model_name,
        deck_type=_infer_deck_type(job),
        render_engine=job.render_engine,
        instruction=job.instruction,
        parent_job_id=job.parent_job_id,
        feedback_rounds=len(job.feedback_history or []),
        created_at=created_at,
        updated_at=updated_at,
        last_event=last_event,
    )


def _known_slide_count(job: Job) -> int:
    for value in (job.slides_completed, job.total_slides):
        try:
            number = int(value or 0)
        except (TypeError, ValueError):
            number = 0
        if number > 0:
            return number
    return 0


def _session_to_history_file(session: Session | None) -> HistoryFile | None:
    if session is None:
        return None
    return HistoryFile(
        session_id=session.id,
        name=session.file_name,
        size=session.file_size,
        source_type=session.source_type,
        path=str(session.file_path),
    )


def _infer_deck_type(job: Job) -> str:
    style = (job.style or "").lower()
    project_dir = (job.project_dir or "").lower()
    instruction = (job.instruction or "").lower()
    if "roadshow" in style or "roadshow_ppt" in project_dir or "职业院校技能大赛" in instruction:
        return "roadshow"
    if "paper_ppt" in project_dir or style == "academic":
        return "paper"
    return "unknown"


def _slide_count(project_dir: str | None) -> int:
    if not project_dir:
        return 0
    path = Path(project_dir)
    if not path.exists():
        return 0
    final_files = get_svg_files(path, "final")
    output_files = get_svg_files(path, "output")
    return len(final_files or output_files)


def _event_ts(event: dict[str, Any]) -> float:
    try:
        return float(event.get("ts") or 0)
    except (TypeError, ValueError):
        return 0


def _path_time(*raw_paths: str | None) -> float:
    for raw in raw_paths:
        if not raw:
            continue
        path = Path(raw)
        try:
            if path.exists():
                return path.stat().st_mtime
        except OSError:
            continue
    return 0
