"""Support-material binding for vocational competition roadshow decks."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from backend.parser.paper_model import ParsedPaper, PaperFigure

from .roadshow_quality import classify_roadshow_figure
from .roadshow_asset_registry import infer_roadshow_asset_type


@dataclass(frozen=True)
class EvidenceAsset:
    asset_id: str
    asset_type: str
    source: str
    caption: str
    usable_for: str
    confidence: str = "medium"
    token: str = ""


CORE_EVIDENCE_TYPES = (
    "system_screenshot",
    "workflow_diagram",
    "code_or_interface",
    "test_record",
    "log_record",
    "device_or_scene",
    "result_claim_source",
    "fault_recovery",
)

TEXT_EVIDENCE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("code_or_interface", ("代码", "函数", "接口", "API", "SQL", "配置", "协议", "蓝牙", "HTTP", "SSE")),
    ("test_record", ("测试", "用例", "验收", "复测", "准确率", "成功率", "耗时", "样本")),
    ("log_record", ("日志", "记录", "审计", "追溯", "工单", "留痕")),
    ("device_or_scene", ("设备", "传感器", "硬件", "大屏", "现场", "实操", "环境")),
    ("result_claim_source", ("成果", "应用", "推广", "用户反馈", "经济", "节约", "提升", "企业", "基地")),
    ("fault_recovery", ("故障", "异常", "应急", "备用", "恢复", "排查", "修复")),
)


def build_evidence_asset_report(
    paper: ParsedPaper,
    source_md: str,
    material_analysis: str = "",
) -> dict[str, Any]:
    """Build a deterministic evidence inventory before LLM planning."""
    text = f"{source_md}\n\n{material_analysis}"
    assets: list[EvidenceAsset] = []
    assets.extend(_figure_assets(paper))
    assets.extend(_text_assets(text))

    by_type = {asset.asset_type for asset in assets}
    missing = [asset_type for asset_type in CORE_EVIDENCE_TYPES if asset_type not in by_type]
    warnings: list[str] = []
    if "system_screenshot" not in by_type and "workflow_diagram" not in by_type:
        warnings.append("缺少可直接进入页面的系统截图或流程图，页面应优先生成原生 SVG 结构图。")
    if "test_record" not in by_type:
        warnings.append("缺少测试记录来源，成果页不能写已达成 KPI，只能写验证方法或待采集口径。")
    if "fault_recovery" not in by_type:
        warnings.append("缺少故障恢复材料，现场实操页必须生成排查/复测方案而不是假装已有记录。")

    return {
        "available_assets": [asdict(asset) for asset in assets[:36]],
        "available_types": sorted(by_type),
        "missing_core_types": missing,
        "formal_readiness": "ready" if not missing else "draft",
        "warnings": warnings,
    }


def evidence_asset_prompt_block(report: dict[str, Any]) -> str:
    lines = [
        "## Support Material Binder Report",
        "",
        "这份报告是本地支撑材料绑定结果，用于避免把资料分析 PPT 做成空泛摘要。",
        "后续页面必须围绕 proof_object 选择真实支撑材料或明确写验证方法；不得编造截图、日志、时间戳、编号或 KPI。",
        "PPT 可见正文不要出现“证据”二字，改用支撑材料、运行记录、验证结果、成果材料或资料来源。",
        "",
        f"- formal_readiness: {report.get('formal_readiness', 'draft')}",
        "- available_types: " + ", ".join(report.get("available_types") or ["none"]),
        "- missing_core_types: " + ", ".join(report.get("missing_core_types") or ["none"]),
    ]
    warnings = report.get("warnings") or []
    if warnings:
        lines.append("- warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")

    assets = report.get("available_assets") or []
    if not assets:
        lines.append("\nNo bound support materials were found. Use native SVG diagrams and mark material needs as verification methods, not facts.")
    else:
        lines.extend(["", "| asset_id | token | type | source | usable_for | caption |", "| --- | --- | --- | --- | --- | --- |"])
        for asset in assets[:18]:
            caption = _short(str(asset.get("caption") or ""), 90)
            lines.append(
                f"| {asset.get('asset_id', '')} | {asset.get('token', '')} | {asset.get('asset_type', '')} | "
                f"{asset.get('source', '')} | {asset.get('usable_for', '')} | {caption} |"
            )
    lines.extend(
        [
            "",
            "Page planning rule:",
            "- 每页必须写 proof_object，说明这页要证明的对象、可用来源和缺失时的替代表达。",
            "- 页面需要真实截图、设备照片、运行图表、视频关键帧或正式图片材料时，required_assets 必须引用表格中的 `[[ASSET:asset_id]]`，不要直接写中文文件路径。",
            "- 如果页面使用了 `[[ASSET:asset_id]]` 且 asset_status=provided，后续 SVG 页面必须包含真实 `<image>`，否则会进入修复或正式导出拦截。",
            "- proof_object 有来源时，优先把支撑对象转成主视觉；没有来源时，页面可展示验证流程/采集清单，但不能写成已完成成果。",
            "- 不允许把 PDF 整页裁图或表格裁图直接当正式材料看板。能用原生 SVG 重绘的必须重绘。",
        ]
    )
    return "\n".join(lines)


def _figure_assets(paper: ParsedPaper) -> list[EvidenceAsset]:
    assets: list[EvidenceAsset] = []
    for fig in paper.all_figures():
        if not getattr(fig, "available", False):
            continue
        meta = classify_roadshow_figure(fig)
        if not meta.get("allowed_for_roadshow"):
            continue
        asset_type = _asset_type_from_figure(fig, str(meta.get("semantic_type") or ""))
        asset_id = fig.fig_id
        if asset_id.startswith("asset_"):
            asset_type = infer_roadshow_asset_type(f"{fig.caption} {fig.path.name}")
        assets.append(
            EvidenceAsset(
                asset_id=asset_id,
                asset_type=asset_type,
                source="uploaded_figure",
                caption=(fig.caption or Path(fig.path).stem).replace("\n", " ").strip(),
                usable_for=_usable_for(asset_type),
                confidence="high" if asset_type in {"system_screenshot", "workflow_diagram"} else "medium",
                token=f"[[ASSET:{asset_id}]]" if asset_id.startswith("asset_") else f"[[FIG:{asset_id}]]",
            )
        )
    return assets


def _text_assets(text: str) -> list[EvidenceAsset]:
    assets: list[EvidenceAsset] = []
    seen: set[str] = set()
    for asset_type, hints in TEXT_EVIDENCE_HINTS:
        for line in text.splitlines():
            clean = re.sub(r"\s+", " ", line).strip(" #|*-")
            if len(clean) < 8 or not any(hint.lower() in clean.lower() for hint in hints):
                continue
            key = f"{asset_type}:{clean[:80]}"
            if key in seen:
                continue
            seen.add(key)
            assets.append(
                EvidenceAsset(
                    asset_id=f"text_{asset_type}_{len(assets) + 1:02d}",
                    asset_type=asset_type,
                    source="uploaded_text",
                    caption=_short(clean, 140),
                    usable_for=_usable_for(asset_type),
                    confidence="medium",
                )
            )
            break
    return assets


def _asset_type_from_figure(fig: PaperFigure, semantic_type: str) -> str:
    text = f"{fig.caption} {fig.path.stem}".lower()
    if semantic_type == "screenshot" or any(token in text for token in ("截图", "界面", "screen", "dashboard")):
        return "system_screenshot"
    if semantic_type == "diagram" or any(token in text for token in ("架构", "流程", "flow", "architecture")):
        return "workflow_diagram"
    if any(token in text for token in ("设备", "传感器", "现场", "硬件", "device")):
        return "device_or_scene"
    return "workflow_diagram"


def _usable_for(asset_type: str) -> str:
    mapping = {
        "system_screenshot": "产品效果测试、实操看板、材料看板",
        "workflow_diagram": "技术架构、数据流、实施过程",
        "policy_source": "政策背景、公开来源说明",
        "device_or_scene": "现场场景、设备接入、实操说明",
        "data_chart": "运行记录、测试图表、成果验证",
        "video_frame": "现场实操过程、演示复盘",
        "formal_document_image": "证书、协议、应用反馈、成果材料",
        "material_image": "项目支撑材料",
        "code_or_interface": "关键技术/代码还原",
        "test_record": "测试仪表盘、成果验证",
        "log_record": "支撑链路、审计追溯",
        "device_or_scene": "现场实操准备、设备接入",
        "result_claim_source": "应用价值、成果页",
        "fault_recovery": "风险控制、异常恢复",
    }
    return mapping.get(asset_type, "页面支撑材料")


def _short(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
