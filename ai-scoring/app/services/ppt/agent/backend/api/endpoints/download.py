"""Download endpoint for completed presentations."""

import json
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from backend.api.auth import ensure_job_owner
from backend.api.schemas import ReexportResponse
from backend.config import settings
from backend.generator.project_manager import get_notes, get_svg_files
from backend.generator.svg_to_pptx import create_pptx
from backend.orchestrator.roadshow_quality import evaluate_roadshow_export_gate
from backend.session.manager import session_manager

router = APIRouter()


@router.get("/download/{job_id}")
async def download_presentation(job_id: str, request: Request) -> FileResponse:
    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)

    if job.output_path:
        path = _resolve_workspace_file(job.output_path)
        if path is not None and path.exists():
            if job.status != "complete":
                session_manager.update_job(
                    job_id,
                    status="complete",
                    message="Presentation ready",
                    output_path=str(path),
                    error=None,
                )
            return _pptx_response(path)

    if job.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Presentation is not ready yet.",
        )

    # A roadshow job can finish preview generation while the stricter formal
    # export gate blocks the PPTX. In that case users still need a tangible
    # draft deck instead of a JSON error page.
    reexported = await _export_presentation(job_id, job, enforce_roadshow_gate=False, draft=True)
    return _pptx_response(Path(reexported.output_path))


@router.get("/download-file")
async def download_presentation_file(output_path: str, request: Request) -> FileResponse:
    path = _resolve_workspace_file(output_path)
    if path is None or not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output file not found.")
    matched_job = None
    for job in session_manager.list_jobs():
        if job.output_path and _resolve_workspace_file(job.output_path) == path:
            matched_job = job
            break
    ensure_job_owner(matched_job, request)

    return _pptx_response(path)


@router.post("/download/{job_id}/reexport", response_model=ReexportResponse)
async def reexport_presentation(job_id: str, request: Request) -> ReexportResponse:
    job = session_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    ensure_job_owner(job, request)
    return await _export_presentation(job_id, job, enforce_roadshow_gate=True, draft=False)


async def _export_presentation(
    job_id: str,
    job,
    *,
    enforce_roadshow_gate: bool,
    draft: bool,
) -> ReexportResponse:
    if not job.project_dir:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job has no project workspace.",
        )

    project_dir = _resolve_workspace_file(job.project_dir)
    if project_dir is None or not project_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    svg_files = get_svg_files(project_dir, "final") or get_svg_files(project_dir, "output")
    if not svg_files:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No slide SVGs found for re-export.",
        )

    if enforce_roadshow_gate and (
        (job.style or "").lower() == "roadshow" or project_dir.name.startswith("roadshow_")
    ):
        manuscript = _read_workspace_text(project_dir / "manuscript.md")
        design_spec = _read_workspace_text(project_dir / "design_spec.md")
        gate = evaluate_roadshow_export_gate(
            project_dir,
            manuscript=manuscript,
            design_spec=design_spec,
            svg_files=svg_files,
        )
        if gate.get("blocking_findings"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Roadshow formal export blocked.",
                    "blocking_findings": gate["blocking_findings"],
                    "report_path": str(project_dir / "roadshow_export_gate_report.json"),
                },
            )

    notes = get_notes(project_dir, svg_files)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    canvas_format = job.canvas_format or "ppt169"
    output_name = f"presentation_draft_{timestamp}.pptx" if draft else f"presentation_{timestamp}.pptx"
    output_path = project_dir / "exports" / output_name

    from backend.runtime import aoffload

    # PPTX assembly is python-pptx + zipfile + optional SVG raster fallback —
    # all synchronous and
    # CPU-heavy (5–20s for a long deck). Offload so re-export from the result
    # page doesn't freeze the API while it runs.
    image2_warnings: list[str] = []
    if job.render_engine == "image2" and settings.image2_export_mode == "image":
        from backend.generator.image2_editable_export import create_image2_image_pptx

        _, image2_warnings = await aoffload(
            create_image2_image_pptx,
            project_dir,
            output_path,
            aspect_ratio="16:9",
        )
    elif job.render_engine == "image2" and settings.image2_export_mode == "editable":
        from backend.generator.image2_editable_export import create_image2_editable_pptx

        _, image2_warnings = await aoffload(
            create_image2_editable_pptx,
            svg_files,
            project_dir,
            output_path,
            canvas_format=canvas_format,
            notes=notes,
        )
    else:
        await aoffload(
            create_pptx,
            svg_files,
            output_path,
            canvas_format=canvas_format,
            notes=notes,
        )
    fallback_slides = _read_fallback_slides(output_path)
    warnings = list(image2_warnings)
    if fallback_slides and not any("raster fallback" in warning for warning in warnings):
        warnings.append(f"Slides {', '.join(map(str, fallback_slides))} used raster fallback export.")

    session_manager.update_job(
        job_id,
        status="complete",
        message="Draft PowerPoint exported" if draft else "Presentation re-exported",
        output_path=str(output_path),
        error=None,
    )

    return ReexportResponse(
        job_id=job_id,
        status="complete",
        output_path=str(output_path),
        fallback_slides=fallback_slides,
        warnings=warnings,
    )


def _pptx_response(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=path.name,
    )


def _read_fallback_slides(output_path: Path) -> list[int]:
    report_path = output_path.with_suffix(".conversion_report.json")
    if not report_path.exists():
        return []
    try:
        rows = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(rows, list):
        return []
    slides: list[int] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("mode") != "fallback_image":
            continue
        slide = row.get("slide")
        if isinstance(slide, int):
            slides.append(slide)
    return slides


def _read_workspace_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _resolve_workspace_file(raw_path: str) -> Path | None:
    try:
        resolved = Path(raw_path).resolve()
        resolved.relative_to(settings.workspaces_dir.resolve())
    except (OSError, ValueError):
        return None
    return resolved
