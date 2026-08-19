"""Integrated PPT Agent API routes.

This router mounts the full paper-ppt-agent backend under ``/api/ppt`` while
keeping it inside the ai-scoring service process.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services.ppt.agent_runtime import bootstrap_ppt_agent

bootstrap_ppt_agent()

from backend.api.endpoints import (  # noqa: E402
    download,
    font_update,
    generate,
    history,
    image_search,
    materials,
    preview,
    providers,
    refine,
    roadshow_plan,
    session,
    status,
    template_import,
    templates,
    upload,
    usage,
    versions,
)
from backend.api import websocket  # noqa: E402
from backend.config import settings  # noqa: E402

router = APIRouter(prefix="/api/ppt", tags=["PPT Agent"])


@router.get("/health")
async def health() -> dict[str, object]:
    import os

    from backend.store.db import db_enabled, ping as db_ping

    execution_mode = (os.getenv("PPT_EXECUTION_MODE") or "inline").strip().lower()
    db_ok = bool(db_enabled() and db_ping())
    return {
        "status": "ok",
        "service": "Integrated PPT Agent",
        "image2_configured": bool((settings.image2_api_key or "").strip()),
        "image2_export_mode": settings.image2_export_mode,
        "execution_mode": execution_mode,
        "db_enabled": db_enabled(),
        "db_ok": db_ok,
        "queue_mode": execution_mode in {"queue", "db", "worker"} and db_ok,
    }


router.include_router(upload.router, tags=["ppt-upload"])
router.include_router(materials.router, tags=["ppt-materials"])
router.include_router(generate.router, tags=["ppt-generate"])
router.include_router(history.router, tags=["ppt-history"])
router.include_router(refine.router, tags=["ppt-refine"])
router.include_router(roadshow_plan.router, tags=["ppt-roadshow-plan"])
router.include_router(status.router, tags=["ppt-status"])
router.include_router(download.router, tags=["ppt-download"])
router.include_router(font_update.router, tags=["ppt-fonts"])
router.include_router(preview.router, tags=["ppt-preview"])
router.include_router(providers.router, tags=["ppt-providers"])
router.include_router(session.router, tags=["ppt-session"])
router.include_router(templates.router, tags=["ppt-templates"])
router.include_router(template_import.router, tags=["ppt-template-import"])
router.include_router(usage.router, tags=["ppt-usage"])
router.include_router(versions.router, tags=["ppt-versions"])
router.include_router(image_search.router, tags=["ppt-image-search"])
router.include_router(websocket.router, tags=["ppt-ws"])
