"""Roadshow planning artifacts and editable page content cards.

The vocational roadshow flow needs a stable middle layer before visual
rendering.  These helpers persist three reviewable JSON artifacts:

* material_diagnosis.json
* storyline_plan.json
* page_content_cards.json

The SVG executor should never be the first place where a slide's purpose is
decided.  It should render a confirmed PageContentCard.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from .manuscript import extract_page_type, page_title, split_manuscript_pages

ASSET_TOKEN_RE = re.compile(r"\[\[ASSET:([A-Za-z0-9_.:-]+)\]\]")
FIG_TOKEN_RE = re.compile(r"\[\[FIG:([A-Za-z0-9_.:-]+)\]\]")
PLACEHOLDER_TEXT_RE = re.compile(
    r"待确认|内容待|待补充|请补充|本页需补充|占位|placeholder|TODO|TBD|lorem",
    re.I,
)


@dataclass
class PageContentCard:
    """Editable per-slide content contract before visual rendering."""

    page: int
    page_type: str = "content"
    section: str = ""
    formal_title: str = ""
    core_sentence: str = ""
    visible_content: str = ""
    page_role: str = ""
    judge_focus: str = ""
    story_role: str = ""
    main_visual: dict[str, Any] = field(default_factory=dict)
    primary_visual: dict[str, Any] = field(default_factory=dict)
    required_assets: list[str] = field(default_factory=list)
    asset_ids: list[str] = field(default_factory=list)
    figure_ids: list[str] = field(default_factory=list)
    asset_status: str = "missing"
    material_policy: str = "missing_material_use_svg_or_method"
    fallback_visual: str = ""
    export_gate: str = "review_required"
    speaker_goal: str = ""
    speaker_notes: str = ""
    main_script: str = ""
    sub_script: str = ""
    transition: str = ""
    stage_mode: str = ""
    time_budget_sec: int | None = None
    execution: dict[str, Any] = field(default_factory=dict)
    source: str = "light_plan"
    quality_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_dir_from_debug_dir(debug_dir: Path | None) -> Path | None:
    if debug_dir is None:
        return None
    if debug_dir.name == "debug":
        return debug_dir.parent
    return debug_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_planning_artifacts(
    project_dir: Path | None,
    *,
    material_analysis: str,
    locked_facts: Any,
    page_count_decision: dict[str, Any],
    evidence_report: dict[str, Any],
    source_profile: dict[str, Any],
    outline_plan: str,
    run_of_show_plan: str,
    contestant_plan: str,
    slide_content_plan: str,
    allow_placeholder_fill: bool = True,
) -> list[PageContentCard]:
    cards = parse_slide_content_plan(slide_content_plan)
    if allow_placeholder_fill:
        cards = _ensure_card_count(cards, int(page_count_decision.get("recommended_pages") or len(cards) or 0))
    cards = normalize_cards(cards)

    if project_dir is None:
        return cards

    diagnosis = build_material_diagnosis(
        material_analysis=material_analysis,
        locked_facts=locked_facts,
        page_count_decision=page_count_decision,
        evidence_report=evidence_report,
        source_profile=source_profile,
    )
    storyline = build_storyline_plan(
        outline_plan=outline_plan,
        run_of_show_plan=run_of_show_plan,
        contestant_plan=contestant_plan,
        page_count_decision=page_count_decision,
        cards=cards,
    )
    card_payload = build_page_content_cards_payload(cards, page_count_decision=page_count_decision)

    write_json(project_dir / "material_diagnosis.json", diagnosis)
    write_json(project_dir / "storyline_plan.json", storyline)
    write_json(project_dir / "page_content_cards.json", card_payload)
    return cards


def write_image2_page_descriptions(project_dir: Path | None, cards: list[PageContentCard]) -> dict[str, Any]:
    payload = build_image2_page_descriptions_payload(cards)
    if project_dir is not None:
        write_json(project_dir / "image2_page_descriptions.json", payload)
    return payload


def write_image2_page_briefs(project_dir: Path | None, cards: list[PageContentCard]) -> dict[str, Any]:
    """Write rich page briefs consumed by the image2 renderer.

    This artifact intentionally stays deterministic: it thickens the existing
    PageContentCard contract without adding another long LLM request before
    rendering.
    """
    payload = build_image2_page_briefs_payload(cards)
    if project_dir is not None:
        write_json(project_dir / "image2_page_briefs.json", payload)
    return payload


def build_image2_page_descriptions_payload(cards: list[PageContentCard]) -> dict[str, Any]:
    normalized = normalize_cards(cards)
    return {
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "render_engine": "image2",
        "description_source": "clean_outline_cards",
        "descriptions": [
            {
                "page": card.page,
                "page_type": card.page_type,
                "section": card.section,
                "title": card.formal_title,
                "core_message": card.core_sentence,
                "page_text": card.visible_content or card.core_sentence,
                "visual_scene": _image2_visual_scene(card),
                "asset_refs": card.required_assets,
                "speaker_goal": card.speaker_goal,
            }
            for card in normalized
        ],
    }


def build_image2_page_briefs_payload(cards: list[PageContentCard]) -> dict[str, Any]:
    normalized = normalize_cards(cards)
    return {
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "render_engine": "image2",
        "brief_source": "page_content_cards",
        "briefs": [_image2_page_brief(card) for card in normalized],
    }


def _image2_page_brief(card: PageContentCard) -> dict[str, Any]:
    return {
        "page": card.page,
        "page_type": card.page_type,
        "section": card.section,
        "title": card.formal_title,
        "core_message": card.core_sentence,
        "visible_points": card.visible_content or card.core_sentence,
        "visual_scene": _image2_visual_scene(card),
        "layout_intent": _image2_layout_intent(card),
        "evidence_focus": _image2_evidence_focus(card),
        "asset_refs": list(card.required_assets or []),
        "speaker_goal": card.speaker_goal,
        "image_prompt_notes": _image2_prompt_notes(card),
        "material_policy": card.material_policy,
    }


def build_material_diagnosis(
    *,
    material_analysis: str,
    locked_facts: Any,
    page_count_decision: dict[str, Any],
    evidence_report: dict[str, Any],
    source_profile: dict[str, Any],
) -> dict[str, Any]:
    locked = locked_facts.to_dict() if hasattr(locked_facts, "to_dict") else locked_facts
    available_assets = evidence_report.get("available_assets") or []
    missing_core_types = evidence_report.get("missing_core_types") or []
    return {
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "audience": "职业院校技能大赛评审专家",
        "speech_design": {
            "official_minutes": 60,
            "content_minutes": 55,
            "buffer_minutes": 5,
        },
        "page_count_decision": page_count_decision,
        "source_profile": source_profile,
        "material_analysis": material_analysis.strip(),
        "locked_facts": locked,
        "asset_summary": {
            "available_asset_count": len(available_assets),
            "available_types": evidence_report.get("available_types") or [],
            "missing_core_types": missing_core_types,
            "formal_readiness": evidence_report.get("formal_readiness") or "unknown",
        },
        "truth_policy": [
            "真实截图、日志、证书、测试数据和合作材料只能来自用户上传或明确资料。",
            "缺少真实材料时，页面只能使用 SVG 示意、验证方法或待采集口径，不得伪造完成事实。",
            "搜索材料只补赛制、政策、行业背景，不覆盖用户真实项目材料。",
        ],
    }


def build_storyline_plan(
    *,
    outline_plan: str,
    run_of_show_plan: str,
    contestant_plan: str,
    page_count_decision: dict[str, Any],
    cards: list[PageContentCard],
) -> dict[str, Any]:
    phases = _infer_storyline_phases(cards)
    return {
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "recommended_pages": page_count_decision.get("recommended_pages") or len(cards),
        "storyline_principle": "比赛路演按项目成立、系统跑通、现场证明、创新价值、推广成长推进，突出现场验证、支撑材料和团队协作。",
        "phases": phases,
        "outline_plan_md": outline_plan.strip(),
        "run_of_show_md": run_of_show_plan.strip(),
        "contestant_perspective_md": contestant_plan.strip(),
    }


def build_page_content_cards_payload(
    cards: list[PageContentCard],
    *,
    page_count_decision: dict[str, Any] | None = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "status": "confirmed" if confirmed else "draft",
        "recommended_pages": page_count_decision.get("recommended_pages") if page_count_decision else len(cards),
        "page_count_decision": page_count_decision or {},
        "cards": [card.to_dict() for card in normalize_cards(cards)],
    }


def load_cards_payload(project_dir: Path, *, confirmed: bool = False) -> dict[str, Any]:
    preferred = project_dir / "page_content_cards.confirmed.json" if confirmed else project_dir / "page_content_cards.json"
    fallback = project_dir / "page_content_cards.json"
    path = preferred if preferred.exists() else fallback
    if not path.exists():
        return {"schema_version": 1, "deck_type": "vocational_roadshow", "status": "missing", "cards": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_cards_payload(project_dir: Path, payload: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
    raw_cards = payload.get("cards") or []
    cards = normalize_cards([card_from_dict(item, index + 1) for index, item in enumerate(raw_cards)])
    next_payload = {
        **payload,
        "schema_version": 1,
        "deck_type": "vocational_roadshow",
        "status": "confirmed" if confirmed else payload.get("status", "draft"),
        "cards": [card.to_dict() for card in cards],
    }
    target = project_dir / ("page_content_cards.confirmed.json" if confirmed else "page_content_cards.json")
    write_json(target, next_payload)
    if confirmed:
        write_json(project_dir / "page_content_cards.json", {**next_payload, "status": "confirmed"})
    return next_payload


def card_has_placeholder_text(card: PageContentCard) -> bool:
    text = "\n".join(
        str(value or "")
        for value in (
            card.formal_title,
            card.core_sentence,
            card.visible_content,
            card.speaker_goal,
            card.speaker_notes,
            (card.main_visual or {}).get("visual_scene"),
        )
    )
    return bool(PLACEHOLDER_TEXT_RE.search(text))


def validate_cards_for_formal_render(cards: list[PageContentCard], expected_pages: int | None = None) -> list[str]:
    errors: list[str] = []
    if expected_pages and len(cards) != expected_pages:
        errors.append(f"页纲数量不完整：expected {expected_pages}, got {len(cards)}")
    if not cards:
        errors.append("页纲为空")
        return errors
    for card in cards:
        page = card.page or len(errors) + 1
        if card.source == "local_placeholder" or "missing_llm_plan_row" in (card.quality_flags or []):
            errors.append(f"第 {page} 页来自本地占位补齐")
        if card_has_placeholder_text(card):
            errors.append(f"第 {page} 页含占位文本")
        if not _clean(card.formal_title):
            errors.append(f"第 {page} 页缺少正式标题")
        if not _clean(card.core_sentence):
            errors.append(f"第 {page} 页缺少核心句")
        if len(_clean(card.visible_content)) < 8:
            errors.append(f"第 {page} 页可见内容过短")
    return errors


def card_from_dict(data: dict[str, Any], default_page: int) -> PageContentCard:
    return PageContentCard(
        page=int(data.get("page") or default_page),
        page_type=str(data.get("page_type") or "content"),
        section=str(data.get("section") or ""),
        formal_title=str(data.get("formal_title") or data.get("title") or ""),
        core_sentence=str(data.get("core_sentence") or data.get("page_core_sentence") or ""),
        visible_content=str(data.get("visible_content") or ""),
        page_role=str(data.get("page_role") or ""),
        judge_focus=str(data.get("judge_focus") or ""),
        story_role=str(data.get("story_role") or ""),
        main_visual=dict(data.get("main_visual") or {}),
        primary_visual=dict(data.get("primary_visual") or {}),
        required_assets=_coerce_list(data.get("required_assets")),
        asset_ids=_coerce_list(data.get("asset_ids")),
        figure_ids=_coerce_list(data.get("figure_ids")),
        asset_status=str(data.get("asset_status") or "missing"),
        material_policy=str(data.get("material_policy") or "missing_material_use_svg_or_method"),
        fallback_visual=str(data.get("fallback_visual") or ""),
        export_gate=str(data.get("export_gate") or "review_required"),
        speaker_goal=str(data.get("speaker_goal") or ""),
        speaker_notes=str(data.get("speaker_notes") or data.get("speech_script") or data.get("script") or ""),
        main_script=str(data.get("main_script") or ""),
        sub_script=str(data.get("sub_script") or ""),
        transition=str(data.get("transition") or ""),
        stage_mode=str(data.get("stage_mode") or ""),
        time_budget_sec=_optional_int(data.get("time_budget_sec")),
        execution=dict(data.get("execution") or {}),
        source=str(data.get("source") or "edited"),
        quality_flags=_coerce_list(data.get("quality_flags")),
    )


def parse_slide_content_plan(markdown: str) -> list[PageContentCard]:
    rows = _parse_markdown_table(markdown)
    cards: list[PageContentCard] = []
    if rows:
        for fallback_index, row in enumerate(rows, start=1):
            page = _optional_int(row.get("page")) or fallback_index
            required_assets = _split_assets(row.get("required_assets") or row.get("asset_refs") or "")
            core_sentence = _clean(
                row.get("page_core_sentence")
                or row.get("core_sentence")
                or row.get("core_message")
                or ""
            )
            visible_content = _clean(
                row.get("visible_content")
                or row.get("visible_points")
                or row.get("page_text")
                or core_sentence
            )
            visual_scene = _clean(
                row.get("visual_scene")
                or row.get("visual_intent")
                or row.get("main_visual")
                or row.get("main_visual_type")
                or ""
            )
            card = PageContentCard(
                page=page,
                page_type=_clean(row.get("page_type") or "content"),
                section=_clean(row.get("section") or ""),
                formal_title=_clean(row.get("formal_title") or row.get("title") or f"第 {page} 页"),
                core_sentence=core_sentence,
                visible_content=visible_content,
                main_visual={
                    "type": _clean(row.get("main_visual_type") or row.get("visual_type") or "generated_image"),
                    "asset_source": "uploaded" if "[[ASSET:" in " ".join(required_assets) else "generated",
                    "asset_status": _clean(row.get("asset_status") or "missing"),
                    "visual_scene": visual_scene,
                    "fallback": _clean(row.get("fallback_visual") or ""),
                    "export_rule": _clean(row.get("export_gate") or "review_required"),
                },
                required_assets=required_assets,
                asset_status=_clean(row.get("asset_status") or _infer_asset_status(required_assets)),
                fallback_visual=_clean(row.get("fallback_visual") or ""),
                export_gate=_clean(row.get("export_gate") or "review_required"),
                speaker_goal=_clean(row.get("speaker_goal") or ""),
            )
            cards.append(card)
    if not cards:
        cards = _parse_loose_plan(markdown)
    return normalize_cards(cards)


def cards_from_manuscript(manuscript: str) -> list[PageContentCard]:
    cards: list[PageContentCard] = []
    for index, page in enumerate(split_manuscript_pages(manuscript), start=1):
        fields = _private_fields(page)
        required_assets = _split_assets(fields.get("required_assets", ""))
        card = PageContentCard(
            page=index,
            page_type=extract_page_type(page),
            section=fields.get("section", ""),
            formal_title=fields.get("formal_title") or fields.get("title") or page_title(page),
            core_sentence=fields.get("page_core_sentence", ""),
            visible_content=fields.get("visible_content", ""),
            page_role=fields.get("page_role", ""),
            judge_focus=fields.get("judge_focus", ""),
            story_role=fields.get("story_role", ""),
            main_visual=_parse_kv_block(fields.get("main_visual", "")),
            primary_visual=_parse_kv_block(fields.get("primary_visual", "")),
            required_assets=required_assets,
            asset_status=fields.get("asset_status") or _infer_asset_status(required_assets),
            fallback_visual=fields.get("fallback_visual", ""),
            export_gate=fields.get("export_gate", "review_required"),
            speaker_goal=fields.get("speaker_goal", ""),
            speaker_notes=fields.get("speaker_notes", ""),
            main_script=fields.get("main_script", ""),
            sub_script=fields.get("sub_script", ""),
            transition=fields.get("transition", ""),
            stage_mode=fields.get("stage_mode", ""),
            time_budget_sec=_optional_int(fields.get("time_budget_sec")),
            execution={
                "display_target": fields.get("display_target", ""),
                "speaker_role": fields.get("speaker_role", ""),
                "operator_role": fields.get("operator_role", ""),
                "operator_action": fields.get("operator_action", ""),
                "expected_screen_state": fields.get("expected_screen_state", ""),
                "fallback_plan": fields.get("fallback_plan", ""),
                "module_flow": fields.get("module_flow", ""),
                "acceptance_signal": fields.get("acceptance_signal", ""),
                "command_cue": fields.get("command_cue", ""),
            },
            source="manuscript",
        )
        cards.append(card)
    return normalize_cards(cards)


def cards_to_manuscript(cards: list[PageContentCard] | list[dict[str, Any]]) -> str:
    normalized = normalize_cards([
        card if isinstance(card, PageContentCard) else card_from_dict(card, index + 1)
        for index, card in enumerate(cards)
    ])
    pages: list[str] = []
    for index, card in enumerate(normalized):
        page_type = _normalize_page_type(card.page_type, card.page, len(normalized))
        heading = card.formal_title or f"第 {card.page} 页"
        core = card.core_sentence.strip()
        visible = card.visible_content.strip() or core or _fallback_visible_content(card)
        speaker_notes = card.speaker_notes.strip()
        next_title = (
            normalized[index + 1].formal_title
            if index + 1 < len(normalized)
            else "结束页致谢"
        )
        exec_fields = dict(card.execution or {})
        lines = [
            f"<!-- page_type: {page_type} -->",
            f"# {heading}",
        ]
        if core:
            lines.append(f"**{core}**")
        lines.append(visible)
        lines.extend(
            [
                f"page: {card.page}",
                f"section: {card.section}",
                f"formal_title: {heading}",
                f"page_core_sentence: {core}",
                f"visible_content: {visible}",
                f"page_role: {card.page_role or 'content'}",
                f"judge_focus: {card.judge_focus or core or heading}",
                f"story_role: {card.story_role or _default_story_role(card)}",
                f"contestant_intent: {exec_fields.get('contestant_intent') or f'讲清「{core or heading}」'}",
                f"audience_takeaway: {exec_fields.get('audience_takeaway') or core or heading}",
                "visual_pattern:",
                f"  pattern_id: {exec_fields.get('visual_pattern_id') or _default_pattern_id(card)}",
                f"  why: {exec_fields.get('visual_pattern_why') or '匹配本页证明对象与主视觉类型'}",
                f"next_slide_bridge: {exec_fields.get('next_slide_bridge') or f'自然过渡到「{next_title}」'}",
                "main_visual:",
                *_dict_lines(card.main_visual or _default_main_visual(card)),
                f"visual_asset_plan: {exec_fields.get('visual_asset_plan') or _default_visual_asset_plan(card)}",
                f"required_assets: {_join_assets(card)}",
                f"asset_status: {card.asset_status}",
                f"fallback_visual: {card.fallback_visual or '缺少真实材料时使用 SVG 示意或验证方法说明'}",
                f"asset_gap_handling: {exec_fields.get('asset_gap_handling') or _default_asset_gap_handling(card)}",
                f"export_gate: {card.export_gate or 'review_required'}",
                f"speaker_goal: {card.speaker_goal or core or heading}",
                f"speaker_notes: {speaker_notes}",
                f"main_script: {card.main_script or core}",
                f"sub_script: {card.sub_script or visible[:120]}",
                f"transition: {card.transition or f'接下来看「{next_title}」'}",
                "proof_object:",
                *_dict_lines(
                    {
                        "type": card.primary_visual.get("type") or card.main_visual.get("type") or "support_object",
                        "source": _join_assets(card) or card.asset_status,
                        "must_be_visible": "true" if card.asset_status == "provided" else "false",
                        "fallback": card.fallback_visual or "缺少真实材料时使用验证方法或 SVG 示意",
                    }
                ),
                "primary_visual:",
                *_dict_lines(card.primary_visual or _default_primary_visual(card)),
                f"stage_mode: {card.stage_mode or exec_fields.get('stage_mode') or 'ppt_explain'}",
                f"time_budget_sec: {card.time_budget_sec or exec_fields.get('time_budget_sec') or 80}",
                f"display_target: {exec_fields.get('display_target') or 'main_screen'}",
                f"speaker_role: {exec_fields.get('speaker_role') or '主讲选手'}",
                f"operator_role: {exec_fields.get('operator_role') or _default_operator_role(card)}",
                f"operator_action: {exec_fields.get('operator_action') or '按本页演示步骤操作或切换画面'}",
                f"expected_screen_state: {exec_fields.get('expected_screen_state') or core or heading}",
                f"fallback_plan: {exec_fields.get('fallback_plan') or '现场异常时切换预置截图/录屏，说明排查与复测步骤后继续'}",
                f"module_flow: {exec_fields.get('module_flow') or '讲解 → 展示主视觉 → 点出结果 → 转场'}",
                f"acceptance_signal: {exec_fields.get('acceptance_signal') or '评委能复述本页核心句'}",
                f"command_cue: {exec_fields.get('command_cue') or '请切换到本页主视觉'}",
            ]
        )
        # Preserve any extra execution keys not already written.
        written = {
            "display_target", "speaker_role", "operator_role", "operator_action",
            "expected_screen_state", "fallback_plan", "module_flow", "acceptance_signal",
            "command_cue", "contestant_intent", "audience_takeaway", "visual_pattern_id",
            "visual_pattern_why", "next_slide_bridge", "visual_asset_plan", "asset_gap_handling",
            "stage_mode", "time_budget_sec",
        }
        for key, value in exec_fields.items():
            if key in written or value in (None, ""):
                continue
            lines.append(f"{key}: {value}")
        pages.append("\n".join(line for line in lines if line is not None).strip())
    return "\n\n---\n\n".join(pages)


def normalize_cards(cards: list[PageContentCard]) -> list[PageContentCard]:
    total = len(cards)
    normalized: list[PageContentCard] = []
    for index, card in enumerate(cards, start=1):
        card.page = index
        card.page_type = _normalize_page_type(card.page_type, index, total)
        card.formal_title = _clean(card.formal_title) or f"第 {index} 页"
        card.core_sentence = _clean(card.core_sentence)
        card.visible_content = _clean(card.visible_content)
        if not card.visible_content and card.core_sentence:
            card.visible_content = card.core_sentence
        card.required_assets = _split_assets(card.required_assets)
        if index == 1:
            visual_scene = str((card.main_visual or {}).get("visual_scene") or "").strip()
            card.required_assets = []
            card.asset_ids = []
            card.figure_ids = []
            card.asset_status = "not_required"
            card.main_visual = {
                **(card.main_visual or {}),
                "type": "generated_image",
                "asset_source": "none",
                "asset_status": "not_required",
                "visual_scene": visual_scene or "完整封面视觉：大标题、项目定位、关键词、科技农业背景、抽象几何与光效。",
                "fallback": "封面不绑定上传素材，但必须由 image2 生成完整封面视觉。",
                "export_rule": "formal_ok",
            }
            card.fallback_visual = card.fallback_visual or "封面不绑定上传素材，但必须由 image2 生成完整封面视觉。"
            card.export_gate = "formal_ok"
        card.asset_ids = sorted(set([*card.asset_ids, *ASSET_TOKEN_RE.findall(" ".join(card.required_assets))]))
        card.figure_ids = sorted(set([*card.figure_ids, *FIG_TOKEN_RE.findall(" ".join(card.required_assets))]))
        card.asset_status = _normalize_asset_status(card.asset_status, card.asset_ids, card.required_assets)
        if not card.main_visual:
            card.main_visual = _default_main_visual(card)
        else:
            card.main_visual.setdefault("asset_status", card.asset_status)
        if not card.primary_visual:
            card.primary_visual = _default_primary_visual(card)
        if not card.story_role:
            card.story_role = _default_story_role(card)
        if not card.stage_mode:
            card.stage_mode = "ppt_explain"
        if card.time_budget_sec is None:
            card.time_budget_sec = 80
        if not card.fallback_visual:
            card.fallback_visual = "缺少真实材料时使用 SVG 示意或验证方法说明"
        if not card.speaker_goal:
            card.speaker_goal = card.core_sentence or card.formal_title
        # Editable plan_only often produces thin light-plan rows. Fill execution
        # contract defaults so render_from_cards manuscript is gate-shaped and
        # the card editor has concrete values to refine (not blank fields).
        card.execution = _ensure_execution_defaults(card)
        card.material_policy = _material_policy(card)
        card.quality_flags = _quality_flags(card)
        normalized.append(card)
    return _dedupe_near_identical_cards(normalized)


def _dedupe_near_identical_cards(cards: list[PageContentCard]) -> list[PageContentCard]:
    """Soft-differentiate pages that share the same title/core so export gate
    and storyline quality do not collapse on homogeneous neighbors.
    """
    seen: dict[str, int] = {}
    for card in cards:
        key = f"{_clean(card.formal_title)}|{_clean(card.core_sentence)}"
        if not key or key == "|":
            continue
        count = seen.get(key, 0) + 1
        seen[key] = count
        if count <= 1:
            continue
        # Keep content but force a distinct proof angle in title/core.
        suffix = f"（证明点{count}）"
        if suffix not in card.formal_title:
            card.formal_title = f"{card.formal_title}{suffix}"
        if card.core_sentence and suffix not in card.core_sentence:
            card.core_sentence = f"{card.core_sentence}{suffix}"
        if "near_duplicate_soft_fix" not in (card.quality_flags or []):
            card.quality_flags = list(card.quality_flags or []) + ["near_duplicate_soft_fix"]
        exec_fields = dict(card.execution or {})
        exec_fields["contestant_intent"] = (
            exec_fields.get("contestant_intent")
            or f"从不同角度讲清「{card.core_sentence or card.formal_title}」"
        )
        card.execution = exec_fields
    return cards


def _default_story_role(card: PageContentCard) -> str:
    text = f"{card.section} {card.formal_title} {card.core_sentence}".lower()
    if card.page_type == "cover" or card.page <= 2:
        return "raise_problem" if card.page > 1 else "reveal_solution"
    if any(token in text for token in ("成果", "价值", "推广", "就业", "应用")):
        return "land_value"
    if any(token in text for token in ("创新", "对比", "亮点")):
        return "extract_innovation"
    if any(token in text for token in ("测试", "数据", "复核", "结果")):
        return "verify_result"
    if any(token in text for token in ("实操", "演示", "联动", "处置", "工单")):
        return "prove_flow"
    if any(token in text for token in ("代码", "接口", "架构", "算法", "机制")):
        return "unpack_mechanism"
    if any(token in text for token in ("方案", "系统", "总体")):
        return "reveal_solution"
    return "unpack_mechanism"


def _default_pattern_id(card: PageContentCard) -> str:
    text = f"{card.section} {card.formal_title} {card.core_sentence}"
    if card.page_type == "cover" or card.page == 1:
        return "competition_cover_identity"
    if card.page == 2 or "目录" in text or "大纲" in text:
        return "field_route_agenda"
    if any(token in text for token in ("政策", "背景", "痛点", "市场")):
        return "policy_problem_project_fit"
    if any(token in text for token in ("实操", "演示", "联动", "预警")):
        return "live_demo_input_action_output_evidence"
    if any(token in text for token in ("代码", "接口", "算法")):
        return "code_walkthrough_with_output"
    if any(token in text for token in ("测试", "数据", "成果")):
        return "test_record_dashboard"
    if any(token in text for token in ("团队", "分工")):
        return "role_task_skill_output"
    if any(token in text for token in ("架构", "方案", "系统")):
        return "system_runs_like_this"
    return "support_material_wall"


def _default_operator_role(card: PageContentCard) -> str:
    text = f"{card.section} {card.formal_title}"
    if any(token in text for token in ("实操", "演示", "设备", "联动")):
        return "操作选手"
    return "主讲选手"


def _default_visual_asset_plan(card: PageContentCard) -> str:
    assets = _join_assets(card)
    if assets:
        return f"优先使用已登记素材：{assets}；缺项用 SVG 示意补位"
    scene = str((card.main_visual or {}).get("visual_scene") or "").strip()
    if scene:
        return f"主视觉场景：{scene}；无上传素材时用示意图形表达"
    return "以主视觉对象承载本页证明点；无真实截图时用示意/方法说明"


def _default_asset_gap_handling(card: PageContentCard) -> str:
    if card.asset_status in {"provided", "not_required"}:
        return "素材已就绪或本页不强制真实素材"
    if card.export_gate == "blocked_until_assets":
        return "关键真实素材缺失，正式导出前必须补采；预览可用示意"
    return "缺素材时降级为验证方法/示意，并在卡片中标记待补采"


def _ensure_execution_defaults(card: PageContentCard) -> dict[str, Any]:
    exec_fields = dict(card.execution or {})
    defaults = {
        "display_target": "main_screen",
        "speaker_role": "主讲选手",
        "operator_role": _default_operator_role(card),
        "operator_action": "按本页演示步骤操作或切换画面",
        "expected_screen_state": card.core_sentence or card.formal_title,
        "fallback_plan": "现场异常时切换预置截图/录屏，说明排查与复测步骤后继续",
        "module_flow": "讲解 → 展示主视觉 → 点出结果 → 转场",
        "acceptance_signal": "评委能复述本页核心句",
        "command_cue": "请切换到本页主视觉",
        "contestant_intent": f"讲清「{card.core_sentence or card.formal_title}」",
        "audience_takeaway": card.core_sentence or card.formal_title,
        "visual_pattern_id": _default_pattern_id(card),
        "visual_pattern_why": "匹配本页证明对象与主视觉类型",
        "next_slide_bridge": "自然进入下一页证明点",
        "visual_asset_plan": _default_visual_asset_plan(card),
        "asset_gap_handling": _default_asset_gap_handling(card),
    }
    for key, value in defaults.items():
        if not str(exec_fields.get(key) or "").strip():
            exec_fields[key] = value
    return exec_fields


def _parse_markdown_table(markdown: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = _split_table_row(lines[0])
    if not header or "page" not in [item.lower() for item in header]:
        return []
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        cells = _split_table_row(line)
        if not cells or all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells):
            continue
        if len(cells) < len(header):
            cells.extend([""] * (len(header) - len(cells)))
        rows.append({header[index].strip(): cells[index].strip() for index in range(len(header))})
    return rows


def _split_table_row(line: str) -> list[str]:
    raw = line.strip().strip("|")
    reader = csv.reader(StringIO(raw), delimiter="|", escapechar="\\")
    try:
        return [cell.strip() for cell in next(reader)]
    except StopIteration:
        return []


def _parse_loose_plan(markdown: str) -> list[PageContentCard]:
    cards: list[PageContentCard] = []
    page_blocks = re.split(r"(?im)^\s*(?:#{1,4}\s*)?(?:page|slide|第)\s*(\d+)\s*(?:页)?[^\n]*$", markdown)
    if len(page_blocks) <= 1:
        return cards
    iterator = iter(page_blocks[1:])
    for page_text, block in zip(iterator, iterator):
        page = _optional_int(page_text) or len(cards) + 1
        title = _first_nonempty_line(block) or f"第 {page} 页"
        cards.append(
            PageContentCard(
                page=page,
                formal_title=_clean(title),
                core_sentence=_field_like(block, "page_core_sentence") or _field_like(block, "core_sentence"),
                visible_content=_field_like(block, "visible_content") or _clean(block[:180]),
                required_assets=_split_assets(_field_like(block, "required_assets")),
                source="loose_plan",
            )
        )
    return cards


def _private_fields(page: str) -> dict[str, str]:
    field_re = re.compile(r"(?ms)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)(?=^\s*[A-Za-z_][A-Za-z0-9_]*\s*:|\Z)")
    return {match.group(1): match.group(2).strip() for match in field_re.finditer(page)}


def _parse_kv_block(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in value.splitlines():
        match = re.match(r"\s*[-*]?\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+?)\s*$", line)
        if match:
            result[match.group(1)] = match.group(2).strip()
    if not result and value.strip():
        for part in re.split(r";|；", value):
            match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+?)\s*$", part)
            if match:
                result[match.group(1)] = match.group(2).strip()
    return result


def _infer_storyline_phases(cards: list[PageContentCard]) -> list[dict[str, Any]]:
    buckets = [
        ("项目成立", 1, max(2, len(cards) // 5), "讲清背景、痛点、政策/市场依据和项目为什么值得做。"),
        ("研发方案", max(3, len(cards) // 5 + 1), max(4, len(cards) * 2 // 5), "讲清系统方案、技术架构、关键机制和创新路径。"),
        ("现场证明", max(5, len(cards) * 2 // 5 + 1), max(6, len(cards) * 3 // 5), "围绕一次真实事件跑通输入、判断、处置、记录、复核。"),
        ("结果验证", max(7, len(cards) * 3 // 5 + 1), max(8, len(cards) * 4 // 5), "用测试、运行记录、支撑材料和风险预案证明可落地。"),
        ("价值推广", max(9, len(cards) * 4 // 5 + 1), len(cards), "回到企业、学校、团队、就业和行业推广价值。"),
    ]
    phases = []
    for name, start, end, purpose in buckets:
        start = max(1, min(start, len(cards) or 1))
        end = max(start, min(end, len(cards) or start))
        phases.append({"name": name, "page_range": [start, end], "purpose": purpose})
    return phases


def _ensure_card_count(cards: list[PageContentCard], count: int) -> list[PageContentCard]:
    if not count or len(cards) >= count:
        return cards
    next_cards = list(cards)
    for index in range(len(next_cards) + 1, count + 1):
        next_cards.append(
            PageContentCard(
                page=index,
                formal_title=f"第 {index} 页内容待确认",
                core_sentence="本页需补充正式核心句。",
                visible_content="请补充本页可见正文、主视觉和支撑材料。",
                source="local_placeholder",
                quality_flags=["missing_llm_plan_row"],
            )
        )
    return next_cards


def _normalize_page_type(page_type: str, page: int, total: int) -> str:
    value = (page_type or "").strip().lower()
    if page == 1:
        return "cover"
    if total and page == total:
        return "ending"
    if value in {"cover", "chapter", "toc", "content", "ending"}:
        if value == "cover":
            return "content"
        if value == "ending":
            return "content"
        return value
    return "content"


def _normalize_asset_status(status: str, asset_ids: list[str], required_assets: list[str]) -> str:
    value = (status or "").strip().lower()
    if asset_ids or any("[[ASSET:" in item for item in required_assets):
        return "provided"
    if value in {"provided", "missing", "needs_svg", "generated", "public_source", "method_only", "not_required"}:
        return value
    if "缺" in value or "待" in value:
        return "missing"
    return "missing"


def _infer_asset_status(required_assets: list[str]) -> str:
    return "provided" if any("[[ASSET:" in item for item in required_assets) else "missing"


def _material_policy(card: PageContentCard) -> str:
    visual_type = str(card.main_visual.get("type") or "")
    if card.asset_status == "provided" and card.asset_ids:
        return "must_render_real_image"
    if visual_type in {"screenshot", "real_image", "product_ui", "chart", "certificate", "material_photo"}:
        return "real_asset_required_or_regenerate"
    return "svg_allowed_if_no_real_asset"


def _quality_flags(card: PageContentCard) -> list[str]:
    flags = list(card.quality_flags or [])
    if not card.formal_title or "待确认" in card.formal_title:
        flags.append("missing_formal_title")
    if not card.core_sentence:
        flags.append("missing_core_sentence")
    if len(card.visible_content) < 12:
        flags.append("thin_visible_content")
    if card.asset_status == "provided" and not card.asset_ids:
        flags.append("provided_without_asset_id")
    return sorted(set(flags))


def _default_main_visual(card: PageContentCard) -> dict[str, str]:
    return {
        "type": "real_image" if card.asset_ids else "svg_diagram",
        "asset_source": "uploaded" if card.asset_ids else "generated",
        "asset_status": card.asset_status,
        "fallback": card.fallback_visual or "缺少真实素材时使用结构化 SVG 示意",
        "export_rule": card.export_gate or "review_required",
    }


def _default_primary_visual(card: PageContentCard) -> dict[str, str]:
    visual_type = str(card.main_visual.get("type") or "svg_diagram")
    if visual_type in {"screenshot", "product_ui"}:
        primary_type = "live_demo_board"
    elif visual_type in {"chart"}:
        primary_type = "test_dashboard"
    elif visual_type in {"real_image", "material_photo", "certificate"}:
        primary_type = "support_material_flow"
    else:
        primary_type = "solution_map"
    return {
        "type": primary_type,
        "purpose": card.core_sentence or card.formal_title,
        "required_elements": card.visible_content[:120],
        "visual_weight": "60%-75%",
        "forbidden_layouts": "不要用等大信息卡片替代主视觉对象",
    }


def _image2_visual_scene(card: PageContentCard) -> str:
    main_visual = card.main_visual or {}
    visual_scene = str(main_visual.get("visual_scene") or "").strip()
    if visual_scene:
        return visual_scene
    primary = card.primary_visual or {}
    primary_hint = "；".join(
        str(primary.get(key) or "").strip()
        for key in ("purpose", "required_elements")
        if str(primary.get(key) or "").strip()
    )
    if primary_hint:
        return primary_hint
    return card.visible_content or card.core_sentence or card.formal_title


def _image2_layout_intent(card: PageContentCard) -> str:
    primary = card.primary_visual or {}
    main_visual = card.main_visual or {}
    visual_type = str(primary.get("type") or main_visual.get("type") or "").strip()
    weight = str(primary.get("visual_weight") or "").strip()
    forbidden = str(primary.get("forbidden_layouts") or "").strip()
    required = str(primary.get("required_elements") or "").strip()
    parts = []
    if visual_type:
        parts.append(f"主视觉类型：{visual_type}")
    if weight:
        parts.append(f"视觉占比：{weight}")
    if required:
        parts.append(f"必须呈现：{required}")
    if forbidden:
        parts.append(f"避免：{forbidden}")
    if not parts:
        if card.asset_ids:
            return "以真实素材为主视觉，旁边用短要点和来源说明辅助。"
        return "以清晰标题、核心句、短要点和结构化图示组成完整 PPT 页面。"
    return "；".join(parts)


def _image2_evidence_focus(card: PageContentCard) -> str:
    primary = card.primary_visual or {}
    focus = "；".join(
        part
        for part in (
            card.judge_focus.strip(),
            card.page_role.strip(),
            card.story_role.strip(),
            str(primary.get("purpose") or "").strip(),
        )
        if part
    )
    if focus:
        return focus
    if card.asset_ids:
        return "用真实上传素材证明本页结论，而不是只做概念性说明。"
    return "用清晰的结构、流程或数据化表达支撑本页核心结论。"


def _image2_prompt_notes(card: PageContentCard) -> str:
    notes: list[str] = []
    if card.page == 1:
        notes.append("封面不使用上传素材，但必须生成完整封面视觉。")
    if card.asset_ids:
        notes.append("真实素材可作为页面主视觉或局部证据图使用，不要把 asset_id 印到页面上。")
    if card.material_policy == "must_render_real_image":
        notes.append("页面必须优先呈现真实素材，不能降级成纯示意图。")
    if card.fallback_visual:
        notes.append(f"素材不足时的表达边界：{card.fallback_visual}")
    return "；".join(notes)


def _fallback_visible_content(card: PageContentCard) -> str:
    visual_scene = str((card.main_visual or {}).get("visual_scene") or "").strip()
    if card.core_sentence:
        return card.core_sentence
    if visual_scene:
        return visual_scene
    return f"围绕“{card.formal_title}”提炼2到4条正式汇报要点。"


def _dict_lines(data: dict[str, Any]) -> list[str]:
    return [f"  {key}: {value}" for key, value in data.items() if value not in (None, "")]


def _join_assets(card: PageContentCard) -> str:
    items = list(card.required_assets or [])
    existing_asset_ids = set(ASSET_TOKEN_RE.findall("；".join(items)))
    for asset_id in card.asset_ids:
        if asset_id not in existing_asset_ids:
            items.append(f"[[ASSET:{asset_id}]]")
    return "；".join(items)


def _field_like(text: str, name: str) -> str:
    match = re.search(rf"(?ims)^\s*{re.escape(name)}\s*:\s*(.*?)(?=^\s*[A-Za-z_][A-Za-z0-9_]*\s*:|\Z)", text)
    return _clean(match.group(1)) if match else ""


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip(" #|")
        if stripped:
            return stripped
    return ""


def _split_assets(value: Any) -> list[str]:
    if isinstance(value, list):
        text = "；".join(str(item) for item in value)
    else:
        text = str(value or "")
    parts = [part.strip(" `") for part in re.split(r"[；;,\n]+", text) if part.strip(" `")]
    return parts[:8]


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return _split_assets(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("<br>", "\n").replace("<br/>", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" |`")
