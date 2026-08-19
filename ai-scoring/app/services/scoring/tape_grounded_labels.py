"""Deterministic observation labels from the tape itself.

Official score must be a function of (transcript + rubric), not of the LLM's
mood. Same cached transcript + same rule → same evidence/performance labels.
LLM extraction remains diagnostic (model review), it does not pick E-level or
performanceLevel for the ledger.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.services.evidence_extraction_service import PERFORMANCE_RATIOS

_SPLIT = re.compile(r"[、，,;；/|]+")
_STOP = {
    "是否", "以及", "或者", "进行", "相关", "对应", "内容", "情况", "方面",
    "需要", "可以", "没有", "不是", "这个", "一个", "我们", "他们",
}
_DEMO = re.compile(r"演示|运行|启动|部署|测试|讲解|展示|调试|编译|联调|现场")
_QTY = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|秒|分钟|次|个|人|元|ms|qps|QPS)", re.I)
_VERSION = "tape-grounded-labels-v1"


def transcript_sha256(asr_result: dict | None) -> str:
    text = compact_text(_transcript_text(asr_result))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compact_text(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def apply_tape_grounded_labels(
    extraction: dict | None,
    asr_result: dict | None,
    track_rule: dict | None,
) -> dict:
    """Overwrite observation E-level / performance from transcript + rubric."""
    payload = dict(extraction or {})
    observations = [dict(item) for item in (payload.get("observationEvidence") or []) if isinstance(item, dict)]
    rules = {
        item.get("observationCode"): item
        for item in (track_rule or {}).get("observations") or []
        if isinstance(item, dict) and item.get("observationCode")
    }
    text = _transcript_text(asr_result)
    compact = compact_text(text)
    segments = [
        seg for seg in (asr_result or {}).get("segments") or []
        if isinstance(seg, dict) and compact_text(seg.get("text"))
    ]
    stamped = []
    for item in observations:
        code = item.get("observationCode")
        rule = rules.get(code) or {}
        stamped.append(_stamp_one(item, rule, compact, segments, text))
    payload["observationEvidence"] = stamped
    quality = dict(payload.get("extractionQuality") or {})
    quality["tapeGrounded"] = True
    quality["tapeGroundedVersion"] = _VERSION
    quality["transcriptSha256"] = transcript_sha256(asr_result)
    payload["extractionQuality"] = quality
    return payload


def _stamp_one(
    item: dict,
    rule: dict,
    compact_transcript: str,
    segments: list[dict],
    raw_transcript: str,
) -> dict:
    out = dict(item)
    out["llmEvidenceLevel"] = item.get("evidenceLevel")
    out["llmPerformanceLevel"] = item.get("performanceLevel") or item.get("achievementLevel")
    tokens = tokens_for_observation(rule if rule else item)
    hits = [tok for tok in tokens if tok and compact_text(tok) in compact_transcript]
    timed_hits = [
        tok for tok in hits
        if any(compact_text(tok) in compact_text(seg.get("text")) and _seg_has_time(seg) for seg in segments)
    ]
    has_qty = bool(_QTY.search(raw_transcript or ""))
    has_demo = bool(_DEMO.search(raw_transcript or ""))
    level = _evidence_level(len(hits), len(timed_hits), has_qty, has_demo)
    ratio = (len(hits) / len(tokens)) if tokens else 0.0
    performance = _performance_level(ratio, has_demo and timed_hits)
    max_score = _safe_float(rule.get("maxScore") or item.get("maxScore"), 0.0)
    caps = rule.get("evidenceCaps") or item.get("evidenceCaps") or {}
    score_cap = _cap_points(caps, level, max_score)
    base = round(max_score * PERFORMANCE_RATIOS.get(performance, 0.0), 2)
    if level == "E0" and score_cap > base:
        base = score_cap
    out["evidenceLevel"] = level
    out["performanceLevel"] = performance
    out["achievementLevel"] = performance
    out["suggestedScoreCap"] = score_cap
    out["suggestedBaseScore"] = base
    out["scoreCapUnit"] = "points"
    out["labelSource"] = _VERSION
    out["tapeHits"] = hits
    out["tapeTimedHits"] = timed_hits
    out["evidenceReason"] = (
        f"按转写命中 {len(hits)}/{len(tokens)} 个观测词，"
        f"其中 {len(timed_hits)} 个可落到时间戳；等级 {level}，表现 {performance}"
    )
    return out


def tokens_for_observation(observation: dict) -> list[str]:
    raw: list[str] = []
    for field in ("claimTypes", "acceptableEvidence"):
        for item in observation.get(field) or []:
            raw.append(str(item))
    for item in observation.get("requiredInfo") or []:
        raw.extend(_SPLIT.split(str(item)))
    name = str(observation.get("observationName") or "").strip()
    if name:
        raw.append(name)
    seen = set()
    out = []
    for token in raw:
        cleaned = re.sub(r"\s+", "", token.strip())
        if len(cleaned) < 2 or len(cleaned) > 20 or cleaned in _STOP:
            continue
        key = compact_text(cleaned)
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _evidence_level(hit_count: int, timed_count: int, has_qty: bool, has_demo: bool) -> str:
    if hit_count <= 0:
        return "E0"
    if timed_count <= 0:
        return "E1"
    if timed_count >= 2 and (has_qty or has_demo):
        return "E3"
    if timed_count >= 1 and has_qty and has_demo:
        return "E3"
    return "E2"


def _performance_level(hit_ratio: float, demo_with_time: bool) -> str:
    if hit_ratio <= 0:
        return "not_demonstrated"
    if hit_ratio < 0.35:
        return "partial"
    if hit_ratio < 0.7:
        return "substantial"
    return "complete" if demo_with_time else "substantial"


def _cap_points(caps: dict, level: str, max_score: float) -> float:
    raw = caps.get(level)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.0
    if 0 < value <= 1 and max_score > 0:
        return round(max_score * value, 2)
    if max_score > 0:
        return round(min(max_score, max(0.0, value)), 2)
    return round(max(0.0, value), 2)


def _transcript_text(asr_result: dict | None) -> str:
    asr = asr_result or {}
    text = str(asr.get("transcript") or "").strip()
    if text:
        return text
    parts = []
    for seg in asr.get("segments") or []:
        if isinstance(seg, dict) and seg.get("text"):
            parts.append(str(seg.get("text")))
    return "".join(parts)


def _seg_has_time(seg: dict) -> bool:
    for key in ("start", "startMs", "begin"):
        if seg.get(key) is not None:
            try:
                return float(seg.get(key)) >= 0
            except (TypeError, ValueError):
                return True
    return False


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
