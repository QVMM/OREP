"""Main paper-to-PPT pipeline orchestrator.

Ties together: parsing → research → strategist → SVG executor → finalize → export.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

from backend.config import settings
from backend.api.schemas import ResearchConfig
from backend.generator.svg_critic import CriticReport
from backend.runtime import aoffload, aread_text, awrite_text
from backend.usage.tracker import reset_usage_context, set_usage_context

from .manuscript import count_manuscript_pages, page_title, split_manuscript_pages
from . import research_agent, roadshow_agent, strategist_agent, svg_executor
from .research_agent import ResearchContext
from .research_enrichment import enrich_context
from .roadshow_quality import (
    evaluate_roadshow_export_gate,
    extract_locked_facts,
    filter_roadshow_figure_inventory,
)
from .roadshow_hard_quality import (
    evaluate_roadshow_export_artifacts,
    strip_svg_images,
    svg_has_image,
)


@dataclass
class ProgressEvent:
    """Progress event emitted during pipeline execution."""

    stage: str
    status: Literal["started", "progress", "complete", "error"]
    message: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    data: dict | None = None


def _configured_secret(*values: str | None) -> str:
    """Return the first real secret, skipping empty values and .env placeholders."""
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if normalized.startswith("${") and normalized.endswith("}"):
            continue
        return normalized
    return ""


def _format_enrichment_message(stats) -> str:
    """One-line summary of enrichment results for the progress channel.

    Translation happens on the frontend via i18nStatus — keep this string
    structural and English-source so the translator can pattern-match.
    """
    bits: list[str] = []
    if stats.arxiv_found or stats.arxiv_error is not None:
        if stats.arxiv_error:
            bits.append(f"arXiv: {stats.arxiv_error}")
        else:
            bits.append(f"arXiv: {stats.arxiv_found}")
    if stats.scholar_found or stats.scholar_error is not None:
        if stats.scholar_error:
            bits.append(f"Semantic Scholar: {stats.scholar_error}")
        else:
            bits.append(f"Semantic Scholar: {stats.scholar_found}")
    if stats.web_found or stats.web_error is not None:
        if stats.web_error:
            bits.append(f"Web: {stats.web_error}")
        else:
            bits.append(f"Web: {stats.web_found}")
    if not bits:
        return "External research returned no results"
    return f"External research — {', '.join(bits)}"


def _querying_enrichment_payload(config: ResearchConfig) -> dict:
    payload: dict = {"phase": "querying", "total_findings": 0, "filtered_findings": 0}
    if config.arxiv_search_enabled:
        payload["arxiv"] = {"found": 0}
    if config.semantic_scholar_enabled:
        payload["semantic_scholar"] = {"found": 0}
    if config.web_search_enabled:
        provider = getattr(config, "web_search_provider", None)
        if not provider:
            provider = "tavily" if config.tavily_api_key else "serpapi" if config.serpapi_key else None
        web: dict = {"found": 0}
        if provider:
            web["provider"] = provider
        payload["web"] = web
    return payload


_ROADSHOW_FIELD_RE = re.compile(
    r"(?ims)^\s*(?:\*\*)?{field}(?:\*\*)?\s*[:：]\s*(.*?)(?=^\s*(?:\*\*)?"
    r"(?:page_core_sentence|visible_content|main_visual|visual_asset_plan|required_assets|asset_status|"
    r"fallback_visual|asset_gap_handling|export_gate|speaker_notes|main_script|sub_script|transition|"
    r"page_role|judge_focus|visual_strategy|layout_hint|story_role|primary_visual|stage_mode|"
    r"display_target|operator_role|operator_action|fallback_plan|acceptance_signal|command_cue)"
    r"(?:\*\*)?\s*[:：]|\Z)"
)
_SCRIPT_META_SENTENCE_RE = re.compile(
    r"(本页|这一页|这页|页面|主视觉|版式|布局|字段|备注|待补充|证明对象|证明任务|"
    r"讲解时|可见内容|副标题|底部任务|项目名称、一句定位语|设计|素材状态)"
)


def _roadshow_field_value(page: str, field: str) -> str:
    pattern = re.compile(_ROADSHOW_FIELD_RE.pattern.format(field=re.escape(field)), re.I | re.M | re.S)
    match = pattern.search(page)
    if not match:
        return ""
    value = match.group(1).strip()
    value = re.sub(r"(?im)^\s*[-*]\s+", "", value)
    value = re.sub(r"```[\s\S]*?```", "", value)
    return value.strip()


def _clean_export_note_text(text: str) -> str:
    text = re.sub(r"(?im)^\s*(?:speaker_notes|speech_script|script|main_script|sub_script|transition)\s*[:：]\s*", "", text)
    text = re.sub(r"\[\[ASSET:[^\]]+\]\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""

    parts = re.split(r"(?<=[。！？!?])\s*", text)
    kept: list[str] = []
    for part in parts:
        sentence = part.strip()
        if not sentence:
            continue
        if _SCRIPT_META_SENTENCE_RE.search(sentence):
            continue
        kept.append(sentence)
    cleaned = "".join(kept).strip()
    return cleaned or text


def _extract_export_speaker_note(page: str) -> str:
    notes = _roadshow_field_value(page, "speaker_notes")
    if not notes:
        return ""
    return _clean_export_note_text(notes)


async def _ensure_notes_files_from_manuscript(
    project_dir: Path,
    manuscript: str | None,
    svg_files: list[Path],
) -> None:
    """Persist generated roadshow speaker notes so PPTX export can embed them."""
    if not manuscript or not svg_files:
        return
    pages = split_manuscript_pages(manuscript)
    if not pages:
        return

    notes_dir = project_dir / "notes"
    await aoffload(notes_dir.mkdir, parents=True, exist_ok=True)
    for svg_path, page in zip(svg_files, pages):
        note = _extract_export_speaker_note(page)
        if not note:
            continue
        title = page_title(page)
        body = f"{title}\n\n{note}" if title and title not in note[:80] else note
        await awrite_text(notes_dir / f"{svg_path.stem}.md", body.strip() + "\n", encoding="utf-8")


async def _ensure_roadshow_cover_svg_has_no_images(svg_files: list[Path]) -> bool:
    if not svg_files:
        return False
    cover_path = svg_files[0]
    try:
        content = await aread_text(cover_path, encoding="utf-8")
    except OSError:
        return False
    if not svg_has_image(content):
        return False
    stripped = strip_svg_images(content)
    await awrite_text(cover_path, stripped, encoding="utf-8")
    return True


def _format_quality_findings(findings: list[dict], *, include_warnings: bool = False) -> str:
    selected = [
        item for item in findings
        if include_warnings or item.get("severity") == "error"
    ]
    bits: list[str] = []
    for item in selected[:6]:
        page = item.get("page")
        page_prefix = f"第 {page} 页：" if page else ""
        message = str(item.get("message") or item.get("rule") or "质量检查未通过")
        bits.append(page_prefix + message)
    return "；".join(bits)


def _looks_like_roadshow_manuscript(manuscript: str | None) -> bool:
    if not manuscript:
        return False
    return bool(re.search(r"(?im)^\s*(?:speaker_notes|page_core_sentence|operator_action|acceptance_signal)\s*[:：]", manuscript))


def _safe_pipeline_error(exc: Exception) -> str:
    """Convert noisy provider errors into user-actionable messages."""
    text = str(exc)
    lower = text.lower()
    if "bad gateway" in lower or "openresty" in lower:
        return (
            "智能生成服务连接不稳定。"
            "任务工作区已保留，系统会继续监听可用结果，并复用已生成的阶段产物。"
        )
    if "request timed out" in lower or "timeout" in lower:
        return (
            "智能生成服务连接波动。任务工作区已保留，"
            "系统正在继续监听并重新建立请求。"
        )
    return text


def _resolve_visual_critic_route():
    """Return a dedicated visual-QA LLM route, preferring Qwen vision.

    The main deck model may be text-first. Visual QA needs image input, so we
    keep this route independent and server-configured instead of asking users
    to fill another key in the UI.
    """
    from backend.llm import create_provider

    provider = (settings.visual_qa_provider or "qwen").strip()
    if not provider:
        return None, None
    if provider == "qwen":
        configured_model = settings.visual_qa_model or settings.ppt_vision_model
        if configured_model and not any(
            marker in configured_model.lower() for marker in ("vl", "omni", "vision")
        ):
            configured_model = None
        model = configured_model or settings.qwen_vision_model or "qwen3-vl-flash"
        api_key = _configured_secret(
            settings.visual_qa_api_key,
            settings.ppt_vision_api_key,
            settings.dashscope_api_key,
        )
        base_url = (
            settings.visual_qa_base_url
            or settings.ppt_vision_base_url
            or settings.dashscope_base_url
        )
    elif provider == "mimo":
        model = settings.visual_qa_model or "mimo-v2-omni"
        api_key = settings.visual_qa_api_key or settings.mimo_api_key or ""
        base_url = settings.visual_qa_base_url or settings.mimo_base_url
    else:
        model = settings.visual_qa_model or settings.default_llm_model
        api_key = settings.visual_qa_api_key or ""
        base_url = settings.visual_qa_base_url
    if not api_key:
        logger.warning("Visual QA route '%s' has no API key; using main model", provider)
        return None, None
    try:
        return create_provider(provider, api_key, base_url=base_url), model
    except Exception as exc:  # noqa: BLE001
        logger.warning("Visual QA route '%s' unavailable: %s", provider, exc)
        return None, None


def _parsed_paper_cache_path(project_dir: Path) -> Path:
    return project_dir / "sources" / "parsed_paper.pkl"


def _save_parsed_paper_cache(project_dir: Path, paper: object) -> None:
    import pickle

    path = _parsed_paper_cache_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(paper, protocol=pickle.HIGHEST_PROTOCOL))


def _load_parsed_paper_cache(project_dir: Path):
    import pickle

    path = _parsed_paper_cache_path(project_dir)
    if not path.exists():
        return None
    try:
        return pickle.loads(path.read_bytes())
    except Exception:
        logger.warning("failed to load parsed paper cache from %s", path, exc_info=True)
        return None


async def _write_enrichment_debug(
    project_dir: Path, ctx: ResearchContext, stats
) -> None:
    debug_dir = project_dir / "debug"
    try:
        await aoffload(debug_dir.mkdir, parents=True, exist_ok=True)
        payload = stats.to_dict()
        payload["queries_used"] = list(ctx.queries_used)
        await awrite_text(
            debug_dir / "research_enrichment_stats.json",
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        block = ctx.enrichment_block_for_pass1()
        if block:
            await awrite_text(
                debug_dir / "research_enrichment_pass1_block.md",
                block,
                encoding="utf-8",
            )
    except OSError:
        pass


async def _read_optional_text(*paths: Path, max_chars: int = 12000) -> str:
    for path in paths:
        try:
            if path.exists():
                text = await aread_text(path, encoding="utf-8")
                if text.strip():
                    return text[:max_chars]
        except (OSError, UnicodeDecodeError):
            continue
    return ""


@dataclass
class GenerationRequest:
    """Request parameters for paper-to-PPT generation."""

    file_path: Path
    source_type: Literal["pdf", "latex"]
    provider: str  # "openai", "anthropic", "gemini"
    model: str
    api_key: str
    deck_type: Literal["paper", "roadshow"] = "paper"
    base_url: str | None = None
    canvas_format: str = "ppt169"
    style: str = "academic"
    num_pages: int | None = None
    instruction: str = ""
    language: str = "zh"
    detail_level: str = "normal"
    timeout_seconds: int | None = None
    max_critic_attempts: int = 3
    style_overrides: dict | None = None  # {palette: [...], font: "...", density: "..."}
    enable_deep_research: bool = False
    icon_library: str = "chunk"  # chunk / tabler-filled / tabler-outline
    deepseek_settings: dict | None = None
    openai_settings: dict | None = None
    enable_visual_critic: bool = False
    enable_icon: bool = False
    enable_icon_rag: bool = False
    gemini_api_key: str | None = None
    visual_qa_max_attempts: int = 1
    template_id: str | None = None  # Template ID from assets/templates/layouts/
    research_config: ResearchConfig | None = None  # Optional external research enrichment
    job_id: str | None = None
    resume_project_dir: str | None = None
    mode: Literal["full", "plan_only", "render_from_cards"] = "full"
    render_engine: Literal["svg", "image2"] = "svg"
    confirmed_cards_path: str | None = None


async def run_pipeline(
    request: GenerationRequest,
) -> AsyncIterator[ProgressEvent]:
    """Execute the full paper-to-PPT pipeline.

    Yields ProgressEvent at each stage transition.
    """
    # Initialize LLM provider
    from backend.generator.project_manager import get_notes, get_svg_files, init_project
    from backend.generator.svg_finalize import finalize_project
    from backend.generator.svg_to_pptx import create_pptx
    from backend.llm import create_provider
    from backend.parser.latex_parser import LaTeXParser
    from backend.parser.pdf_parser import PDFParser

    provider_kwargs = {"base_url": request.base_url}
    if request.deepseek_settings is not None:
        provider_kwargs["deepseek_settings"] = request.deepseek_settings
    if request.openai_settings is not None:
        provider_kwargs["openai_settings"] = request.openai_settings
    llm = create_provider(
        request.provider,
        request.api_key,
        **provider_kwargs,
    )
    visual_llm, visual_model = (
        _resolve_visual_critic_route() if request.enable_visual_critic else (None, None)
    )

    # Create or resume project workspace.  Resume mode keeps page-level SVG
    # artifacts in place so a restarted job can skip already accepted slides.
    resume_dir = Path(request.resume_project_dir).resolve() if request.resume_project_dir else None
    if resume_dir and resume_dir.exists() and resume_dir.is_dir():
        project_dir = resume_dir
    else:
        project_dir = init_project(
            name="roadshow_ppt" if request.deck_type == "roadshow" else "paper_ppt",
            canvas_format=request.canvas_format,
            base_dir=settings.workspaces_dir,
        )

    # Attribute every LLM call inside this run to the caller's job if known.
    job_id = getattr(request, "job_id", None)
    usage_snapshot = set_usage_context(
        job_id=job_id,
        stage="parsing",
        page=None,
        attempt=1,
    )

    current_stage = "parsing"
    current_progress = 0.0

    try:
        # Stage 1: Parse materials (or reuse cache when confirming cards → render)
        current_stage = "parsing"
        current_progress = 0.0
        output_dir = project_dir / "sources"
        paper = None
        parse_info: dict = {}

        # After user confirms content cards we only need the paper object for
        # figures/facts. Re-running PDF parse confuses the UI ("又回到解析资料")
        # and can re-crash fragile parsers — prefer cached parse from plan phase.
        if request.mode == "render_from_cards":
            paper = await aoffload(_load_parsed_paper_cache, project_dir)
            if paper is not None:
                parse_info = {"cache": True, "path": "render_from_cards_cache"}
                current_progress = 0.30

        if paper is None:
            yield ProgressEvent(
                "parsing",
                "started",
                "正在解析资料…" if request.deck_type == "roadshow" else "正在解析文档…",
                data={"project_dir": str(project_dir)},
            )

            if request.source_type == "pdf":
                parser = PDFParser()
            else:
                parser = LaTeXParser()

            paper = await parser.parse(request.file_path, output_dir)

            parse_info = dict(
                getattr(parser, "last_parse_info", None)
                or getattr(type(parser), "last_parse_info", None)
                or {}
            )
            await aoffload(_save_parsed_paper_cache, project_dir, paper)

            title = (paper.title or "").strip() or "资料"
            yield ProgressEvent(
                "parsing",
                "complete",
                f"资料解析完成：{title}",
                0.15,
                data={"parse_info": parse_info} if parse_info else None,
            )
            current_progress = 0.15

        if request.deck_type == "roadshow" and request.mode == "render_from_cards":
            set_usage_context(stage="research", page=None, attempt=1)
            current_stage = "content_cards"
            current_progress = 0.32
            yield ProgressEvent(
                "content_cards",
                "complete",
                "已加载确认后的内容卡片",
                0.32,
                data={"project_dir": str(project_dir)},
            )
            from .roadshow_cards import (
                cards_to_manuscript,
                card_from_dict,
                load_cards_payload,
                normalize_cards,
                write_image2_page_briefs,
                write_image2_page_descriptions,
            )

            cards_payload = load_cards_payload(project_dir, confirmed=True)
            raw_cards = cards_payload.get("cards") or []
            if not raw_cards:
                raise ValueError("未找到已确认的 page_content_cards，无法从卡片进入渲染。")
            cards = normalize_cards([card_from_dict(item, index + 1) for index, item in enumerate(raw_cards)])
            if request.render_engine == "image2":
                write_image2_page_descriptions(project_dir, cards)
                write_image2_page_briefs(project_dir, cards)
            manuscript = cards_to_manuscript(cards)
            yield ProgressEvent(
                "script",
                "started",
                "正在生成国赛完整路演讲稿",
                0.315,
                data={"project_dir": str(project_dir)},
            )
            try:
                from .roadshow_script_skill import enhance_roadshow_script

                debug_dir = project_dir / "debug"
                material_analysis = await _read_optional_text(
                    project_dir / "material_diagnosis.json",
                    debug_dir / "roadshow_pass1_material_diagnosis_response.md",
                )
                outline_plan = await _read_optional_text(
                    debug_dir / "roadshow_pass2_image2_light_outline_response.md",
                    debug_dir / "roadshow_pass5_light_slide_plan_response.md",
                    project_dir / "page_content_cards.confirmed.json",
                )
                run_of_show_plan = await _read_optional_text(
                    debug_dir / "roadshow_pass3_run_of_show_response.md",
                    project_dir / "storyline_plan.json",
                )
                contestant_plan = await _read_optional_text(
                    debug_dir / "roadshow_pass4_contestant_perspective_response.md",
                    project_dir / "page_content_cards.confirmed.json",
                )
                # Hard cap: script skill can hang on long LLM streams; never block render forever.
                script_timeout = float(__import__("os").getenv("PPT_SCRIPT_SKILL_TIMEOUT", "180"))
                script_skill_result = await asyncio.wait_for(
                    enhance_roadshow_script(
                        llm=llm,
                        model=request.model,
                        manuscript=manuscript,
                        project_dir=project_dir,
                        debug_dir=project_dir / "debug",
                        material_analysis=material_analysis,
                        outline_plan=outline_plan,
                        run_of_show_plan=run_of_show_plan,
                        contestant_plan=contestant_plan,
                        target_duration_sec=3600,
                        target_chars=8000,
                        on_progress=None,
                    ),
                    timeout=script_timeout,
                )
                manuscript = script_skill_result.manuscript
                if script_skill_result.quality_report.get("passed"):
                    yield ProgressEvent(
                        "script",
                        "complete",
                        "国赛完整路演讲稿已生成并同步到页面卡片",
                        0.33,
                        data={"project_dir": str(project_dir), "script_ready": True},
                    )
                else:
                    logger.warning(
                        "Roadshow script skill did not pass quality gate for render_from_cards: %s",
                        script_skill_result.quality_report.get("findings"),
                    )
                    yield ProgressEvent(
                        "script",
                        "complete",
                        "国赛完整路演讲稿已生成，部分页面待优化",
                        0.33,
                        data={
                            "project_dir": str(project_dir),
                            "script_ready": True,
                            "quality_passed": False,
                            "quality_report": script_skill_result.quality_report,
                        },
                    )
            except asyncio.TimeoutError:
                logger.warning("Roadshow script skill timed out; continuing to page render")
                yield ProgressEvent(
                    "script",
                    "complete",
                    "讲稿生成超时，先进入页面渲染",
                    0.33,
                    data={"project_dir": str(project_dir), "script_ready": False, "timeout": True},
                )
            except Exception as exc:
                logger.warning("Roadshow script skill failed in render_from_cards; continuing without notes: %s", exc)
                yield ProgressEvent(
                    "script",
                    "complete",
                    "讲稿生成跳过，继续页面渲染",
                    0.33,
                    data={"project_dir": str(project_dir), "script_ready": False, "error": str(exc)},
                )
            await awrite_text(project_dir / "manuscript.md", manuscript, encoding="utf-8")
            locked_facts = extract_locked_facts(manuscript, paper)
            yield ProgressEvent(
                "content_cards",
                "complete",
                f"已确认 {len(cards)} 页内容，进入页面渲染",
                0.33,
                data={
                    "project_dir": str(project_dir),
                    "total_slides": len(cards),
                    "cards_ready": True,
                    "confirmed": True,
                },
            )
            current_progress = 0.33
        else:
            manuscript = None
            locked_facts = None

        # Stage 2: Research agent
        if request.mode != "render_from_cards":
            set_usage_context(stage="research", page=None, attempt=1)
            current_stage = "research"
            current_progress = 0.15
            yield ProgressEvent(
                "research",
                "started",
                (
                        "Competition roadshow analysis: policy, demo, support materials and team plan..."
                    if request.deck_type == "roadshow"
                    else (
                        "Deep reading: analyzing paper content..."
                        if request.enable_deep_research
                        else "Analyzing paper content..."
                    )
                ),
            )

        # Optional Stage 2a: external enrichment runs BEFORE Pass 1 so the
        # related-work context is available where it actually matters
        # (gap analysis, contribution framing). We surface per-source stats
        # via ProgressEvent.data so the frontend can show users that the
        # toggles they enabled actually returned something.
            research_ctx = ResearchContext()
            research_cfg = getattr(request, "research_config", None)
            any_source_enabled = bool(
                research_cfg
                and (
                    research_cfg.arxiv_search_enabled
                    or research_cfg.semantic_scholar_enabled
                    or research_cfg.web_search_enabled
                )
            )
            if any_source_enabled:
                yield ProgressEvent(
                    "research",
                    "progress",
                    "Querying external research sources...",
                    0.10,
                    data={"enrichment": _querying_enrichment_payload(research_cfg)},
                )
                stats = await enrich_context(
                    research_ctx,
                    paper_title=paper.title,
                    paper_abstract=paper.abstract,
                    config=research_cfg,
                )
                await _write_enrichment_debug(project_dir, research_ctx, stats)
                yield ProgressEvent(
                    "research",
                    "progress",
                    _format_enrichment_message(stats),
                    0.12,
                    data={"enrichment": stats.to_dict()},
                )

            yield ProgressEvent(
                "research",
                "progress",
                (
                    "Pass 1/7 — Competition material diagnosis"
                    if request.deck_type == "roadshow"
                    else "Pass 1/4 — Deep reading"
                ),
                0.13,
            )

        # Collect progress events from research_agent via queue for real-time yielding
            _research_progress_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

            def _on_research_progress(message: str, fraction: float) -> None:
                _research_progress_queue.put_nowait(
                    ProgressEvent("research", "progress", message, fraction)
                )

            async def _run_analysis() -> str:
                try:
                    if request.deck_type == "roadshow":
                        result = await roadshow_agent.analyze_materials(
                            paper,
                            llm,
                            request.model,
                            instruction=request.instruction,
                            num_pages=request.num_pages,
                            language=request.language,
                            detail_level=request.detail_level,
                            research_context=research_ctx,
                            debug_dir=project_dir / "debug",
                            on_progress=_on_research_progress,
                            plan_only=request.mode == "plan_only",
                            render_engine=request.render_engine,
                        )
                    else:
                        result = await research_agent.analyze_paper(
                            paper,
                            llm,
                            request.model,
                            instruction=request.instruction,
                            num_pages=request.num_pages,
                            language=request.language,
                            detail_level=request.detail_level,
                            research_context=research_ctx,
                            enable_deep_research=request.enable_deep_research,
                            debug_dir=project_dir / "debug",
                            on_progress=_on_research_progress,
                        )
                    return result
                finally:
                    # ALWAYS unblock the consumer, even if analyze_paper raised.
                    # Without this sentinel the outer ``await queue.get()`` loop
                    # would block forever on auth errors / network failures and
                    # the user would see the pipeline frozen on Pass 1 with no
                    # error in the UI until they manually cancel the job.
                    await _research_progress_queue.put(None)

            analysis_task = asyncio.create_task(_run_analysis())

            # Drain progress events; the producer always posts the sentinel in
            # its `finally`, so this loop terminates whether analysis succeeded
            # or raised.
            while True:
                event = await _research_progress_queue.get()
                if event is None:
                    break
                yield event

            # Now surface the actual result (or re-raise the exception so the
            # outer try/except in run_pipeline emits a proper error event).
            manuscript = analysis_task.result()

            if request.deck_type == "roadshow" and request.mode == "plan_only":
                cards_path = project_dir / "page_content_cards.json"
                cards_count = 0
                if cards_path.exists():
                    try:
                        cards_count = len(json.loads(cards_path.read_text(encoding="utf-8")).get("cards") or [])
                    except Exception:
                        cards_count = 0
                yield ProgressEvent(
                    "content_cards",
                    "complete",
                    f"已生成 {cards_count} 页内容卡片",
                    0.34,
                    data={
                        "project_dir": str(project_dir),
                        "total_slides": cards_count,
                        "cards_ready": True,
                        "plan_only": True,
                    },
                )
                yield ProgressEvent(
                    "waiting_confirmation",
                    "complete",
                    "内容卡片已生成，请确认后进入页面渲染。",
                    0.35,
                    data={
                        "project_dir": str(project_dir),
                        "total_slides": cards_count,
                        "cards_ready": True,
                        "plan_only": True,
                    },
                )
                return

            # Save manuscript and deep analysis artifacts
            await awrite_text(project_dir / "manuscript.md", manuscript, encoding="utf-8")
            locked_facts = extract_locked_facts(manuscript, paper) if request.deck_type == "roadshow" else None
            yield ProgressEvent(
                "research",
                "complete",
                (
                    "Competition roadshow manuscript complete"
                    if request.deck_type == "roadshow"
                    else (
                        "Deep analysis complete (4-pass)"
                        if request.enable_deep_research
                        else "Paper analysis complete"
                    )
                ),
                0.30,
            )
            current_progress = 0.30

        # Stage 3: Strategist agent
        set_usage_context(stage="strategy", page=None, attempt=1)
        current_stage = "strategy"
        current_progress = 0.31
        yield ProgressEvent("strategy", "started", "正在生成设计规范…", 0.31)
        figure_inventory = _build_figure_inventory(paper, project_dir)
        if request.deck_type == "roadshow":
            figure_inventory = filter_roadshow_figure_inventory(figure_inventory)

        # Load template context if specified
        template_context_strat = ""
        template_context_exec = ""
        template_skeletons: dict[str, str] | None = None
        if request.template_id:
            from backend.generator.template_manager import (
                build_template_context_for_executor,
                build_template_context_for_strategist,
                build_template_skeletons,
                load_template,
            )
            tmpl = load_template(request.template_id)
            if tmpl:
                template_context_strat = build_template_context_for_strategist(tmpl)
                template_context_exec = build_template_context_for_executor(tmpl)
                template_skeletons = build_template_skeletons(tmpl)
                yield ProgressEvent(
                    "strategy", "progress",
                    f"Template '{request.template_id}' loaded: {tmpl.info.label}",
                    0.34,
                )
                current_progress = 0.34

        existing_design_spec_path = project_dir / "design_spec.md"
        if request.mode == "render_from_cards" and existing_design_spec_path.exists():
            design_spec = await aread_text(existing_design_spec_path, encoding="utf-8")
            yield ProgressEvent(
                "strategy",
                "complete",
                "Reused existing design specification",
                0.40,
            )
        else:
            design_spec = await strategist_agent.create_design_spec(
                manuscript,
                llm,
                request.model,
                canvas_format=request.canvas_format,
                style=request.style,
                language=request.language,
                detail_level=request.detail_level,
                icon_library=request.icon_library,
                style_overrides=request.style_overrides,
                enable_icon=request.enable_icon,
                enable_icon_rag=request.enable_icon_rag,
                gemini_api_key=request.gemini_api_key,
                figure_inventory=figure_inventory,
                locked_facts=locked_facts,
                debug_dir=project_dir / "debug",
                template_context=template_context_strat or None,
            )

            # Save design spec
            await awrite_text(project_dir / "design_spec.md", design_spec, encoding="utf-8")
            yield ProgressEvent("strategy", "complete", "Design spec created", 0.40)
        current_progress = 0.40

        # Stage 4: SVG executor
        set_usage_context(stage="generation", page=None, attempt=1)
        current_stage = "generation"
        current_progress = 0.40
        total_pages = count_manuscript_pages(manuscript)
        yield ProgressEvent(
            "generation",
            "started",
            "Generating image2 editable slide layers..."
            if request.deck_type == "roadshow" and request.render_engine == "image2"
            else "Generating slide SVGs...",
            0.40,
            data={
                "total_slides": total_pages,
                "render_engine": request.render_engine,
            },
        )
        generated = 0

        critic_events: list[dict] = []
        svg_event_queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()

        async def _on_critic(
            page_num: int,
            attempt: int,
            report: CriticReport,
            repair_prompt: str | None,
            archive_path: str | None,
        ) -> None:
            entry: dict = {
                "page": page_num,
                "attempt": attempt,
                "report": report.to_dict(),
            }
            if repair_prompt is not None:
                entry["repair_prompt"] = repair_prompt
            if archive_path is not None:
                entry["archive_path"] = archive_path
            critic_events.append(entry)

        async def _on_svg_update(page_num: int, svg: str) -> None:
            await svg_event_queue.put(("svg_update", (page_num, svg)))

        async def _on_page_status(
            page_num: int,
            attempt: int,
            phase: str,
            message: str,
            data: dict | None,
        ) -> None:
            progress = 0.40 + (generated / max(1, total_pages)) * 0.35
            await svg_event_queue.put(
                (
                    "event",
                    ProgressEvent(
                        "generation",
                        "progress",
                        message,
                        progress,
                        data={
                            "page": page_num,
                            "attempt": attempt,
                            "phase": phase,
                            "page_status": True,
                            **(data or {}),
                        },
                    ),
                )
            )

        async def _produce_svg_pages() -> None:
            try:
                if request.deck_type == "roadshow" and request.render_engine == "image2":
                    from .image2_renderer import generate_image2_svg_pages

                    async def _on_image2_svg_ready(page_num: int, svg_content: str) -> None:
                        await svg_event_queue.put(("page", (page_num, svg_content)))

                    await generate_image2_svg_pages(
                        manuscript,
                        design_spec,
                        project_dir,
                        canvas_format=request.canvas_format,
                        language=request.language,
                        on_page_status=_on_page_status,
                        on_svg_ready=_on_image2_svg_ready,
                    )
                else:
                    async for page_num, svg_content in svg_executor.generate_svg_pages(
                        design_spec,
                        manuscript,
                        project_dir,
                        llm,
                        request.model,
                        style=request.style,
                        language=request.language,
                        detail_level=request.detail_level,
                        extra_instruction=_build_style_overrides_block(request.style_overrides),
                        on_critic=_on_critic,
                        on_svg_update=_on_svg_update,
                        on_page_status=_on_page_status,
                        figure_inventory=figure_inventory,
                        enable_visual_critic=request.enable_visual_critic,
                        max_critic_attempts=request.max_critic_attempts,
                        visual_qa_max_attempts=request.visual_qa_max_attempts,
                        visual_critic_llm=visual_llm,
                        visual_critic_model=visual_model,
                        template_context=template_context_exec or None,
                        template_skeletons=template_skeletons,
                    ):
                        await svg_event_queue.put(("page", (page_num, svg_content)))
            except Exception as exc:
                await svg_event_queue.put(("error", exc))
            finally:
                await svg_event_queue.put(("done", None))

        svg_producer = asyncio.create_task(_produce_svg_pages())
        try:
            while True:
                item_type, payload = await svg_event_queue.get()
                if item_type == "event":
                    yield payload  # type: ignore[misc]
                    continue
                if item_type == "svg_update":
                    upd_page, upd_svg = payload  # type: ignore[misc]
                    upd_preview = _embed_svg_preview(upd_svg, project_dir, page_num=upd_page)
                    progress = 0.40 + (generated / max(1, total_pages)) * 0.35
                    yield ProgressEvent(
                        "generation",
                        "progress",
                        f"第 {upd_page}/{total_pages} 页修复版本已更新到预览",
                        progress,
                        data={"page": upd_page, "svg": upd_preview},
                    )
                    continue
                if item_type == "page":
                    page_num, svg_content = payload  # type: ignore[misc]
                    generated += 1
                    progress = 0.40 + (generated / total_pages) * 0.35
                    current_progress = progress

                    # Embed images inline for live preview (browser can't load file:// paths)
                    preview_svg = _embed_svg_preview(svg_content, project_dir, page_num=page_num)
                    page_critic = [ev for ev in critic_events if ev["page"] == page_num]
                    yield ProgressEvent(
                        "generation",
                        "progress",
                        f"Generated slide {page_num}/{total_pages}",
                        progress,
                        data={
                            "page": page_num,
                            "svg": preview_svg,
                            "critic": page_critic,
                        },
                    )
                    continue
                if item_type == "error":
                    raise payload  # type: ignore[misc]
                if item_type == "done":
                    break
        finally:
            if not svg_producer.done():
                svg_producer.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await svg_producer

        yield ProgressEvent(
            "generation",
            "complete",
            f"{generated} slides generated",
            0.75,
            data={"critic": critic_events},
        )

        await _save_critic_history(project_dir, critic_events)

        # Stage 5: Post-processing
        set_usage_context(stage="postprocess", page=None, attempt=1)
        current_stage = "postprocess"
        current_progress = 0.75
        yield ProgressEvent("postprocess", "started", "Finalizing SVGs...")
        # finalize_project walks every SVG, runs cairosvg / PIL / regex
        # rewrites: minutes of synchronous CPU work. Push it to the offload
        # pool so heartbeats, the WS event bus, and the scheduler dispatcher
        # all keep ticking.
        stats = await aoffload(finalize_project, project_dir)
        yield ProgressEvent(
            "postprocess",
            "complete",
            f"Processed {stats['total_files']} files",
            0.85,
        )

        # Stage 6: Export PPTX
        set_usage_context(stage="export", page=None, attempt=1)
        current_stage = "export"
        current_progress = 0.85
        yield ProgressEvent("export", "started", "Exporting to PowerPoint...")
        svg_files = get_svg_files(project_dir, source="final")
        cover_stripped = False
        if request.deck_type == "roadshow" and request.render_engine != "image2":
            cover_stripped = await _ensure_roadshow_cover_svg_has_no_images(svg_files)
        await _ensure_notes_files_from_manuscript(project_dir, manuscript, svg_files)
        notes = get_notes(project_dir, svg_files)

        if request.deck_type == "roadshow":
            hard_gate = await evaluate_roadshow_export_artifacts(svg_files, notes)
            hard_gate["cover_image_removed"] = cover_stripped
            await awrite_text(
                project_dir / "roadshow_export_hard_quality.json",
                json.dumps(hard_gate, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            if not hard_gate.get("passed"):
                message = "已生成预览；正式导出需补齐：" + _format_quality_findings(hard_gate.get("findings") or [])
                yield ProgressEvent(
                    "export",
                    "complete",
                    message,
                    1.0,
                    data={
                        "output_path": None,
                        "formal_export_blocked": True,
                        "roadshow_hard_quality": hard_gate,
                    },
                )
                return
            gate = evaluate_roadshow_export_gate(
                project_dir,
                manuscript=manuscript,
                design_spec=design_spec,
                svg_files=svg_files,
                figure_inventory=figure_inventory,
            )
            if gate.get("blocking_findings"):
                findings = gate["blocking_findings"]
                short = "；".join(findings[:3])
                extra = f" 等共 {len(findings)} 项" if len(findings) > 3 else ""
                message = (
                    "预览已生成，可下载工作预览稿继续编辑。"
                    f"正式赛用导出仍需补齐：{short}{extra}。"
                )
                yield ProgressEvent(
                    "export",
                    "complete",
                    message,
                    1.0,
                    data={
                        "output_path": None,
                        "formal_export_blocked": True,
                        "roadshow_export_gate": gate,
                        "draft_download_available": True,
                    },
                )
                return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pptx_path = project_dir / "exports" / f"presentation_{timestamp}.pptx"

        export_warnings: list[str] = []
        if request.deck_type == "roadshow" and request.render_engine == "image2" and settings.image2_export_mode == "image":
            from backend.generator.image2_editable_export import create_image2_image_pptx

            _, export_warnings = await aoffload(
                create_image2_image_pptx,
                project_dir,
                pptx_path,
                aspect_ratio="16:9",
            )
        elif request.deck_type == "roadshow" and request.render_engine == "image2" and settings.image2_export_mode == "editable":
            from backend.generator.image2_editable_export import create_image2_editable_pptx

            _, export_warnings = await aoffload(
                create_image2_editable_pptx,
                svg_files,
                project_dir,
                pptx_path,
                canvas_format=request.canvas_format,
                notes=notes,
            )
        else:
            await aoffload(
                create_pptx,
                svg_files,
                pptx_path,
                canvas_format=request.canvas_format,
                notes=notes,
            )

        yield ProgressEvent(
            "export",
            "complete",
            "PowerPoint generated!",
            1.0,
            data={"output_path": str(pptx_path), "warnings": export_warnings},
        )

    except Exception as e:
        yield ProgressEvent(
            current_stage,
            "error",
            _safe_pipeline_error(e),
            current_progress,
            data={"error_type": type(e).__name__},
        )
        return
    finally:
        reset_usage_context(usage_snapshot)


async def _load_figure_inventory(project_dir: Path) -> list[dict]:
    """Read figure_review.json from a refine workspace.

    The refine pipeline runs without re-parsing the PDF, so we cannot call
    ``_build_figure_inventory(paper, ...)`` here. ``figure_review.json``
    is written once during the original parse and contains everything the
    executor needs to resolve `[[FIG:id]]` tokens to real hrefs.
    """
    candidate = project_dir / "sources" / "images" / "figure_review.json"
    if not candidate.exists():
        return []
    try:
        text = await aread_text(candidate, encoding="utf-8")
        records = json.loads(text)
    except (OSError, ValueError):
        return []
    inventory: list[dict] = []
    for rec in records:
        try:
            abs_path = Path(rec.get("path") or "").resolve()
            try:
                rel = abs_path.relative_to(project_dir.resolve())
                rel_str = f"../{rel.as_posix()}" if rel.parts and rel.parts[0] == "sources" else rel.as_posix()
            except ValueError:
                rel_str = str(abs_path)
        except (OSError, ValueError):
            rel_str = str(rec.get("path") or "")
        inventory.append({
            "path": rel_str,
            "natural_width": int(rec.get("natural_width") or 0),
            "natural_height": int(rec.get("natural_height") or 0),
            "aspect_ratio": float(rec.get("aspect_ratio") or 0.0),
            "caption": rec.get("caption") or "",
            "page_number": rec.get("page_number"),
            "extraction_method": rec.get("extraction_method") or "",
            "review_flags": list(rec.get("review_flags") or []),
        })
    return inventory


def _build_figure_inventory(paper, project_dir: Path) -> list[dict]:
    """Collect available figures with natural sizes for the strategist prompt."""
    inventory: list[dict] = []
    for fig in paper.all_figures():
        if not getattr(fig, "available", False):
            continue
        try:
            rel = Path(fig.path).resolve().relative_to(project_dir.resolve())
            rel_str = f"../{rel.as_posix()}" if rel.parts and rel.parts[0] == "sources" else rel.as_posix()
        except (ValueError, OSError):
            rel_str = str(fig.path)
        inventory.append({
            "path": rel_str,
            "natural_width": int(getattr(fig, "natural_width", 0) or 0),
            "natural_height": int(getattr(fig, "natural_height", 0) or 0),
            "aspect_ratio": float(getattr(fig, "aspect_ratio", 0.0) or 0.0),
            "caption": getattr(fig, "caption", "") or "",
            "page_number": getattr(fig, "page_number", None),
            "extraction_method": getattr(fig, "extraction_method", "") or "",
            "review_flags": list(getattr(fig, "review_flags", []) or []),
        })
    return inventory


def _embed_svg_preview(svg_content: str, project_dir: Path, page_num: int | None = None) -> str:
    """Embed image hrefs as base64 data URIs so browsers can render them.

    Runs the same lightweight render-prep path used by preview/export,
    including icon embedding, image embedding, and safe text flattening.
    """
    from backend.generator.svg_finalize.render_ready import prepare_svg_content_for_render

    try:
        return prepare_svg_content_for_render(svg_content, project_dir / "svg_output", page_num=page_num)
    except Exception as exc:
        raise RuntimeError(f"SVG preview preparation failed: {exc}") from exc


# ── Refine pipeline ───────────────────────────────────────────────────────────


@dataclass
class RefineRequest:
    """Parameters for a refine (feedback-based iteration) run."""

    project_dir: str        # absolute path to the existing project workspace
    feedback: str           # latest user feedback text
    feedback_history: list[str]  # all feedback rounds including the latest
    job_id: str             # new job ID (for logging / context)
    parent_job_id: str      # job ID of the previous generation
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str | None = None
    canvas_format: str = "ppt169"
    style: str = "academic"
    language: str = "zh"
    detail_level: str = "normal"
    timeout_seconds: int | None = None
    max_critic_attempts: int = 3
    target_pages: list[int] | None = None
    allow_structure_changes: bool = False
    style_overrides: dict | None = None
    icon_library: str = "chunk"
    deepseek_settings: dict | None = None
    openai_settings: dict | None = None
    enable_visual_critic: bool = False
    enable_icon: bool = False
    enable_icon_rag: bool = False
    gemini_api_key: str | None = None
    visual_qa_max_attempts: int = 1
    template_id: str | None = None
    render_engine: Literal["svg", "image2"] = "svg"


async def run_refine_pipeline(
    request: RefineRequest,
) -> AsyncIterator[ProgressEvent]:
    """Re-run stages 4–6 (SVG generation → finalize → export) with feedback.

    Reads the existing ``manuscript.md`` and ``design_spec.md`` from the
    project directory, appends the accumulated feedback as an extra
    instruction block, then re-generates all SVG pages.

    Previously generated SVGs are archived to ``svg_archive/round_N/``
    before being overwritten so the user can compare iterations.

    Yields ProgressEvent at each stage transition — identical shape to
    ``run_pipeline`` so the frontend WebSocket handler needs no changes.
    """
    from backend.generator.project_manager import get_notes, get_svg_files
    from backend.generator.svg_finalize import finalize_project
    from backend.generator.svg_to_pptx import create_pptx
    from backend.llm import create_provider

    project_dir = Path(request.project_dir)
    if not project_dir.exists():
        yield ProgressEvent("error", "error", f"Project directory not found: {project_dir}")
        return

    # Read existing manuscript and design_spec
    manuscript_path = project_dir / "manuscript.md"
    design_spec_path = project_dir / "design_spec.md"

    if not manuscript_path.exists() or not design_spec_path.exists():
        yield ProgressEvent(
            "error", "error",
            "Cannot refine: manuscript.md or design_spec.md missing from project."
        )
        return

    manuscript = await aread_text(manuscript_path, encoding="utf-8")
    design_spec = await aread_text(design_spec_path, encoding="utf-8")

    provider_kwargs = {"base_url": request.base_url}
    if request.deepseek_settings is not None:
        provider_kwargs["deepseek_settings"] = request.deepseek_settings
    if request.openai_settings is not None:
        provider_kwargs["openai_settings"] = request.openai_settings
    llm = create_provider(
        request.provider,
        request.api_key,
        **provider_kwargs,
    )
    visual_llm, visual_model = (
        _resolve_visual_critic_route() if request.enable_visual_critic else (None, None)
    )
    target_pages = sorted({page for page in (request.target_pages or []) if page > 0})

    refine_snapshot = set_usage_context(
        job_id=request.job_id,
        stage="refine",
        page=None,
        attempt=1,
    )

    # Build feedback block injected into the SVG executor prompt
    feedback_block = _build_feedback_block(
        request.feedback_history,
        target_pages=target_pages,
        allow_structure_changes=request.allow_structure_changes,
    )
    overrides_block = _build_style_overrides_block(request.style_overrides)
    if overrides_block:
        feedback_block = (
            f"{feedback_block}\n\n{overrides_block}" if feedback_block else overrides_block
        )

    if request.allow_structure_changes:
        set_usage_context(stage="research", page=None, attempt=1)
        yield ProgressEvent("research", "started", "Revising manuscript structure from feedback...", 0.0)
        manuscript = await research_agent.revise_manuscript(
            manuscript,
            llm,
            request.model,
            feedback_history=request.feedback_history,
            language=request.language,
            detail_level=request.detail_level,
            target_pages=target_pages,
            allow_structure_changes=True,
        )
        await awrite_text(manuscript_path, manuscript, encoding="utf-8")
        yield ProgressEvent("research", "complete", "Manuscript revised", 0.15)

        set_usage_context(stage="strategy", page=None, attempt=1)
        yield ProgressEvent("strategy", "started", "Rebuilding design specification...", 0.15)
        refine_figure_inventory = await _load_figure_inventory(project_dir)
        design_spec = await strategist_agent.create_design_spec(
            manuscript,
            llm,
            request.model,
            canvas_format=request.canvas_format,
            style=request.style,
            language=request.language,
            detail_level=request.detail_level,
            icon_library=request.icon_library,
            style_overrides=request.style_overrides,
            enable_icon=request.enable_icon,
            enable_icon_rag=request.enable_icon_rag,
            gemini_api_key=request.gemini_api_key,
            figure_inventory=refine_figure_inventory,
        )
        await awrite_text(design_spec_path, design_spec, encoding="utf-8")
        yield ProgressEvent("strategy", "complete", "Design spec rebuilt", 0.30)

    # Archive current svg_output before overwriting
    _archive_svgs(project_dir)
    if target_pages and not request.allow_structure_changes:
        _seed_svg_output_for_targeted_refine(project_dir, target_pages)

    # ── Stage 4: SVG generation (with feedback) ───────────────────────────
    set_usage_context(stage="generation", page=None, attempt=1)
    total_pages = count_manuscript_pages(manuscript)
    pages_to_generate = len(target_pages) if target_pages and not request.allow_structure_changes else total_pages
    generation_start = 0.30 if request.allow_structure_changes else 0.0
    generation_span = 0.30 if request.allow_structure_changes else 0.60
    yield ProgressEvent(
        "generation", "started",
        "Re-generating selected slides with feedback..." if target_pages and not request.allow_structure_changes else "Re-generating slides with feedback...",
        generation_start,
        data={"total_slides": pages_to_generate},
    )
    generated = 0

    refine_critic_events: list[dict] = []

    async def _refine_on_critic(
        page_num: int,
        attempt: int,
        report: CriticReport,
        repair_prompt: str | None,
        archive_path: str | None,
    ) -> None:
        entry: dict = {
            "page": page_num,
            "attempt": attempt,
            "report": report.to_dict(),
        }
        if repair_prompt is not None:
            entry["repair_prompt"] = repair_prompt
        if archive_path is not None:
            entry["archive_path"] = archive_path
        refine_critic_events.append(entry)

    refine_inventory = await _load_figure_inventory(project_dir)

    # Load template context for refine if specified
    refine_template_ctx = ""
    refine_template_skeletons: dict[str, str] | None = None
    if request.template_id:
        from backend.generator.template_manager import (
            build_template_context_for_executor,
            build_template_skeletons,
            load_template,
        )
        _tmpl = load_template(request.template_id)
        if _tmpl:
            refine_template_ctx = build_template_context_for_executor(_tmpl)
            refine_template_skeletons = build_template_skeletons(_tmpl)

    target_page_set = set(target_pages) if target_pages and not request.allow_structure_changes else None
    if request.render_engine == "image2":
        from .image2_renderer import generate_image2_svg_pages

        image2_pages = await generate_image2_svg_pages(
            manuscript,
            f"{design_spec}\n\nFeedback direction:\n{feedback_block}",
            project_dir,
            canvas_format=request.canvas_format,
            language=request.language,
            target_pages=target_page_set,
        )
        page_stream = image2_pages
    else:
        page_stream = []
        async for page_num, svg_content in svg_executor.generate_svg_pages(
            design_spec,
            manuscript,
            project_dir,
            llm,
            request.model,
            style=request.style,
            language=request.language,
            detail_level=request.detail_level,
            extra_instruction=feedback_block,
            target_pages=target_page_set,
            on_critic=_refine_on_critic,
            figure_inventory=refine_inventory,
            enable_visual_critic=request.enable_visual_critic,
            max_critic_attempts=request.max_critic_attempts,
            visual_qa_max_attempts=request.visual_qa_max_attempts,
            visual_critic_llm=visual_llm,
            visual_critic_model=visual_model,
            template_context=refine_template_ctx or None,
            template_skeletons=refine_template_skeletons,
            resume_existing=False,
        ):
            page_stream.append((page_num, svg_content))

    for page_num, svg_content in page_stream:
        generated += 1
        progress = generation_start + (generated / max(pages_to_generate, 1)) * generation_span

        preview_svg = _embed_svg_preview(svg_content, project_dir, page_num=page_num)
        page_critic = [ev for ev in refine_critic_events if ev["page"] == page_num]
        yield ProgressEvent(
            "generation", "progress",
            f"Generated slide {page_num}/{total_pages}",
            progress,
            data={"page": page_num, "svg": preview_svg, "critic": page_critic},
        )

    yield ProgressEvent(
        "generation",
        "complete",
        f"{generated} slides regenerated",
        generation_start + generation_span,
    )

    # ── Stage 5: Post-processing ──────────────────────────────────────────
    set_usage_context(stage="postprocess", page=None, attempt=1)
    postprocess_start = generation_start + generation_span
    export_start = 0.80 if request.allow_structure_changes else 0.80
    yield ProgressEvent("postprocess", "started", "Finalizing SVGs...", postprocess_start)
    stats = await aoffload(finalize_project, project_dir)
    yield ProgressEvent(
        "postprocess", "complete",
        f"Processed {stats['total_files']} files",
        export_start,
    )

    # ── Stage 6: Export PPTX ─────────────────────────────────────────────
    set_usage_context(stage="export", page=None, attempt=1)
    yield ProgressEvent("export", "started", "Exporting to PowerPoint...", export_start)
    svg_files = get_svg_files(project_dir, source="final")
    is_roadshow_refine = _looks_like_roadshow_manuscript(manuscript)
    cover_stripped = False
    if is_roadshow_refine and request.render_engine != "image2":
        cover_stripped = await _ensure_roadshow_cover_svg_has_no_images(svg_files)
    await _ensure_notes_files_from_manuscript(project_dir, manuscript, svg_files)
    notes = get_notes(project_dir, svg_files)
    if is_roadshow_refine:
        hard_gate = await evaluate_roadshow_export_artifacts(svg_files, notes)
        hard_gate["cover_image_removed"] = cover_stripped
        await awrite_text(
            project_dir / "roadshow_refine_export_hard_quality.json",
            json.dumps(hard_gate, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not hard_gate.get("passed"):
            yield ProgressEvent(
                "export",
                "complete",
                "已生成预览；正式导出需补齐：" + _format_quality_findings(hard_gate.get("findings") or []),
                1.0,
                data={
                    "output_path": None,
                    "formal_export_blocked": True,
                    "roadshow_hard_quality": hard_gate,
                },
            )
            return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pptx_path = project_dir / "exports" / f"presentation_{timestamp}.pptx"

    export_warnings: list[str] = []
    if request.render_engine == "image2" and settings.image2_export_mode == "image":
        from backend.generator.image2_editable_export import create_image2_image_pptx

        _, export_warnings = await aoffload(
            create_image2_image_pptx,
            project_dir,
            pptx_path,
            aspect_ratio="16:9",
        )
    elif request.render_engine == "image2" and settings.image2_export_mode == "editable":
        from backend.generator.image2_editable_export import create_image2_editable_pptx

        _, export_warnings = await aoffload(
            create_image2_editable_pptx,
            svg_files,
            project_dir,
            pptx_path,
            canvas_format=request.canvas_format,
            notes=notes,
        )
    else:
        await aoffload(
            create_pptx,
            svg_files,
            pptx_path,
            canvas_format=request.canvas_format,
            notes=notes,
        )

    # Persist feedback history to disk for auditability
    await _save_feedback_history(project_dir, request.feedback_history)
    await _save_critic_history(project_dir, refine_critic_events, refine=True)

    yield ProgressEvent(
        "export", "complete",
        "Refined PowerPoint generated!",
        1.0,
        data={"output_path": str(pptx_path), "critic": refine_critic_events, "warnings": export_warnings},
    )

    reset_usage_context(refine_snapshot)


def _archive_svgs(project_dir: Path) -> None:
    """Copy current svg_output/ into svg_archive/round_N/ before overwriting."""
    import shutil

    svg_output = project_dir / "svg_output"
    if not svg_output.exists():
        return

    archive_base = project_dir / "svg_archive"
    archive_base.mkdir(exist_ok=True)

    # find next round number
    existing = [d for d in archive_base.iterdir() if d.is_dir() and d.name.startswith("round_")]
    next_round = len(existing) + 1
    dest = archive_base / f"round_{next_round:02d}"
    try:
        shutil.copytree(svg_output, dest)
    except Exception:
        pass


def _build_feedback_block(
    feedback_history: list[str],
    *,
    target_pages: list[int] | None = None,
    allow_structure_changes: bool = False,
) -> str:
    """Format accumulated feedback history as a prompt instruction block."""
    if not feedback_history:
        return ""
    lines = ["## User Feedback (apply to ALL slides)"]
    if target_pages:
        lines.append(
            "\n## Targeted Scope\n"
            f"\nOnly modify these slide pages: {', '.join(map(str, target_pages))}."
            "\nKeep all other pages visually and semantically unchanged."
        )
    if allow_structure_changes:
        lines.append(
            "\n## Structural Changes Allowed\n"
            "\nYou may insert new slides, remove slides, split dense slides, or reorder slides if needed."
        )
    for i, fb in enumerate(feedback_history, 1):
        lines.append(f"\n### Round {i}\n{fb.strip()}")
    lines.append(
        "\n**Important:** Address ALL feedback points above when generating each slide."
    )
    return "\n".join(lines)


def _build_style_overrides_block(overrides: dict | None) -> str:
    """Format user style overrides (palette/font/density) as a prompt block."""
    if not overrides:
        return ""
    parts: list[str] = []
    palette = overrides.get("palette") if isinstance(overrides, dict) else None
    font = overrides.get("font") if isinstance(overrides, dict) else None
    font_heading = overrides.get("font_heading") if isinstance(overrides, dict) else None
    font_body = overrides.get("font_body") if isinstance(overrides, dict) else None
    cjk_heading = overrides.get("cjk_heading") if isinstance(overrides, dict) else None
    cjk_body = overrides.get("cjk_body") if isinstance(overrides, dict) else None
    density = overrides.get("density") if isinstance(overrides, dict) else None
    if palette:
        try:
            colors = ", ".join(str(c) for c in palette if c)
        except TypeError:
            colors = ""
        if colors:
            parts.append(
                f"- **Palette override** (use these exact colors for primary / accent / background "
                f"where appropriate): {colors}"
            )
    if font_heading or font_body or cjk_heading or cjk_body:
        if font_heading:
            parts.append(
                f"- **Western heading font**: Use `{font_heading}` for Western heading `<text>` elements."
            )
        if font_body:
            parts.append(
                f"- **Western body font**: Use `{font_body}` for Western body `<text>` elements."
            )
        if cjk_heading:
            parts.append(
                f"- **CJK heading font**: Use `{cjk_heading}` for CJK heading `<text>` elements."
            )
        if cjk_body:
            parts.append(
                f"- **CJK body font**: Use `{cjk_body}` for CJK body `<text>` elements."
            )
    elif font:
        parts.append(
            f"- **Font override**: Use this font-family for every SVG `<text>` element: `{font}`."
        )
    if density:
        density_hint = {
            "compact": "Prefer dense but legible layouts: smaller paddings, tighter line heights, more items per slide.",
            "normal": "Keep balanced spacing and default density.",
            "spacious": "Use generous whitespace, larger margins, fewer items per slide.",
        }.get(str(density), "")
        parts.append(f"- **Density override** (`{density}`): {density_hint}")
    if not parts:
        return ""
    return "## Style Overrides (must follow)\n" + "\n".join(parts)


async def _save_feedback_history(project_dir: Path, history: list[str]) -> None:
    """Append-write feedback_history.json for auditability."""
    path = project_dir / "feedback_history.json"
    await awrite_text(
        path,
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def _save_critic_history(
    project_dir: Path,
    critic_events: list[dict],
    *,
    refine: bool = False,
) -> None:
    """Persist critic events to critic_history.json for post-run analysis."""
    path = project_dir / "critic_history.json"
    existing: dict = {}
    if path.exists():
        try:
            text = await aread_text(path, encoding="utf-8")
            existing = json.loads(text)
        except (json.JSONDecodeError, OSError):
            existing = {}

    key = "refine_events" if refine else "generation_events"
    existing[key] = critic_events
    existing["updated_at"] = datetime.now().isoformat()
    if "created_at" not in existing:
        existing["created_at"] = existing["updated_at"]

    await awrite_text(
        path,
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _seed_svg_output_for_targeted_refine(project_dir: Path, target_pages: list[int]) -> None:
    """Seed svg_output/ with the latest stable deck before partial regeneration."""
    import shutil

    source_dir = project_dir / "svg_final"
    if not source_dir.exists() or not any(source_dir.glob("*.svg")):
        source_dir = project_dir / "svg_output"
    if not source_dir.exists():
        return

    output_dir = project_dir / "svg_output"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for svg_path in sorted(source_dir.glob("*.svg")):
        shutil.copy2(svg_path, output_dir / svg_path.name)

    for page in target_pages:
        for existing in output_dir.glob(f"{page:02d}_*.svg"):
            existing.unlink(missing_ok=True)
