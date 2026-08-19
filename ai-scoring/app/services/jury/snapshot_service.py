"""Evidence snapshot helpers for AI jury review."""
from __future__ import annotations

from copy import deepcopy


ALLOWED_RESULT_KEYS = (
    "meeting_id",
    "started_at",
    "completed_at",
    "audio_info",
    "asr",
    "speech_quality",
    "video_analysis",
    "video_camera_analysis",
    "video_screen_analysis",
    "fusion",
    "recording_mode",
    "has_video",
    "roadshow_memory",
    "roadshowMemory",
)


FORBIDDEN_KEYS = {
    "ai_score",
    "ai_score_comparison",
    "official_score",
    "official_ai_score",
    "overall_score",
    "dimensions",
    "highlights",
    "critical_issues",
    "improvement_priorities",
    "character_profile",
}


def _strip_forbidden(value):
    if isinstance(value, dict):
        return {
            key: _strip_forbidden(item)
            for key, item in value.items()
            if key not in FORBIDDEN_KEYS
        }
    if isinstance(value, list):
        return [_strip_forbidden(item) for item in value]
    return value


def _safe_memory_item(item):
    if not isinstance(item, dict):
        return {"title": str(item or ""), "description": str(item or "")}
    safe = {
        key: deepcopy(item.get(key))
        for key in (
            "title",
            "description",
            "status",
            "conclusion",
            "severity",
            "category",
            "acceptance",
            "roundNo",
            "issueCount",
        )
        if item.get(key) not in (None, "")
    }
    anchors = _safe_evidence_anchors(item.get("evidenceAnchors") or item.get("evidence_anchors"))
    if anchors:
        safe["evidence_anchors"] = anchors
    return safe


def _safe_evidence_anchors(anchors):
    safe_anchors = []
    for anchor in anchors if isinstance(anchors, list) else []:
        if not isinstance(anchor, dict):
            continue
        safe = {
            key: deepcopy(anchor.get(key))
            for key in ("type", "summary", "sourceRef", "source_ref", "roundNo", "meetingId", "aiReportId")
            if anchor.get(key) not in (None, "")
        }
        if "source_ref" in safe and "sourceRef" not in safe:
            safe["sourceRef"] = safe.pop("source_ref")
        if safe:
            safe_anchors.append(safe)
        if len(safe_anchors) >= 4:
            break
    return safe_anchors


def _build_jury_memory_context(memory_summary: dict | None) -> dict:
    """Keep issue continuity for judges while removing score anchors."""
    if not isinstance(memory_summary, dict):
        return {}
    full_score_gap = memory_summary.get("fullScoreGap") or memory_summary.get("full_score_gap") or {}
    safe = {
        "prior_issue_review": [
            _safe_memory_item(item)
            for item in (memory_summary.get("priorIssueReview") or memory_summary.get("prior_issue_review") or [])[:8]
        ],
        "new_issues": [
            _safe_memory_item(item)
            for item in (memory_summary.get("newIssues") or memory_summary.get("new_issues") or [])[:8]
        ],
        "training_plan": [
            _safe_memory_item(item)
            for item in (memory_summary.get("trainingPlan") or memory_summary.get("training_plan") or [])[:8]
        ],
        "full_score_gap_reasons": [
            str(item)
            for item in (full_score_gap.get("reasons") or [])[:6]
            if item
        ],
        "timeline": [
            _safe_memory_item(item)
            for item in (memory_summary.get("timeline") or [])[-6:]
        ],
    }
    return {key: value for key, value in safe.items() if value}


def build_jury_evidence_snapshot(
    pipeline_result: dict,
    project_info: dict | None = None,
    memory_summary: dict | None = None,
) -> dict:
    """Build the judge input snapshot without official scoring anchors."""
    snapshot = {
        "snapshot_version": "ai_jury_evidence_v2",
        "project_info": deepcopy(project_info or {}),
    }
    for key in ALLOWED_RESULT_KEYS:
        if key in pipeline_result:
            snapshot[key] = deepcopy(pipeline_result[key])
    memory = memory_summary or snapshot.pop("roadshowMemory", None) or snapshot.pop("roadshow_memory", None)
    memory_context = _build_jury_memory_context(memory)
    if memory_context:
        snapshot["roadshow_memory"] = memory_context
    return _strip_forbidden(snapshot)
