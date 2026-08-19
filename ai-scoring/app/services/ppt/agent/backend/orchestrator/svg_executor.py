"""SVG Executor agent: generates SVG page code from design spec.

The executor runs a page-by-page generation loop. Each page is checked by
the static :mod:`backend.generator.svg_critic` before being accepted. If
the critic finds violations, a targeted repair prompt is fed back to the
LLM (bounded retries, with slightly lower temperature on each retry) so
that regeneration is *informed* rather than blind.
"""

from __future__ import annotations

import asyncio
import html
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

from PIL import Image

from backend.config import settings
from backend.generator.svg_critic import CriticConfig, CriticReport, Violation, check_svg
from backend.generator.svg_finalize.render_ready import strip_svg_image_elements
from backend.generator.visual_critic import VisualCriticConfig, visual_check
from backend.llm import LLMMessage, LLMProvider, LLMResponse
from backend.orchestrator.manuscript import (
    extract_page_type,
    split_manuscript_pages,
    strip_page_type_metadata,
)
from backend.orchestrator.provider_guidance import (
    deepseek_executor_guidance,
    is_deepseek_provider,
)
from backend.orchestrator.roadshow_content_contract import (
    extract_roadshow_executor_guidance,
    sanitize_page_for_executor,
    scan_svg_visible_text,
)
from backend.orchestrator.roadshow_asset_registry import load_asset_registry
from backend.usage.tracker import reset_usage_context, set_usage_context

# `[[FIG:fig_007_p9_page]]` style tokens emitted by the research agent.
FIG_TOKEN_RE = re.compile(r"\[\[FIG:([A-Za-z0-9_\-]+)\]\]")
ASSET_TOKEN_RE = re.compile(r"\[\[ASSET:([A-Za-z0-9_\-]+)\]\]")
IMAGE_HREF_RE = re.compile(r"<image\b[^>]*\bhref=[\"']([^\"']+)[\"']", re.IGNORECASE)
DATA_ICON_RE = re.compile(
    r"<use\b(?=[^>]*\bdata-icon=([\"'])([^\"']+)\1)[^>]*(?:/>|>\s*</use>)",
    re.IGNORECASE | re.DOTALL,
)
PSEUDO_ICON_BADGE_TEXT = frozenset({"P", "Δ", "!", "G", "?", "i", "I", "✓", "×"})
FIGURE_LABEL_RE = re.compile(
    r"\b(fig(?:ure)?|table)\s*\.?\s*(\d+)\b|([图表])\s*(\d+)",
    re.IGNORECASE,
)

PROMPT_PATH = Path(__file__).parent / "prompts" / "executor.md"

# Default number of static critic checks per page, including the first
# post-generation check. A value of 3 allows two repair calls.
DEFAULT_MAX_CRITIC_ATTEMPTS = 3

# Max prior page exchanges kept in the conversation (sliding window).
#
# Keep this at 0: each page receives a compact global design context plus its
# own page render spec. Carrying prior pages means every later page re-sends old
# SVG and large manuscript fragments, which made long roadshow decks crawl.
MAX_PRIOR_PAGES_IN_CONTEXT = 0

# Hard caps for context that is sent to the SVG model. The full manuscript and
# design spec remain on disk; these limits only affect the per-call prompt.
MAX_GLOBAL_DESIGN_CONTEXT_CHARS = 12000
MAX_PAGE_DESIGN_CONTEXT_CHARS = 4200
MAX_PAGE_RENDER_CONTENT_CHARS = 14000

# Initial response plus bounded same-page retries when no SVG can be extracted.
MAX_SVG_EXTRACTION_ATTEMPTS = 3
MAX_EMPTY_RESPONSE_RECOVERY_ATTEMPTS = 2
PAGE_STATUS_HEARTBEAT_SECONDS = 15

CriticCallback = Callable[[int, int, CriticReport, str | None, str | None], Awaitable[None]]
SvgUpdateCallback = Callable[[int, str], Awaitable[None]]
PageStatusCallback = Callable[[int, int, str, str, dict | None], Awaitable[None]]


async def _emit_page_status(
    callback: PageStatusCallback | None,
    page_num: int,
    attempt: int,
    phase: str,
    message: str,
    data: dict | None = None,
) -> None:
    if callback is None:
        return
    await callback(page_num, attempt, phase, message, data)


async def _chat_with_page_status(
    llm: LLMProvider,
    messages: list[LLMMessage],
    model: str,
    *,
    temperature: float,
    max_tokens: int,
    page_num: int,
    total_pages: int,
    attempt: int,
    phase: str,
    on_page_status: PageStatusCallback | None,
) -> LLMResponse:
    """Run one LLM call with heartbeat and non-fatal failure output."""
    phase_label = {
        "generation": "生成",
        "recovery": "重新生成",
        "repair": "修复",
    }.get(phase, phase)
    await _emit_page_status(
        on_page_status,
        page_num,
        attempt,
        phase,
        f"第 {page_num}/{total_pages} 页正在{phase_label}，第 {attempt} 次尝试",
        {"phase": phase},
    )
    started_at = time.monotonic()
    task = asyncio.create_task(
        llm.chat(messages, model, temperature=temperature, max_tokens=max_tokens)
    )
    try:
        while True:
            elapsed = time.monotonic() - started_at
            done, _ = await asyncio.wait(
                {task},
                timeout=PAGE_STATUS_HEARTBEAT_SECONDS,
            )
            if task in done:
                try:
                    response = task.result()
                except Exception as exc:
                    await _emit_page_status(
                        on_page_status,
                        page_num,
                        attempt,
                        "error",
                        f"第 {page_num}/{total_pages} 页第 {attempt} 次{phase_label}调用失败，正在重新建立请求",
                        {"phase": phase, "error": str(exc)},
                    )
                    return LLMResponse(
                        content="",
                        raw={"error": str(exc)},
                        finish_reason="error",
                    )
                content_length = len((response.content or "").strip())
                if content_length:
                    await _emit_page_status(
                        on_page_status,
                        page_num,
                        attempt,
                        phase,
                        f"第 {page_num}/{total_pages} 页第 {attempt} 次{phase_label}已返回，正在解析 SVG",
                        {"content_length": content_length},
                    )
                else:
                    await _emit_page_status(
                        on_page_status,
                        page_num,
                        attempt,
                        "empty_response",
                        f"第 {page_num}/{total_pages} 页第 {attempt} 次{phase_label}返回为空，正在重新建立请求",
                        {"phase": phase},
                    )
                return response

            await _emit_page_status(
                on_page_status,
                page_num,
                attempt,
                phase,
                f"第 {page_num}/{total_pages} 页仍在{phase_label}中，已等待 {int(elapsed)} 秒",
                {
                    "phase": phase,
                    "elapsed_seconds": int(elapsed),
                },
            )
    finally:
        if not task.done():
            task.cancel()


def _limit_text(text: str, max_chars: int, *, label: str = "content") -> str:
    """Bound a prompt block while making truncation explicit to the model."""
    text = (text or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    keep_head = max_chars * 3 // 4
    keep_tail = max_chars - keep_head
    return (
        text[:keep_head].rstrip()
        + f"\n\n[... {label} trimmed for SVG rendering context ...]\n\n"
        + text[-keep_tail:].lstrip()
    )


def _section_before_content_outline(design_spec: str) -> str:
    """Return the global visual/spec section before the per-slide outline."""
    match = re.search(
        r"(?im)^#{2,4}\s*(?:IX\.?\s*)?(?:Content\s+Outline|内容大纲)\b",
        design_spec,
    )
    return design_spec[: match.start()] if match else design_spec


def _drop_design_section(text: str, heading_keywords: tuple[str, ...]) -> str:
    """Remove a large top-level design section from a Markdown block."""
    if not text:
        return text
    keywords = "|".join(re.escape(item) for item in heading_keywords)
    pattern = (
        rf"(?ims)^#{2,4}\s*(?:[IVXLCDM]+\.?\s*)?"
        rf"(?:{keywords})\b.*?(?=^#{2,4}\s*(?:[IVXLCDM]+\.?\s*)?\S|\Z)"
    )
    return re.sub(pattern, "", text).strip()


def _global_design_context(design_spec: str) -> str:
    """Compact style context used in every SVG call.

    The full design spec can be tens of thousands of characters because it also
    contains all page outlines and asset tables. For rendering a single page,
    the model only needs stable global rules here; page-specific assignments are
    supplied separately by :func:`_page_design_context`.
    """
    global_text = _section_before_content_outline(design_spec)
    global_text = _drop_design_section(
        global_text,
        (
            "Image Resource List",
            "Visualization Reference List",
            "图片素材",
            "图像资源",
            "可视化",
        ),
    )
    return _limit_text(
        global_text,
        MAX_GLOBAL_DESIGN_CONTEXT_CHARS,
        label="global design context",
    )


def _page_design_context(design_spec: str, page_num: int) -> str:
    """Extract only the current slide's design outline from Section IX."""
    page_pattern = (
        rf"(?ims)^#+\s*(?:slide|page)\s*0*{page_num}\b.*?"
        rf"(?=^#+\s*(?:slide|page)\s*0*\d+\b|\Z)"
    )
    page_match = re.search(page_pattern, design_spec)
    if not page_match:
        return ""
    return _limit_text(
        page_match.group(0),
        MAX_PAGE_DESIGN_CONTEXT_CHARS,
        label=f"page {page_num} design context",
    )


def _cached_svg_for_page(svg_output_dir: Path, page_num: int) -> str | None:
    """Return an already accepted SVG for a page, if one exists on disk."""
    for path in sorted(svg_output_dir.glob(f"{page_num:02d}_*.svg")):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        svg = _extract_svg(content)
        if svg:
            return svg
        stripped = content.strip()
        if stripped.startswith("<svg") and stripped.endswith("</svg>"):
            return stripped
    return None


def _resolve_fig_tokens(
    page_content: str,
    figure_inventory: list[dict] | None,
) -> tuple[str, list[dict], list[str]]:
    """Replace `[[FIG:id]]` tokens with explicit real-figure references."""
    if not figure_inventory:
        return page_content, [], []

    by_id = _figure_alias_map(figure_inventory)
    used: list[dict] = []
    seen: set[str] = set()
    rejected: list[str] = []

    def _replace(match: re.Match) -> str:
        fig_id = match.group(1)
        fig = by_id.get(fig_id)
        if fig is None:
            return f"[[MISSING_FIG:{fig_id}]]"
        resolved_id = Path(str(fig.get("path") or "")).stem or fig_id
        line = _line_containing(page_content, match.start())
        mismatch = _figure_label_mismatch(line, str(fig.get("caption") or ""))
        if mismatch:
            rejected.append(f"{fig_id}: {mismatch}")
            return f"[[REJECTED_FIG:{fig_id} — {mismatch}]]"
        if resolved_id not in seen:
            seen.add(resolved_id)
            used.append(fig)
        return _paper_figure_reference_line(fig, resolved_id)

    return FIG_TOKEN_RE.sub(_replace, page_content), used, rejected


def _figure_alias_map(figure_inventory: list[dict]) -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for fig in figure_inventory:
        path = str(fig.get("path") or "")
        if path:
            stem = Path(path).stem
            by_id[stem] = fig
            label = _extract_figure_label(str(fig.get("caption") or ""))
            if label:
                kind, number = label
                aliases = {f"{kind}{number}", f"{kind}_{number}"}
                if kind == "figure":
                    aliases.update({f"fig{number}", f"fig_{number}"})
                for alias in aliases:
                    by_id.setdefault(alias, fig)
    return by_id


def _paper_figure_reference_line(fig: dict, resolved_id: str | None = None) -> str:
    resolved_id = resolved_id or Path(str(fig.get("path") or "")).stem
    path = fig.get("path") or ""
    cap = (fig.get("caption") or "").strip().replace("\n", " ")
    if len(cap) > 160:
        cap = cap[:157] + "..."
    return f"[PAPER FIGURE — id={resolved_id}, href=\"{path}\", caption: {cap}]"


def _resolve_asset_tokens(
    page_content: str,
    asset_registry: dict[str, dict],
    *,
    token_source: str | None = None,
) -> tuple[str, list[dict], list[str]]:
    """Replace or append `[[ASSET:id]]` references with concrete hrefs."""
    source = token_source if token_source is not None else page_content
    if not asset_registry:
        missing = sorted(set(ASSET_TOKEN_RE.findall(source)))
        return page_content, [], [f"{asset_id}: asset_registry.json not found" for asset_id in missing]

    used: list[dict] = []
    seen: set[str] = set()
    rejected: list[str] = []

    def _asset_ref(asset_id: str) -> str:
        asset = asset_registry.get(asset_id)
        if asset is None:
            rejected.append(f"{asset_id}: missing from asset_registry.json")
            return f"[[MISSING_ASSET:{asset_id}]]"
        if asset_id not in seen:
            seen.add(asset_id)
            used.append(asset)
        href = str(asset.get("href") or asset.get("path") or "")
        caption = str(asset.get("caption") or asset.get("original_rel") or asset_id).replace("\n", " ").strip()
        if len(caption) > 160:
            caption = caption[:157] + "..."
        asset_type = str(asset.get("asset_type") or "material_image")
        return f"[ROADSHOW ASSET — id={asset_id}, type={asset_type}, href=\"{href}\", caption: {caption}]"

    def _replace(match: re.Match) -> str:
        return _asset_ref(match.group(1))

    rewritten = ASSET_TOKEN_RE.sub(_replace, page_content)
    all_ids = list(dict.fromkeys(ASSET_TOKEN_RE.findall(source)))
    appended: list[str] = []
    for asset_id in all_ids:
        if asset_id in seen:
            continue
        appended.append(_asset_ref(asset_id))
    if appended:
        rewritten = (
            f"{rewritten}\n\nRoadshow asset assignment recovered for this slide:\n"
            + "\n".join(appended)
        )
    return rewritten, used, rejected


def _strip_roadshow_asset_assignment_text(content: str) -> str:
    """Remove uploaded-material assignments from pages that must not use images."""
    if not content:
        return ""
    stripped = ASSET_TOKEN_RE.sub("", content)
    stripped = re.sub(r"(?im)^Roadshow asset assignment recovered for this slide:\s*$", "", stripped)
    stripped = re.sub(r"(?im)^\s*\[ROADSHOW ASSET[^\n]*\]\s*$", "", stripped)
    stripped = re.sub(r"(?im)^\s*required_assets\s*:\s*.*$", "required_assets: 无", stripped)
    stripped = re.sub(r"(?im)^\s*asset_status\s*:\s*.*$", "asset_status: not_required", stripped)
    return re.sub(r"\n{3,}", "\n\n", stripped).strip()


def _cover_no_image_policy_block() -> str:
    return (
        "## Roadshow Cover Asset Policy\n"
        "- The cover page must not use uploaded/source/generated images, screenshots, dashboard mockups, or `<image>` elements.\n"
        "- Ignore all asset assignments, required_assets, image-resource tables, and recovered roadshow asset references for this cover.\n"
        "- Build the cover only with native SVG: title, subtitle, role/team line, abstract geometry, grid, lines, dots, brackets, and subtle rings.\n"
        "- Do not draw a fake product dashboard or screenshot-like UI frame on the cover."
    )


def _figures_from_design_spec_for_page(
    design_spec: str,
    page_num: int,
    figure_inventory: list[dict] | None,
    page_type: str | None = None,
) -> list[dict]:
    """Recover slide image assignments from the design spec as a safety net."""
    if not figure_inventory:
        return []
    if (page_type or "").lower() in {"cover", "chapter", "toc", "ending"}:
        return []
    page_pattern = (
        rf"(?ims)^#+\s*(?:slide|page)\s*0*{page_num}\b.*?"
        rf"(?=^#+\s*(?:slide|page)\s*0*\d+\b|\Z)"
    )
    page_match = re.search(page_pattern, design_spec)
    if not page_match:
        return []
    block = page_match.group(0)
    image_ids = re.findall(r"(?im)^\s*-\s*\*\*Image\*\*\s*:\s*`([^`]+)`", block)
    if not image_ids:
        return []
    by_id = _figure_alias_map(figure_inventory)
    figures: list[dict] = []
    seen: set[str] = set()
    for image_id in image_ids:
        fig = by_id.get(image_id.strip())
        if not fig:
            continue
        stem = Path(str(fig.get("path") or "")).stem
        if stem in seen:
            continue
        seen.add(stem)
        figures.append(fig)
    return figures


def _icon_from_inventory_table(design_spec: str, page_num: int) -> dict | None:
    """Look up icon from Section VI inventory table."""
    vi_pattern = r"(?ims)^#+\s*VI\.?\s*Icon\s+Usage.*?(?=^#+\s*VII\.?\s|\Z)"
    vi_match = re.search(vi_pattern, design_spec)
    if not vi_match:
        return None
    vi_text = vi_match.group(0)

    for raw_line in vi_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or not re.fullmatch(r"0*\d+", cells[0]):
            continue
        if int(cells[0]) != page_num:
            continue
        icon_name = cells[1].strip().strip("`")
        if not icon_name or icon_name.lower() in {"none", "null", "n/a"}:
            return None
        role = cells[2] if len(cells) > 2 else ""
        anchor = cells[3] if len(cells) > 3 else ""
        placement = cells[4] if len(cells) > 4 else ""
        size_text = cells[5] if len(cells) > 5 else ""
        note = "; ".join(
            part
            for part in (
                f"role: {role}" if role else "",
                f"anchor: {anchor}" if anchor else "",
                f"placement: {placement}" if placement else "",
                f"size: {size_text}" if size_text else "",
            )
            if part
        )
        return {
            "name": icon_name,
            "size": _icon_size_from_text(size_text, default=40),
            "color": _icon_color_from_text(size_text, default="#2563EB"),
            "note": note,
            "role": role,
            "anchor": anchor,
            "placement": placement,
            "reason": "",
        }

    # Match table rows like | 03 | `chunk/target` | ... |
    row_pattern = rf"\|\s*0*{page_num}\s*\|\s*`([^`]+)`\s*\|"
    row_match = re.search(row_pattern, vi_text)
    if not row_match:
        return None
    icon_name = row_match.group(1).strip()
    if not icon_name or icon_name.lower() in {"none", "null", "n/a"}:
        return None
    return {"name": icon_name, "size": 40, "color": "#2563EB", "note": ""}


def _icon_note_fields(note: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(
        r"(?is)\b(role|anchor|placement|size|reason|color)\s*:\s*"
        r"(.*?)(?=;\s*\b(?:role|anchor|placement|size|reason|color)\s*:|$)",
        note,
    ):
        fields[match.group(1).lower()] = match.group(2).strip(" ;.-")
    return fields


def _icon_size_from_text(text: str, *, default: int = 40) -> int:
    size_match = re.search(r"(\d{1,3})\s*[x×]\s*(\d{1,3})\s*px?", text, re.IGNORECASE)
    if size_match:
        return max(int(size_match.group(1)), int(size_match.group(2)))
    single_match = re.search(r"\b(\d{2,3})\s*px\b", text, re.IGNORECASE)
    if single_match:
        return int(single_match.group(1))
    return default


def _icon_color_from_text(text: str, *, default: str = "#2563EB") -> str:
    color_match = re.search(r"`(#[0-9A-Fa-f]{3,8})`|(#[0-9A-Fa-f]{3,8})", text)
    if color_match:
        return color_match.group(1) or color_match.group(2)
    return default


def _icon_from_design_spec_for_page(design_spec: str, page_num: int) -> dict | None:
    """Recover a slide-level icon assignment from the design spec.

    Looks in Section IX first (Icon: line), then Section VI inventory table.
    """
    # Primary: Section IX Icon: line
    page_pattern = (
        rf"(?ims)^#+\s*(?:slide|page)\s*0*{page_num}\b.*?"
        rf"(?=^#+\s*(?:slide|page)\s*0*\d+\b|\Z)"
    )
    page_match = re.search(page_pattern, design_spec)
    if page_match:
        block = page_match.group(0)
        icon_match = re.search(
            r"(?im)^\s*-\s*\*\*Icon\*\*\s*:\s*`([^`]+)`([^\n]*)",
            block,
        )
        if icon_match:
            icon_name = icon_match.group(1).strip()
            if not icon_name or icon_name.lower() in {"none", "null", "n/a"}:
                return None

            note = icon_match.group(2).strip()
            fields = _icon_note_fields(note)
            size_text = fields.get("size", note)
            color_text = fields.get("color", note)

            return {
                "name": icon_name,
                "size": _icon_size_from_text(size_text, default=40),
                "color": _icon_color_from_text(color_text, default="#2563EB"),
                "note": note,
                "role": fields.get("role", ""),
                "anchor": fields.get("anchor", ""),
                "placement": fields.get("placement", ""),
                "reason": fields.get("reason", ""),
            }

    # Secondary: Section VI inventory table
    return _icon_from_inventory_table(design_spec, page_num)


def _icon_guidance_block(icon_assignment: dict | None) -> str:
    """Constrain icon rendering to explicit design-spec placeholders."""
    if not icon_assignment:
        return (
            "## Icon Guidance\n"
            "- This slide has no explicit design-spec icon assignment. Do not add "
            "`<use data-icon=\"...\"/>` placeholders or decorative icons.\n"
            "- Do not simulate icons with standalone letter/symbol badges inside "
            "small squares or circles, such as `P`, `Δ`, `!`, `G`, `?`, or `i`.\n"
            "- If cards need structure, use plain numbered markers only when the "
            "design spec asks for `Card Marker: numbered`; otherwise use title text "
            "and spacing.\n"
            "- If a technical concept needs a visual cue, draw a micro diagram that "
            "shows structure, such as distribution bins, residual arrows, error "
            "growth, gate sliders, stage flow, or mini charts."
        )

    name = str(icon_assignment["name"])
    size = int(icon_assignment.get("size") or 40)
    color = str(icon_assignment.get("color") or "#2563EB")
    role = str(icon_assignment.get("role") or "semantic layout anchor")
    anchor = str(icon_assignment.get("anchor") or "the nearest related content block")
    placement = str(
        icon_assignment.get("placement")
        or "reserve a small slot before laying out text and charts"
    )
    reason = str(icon_assignment.get("reason") or "").strip()
    return (
        "## Icon Guidance\n"
        f"- The design spec assigns this slide exactly one semantic icon: `{name}`.\n"
        f"- Icon role: {role}.\n"
        f"- Anchor it to: {anchor}.\n"
        f"- Natural placement: {placement}.\n"
        + (f"- Why it belongs: {reason}.\n" if reason else "")
        + "- Reserve the icon slot before placing body text, charts, or cards; then fit surrounding content around that slot.\n"
        "- Render it with a real icon placeholder so the finalizer can embed the "
        "icon library asset. Do not redraw it with inline `<path>`, `<polygon>`, "
        "or decorative geometry.\n"
        f"- Use this form with double quotes: "
        f"`<use data-icon=\"{name}\" x=\"...\" y=\"...\" width=\"{size}\" "
        f"height=\"{size}\" fill=\"{color}\"/>`.\n"
        "- Keep it visually integrated with that anchor. Do not float it in an unrelated corner, use it as wallpaper, or overlay it on charts/figures.\n"
        "- Keep it sparse and purposeful; use no other icon placeholders on this slide.\n"
        "- Do not add extra standalone letter/symbol badges as fake icons in cards."
    )


def _figure_guidance_block(
    used: list[dict],
    rejected: list[str] | None = None,
    *,
    source: str = "manuscript",
) -> str:
    """Constrain real paper-figure hrefs without limiting native SVG visuals."""
    rejected = rejected or []
    if not used:
        lines = [
            "## Paper Figure Guidance\n"
            "- This slide does not contain an explicit paper-figure token. "
            "Do not invent a paper-figure `<image href>` path. This restriction "
            "applies only to extracted paper figures; native SVG diagrams, charts, "
            "and visual treatments remain available."
        ]
        for item in rejected:
            lines.append(
                f"- Rejected paper figure token: {item}. Do not use its href; "
                "summarize the idea with native SVG or omit the image."
            )
        return "\n".join(lines)

    lines = ["## Paper Figure Guidance"]
    if source == "design_spec":
        lines.append(
            "- The design spec explicitly assigns the following paper figure(s) to this slide. "
            "Include them unless the slide would become unreadable; preserve the listed aspect ratio."
        )
    for fig in used:
        path = fig.get("path") or ""
        cap = (fig.get("caption") or "").strip().replace("\n", " ")
        if len(cap) > 160:
            cap = cap[:157] + "..."

        dim_info = ""
        w = int(fig.get("natural_width") or 0)
        h = int(fig.get("natural_height") or 0)
        if w > 0 and h > 0:
            dim_info = f" actual dimensions: {w}x{h} (ratio {w / h:.2f});"
        else:
            try:
                img_path = Path(path)
                if img_path.exists():
                    with Image.open(img_path) as img:
                        w, h = img.size
                        ratio = w / h
                        dim_info = f" actual dimensions: {w}x{h} (ratio {ratio:.2f});"
            except Exception:
                pass

        lines.append(
            f"- Allowed paper figure href: \"{path}\";{dim_info} caption: {cap}"
        )
    lines.append(
        "Use only the listed hrefs for extracted paper figures. Never substitute "
        "a different paper-figure href, reuse one from another slide, or invent "
        "a paper-figure path. This does not restrict native SVG visuals."
    )
    return "\n".join(lines)


def _asset_guidance_block(
    used: list[dict],
    rejected: list[str] | None = None,
    *,
    page_type: str | None = None,
) -> str:
    """Constrain roadshow source-material image usage."""
    rejected = rejected or []
    if (page_type or "").lower() == "cover":
        return _cover_no_image_policy_block()
    if not used:
        lines = [
            "## Roadshow Asset Guidance",
            "- This slide has no explicit `[[ASSET:id]]` assignment. Do not invent uploaded-material image paths.",
            "- If the slide needs a screenshot, device photo, data chart, certificate, video frame, or feedback image, it must be assigned through `[[ASSET:id]]`; otherwise use native SVG and mark missing materials in the private fields only.",
        ]
        for item in rejected:
            lines.append(f"- Rejected roadshow asset token: {item}. Do not invent a replacement image path.")
        return "\n".join(lines)

    lines = [
        "## Roadshow Asset Guidance",
        "- This slide is explicitly assigned uploaded roadshow source material. You MUST include at least one `<image href=\"...\">` using one of the allowed hrefs below as a main or supporting visual.",
        "- Use the exact href string; do not translate it, shorten it, or replace it with a Chinese file path.",
        "- Preserve aspect ratio with `preserveAspectRatio=\"xMidYMid slice\"` or `xMidYMid meet` depending on the crop.",
    ]
    for asset in used:
        asset_id = str(asset.get("asset_id") or "")
        href = str(asset.get("href") or asset.get("path") or "")
        cap = str(asset.get("caption") or asset.get("original_rel") or asset_id).replace("\n", " ").strip()
        asset_type = str(asset.get("asset_type") or "material_image")
        w = int(asset.get("natural_width") or 0)
        h = int(asset.get("natural_height") or 0)
        dim = f"; actual dimensions: {w}x{h}" if w > 0 and h > 0 else ""
        lines.append(f"- Allowed roadshow asset id={asset_id}; type={asset_type}; href=\"{href}\"{dim}; caption: {cap}")
    for item in rejected:
        lines.append(f"- Rejected roadshow asset token: {item}. Do not invent a replacement image path.")
    return "\n".join(lines)


# -- Character budget & image layout helpers ----------------------------------

# Content area defaults for PPT 16:9 (may be overridden by design_spec)
_DEFAULT_CONTENT_AREA = {"x": 40, "y": 100, "width": 1200, "height": 520}


def _estimate_capacity(width: int, height: int, font_size: int = 16) -> int:
    """Estimate max characters that fit in a content area."""
    line_height = int(font_size * 1.3)
    max_lines = max(1, height // line_height)
    # Average char width: blend of CJK (1.0) and Latin (0.55), assume 0.75
    avg_char_w = font_size * 0.75
    chars_per_line = max(1, int(width / avg_char_w))
    return max_lines * chars_per_line


# Width presets for common layout scenarios (content area = 1200×520)
_LAYOUT_WIDTHS = {
    "full": 1200,          # full-width body text
    "half_left": 560,      # left column in two-column
    "half_right": 560,     # right column in two-column
    "card": 480,           # card content area
    "card_narrow": 380,    # narrow card (3-column)
}

# Regex to identify structural elements in manuscript Markdown
_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[\s]*[-*•]\s+(.+)$", re.MULTILINE)


def _char_budget_block(manuscript_page: str) -> str:
    """Return a per-element character budget guide for the page.

    Instead of a single whole-page estimate, this analyses the manuscript
    structure (headings, bullets, paragraphs) and tells the LLM how many
    characters fit per line for each common layout scenario.
    """
    text = manuscript_page.strip()
    est_chars = len(text)

    # Whole-page capacity for density warning
    total_capacity = _estimate_capacity(
        _DEFAULT_CONTENT_AREA["width"],
        _DEFAULT_CONTENT_AREA["height"],
    )
    ratio = est_chars / total_capacity if total_capacity else 0

    # Per-layout character-per-line estimates at common font sizes
    lines = []
    lines.append("## Character Budget Per Line")
    lines.append("Use these limits to decide when to wrap text. "
                 "Do NOT wrap prematurely when >40% of line width is unused.")
    lines.append("")
    lines.append("| Layout | Width | font 16 cpl | font 18 cpl | font 22 cpl |")
    lines.append("|--------|-------|-------------|-------------|-------------|")
    for name, w in _LAYOUT_WIDTHS.items():
        cpl16 = int(w / (16 * 0.75))
        cpl18 = int(w / (18 * 0.75))
        cpl22 = int(w / (22 * 0.75))
        lines.append(f"| {name} | {w}px | {cpl16} | {cpl18} | {cpl22} |")

    # Count structural elements for a concrete hint
    headings = _HEADING_RE.findall(text)
    bullets = _BULLET_RE.findall(text)
    if headings or bullets:
        lines.append("")
        lines.append(f"Page structure: {len(headings)} heading(s), "
                     f"{len(bullets)} bullet(s), ~{est_chars} total chars.")

    # Density warning
    if ratio > 0.8:
        lines.append("")
        lines.append(
            f"⚠ **Density warning**: ~{est_chars} chars / ~{total_capacity} capacity "
            f"({ratio:.0%}). Consider splitting across multiple slides or condensing."
        )
    else:
        lines.append("")
        lines.append(
            f"Density: ~{est_chars} chars / ~{total_capacity} capacity ({ratio:.0%})."
        )

    return "\n".join(lines)


def _response_diagnostic(response: LLMResponse) -> str:
    usage = response.usage
    usage_text = (
        f"prompt_tokens={usage.prompt_tokens}, completion_tokens={usage.completion_tokens}"
        if usage
        else "usage=unavailable"
    )
    return (
        f"finish_reason={getattr(response, 'finish_reason', None) or 'unknown'}, "
        f"content_chars={len(response.content or '')}, {usage_text}"
    )


def _write_executor_response_debug(
    project_dir: Path,
    page_num: int,
    attempt: int,
    response: LLMResponse,
    *,
    recovery: bool = False,
) -> None:
    suffix = f"attempt{attempt:02d}{'_recovery' if recovery else ''}"
    path = project_dir / "debug" / f"executor_page_{page_num:02d}_{suffix}_response.md"
    body = response.content or ""
    text = f"<!-- {_response_diagnostic(response)} -->\n\n{body}"
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        pass


def _write_svg_recovery_note(
    project_dir: Path,
    page_num: int,
    message: str,
) -> None:
    path = project_dir / "debug" / f"executor_page_{page_num:02d}_recovery.md"
    try:
        prior = path.read_text(encoding="utf-8") if path.exists() else ""
        path.write_text((prior + message + "\n").strip() + "\n", encoding="utf-8")
    except OSError:
        pass


def _figure_layout_guidance(used_figures: list[dict]) -> str:
    """For each paper figure, recommend layout based on its aspect ratio."""
    if not used_figures:
        return ""
    ca_w = _DEFAULT_CONTENT_AREA["width"]
    ca_h = _DEFAULT_CONTENT_AREA["height"]
    lines = ["## Image Layout Recommendations"]
    for fig in used_figures:
        path = fig.get("path") or ""
        try:
            img_path = Path(path)
            if img_path.exists():
                with Image.open(img_path) as img:
                    w, h = img.size
                    r = w / h
                    if r > 1.2:
                        layout = "top-bottom"
                        img_w, img_h = ca_w, int(ca_w / r)
                        txt_area = f"{ca_w}x{ca_h - img_h - 20}"
                    else:
                        layout = "left-right"
                        img_h, img_w = ca_h, int(ca_h * r)
                        txt_area = f"{ca_w - img_w - 20}x{ca_h}"
                    lines.append(
                        f"- {Path(path).stem}: ratio={r:.2f}, "
                        f"recommended={layout}, "
                        f"image={img_w}x{img_h}, text_area={txt_area}"
                    )
                    continue
        except Exception:
            pass
        lines.append(f"- {Path(path).stem}: unable to read dimensions")
    return "\n".join(lines)


def _line_containing(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    return text[start:end]


def _extract_figure_label(text: str) -> tuple[str, str] | None:
    match = FIGURE_LABEL_RE.search(text)
    if not match:
        return None
    if match.group(1):
        kind_raw = match.group(1).lower()
        kind = "table" if kind_raw == "table" else "figure"
        return kind, match.group(2)
    kind = "figure" if match.group(3) == "图" else "table"
    return kind, match.group(4)


def _figure_label_mismatch(reference_line: str, caption: str) -> str | None:
    requested = _extract_figure_label(reference_line)
    actual = _extract_figure_label(caption)
    if not requested or not actual:
        return None
    if requested != actual:
        req_kind, req_num = requested
        actual_kind, actual_num = actual
        return (
            f"requested {req_kind} {req_num}, but inventory caption is "
            f"{actual_kind} {actual_num}"
        )
    return None


def _paper_figure_key_from_href(href: str) -> str | None:
    if href.startswith("data:"):
        return None
    normalized = href.replace("\\", "/")
    stem = Path(normalized).stem
    if stem.startswith("asset_") or "/sources/images/assets/" in normalized:
        return None
    if "/sources/images/" in normalized or stem.startswith("fig_"):
        return stem
    return None


def _validate_paper_figure_refs(
    svg_content: str,
    *,
    allowed_figures: list[dict],
    used_paper_figures: dict[str, int],
) -> CriticReport:
    allowed_keys = {
        Path(str(fig.get("path") or "")).stem
        for fig in allowed_figures
        if fig.get("path")
    }
    hrefs = IMAGE_HREF_RE.findall(svg_content)
    paper_keys = [
        key for href in hrefs if (key := _paper_figure_key_from_href(href)) is not None
    ]
    violations: list[Violation] = []

    for key in sorted(set(paper_keys)):
        if key not in allowed_keys:
            violations.append(
                Violation(
                    rule="paper_figure_not_allowed",
                    severity="error",
                    detail=(
                        f'Paper figure "{key}" is not allowed for this slide. '
                        "Remove it or replace it with one of the current page's "
                        "explicitly allowed paper-figure hrefs."
                    ),
                )
            )
        if paper_keys.count(key) > 1:
            violations.append(
                Violation(
                    rule="paper_figure_duplicate_on_slide",
                    severity="error",
                    detail=(
                        f'Paper figure "{key}" appears multiple times on this slide. '
                        "Use it once at most, or replace repeated copies with native SVG."
                    ),
                )
            )
        previous_page = used_paper_figures.get(key)
        if previous_page is not None:
            violations.append(
                Violation(
                    rule="paper_figure_reused_from_previous_slide",
                    severity="error",
                    detail=(
                        f'Paper figure "{key}" was already used on slide {previous_page}. '
                        "Do not repeat extracted paper images across slides; redraw the "
                        "idea with native SVG or choose a different explicitly allowed figure."
                    ),
                )
            )

    return CriticReport(passed=not violations, violations=violations)


def _roadshow_asset_key_from_href(href: str) -> str | None:
    if href.startswith("data:"):
        return None
    stem = Path(href.replace("\\", "/")).stem
    if stem.startswith("asset_"):
        return stem
    return None


def _validate_roadshow_asset_refs(
    svg_content: str,
    *,
    allowed_assets: list[dict],
    require_asset: bool,
) -> CriticReport:
    allowed_ids = {
        str(asset.get("asset_id") or Path(str(asset.get("path") or "")).stem)
        for asset in allowed_assets
        if asset.get("asset_id") or asset.get("path")
    }
    hrefs = IMAGE_HREF_RE.findall(svg_content)
    asset_keys = [
        key for href in hrefs if (key := _roadshow_asset_key_from_href(href)) is not None
    ]
    violations: list[Violation] = []

    if require_asset and not asset_keys:
        allowed = ", ".join(sorted(allowed_ids)) or "assigned asset"
        violations.append(
            Violation(
                rule="roadshow_required_asset_image_missing",
                severity="error",
                detail=(
                    "This slide has a provided `[[ASSET:id]]` source-material assignment "
                    f"({allowed}), but the SVG contains no matching `<image href=\"...\">`. "
                    "Insert the assigned real image as a visible main/supporting visual."
                ),
            )
        )

    for key in sorted(set(asset_keys)):
        if allowed_ids and key not in allowed_ids:
            violations.append(
                Violation(
                    rule="roadshow_asset_not_allowed",
                    severity="error",
                    detail=(
                        f'Roadshow asset "{key}" is not assigned to this slide. '
                        "Use only the current slide's `[[ASSET:id]]` hrefs or remove the image."
                    ),
                )
            )

    return CriticReport(passed=not violations, violations=violations)


def _validate_roadshow_cover_no_images(
    svg_content: str,
    *,
    page_type: str,
    page_num: int | None = None,
) -> CriticReport:
    if (page_type or "").lower() != "cover" and page_num != 1:
        return CriticReport(passed=True)
    hrefs = IMAGE_HREF_RE.findall(svg_content)
    if not hrefs:
        return CriticReport(passed=True)
    return CriticReport(
        passed=False,
        violations=[
            Violation(
                rule="roadshow_cover_image_not_allowed",
                severity="error",
                detail=(
                    "Roadshow cover must not contain image elements. Remove uploaded, "
                    "generated, screenshot, or background images and use native SVG "
                    "text, color blocks, lines, and abstract geometry instead."
                ),
            )
        ],
    )


def _fallback_text_lines_for_roadshow_asset(page_name: str, page_content: str) -> tuple[str, list[str]]:
    """Extract conservative visible copy for deterministic asset fallback pages."""
    content = re.sub(r"(?im)^\s*\[ROADSHOW ASSET[^\n]*\]\s*$", "", page_content)
    content = re.sub(r"(?im)^Roadshow asset assignment recovered for this slide:\s*$", "", content)
    lines = []
    title = page_name or "项目素材页"
    for raw in content.splitlines():
        line = raw.strip(" \t-*#`")
        if not line:
            continue
        if line.startswith("[ROADSHOW ASSET"):
            continue
        if re.match(r"(?i)^(page|section|formal_title|title)\s*:", line):
            continue
        if ":" in line and re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", line):
            continue
        if title == (page_name or "项目素材页") and raw.lstrip().startswith("#"):
            title = line[:34]
            continue
        if len(line) > 42:
            line = line[:40] + "..."
        lines.append(line)
        if len(lines) >= 5:
            break
    return title[:34] or "项目素材页", lines[:5]


def _roadshow_asset_fallback_svg(
    page_num: int,
    page_name: str,
    page_content: str,
    used_assets: list[dict],
) -> str:
    """Last-resort SVG that guarantees assigned roadshow material renders as `<image>`."""
    asset = used_assets[0]
    href = html.escape(str(asset.get("href") or asset.get("path") or ""), quote=True)
    asset_id = html.escape(str(asset.get("asset_id") or Path(href).stem or "asset"), quote=True)
    title, lines = _fallback_text_lines_for_roadshow_asset(page_name, page_content)
    title = html.escape(title, quote=False)
    safe_lines = [html.escape(line, quote=False) for line in lines if line]
    if not safe_lines:
        safe_lines = ["真实素材已接入本页主视觉", "页面结论以左侧上传材料为支撑", "右侧保留关键说明与讲解要点"]
    bullet_nodes = []
    for idx, line in enumerate(safe_lines[:5]):
        y = 210 + idx * 58
        bullet_nodes.append(
            f'<circle cx="878" cy="{y - 6}" r="5" fill="#2fbf8f"/>'
            f'<text x="898" y="{y}" font-size="22" fill="#172033">{line}</text>'
        )
    bullets = "\n      ".join(bullet_nodes)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <defs>
    <clipPath id="roadshowAssetClip{page_num}">
      <rect x="58" y="126" width="750" height="512" rx="18"/>
    </clipPath>
    <linearGradient id="roadshowBg{page_num}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f6f8fb"/>
      <stop offset="1" stop-color="#eaf3ef"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#roadshowBg{page_num})"/>
  <rect x="36" y="40" width="1208" height="636" rx="22" fill="#ffffff" stroke="#d7dee8" stroke-width="2"/>
  <text x="62" y="91" font-size="34" font-weight="700" fill="#101828">{title}</text>
  <text x="62" y="116" font-size="15" fill="#667085">上传素材主视觉 · {asset_id}</text>
  <rect x="58" y="126" width="750" height="512" rx="18" fill="#f2f4f7" stroke="#cbd5e1" stroke-width="2"/>
  <image href="{href}" x="58" y="126" width="750" height="512" preserveAspectRatio="xMidYMid meet" clip-path="url(#roadshowAssetClip{page_num})"/>
  <rect x="842" y="126" width="362" height="512" rx="18" fill="#f8fafc" stroke="#d7dee8" stroke-width="2"/>
  <text x="878" y="174" font-size="24" font-weight="700" fill="#101828">本页讲解重点</text>
  <g>
      {bullets}
  </g>
  <rect x="878" y="578" width="252" height="34" rx="17" fill="#e6f7ef"/>
  <text x="904" y="601" font-size="17" font-weight="700" fill="#087443">已使用真实上传素材</text>
</svg>'''


def _unparseable_page_fallback_svg(
    page_num: int,
    page_name: str,
    page_content: str,
    used_assets: list[dict],
) -> str:
    """Last-resort formal SVG for empty/non-SVG model responses so one page cannot kill a deck."""
    if used_assets:
        return _roadshow_asset_fallback_svg(page_num, page_name, page_content, used_assets)

    title, lines = _fallback_text_lines_for_roadshow_asset(page_name, page_content)
    title = html.escape(title or f"第 {page_num} 页", quote=False)
    safe_lines = [html.escape(line, quote=False) for line in lines if line]
    if not safe_lines:
        safe_lines = [
            "围绕本页主题展示关键事实与支撑信息",
            "突出项目问题、方案或验证链路中的核心结论",
            "用于保证整套路演结构连续完整",
        ]

    bullet_nodes = []
    for idx, line in enumerate(safe_lines[:5]):
        y = 232 + idx * 62
        bullet_nodes.append(
            f'<circle cx="132" cy="{y - 7}" r="6" fill="#06B6D4"/>'
            f'<text x="154" y="{y}" font-size="24" fill="#E2E8F0">{line}</text>'
        )
    bullets = "\n      ".join(bullet_nodes)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <defs>
    <linearGradient id="fallbackBg{page_num}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0A1628"/>
      <stop offset="1" stop-color="#102A3F"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#fallbackBg{page_num})"/>
  <rect x="54" y="46" width="1172" height="628" rx="22" fill="#111C2E" stroke="#334155" stroke-width="2"/>
  <rect x="90" y="108" width="8" height="82" rx="4" fill="#06B6D4"/>
  <text x="118" y="142" font-size="18" fill="#38BDF8">智农云控温室环境智能监测与调控系统</text>
  <text x="118" y="184" font-size="38" font-weight="700" fill="#F8FAFC">{title}</text>
  <rect x="96" y="218" width="1088" height="330" rx="18" fill="#172033" stroke="#334155" stroke-width="2"/>
  <g>
      {bullets}
  </g>
  <rect x="96" y="586" width="1088" height="46" rx="14" fill="#0F766E" fill-opacity="0.18" stroke="#0F766E" stroke-width="1"/>
  <text x="122" y="616" font-size="18" fill="#99F6E4">本页讲解重点：用关键事实支撑项目叙事，承接前后页面的路演逻辑。</text>
  <text x="1116" y="646" font-size="14" fill="#64748B">{page_num:02d}</text>
</svg>'''


def _validate_icon_refs(
    svg_content: str,
    *,
    required_icon: str | None,
) -> CriticReport:
    placeholders = [
        {"quote": match.group(1), "name": match.group(2)}
        for match in DATA_ICON_RE.finditer(svg_content)
    ]
    names = [item["name"] for item in placeholders]
    violations: list[Violation] = []

    for item in placeholders:
        if item["quote"] != '"':
            violations.append(
                Violation(
                    rule="icon_placeholder_quote_unsupported",
                    severity="error",
                    detail=(
                        f'Icon placeholder "{item["name"]}" uses single quotes. '
                        "Use double quotes so the icon finalizer can embed it."
                    ),
                )
            )

    if required_icon:
        if required_icon not in names:
            violations.append(
                Violation(
                    rule="required_icon_missing",
                    severity="error",
                    detail=(
                        f'This slide is assigned icon "{required_icon}" in the design spec, '
                        "but the SVG does not contain the required "
                        f'`<use data-icon="{required_icon}" .../>` placeholder. '
                        "Do not redraw the icon manually with inline paths."
                    ),
                )
            )
        for name in sorted(set(names)):
            if name != required_icon:
                violations.append(
                    Violation(
                        rule="unassigned_icon_placeholder",
                        severity="error",
                        detail=(
                            f'Icon placeholder "{name}" is not assigned to this slide. '
                            f'Use only "{required_icon}" or remove the extra placeholder.'
                        ),
                    )
                )
    elif names:
        for name in sorted(set(names)):
            violations.append(
                Violation(
                    rule="unassigned_icon_placeholder",
                    severity="error",
                    detail=(
                        f'Icon placeholder "{name}" is not assigned to this slide. '
                        "Remove it; restrained icon mode allows icons only on slides "
                        "with an explicit design-spec Icon line."
                    ),
                )
            )

    if not required_icon:
        violations.extend(_pseudo_icon_badge_violations(svg_content))

    return CriticReport(passed=not violations, violations=violations)


def _pseudo_icon_badge_violations(svg_content: str) -> list[Violation]:
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        return []

    small_rects: list[tuple[float, float, float, float]] = []
    small_circles: list[tuple[float, float, float]] = []
    for elem in root.iter():
        tag = _local_tag(elem.tag)
        if tag == "rect":
            x = _float_attr(elem, "x")
            y = _float_attr(elem, "y")
            w = _float_attr(elem, "width")
            h = _float_attr(elem, "height")
            if 24 <= w <= 72 and 24 <= h <= 72:
                small_rects.append((x, y, w, h))
        elif tag == "circle":
            r = _float_attr(elem, "r")
            if 10 <= r <= 36:
                small_circles.append((_float_attr(elem, "cx"), _float_attr(elem, "cy"), r))

    violations: list[Violation] = []
    for elem in root.iter():
        if _local_tag(elem.tag) != "text":
            continue
        text = "".join(elem.itertext()).strip()
        if text not in PSEUDO_ICON_BADGE_TEXT:
            continue
        x = _float_attr(elem, "x")
        y = _float_attr(elem, "y")
        font_size = _float_attr(elem, "font-size", 18.0)
        inside_rect = any(
            rx <= x <= rx + rw and ry <= y <= ry + rh + font_size * 0.4
            for rx, ry, rw, rh in small_rects
        )
        inside_circle = any(
            abs(x - cx) <= r * 0.75 and abs(y - (cy + font_size * 0.35)) <= r
            for cx, cy, r in small_circles
        )
        if inside_rect or inside_circle:
            violations.append(
                Violation(
                    rule="pseudo_icon_badge_not_allowed",
                    severity="error",
                    detail=(
                        f'Standalone badge "{text}" looks like a fake icon, but this '
                        "slide has `Icon: None`. Replace it with a numbered card marker "
                        "only if requested, or with a micro diagram such as distribution "
                        "bins, residual arrows, error growth, a gate slider, or stage flow."
                    ),
                )
            )
    return violations


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _float_attr(elem: ET.Element, name: str, default: float = 0.0) -> float:
    try:
        return float(elem.get(name, default))
    except (TypeError, ValueError):
        return default


def _merge_reports(*reports: CriticReport) -> CriticReport:
    violations: list[Violation] = []
    canvas = None
    for report in reports:
        violations.extend(report.violations)
        canvas = canvas or report.canvas
    return CriticReport(
        passed=all(report.passed for report in reports),
        violations=violations,
        canvas=canvas,
    )


def _is_roadshow_generation(style: str, design_spec: str, manuscript: str) -> bool:
    """Return true for vocational roadshow decks without affecting paper decks."""
    style_text = (style or "").lower()
    if "roadshow" in style_text or "competition" in style_text:
        return True
    sample = f"{design_spec[:4000]}\n{manuscript[:4000]}"
    return (
        "职业院校技能大赛" in sample
        or ("primary_visual:" in sample and "stage_mode:" in sample)
        or "Roadshow Formal Guardrails" in sample
    )


def _roadshow_visible_text_report(svg_content: str) -> CriticReport:
    """Critic report for roadshow-only visible text leakage."""
    violations = [
        Violation(
            rule=f"roadshow_visible_text_{item.rule}",
            severity="error",
            detail=(
                "Roadshow slides must look like participant-facing competition "
                "materials. Remove internal scoring/runbook/gate wording from "
                f"visible SVG text: {item.phrase!r} in {item.context!r}."
            ),
        )
        for item in scan_svg_visible_text(svg_content)
    ]
    return CriticReport(passed=not violations, violations=violations)


async def generate_svg_pages(
    design_spec: str,
    manuscript: str,
    project_dir: Path,
    llm: LLMProvider,
    model: str,
    *,
    style: str = "academic",
    language: str = "en",
    detail_level: str = "normal",
    extra_instruction: str = "",
    target_pages: set[int] | None = None,
    critic_config: CriticConfig | None = None,
    on_critic: CriticCallback | None = None,
    on_svg_update: SvgUpdateCallback | None = None,
    on_page_status: PageStatusCallback | None = None,
    figure_inventory: list[dict] | None = None,
    enable_visual_critic: bool = False,
    max_critic_attempts: int = DEFAULT_MAX_CRITIC_ATTEMPTS,
    visual_qa_max_attempts: int = 1,
    visual_critic_llm: LLMProvider | None = None,
    visual_critic_model: str | None = None,
    visual_critic_config: VisualCriticConfig | None = None,
    template_context: str | None = None,
    template_skeletons: dict[str, str] | None = None,
    resume_existing: bool = True,
) -> AsyncIterator[tuple[int, str]]:
    """Generate SVG code for each slide page sequentially."""
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    standards_path = settings.references_dir / "shared-standards-essential.md"
    if not standards_path.exists():
        standards_path = settings.references_dir / "shared-standards.md"
    standards = ""
    if standards_path.exists():
        standards = standards_path.read_text(encoding="utf-8")

    pages = split_manuscript_pages(manuscript)
    is_roadshow = _is_roadshow_generation(style, design_spec, manuscript)
    asset_registry = load_asset_registry(project_dir) if is_roadshow else {}
    svg_output_dir = project_dir / "svg_output"
    svg_output_dir.mkdir(parents=True, exist_ok=True)
    repair_archive_dir = project_dir / "svg_archive" / "repair"
    used_paper_figures: dict[str, int] = {}
    if max_critic_attempts is None:
        max_critic_attempts = DEFAULT_MAX_CRITIC_ATTEMPTS
    max_critic_attempts = max(0, int(max_critic_attempts))
    visual_qa_max_attempts = max(0, int(visual_qa_max_attempts or 0))

    extra_sections = []
    if extra_instruction:
        extra_sections.append(extra_instruction)
    if is_deepseek_provider(llm, model):
        extra_sections.append(deepseek_executor_guidance(detail_level))
    if template_context:
        extra_sections.append(template_context)
    extra_block = "\n\n" + "\n\n".join(extra_sections) if extra_sections else ""
    compact_design_context = _global_design_context(design_spec)
    conversation: list[LLMMessage] = [
        LLMMessage.system(system_prompt),
        LLMMessage.user(
            f"## Global Design Context (compact)\n\n{compact_design_context}\n\n"
            f"## SVG Technical Standards\n\n{standards}\n\n"
            f"## Fixed Runtime Configuration\n\n"
            f"- Selected style preset: {style}\n"
            f"- Selected language: {language}\n"
            f"- Selected detail level: {detail_level}\n"
            f"- Do not replace the requested style with another preset.\n"
            f"- All visible SVG text must follow the selected language unless a proper noun must stay in its original form.\n\n"
            f"Total pages to generate: {len(pages)}\n\n"
            f"You will generate SVG code for each page sequentially. "
            f"I will provide a self-contained Page Render Spec for each page. "
            f"Do not ask for or rely on the full manuscript or full design_spec."
            f"{extra_block}"
        ),
        LLMMessage.assistant(
            "Understood. I have the design specification and technical constraints. "
            "Please provide the content for page 1."
        ),
    ]

    # Save full initial prompt for debugging
    try:
        debug_dir = project_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = debug_dir / "executor_prompt.md"
        parts = []
        for msg in conversation:
            parts.append(f"--- ROLE: {msg.role} ---\n\n{msg.content}")
        prompt_file.write_text("\n\n".join(parts), encoding="utf-8")
    except Exception:
        pass

    # Track how many page exchanges we've appended beyond the preamble
    # (system + design-spec user + ack assistant = 3 preamble messages).
    _preamble_len = len(conversation)

    for i, page_content in enumerate(pages):
        page_num = i + 1
        if target_pages is not None and page_num not in target_pages:
            continue

        if resume_existing:
            cached_svg = _cached_svg_for_page(svg_output_dir, page_num)
            if cached_svg:
                await _emit_page_status(
                    on_page_status,
                    page_num,
                    0,
                    "cached",
                    f"第 {page_num}/{len(pages)} 页已存在，直接复用缓存",
                    {"page": page_num, "cached": True},
                )
                for href in IMAGE_HREF_RE.findall(cached_svg):
                    key = _paper_figure_key_from_href(href)
                    if key is not None:
                        used_paper_figures.setdefault(key, page_num)
                yield page_num, cached_svg
                continue

        # Sliding window: trim old page exchanges, keeping only the most
        # recent ones to avoid unbounded context growth.  Each page
        # produces up to max_critic_attempts * 2 messages
        # (user prompt + assistant SVG per round).
        _max_context_msgs = MAX_PRIOR_PAGES_IN_CONTEXT * max(1, max_critic_attempts) * 2
        _beyond_preamble = len(conversation) - _preamble_len
        if _beyond_preamble > _max_context_msgs:
            _trim = _beyond_preamble - _max_context_msgs
            conversation[:] = conversation[:_preamble_len] + conversation[_preamble_len + _trim:]

        page_name = _make_page_name(page_num, page_content)
        page_type = "cover" if page_num == 1 else _classify_page_type(page_content)
        page_design_context = _page_design_context(design_spec, page_num)
        visible_page_content = strip_page_type_metadata(page_content)
        roadshow_guidance = ""
        if is_roadshow:
            roadshow_guidance = extract_roadshow_executor_guidance(visible_page_content)
            visible_page_content = sanitize_page_for_executor(visible_page_content)
        rewritten_content, used_figures, rejected_figures = _resolve_fig_tokens(
            visible_page_content,
            figure_inventory,
        )
        rewritten_content, used_assets, rejected_assets = _resolve_asset_tokens(
            rewritten_content,
            asset_registry,
            token_source=f"{page_content}\n\n{visible_page_content}\n\n{roadshow_guidance}",
        )
        if is_roadshow and page_type == "cover":
            roadshow_guidance = _strip_roadshow_asset_assignment_text(roadshow_guidance)
            rewritten_content = _strip_roadshow_asset_assignment_text(rewritten_content)
            page_design_context = (
                f"{_strip_roadshow_asset_assignment_text(page_design_context)}\n\n"
                f"{_cover_no_image_policy_block()}"
            ).strip()
            if used_assets or used_figures:
                rewritten_content = (
                    f"{rewritten_content}\n\n"
                    "Roadshow cover visual policy: do not use image assets or paper figures on the cover. "
                    "Use native SVG title typography, color blocks, lines, and abstract geometry only."
                )
            used_assets = []
            rejected_assets = []
            used_figures = []
            rejected_figures = []
        figure_source = "manuscript"
        if not used_figures:
            design_spec_figures = _figures_from_design_spec_for_page(
                design_spec,
                page_num,
                figure_inventory,
                page_type,
            )
            if design_spec_figures:
                figure_source = "design_spec"
                used_figures = design_spec_figures
                fallback_refs = "\n".join(
                    _paper_figure_reference_line(fig) for fig in design_spec_figures
                )
                rewritten_content = (
                    f"{rewritten_content}\n\n"
                    "Design spec image assignment recovered for this slide:\n"
                    f"{fallback_refs}"
                )
        figure_guidance = _figure_guidance_block(
            used_figures,
            rejected_figures,
            source=figure_source,
        )
        asset_guidance = _asset_guidance_block(used_assets, rejected_assets, page_type=page_type) if is_roadshow else ""
        icon_assignment = _icon_from_design_spec_for_page(design_spec, page_num)
        required_icon = (
            str(icon_assignment["name"]) if icon_assignment is not None else None
        )
        icon_guidance = _icon_guidance_block(icon_assignment)
        char_budget = _char_budget_block(rewritten_content)
        img_layout = _figure_layout_guidance(used_figures)
        render_content = _limit_text(
            rewritten_content,
            MAX_PAGE_RENDER_CONTENT_CHARS,
            label=f"page {page_num} render content",
        )

        # Build skeleton injection block if template skeletons are available
        skeleton_block = ""
        if template_skeletons:
            skeleton_svg = template_skeletons.get(page_type)
            if skeleton_svg:
                skeleton_block = (
                    f"\n\n## Template Skeleton ({page_type} page)\n"
                    f"Use this SVG as your starting point. Replace {{{{PLACEHOLDER}}}} tokens "
                    f"with actual content below. Preserve ALL decorative elements, gradients, "
                    f"and structural chrome. Do NOT rewrite from scratch.\n\n"
                    f"```svg\n{skeleton_svg}\n```"
                )

        roadshow_visual_boost = ""
        if (style or "").lower() == "roadshow" or "roadshow" in (project_dir.name if project_dir else ""):
            roadshow_visual_boost = (
                "## Competition Roadshow Visual Quality Bar\n"
                "- Design for a 16:9 stage screen: clear hierarchy, large titles, generous margins (≥48px).\n"
                "- One dominant visual object (diagram / process / dashboard / board) should occupy 55-70% of the content area; avoid equal 4-card grids as the main layout.\n"
                "- Visible copy: title + 1 core sentence + 3-5 short bullets max; no walls of text.\n"
                "- Use a cohesive teal/indigo professional palette with one accent for the key claim; high contrast body text.\n"
                "- Prefer process arrows, layered architecture, or metric callouts over decorative lines alone.\n"
                "- Leave breathing room; align columns to a consistent grid; no overlapping text/shapes.\n"
                "- Do not invent fake screenshots or certificates; use clean schematic SVG when real assets are absent.\n"
            )
        page_render_spec = (
            f"## Page {page_num}/{len(pages)}: {page_name}\n\n"
            f"## Page Design Context\n\n"
            f"{page_design_context or '- No per-page design outline found; use the page content and global design context.'}\n\n"
            f"## Page Render Content\n\n"
            f"{render_content}\n\n"
            f"## Runtime Reminders\n"
            f"- Style preset: {style}\n"
            f"- Language: {language}\n"
            f"- Detail level: {detail_level}\n"
            f"- Page type: {page_type}. Use this type only for template selection; do not render metadata comments.\n"
            f"- Use only the supplied visible page content as slide copy.\n"
            f"- For roadshow decks, never render scoring, points, internal field names, command cues, operator roles, export gates, draft states, placeholders, evidence-gap labels, or the Chinese word `证据` as visible text. Use 支撑材料、运行记录、验证结果、成果材料、资料来源 instead.\n"
            f"- For roadshow cover pages, do not use `<image>` at all. Build the cover with native SVG typography, color blocks, lines, and abstract geometry; no uploaded, generated, screenshot, or background image.\n"
            f"- Keep all visible text in the requested language.\n"
            f"- {char_budget}\n\n"
            f"{roadshow_visual_boost}\n"
            f"{roadshow_guidance}\n\n"
            f"{figure_guidance}\n\n"
            f"{asset_guidance}\n\n"
            f"{icon_guidance}\n\n"
            f"{img_layout}\n\n"
            f"Generate the complete SVG code for this page. "
            f"Output ONLY the SVG code, wrapped in ```svg code block."
            f"{skeleton_block}"
        )
        conversation.append(LLMMessage.user(page_render_spec))
        await _emit_page_status(
            on_page_status,
            page_num,
            1,
            "generation",
            f"开始生成第 {page_num}/{len(pages)} 页：{page_name}",
            {"page_name": page_name, "page_type": page_type},
        )
        try:
            debug_dir = project_dir / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            prompt_file = debug_dir / f"executor_page_{page_num:02d}_prompt.md"
            parts = [f"--- ROLE: {msg.role} ---\n\n{msg.content}" for msg in conversation]
            prompt_file.write_text("\n\n".join(parts), encoding="utf-8")
        except OSError:
            pass

        snapshot = set_usage_context(stage="generation", page=page_num, attempt=1)
        try:
            response: LLMResponse = await _chat_with_page_status(
                llm,
                conversation,
                model,
                temperature=0.3,
                max_tokens=16384,
                page_num=page_num,
                total_pages=len(pages),
                attempt=1,
                phase="generation",
                on_page_status=on_page_status,
            )
        finally:
            reset_usage_context(snapshot)
        _write_executor_response_debug(project_dir, page_num, 1, response)

        svg_content = _extract_svg(response.content)
        empty_recovery_attempts = 0
        for extraction_attempt in range(2, MAX_SVG_EXTRACTION_ATTEMPTS + 1):
            if svg_content:
                break
            is_empty_response = not (response.content or "").strip()
            if is_empty_response and empty_recovery_attempts < MAX_EMPTY_RESPONSE_RECOVERY_ATTEMPTS:
                empty_recovery_attempts += 1
                _write_svg_recovery_note(
                    project_dir,
                    page_num,
                    (
                        f"attempt={extraction_attempt}: empty model response; "
                        f"{_response_diagnostic(response)}; using compact recovery prompt"
                    ),
                )
                retry_messages = _build_empty_response_recovery_messages(
                    page_num=page_num,
                    total_pages=len(pages),
                    page_name=page_name,
                    page_type=page_type,
                    compact_design_context=compact_design_context,
                    page_design_context=page_design_context,
                    page_content=render_content,
                    roadshow_guidance=roadshow_guidance,
                    figure_guidance=figure_guidance,
                    asset_guidance=asset_guidance,
                    icon_guidance=icon_guidance,
                    style=style,
                    language=language,
                )
                recovery_call = True
            else:
                if response.content:
                    conversation.append(LLMMessage.assistant(response.content))
                conversation.append(
                    LLMMessage.user(
                        _build_svg_extraction_retry_prompt(
                            page_num=page_num,
                            total_pages=len(pages),
                            page_name=page_name,
                            page_content=page_content,
                            attempt=extraction_attempt,
                        )
                    )
                )
                retry_messages = conversation
                recovery_call = False
            snapshot = set_usage_context(
                stage="generation", page=page_num, attempt=extraction_attempt
            )
            try:
                response = await _chat_with_page_status(
                    llm,
                    retry_messages,
                    model,
                    temperature=0.15 if recovery_call else 0.2,
                    max_tokens=16384,
                    page_num=page_num,
                    total_pages=len(pages),
                    attempt=extraction_attempt,
                    phase="recovery" if recovery_call else "generation",
                    on_page_status=on_page_status,
                )
            finally:
                reset_usage_context(snapshot)
            _write_executor_response_debug(
                project_dir,
                page_num,
                extraction_attempt,
                response,
                recovery=recovery_call,
            )
            svg_content = _extract_svg(response.content)

        if svg_content:
            conversation.append(LLMMessage.assistant(f"```svg\n{svg_content}\n```"))

            best_svg = svg_content
            visual_attempts = 0
            critic_attempt = 1
            while True:
                if max_critic_attempts <= 0:
                    best_svg = svg_content
                    break
                report = _merge_reports(
                    check_svg(svg_content, critic_config),
                    _validate_paper_figure_refs(
                        svg_content,
                        allowed_figures=used_figures,
                        used_paper_figures=used_paper_figures,
                    ),
                    _validate_roadshow_asset_refs(
                        svg_content,
                        allowed_assets=used_assets,
                        require_asset=bool(used_assets),
                    )
                    if is_roadshow
                    else CriticReport(passed=True),
                    _validate_roadshow_cover_no_images(svg_content, page_type=page_type, page_num=page_num)
                    if is_roadshow
                    else CriticReport(passed=True),
                    _validate_icon_refs(svg_content, required_icon=required_icon),
                    _roadshow_visible_text_report(svg_content)
                    if is_roadshow
                    else CriticReport(passed=True),
                )
                # Archive pre-repair SVG on first violation detection
                first_archive: str | None = None
                if not report.passed:
                    try:
                        repair_archive_dir.mkdir(parents=True, exist_ok=True)
                        archive_filename = f"p{page_num:02d}_attempt{critic_attempt}.svg"
                        archive_path = repair_archive_dir / archive_filename
                        archive_path.write_text(svg_content, encoding="utf-8")
                        first_archive = f"svg_archive/repair/{archive_filename}"
                    except OSError:
                        pass

                # When the static critic is satisfied, run visual critic
                # passes if enabled. Visual issues become the next repair
                # prompt, bounded by the static critic budget.
                if report.passed:
                    if on_critic is not None:
                        await on_critic(
                            page_num,
                            critic_attempt,
                            report,
                            None,
                            first_archive,
                        )
                    if enable_visual_critic and visual_attempts < visual_qa_max_attempts:
                        visual_attempts += 1
                        snapshot = set_usage_context(
                            stage="visual_qa", page=page_num, attempt=visual_attempts
                        )
                        try:
                            visual_outcome = await visual_check(
                                svg_content,
                                llm=visual_critic_llm or llm,
                                model=visual_critic_model or model,
                                page_num=page_num,
                                page_title=page_name,
                                style=style,
                                config=visual_critic_config,
                            )
                        finally:
                            reset_usage_context(snapshot)
                        if on_critic is not None:
                            await on_critic(
                                page_num,
                                critic_attempt,
                                visual_outcome.report,
                                None,
                                None,
                            )
                        if (
                            visual_outcome.rendered
                            and not visual_outcome.report.passed
                        ):
                            report = visual_outcome.report
                            # fall through to the repair prompt below
                        else:
                            best_svg = svg_content
                            break
                    else:
                        best_svg = svg_content
                        break

                if critic_attempt >= max_critic_attempts:
                    await _emit_page_status(
                        on_page_status,
                        page_num,
                        critic_attempt,
                        "repair_exhausted",
                        f"第 {page_num}/{len(pages)} 页已达到修复上限，保留当前可用版本继续生成后续页面",
                        {"max_critic_attempts": max_critic_attempts},
                    )
                    best_svg = svg_content
                    break

                # Archive pre-repair SVG for before/after comparison
                archive_rel: str | None = None
                try:
                    repair_archive_dir.mkdir(parents=True, exist_ok=True)
                    archive_filename = f"p{page_num:02d}_attempt{critic_attempt + 1}.svg"
                    archive_path = repair_archive_dir / archive_filename
                    archive_path.write_text(svg_content, encoding="utf-8")
                    archive_rel = f"svg_archive/repair/{archive_filename}"
                except OSError:
                    pass

                repair_prompt_text = (
                    report.to_prompt_block()
                    + "\n\nReturn the complete corrected SVG only, "
                    "wrapped in a ```svg code block."
                )
                if on_critic is not None:
                    await on_critic(
                        page_num,
                        critic_attempt,
                        report,
                        repair_prompt_text,
                        archive_rel or first_archive,
                    )
                await _emit_page_status(
                    on_page_status,
                    page_num,
                    critic_attempt + 1,
                    "repair",
                    f"第 {page_num}/{len(pages)} 页校验未通过，进入第 {critic_attempt + 1} 次修复",
                    {
                        "errors": report.error_count,
                        "warnings": report.warning_count,
                        "archive_path": archive_rel or first_archive,
                    },
                )
                conversation.append(LLMMessage.user(repair_prompt_text))
                repair_temp = max(0.1, 0.3 - 0.1 * critic_attempt)
                snapshot = set_usage_context(
                    stage="repair", page=page_num, attempt=critic_attempt + 1
                )
                try:
                    response = await _chat_with_page_status(
                        llm,
                        conversation,
                        model,
                        temperature=repair_temp,
                        max_tokens=16384,
                        page_num=page_num,
                        total_pages=len(pages),
                        attempt=critic_attempt + 1,
                        phase="repair",
                        on_page_status=on_page_status,
                    )
                finally:
                    reset_usage_context(snapshot)

                repaired = _extract_svg(response.content)
                if repaired:
                    svg_content = repaired
                    best_svg = repaired
                    conversation.append(
                        LLMMessage.assistant(f"```svg\n{repaired}\n```")
                    )
                    if on_svg_update is not None:
                        await on_svg_update(page_num, repaired)
                else:
                    conversation.append(LLMMessage.assistant(response.content))
                    break
                critic_attempt += 1

            if is_roadshow and used_assets:
                asset_report = _validate_roadshow_asset_refs(
                    best_svg,
                    allowed_assets=used_assets,
                    require_asset=True,
                )
                if not asset_report.passed:
                    best_svg = _roadshow_asset_fallback_svg(
                        page_num,
                        page_name,
                        rewritten_content,
                        used_assets,
                    )
                    try:
                        repair_archive_dir.mkdir(parents=True, exist_ok=True)
                        continuity_path = repair_archive_dir / f"p{page_num:02d}_asset_continuity.svg"
                        continuity_path.write_text(best_svg, encoding="utf-8")
                    except OSError:
                        pass
                    if on_critic is not None:
                        await on_critic(
                            page_num,
                            critic_attempt,
                            asset_report,
                            "Source material reference was not render-ready; kept an editable source-material layout and continued generation.",
                            f"svg_archive/repair/p{page_num:02d}_asset_continuity.svg",
                        )
                    if on_svg_update is not None:
                        await on_svg_update(page_num, best_svg)

            if is_roadshow and page_num == 1:
                best_svg = strip_svg_image_elements(best_svg)

            svg_path = svg_output_dir / f"{page_num:02d}_{page_name}.svg"
            svg_path.write_text(best_svg, encoding="utf-8")
            await _emit_page_status(
                on_page_status,
                page_num,
                0,
                "page_complete",
                f"第 {page_num}/{len(pages)} 页已生成并写入文件",
                {"svg_path": str(svg_path)},
            )
            for href in IMAGE_HREF_RE.findall(best_svg):
                key = _paper_figure_key_from_href(href)
                if key is not None:
                    used_paper_figures.setdefault(key, page_num)
            yield page_num, best_svg
        else:
            conversation.append(LLMMessage.assistant(response.content))
            best_svg = _unparseable_page_fallback_svg(
                page_num,
                page_name,
                rewritten_content,
                used_assets if is_roadshow else [],
            )
            continuity_rel = f"svg_archive/repair/p{page_num:02d}_unparseable_continuity.svg"
            try:
                repair_archive_dir.mkdir(parents=True, exist_ok=True)
                (repair_archive_dir / f"p{page_num:02d}_unparseable_continuity.svg").write_text(
                    best_svg,
                    encoding="utf-8",
                )
            except OSError:
                pass
            _write_svg_recovery_note(
                project_dir,
                page_num,
                (
                    "final: no parseable SVG after repair attempts; "
                    f"kept formal editable continuity SVG at {continuity_rel}"
                ),
            )

            if is_roadshow and page_num == 1:
                best_svg = strip_svg_image_elements(best_svg)

            svg_path = svg_output_dir / f"{page_num:02d}_{page_name}.svg"
            svg_path.write_text(best_svg, encoding="utf-8")
            await _emit_page_status(
                on_page_status,
                page_num,
                0,
                "repair_continuity",
                f"第 {page_num}/{len(pages)} 页已保留可编辑版本并继续生成，后续可单页精修",
                {"svg_path": str(svg_path), "editable_continuity": True},
            )
            for href in IMAGE_HREF_RE.findall(best_svg):
                key = _paper_figure_key_from_href(href)
                if key is not None:
                    used_paper_figures.setdefault(key, page_num)
            yield page_num, best_svg


def _classify_page_type(page_content: str) -> str:
    """Classify a page from manuscript metadata only."""
    return extract_page_type(page_content)


def _make_page_name(num: int, content: str) -> str:
    """Generate a clean filename from page content."""
    match = re.match(r"^##?\s+(.+)$", content, re.MULTILINE)
    if match:
        name = match.group(1).strip()
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"\s+", "_", name)
        return name[:40].lower()
    return f"page_{num}"


def _extract_svg(text: str) -> str | None:
    """Extract SVG content from LLM response."""
    match = re.search(r"```(?:svg|xml)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        svg = match.group(1).strip()
        if svg.startswith("<svg"):
            return svg

    match = re.search(r"(<svg[^>]*>.*?</svg>)", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def _build_empty_response_recovery_messages(
    *,
    page_num: int,
    total_pages: int,
    page_name: str,
    page_type: str,
    compact_design_context: str,
    page_design_context: str,
    page_content: str,
    roadshow_guidance: str,
    figure_guidance: str,
    asset_guidance: str,
    icon_guidance: str,
    style: str,
    language: str,
) -> list[LLMMessage]:
    """Build a smaller one-shot render prompt after provider empty responses."""
    return [
        LLMMessage.system(
            "You are a resilient SVG renderer for presentation slides. "
            "Return exactly one complete SVG document. Do not explain, do not use Markdown, "
            "do not ask questions."
        ),
        LLMMessage.user(
            f"Generate page {page_num}/{total_pages}: {page_name}\n\n"
            "Canvas: 1280x720, viewBox=\"0 0 1280 720\". "
            "Use a formal competition-roadshow style. Keep all content inside the safe area.\n\n"
            f"Style={style}; Language={language}; Page type={page_type}\n\n"
            "## Compact Design Context\n"
            f"{_limit_text(compact_design_context, 5200, label='compact design context')}\n\n"
            "## Page Design Context\n"
            f"{_limit_text(page_design_context or '', 2600, label='page design context') or '- Use a clean formal layout.'}\n\n"
            "## Visible Page Content\n"
            f"{_limit_text(page_content, 5200, label='page content')}\n\n"
            f"{_limit_text(roadshow_guidance, 1800, label='roadshow guidance')}\n\n"
            f"{_limit_text(figure_guidance, 1200, label='figure guidance')}\n\n"
            f"{_limit_text(asset_guidance, 1600, label='asset guidance')}\n\n"
            f"{_limit_text(icon_guidance, 900, label='icon guidance')}\n\n"
            "Output requirements:\n"
            "- Start with <svg and end with </svg>.\n"
            "- Do not include ``` fences.\n"
            "- Do not render internal fields, errors, fallback labels, debug text, or placeholders.\n"
            "- If this is page 1 or a cover page, do not include any `<image>` element; use native SVG typography and abstract geometry only.\n"
            "- If real material is assigned, include it as a visible <image href=\"...\">.\n"
        ),
    ]


def _build_svg_extraction_retry_prompt(
    *,
    page_num: int,
    total_pages: int,
    page_name: str,
    page_content: str,
    attempt: int,
) -> str:
    """Build structured feedback when the model output is not parseable SVG."""
    return (
        "## Generation Validation Report\n\n"
        f"The previous response for page {page_num}/{total_pages} ({page_name}) "
        "did not contain a parseable complete SVG document.\n\n"
        "## Failure\n"
        "- No complete `<svg ...>...</svg>` block could be extracted.\n"
        "- The current page has not been generated yet.\n\n"
        "## Regeneration Instructions\n"
        f"- Regenerate page {page_num}/{total_pages} only; do not move to another page.\n"
        "- Preserve the page content below; do not invent a different slide.\n"
        "- Return one complete SVG document, wrapped in a ```svg code block.\n"
        "- The SVG must start with `<svg` and end with `</svg>`.\n\n"
        f"## Page Content To Render\n\n{page_content}\n\n"
        f"## Retry Attempt\n\n{attempt}"
    )
