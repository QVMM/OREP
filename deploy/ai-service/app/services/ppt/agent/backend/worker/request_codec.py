"""Serialize / deserialize GenerationRequest for the DB job queue."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generation_request_to_dict(request: Any) -> dict[str, Any]:
    research = getattr(request, "research_config", None)
    research_payload = None
    if research is not None:
        if hasattr(research, "model_dump"):
            research_payload = research.model_dump()
        elif hasattr(research, "__dict__"):
            research_payload = dict(research.__dict__)

    return {
        "file_path": str(request.file_path),
        "source_type": request.source_type,
        "provider": request.provider,
        "model": request.model,
        "api_key": request.api_key,
        "deck_type": request.deck_type,
        "base_url": request.base_url,
        "canvas_format": request.canvas_format,
        "style": request.style,
        "num_pages": request.num_pages,
        "instruction": request.instruction,
        "language": request.language,
        "detail_level": request.detail_level,
        "timeout_seconds": request.timeout_seconds,
        "max_critic_attempts": request.max_critic_attempts,
        "style_overrides": request.style_overrides,
        "enable_deep_research": request.enable_deep_research,
        "icon_library": request.icon_library,
        "deepseek_settings": request.deepseek_settings,
        "openai_settings": request.openai_settings,
        "enable_visual_critic": request.enable_visual_critic,
        "enable_icon": request.enable_icon,
        "enable_icon_rag": request.enable_icon_rag,
        "gemini_api_key": request.gemini_api_key,
        "visual_qa_max_attempts": request.visual_qa_max_attempts,
        "template_id": request.template_id,
        "research_config": research_payload,
        "job_id": request.job_id,
        "resume_project_dir": request.resume_project_dir,
        "mode": request.mode,
        "render_engine": request.render_engine,
        "confirmed_cards_path": request.confirmed_cards_path,
    }


def generation_request_from_dict(data: dict[str, Any]) -> Any:
    from backend.api.schemas import ResearchConfig
    from backend.orchestrator.pipeline import GenerationRequest

    research_cfg = None
    raw_research = data.get("research_config")
    if isinstance(raw_research, dict) and raw_research:
        try:
            research_cfg = ResearchConfig(**raw_research)
        except Exception:
            research_cfg = None

    return GenerationRequest(
        file_path=Path(data["file_path"]),
        source_type=data.get("source_type") or "pdf",
        provider=data.get("provider") or "mimo",
        model=data.get("model") or "",
        api_key=data.get("api_key") or "",
        deck_type=data.get("deck_type") or "paper",
        base_url=data.get("base_url"),
        canvas_format=data.get("canvas_format") or "ppt169",
        style=data.get("style") or "academic",
        num_pages=data.get("num_pages"),
        instruction=data.get("instruction") or "",
        language=data.get("language") or "zh",
        detail_level=data.get("detail_level") or "normal",
        timeout_seconds=data.get("timeout_seconds"),
        max_critic_attempts=int(data.get("max_critic_attempts") or 3),
        style_overrides=data.get("style_overrides"),
        enable_deep_research=bool(data.get("enable_deep_research")),
        icon_library=data.get("icon_library") or "chunk",
        deepseek_settings=data.get("deepseek_settings"),
        openai_settings=data.get("openai_settings"),
        enable_visual_critic=bool(data.get("enable_visual_critic")),
        enable_icon=bool(data.get("enable_icon")),
        enable_icon_rag=bool(data.get("enable_icon_rag")),
        gemini_api_key=data.get("gemini_api_key"),
        visual_qa_max_attempts=int(data.get("visual_qa_max_attempts") or 1),
        template_id=data.get("template_id"),
        research_config=research_cfg,
        job_id=data.get("job_id"),
        resume_project_dir=data.get("resume_project_dir"),
        mode=data.get("mode") or "full",
        render_engine=data.get("render_engine") or "svg",
        confirmed_cards_path=data.get("confirmed_cards_path"),
    )
