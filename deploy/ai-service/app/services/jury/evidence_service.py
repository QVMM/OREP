"""System-computed evidence counts for AI jury reviews."""

from __future__ import annotations

import re
from typing import Any


EVIDENCE_KEYWORDS = (
    "展示", "说明", "数据", "图表", "代码", "标准", "规范", "成本", "用户", "反馈",
    "演示", "测试", "安全", "团队", "分工", "功能", "模块", "对比", "成果", "应用",
)


def build_system_evidence_summary(official_result: dict[str, Any]) -> dict[str, Any]:
    """Count evidence from stored ASR, visual frames, and audio-video fusion data."""
    verbal_points = _verbal_points(official_result)
    visual_points = _visual_points(official_result)
    cross_count = _cross_validated_count(verbal_points, visual_points)
    return {
        "verbal_evidence_count": len(verbal_points),
        "visual_evidence_count": len(visual_points),
        "cross_validated_count": cross_count,
        "source": "system_computed",
    }


def has_visual_evidence(official_or_snapshot: dict[str, Any]) -> bool:
    return build_system_evidence_summary(official_or_snapshot).get("visual_evidence_count", 0) > 0


def _verbal_points(result: dict[str, Any]) -> list[dict[str, Any]]:
    asr = result.get("asr") or {}
    points = []
    for segment in asr.get("segments") or []:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        if _has_evidence_keyword(text):
            points.append({
                "time_min": _seconds_to_min(segment.get("start")),
                "text": text,
            })
    if points:
        return points
    transcript = str(asr.get("transcript") or "")
    if transcript:
        chunks = [chunk.strip() for chunk in re.split(r"[。！？\n]+", transcript) if chunk.strip()]
        return [{"time_min": None, "text": chunk} for chunk in chunks if _has_evidence_keyword(chunk)]
    return []


def _visual_points(result: dict[str, Any]) -> list[dict[str, Any]]:
    video = result.get("video_analysis") or {}
    fusion = result.get("fusion") or {}
    points = []
    seen = set()

    for frame in video.get("per_frame") or []:
        if not isinstance(frame, dict) or frame.get("error"):
            continue
        screen = frame.get("screen_content") or {}
        text = " ".join(str(screen.get(key) or "") for key in ("screen_type", "visible_text", "summary", "description"))
        timestamp = frame.get("timestamp_min")
        if text.strip() and not _has_similar_visual_point(points, timestamp, text):
            seen.add(("frame", timestamp, text[:60]))
            points.append({"time_min": _number_or_none(timestamp), "text": text.strip()})

    screen_summary = fusion.get("screen_content_summary") or {}
    for item in screen_summary.get("visible_texts") or []:
        text = str(item.get("text") or "").strip()
        timestamp = item.get("timestamp_min")
        if text and not _has_similar_visual_point(points, timestamp, text):
            seen.add(("visible_text", timestamp, text[:60]))
            points.append({"time_min": _number_or_none(timestamp), "text": text})

    for key_name in (
        "standard_detections", "code_detections", "chart_detections",
        "cost_detections", "security_detections", "collaboration_detections",
    ):
        for item in screen_summary.get(key_name) or []:
            text = " ".join(str(item.get(key) or "") for key in ("title", "text", "desc", "type"))
            timestamp = item.get("timestamp_min")
            key = (key_name, timestamp, text[:60])
            if text.strip() and key not in seen and not _has_similar_visual_point(points, timestamp, text):
                seen.add(key)
                points.append({"time_min": _number_or_none(timestamp), "text": text.strip()})

    return points


def _cross_validated_count(verbal_points: list[dict[str, Any]], visual_points: list[dict[str, Any]]) -> int:
    count = 0
    matched_visual = set()
    for verbal in verbal_points:
        v_time = verbal.get("time_min")
        v_tokens = _tokens(verbal.get("text"))
        for index, visual in enumerate(visual_points):
            if index in matched_visual:
                continue
            if _time_close(v_time, visual.get("time_min")) and (v_tokens & _tokens(visual.get("text"))):
                matched_visual.add(index)
                count += 1
                break
    return count


def _has_evidence_keyword(text: str) -> bool:
    return any(keyword in text for keyword in EVIDENCE_KEYWORDS)


def _tokens(text: Any) -> set[str]:
    value = str(text or "")
    return {keyword for keyword in EVIDENCE_KEYWORDS if keyword in value}


def _has_similar_visual_point(points: list[dict[str, Any]], timestamp: Any, text: Any) -> bool:
    current_time = _number_or_none(timestamp)
    current_tokens = _tokens(text)
    for point in points:
        if current_time is None or point.get("time_min") is None:
            continue
        if abs(current_time - float(point.get("time_min"))) <= 0.12:
            point_tokens = _tokens(point.get("text"))
            if current_tokens & point_tokens or str(text or "") in str(point.get("text") or "") or str(point.get("text") or "") in str(text or ""):
                return True
    return False


def _time_close(left: Any, right: Any, tolerance_min: float = 0.75) -> bool:
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance_min


def _seconds_to_min(value: Any) -> float | None:
    number = _number_or_none(value)
    return round(number / 60, 2) if number is not None else None


def _number_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
