"""Roadshow presentation script skill.

This module upgrades per-slide roadshow speaker notes into a full-session
competition script while preserving the existing manuscript contract.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from backend.llm import LLMMessage, LLMProvider

from .manuscript import extract_page_type, page_title, split_manuscript_pages

logger = logging.getLogger(__name__)

DEFAULT_TARGET_DURATION_SEC = 60 * 60
DEFAULT_TARGET_CHARS = 8000
MAX_NOTE_CHARS = 4000

FIELD_VALUE_RE_TEMPLATE = (
    r"(?ims)^\s*(?:\*\*)?{name}(?:\*\*)?\s*:\s*"
    r"(.*?)(?=^\s*(?:\*\*)?[A-Za-z_][A-Za-z0-9_]*(?:\*\*)?\s*:|^\s*<!--|^\s*#|\Z)"
)
SPEAKER_NOTES_FIELD_RE = re.compile(
    FIELD_VALUE_RE_TEMPLATE.format(name=re.escape("speaker_notes"))
)
FORBIDDEN_SCRIPT_META_RE = re.compile(
    r"本页|这一页|这页|页面|核心观点|核心结论|证明任务|证明对象|"
    r"讲解时|可以自然提示|如果现场|字段|备注|主视觉|版式|布局|"
    r"占位|待补充|项目名称|一句定位语|speaker_notes|main_script|sub_script|"
    r"transition|prompt|生成器",
    re.IGNORECASE,
)
SENTENCE_END_RE = re.compile(r"[。！？!?]$")


@dataclass
class ScriptPage:
    page_index: int
    page_type: str
    title: str
    core: str
    visible_content: str
    speaker_goal: str
    judge_focus: str
    story_role: str
    stage_mode: str
    transition: str
    time_budget_sec: int
    existing_notes: str
    image2_page_text: str = ""
    visual_scene: str = ""
    primary_visual: str = ""
    asset_refs: str = ""
    visual_calibration_priority: str = "normal"
    visual_calibration_reason: str = ""


@dataclass
class ScriptSkillResult:
    manuscript: str
    artifact: dict[str, Any]
    quality_report: dict[str, Any]


def _scaled_script_targets(
    page_count: int,
    target_duration_sec: int,
    target_chars: int,
) -> tuple[int, int]:
    return (
        min(target_duration_sec, max(180, max(1, page_count) * 105)),
        min(target_chars, max(800, max(1, page_count) * 320)),
    )


def _script_token_budget(target_chars: int) -> int:
    return min(14000, max(4096, target_chars * 2))


async def enhance_roadshow_script(
    *,
    llm: LLMProvider,
    model: str,
    manuscript: str,
    project_dir: Path,
    debug_dir: Path | None = None,
    material_analysis: str = "",
    outline_plan: str = "",
    run_of_show_plan: str = "",
    contestant_plan: str = "",
    target_duration_sec: int = DEFAULT_TARGET_DURATION_SEC,
    target_chars: int = DEFAULT_TARGET_CHARS,
    on_progress: Callable[[str, float], None] | None = None,
) -> ScriptSkillResult:
    """Generate a full roadshow script artifact and rewrite speaker notes."""
    pages = _parse_script_pages(manuscript)
    pages = _enrich_pages_with_visual_context(pages, project_dir)
    if not pages:
        artifact = _empty_artifact(target_duration_sec, target_chars)
        report = {"passed": False, "findings": [{"severity": "error", "message": "No manuscript pages found."}]}
        _write_artifacts(project_dir, artifact, report)
        return ScriptSkillResult(manuscript=manuscript, artifact=artifact, quality_report=report)

    # The defaults describe a full competition deck. Keep short smoke tests
    # and intentionally small decks proportional instead of asking a two-page
    # deck for an 8,000-character, 60-minute script.
    target_duration_sec, target_chars = _scaled_script_targets(
        len(pages),
        target_duration_sec,
        target_chars,
    )

    if on_progress:
        on_progress("正在生成国赛完整路演讲稿", 0.287)

    artifact: dict[str, Any] | None = None
    llm_error: str | None = None
    try:
        artifact = await _generate_script_artifact_with_llm(
            llm=llm,
            model=model,
            pages=pages,
            material_analysis=material_analysis,
            outline_plan=outline_plan,
            run_of_show_plan=run_of_show_plan,
            contestant_plan=contestant_plan,
            target_duration_sec=target_duration_sec,
            target_chars=target_chars,
        )
    except Exception as exc:  # pragma: no cover - production generation guard
        llm_error = str(exc)
        logger.warning("Roadshow script skill LLM generation failed; leaving speaker notes empty: %s", exc)

    if artifact is None:
        artifact = _empty_artifact(target_duration_sec, target_chars)
        artifact["generationError"] = llm_error or "LLM output unavailable"

    try:
        artifact = _normalize_artifact(artifact, pages, target_duration_sec, target_chars)
    except Exception as exc:
        logger.warning("Roadshow script skill artifact normalization failed: %s", exc)
        artifact = _empty_artifact(target_duration_sec, target_chars)
        artifact["generationError"] = f"artifact normalization failed: {exc}"
    quality_report = _quality_report(artifact, pages, target_chars)

    enhanced_manuscript = _rewrite_manuscript_speaker_notes(manuscript, artifact)
    _write_artifacts(project_dir, artifact, quality_report)
    _sync_cards_speaker_notes(project_dir, artifact)
    _write_visual_calibration_plan(project_dir, pages, artifact)
    if debug_dir:
        _write_json(debug_dir / "roadshow_script_skill_artifact.json", artifact)
        _write_json(debug_dir / "roadshow_script_skill_quality_report.json", quality_report)
        _write_visual_calibration_plan(debug_dir, pages, artifact)

    return ScriptSkillResult(
        manuscript=enhanced_manuscript,
        artifact=artifact,
        quality_report=quality_report,
    )


def _parse_script_pages(manuscript: str) -> list[ScriptPage]:
    pages: list[ScriptPage] = []
    for index, page in enumerate(split_manuscript_pages(manuscript), start=1):
        pages.append(
            ScriptPage(
                page_index=index,
                page_type=extract_page_type(page),
                title=_clean_text(page_title(page), max_chars=80) or f"第{index}页",
                core=_field_value(page, "page_core_sentence", max_chars=220),
                visible_content=_field_value(page, "visible_content", max_chars=420),
                speaker_goal=_field_value(page, "speaker_goal", max_chars=180),
                judge_focus=_field_value(page, "judge_focus", max_chars=160),
                story_role=_field_value(page, "story_role", max_chars=80),
                stage_mode=_field_value(page, "stage_mode", max_chars=80),
                transition=_field_value(page, "transition", max_chars=180)
                or _field_value(page, "next_slide_bridge", max_chars=180),
                time_budget_sec=_safe_int(_field_value(page, "time_budget_sec", max_chars=20), 0),
                existing_notes=_field_value(page, "speaker_notes", max_chars=MAX_NOTE_CHARS),
            )
        )
    return pages


def _enrich_pages_with_visual_context(pages: list[ScriptPage], project_dir: Path) -> list[ScriptPage]:
    contexts = _load_visual_contexts(project_dir)
    for page in pages:
        context = contexts.get(page.page_index, {})
        page.image2_page_text = _clean_text(context.get("page_text") or "", max_chars=520)
        page.visual_scene = _clean_text(context.get("visual_scene") or "", max_chars=700)
        page.primary_visual = _clean_text(context.get("primary_visual") or "", max_chars=520)
        page.asset_refs = _clean_text(context.get("asset_refs") or "", max_chars=320)
        priority, reason = _visual_calibration_priority(page)
        page.visual_calibration_priority = priority
        page.visual_calibration_reason = reason
    return pages


def _load_visual_contexts(project_dir: Path) -> dict[int, dict[str, Any]]:
    contexts: dict[int, dict[str, Any]] = {}
    _merge_image2_descriptions(contexts, project_dir / "image2_page_descriptions.json")
    for name in ("page_content_cards.confirmed.json", "page_content_cards.json"):
        _merge_page_cards(contexts, project_dir / name)
    return contexts


def _merge_image2_descriptions(contexts: dict[int, dict[str, Any]], path: Path) -> None:
    payload = _read_json(path)
    rows = payload.get("descriptions") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return
    for fallback_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        page = _safe_int(item.get("page"), fallback_index)
        context = contexts.setdefault(page, {})
        context.update(
            {
                "page_text": item.get("page_text") or item.get("core_message") or context.get("page_text", ""),
                "visual_scene": item.get("visual_scene") or context.get("visual_scene", ""),
                "primary_visual": item.get("visual_scene") or context.get("primary_visual", ""),
                "asset_refs": _join_list(item.get("asset_refs")) or context.get("asset_refs", ""),
            }
        )


def _merge_page_cards(contexts: dict[int, dict[str, Any]], path: Path) -> None:
    payload = _read_json(path)
    rows = payload.get("cards") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return
    for fallback_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        page = _safe_int(item.get("page"), fallback_index)
        context = contexts.setdefault(page, {})
        main_visual = item.get("main_visual") if isinstance(item.get("main_visual"), dict) else {}
        primary_visual = item.get("primary_visual") if isinstance(item.get("primary_visual"), dict) else {}
        primary_visual_text = "；".join(
            str(value).strip()
            for value in [
                primary_visual.get("type"),
                primary_visual.get("purpose"),
                primary_visual.get("required_elements"),
            ]
            if value
        )
        context.setdefault("page_text", item.get("visible_content") or item.get("core_sentence") or "")
        context.setdefault(
            "visual_scene",
            main_visual.get("visual_scene") or main_visual.get("purpose") or item.get("visual_strategy") or "",
        )
        context.setdefault("primary_visual", primary_visual_text)
        context.setdefault("asset_refs", _join_list(item.get("required_assets")) or _join_list(item.get("asset_ids")))


def _visual_calibration_priority(page: ScriptPage) -> tuple[str, str]:
    text = _page_signal_text(page)
    if page.page_type in {"cover", "chapter", "ending"}:
        return "low", "structural page"
    if re.search(r"政策|背景|痛点|需求|行业|市场|调研|研发动因|方案|架构|实操|演示|测试|结果|价值", text):
        return "high", "key narrative or proof page"
    if page.visual_scene or page.primary_visual:
        return "medium", "has image2/page-card visual context"
    return "normal", "standard content page"


SCRIPT_CHUNK_SIZE = 8
SCRIPT_CHUNK_PARALLEL = 2


async def _generate_script_artifact_with_llm(
    *,
    llm: LLMProvider,
    model: str,
    pages: list[ScriptPage],
    material_analysis: str,
    outline_plan: str,
    run_of_show_plan: str,
    contestant_plan: str,
    target_duration_sec: int,
    target_chars: int,
) -> dict[str, Any]:
    """Generate script JSON in parallel page chunks for reliability on 35-45 page decks.

    One giant JSON for 40 pages often returns empty/truncated payloads; chunking
    raises pass rate while keeping the same speaker-note contract.
    """
    import asyncio

    if len(pages) <= SCRIPT_CHUNK_SIZE:
        return await _generate_script_chunk_with_llm(
            llm=llm,
            model=model,
            pages=pages,
            material_analysis=material_analysis,
            outline_plan=outline_plan,
            run_of_show_plan=run_of_show_plan,
            contestant_plan=contestant_plan,
            target_duration_sec=target_duration_sec,
            target_chars=target_chars,
            chunk_label="full",
        )

    ranges = [
        (start, min(start + SCRIPT_CHUNK_SIZE - 1, len(pages)))
        for start in range(1, len(pages) + 1, SCRIPT_CHUNK_SIZE)
    ]
    sem = asyncio.Semaphore(SCRIPT_CHUNK_PARALLEL)
    merged_pages: list[dict[str, Any]] = []

    async def _one(start: int, end: int) -> list[dict[str, Any]]:
        chunk_pages = [page for page in pages if start <= page.page_index <= end]
        # Proportional targets for this segment.
        chunk_duration = max(60, int(target_duration_sec * len(chunk_pages) / max(1, len(pages))))
        chunk_chars = max(400, int(target_chars * len(chunk_pages) / max(1, len(pages))))
        async with sem:
            try:
                artifact = await _generate_script_chunk_with_llm(
                    llm=llm,
                    model=model,
                    pages=chunk_pages,
                    material_analysis=material_analysis,
                    outline_plan=outline_plan,
                    run_of_show_plan=run_of_show_plan,
                    contestant_plan=contestant_plan,
                    target_duration_sec=chunk_duration,
                    target_chars=chunk_chars,
                    chunk_label=f"{start:02d}_{end:02d}",
                )
            except Exception as exc:
                logger.warning(
                    "Roadshow script chunk %s-%s failed: %s",
                    start,
                    end,
                    exc,
                )
                return []
        raw = artifact.get("pages") if isinstance(artifact, dict) else None
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    results = await asyncio.gather(*[_one(start, end) for start, end in ranges])
    for part in results:
        merged_pages.extend(part)

    if not merged_pages:
        raise ValueError("All script chunks failed or returned empty pages.")

    return {
        "version": 1,
        "targetDurationSec": target_duration_sec,
        "targetWordCount": target_chars,
        "pages": merged_pages,
    }


async def _generate_script_chunk_with_llm(
    *,
    llm: LLMProvider,
    model: str,
    pages: list[ScriptPage],
    material_analysis: str,
    outline_plan: str,
    run_of_show_plan: str,
    contestant_plan: str,
    target_duration_sec: int,
    target_chars: int,
    chunk_label: str,
) -> dict[str, Any]:
    prompt = _script_prompt(
        pages,
        material_analysis=material_analysis,
        outline_plan=outline_plan,
        run_of_show_plan=run_of_show_plan,
        contestant_plan=contestant_plan,
        target_duration_sec=target_duration_sec,
        target_chars=target_chars,
    )
    if chunk_label != "full":
        prompt += (
            f"\n\n## Chunk Constraint\n\n"
            f"只为页码 {pages[0].page_index}-{pages[-1].page_index} 生成 pages 数组，"
            f"共 {len(pages)} 项。pageIndex 使用全局页码，不要从 1 重编号。"
        )
    response = await llm.chat(
        [
            LLMMessage.system(_SCRIPT_SYSTEM_PROMPT),
            LLMMessage.user(prompt),
        ],
        model,
        temperature=0.42,
        max_tokens=_script_token_budget(target_chars),
    )
    return _parse_json_object(response.content)


_SCRIPT_SYSTEM_PROMPT = """你是职业院校技能大赛国赛路演讲稿总导演。

你的任务是把 PPT 页面稿升级成一套完整可上台朗读的路演讲稿。你写的是参赛选手对评委说的话，不是页面说明、备注、提示词或设计分析。

硬性标准：
- 默认按 60 分钟内路演、约 8000 个中文字符组织全稿，允许根据页数微调。
- 必须有完整故事线：真实问题 -> 解决方案 -> 系统实现 -> 现场证明 -> 测试结果 -> 创新价值 -> 团队收束。
- 必须支持团队协作，至少使用主讲人A、技术演示B、总结人C；涉及操作、测试、代码、设备的页要自然交接给技术演示B。
- 每页必须给出正式讲稿、预计时长、讲述人、舞台动作、评分关注点、自然转场和压缩版。
- 语言要像真实国赛现场：专业、克制、有画面感、有节奏、有评委意识。
- 禁止出现：本页、这一页、页面、核心观点、证明任务、证明对象、讲解时、字段、备注、主视觉、版式、布局、占位、待补充、项目名称、一句定位语、speaker_notes、main_script、prompt。

只输出一个 JSON 对象，不要 Markdown，不要解释。"""


def _script_prompt(
    pages: list[ScriptPage],
    *,
    material_analysis: str,
    outline_plan: str,
    run_of_show_plan: str,
    contestant_plan: str,
    target_duration_sec: int,
    target_chars: int,
) -> str:
    page_rows = []
    budgets = _page_budgets(pages, target_duration_sec, target_chars)
    for page, budget in zip(pages, budgets):
        page_rows.append(
            {
                "pageIndex": page.page_index,
                "pageType": page.page_type,
                "title": page.title,
                "targetChars": budget["targetChars"],
                "durationSec": budget["durationSec"],
                "core": page.core,
                "visibleContent": page.visible_content,
                "speakerGoal": page.speaker_goal,
                "judgeFocus": page.judge_focus,
                "storyRole": page.story_role,
                "stageMode": page.stage_mode,
                "transition": page.transition,
                "existingNotes": page.existing_notes,
                "image2PageText": page.image2_page_text,
                "visualScene": page.visual_scene,
                "primaryVisual": page.primary_visual,
                "assetRefs": page.asset_refs,
                "visualCalibrationPriority": page.visual_calibration_priority,
                "visualCalibrationReason": page.visual_calibration_reason,
            }
        )
    return (
        f"## Target\n"
        f"- totalDurationSec: {target_duration_sec}\n"
        f"- targetWordCount: {target_chars}\n"
        f"- totalPages: {len(pages)}\n\n"
        "## Output JSON Shape\n"
        "{\n"
        '  "version": 1,\n'
        '  "targetDurationSec": 3600,\n'
        '  "targetWordCount": 8000,\n'
        '  "pages": [\n'
        "    {\n"
        '      "pageIndex": 1,\n'
        '      "speaker": "主讲人A",\n'
        '      "durationSec": 90,\n'
        '      "targetChars": 180,\n'
        '      "emotion": "稳重开场",\n'
        '      "script": "正式可朗读讲稿",\n'
        '      "transitionOut": "自然转场",\n'
        '      "stageActions": ["面向评委", "指向屏幕"],\n'
        '      "scoringPoints": ["项目定位"],\n'
        '      "shortVersion": "30秒压缩版"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "## Page Inputs\n"
        f"{json.dumps(page_rows, ensure_ascii=False, indent=2)}\n\n"
        "## Material Analysis Snapshot\n"
        f"{_truncate(material_analysis, 2600)}\n\n"
        "## Outline Snapshot\n"
        f"{_truncate(outline_plan, 2200)}\n\n"
        "## Run Of Show Snapshot\n"
        f"{_truncate(run_of_show_plan, 2600)}\n\n"
        "## Contestant Perspective Snapshot\n"
        f"{_truncate(contestant_plan, 2200)}\n\n"
        "## Writing Rules\n"
        "- 写讲稿时必须同时参考 Page Inputs 里的 visibleContent、image2PageText、visualScene、primaryVisual 和 assetRefs；讲稿要能对得上最终 image2 页面画面，而不是只复述标题。\n"
        "- visualCalibrationPriority=high 的页面是关键页，必须讲清因果、证据、画面重点和评委判断，不得草草带过。\n"
        "- 不要平均用力，实操、系统、测试和价值页可以更饱满。\n"
        "- 政策背景、行业需求、市场分析、研发动因和痛点页是整场汇报的立论基础，必须讲透：先讲政策/行业变化，再讲传统方式为什么不够，最后落到本项目为什么必须做。\n"
        "- 这些立论基础页不能只写“政策支持、市场广阔、痛点明显”这类结论，必须补充因果链、场景代入和评委应关注的判断。\n"
        "- 封面和章节页要短，内容页要讲清事实，实操页要包含队友交接和评委观察点。\n"
        "- 每页 script 尽量贴近 targetChars，但不要为了凑字重复。\n"
        "- 每 3 到 5 页要有节奏变化，例如提问、强调数据、请队友操作、回扣评委关注点。\n"
    )


def _transition_for_page(page: ScriptPage) -> str:
    explicit = _clean_for_script(page.transition)
    if explicit:
        return _sentence(explicit)
    if page.page_type == "ending":
        return "我的汇报到此结束，感谢各位评委老师。"
    if re.search(r"实操|演示|测试|运行", page.title):
        return "接下来，我们继续用运行结果说明系统能力。"
    return "接下来，我们沿着这条主线继续展开。"


def _page_budgets(
    pages: list[ScriptPage],
    target_duration_sec: int,
    target_chars: int,
) -> list[dict[str, int]]:
    weights = []
    for page in pages:
        weight = 1.0
        page_text = _page_signal_text(page)
        if page.page_type in {"cover", "chapter", "ending"}:
            weight = 0.48
        if re.search(r"目录|大纲|议程|汇报结构", page_text):
            weight = 0.42
        if re.search(r"政策|背景|痛点|需求|行业|市场|调研|研发动因|十四五|乡村振兴|现代农业", page_text):
            weight += 1.15
        if re.search(r"方案|架构|总体设计|技术路线|系统设计", page_text):
            weight += 0.45
        if re.search(r"demo|operate|field|live|test|code|device|演示|实操|测试|代码|设备|联动", page.stage_mode + page.title):
            weight += 0.65
        if page.story_role in {"verify_result", "land_value", "unpack_mechanism"}:
            weight += 0.28
        weights.append(weight)
    total_weight = sum(weights) or 1
    budgets = []
    for page, weight in zip(pages, weights):
        target = max(90, round(target_chars * weight / total_weight))
        duration = page.time_budget_sec or max(35, round(target_duration_sec * weight / total_weight))
        if page.page_type in {"cover", "chapter", "ending"}:
            target = min(target, 220)
            duration = min(duration, 100)
        if _is_foundation_page(page):
            target = max(target, 420)
            duration = max(duration, 170)
        if _is_demo_or_technical_page(page):
            target = max(target, 360)
            duration = max(duration, 150)
        budgets.append({"targetChars": target, "durationSec": duration})
    return budgets


def _page_signal_text(page: ScriptPage) -> str:
    return " ".join(
        [
            page.title,
            page.core,
            page.visible_content,
            page.speaker_goal,
            page.judge_focus,
            page.story_role,
            page.stage_mode,
            page.image2_page_text,
            page.visual_scene,
            page.primary_visual,
            page.asset_refs,
        ]
    )


def _is_foundation_page(page: ScriptPage) -> bool:
    if page.page_type in {"cover", "chapter", "ending"}:
        return False
    if re.search(r"目录|大纲|议程|汇报结构", _page_signal_text(page)):
        return False
    return bool(
        re.search(
            r"政策|背景|痛点|需求|行业|市场|调研|研发动因|十四五|乡村振兴|现代农业",
            _page_signal_text(page),
        )
    )


def _is_demo_or_technical_page(page: ScriptPage) -> bool:
    return bool(
        re.search(
            r"demo|operate|field|live|test|code|device|演示|实操|测试|代码|设备|联动|方案|架构|技术路线|系统设计",
            _page_signal_text(page),
            flags=re.IGNORECASE,
        )
    )


def _normalize_artifact(
    artifact: dict[str, Any],
    pages: list[ScriptPage],
    target_duration_sec: int,
    target_chars: int,
) -> dict[str, Any]:
    raw_pages = artifact.get("pages")
    if not isinstance(raw_pages, list):
        raise ValueError("Script artifact missing pages list.")
    by_index = {
        _safe_int(item.get("pageIndex"), 0): item
        for item in raw_pages
        if isinstance(item, dict)
    }
    budgets = _page_budgets(pages, target_duration_sec, target_chars)
    normalized_pages = []
    for page, budget in zip(pages, budgets):
        item = by_index.get(page.page_index) or {}
        script = _clean_for_script(str(item.get("script") or ""))
        if not script or FORBIDDEN_SCRIPT_META_RE.search(script):
            # Prefer existing notes, then a deterministic stage-ready fallback so
            # render_from_cards never ships empty speaker_notes after skill failure.
            script = _clean_for_script(page.existing_notes) if page.existing_notes else ""
            if not script or FORBIDDEN_SCRIPT_META_RE.search(script):
                script = _fallback_script_for_page(page)
        normalized_pages.append(
            {
                "pageIndex": page.page_index,
                "title": page.title,
                "speaker": _clean_text(item.get("speaker"), max_chars=20) or _speaker_for_page(page),
                "durationSec": _safe_int(item.get("durationSec"), budget["durationSec"]),
                "targetChars": _safe_int(item.get("targetChars"), budget["targetChars"]),
                "emotion": _clean_text(item.get("emotion"), max_chars=30) or _emotion_for_page(page),
                "script": _truncate_on_sentence(script, MAX_NOTE_CHARS),
                "transitionOut": _clean_for_script(str(item.get("transitionOut") or "")) or _transition_for_page(page),
                "stageActions": _string_list(item.get("stageActions")) or _stage_actions_for_page(page),
                "scoringPoints": _string_list(item.get("scoringPoints")) or _scoring_points_for_page(page),
                "shortVersion": _clean_for_script(str(item.get("shortVersion") or "")) or _short_version(script),
            }
        )
    return {
        "version": 1,
        "targetDurationSec": target_duration_sec,
        "targetWordCount": target_chars,
        "actualWordCount": sum(_char_count(item["script"]) for item in normalized_pages),
        "pages": normalized_pages,
    }


def _quality_report(artifact: dict[str, Any], pages: list[ScriptPage], target_chars: int) -> dict[str, Any]:
    findings = []
    artifact_pages = artifact.get("pages") or []
    if len(artifact_pages) != len(pages):
        findings.append({"severity": "error", "message": "Script page count does not match manuscript."})
    total_chars = sum(_char_count(str(item.get("script", ""))) for item in artifact_pages if isinstance(item, dict))
    if total_chars < int(target_chars * 0.62):
        findings.append({"severity": "warning", "message": "Full script is shorter than target."})
    if total_chars > target_chars * 2:
        findings.append({"severity": "warning", "message": "Full script is much longer than target."})
    speakers = {str(item.get("speaker", "")).strip() for item in artifact_pages if isinstance(item, dict)}
    if len([speaker for speaker in speakers if speaker]) < 2 and len(pages) >= 8:
        findings.append({"severity": "warning", "message": "Speaker role variety is weak."})
    for item in artifact_pages:
        if not isinstance(item, dict):
            continue
        script = str(item.get("script") or "")
        page_index = _safe_int(item.get("pageIndex"), 0)
        page = next((page for page in pages if page.page_index == page_index), None)
        min_chars = 35 if page and page.page_type in {"cover", "chapter", "toc", "ending"} else 70
        severity = "warning" if page and page.page_type in {"cover", "chapter", "toc", "ending"} else "error"
        if _char_count(script) < min_chars:
            findings.append({"severity": severity, "page": page_index, "message": "Page script is shorter than expected."})
        if FORBIDDEN_SCRIPT_META_RE.search(script):
            findings.append({"severity": "error", "page": page_index, "message": "Page script contains internal meta language."})
    return {
        "passed": not any(item.get("severity") == "error" for item in findings),
        "actualWordCount": total_chars,
        "targetWordCount": target_chars,
        "findings": findings,
    }


def _rewrite_manuscript_speaker_notes(manuscript: str, artifact: dict[str, Any]) -> str:
    notes_by_index = {
        _safe_int(item.get("pageIndex"), 0): str(item.get("script") or "").strip()
        for item in artifact.get("pages", [])
        if isinstance(item, dict)
    }
    pages = split_manuscript_pages(manuscript)
    rewritten = []
    for index, page in enumerate(pages, start=1):
        note = notes_by_index.get(index, "")
        if note:
            rewritten.append(_replace_speaker_notes(page, note))
        else:
            rewritten.append(page)
    return "\n\n---\n\n".join(rewritten)


def _replace_speaker_notes(page: str, note: str) -> str:
    safe_note = _truncate_on_sentence(_clean_for_script(note), MAX_NOTE_CHARS)
    match = SPEAKER_NOTES_FIELD_RE.search(page)
    if match:
        start, end = match.span(1)
        return page[:start] + safe_note + "\n" + page[end:]
    return page.rstrip() + f"\n\nspeaker_notes: {safe_note}\n"


def _field_value(page: str, name: str, *, max_chars: int) -> str:
    pattern = re.compile(FIELD_VALUE_RE_TEMPLATE.format(name=re.escape(name)))
    match = pattern.search(page)
    if not match:
        return ""
    return _clean_text(match.group(1), max_chars=max_chars)


def _parse_json_object(text: str) -> dict[str, Any]:
    content = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
    if fenced:
        content = fenced.group(1)
    else:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def _speaker_for_page(page: ScriptPage) -> str:
    text = f"{page.stage_mode} {page.title} {page.story_role}".lower()
    if re.search(r"demo|operate|field|live|test|code|device|演示|实操|测试|代码|设备|联动", text):
        return "技术演示B"
    if page.page_type == "ending" or page.story_role == "land_value":
        return "总结人C"
    return "主讲人A"


def _emotion_for_page(page: ScriptPage) -> str:
    if page.page_type == "cover":
        return "稳重开场"
    if page.page_type == "ending":
        return "有力收束"
    if page.story_role == "raise_problem":
        return "问题牵引"
    if page.story_role == "verify_result":
        return "证据增强"
    if page.story_role == "land_value":
        return "价值升维"
    return "专业推进"


def _stage_actions_for_page(page: ScriptPage) -> list[str]:
    actions = ["面向评委", "指向屏幕关键信息"]
    if _speaker_for_page(page) == "技术演示B":
        actions.append("配合现场操作")
    if page.page_type == "ending":
        actions = ["回到评委席视线", "完成感谢收束"]
    return actions


def _scoring_points_for_page(page: ScriptPage) -> list[str]:
    text = f"{page.judge_focus} {page.speaker_goal} {page.story_role} {page.title}"
    points = []
    mapping = [
        ("应用场景", r"场景|用户|温室|企业|应用"),
        ("技术实现", r"技术|系统|架构|接口|代码|算法|设备"),
        ("现场实操", r"演示|实操|操作|联动|测试|运行"),
        ("成果验证", r"结果|数据|验证|记录|复核"),
        ("创新价值", r"创新|价值|推广|教学|就业|团队"),
    ]
    for label, pattern in mapping:
        if re.search(pattern, text):
            points.append(label)
    return points[:3] or ["表达逻辑", "项目支撑"]


def _short_version(script: str) -> str:
    sentences = re.split(r"(?<=[。！？!?])", script)
    result = "".join(sentence for sentence in sentences[:2]).strip()
    return _truncate_on_sentence(result or script, 160)


def _clean_text(value: Any, *, max_chars: int) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\[\[(?:ASSET|FIG):[^\]]+\]\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].strip()


def _clean_for_script(value: str) -> str:
    text = _clean_text(value, max_chars=MAX_NOTE_CHARS)
    text = re.sub(r"^(?:speaker_notes|speech_script|script|main_script|sub_script|transition)\s*[:：]\s*", "", text, flags=re.I)
    text = FORBIDDEN_SCRIPT_META_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ，,；;")
    return text


def _sentence(value: str) -> str:
    text = _clean_for_script(value)
    if not text:
        return ""
    return text if SENTENCE_END_RE.search(text) else f"{text}。"


def _split_points(value: str) -> list[str]:
    text = _clean_for_script(value)
    text = re.sub(r"(?:^|\s)(?:\d+|[一二三四五六七八九十]+)[.、]\s*", "\n", text)
    return [
        item.strip(" ，,；;")
        for item in re.split(r"[。；;\n]|->|→", text)
        if len(item.strip()) >= 4
    ]


def _truncate_on_sentence(text: str, max_chars: int) -> str:
    text = _clean_for_script(text)
    if len(text) <= max_chars:
        return text
    result = ""
    for sentence in re.split(r"(?<=[。！？!?])", text):
        if len(result + sentence) > max_chars:
            break
        result += sentence
    return (result or text[:max_chars]).strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_clean_text(item, max_chars=40) for item in value if _clean_text(item, max_chars=40)]
    if isinstance(value, str):
        return [_clean_text(item, max_chars=40) for item in re.split(r"[,，、;；]", value) if _clean_text(item, max_chars=40)]
    return []


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return fallback


def _char_count(value: str) -> int:
    return len(re.sub(r"\s+", "", str(value or "")))


def _quality_score(report: dict[str, Any]) -> int:
    score = 100
    for item in report.get("findings", []):
        score -= 30 if item.get("severity") == "error" else 8
    return score


def _truncate(value: str, limit: int) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "\n..."


def _empty_artifact(target_duration_sec: int, target_chars: int) -> dict[str, Any]:
    return {
        "version": 1,
        "targetDurationSec": target_duration_sec,
        "targetWordCount": target_chars,
        "actualWordCount": 0,
        "pages": [],
    }


def _fallback_script_for_page(page: ScriptPage) -> str:
    """Build a short, stage-ready script when LLM output is missing.

    This is intentionally factual and plain so export/preview still have
    readable notes; it is not a substitute for full skill quality.
    """
    core = _clean_for_script(page.core) or page.title
    points = _split_points(page.visible_content)[:4]
    body = "；".join(points) if points else _clean_for_script(page.visible_content)
    if page.page_type == "cover":
        return (
            f"尊敬的各位评委老师，大家好。我们汇报的项目是「{page.title}」。"
            f"核心定位是：{core}。接下来将按背景、方案、现场验证、成果与价值展开。"
        )
    if page.page_type == "ending":
        return (
            f"以上是「{page.title}」的汇报收束。{core}。"
            "感谢各位评委老师的指导，欢迎提问。"
        )
    transition = _clean_for_script(page.transition) or "接下来进入下一环节。"
    if body:
        return f"{core}。{body}。{transition}"
    return f"{core}。下面结合页面要点向各位评委说明。{transition}"


def _write_artifacts(project_dir: Path, artifact: dict[str, Any], report: dict[str, Any]) -> None:
    _write_json(project_dir / "roadshow_script_skill.json", artifact)
    _write_json(project_dir / "roadshow_script_quality_report.json", report)


def _sync_cards_speaker_notes(project_dir: Path, artifact: dict[str, Any]) -> None:
    notes_by_index = {
        _safe_int(item.get("pageIndex"), 0): _truncate_on_sentence(
            _clean_for_script(str(item.get("script") or "")),
            MAX_NOTE_CHARS,
        )
        for item in artifact.get("pages", [])
        if isinstance(item, dict)
    }
    notes_by_index = {page: note for page, note in notes_by_index.items() if page > 0 and note}
    if not notes_by_index:
        return
    for name in ("page_content_cards.json", "page_content_cards.confirmed.json"):
        path = project_dir / name
        payload = _read_json(path)
        cards = payload.get("cards")
        if not isinstance(cards, list):
            continue
        changed = False
        for fallback_index, card in enumerate(cards, start=1):
            if not isinstance(card, dict):
                continue
            page = _safe_int(card.get("page"), fallback_index)
            note = notes_by_index.get(page)
            if not note:
                continue
            if card.get("speaker_notes") != note:
                card["speaker_notes"] = note
                card["script_source"] = "roadshow-script-skill"
                changed = True
        if changed:
            _write_json(path, payload)


def _write_visual_calibration_plan(project_dir: Path, pages: list[ScriptPage], artifact: dict[str, Any]) -> None:
    artifact_pages = {
        _safe_int(item.get("pageIndex"), 0): item
        for item in artifact.get("pages", [])
        if isinstance(item, dict)
    }
    candidates = []
    for page in pages:
        if page.visual_calibration_priority not in {"high", "medium"}:
            continue
        script = str(artifact_pages.get(page.page_index, {}).get("script") or "")
        candidates.append(
            {
                "pageIndex": page.page_index,
                "title": page.title,
                "priority": page.visual_calibration_priority,
                "reason": page.visual_calibration_reason,
                "hasImage2Description": bool(page.image2_page_text or page.visual_scene),
                "hasPageCardVisualScene": bool(page.visual_scene or page.primary_visual),
                "scriptChars": _char_count(script),
                "visionModelStatus": "not_run",
                "recommendedNextStep": "run_vision_model_on_final_slide_image" if page.visual_calibration_priority == "high" else "use_structured_visual_context",
            }
        )
    _write_json(
        project_dir / "roadshow_visual_calibration_plan.json",
        {
            "version": 1,
            "mode": "medium_cost_key_pages",
            "policy": "Use structured page cards and image2 descriptions for all pages; reserve vision-model checks for high-priority or mismatch pages.",
            "candidateCount": len(candidates),
            "candidates": candidates,
        },
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _join_list(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip()
    return ""
