"""Visible-content contract helpers for vocational roadshow decks.

Roadshow manuscripts intentionally contain private planning fields that are
useful for the agent chain, but those fields must never leak onto slides.  This
module keeps the visible slide copy separate from speaker/runbook strategy.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any


PRIVATE_FIELD_NAMES = (
    "page",
    "section",
    "formal_title",
    "title",
    "page_role",
    "judge_focus",
    "visual_strategy",
    "layout_hint",
    "evidence_assets",
    "speaker_goal",
    "contestant_intent",
    "audience_takeaway",
    "proof_object",
    "visual_pattern",
    "next_slide_bridge",
    "story_role",
    "primary_visual",
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
    "visual_contract",
    "private_runbook",
    "speaker_notes",
    "evidence_gate",
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
)

SOURCE_PRIVATE_MARKERS = (
    "职业院校技能大赛路演PPT智能生成母稿",
    "primary_visual",
    "private_runbook",
    "command_cue",
    "正式导出门禁",
    "Run-of-Show",
    "模拟测试数据",
)

VISIBLE_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("scoring_logic", re.compile(r"评分要素|评分点|评分维度|得分点|采分点|展示映射|评分支撑|评分关注")),
    ("private_field_name", re.compile(r"\b(?:" + "|".join(re.escape(name) for name in PRIVATE_FIELD_NAMES) + r")\b")),
    ("runbook_role", re.compile(r"(?:讲解|操作|记录|应急|测试|保障)角色\s*[A-D]")),
    ("command_or_signal", re.compile(r"关键节点口令|节点口令|口令交接|现场口令|成功信号|成功判据")),
    ("export_gate", re.compile(r"正式导出门禁|导出门禁|测试草稿版|草稿态|不可正式导出")),
    ("pending_or_mock", re.compile(r"来源待补充|未核验数据|模拟截图|模拟日志|模拟测试数据|模拟编号|模拟报告")),
    ("placeholder_identity", re.compile(r"XX职业院校|XX代表队|\[(?:学校|团队名称|联系方式|电话|邮箱|姓名)\]")),
    ("visible_evidence_word", re.compile(r"证据")),
    ("planning_language", re.compile(r"我们如何证明|一张图看懂|支撑材料的总链路|支撑链路|路演路线|生成器|内部逻辑|页面任务")),
    ("standalone_prep_page", re.compile(r"现场实操演示准备|演示环境与操作脚本已就绪|演示环境已准备|操作脚本已就绪|演示准备状态|播放录屏")),
)

PRIVATE_FIELD_RE = re.compile(
    r"^\s*(?:\*\*)?(?P<name>" + "|".join(re.escape(name) for name in PRIVATE_FIELD_NAMES) + r")(?:\*\*)?\s*:",
    re.IGNORECASE,
)
PRIVATE_GROUP_HEADING_RE = re.compile(
    r"^\s*(?:\*\*)?\s*(?:Slide Content Plan|Visual Planning Fields|Contestant Perspective Fields|Field Execution Fields)\s*:?\s*(?:\*\*)?\s*$",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
SVG_TEXT_RE = re.compile(r"<(?:text|tspan)\b[^>]*>(.*?)</(?:text|tspan)>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

VISIBLE_TERMINOLOGY_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"关键证据链"), "关键支撑链路"),
    (re.compile(r"证据链"), "支撑链路"),
    (re.compile(r"证据墙"), "材料看板"),
    (re.compile(r"证据材料"), "支撑材料"),
    (re.compile(r"证据留存"), "运行记录留存"),
    (re.compile(r"数据证据"), "验证数据"),
    (re.compile(r"关键证据"), "关键支撑材料"),
    (re.compile(r"证据摘要"), "支撑材料摘要"),
    (re.compile(r"证据对象"), "支撑对象"),
    (re.compile(r"证据列"), "记录列"),
    (re.compile(r"证据"), "支撑材料"),
)


@dataclass(frozen=True)
class VisibleTextViolation:
    rule: str
    phrase: str
    context: str

    def to_dict(self) -> dict[str, str]:
        return {"rule": self.rule, "phrase": self.phrase, "context": self.context}


def classify_roadshow_source(source_md: str) -> dict[str, Any]:
    """Classify uploaded roadshow material for prompt routing."""
    hits = [marker for marker in SOURCE_PRIVATE_MARKERS if marker in source_md]
    has_agent_seed = len(hits) >= 3
    has_real_evidence = any(
        token in source_md
        for token in (
            "测试记录",
            "日志",
            "截图",
            "设备照片",
            "用户反馈",
            "调研记录",
            "[[FIG:",
        )
    )
    return {
        "type": "agent_seed_draft" if has_agent_seed else "project_material",
        "agent_seed_draft": has_agent_seed,
        "private_marker_hits": hits,
        "has_real_evidence_hints": has_real_evidence,
    }


def source_profile_prompt_block(profile: dict[str, Any]) -> str:
    """Prompt text that tells the LLM how to treat the detected source type."""
    if profile.get("agent_seed_draft"):
        hits = "、".join(profile.get("private_marker_hits") or [])
        return (
            "## Source Type Notice\n\n"
            "检测到用户上传资料像是 PPT 生成母稿或 Agent 规划稿，而不是最终参赛资料。\n"
            f"命中的内部标记：{hits or '无'}。\n"
            "处理规则：只抽取项目事实、真实支撑材料、模块链路和缺口；不得把母稿中的评分映射、"
            "字段名、口令、角色调度、门禁、模拟数据写入 PPT 可见正文。"
        )
    return (
        "## Source Type Notice\n\n"
        "按普通项目资料处理。仍需区分可展示事实、选手讲稿和系统内部执行信息，"
        "禁止把评分/口令/门禁语言写入 PPT 可见正文。"
    )


def sanitize_page_for_executor(page_text: str) -> str:
    """Return the visible-safe subset of a manuscript page for SVG generation."""
    safe_lines: list[str] = []
    private_block_indent: int | None = None

    for raw_line in page_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if safe_lines and safe_lines[-1] != "":
                safe_lines.append("")
            continue
        if PRIVATE_GROUP_HEADING_RE.match(stripped):
            continue

        match = PRIVATE_FIELD_RE.match(line)
        indent = len(line) - len(line.lstrip(" "))
        if match:
            private_block_indent = indent
            continue
        if private_block_indent is not None:
            if indent > private_block_indent and not SECTION_HEADING_RE.match(line):
                continue
            private_block_indent = None

        rewritten = rewrite_visible_line(stripped)
        if rewritten:
            safe_lines.append(rewritten)

    safe = "\n".join(safe_lines).strip()
    safe = re.sub(r"\n{3,}", "\n\n", safe)
    if not safe:
        return "本页用于项目汇报，请基于项目事实生成简洁、正式、可验证的可见页面内容。"
    return safe


def extract_roadshow_executor_guidance(page_text: str) -> str:
    """Extract hidden roadshow planning guidance for SVG composition.

    The returned text is safe to show to the executor as private instructions,
    but it must not become visible slide copy.  It helps the SVG stage stop
    guessing layout from generic visible bullets and instead design around the
    contestant's proof object and reference pattern.
    """
    fields = _private_field_blocks(page_text)
    wanted = (
        "contestant_intent",
        "audience_takeaway",
        "proof_object",
        "visual_pattern",
        "story_role",
        "primary_visual",
        "page_core_sentence",
        "visible_content",
        "main_visual",
        "visual_asset_plan",
        "required_assets",
        "asset_status",
        "fallback_visual",
        "asset_gap_handling",
        "speaker_goal",
        "main_script",
        "sub_script",
        "transition",
        "layout_hint",
    )
    lines = [
        "## Roadshow Hidden Design Guidance",
        "Use these fields only to decide composition, hierarchy, and diagrams. Do not render field names or values as slide text.",
    ]
    found = False
    for name in wanted:
        value = fields.get(name, "").strip()
        if not value:
            continue
        found = True
        value = _compact_guidance_value(value)
        lines.append(f"- {name}: {value}")
    if not found:
        return (
            "## Roadshow Hidden Design Guidance\n"
            "- No private guidance fields were found. Build a participant-facing page around the visible claim, one main explanatory object, and concise evidence labels."
        )
    lines.extend(
        [
            "- Turn `proof_object` into the slide's main object where possible: architecture, workflow, evidence chain, live demo board, test dashboard, or result dashboard.",
            "- `visual_pattern` is a structure choice, not visible text. Do not render pattern ids.",
            "- Use `story_role` to preserve the launch-style storyline; do not render it.",
            "- Never create a standalone visible preparation page such as 演示环境已就绪 or 操作脚本已就绪. Put preparation and backup details in speaker notes or fallback_plan.",
            "- Use page_core_sentence and visible_content to choose concise visible copy, but never render those field names.",
            "- Use main_visual/visual_asset_plan/required_assets/asset_status/fallback_visual to decide whether the page needs a real image, screenshot, chart, generated image, SVG diagram, or export blocking.",
            "- Use main_script/sub_script/transition only as speaker-notes guidance. Do not render these field names or speaker-note prose on the slide.",
            "- Keep the page from becoming a generic card wall; use cards only as annotations around the main object.",
            "- Never render the Chinese word `证据` as visible slide copy. Use 支撑材料、运行记录、验证结果、成果材料、资料来源 instead.",
        ]
    )
    return "\n".join(lines)


def rewrite_visible_line(line: str) -> str:
    """Rewrite or remove unsafe visible manuscript lines."""
    if PRIVATE_FIELD_RE.match(line):
        return ""
    for pattern, replacement in VISIBLE_TERMINOLOGY_REWRITES:
        line = pattern.sub(replacement, line)
    if any(pattern.search(line) for _, pattern in VISIBLE_FORBIDDEN_PATTERNS):
        if "待补充" in line or "未核验" in line:
            return ""
        if any(term in line for term in ("评分", "采分", "得分点", "口令", "角色", "门禁", "草稿")):
            return ""
        if any(
            term in line
            for term in (
                "我们如何证明",
                "一张图看懂",
                "路演路线",
                "生成器",
                "内部逻辑",
                "页面任务",
                "现场实操演示准备",
                "演示环境与操作脚本已就绪",
                "演示环境已准备",
                "操作脚本已就绪",
                "演示准备状态",
                "播放录屏",
            )
        ):
            return ""
    line = re.sub(r"待补充来源|待补充|未核验数据", "需以真实资料核验", line)
    line = re.sub(r"模拟测试数据|模拟日志|模拟截图", "测试资料", line)
    return line.strip()


def _private_field_blocks(page_text: str) -> dict[str, str]:
    fields: dict[str, list[str]] = {}
    current: str | None = None
    current_indent = 0
    for raw_line in page_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        match = PRIVATE_FIELD_RE.match(line)
        indent = len(line) - len(line.lstrip(" "))
        if match:
            current = match.group("name").lower()
            current_indent = indent
            value = line.split(":", 1)[1].strip() if ":" in line else ""
            fields.setdefault(current, [])
            if value:
                fields[current].append(value)
            continue
        if current is not None:
            if stripped and indent > current_indent and not SECTION_HEADING_RE.match(line):
                fields[current].append(stripped)
                continue
            current = None
    return {name: "\n".join(values).strip() for name, values in fields.items()}


def _compact_guidance_value(value: str, *, limit: int = 420) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def scan_visible_text(text: str) -> list[VisibleTextViolation]:
    """Scan plain visible text for forbidden roadshow leakage."""
    violations: list[VisibleTextViolation] = []
    for rule, pattern in VISIBLE_FORBIDDEN_PATTERNS:
        for match in pattern.finditer(text):
            phrase = match.group(0)
            start = max(0, match.start() - 28)
            end = min(len(text), match.end() + 28)
            context = text[start:end].replace("\n", " ")
            violations.append(VisibleTextViolation(rule=rule, phrase=phrase, context=context))
    return violations


def scan_svg_visible_text(svg: str) -> list[VisibleTextViolation]:
    """Extract likely visible SVG text and scan it for forbidden terms."""
    chunks: list[str] = []
    for match in SVG_TEXT_RE.finditer(svg):
        raw = TAG_RE.sub("", match.group(1))
        text = html.unescape(raw).strip()
        if text:
            chunks.append(text)
    return scan_visible_text("\n".join(chunks))


def format_visible_text_violations(violations: list[VisibleTextViolation], *, limit: int = 10) -> str:
    """Render visible text violations for logs, critic prompts, and export gates."""
    if not violations:
        return ""
    lines = []
    for violation in violations[:limit]:
        lines.append(f"- {violation.rule}: `{violation.phrase}` in `{violation.context}`")
    if len(violations) > limit:
        lines.append(f"- ... and {len(violations) - limit} more")
    return "\n".join(lines)
