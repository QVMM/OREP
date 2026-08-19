"""Job status endpoint."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.api.auth import ensure_job_owner
from backend.api.schemas import CancelJobResponse, JobStatus
from backend.orchestrator.manuscript import split_manuscript_pages
from backend.session.manager import session_manager

router = APIRouter()


def _infer_disk_progress(job) -> tuple[int, int, float]:
    """Recover slide progress from workspace files when in-memory state is stale."""
    slides_completed = int(job.slides_completed or 0)
    total_slides = int(job.total_slides or 0)
    progress = float(job.progress or 0.0)

    if not job.project_dir:
        return slides_completed, total_slides, progress

    project_dir = Path(job.project_dir)
    if not project_dir.exists():
        return slides_completed, total_slides, progress

    svg_output_dir = project_dir / "svg_output"
    if svg_output_dir.exists():
        disk_slides = len(list(svg_output_dir.glob("*.svg")))
        slides_completed = max(slides_completed, disk_slides)

    manuscript_path = project_dir / "manuscript.md"
    if manuscript_path.exists():
        try:
            total_slides = max(
                total_slides,
                len(split_manuscript_pages(manuscript_path.read_text(encoding="utf-8"))),
            )
        except Exception:
            pass

    if total_slides > 0 and slides_completed > 0:
        inferred_generation_progress = 0.40 + (slides_completed / total_slides) * 0.35
        progress = max(progress, min(inferred_generation_progress, 0.75))

    return slides_completed, total_slides, progress


def _safe_status_text(text: str | None) -> str:
    """Return a user-facing error without provider HTML/noisy SDK payloads."""
    if not text:
        return ""

    lower = text.lower()
    if "server restarted" in lower or "生成服务已重启" in text:
        return (
            "生成服务刚才重启，当前任务已中断。"
            "请点击「重新生成」或「从中断处重试」；已上传资料会话通常仍可用。"
        )
    if "bad gateway" in lower or "openresty" in lower:
        return (
            "上游模型服务临时失败（502 Bad Gateway）。"
            "任务工作区已保留，请稍后重试；若已有生成页面，可点击“从缓存继续”。"
        )
    if "request timed out" in lower or "timeout" in lower:
        return (
            "上游模型服务请求超时。任务工作区已保留，请稍后重试；"
            "若已有生成页面，可点击“从缓存继续”。"
        )
    if "connection error" in lower or "failed to fetch" in lower:
        return "连接暂时失败。任务工作区已保留，请稍后重试。"
    if "session not found" in lower:
        return "上传会话已失效，请重新选择/上传资料后再生成。"
    return text


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str, request: Request) -> JobStatus:
    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    ensure_job_owner(job, request)

    normalized_status = "complete" if job.output_path and Path(job.output_path).exists() else job.status
    slides_completed, total_slides, progress = _infer_disk_progress(job)
    # Keep job counters aligned with disk so resume UI sees real progress.
    if slides_completed != job.slides_completed or total_slides != job.total_slides:
        session_manager.update_job(
            job.id,
            slides_completed=slides_completed,
            total_slides=total_slides,
            progress=progress,
        )
    recovery = session_manager.job_recovery_flags(job)

    return JobStatus(
        status=normalized_status,
        progress=progress,
        message=_safe_status_text(job.message),
        render_engine=job.render_engine if job.render_engine in {"svg", "image2"} else None,
        slides_completed=slides_completed,
        total_slides=total_slides,
        output_path=job.output_path,
        error=None if normalized_status == "complete" else (_safe_status_text(job.error) or None),
        session_id=recovery.get("session_id"),
        session_alive=bool(recovery.get("session_alive")),
        can_resume=bool(recovery.get("can_resume")),
        can_retry=bool(recovery.get("can_retry")),
        project_dir_exists=bool(recovery.get("project_dir_exists")),
    )


@router.post("/status/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(job_id: str, request: Request) -> CancelJobResponse:
    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    ensure_job_owner(job, request)

    if job.status in {"complete", "error", "cancelled"}:
        return CancelJobResponse(job_id=job_id, status=job.status)

    if job.status == "cancelling":
        return CancelJobResponse(job_id=job_id, status="cancelling")

    cancelled = session_manager.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前任务无法取消（可能已结束）。请刷新页面查看最新状态。",
        )

    # Refresh after cancel so response reflects cancelled vs cooperative cancelling.
    job_after = session_manager.get_job(job_id)
    out_status = (job_after.status if job_after else None) or "cancelling"
    if out_status not in {"cancelled", "cancelling"}:
        out_status = "cancelling"
    return CancelJobResponse(job_id=job_id, status=out_status)


@router.delete("/status/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, request: Request) -> Response:
    job = session_manager.get_job(job_id)
    ensure_job_owner(job, request)
    deleted = session_manager.delete_job(job_id, delete_files=True)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
