"""Hard quality checks for competition-roadshow PPT generation.

These checks focus on rules that should hold for every generated deck, not on
subjective visual taste.  They run before SVG generation and again before PPTX
export so regressions are caught close to where they happen.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .manuscript import page_title, split_manuscript_pages

_FIELD_NAMES = (
    "page_core_sentence",
    "visible_content",
    "main_visual",
    "visual_asset_plan",
    "required_assets",
    "asset_status",
    "speaker_notes",
    "main_script",
    "sub_script",
    "transition",
    "story_role",
    "primary_visual",
    "stage_mode",
    "display_target",
    "operator_role",
    "operator_action",
    "acceptance_signal",
)
_FIELD_RE_TEMPLATE = (
    r"(?ims)^\s*(?:\*\*)?{field}(?:\*\*)?\s*[:：]\s*(.*?)"
    r"(?=^\s*(?:\*\*)?(?:"
    + "|".join(re.escape(name) for name in _FIELD_NAMES)
    + r")(?:\*\*)?\s*[:：]|^\s*<!--|^\s*#|\Z)"
)
_FIELD_HEADER_RE = re.compile(
    r"(?im)^\s*(?:\*\*)?(" + "|".join(re.escape(name) for name in _FIELD_NAMES) + r")(?:\*\*)?\s*[:：]"
)
_ASSET_TOKEN_RE = re.compile(r"\[\[ASSET:[^\]]+\]\]")
_SVG_IMAGE_RE = re.compile(r"<image\b[^>]*(?:/>|>.*?</image>)", re.I | re.S)
_TEXT_TAG_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_SVG_LAYOUT_TAG_RE = re.compile(r"<(?:text|foreignObject|rect|path|circle|ellipse|polygon|polyline|line)\b", re.I)
_CHAPTER_RE = re.compile(r"(?:CHAPTER\s*|第\s*)(\d{1,2})(?:\s*章)?", re.I)

_COVER_IMAGE_HINT_RE = re.compile(
    r"\[\[ASSET:|real_image|material_photo|product_ui|screenshot|uploaded|image|图片|照片|截图|素材",
    re.I,
)
_SOURCE_PAGE_HINT_RE = re.compile(
    r"政策|调研|测试|数据|效率|稳定|成效|反馈|成本|提升|降低|增长|通过率|运行|样本|趋势|对比|价值",
)
_SOURCE_EVIDENCE_RE = re.compile(
    r"来源|日期|时间|样本|测试环境|测试记录|运行日志|截图|报告|政策|官网|访谈|问卷|\[\[ASSET:",
)
_SCRIPT_META_RE = re.compile(
    r"副标题|底部任务|本页展示|这一页展示|页面上|主视觉|版式|布局|字段|待补充|建议补充|"
    r"项目名称、一句定位语|证明对象|证明任务|设计解释",
)


def _is_image2_cover_plan(text: str) -> bool:
    lowered = (text or "").lower()
    return "image2" in lowered or "generated_image" in lowered or "完整封面视觉" in text


@dataclass(slots=True)
class RoadshowQualityFinding:
    rule: str
    severity: str
    message: str
    page: int | None = None
    evidence: str = ""
    action: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _field_value(page: str, field: str) -> str:
    pattern = re.compile(_FIELD_RE_TEMPLATE.format(field=re.escape(field)), re.I | re.M | re.S)
    match = pattern.search(page)
    if not match:
        return ""
    return match.group(1).strip()


def _replace_or_append_field(page: str, field: str, value: str) -> str:
    pattern = re.compile(_FIELD_RE_TEMPLATE.format(field=re.escape(field)), re.I | re.M | re.S)
    replacement = f"{field}: {value.strip()}"
    if pattern.search(page):
        return pattern.sub(replacement, page, count=1)
    return page.rstrip() + "\n" + replacement + "\n"


def _clean_note(note: str) -> str:
    note = re.sub(r"(?im)^\s*(?:speaker_notes|speech_script|script|main_script|sub_script|transition)\s*[:：]\s*", "", note)
    note = _ASSET_TOKEN_RE.sub("", note)
    return re.sub(r"\s+", " ", note).strip()


def _page_density(page: str) -> tuple[int, int]:
    visible = _field_value(page, "visible_content")
    bullet_count = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.、])\s+", visible))
    separators = len(re.findall(r"[；;]|(?:\s->\s)|(?:\s→\s)", visible))
    return len(visible), bullet_count + separators


def _asset_ids(text: str) -> list[str]:
    return [m.group(0)[8:-2] for m in _ASSET_TOKEN_RE.finditer(text)]


def ensure_roadshow_manuscript_hard_requirements(
    manuscript: str,
    *,
    expected_pages: int | None = None,
    allow_cover_images: bool = False,
) -> str:
    """Apply deterministic fixes for non-negotiable rules.

    This does not rewrite story or speaker notes. Speaker notes are generated
    by Roadshow Script Skill; this function only handles structural hard rules.
    """
    pages = split_manuscript_pages(manuscript)
    if expected_pages and len(pages) != expected_pages:
        return manuscript
    if not pages:
        return manuscript

    fixed: list[str] = []
    for idx, page in enumerate(pages, start=1):
        current = page
        if idx == 1 and not allow_cover_images:
            current = _ASSET_TOKEN_RE.sub("", current)
            for field in ("main_visual", "primary_visual", "visual_asset_plan"):
                if _COVER_IMAGE_HINT_RE.search(_field_value(current, field)):
                    current = _replace_or_append_field(current, field, "native_svg_background")
            current = _replace_or_append_field(current, "required_assets", "无")
            current = _replace_or_append_field(current, "asset_status", "not_required")
        fixed.append(current.strip())
    return "\n\n---\n\n".join(fixed).strip() + "\n"


def evaluate_roadshow_manuscript_quality(
    manuscript: str,
    *,
    expected_pages: int | None = None,
    allow_cover_images: bool = False,
    require_notes: bool = True,
) -> dict:
    pages = split_manuscript_pages(manuscript)
    findings: list[RoadshowQualityFinding] = []

    if expected_pages is not None and len(pages) != expected_pages:
        findings.append(
            RoadshowQualityFinding(
                rule="page_count",
                severity="error",
                message=f"内容页数应为 {expected_pages} 页，当前为 {len(pages)} 页。",
                action="保持页数不变，补齐或合并异常页面。",
            )
        )

    if require_notes:
        missing_notes: list[int] = []
        weak_notes: list[int] = []
        for idx, page in enumerate(pages, start=1):
            note = _clean_note(_field_value(page, "speaker_notes"))
            if not note:
                missing_notes.append(idx)
            elif len(note) < 80 or _SCRIPT_META_RE.search(note):
                weak_notes.append(idx)
        if missing_notes:
            findings.append(
                RoadshowQualityFinding(
                    rule="notes_count",
                    severity="error",
                    message=f"有 {len(missing_notes)} 页缺少可直接朗读的讲稿。",
                    evidence="页码：" + "、".join(map(str, missing_notes[:20])),
                    action="为每一页补齐 speaker_notes，语气必须像现场选手发言。",
                )
            )
        if weak_notes:
            findings.append(
                RoadshowQualityFinding(
                    rule="notes_quality",
                    severity="warning",
                    message=f"有 {len(weak_notes)} 页讲稿过短或含有页面设计说明。",
                    evidence="页码：" + "、".join(map(str, weak_notes[:20])),
                    action="改写为可以直接照读的讲稿，删除设计解释和系统思考语句。",
                )
            )

    if pages and not allow_cover_images:
        cover_text = "\n".join(
            _field_value(pages[0], field)
            for field in ("main_visual", "primary_visual", "visual_asset_plan", "required_assets", "asset_status")
        )
        if _COVER_IMAGE_HINT_RE.search(cover_text) and not _is_image2_cover_plan(cover_text):
            findings.append(
                RoadshowQualityFinding(
                    rule="cover_no_image",
                    severity="error",
                    message="首页不得配置图片、截图或真实素材。",
                    page=1,
                    evidence=cover_text[:180],
                    action="首页改为字体、线框、几何图形和纯 SVG 背景。",
                )
            )

    chapter_numbers: list[tuple[int, int]] = []
    asset_usage: dict[str, list[int]] = {}
    for idx, page in enumerate(pages, start=1):
        title = page_title(page)
        visible = _field_value(page, "visible_content")
        combined = f"{title}\n{visible}"
        for match in _CHAPTER_RE.finditer(combined):
            chapter_numbers.append((idx, int(match.group(1))))
        chars, item_count = _page_density(page)
        if chars > 360 or item_count > 12:
            findings.append(
                RoadshowQualityFinding(
                    rule="density",
                    severity="warning",
                    message="页面文字密度偏高，现场投影不利于快速理解。",
                    page=idx,
                    evidence=f"{chars} 字，约 {item_count} 个信息项",
                    action="压缩为 1 个核心结论、3-5 个要点；必要时拆成流程/证据/结论页。",
                )
            )
        if _SOURCE_PAGE_HINT_RE.search(combined) and not _SOURCE_EVIDENCE_RE.search(page):
            findings.append(
                RoadshowQualityFinding(
                    rule="data_source",
                    severity="warning",
                    message="该页包含数据、政策、测试或价值判断，但缺少来源口径。",
                    page=idx,
                    evidence=combined[:140],
                    action="补充来源、测试时间、样本量、截图/日志/政策文件等可审查依据；无依据则弱化结论。",
                )
            )
        for asset_id in _asset_ids(page):
            asset_usage.setdefault(asset_id, []).append(idx)

    if chapter_numbers:
        unique_numbers = []
        for _, num in chapter_numbers:
            if num not in unique_numbers:
                unique_numbers.append(num)
        expected = list(range(1, len(unique_numbers) + 1))
        if unique_numbers != expected:
            findings.append(
                RoadshowQualityFinding(
                    rule="chapter_number",
                    severity="warning",
                    message="章节编号不连续或顺序异常。",
                    evidence=f"检测到章节编号：{unique_numbers}",
                    action="按出现顺序重排为连续编号。",
                )
            )

    repeated_assets = {
        asset_id: page_nums
        for asset_id, page_nums in asset_usage.items()
        if len(set(page_nums)) >= 3
    }
    for asset_id, page_nums in list(repeated_assets.items())[:8]:
        findings.append(
            RoadshowQualityFinding(
                rule="duplicate_asset",
                severity="warning",
                message="同一素材被多页重复使用，证据链会显得单薄。",
                evidence=f"{asset_id}: 第 {'、'.join(map(str, sorted(set(page_nums))))} 页",
                action="保留最有证明价值的一页使用真实素材，其余改为流程图、表格或不同截图。",
            )
        )

    return {
        "passed": not any(item.severity == "error" for item in findings),
        "needs_repair": bool(findings),
        "page_count": len(pages),
        "expected_pages": expected_pages,
        "findings": [item.to_dict() for item in findings],
    }


def build_roadshow_quality_repair_instruction(report: dict) -> str:
    findings = report.get("findings") or []
    lines = []
    for item in findings[:40]:
        page = item.get("page")
        prefix = f"第 {page} 页" if page else "全局"
        lines.append(
            f"- [{item.get('severity')}] {prefix} / {item.get('rule')}: "
            f"{item.get('message')} 证据：{item.get('evidence') or '无'} 修正：{item.get('action') or '按规则修正'}"
        )
    return (
        "请基于以下硬质检结果修订稿件，并输出完整 manuscript。\n"
        "要求：保持页数和页面顺序不变；首页不得使用任何图片/截图/上传素材；每页必须有可直接照读的 speaker_notes；"
        "高密度页面压缩为清晰要点；涉及政策、测试、数据、成效、反馈的页面补充可审查来源口径，无法支撑的结论要降为谨慎表达；"
        "章节编号必须连续；重复素材要减少，优先用不同截图、流程图或表格承载。\n\n"
        + "\n".join(lines)
    )


def strip_svg_images(svg: str) -> str:
    return _SVG_IMAGE_RE.sub("", svg)


def svg_has_image(svg: str) -> bool:
    return bool(_SVG_IMAGE_RE.search(svg))


def is_image2_full_page_svg(svg: str, svg_path: Path | None = None) -> bool:
    if svg_path and "image2" in svg_path.stem:
        return True
    image_tags = _SVG_IMAGE_RE.findall(svg or "")
    if len(image_tags) != 1:
        return False
    if not re.search(r"<image\b[^>]*href=[\"']data:image/(?:png|jpe?g|webp);base64,", image_tags[0], re.I):
        return False
    return not _SVG_LAYOUT_TAG_RE.search(svg or "")


def svg_text_density(svg: str) -> tuple[int, int]:
    texts = []
    for raw in _TEXT_TAG_RE.findall(svg):
        text = _TAG_RE.sub("", raw)
        text = re.sub(r"\s+", "", text)
        if text:
            texts.append(text)
    return sum(len(text) for text in texts), len(texts)


async def evaluate_roadshow_export_artifacts(
    svg_files: list[Path],
    notes: dict[str, str],
) -> dict:
    findings: list[RoadshowQualityFinding] = []
    if not svg_files:
        return {"passed": False, "findings": [RoadshowQualityFinding("svg_files", "error", "未找到可导出的页面。").to_dict()]}

    missing_notes = [idx for idx, svg_path in enumerate(svg_files, start=1) if not (notes.get(svg_path.stem) or "").strip()]
    if missing_notes:
        findings.append(
            RoadshowQualityFinding(
                rule="notes_count",
                severity="error",
                message="导出前仍有页面缺少演讲者备注。",
                evidence="页码：" + "、".join(map(str, missing_notes[:30])),
                action="阻止正式导出并回到讲稿生成/同步链路补齐。",
            )
        )

    href_usage: dict[str, list[int]] = {}
    for idx, svg_path in enumerate(svg_files, start=1):
        try:
            svg = svg_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if idx == 1 and svg_has_image(svg) and not is_image2_full_page_svg(svg, svg_path):
            findings.append(
                RoadshowQualityFinding(
                    rule="cover_no_image",
                    severity="error",
                    message="导出前检测到首页 SVG 仍包含图片元素。",
                    page=1,
                    action="移除首页图片元素后再导出。",
                )
            )
        chars, text_nodes = svg_text_density(svg)
        if chars > 520 or text_nodes > 45:
            findings.append(
                RoadshowQualityFinding(
                    rule="density",
                    severity="warning",
                    message="导出页文字密度偏高。",
                    page=idx,
                    evidence=f"{chars} 字，{text_nodes} 个文本节点",
                    action="后续生成应拆页或压缩文字。",
                )
            )
        for href in re.findall(r"<image\b[^>]*(?:href|xlink:href)=['\"]([^'\"]+)['\"]", svg, re.I):
            href_usage.setdefault(href, []).append(idx)

    for href, page_nums in href_usage.items():
        unique = sorted(set(page_nums))
        if len(unique) >= 3:
            findings.append(
                RoadshowQualityFinding(
                    rule="duplicate_asset",
                    severity="warning",
                    message="同一图片资源在多页重复使用。",
                    evidence=f"{Path(href).name}: 第 {'、'.join(map(str, unique[:12]))} 页",
                    action="后续生成应减少重复素材，改用不同证据或图解。",
                )
            )

    return {
        "passed": not any(item.severity == "error" for item in findings),
        "findings": [item.to_dict() for item in findings],
    }
