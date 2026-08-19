"""Helpers for projecting pipeline events into API and WebSocket state."""

from __future__ import annotations

from typing import Any

from .manager import Job

PIPELINE_STAGES = (
    "pending",
    "queued",
    "running",
    "parsing",
    "research",
    "content_cards",
    "waiting_confirmation",
    "script",  # roadshow speaker-notes skill between cards and design
    "strategy",
    "generation",
    "postprocess",
    "export",
    "cancelling",
    "error",
    "cancelled",
)


def _event_stage(stage: str) -> str:
    """Map pipeline stage for UI. Unknown stages stay as-is (not forced to error)."""
    raw = str(stage or "").strip()
    if not raw:
        return "research"
    if raw in PIPELINE_STAGES:
        return raw
    # Legacy aliases
    if raw in {"started", "progress"}:
        return "research"
    return raw


def build_snapshot_event(job_id: str, job: Job) -> dict[str, Any]:
    """Build a progress-shaped snapshot event for new WebSocket subscribers."""
    stage = _event_stage(job.status)
    status = "progress"
    if job.status == "pending":
        status = "started"
        stage = "parsing"
    elif job.status == "queued":
        status = "started"
        stage = "queued"
    elif job.status == "error":
        status = "error"
    elif job.status == "cancelled":
        status = "error"
        stage = "cancelled"
    elif job.status == "cancelling":
        status = "progress"
        stage = "cancelling"
    elif job.status == "complete":
        status = "complete"
        stage = "export"

    return {
        "type": "progress",
        "job_id": job_id,
        "stage": stage,
        "status": status,
        "message": job.message,
        "progress": job.progress,
        "slides_completed": job.slides_completed,
        "total_slides": job.total_slides,
        "data": {
            "output_path": job.output_path,
            "project_dir": job.project_dir,
        },
    }


def payloads_from_progress_event(job_id: str, job: Job, event: Any) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Turn a pipeline event into one or more socket payloads plus job updates."""
    payloads: list[tuple[dict[str, Any], dict[str, Any]]] = []
    stage = _event_stage(event.stage)
    updates: dict[str, Any] = {
        "message": event.message,
        "progress": event.progress,
    }

    if event.data and event.data.get("project_dir"):
        updates["project_dir"] = event.data["project_dir"]

    if event.data and event.data.get("total_slides"):
        updates["total_slides"] = int(event.data["total_slides"])

    if (
        event.stage == "generation"
        and event.status == "progress"
        and event.data
        and event.data.get("svg")
    ):
        page = int(event.data.get("page", 0)) if event.data else 0
        updates["slides_completed"] = max(job.slides_completed, page)

    if event.stage == "export" and event.status == "complete":
        updates["output_path"] = event.data.get("output_path") if event.data else None
        updates["status"] = "complete"
        updates["error"] = None
    elif event.stage == "error" or event.status == "error":
        updates["status"] = "error"
        updates["error"] = event.message
    else:
        # Keep real stage names (including script); clear stale restart errors
        # so UI does not keep showing "异常" while the job is healthy again.
        updates["status"] = event.stage
        updates["error"] = None

    progress_payload = {
        "type": "progress",
        "job_id": job_id,
        "stage": stage,
        "status": event.status,
        "message": event.message,
        "progress": event.progress,
        "slides_completed": updates.get("slides_completed", job.slides_completed),
        "total_slides": updates.get("total_slides", job.total_slides),
        "data": event.data or {},
        "error": None if updates.get("error") is None and event.status != "error" else updates.get("error"),
    }
    payloads.append((progress_payload, updates))

    if (
        event.stage == "generation"
        and event.status == "progress"
        and event.data
        and event.data.get("svg")
    ):
        slide_payload = {
            "type": "slide_ready",
            "job_id": job_id,
            "stage": event.stage,
            "status": event.status,
            "message": event.message,
            "progress": event.progress,
            "slides_completed": updates.get("slides_completed", job.slides_completed),
            "total_slides": updates.get("total_slides", job.total_slides),
            "data": {
                "page": event.data.get("page"),
                "svg": event.data.get("svg"),
            },
        }
        payloads.append((slide_payload, {}))

    if event.stage == "export" and event.status == "complete":
        complete_data: dict[str, Any] = {
            "output_path": updates.get("output_path"),
        }
        if event.data and event.data.get("critic"):
            complete_data["critic"] = event.data["critic"]
        complete_payload = {
            "type": "complete",
            "job_id": job_id,
            "stage": "export",
            "status": "complete",
            "message": event.message,
            "progress": 1.0,
            "slides_completed": updates.get("slides_completed", job.slides_completed),
            "total_slides": updates.get("total_slides", job.total_slides),
            "data": complete_data,
        }
        payloads.append((complete_payload, {}))

    if event.stage == "error" or event.status == "error":
        error_payload = {
            "type": "error",
            "job_id": job_id,
            "stage": stage,
            "status": "error",
            "message": event.message,
            "progress": event.progress,
            "slides_completed": job.slides_completed,
            "total_slides": job.total_slides,
            "data": {"error": event.message, **(event.data or {})},
        }
        payloads.append((error_payload, {}))

    return payloads
