"""Roadshow-specific fact, asset, and export quality gates.

The academic paper path can safely use extracted figures as primary assets
because paper figures are usually the work's visual support material.  Competition
roadshow decks are different: uploaded PDFs often contain tables, schedules,
role sheets, or page crops that should be converted into designed layouts
instead of being pasted as images.  This module keeps those roadshow rules
separate from the original paper-ppt-agent flow.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.parser.paper_model import ParsedPaper, PaperFigure
from backend.orchestrator.roadshow_content_contract import (
    format_visible_text_violations,
    scan_svg_visible_text,
)
from backend.orchestrator.roadshow_reference_patterns import PATTERN_IDS, normalize_pattern_id


PROJECT_TITLE_PATTERNS = (
    re.compile(r"locked_project_title\s*:\s*([^\n<>]{6,80})"),
    re.compile(r"(?:项目名称|作品名称|系统名称)\s*[：:]\s*([^\n，。；;]{6,80})"),
    re.compile(r"《([^》]{6,80})》"),
    re.compile(r"[“\"]([^”\"]{6,80}(?:系统|平台|方案|装置|作品))[”\"]"),
)

BAD_PROJECT_TITLE_TERMS = (
    "团队岗位分工",
    "团队与岗位分工",
    "团队分工",
    "岗位分工",
    "岗位职责",
    "任务分工",
    "人员分工",
    "上传清单",
    "素材包说明",
    "素材包图片预览",
    "需求调研纪要",
    "研发历程记录",
    "运行验证记录",
    "应用反馈汇总",
    "成果材料清单",
    "接口与数据字典",
    "政策依据",
    "政策文件",
    "文档材料",
    "latex_src",
    "project_zip",
)

METRIC_ROW_RE = re.compile(
    r"(?P<name>[\u4e00-\u9fffA-Za-z0-9（）()/+\-]{2,30})"
    r"[：:\s|]+"
    r"(?P<value>[<>≥≤]?\s*[+\-]?\d+(?:\.\d+)?\s*(?:%|秒|s|min|分钟|条|台|次|份|人)?)"
)

FIG_TOKEN_RE = re.compile(r"\[\[FIG:([A-Za-z0-9_.-]+)\]\]")
ASSET_TOKEN_RE = re.compile(r"\[\[ASSET:([A-Za-z0-9_.-]+)\]\]")
IMAGE_HREF_RE = re.compile(r"<image\b[^>]*\bhref=[\"']([^\"']+)[\"']", re.IGNORECASE)

INVALID_WEB_MARKERS = (
    "我目前没有联网搜索工具",
    "无法实时搜索互联网",
    "没有联网搜索工具",
    "作为 ai 语言模型",
    "作为AI语言模型",
    "请使用搜索引擎",
    "很抱歉",
)

PLACEHOLDER_PATTERNS = (
    re.compile(r"\[[^\]]*(?:团队|赛事|日期|联系方式|学校|姓名|电话|邮箱)[^\]]*\]"),
    re.compile(r"(?:团队名称|团队编号|联系方式|联系电话|邮箱地址|学校名称|姓名)"),
)

FABRICATED_LOOKING_PATTERNS = (
    re.compile(r"\bRPT-\d{4}[-\d]*\b", re.IGNORECASE),
    re.compile(r"\b20\d{2}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\b"),
)

EVIDENCE_PAGE_HINTS = ("实操", "支撑", "材料", "数据", "测试", "指标", "成果", "审计", "工单")
STANDALONE_PREP_VISIBLE_TERMS = (
    "现场实操演示准备",
    "演示环境与操作脚本已就绪",
    "演示环境已准备",
    "操作脚本已就绪",
    "演示准备状态",
    "播放录屏",
)
ROADSHOW_EXECUTION_FIELDS = (
    "stage_mode:",
    "display_target:",
    "time_budget_sec:",
    "speaker_role:",
    "operator_role:",
    "operator_action:",
    "expected_screen_state:",
    "fallback_plan:",
    "module_flow:",
    "acceptance_signal:",
    "command_cue:",
)
ROADSHOW_CONTESTANT_FIELDS = (
    "contestant_intent:",
    "audience_takeaway:",
    "proof_object:",
    "visual_pattern:",
    "next_slide_bridge:",
    "story_role:",
)
ROADSHOW_CONTENT_PLAN_FIELDS = (
    "page_core_sentence:",
    "visible_content:",
    "main_visual:",
    "visual_asset_plan:",
    "required_assets:",
    "asset_status:",
    "fallback_visual:",
    "asset_gap_handling:",
    "export_gate:",
    "main_script:",
    "sub_script:",
    "transition:",
)
CODE_RESTORATION_HINTS = (
    "代码还原",
    "关键代码",
    "代码讲解",
    "函数",
    "接口",
    "协议",
    "配置",
    "算法逻辑",
    "code_walkthrough",
)
SOURCE_HINTS = (
    "来源",
    "source",
    "验证",
    "测试记录",
    "用户反馈",
    "基地",
    "企业",
    "调研",
    "联网",
    "公开",
    "依据",
    "来自",
)
RESULT_PAGE_HINTS = ("成果", "价值", "应用", "推广", "经济", "降本", "提升", "节约", "缩短")


@dataclass
class LockedFacts:
    """Facts extracted from source material that downstream agents must not rewrite."""

    project_title: str = ""
    verified_metrics: list[dict[str, str]] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        lines = ["## Locked Roadshow Facts"]
        if self.project_title:
            lines.append(f"- locked_project_title: {self.project_title}")
            lines.append("- 后续所有页面、页脚、design spec 项目名必须使用 locked_project_title，不得改写、缩写替换或重新命名。")
        if self.verified_metrics:
            lines.append("- verified_metrics:")
            for item in self.verified_metrics[:16]:
                source = item.get("source") or "source material"
                lines.append(f"  - {item.get('name', '')}: {item.get('value', '')}；source={source}")
            lines.append("- 所有 KPI/达成数据只能来自 verified_metrics；没有来源的数据必须写“待补充/待实测”。")
        else:
            lines.append("- verified_metrics: none; 不得编造 KPI 达成值。")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_title": self.project_title,
            "verified_metrics": list(self.verified_metrics),
        }


def extract_locked_facts(material_analysis: str, paper: ParsedPaper) -> LockedFacts:
    """Extract title and obvious metrics from the roadshow material analysis."""
    title = _extract_project_title(material_analysis) or _extract_project_title(paper.to_markdown())
    if not _usable_title(title):
        title = paper.title.strip() if _usable_title(paper.title) else ""
    metrics = _extract_metrics(material_analysis)
    return LockedFacts(project_title=title, verified_metrics=metrics)


def _usable_title(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    if len(text) < 6:
        return False
    if text in {"摘要", "目录", "说明书"}:
        return False
    lowered = text.lower()
    if lowered in {"latex_src", "project_zip", "prepared_materials"}:
        return False
    if any(term in text for term in BAD_PROJECT_TITLE_TERMS):
        return False
    if re.fullmatch(r"\d+[_\-].+", text):
        return False
    if text.endswith((".docx", ".doc", ".pdf", ".pptx", ".zip", ".md", ".csv", ".xlsx")):
        return False
    return True


def _extract_project_title(text: str) -> str:
    for pattern in PROJECT_TITLE_PATTERNS:
        match = pattern.search(text)
        if match:
            title = re.sub(r"[，。；;].*$", "", match.group(1)).strip(" #*`：: \t")
            if _usable_title(title):
                return title
    for line in text.splitlines():
        clean = line.strip(" #*`：: \t")
        if clean.endswith(("系统", "平台", "方案", "装置", "作品")) and _usable_title(clean):
            return clean[:80]
    return ""


def _extract_metrics(text: str) -> list[dict[str, str]]:
    metrics: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in text.splitlines():
        if not any(token in line for token in ("指标", "准确", "成功", "延迟", "样本", "工单", "设备", "耗时", "补传", "闭环")):
            continue
        for match in METRIC_ROW_RE.finditer(line):
            name = match.group("name").strip(" |-*")
            value = re.sub(r"\s+", "", match.group("value"))
            key = (name, value)
            if key in seen or len(name) < 2:
                continue
            seen.add(key)
            metrics.append({"name": name, "value": value, "source": "uploaded_material"})
    return metrics[:24]


def valid_external_findings(findings: list[Any]) -> list[Any]:
    """Drop model apologies or empty web-search pseudo-results."""
    valid: list[Any] = []
    for item in findings:
        title = str(getattr(item, "title", "") or "").strip()
        abstract = str(getattr(item, "abstract", "") or "").strip()
        url = str(getattr(item, "url", "") or "").strip()
        combined = f"{title}\n{abstract}".lower()
        if len(title) < 4 and len(abstract) < 20:
            continue
        if any(marker.lower() in combined for marker in INVALID_WEB_MARKERS):
            continue
        if getattr(item, "source", "") == "web" and not url:
            continue
        valid.append(item)
    return valid


def classify_roadshow_figure(fig_or_record: PaperFigure | dict[str, Any]) -> dict[str, Any]:
    """Return semantic metadata and roadshow permission for an extracted image."""
    if isinstance(fig_or_record, dict):
        caption = str(fig_or_record.get("caption") or "")
        extraction_method = str(fig_or_record.get("extraction_method") or "")
        path = Path(str(fig_or_record.get("path") or ""))
        review_flags = list(fig_or_record.get("review_flags") or [])
    else:
        caption = fig_or_record.caption or ""
        extraction_method = fig_or_record.extraction_method or ""
        path = fig_or_record.path
        review_flags = list(fig_or_record.review_flags or [])

    text = f"{caption} {path.stem}".lower()
    semantic_type = "unknown"
    allowed = True
    reason = ""

    if "table_region" in extraction_method:
        semantic_type = "table_crop"
        allowed = False
        reason = "PDF table-region crop; convert to designed table/cards instead of pasting as a figure."
    if "page_level_fallback" in review_flags:
        semantic_type = "page_crop"
        allowed = False
        reason = "Page-level fallback crop is too risky for formal roadshow pages."
    if any(token in text for token in ("screenshot", "截图", "界面", "dashboard", "screen")):
        semantic_type = "screenshot"
        allowed = True
        reason = "Likely a system screenshot."
    elif any(token in text for token in ("架构", "architecture", "流程", "flow", "数据流")) and "table_region" not in extraction_method:
        semantic_type = "diagram"
        allowed = True
        reason = "Likely a diagram/flow asset."

    return {
        "semantic_type": semantic_type,
        "allowed_for_roadshow": allowed,
        "roadshow_reason": reason,
    }


def filter_roadshow_figure_inventory(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only figures that are safe to offer to roadshow strategist/executor."""
    filtered: list[dict[str, Any]] = []
    for rec in inventory:
        meta = classify_roadshow_figure(rec)
        enriched = {**rec, **meta}
        if enriched["allowed_for_roadshow"]:
            filtered.append(enriched)
    return filtered


def roadshow_figure_token_inventory_block(paper: ParsedPaper) -> str:
    """Prompt block listing only roadshow-safe figure tokens."""
    lines = [
        "## Roadshow-safe Figure Tokens",
        "",
        "Only use figure tokens listed here. PDF table crops, schedule tables, team-role tables, and page crops are intentionally excluded.",
        "If no listed token matches a needed screenshot/diagram, write `evidence_assets: 待补充` instead of inventing or reusing a wrong crop.",
        "",
    ]
    rows: list[str] = []
    for fig in paper.all_figures():
        if not getattr(fig, "available", False):
            continue
        meta = classify_roadshow_figure(fig)
        if not meta["allowed_for_roadshow"]:
            continue
        caption = (fig.caption or meta["semantic_type"] or "Figure").replace("\n", " ").strip()
        rows.append(f"| `[[FIG:{fig.fig_id}]]` | {caption} | {meta['semantic_type']} |")
    if not rows:
        lines.append("No roadshow-safe figure tokens are available. Do not use `[[FIG:...]]` in the manuscript.")
        return "\n".join(lines)
    lines.extend(["| Token | Caption | Type |", "| ----- | ------- | ---- |"])
    lines.extend(rows)
    return "\n".join(lines)


def remove_disallowed_figure_tokens(manuscript: str, paper: ParsedPaper) -> str:
    allowed = {
        fig.fig_id
        for fig in paper.all_figures()
        if getattr(fig, "available", False)
        and classify_roadshow_figure(fig)["allowed_for_roadshow"]
    }
    if not allowed:
        return FIG_TOKEN_RE.sub("待补充", manuscript)
    return FIG_TOKEN_RE.sub(lambda m: m.group(0) if m.group(1) in allowed else "待补充", manuscript)


def apply_locked_facts_to_manuscript(manuscript: str, facts: LockedFacts) -> str:
    if not facts.project_title:
        return manuscript
    pages = re.split(r"(?m)^---\s*$", manuscript)
    if not pages:
        return manuscript
    first = pages[0]
    if "locked_project_title:" not in first:
        first = first.replace(
            "\n",
            f"\n<!-- locked_project_title: {facts.project_title} -->\n",
            1,
        )
    pages[0] = first
    return "\n---\n".join(page.strip() for page in pages if page.strip())


def enforce_locked_title_in_design_spec(design_spec: str, facts: LockedFacts) -> str:
    title = facts.project_title.strip()
    if not title:
        return design_spec
    text = design_spec
    text = re.sub(r"^#\s+.+?\s+-\s+Design Spec\s*$", f"# {title} - Design Spec", text, flags=re.MULTILINE)
    text = re.sub(r"\|\s*\*\*Project Name\*\*\s*\|\s*[^|\n]+\|", f"| **Project Name** | {title} |", text)
    return text


def build_roadshow_strategist_guardrails(facts: LockedFacts) -> str:
    lines = [
        "\n## Roadshow Formal Guardrails",
        "- Treat this as a vocational-skills-competition roadshow deck, not an academic paper deck.",
        "- Do not create personal/school/contact placeholders. Avoid `[团队名称]`, `[学校]`, `[电话]`, `[邮箱]`, `[联系方式]`.",
        "- Do not fabricate KPI results, timestamps, report IDs, test dates, team identities, or data sources.",
        "- If support material is missing, mark it as `待补充` in planning text; do not invent screenshots.",
        "- Architecture, demo workflow, support materials, risk control and anonymous team roles are core page types.",
        "- Roadshow visible copy must not render the Chinese word `证据`; use 支撑材料、运行记录、验证结果、成果材料、资料来源 instead.",
        "- Make policy/news, market research, industry pain points, helped industries, economy, employment, school-enterprise cooperation and IP/cooperation value explicit when sources allow.",
        "- Use the participant-facing five-block narrative by default: 项目背景、研发历程、实施过程、创新设计、应用价值.",
        "- For each core module, preserve the skills-competition chain: 功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结.",
        "- Treat roadshow pages as live operation boards where useful: current step, screen state, operator action, material marker, fallback strip.",
        "- Every roadshow page must be designed around its `primary_visual` contract. The primary_visual is the page's main explanatory object, not decoration.",
        "- Do not downgrade technical/demo/support-material/result pages into pure card, list, or table pages. Cards may annotate the main visual, but must not become the main structure.",
        "- Map primary_visual.type to a concrete design: architecture_map/data_flow/rule_tree/support_material_flow/live_demo_board/code_explain_board/test_dashboard/result_dashboard/team_handoff/risk_fallback.",
        "- Hidden strategy fields such as judge_focus, scoring logic, manuscript JSON, page_role, command_cue, acceptance_signal, operator_role, fallback_plan must guide design only. They must not appear as visible slide copy.",
        "- Visible slide copy must not contain scoring/points language, command cues, operator-role labels, export-gate wording, draft-state wording, placeholders, evidence-gap labels, or the word 证据.",
        "- Result percentages, cost savings, cycle reductions, promotion counts, and cooperation numbers need explicit source labels or must be shown as 待补充来源.",
    ]
    if facts.project_title:
        lines.append(f"- Locked project title: `{facts.project_title}`. Use this exact title wherever a project title is needed.")
    if facts.verified_metrics:
        lines.append("- Verified metric values available for formal KPI pages:")
        for item in facts.verified_metrics[:12]:
            lines.append(f"  - {item.get('name', '')}: {item.get('value', '')}")
    else:
        lines.append("- No verified metric values are available; KPI pages should show targets or `待补充/待实测`, not achieved results.")
    return "\n".join(lines)


def evaluate_roadshow_export_gate(
    project_dir: Path,
    *,
    manuscript: str,
    design_spec: str,
    svg_files: list[Path] | None = None,
    figure_inventory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return export gate findings. Blocking findings prevent formal PPTX export."""
    blocking: list[str] = []
    warnings: list[str] = []
    combined = "\n".join([manuscript, design_spec])

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(combined):
            blocking.append("存在团队/赛事/日期/联系方式等占位符，正式版导出已拦截。")
            break

    for pattern in FABRICATED_LOOKING_PATTERNS:
        if pattern.search(combined):
            blocking.append("存在疑似自动编造的报告编号或精确时间戳，需改为真实来源或删除。")
            break

    if _has_pending_evidence_on_core_pages(manuscript):
        blocking.append("实操/支撑材料/数据页面仍有 `待补充` 材料，不能作为正式版导出。")

    if _has_visible_standalone_prep_page(manuscript):
        blocking.append("存在独立的演示准备/操作脚本/录屏备用可见页面，正式路演应合并到讲稿或备用方案。")

    story_pages = _implementation_storyline_issue_pages(manuscript)
    if story_pages:
        blocking.append(
            "实施过程第 "
            + "、".join(str(page) for page in story_pages[:8])
            + " 页仍像模块说明书，未围绕一次现场事件形成连续证明链。"
        )

    missing_chain = _implementation_event_chain_missing(manuscript)
    if missing_chain:
        blocking.append("实施过程缺少现场事件证明链环节：" + "、".join(missing_chain) + "。")

    duplicate_pairs = _duplicate_visible_pages(manuscript)
    if duplicate_pairs:
        blocking.append(
            "存在重复或高度同质化页面："
            + "、".join(f"{left}/{right}" for left, right in duplicate_pairs[:8])
            + "，需合并或改成不同证明对象。"
        )

    density_issue = _real_material_density_issue(manuscript)
    if density_issue:
        blocking.append(density_issue)

    missing_execution = _missing_execution_contract_fields(manuscript)
    if missing_execution:
        sample = ", ".join(missing_execution[:8])
        blocking.append(f"缺少现场执行字段：{sample}，不能作为正式版导出。")

    missing_contestant = _missing_contestant_contract_fields(manuscript)
    if missing_contestant:
        sample = ", ".join(missing_contestant[:8])
        blocking.append(f"缺少选手视角/证明对象字段：{sample}，不能作为正式版导出。")

    missing_content_plan = _missing_content_plan_fields(manuscript)
    if missing_content_plan:
        sample = ", ".join(missing_content_plan[:8])
        blocking.append(f"缺少页面内容稿字段：{sample}，不能作为正式版导出。")

    if _has_blocking_asset_gate(manuscript):
        blocking.append("页面内容稿标记存在缺失关键素材或 blocked_until_assets，正式版导出已拦截。")

    if _has_unbacked_real_asset_claim(manuscript):
        blocking.append("真实截图、测试结果、证书或协议类页面缺少素材状态支撑，不能作为正式版导出。")

    missing_asset_pages = _provided_asset_pages_without_images(manuscript, svg_files or [])
    if missing_asset_pages:
        blocking.append(
            "页面标记已提供真实素材但最终 SVG 未使用真实图片：第 "
            + "、".join(str(page) for page in missing_asset_pages[:12])
            + " 页。"
        )

    unresolved_hrefs = _unresolved_external_image_hrefs(svg_files or [])
    if unresolved_hrefs:
        blocking.append(
            "最终 SVG 仍存在未内嵌的外部图片路径，疑似素材路径未解析："
            + "；".join(unresolved_hrefs[:6])
        )

    if not _all_visual_patterns_allowed(manuscript):
        blocking.append("存在未登记的 visual_pattern.pattern_id，页面模式不可控，不能作为正式版导出。")

    if _missing_code_or_implementation_restoration(manuscript):
        blocking.append("核心技能模块缺少代码还原或实现解释，比赛技能水平支撑不足。")

    if _missing_fault_recovery_plan(manuscript):
        blocking.append("现场实操缺少故障恢复、排查或复测方案，不能作为正式版导出。")

    unverified = _unverified_result_claims(manuscript)
    if unverified:
        blocking.append(
            "成果/价值页存在无来源百分比或数量口径："
            + "；".join(unverified[:3])
        )

    disallowed = _disallowed_figure_names(figure_inventory or _load_inventory(project_dir))
    if svg_files and disallowed:
        offenders: list[str] = []
        for svg in svg_files:
            try:
                content = svg.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(name in content for name in disallowed):
                offenders.append(svg.name)
        if offenders:
            blocking.append(
                "正式版使用了不允许的 PDF 表格/页面裁图素材："
                + ", ".join(offenders[:8])
            )

    visible_text_offenders: list[str] = []
    if svg_files:
        for svg in svg_files:
            try:
                content = svg.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            violations = scan_svg_visible_text(content)
            if violations:
                visible_text_offenders.append(
                    f"{svg.name}: {format_visible_text_violations(violations, limit=3)}"
                )
        if visible_text_offenders:
            blocking.append(
                "PPT 可见文字包含后台策划/评分/口令/门禁语言，正式版导出已拦截："
                + "；".join(visible_text_offenders[:5])
            )

    if not blocking:
        warnings.append("Roadshow export gate passed.")

    report = {
        "deck_type": "roadshow",
        "status": "blocked" if blocking else "passed",
        "blocking_findings": blocking,
        "warnings": warnings,
    }
    try:
        (project_dir / "roadshow_export_gate_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
    return report


def _has_pending_evidence_on_core_pages(manuscript: str) -> bool:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    for page in pages:
        if "待补充" not in page:
            continue
        header = page[:260]
        if any(hint in header for hint in EVIDENCE_PAGE_HINTS):
            return True
        role_match = re.search(r"page_role:\s*([^\n]+)", page)
        if role_match and any(hint in role_match.group(1) for hint in EVIDENCE_PAGE_HINTS):
            return True
    return False


def _visible_manuscript_copy(page: str) -> str:
    parts = re.split(
        r"(?im)^\s*(?:\*\*)?(?:Slide Content Plan|page|section|formal_title|title|page_core_sentence|main_visual|visual_asset_plan|required_assets|"
        r"asset_status|fallback_visual|asset_gap_handling|export_gate|main_script|sub_script|transition|"
        r"page_role|judge_focus|visual_strategy|layout_hint|evidence_assets|speaker_goal|contestant_intent|"
        r"audience_takeaway|proof_object|visual_pattern|next_slide_bridge|story_role|primary_visual|stage_mode|"
        r"display_target|time_budget_sec|speaker_role|operator_role|operator_action|expected_screen_state|"
        r"fallback_plan|module_flow|acceptance_signal|command_cue)(?:\*\*)?\s*:?",
        page,
        maxsplit=1,
    )
    visible = parts[0]
    visible = re.sub(r"<!--.*?-->", "", visible, flags=re.S)
    return visible.strip()


def _has_visible_standalone_prep_page(manuscript: str) -> bool:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    for page in pages:
        visible = _visible_manuscript_copy(page)
        if any(term in visible for term in STANDALONE_PREP_VISIBLE_TERMS):
            return True
    return False


def _normalized_page_semantic_key(page: str) -> str:
    visible = _visible_manuscript_copy(page)
    planned = "\n".join(
        value
        for value in (
            " ".join(_field_values(page, "page_core_sentence")),
            " ".join(_field_values(page, "visible_content")),
        )
        if value
    )
    text = f"{visible}\n{planned}"
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = ASSET_TOKEN_RE.sub("", text)
    text = FIG_TOKEN_RE.sub("", text)
    text = re.sub(r"\b\d{1,2}\b", "", text)
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", text).lower()
    return text


def _duplicate_visible_pages(manuscript: str) -> list[tuple[int, int]]:
    seen: dict[str, int] = {}
    duplicates: list[tuple[int, int]] = []
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    for index, page in enumerate(pages, start=1):
        if index in {1, 2}:
            continue
        key = _normalized_page_semantic_key(page)
        if len(key) < 36:
            continue
        previous = seen.get(key)
        if previous is not None:
            duplicates.append((previous, index))
        else:
            seen[key] = index
    return duplicates


def _real_material_density_issue(manuscript: str) -> str | None:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    if len(pages) < 30:
        return None
    unique_assets = set(ASSET_TOKEN_RE.findall(manuscript))
    if len(unique_assets) < 12:
        return None
    asset_pages = [index for index, page in enumerate(pages, start=1) if ASSET_TOKEN_RE.search(page)]
    min_asset_pages = max(14, round(len(pages) * 0.45))
    if len(asset_pages) >= min_asset_pages:
        return None
    return (
        f"上传图片素材已较充分（{len(unique_assets)} 个 asset_id），但只有 {len(asset_pages)}/{len(pages)} 页绑定真实素材；"
        f"正式稿至少应有 {min_asset_pages} 页使用真实截图、设备图、运行图表或成果材料。"
    )


IMPLEMENTATION_REPORT_STYLE_RE = re.compile(
    r"前端开发|后端开发|测试工程|环境监测模块|设备联动控制模块|告警工单闭环模块|数据分析模块|"
    r"模块实现了|聚焦于|确保数据流|功能模块",
)
EVENT_CHAIN_RE = re.compile(
    r"异常|触发|预警|联动|工单|处置|复盘|运行记录|输入|输出|日志|接口|确认|移动端|大屏",
)
EVENT_TRIGGER_RE = re.compile(r"异常|触发|预警|输入|监测|告警")
EVENT_ACTION_RE = re.compile(r"联动|处置|工单|确认|移动端|大屏|设备|控制")
EVENT_REVIEW_RE = re.compile(r"运行记录|日志|复盘|复测|测试|追溯|记录")


def _implementation_storyline_issue_pages(manuscript: str) -> list[int]:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    if len(pages) < 30:
        return []
    offenders: list[int] = []
    for index, page in enumerate(pages, start=1):
        if not 18 <= index <= min(24, len(pages) - 8):
            continue
        visible = _visible_manuscript_copy(page)
        heading_match = re.search(r"(?m)^#{1,3}\s+(.+)$", visible)
        heading = heading_match.group(1).strip() if heading_match else visible.splitlines()[0] if visible else ""
        if IMPLEMENTATION_REPORT_STYLE_RE.search(heading):
            offenders.append(index)
        elif IMPLEMENTATION_REPORT_STYLE_RE.search(visible) and not EVENT_CHAIN_RE.search(visible):
            offenders.append(index)
    return offenders


def _implementation_event_chain_missing(manuscript: str) -> list[str]:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    if len(pages) < 30:
        return []
    middle = "\n".join(pages[17 : min(24, len(pages))])
    missing: list[str] = []
    if not EVENT_TRIGGER_RE.search(middle):
        missing.append("触发/输入")
    if not EVENT_ACTION_RE.search(middle):
        missing.append("处置/联动")
    if not EVENT_REVIEW_RE.search(middle):
        missing.append("记录/复盘")
    return missing


def _missing_execution_contract_fields(manuscript: str) -> list[str]:
    return [field for field in ROADSHOW_EXECUTION_FIELDS if not _has_field(manuscript, field)]


def _missing_contestant_contract_fields(manuscript: str) -> list[str]:
    return [field for field in ROADSHOW_CONTESTANT_FIELDS if not _has_field(manuscript, field)]


def _missing_content_plan_fields(manuscript: str) -> list[str]:
    return [field for field in ROADSHOW_CONTENT_PLAN_FIELDS if not _has_field(manuscript, field)]


def _has_blocking_asset_gate(manuscript: str) -> bool:
    values = [value.lower() for value in _field_values(manuscript, "export_gate")]
    if any("blocked_until_assets" in value for value in values):
        return True
    statuses = [value.lower() for value in _field_values(manuscript, "asset_status")]
    return any(status in {"blocking", "missing"} or "blocking" in status for status in statuses)


def _has_unbacked_real_asset_claim(manuscript: str) -> bool:
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    real_asset_terms = ("screenshot", "product_ui", "certificate", "material_photo", "real_image")
    result_terms = ("运行效果", "测试结果", "证书", "专利", "协议", "应用证明", "反馈材料")
    for page in pages:
        lowered = page.lower()
        if not any(term in lowered for term in real_asset_terms) and not any(term in page for term in result_terms):
            continue
        status_values = " ".join(_field_values(page, "asset_status")).lower()
        gate_values = " ".join(_field_values(page, "export_gate")).lower()
        required_values = " ".join(_field_values(page, "required_assets"))
        if "provided" in status_values or "formal_ok" in gate_values:
            continue
        if any(source_hint in required_values for source_hint in SOURCE_HINTS):
            continue
        return True
    return False


def _provided_asset_pages_without_images(manuscript: str, svg_files: list[Path]) -> list[int]:
    if not svg_files:
        return []
    by_page: dict[int, Path] = {}
    for svg in svg_files:
        match = re.match(r"0*(\d+)_", svg.name)
        if match:
            by_page[int(match.group(1))] = svg
    missing: list[int] = []
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    real_visual_types = ("real_image", "screenshot", "product_ui", "certificate", "material_photo")
    for index, page in enumerate(pages, start=1):
        lowered = page.lower()
        has_asset_token = bool(ASSET_TOKEN_RE.search(page))
        status_values = " ".join(_field_values(page, "asset_status")).lower()
        visual_values = " ".join(_field_values(page, "main_visual")).lower()
        visual_scope = f"{visual_values}\n{lowered}"
        should_use_image = has_asset_token or ("provided" in status_values and any(kind in visual_scope for kind in real_visual_types))
        if not should_use_image:
            continue
        svg = by_page.get(index)
        if svg is None:
            missing.append(index)
            continue
        try:
            content = svg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            missing.append(index)
            continue
        if "<image" not in content.lower():
            missing.append(index)
    return missing


def _unresolved_external_image_hrefs(svg_files: list[Path]) -> list[str]:
    unresolved: list[str] = []
    for svg in svg_files:
        try:
            content = svg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for href in IMAGE_HREF_RE.findall(content):
            if href.startswith("data:"):
                continue
            unresolved.append(f"{svg.name}: {href}")
    return unresolved


def _all_visual_patterns_allowed(manuscript: str) -> bool:
    if "visual_pattern:" not in manuscript:
        return False
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    allowed = {pattern.lower() for pattern in PATTERN_IDS}
    for page in pages:
        lowered = page.lower()
        if "visual_pattern:" not in lowered:
            return False
        start = lowered.find("visual_pattern:")
        tail = lowered[start:]
        end_candidates = [
            pos
            for marker in ("\nnext_slide_bridge:", "\nprimary_visual:", "\nstage_mode:")
            if (pos := tail.find(marker)) > 0
        ]
        block = tail[: min(end_candidates)] if end_candidates else tail[:500]
        match = re.search(r"pattern_id\s*[:：]\s*([^\n]+)", block, re.I)
        if match and normalize_pattern_id(match.group(1)) in allowed:
            continue
        if not any(pattern in block for pattern in allowed):
            return False
    return True


def _missing_code_or_implementation_restoration(manuscript: str) -> bool:
    # Roadshow decks may be hardware/process oriented, so accept either code
    # restoration or concrete implementation explanation.
    return not any(hint.lower() in manuscript.lower() for hint in CODE_RESTORATION_HINTS)


def _missing_fault_recovery_plan(manuscript: str) -> bool:
    fallback_lines = _field_values(manuscript, "fallback_plan")
    if not fallback_lines:
        return True
    meaningful = []
    for line in fallback_lines:
        value = line.strip()
        if not value:
            continue
        if value in {"无", "不涉及", "无。", "不涉及。"}:
            continue
        meaningful.append(value)
    return not meaningful


def _unverified_result_claims(manuscript: str) -> list[str]:
    offenders: list[str] = []
    percent_re = re.compile(r"[+\-]?\d+(?:\.\d+)?\s*%")
    quantity_re = re.compile(r"\d+(?:\.\d+)?\s*(?:家|次|个|万元|元|亩|台|套|人)")
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", manuscript) if p.strip()]
    for page in pages:
        visible = _visible_manuscript_copy(page)
        for raw in visible.splitlines():
            line = raw.strip()
            if _is_metadata_line(line):
                continue
            if not line or not any(hint in line for hint in RESULT_PAGE_HINTS):
                continue
            if not (percent_re.search(line) or quantity_re.search(line)):
                continue
            if any(hint in line for hint in SOURCE_HINTS):
                continue
            offenders.append(line[:120])
    return offenders


def _field_values(text: str, field: str) -> list[str]:
    name = field.strip().rstrip(":：")
    pattern = re.compile(
        rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(name)}(?:\*\*)?\s*[:：]\s*(.+)$"
    )
    return [match.group(1).strip() for match in pattern.finditer(text)]


def _has_field(text: str, field: str) -> bool:
    return bool(_field_values(text, field))


def _is_metadata_line(line: str) -> bool:
    if not line:
        return True
    normalized = line.strip()
    for field in (
        "page_role",
        "judge_focus",
        "visual_strategy",
        "layout_hint",
        "evidence_assets",
        "speaker_goal",
        "page_core_sentence",
        "visible_content",
        "main_visual",
        "visual_asset_plan",
        "required_assets",
        "asset_status",
        "fallback_visual",
        "asset_gap_handling",
        "export_gate",
        "main_script",
        "sub_script",
        "transition",
        "contestant_intent",
        "audience_takeaway",
        "proof_object",
        "visual_pattern",
        "next_slide_bridge",
        "story_role",
        "stage_mode",
        "display_target",
        "time_budget_sec",
        "speaker_role",
        "operator_role",
        "operator_action",
        "expected_screen_state",
        "fallback_plan",
        "module_flow",
        "acceptance_signal",
        "command_cue",
    ):
        if re.match(rf"^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(field)}(?:\*\*)?\s*[:：]", normalized, re.I):
            return True
    return False


def _load_inventory(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "sources" / "images" / "figure_review.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _disallowed_figure_names(inventory: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for rec in inventory:
        meta = classify_roadshow_figure(rec)
        if meta["allowed_for_roadshow"]:
            continue
        path = str(rec.get("path") or "")
        if path:
            names.add(Path(path).stem)
            names.add(Path(path).name)
    return names
