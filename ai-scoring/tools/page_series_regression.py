#!/usr/bin/env python3
"""
页系骨架回归验证脚本

用途：
1. 抽样真实任务页，验证 page_series_type / layout_slots 是否真正落到主生成与重建链路
2. 渲染截图，便于肉眼检查是否还有“普通 HTML 味”
3. 生成 JSON + Markdown 报告，作为页系骨架回归基线
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.ppt.html_generator import HTMLGenerator  # noqa: E402
from app.services.ppt.html_renderer import HTMLRenderer  # noqa: E402
from app.services.ppt.ppt_service import PPTService  # noqa: E402


REPORTS_DIR = ROOT / "qa" / "review_reports"
ARTIFACTS_DIR = ROOT / "uploads" / "ppt" / "page_series_regression"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


logging.getLogger("app.services.ppt.ppt_service").setLevel(logging.ERROR)
logging.getLogger("app.services.ppt.adapter_code.pipeline_coordinator").setLevel(logging.ERROR)

INTERNAL_TOKENS = [
    "system_diagram",
    "supporting_argument",
    "operation_stage_board",
    "evidence_wall",
    "value_matrix",
    "closing_signal",
]


EXPECTED_ROLE_BY_SERIES = {
    "cover_keynote": ["keynote_anchor"],
    "agenda_navigation": ["navigation_board"],
    "definition_canvas": ["definition_canvas"],
    "mapping_bridge": ["flow_mapping"],
    "evidence_board": ["evidence_wall"],
    "practice_evidence": ["operation_stage_board"],
    "architecture_system": ["system_diagram", "supporting_argument"],
    "value_matrix": ["value_matrix"],
    "closing_board": ["closing_signal"],
    "protocol_board": ["protocol_flow", "risk_action_board"],
    "collaboration_matrix": ["role_matrix", "handoff_chain"],
    "journey_timeline": ["timeline_track", "iteration_evidence"],
    "bridge_story": ["bridge_flow", "feedback_loop"],
    "innovation_compare": ["before_after_compare", "innovation_metric"],
}


@dataclass
class ProbeSpec:
    task_id: int
    page_index: int
    expected_series_type: str
    label: str


DEFAULT_PROBES: List[ProbeSpec] = [
    ProbeSpec(128, 1, "cover_keynote", "开场封面页"),
    ProbeSpec(128, 2, "agenda_navigation", "议程导航页"),
    ProbeSpec(128, 4, "definition_canvas", "项目定义页"),
    ProbeSpec(128, 7, "mapping_bridge", "痛点桥接页"),
    ProbeSpec(107, 3, "evidence_board", "政策证据页"),
    ProbeSpec(107, 10, "architecture_system", "技术架构页"),
    ProbeSpec(107, 18, "practice_evidence", "实操证据页"),
    ProbeSpec(107, 31, "value_matrix", "应用价值页"),
    ProbeSpec(107, 27, "protocol_board", "安全规范页"),
    ProbeSpec(107, 36, "collaboration_matrix", "团队协作页"),
    ProbeSpec(107, 34, "journey_timeline", "研发历程页"),
    ProbeSpec(107, 35, "bridge_story", "产教融合桥接页"),
    ProbeSpec(107, 32, "innovation_compare", "创新对照页"),
    ProbeSpec(107, 38, "closing_board", "总结收束页"),
    ProbeSpec(106, 10, "architecture_system", "技术架构页"),
    ProbeSpec(106, 18, "practice_evidence", "实操证据页"),
    ProbeSpec(106, 31, "value_matrix", "应用价值页"),
    ProbeSpec(106, 27, "protocol_board", "安全规范页"),
    ProbeSpec(106, 36, "collaboration_matrix", "团队协作页"),
    ProbeSpec(106, 34, "journey_timeline", "研发历程页"),
    ProbeSpec(106, 35, "bridge_story", "产教融合桥接页"),
    ProbeSpec(106, 32, "innovation_compare", "创新对照页"),
    ProbeSpec(102, 10, "architecture_system", "技术架构页"),
    ProbeSpec(102, 18, "practice_evidence", "实操证据页"),
    ProbeSpec(102, 31, "value_matrix", "应用价值页"),
    ProbeSpec(102, 27, "protocol_board", "安全规范页"),
    ProbeSpec(102, 36, "collaboration_matrix", "团队协作页"),
    ProbeSpec(102, 34, "journey_timeline", "研发历程页"),
    ProbeSpec(102, 35, "bridge_story", "产教融合桥接页"),
    ProbeSpec(102, 32, "innovation_compare", "创新对照页"),
]


def visible_text(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html or "", flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_slot_roles(html: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for role in re.findall(r'data-slot-role=[\'"]([^\'"]+)[\'"]', html or "", flags=re.I):
        counts[role] = counts.get(role, 0) + 1
    return counts


def detect_internal_leaks(html: str) -> List[str]:
    text = visible_text(html).lower()
    hits = [token for token in INTERNAL_TOKENS if token.lower() in text]
    return sorted(set(hits))


def classify_outcome(assessment: Dict[str, Any], failed_checks: List[str], missing_expected_roles: List[str], internal_leaks: List[str]) -> str:
    before_failed = int(assessment.get("before_failed_count") or 0)
    after_failed = int(assessment.get("after_failed_count") or 0)
    introduced = assessment.get("introduced_checks") or []
    score_delta = int(assessment.get("score_delta") or 0)
    if introduced or after_failed > before_failed:
        return "regressed"
    if score_delta > 0 or before_failed > after_failed:
        return "improved"
    if not failed_checks and not missing_expected_roles and not internal_leaks:
        return "stable_pass"
    if after_failed == 0:
        return "stable_pass"
    return "needs_attention"


def ensure_serializable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): ensure_serializable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [ensure_serializable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def copy_if_exists(source: Optional[str], target_dir: Path, target_name: str) -> Optional[str]:
    if not source:
        return None
    src = Path(source)
    if not src.exists():
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    dest = target_dir / target_name
    shutil.copy2(src, dest)
    return str(dest)


async def probe_one(
    service: PPTService,
    renderer: HTMLRenderer,
    generator: HTMLGenerator,
    spec: ProbeSpec,
    output_dir: Path,
) -> Dict[str, Any]:
    task = await service.get_task(spec.task_id)
    if not task:
        return {"task_id": spec.task_id, "page_index": spec.page_index, "status": "missing_task"}

    html_pages = await service.get_html_pages(spec.task_id)
    outline_pages = service._extract_outline_pages(task.get("outline_json") or {})
    project_name = task.get("project_name") or service._infer_outline_project_name(task.get("outline_json") or {}, outline_pages)

    normalized_outline_pages: List[Dict[str, Any]] = []
    for idx, page in enumerate(outline_pages, start=1):
        if not isinstance(page, dict):
            continue
        normalized_page = dict(page)
        service._complete_outline_page_defaults(normalized_page, idx, project_name)
        normalized_outline_pages.append(normalized_page)

    if spec.page_index > len(normalized_outline_pages) or spec.page_index > len(html_pages):
        return {
            "task_id": spec.task_id,
            "page_index": spec.page_index,
            "status": "skip",
            "reason": "not_enough_pages",
        }

    page_meta = normalized_outline_pages[spec.page_index - 1]
    total_pages = max(len(html_pages), len(normalized_outline_pages))
    current_html = html_pages[spec.page_index - 1] or ""
    main_html = generator._generate_page_from_design(page_meta, {}, spec.page_index, total_pages)

    rebuild_result = await service.repair_html_page(
        spec.task_id,
        spec.page_index,
        strategy="structure_rebuild",
        use_ai=False,
        preview_only=True,
        repair_context={
            "goal": "rebuild_page_by_contract",
            "upgrade_mode": "structure_rebuild",
            "source": "page_series_regression",
        },
    )
    rebuild_html = (rebuild_result or {}).get("html_page", {}).get("html_content") or ""
    assessment = (rebuild_result or {}).get("repair_assessment") or {}
    checks = ((rebuild_result or {}).get("quality_report") or {}).get("checks") or {}
    failed_checks = [k for k, v in checks.items() if isinstance(v, dict) and not v.get("pass")]

    probe_dir = output_dir / f"t{spec.task_id}_p{spec.page_index}_{spec.expected_series_type}"
    probe_dir.mkdir(parents=True, exist_ok=True)
    (probe_dir / "current.html").write_text(current_html, encoding="utf-8")
    (probe_dir / "main.html").write_text(main_html, encoding="utf-8")
    (probe_dir / "rebuild.html").write_text(rebuild_html, encoding="utf-8")

    current_png = await renderer.render_page({"html_content": current_html}, page_index=spec.page_index, total_pages=total_pages)
    main_png = await renderer.render_page({"html_content": main_html}, page_index=spec.page_index, total_pages=total_pages)
    rebuild_png = await renderer.render_page({"html_content": rebuild_html}, page_index=spec.page_index, total_pages=total_pages)

    copied_current_png = copy_if_exists(current_png, probe_dir, "current.png")
    copied_main_png = copy_if_exists(main_png, probe_dir, "main.png")
    copied_rebuild_png = copy_if_exists(rebuild_png, probe_dir, "rebuild.png")

    main_roles = extract_slot_roles(main_html)
    rebuild_roles = extract_slot_roles(rebuild_html)
    expected_roles = EXPECTED_ROLE_BY_SERIES.get(spec.expected_series_type, [])
    missing_expected_roles = [role for role in expected_roles if role not in rebuild_roles]

    result = {
        "task_id": spec.task_id,
        "page_index": spec.page_index,
        "label": spec.label,
        "expected_series_type": spec.expected_series_type,
        "detected_series_type": page_meta.get("page_series_type"),
        "contract_id": page_meta.get("contract_id"),
        "title": page_meta.get("title"),
        "page_visual_role": page_meta.get("page_visual_role"),
        "layout_slots": ensure_serializable(page_meta.get("layout_slots") or []),
        "main_roles": main_roles,
        "rebuild_roles": rebuild_roles,
        "missing_expected_roles": missing_expected_roles,
        "current_internal_leaks": detect_internal_leaks(current_html),
        "main_internal_leaks": detect_internal_leaks(main_html),
        "rebuild_internal_leaks": detect_internal_leaks(rebuild_html),
        "assessment": ensure_serializable(assessment),
        "failed_checks": failed_checks,
        "outcome": classify_outcome(assessment, failed_checks, missing_expected_roles, detect_internal_leaks(rebuild_html)),
        "artifacts": {
            "probe_dir": str(probe_dir),
            "current_html": str(probe_dir / "current.html"),
            "main_html": str(probe_dir / "main.html"),
            "rebuild_html": str(probe_dir / "rebuild.html"),
            "current_png": copied_current_png,
            "main_png": copied_main_png,
            "rebuild_png": copied_rebuild_png,
        },
    }
    return result


def render_markdown_report(results: List[Dict[str, Any]], output_dir: Path) -> str:
    lines: List[str] = []
    lines.append("# 页系骨架回归验证报告")
    lines.append("")
    lines.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- 产物目录：`{output_dir}`")
    lines.append("")

    summary_counts: Dict[str, int] = {}
    for item in results:
        summary_counts[item.get("outcome", "unknown")] = summary_counts.get(item.get("outcome", "unknown"), 0) + 1
    lines.append("## 汇总")
    lines.append("")
    for key in sorted(summary_counts):
        lines.append(f"- `{key}`: {summary_counts[key]}")
    lines.append("")

    lines.append("## 逐页结果")
    lines.append("")
    for item in results:
        lines.append(f"### task {item['task_id']} / page {item['page_index']} / {item.get('expected_series_type')}")
        lines.append("")
        lines.append(f"- 标题：{item.get('title') or 'N/A'}")
        lines.append(f"- 契约：`{item.get('contract_id') or 'N/A'}`")
        lines.append(f"- outcome：`{item.get('outcome')}`")
        lines.append(f"- 评估：`{json.dumps(item.get('assessment', {}), ensure_ascii=False)}`")
        lines.append(f"- main roles：`{item.get('main_roles')}`")
        lines.append(f"- rebuild roles：`{item.get('rebuild_roles')}`")
        lines.append(f"- 缺失预期 roles：`{item.get('missing_expected_roles')}`")
        lines.append(f"- rebuild 内部词泄露：`{item.get('rebuild_internal_leaks')}`")
        lines.append(f"- failed checks：`{item.get('failed_checks')}`")
        art = item.get("artifacts", {})
        if art.get("current_png"):
            lines.append(f"- 当前页截图：[{Path(art['current_png']).name}]({art['current_png']})")
        if art.get("main_png"):
            lines.append(f"- 主生成截图：[{Path(art['main_png']).name}]({art['main_png']})")
        if art.get("rebuild_png"):
            lines.append(f"- 重建截图：[{Path(art['rebuild_png']).name}]({art['rebuild_png']})")
        lines.append("")

    return "\n".join(lines)


async def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ARTIFACTS_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    service = PPTService()
    renderer = HTMLRenderer()
    generator = HTMLGenerator()
    results: List[Dict[str, Any]] = []
    try:
        for spec in DEFAULT_PROBES:
            result = await probe_one(service, renderer, generator, spec, output_dir)
            results.append(result)
    finally:
        await renderer.close_browser()

    json_path = output_dir / "report.json"
    md_path = REPORTS_DIR / f"page_series_regression_{timestamp}.md"
    latest_md_path = REPORTS_DIR / "page_series_regression_latest.md"

    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md = render_markdown_report(results, output_dir)
    md_path.write_text(report_md, encoding="utf-8")
    latest_md_path.write_text(report_md, encoding="utf-8")

    print(json.dumps({
        "json": str(json_path),
        "markdown": str(md_path),
        "latest_markdown": str(latest_md_path),
        "artifacts_dir": str(output_dir),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
