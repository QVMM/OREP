"""Strategist agent: produces a design specification from a manuscript."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from backend.config import CANVAS_FORMATS, DESIGN_STYLES, settings
from backend.generator.icon_index import get_icon_index
from backend.llm import LLMMessage, LLMProvider, LLMResponse
from backend.orchestrator.manuscript import (
    count_manuscript_pages,
    format_page_inventory,
    page_inventory,
)
from backend.orchestrator.provider_guidance import (
    deepseek_strategy_guidance,
    is_deepseek_provider,
)
from backend.orchestrator.roadshow_quality import (
    LockedFacts,
    build_roadshow_strategist_guardrails,
    enforce_locked_title_in_design_spec,
    filter_roadshow_figure_inventory,
)

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "strategist.md"
DESIGN_SPEC_MAX_TOKENS = 24576
MAX_DESIGN_SPEC_ATTEMPTS = 2

# Number of icon candidates to pre-select via RAG
ICON_CANDIDATE_COUNT = 30
# Number of search queries to extract from manuscript
ICON_QUERY_COUNT = 8
OFFLINE_ICON_CANDIDATE_COUNT = 28


def _design_spec_token_budget(page_count: int) -> int:
    """Scale strategist output to the deck instead of always requesting 24K."""
    return min(
        DESIGN_SPEC_MAX_TOKENS,
        max(8192, 6000 + max(1, page_count) * 800),
    )

OFFLINE_ICON_PALETTE: list[tuple[str, str, list[str]]] = [
    ("warning / failure mode", "occlusion risk, noisy feature, error propagation, invalid assumption", ["alert-triangle", "circle-exclamation", "alert-circle", "ban", "bug"]),
    ("insight / key idea", "turning point, core thesis, design intuition, important takeaway", ["lightbulb", "sparkles", "bulb", "brain"]),
    ("framework / architecture", "model block, stacked decoder, module composition, hierarchy", ["puzzle", "component", "cube", "layers", "stack", "binary-tree"]),
    ("method / process", "pipeline, stage transition, iterative update, tuning or regulation", ["route", "git-branch", "arrow-right", "settings", "cog", "sliders"]),
    ("result / metric", "quantitative result, AP gain, trade-off, target objective", ["chart-bar", "chart-line", "chart-pie", "activity", "target"]),
    ("evidence / experiment", "ablation, table result, experimental support, dataset evidence", ["flask", "microscope", "clipboard", "database"]),
    ("visibility / perception", "visible/occluded evidence, observation, localization, attention", ["eye", "search", "crosshairs"]),
    ("robustness / safety", "reliability, protection from bad updates, gated trust", ["shield", "lock", "key"]),
    ("people / pose", "person, crowd, keypoint, human pose, accessibility", ["users", "user", "accessibility"]),
    ("future / contribution", "implication, next step, contribution summary, closing message", ["rocket", "flag", "trophy", "book", "file-text"]),
]


def _extract_icon_queries(manuscript: str) -> list[str]:
    """Extract semantic queries for icon search from manuscript content.

    Parses page titles and key concepts from the slide-structured manuscript
    to generate targeted icon search queries.
    """
    queries: list[str] = []

    # Extract page titles (## headings)
    for m in re.finditer(r"^##\s+(.+)$", manuscript, re.MULTILINE):
        title = m.group(1).strip()
        # Clean up numbering like "1. " or "Page 1: "
        title = re.sub(r"^\d+[\.\):\s]+", "", title).strip()
        if title and len(title) > 2:
            queries.append(title)

    # Extract bold concepts (**text**)
    for m in re.finditer(r"\*\*([^*]{3,50})\*\*", manuscript):
        concept = m.group(1).strip()
        if concept not in queries:
            queries.append(concept)

    return queries[:ICON_QUERY_COUNT]


async def _retrieve_icon_candidates(
    manuscript: str,
    lib: str,
    gemini_api_key: str | None = None,
) -> str:
    """Retrieve icon candidates for the chosen library using RAG.

    Returns a formatted string listing candidate icons for injection
    into the strategist prompt.  Wrapped in asyncio.to_thread() so that
    the blocking Gemini embedding call does not prevent task cancellation.
    """
    import os

    # Temporarily set GEMINI_API_KEY if provided via frontend config
    old_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key

    index = get_icon_index()
    if not index.is_available:
        logger.warning("Icon index not available, skipping RAG retrieval")
        return ""

    queries = _extract_icon_queries(manuscript)
    if not queries:
        return ""

    # Collect candidates from all queries — run blocking search in a thread
    # so that asyncio cancellation can interrupt it.
    seen_paths: set[str] = set()
    candidates: list[dict] = []

    for query in queries:
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(index.search, query, lib=lib, k=5),
                timeout=30,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            logger.warning("Icon search timed out or was cancelled for query: %s", query)
            break
        for r in results:
            path = str(r.get("path") or "")
            if path in seen_paths:
                continue
            if not _icon_asset_exists(path):
                logger.warning("Skipping stale icon RAG candidate with missing local asset: %s", path)
                continue
            seen_paths.add(path)
            candidates.append(r)

    # Sort by score descending, take top N
    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:ICON_CANDIDATE_COUNT]

    # Restore original key
    if gemini_api_key:
        if old_key is not None:
            os.environ["GEMINI_API_KEY"] = old_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)

    if not candidates:
        return ""

    # Format as a compact table for prompt injection
    lines = [
        f"\n## Available Icon Candidates ({lib} library, {len(candidates)} icons)",
        "",
        "Semantic-searched from manuscript content. Use only when justified by clear design purpose.",
        "",
        "| # | Icon Path | Category | Tags |",
        "|---|-----------|----------|------|",
    ]

    for i, c in enumerate(candidates, 1):
        tags = ", ".join(c.get("tags", [])[:5])
        cat = c.get("category", "-")
        lines.append(f"| {i} | `{c['path']}` | {cat} | {tags} |")

    lines.append("")
    lines.append(
        "Use the icon path with the `<use data-icon=\"...\"/>` placeholder syntax. "
        "Example: `<use data-icon=\"chart-bar\" x=\"100\" y=\"200\" width=\"32\" height=\"32\" fill=\"#0076A8\"/>`"
    )
    lines.append("")

    return "\n".join(lines)


def _icon_asset_exists(icon_path: str) -> bool:
    if "/" not in icon_path:
        return False
    lib, name = icon_path.split("/", 1)
    return (settings.icons_dir / lib / f"{name}.svg").exists()


def _normalize_missing_icon_assets(text: str) -> str:
    """Downgrade non-existent icon paths instead of failing the whole deck."""

    def replace(match: re.Match[str]) -> str:
        icon_path = match.group(1).strip()
        if icon_path.endswith("/name") or _icon_asset_exists(icon_path):
            return match.group(0)
        return "`None`"

    return re.sub(r"`((?:chunk|tabler-filled|tabler-outline)/[^`]+)`", replace, text)


def _offline_icon_candidates_block(lib: str) -> str:
    """Provide a compact verified palette when semantic icon RAG is disabled."""
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for semantic_role, use_when, names in OFFLINE_ICON_PALETTE:
        for name in names:
            path = f"{lib}/{name}"
            if path in seen or not _icon_asset_exists(path):
                continue
            seen.add(path)
            rows.append((path, semantic_role, use_when))
            if len(rows) >= OFFLINE_ICON_CANDIDATE_COUNT:
                break
        if len(rows) >= OFFLINE_ICON_CANDIDATE_COUNT:
            break

    if not rows:
        return (
            f"\n## Available Icon Candidates ({lib} library, offline fallback)\n\n"
            "No verified local icons were found for this library. Prefer `Icon: None` "
            "unless a specific local icon path is known to exist.\n"
        )

    lines = [
        f"\n## Available Icon Candidates ({lib} library, offline fallback, {len(rows)} verified icons)",
        "",
        "Semantic RAG is disabled, so use this small verified palette instead of inventing icon names.",
        "Choose icons sparingly; most slides should still use `Icon: None`.",
        "",
        "| # | Icon Path | Role | Use when |",
        "|---|-----------|------|----------|",
    ]
    for i, (path, semantic_role, use_when) in enumerate(rows, 1):
        lines.append(f"| {i} | `{path}` | {semantic_role} | {use_when} |")
    lines.append("")
    lines.append(
        "Use icon paths exactly as shown, with the library prefix, in Section VI and Section IX."
    )
    return "\n".join(lines)


def _icon_usage_policy_block(icon_library: str) -> str:
    return (
        "\n## Icon Usage: ENABLED — restrained semantic mode\n"
        "Icons are enabled, but they must remain sparse and purposeful. "
        "Use icons only when they clarify the slide's structure or meaning; do not add icons merely because the switch is on.\n\n"
        "Rules:\n"
        "- Target only high-value placements: chapter dividers, process steps, KPI/result highlights, warnings/failure modes, limitation cards, or future-direction cards.\n"
        "- Avoid icon use on dense technical/data slides unless the icon labels a clear process step or callout.\n"
        "- Never use icons as ordinary bullet prefixes, repeated decoration, filler, or background texture.\n"
        "- Keep to one icon library for the whole deck and use explicit `<use data-icon=\"...\"/>` placeholders.\n"
        "- In Section VI, list only icons with a concrete justification; leave slides unlisted when no icon is needed.\n"
        "- In Section IX Content Outline, add an `Icon: ` line only for slides that should actually render an icon.\n"
        f"- Selected icon library: `{icon_library}`. Icon paths should include this library prefix, e.g. `{icon_library}/name`.\n"
        "- Choose only icon paths that appear in the candidate table below, unless a local asset with that exact path is explicitly known to exist.\n"
        "\nVisual role separation:\n"
        "- `Icon` means a real library icon only. Use `Icon: None` on ordinary content pages unless the icon has a clear semantic job.\n"
        "- `Card Marker` means structural labeling only: prefer `numbered` or `none`. Do not use single-letter/symbol badges such as `P`, `Δ`, `!`, or `G` as fake icons.\n"
        "- `Micro Visual` means a tiny mechanism diagram, not an icon. Prefer forms such as `distribution-bins`, `residual-arrow`, `error-growth`, `gate-slider`, `stage-flow`, `mini-chart`, or `none`.\n"
        "- For dense technical explanation cards, choose numbered markers or micro visuals over decorative icons.\n"
        "- In Section IX, add `Card Marker:` and/or `Micro Visual:` only when they materially guide the Executor; otherwise omit them or use `none`.\n"
    )


def _extract_design_spec_section(content: str, roman: str) -> str:
    pattern = rf"(?ims)^#+\s*{re.escape(roman)}\.\s+.*?(?=^#+\s*[IVXLCDM]+\.\s+|\Z)"
    match = re.search(pattern, content)
    return match.group(0) if match else ""


_PAGE_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "cover": ("cover", "封面", "封面页", "标题页"),
    "chapter": ("chapter", "transition", "section", "章节", "章节页", "章标题", "过渡", "过渡页", "转场"),
    "toc": ("toc", "agenda", "outline", "目录", "大纲"),
    "content": ("content", "body", "main", "内容", "内容页", "正文", "主体", "普通页"),
    "ending": ("ending", "closing", "thanks", "q&a", "结束", "结束页", "致谢", "感谢", "问答"),
}
_PAGE_TYPE_WORD_PATTERN = "|".join(
    re.escape(alias)
    for aliases in _PAGE_TYPE_ALIASES.values()
    for alias in sorted(aliases, key=len, reverse=True)
)
_PAGE_TYPE_LABEL_PATTERN = (
    r"(?:page\s*)?type|page\s*category|slide\s*type|类型|页型|页面类型|幻灯片类型"
)


def _outline_block_mentions_page_type(block: str, page_type: str) -> bool:
    aliases = _PAGE_TYPE_ALIASES.get(page_type, (page_type,))
    for alias in aliases:
        escaped = re.escape(alias)
        if alias.isascii():
            if re.search(rf"(?i)(?<![a-z0-9_]){escaped}(?![a-z0-9_])", block):
                return True
        elif alias in block:
            return True
    return False


def _insert_outline_page_type(block: str, page_num: int | str, page_type: str) -> str:
    first_line_end = block.find("\n")
    if first_line_end < 0:
        first_line = block
        rest = ""
    else:
        first_line = block[:first_line_end]
        rest = block[first_line_end:]

    if first_line.lstrip().startswith("|"):
        page_ref_pattern = rf"(?i)\b((?:page|slide)\s*0*{page_num})\b"
        table_line = re.sub(
            page_ref_pattern,
            rf"\1 (type: {page_type})",
            first_line,
            count=1,
        )
        if table_line != first_line:
            return table_line + rest

    return f"{first_line}\n- **Type**: {page_type}{rest}"


def _design_spec_validation_error(
    content: str,
    *,
    expected_page_count: int | None = None,
    expected_inventory: list[dict[str, str | int]] | None = None,
) -> str | None:
    text = content.strip()
    if len(text) < 1200:
        return f"design_spec.md is too short ({len(text)} characters)"

    required = {
        "I": "Project Information",
        "II": "Canvas Specification",
        "III": "Visual Theme",
        "IX": "Content Outline",
        "XI": "Technical Constraints",
    }
    for roman, title in required.items():
        pattern = rf"(?im)^#+\s*{roman}\.\s+.*{re.escape(title)}"
        if not re.search(pattern, text):
            return f"design_spec.md is missing section {roman}. {title}"

    if expected_page_count is not None:
        count_match = re.search(r"(?im)\bPage Count\s*[:：]\s*(\d+)\b", text)
        if count_match and int(count_match.group(1)) != expected_page_count:
            return (
                f"Page Count is {count_match.group(1)}, expected {expected_page_count}"
            )

        outline = _extract_design_spec_section(text, "IX")
        page_nums = [
            int(match.group(1))
            for match in re.finditer(
                r"(?i)\b(?:page|slide)\s*0*(\d+)\b", outline
            )
        ]
        if page_nums:
            if max(page_nums) > expected_page_count:
                return (
                    f"Content Outline references page {max(page_nums)}, "
                    f"expected no more than {expected_page_count}"
                )
            if len(set(page_nums)) != expected_page_count:
                return (
                    f"Content Outline lists {len(set(page_nums))} unique pages, "
                    f"expected {expected_page_count}"
                )

    if expected_inventory:
        outline = _extract_design_spec_section(text, "IX")
        missing_types = []
        for item in expected_inventory:
            page_num = item["page"]
            page_type = str(item["type"])
            page_pattern = rf"(?is)\b(?:page|slide)\s*0*{page_num}\b(.+?)(?=\b(?:page|slide)\s*0*\d+\b|\Z)"
            page_match = re.search(page_pattern, outline)
            if page_match and not _outline_block_mentions_page_type(
                page_match.group(0),
                page_type,
            ):
                missing_types.append(f"{page_num}:{page_type}")
        if missing_types:
            return "Content Outline page types do not match manuscript: " + ", ".join(missing_types[:5])

    missing_icons = sorted(
        {
            match.group(1).strip()
            for match in re.finditer(
                r"`((?:chunk|tabler-filled|tabler-outline)/[^`]+)`",
                text,
            )
            if not match.group(1).strip().endswith("/name")
            and not _icon_asset_exists(match.group(1).strip())
        }
    )
    if missing_icons:
        return (
            "Design spec references missing local icon assets: "
            + ", ".join(missing_icons[:8])
            + ". Choose exact paths from the provided icon candidate table, or use Icon: None."
        )
    return None


def _ensure_design_spec_required_tail(content: str, fmt: dict) -> str:
    """Append deterministic tail sections when the LLM omits them.

    MiMo occasionally returns a complete strategy up to Section IX/X but drops
    the fixed technical appendix.  That appendix is not creative content, so
    failing the whole job is needless.  We only append missing tail sections;
    page outline and visual strategy remain model-authored and still pass the
    normal validator.
    """
    text = content.strip()
    if not text:
        return text

    additions: list[str] = []
    if not re.search(r"(?im)^#+\s*X\.\s+.*Speaker Notes", text):
        additions.append(
            "## X. Speaker Notes Requirements\n\n"
            "- Tone: concise, confident, and audience-aware.\n"
            "- Each slide should have 2-3 speaker-note points matching the visible content.\n"
            "- For roadshow/live-demo pages, include timing cues, role handoff, and evidence reminders.\n"
        )

    if not re.search(r"(?im)^#+\s*XI\.\s+.*Technical Constraints", text):
        viewbox = fmt.get("viewbox", "0 0 1280 720")
        additions.append(
            "## XI. Technical Constraints Reminder\n\n"
            "### SVG Generation Must Follow:\n\n"
            f"1. viewBox: `{viewbox}`\n"
            "2. Background uses `<rect>` elements\n"
            "3. Text wrapping uses `<tspan>` (`<foreignObject>` FORBIDDEN)\n"
            "4. Transparency uses `fill-opacity` / `stroke-opacity`; `rgba()` FORBIDDEN\n"
            "5. FORBIDDEN: `clipPath`, `mask`, `<style>`, `class`, `foreignObject`\n"
            "6. FORBIDDEN: `textPath`, `animate*`, `script`\n"
            "7. `marker-start` / `marker-end` conditionally allowed only with valid `<marker>` definitions\n\n"
            "### PPT Compatibility Rules:\n\n"
            "- `<g opacity=\"...\">` FORBIDDEN; set opacity on each child element individually\n"
            "- Image transparency uses overlay mask layer (`<rect fill=\"bg-color\" opacity=\"0.x\"/>`)\n"
            "- Inline styles only; external CSS and `@font-face` FORBIDDEN\n"
        )

    if not additions:
        return text
    return text + "\n\n---\n\n" + "\n\n---\n\n".join(additions)


def _align_content_outline_page_types(
    content: str,
    expected_inventory: list[dict[str, str | int]] | None,
) -> str:
    """Repair outline page-type labels when the page contract is otherwise intact."""
    if not expected_inventory:
        return content

    outline = _extract_design_spec_section(content, "IX")
    if not outline:
        return content

    repaired = outline
    for item in expected_inventory:
        page_num = item["page"]
        expected_type = str(item["type"])
        line_pattern = rf"(?im)^(\s*[-*]?\s*(?:page|slide)\s*0*{page_num}\s*[:：\-–—]\s*)(?:\*\*)?(?:{_PAGE_TYPE_WORD_PATTERN})(?:\*\*)?"
        repaired = re.sub(line_pattern, rf"\g<1>{expected_type}", repaired, count=1)

        block_pattern = rf"(?is)(\b(?:page|slide)\s*0*{page_num}\b.+?)(?=\b(?:page|slide)\s*0*\d+\b|\Z)"
        block_match = re.search(block_pattern, repaired)
        if not block_match:
            continue
        block = block_match.group(1)
        if _outline_block_mentions_page_type(block, expected_type):
            continue

        typed_block = re.sub(
            rf"(?im)^(\s*(?:[-*]\s*)?(?:\*\*)?(?:{_PAGE_TYPE_LABEL_PATTERN})(?:\*\*)?\s*[:：]\s*)(?:{_PAGE_TYPE_WORD_PATTERN})",
            rf"\g<1>{expected_type}",
            block,
            count=1,
        )
        if typed_block == block:
            typed_block = _insert_outline_page_type(block, page_num, expected_type)
        if typed_block != block:
            start, end = block_match.span(1)
            repaired = repaired[:start] + typed_block + repaired[end:]

    if repaired == outline:
        return content
    start = content.find(outline)
    if start < 0:
        return content
    return content[:start] + repaired + content[start + len(outline):]


def _language_constraint(language: str) -> str:
    normalized = language.strip().lower()
    if normalized == "zh":
        return "All slide titles, labels, bullets, and annotations must be in Simplified Chinese except proper nouns."
    if normalized == "en":
        return "All slide titles, labels, bullets, and annotations must be in English."
    if normalized == "bilingual":
        return (
            "Page titles and core bullets may include both Chinese and English, but each line must stay readable and deliberate."
        )
    return (
        f"Treat `{language}` as a literal target-language request and keep all visible slide text fully in {language}, "
        "except proper nouns that must remain in their original form."
    )


async def create_design_spec(
    manuscript: str,
    llm: LLMProvider,
    model: str,
    *,
    canvas_format: str = "ppt169",
    style: str = "academic",
    language: str = "en",
    detail_level: str = "normal",
    icon_library: str = "chunk",
    style_overrides: dict | None = None,
    enable_icon: bool = False,
    enable_icon_rag: bool = False,
    gemini_api_key: str | None = None,
    figure_inventory: list[dict] | None = None,
    locked_facts: LockedFacts | None = None,
    debug_dir: Path | None = None,
    template_context: str | None = None,
) -> str:
    """Generate a design specification from a manuscript.

    Args:
        manuscript: Slide-structured manuscript markdown.
        llm: LLM provider instance.
        model: Model ID to use.
        canvas_format: Canvas format key.
        style: Design style key.
        language: Output language.
        detail_level: Requested content depth and density target.
        icon_library: Icon library to use (chunk/tabler-filled/tabler-outline).

    Returns:
        Design specification markdown (design_spec.md content).
    """
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    # Load the design spec reference template
    ref_path = settings.templates_dir / "design_spec_reference.md"
    ref_template = ""
    if ref_path.exists():
        ref_template = ref_path.read_text(encoding="utf-8")

    fmt = CANVAS_FORMATS.get(canvas_format, CANVAS_FORMATS["ppt169"])
    style_info = DESIGN_STYLES.get(style, DESIGN_STYLES["academic"])
    is_roadshow = style == "roadshow"
    audience = "Vocational-skills-competition judges and live-demo audience" if is_roadshow else "Academic/Research community"
    if is_roadshow and figure_inventory:
        figure_inventory = filter_roadshow_figure_inventory(figure_inventory)

    # Count pages in manuscript
    page_count = count_manuscript_pages(manuscript)
    inventory = page_inventory(manuscript)
    inventory_block = format_page_inventory(manuscript)
    enforce_page_types = "<!--" in manuscript and "page_type" in manuscript

    user_parts = [
        f"## Manuscript\n\n{manuscript}",
        f"\n## Manuscript Page Inventory\n\n{inventory_block}",
        f"\n## Canvas Format: {fmt['name']} ({fmt['ratio']}), viewBox: `{fmt['viewbox']}`",
        f"\n## Design Style: {style_info['name']}",
        f"\n## Page Count: {page_count}",
        f"\n## Language: {language}",
        f"\n## Detail Level: {detail_level}",
        f"\n## Pre-resolved Confirmations",
        f"- Canvas Format: {fmt['name']}",
        f"- Page Count: {page_count}",
        f"- Audience: {audience}",
        f"- Style: {style_info['name']}",
    ]

    if template_context:
        # When a template is active, the template's color scheme and
        # typography take precedence.  Only inject the style name for
        # content-strategy guidance (academic vs consulting vs tech),
        # but skip primary/accent color so they don't conflict.
        user_parts.extend([
            "- Color scheme & Typography: defined by the selected template (see Template Reference below)",
            "\n## Hard Constraints",
            "- The template's color scheme, typography, and page structure MUST take precedence over any style defaults.",
            f"- Page contract: exactly {page_count} pages; page N in Section IX must match manuscript page N.",
            "- Do not add, remove, or reorder cover, chapter/transition, content, or ending pages.",
            f"- The visible slide language must be `{language}`.",
            f"- {_language_constraint(language)}",
            "- Detail level `normal` should keep pages concise, `high` should allow moderately denser explanatory content, and `very_high` should accommodate richer explanations and fuller evidence coverage without becoming unreadable.",
        ])
        user_parts.append(f"\n{template_context}")
    else:
        user_parts.extend([
            f"- Primary Color: {style_info['primary']}",
            f"- Accent Color: {style_info['accent']}",
            f"- Typography: Sans-serif (Inter/Arial for body, bold for headings)",
            "\n## Hard Constraints",
            "- Respect the selected design style. Do not silently fall back to a default academic theme when another style is selected.",
            "- No fixed layout template is selected. Create an original visual system for this deck instead of imitating any bundled template.",
            "- Vocational-skills-competition constraints affect content only: no personal information, no fabricated facts, source traceability where claims are made. Do not let these constraints force a government/enterprise template style.",
            "- Cover pages should be visually designed with native SVG backgrounds, gradients, abstract geometry, type hierarchy, and color blocks only. Do not use uploaded images, screenshots, generated pictures, pending image backgrounds, or extracted figures on the cover.",
            "- For Competition Roadshow style, design for a 55-minute on-site presentation with live demo: prioritize architecture, operation workflow, support materials, role handoff, and judge-facing clarity over academic paper structure.",
            "- For Competition Roadshow style, make policy/news, market research, industry pain points, helped industries, economy, employment, school-enterprise cooperation and IP/cooperation value visually explicit when sources allow.",
            "- For Competition Roadshow style, never render the Chinese word `证据` as visible slide copy. Use 支撑材料、运行记录、验证结果、成果材料、资料来源 instead.",
            "- For Competition Roadshow style, pages should feel like a polished project roadshow deck, not a thesis defense or literature-review deck.",
            "- For Competition Roadshow style, do not use PDF table crops as architecture, workflow, screenshot, or support-material images; convert tables into native designed layouts instead.",
            "- For Competition Roadshow style, prefer live-operation layouts when manuscript fields ask for them: competition cockpit, dual-screen board, code restoration board, product test board, material console, team handoff board.",
            "- For Competition Roadshow style, every page's Section IX plan MUST explicitly preserve and operationalize its `primary_visual` contract. Use it as the dominant composition object.",
            "- For Competition Roadshow style, do not turn technical/demo/support-material/result pages into pure cards, pure lists, or pure tables. Cards may annotate a primary visual, but the page must be led by the primary visual.",
            "- For Competition Roadshow style, map primary_visual.type to a concrete SVG design: architecture_map/data_flow/rule_tree/support_material_flow/live_demo_board/code_explain_board/test_dashboard/result_dashboard/team_handoff/risk_fallback/policy_market_map/industry_value_map/employment_role_map.",
            "- For Competition Roadshow style, preserve module_flow, expected_screen_state, operator_action, acceptance_signal and fallback_plan as design intent. Convert them into clean project-facing visual elements; do not expose internal field names as visible copy.",
            "- For code restoration pages, render only decisive code/config/protocol fragments with 3-5 annotations and an input-output explanation. Never fill the slide with tiny code.",
            "- For product test pages, make the current operation, expected screen state, result state, material marker and fallback strip visually explicit.",
            "- For result pages, visually separate verified metrics from pending/unverified claims and show source labels where available.",
            f"- Page contract: exactly {page_count} pages; page N in Section IX must match manuscript page N.",
            "- Do not add, remove, or reorder cover, chapter/transition, content, or ending pages.",
            f"- The visible slide language must be `{language}`.",
            f"- {_language_constraint(language)}",
            "- Detail level `normal` should keep pages concise, `high` should allow moderately denser explanatory content, and `very_high` should accommodate richer explanations and fuller evidence coverage without becoming unreadable.",
        ])

    if is_deepseek_provider(llm, model):
        user_parts.append("\n" + deepseek_strategy_guidance(detail_level))

    # Icon policy: when enabled, Phase 1 skips icon detail — Phase 2 (icon_round) decides
    if not enable_icon:
        user_parts.append(
            "\n## Icon Usage: DISABLED\n"
            "Do NOT use any `<use data-icon=\"...\"/>` elements in any slide. "
            "Use plain SVG shapes (circles, rects, paths) for all visual elements instead."
        )
    else:
        # Phase 1: just tell strategist that icons will be planned separately
        user_parts.append(
            f"\n## Icon Usage: ENABLED (Phase 2)\n"
            f"Icons are enabled but will be planned in a separate phase.\n"
            f"In Section VI, write: `Icon library: {icon_library} — inventory TBD.`\n"
            f"In Section IX, do NOT add `Icon:` lines yet — they will be added later.\n"
            f"Do not use `<use data-icon/>` placeholders in the content outline."
        )

    if is_roadshow:
        user_parts.append(build_roadshow_strategist_guardrails(locked_facts or LockedFacts()))

    # Inject actual image dimensions so the design spec has correct ratios
    if figure_inventory:
        fig_lines = ["\n## Available Figures (actual dimensions)"]
        fig_lines.append("")
        if is_roadshow:
            fig_lines.append("Only the roadshow-safe figures below may be used. If none fit the page purpose, design native SVG diagrams/cards instead.")
        fig_lines.append("Use these EXACT dimensions and ratios in Section VIII Image Resource List.")
        fig_lines.append("Do NOT fabricate dimensions — use the actual values below.")
        fig_lines.append("")
        fig_lines.append("| Filename | Actual Dimensions | Ratio | Page | Caption | Type |")
        fig_lines.append("|----------|-------------------|-------|------|---------|------|")
        for fig in figure_inventory:
            w = fig.get("natural_width", 0)
            h = fig.get("natural_height", 0)
            ratio = fig.get("aspect_ratio", 0)
            page = fig.get("page_number", "?")
            path = fig.get("path", "")
            name = Path(path).stem if path else "?"
            cap = (fig.get("caption") or "")[:60]
            semantic = fig.get("semantic_type") or ""
            if w and h:
                fig_lines.append(f"| {name} | {w}x{h} | {ratio:.2f} | p{page} | {cap} | {semantic} |")
        fig_lines.append("")
        fig_lines.append(
            "**Important**: When placing these images in SVG, the `width/height` ratio MUST match "
            "the actual ratio above. For example, if actual dimensions are 974x269 (ratio 3.62), "
            "use width=500 height=138 (500/3.62≈138)."
        )
        if is_roadshow:
            fig_lines.append(
                "For roadshow pages, do not reinterpret a figure's purpose. If the caption/type does not match architecture, workflow, support-material, or screenshot needs, omit it and design a native SVG visual."
            )
        else:
            fig_lines.append(
                "Do not assign extracted paper figures to cover, chapter, or ending pages unless the manuscript "
                "explicitly asks for that figure on that structural page. Use paper figures primarily on evidence, "
                "method, experiment, or result pages."
            )
        user_parts.append("\n".join(fig_lines))

    if style_overrides:
        override_lines = ["\n## Style Overrides (must override defaults)"]
        palette = style_overrides.get("palette") if isinstance(style_overrides, dict) else None
        font = style_overrides.get("font") if isinstance(style_overrides, dict) else None
        font_heading = style_overrides.get("font_heading") if isinstance(style_overrides, dict) else None
        font_body = style_overrides.get("font_body") if isinstance(style_overrides, dict) else None
        cjk_heading = style_overrides.get("cjk_heading") if isinstance(style_overrides, dict) else None
        cjk_body = style_overrides.get("cjk_body") if isinstance(style_overrides, dict) else None
        density = style_overrides.get("density") if isinstance(style_overrides, dict) else None
        if palette:
            try:
                colors = ", ".join(str(c) for c in palette if c)
            except TypeError:
                colors = ""
            if colors:
                override_lines.append(
                    f"- Palette: {colors} — use these as the primary / accent / background colors "
                    f"in every slide's color system. Do NOT fall back to the default style colors."
                )
        if font_heading or font_body or cjk_heading or cjk_body:
            if font_heading:
                override_lines.append(
                    f"- Western heading font-family: `{font_heading}` — use this for Western (Latin) heading/title text."
                )
            if font_body:
                override_lines.append(
                    f"- Western body font-family: `{font_body}` — use this for Western (Latin) body/paragraph text."
                )
            if cjk_heading:
                override_lines.append(
                    f"- CJK heading font-family: `{cjk_heading}` — use this for CJK (Chinese/Japanese/Korean) heading/title text."
                )
            if cjk_body:
                override_lines.append(
                    f"- CJK body font-family: `{cjk_body}` — use this for CJK (Chinese/Japanese/Korean) body/paragraph text."
                )
        elif font:
            override_lines.append(
                f"- Font-family: `{font}` — use this family for every text element throughout."
            )
        if density:
            override_lines.append(
                f"- Layout density: `{density}` — respect this target spacing/whitespace aesthetic."
            )
        user_parts.append("\n".join(override_lines))

    if ref_template:
        user_parts.append(
            f"\n## Design Spec Reference Template\n\n"
            f"Follow this template structure exactly:\n\n{ref_template}"
        )

    user_parts.append(
        "\n\nGenerate the complete design_spec.md following the template structure. "
        "All 11 sections (I through XI) must be present. In Section IX, list each page once with its page type."
    )

    base_messages = [
        LLMMessage.system(system_prompt),
        LLMMessage.user("\n".join(user_parts)),
    ]

    # Save full prompt for debugging
    if debug_dir:
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            prompt_file = debug_dir / "strategist_prompt.md"
            parts = []
            for msg in base_messages:
                parts.append(f"--- ROLE: {msg.role} ---\n\n{msg.content}")
            prompt_file.write_text("\n\n".join(parts), encoding="utf-8")
        except Exception:
            pass

    last_error = ""
    for attempt in range(1, MAX_DESIGN_SPEC_ATTEMPTS + 1):
        messages = list(base_messages)
        if last_error:
            messages.append(
                LLMMessage.user(
                    "The previous design_spec.md response was invalid: "
                    f"{last_error}. Regenerate the complete design_spec.md now. "
                    "Do not return an empty response. Include all required sections I through XI."
                )
            )

        response: LLMResponse = await llm.chat(
            messages,
            model,
            temperature=0.25 if attempt > 1 else 0.4,
            max_tokens=_design_spec_token_budget(page_count),
        )
        content = response.content.strip()
        if debug_dir:
            try:
                (debug_dir / f"strategist_response_attempt{attempt}.md").write_text(
                    content,
                    encoding="utf-8",
                )
            except Exception:
                pass
        content = _ensure_design_spec_required_tail(content, fmt)
        if enforce_page_types:
            content = _align_content_outline_page_types(content, inventory)
        content = _normalize_missing_icon_assets(content)
        error = _design_spec_validation_error(
            content,
            expected_page_count=page_count,
            expected_inventory=inventory if enforce_page_types else None,
        )
        if error is None:
            if is_roadshow and locked_facts:
                content = enforce_locked_title_in_design_spec(content, locked_facts)
            # Phase 2: Icon Decoration Round (if enabled)
            if enable_icon:
                from backend.orchestrator.icon_round import run_icon_round

                logger.info("Running Icon Decoration Round (Phase 2)")
                content = await run_icon_round(
                    content,
                    manuscript,
                    icon_library,
                    llm,
                    model,
                    enable_icon_rag=enable_icon_rag,
                    gemini_api_key=gemini_api_key,
                    debug_dir=debug_dir,
                )
            return content
        last_error = error

    raise RuntimeError(f"Invalid design specification from strategist: {last_error}")
