"""Stable asset registry for vocational roadshow source materials."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RoadshowAssetRecord:
    asset_id: str
    asset_type: str
    original_rel: str
    filename: str
    path: str
    href: str
    caption: str
    natural_width: int = 0
    natural_height: int = 0
    token: str = ""


IMAGE_ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


MOJIBAKE_CHARS = (
    "µ╕⌐σ╖▒ÅτÄΣΦäöΘ┐┤₧"
    "鏀跨瓥瀵煎悜鎽樿鐜鐩戞祴澶у睆璁惧鑱斿姩鎺у埗"
    "鍛婅宸ュ崟闂幆绉诲姩绔伐浣滃彴鏁版嵁鍒嗘瀽涓績"
    "浼犳劅鑺傜偣杩戞櫙绠辨帴绾垮浘"
)


def _mojibake_score(value: str) -> int:
    score = sum(3 for ch in value if ch in MOJIBAKE_CHARS)
    score += value.count("�") * 5
    score += sum(5 for ch in value if "\ue000" <= ch <= "\uf8ff")
    score -= sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
    return score


def normalize_roadshow_asset_rel(rel: str) -> str:
    """Recover common CP437-decoded Chinese zip paths before semantic routing."""
    if not rel:
        return rel
    candidates = [rel]
    try:
        raw_bytes = rel.encode("cp437")
    except UnicodeEncodeError:
        raw_bytes = b""
    if raw_bytes:
        for encoding in ("utf-8", "gb18030"):
            try:
                candidates.append(raw_bytes.decode(encoding))
            except UnicodeDecodeError:
                continue
    for source_encoding in ("gb18030", "latin1", "cp1252"):
        try:
            candidates.append(rel.encode(source_encoding).decode("utf-8"))
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return min(candidates, key=_mojibake_score)


def infer_roadshow_asset_type(rel: str) -> str:
    rel = normalize_roadshow_asset_rel(rel)
    text = rel.lower()
    if any(token in rel for token in ("政策", "官网", "文件", "产业发展", "规划", "标准")):
        return "policy_source"
    if any(token in rel for token in ("视频", "关键帧", "录屏")) or any(token in text for token in ("video", "frame")):
        return "video_frame"
    if any(token in rel for token in ("证书", "专利", "协议", "反馈", "证明", "合作", "软著", "知识产权")):
        return "formal_document_image"
    if any(token in rel for token in ("截图", "系统", "界面", "大屏", "驾驶舱", "工单", "移动端", "工作台", "后台")) or any(
        token in text for token in ("screenshot", "screen", "dashboard", "ui", "app")
    ):
        return "system_screenshot"
    if any(token in rel for token in ("数据", "图表", "趋势", "统计", "对比", "效率", "运行", "稳定性", "成效", "分析中心")) or any(
        token in text for token in ("chart", "data", "result", "metric")
    ):
        return "data_chart"
    if any(token in rel for token in ("设备", "传感", "节点", "控制箱", "接线", "温室", "现场", "巡检", "布设", "硬件")) or any(
        token in text for token in ("device", "scene", "photo", "hardware")
    ):
        return "device_or_scene"
    return "material_image"


def asset_caption_from_rel(rel: str) -> str:
    rel = normalize_roadshow_asset_rel(rel)
    stem = Path(rel).stem
    clean = re.sub(r"[_\-]+", " ", stem).strip()
    asset_type = infer_roadshow_asset_type(rel)
    prefix = {
        "policy_source": "政策/公开来源截图",
        "system_screenshot": "系统界面截图",
        "device_or_scene": "设备或现场素材",
        "data_chart": "运行数据图表",
        "video_frame": "演示视频关键帧",
        "formal_document_image": "成果或合作材料图片",
        "material_image": "项目素材图片",
    }.get(asset_type, "项目素材图片")
    return f"{prefix}: {clean or Path(rel).name}"


def write_asset_registry(output_dir: Path, records: list[RoadshowAssetRecord]) -> None:
    payload = {
        "version": 1,
        "assets": [asdict(record) for record in records],
    }
    for target in (output_dir / "asset_registry.json", output_dir / "images" / "asset_registry.json"):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            continue


def load_asset_registry(project_dir: Path) -> dict[str, dict[str, Any]]:
    candidates = [
        project_dir / "sources" / "asset_registry.json",
        project_dir / "sources" / "images" / "asset_registry.json",
        project_dir / "asset_registry.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        assets = data.get("assets") if isinstance(data, dict) else data
        if not isinstance(assets, list):
            continue
        by_id: dict[str, dict[str, Any]] = {}
        for item in assets:
            if not isinstance(item, dict):
                continue
            asset_id = str(item.get("asset_id") or "").strip()
            if not asset_id:
                continue
            by_id[asset_id] = item
        if by_id:
            return by_id
    return {}
