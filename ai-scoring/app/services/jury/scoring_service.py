"""File-backed orchestration for independent AI jury review."""
from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import re
import threading
import traceback
import uuid
from datetime import datetime
from typing import Any

from app.config import settings
from app.services import llm_scoring_service
from app.services.jury.aggregate_service import aggregate_judge_reports
from app.services.jury.evidence_service import build_system_evidence_summary
from app.services.jury.persona_repository import load_personas
from app.services.jury.personas import select_personas
from app.services.jury.snapshot_service import build_jury_evidence_snapshot

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
# MiniMax 评分通道已停用：额度不足时会返回 429，不能再进入评审团调度。
SUPPORTED_PROVIDERS = {"deepseek"}


def _now() -> str:
    return datetime.now().isoformat()


def _jury_root() -> str:
    path = os.path.join(settings.UPLOAD_DIR, "results", "jury")
    os.makedirs(path, exist_ok=True)
    return path


def _session_path(session_id: str) -> str:
    return os.path.join(_jury_root(), f"jury_session_{session_id}.json")


def _latest_path(meeting_id: str) -> str:
    return os.path.join(_jury_root(), f"latest_jury_{meeting_id}.json")


def _snapshot_path(session_id: str) -> str:
    return os.path.join(_jury_root(), f"evidence_snapshot_{session_id}.json")


def _write_json(path: str, data: dict):
    with _LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _official_result_path(meeting_id: str) -> str:
    return os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")


def load_official_result(meeting_id: str) -> dict:
    path = _official_result_path(meeting_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"会议 {meeting_id} 的本场评分结果不存在")
    return _read_json(path)


def get_latest_jury_session(meeting_id: str) -> dict | None:
    path = _latest_path(meeting_id)
    if not os.path.exists(path):
        return None
    index = _read_json(path)
    session_id = index.get("jury_session_id")
    if not session_id:
        return None
    session_path = _session_path(session_id)
    if not os.path.exists(session_path):
        return None
    return _read_json(session_path)


def _extract_fusion_context(snapshot: dict) -> dict | None:
    fusion = snapshot.get("fusion")
    if not isinstance(fusion, dict) or fusion.get("error"):
        return None
    return {
        "trends": fusion.get("trends", {}),
        "contradictions": fusion.get("contradictions", []),
        "visual_aggregates": snapshot.get("video_analysis", {}).get("aggregates", {}),
        "audio_windows": fusion.get("audio_windows", []),
        "screen_content_summary": fusion.get("screen_content_summary", {}),
    }


def resolve_provider_channels(raw_channels: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Resolve configured model channels and keep only supported providers."""
    if isinstance(raw_channels, str):
        candidates = [item.strip() for item in raw_channels.split(",")]
    elif raw_channels:
        candidates = [str(item).strip() for item in raw_channels]
    else:
        candidates = []
    providers = [item for item in candidates if item in SUPPORTED_PROVIDERS]
    return providers or ["deepseek"]


def resolve_jury_provider_channels(requested_provider: str | list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Resolve jury channels from env first, then request payload."""
    configured = str(getattr(settings, "AI_JURY_PROVIDERS", "") or "").strip()
    return resolve_provider_channels(configured or requested_provider)


def provider_for_member(member: dict, channels: list[str]) -> str:
    """Assign provider channels by judge seat, keeping a stable round-robin."""
    if not channels:
        return "deepseek"
    try:
        seat_no = int(member.get("seat_no") or 1)
    except (TypeError, ValueError):
        seat_no = 1
    return channels[(seat_no - 1) % len(channels)]


def jury_member_total_timeout_seconds(stage_timeout_seconds: int, member_retries: int) -> int:
    """Allow each member to finish all three staged LLM calls on every attempt."""
    attempts = max(1, int(member_retries) + 1)
    return max(1, int(stage_timeout_seconds)) * 3 * attempts + 10


def is_failed_llm_report(raw_report: dict | None) -> bool:
    """Detect fallback reports returned by the base LLM scorer after provider errors."""
    if not isinstance(raw_report, dict):
        return True
    if raw_report.get("status") in {"review_required", "scoring_completed_report_review_required"}:
        return True
    if raw_report.get("overall_score") is None:
        return True
    issues = raw_report.get("critical_issues") or []
    has_failure_issue = any(str(item).startswith("评分失败") for item in issues)
    has_no_dimensions = not bool(raw_report.get("dimensions"))
    try:
        score = float(raw_report.get("overall_score", 0) or 0)
    except (TypeError, ValueError):
        score = 0
    return has_failure_issue and has_no_dimensions and score == 0


def validate_jury_evidence_quality(official_result: dict) -> None:
    """Reject jury generation when a video meeting has no valid visual evidence."""
    if not official_result.get("has_video"):
        return
    video = official_result.get("video_analysis") or {}
    aggregates = video.get("aggregates") or {}
    fusion = official_result.get("fusion") or {}
    has_per_frame = bool(video.get("per_frame"))
    has_screen_summary = bool(aggregates.get("screen_content_summary") or fusion.get("screen_content_summary"))
    has_timeline = bool(fusion.get("timeline"))
    if aggregates.get("error") or (not has_per_frame and not has_screen_summary and not has_timeline):
        raise ValueError("该会议有视频，但视频帧分析没有有效结果，请先重新生成AI评分或补跑视频分析")


def _normalize_judge_report(
    raw_report: dict,
    member: dict,
    provider: str,
    started_at: str,
) -> dict:
    completed_at = _now()
    report = {
        "id": member["seat_no"],
        "member_id": member["seat_no"],
        "seat_no": member["seat_no"],
        "persona_code": member["code"],
        "persona_name": member.get("name"),
        "role_label": member.get("role_label") or member.get("name"),
        "overall_score": raw_report.get("overall_score"),
        "dimensions": raw_report.get("dimensions", {}),
        "highlights": raw_report.get("highlights", []),
        "critical_issues": raw_report.get("critical_issues", []),
        "improvement_priorities": raw_report.get("improvement_priorities", []),
        "evidence_summary": raw_report.get("evidence_summary", {}),
        "persona_view": raw_report.get("persona_view") or {
            "persona_code": member["code"],
            "role_label": member.get("role_label") or member.get("name"),
            "top_concerns": [],
            "score_reasoning_style": member.get("short_label", ""),
            "optimization_angle": member.get("prompt_modifier", ""),
        },
        "model": raw_report.get("model", ""),
        "provider": raw_report.get("provider", provider),
        "tokens_used": raw_report.get("tokens_used", {}),
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
    }
    return report


def _score_member(snapshot: dict, member: dict, provider: str, ppt_recognition: bool) -> dict:
    started_at = _now()
    attempts = max(1, settings.AI_JURY_MEMBER_RETRIES + 1)
    last_error = None
    system_evidence = build_system_evidence_summary(snapshot)
    use_visual_evidence = bool(ppt_recognition or system_evidence.get("visual_evidence_count", 0) > 0)
    project_info = dict(snapshot.get("project_info") or {})
    if snapshot.get("roadshow_memory"):
        project_info["roadshow_memory"] = snapshot["roadshow_memory"]
    dispute_context = snapshot.get("dispute_review_context") or {}
    if dispute_context:
        project_info["jury_review_mode"] = "dispute_review"
        project_info["dispute_review_context"] = dispute_context
        member = dict(member)
        member["review_mode"] = "dispute_review"
        member["review_scope"] = "围绕规则引擎结果复核争议点，只输出复核意见、争议点与人工复核建议，不覆盖最终分。"
        member["dispute_review_context"] = dispute_context
    for attempt in range(1, attempts + 1):
        try:
            raw_report = llm_scoring_service.score_roadshow(
                snapshot.get("asr", {}),
                snapshot.get("speech_quality", {}),
                project_info,
                provider=provider,
                fusion_context=_extract_fusion_context(snapshot),
                ppt_recognition=use_visual_evidence,
                persona_context=member,
            )
            if is_failed_llm_report(raw_report):
                raise RuntimeError("; ".join(str(item) for item in raw_report.get("critical_issues", [])) or "模型评分失败")
            report = _normalize_judge_report(raw_report, member, provider, started_at)
            report["attempts"] = attempt
            return report
        except Exception as exc:
            last_error = exc

    return _failed_member_report(member, provider, started_at, str(last_error), traceback.format_exc())


def _failed_member_report(member: dict, provider: str, started_at: str, message: str, trace: str = "") -> dict:
    return {
        "id": member["seat_no"],
        "member_id": member["seat_no"],
        "seat_no": member["seat_no"],
        "persona_code": member["code"],
        "persona_name": member.get("name"),
        "role_label": member.get("role_label") or member.get("name"),
        "overall_score": None,
        "dimensions": {},
        "critical_issues": [],
        "provider": provider,
        "status": "failed",
        "error_message": message,
        "traceback": trace,
        "started_at": started_at,
        "completed_at": _now(),
    }


def _build_session(
    meeting_id: str,
    official_result: dict,
    project_info: dict | None,
    provider: str,
    ppt_recognition: bool,
    memory_summary: dict | None = None,
    dispute_review_context: dict | None = None,
) -> dict:
    validate_jury_evidence_quality(official_result)
    session_id = uuid.uuid4().hex
    official_score = official_result.get("ai_score", {}).get("overall_score")
    official_evidence_summary = build_system_evidence_summary(official_result)
    snapshot = build_jury_evidence_snapshot(
        official_result,
        project_info or official_result.get("project_info") or {},
        memory_summary=memory_summary,
    )
    if dispute_review_context:
        snapshot["dispute_review_context"] = dispute_review_context
    snapshot_file = _snapshot_path(session_id)
    _write_json(snapshot_file, snapshot)

    seed = f"{meeting_id}:ai_jury_v1"
    persona_pool = [persona for persona in load_personas() if persona.get("enabled", True)]
    members = select_personas(seed, count=settings.AI_JURY_COUNT, pool=persona_pool)
    now = _now()
    session = {
        "jury_session_id": session_id,
        "meeting_id": str(meeting_id),
        "status": "processing",
        "seed": seed,
        "judge_count": len(members),
        "provider": provider,
        "ppt_recognition": ppt_recognition,
        "official_score": official_score,
        "review_mode": "dispute_review",
        "dispute_review_context": dispute_review_context or {},
        "official_evidence_summary": official_evidence_summary,
        "roadshow_memory_summary": snapshot.get("roadshow_memory", {}),
        "evidence_snapshot_path": snapshot_file,
        "members": members,
        "judge_reports": [],
        "aggregate": None,
        "started_at": now,
        "completed_at": None,
        "updated_at": now,
    }
    _write_json(_session_path(session_id), session)
    _write_json(_latest_path(meeting_id), {
        "meeting_id": str(meeting_id),
        "jury_session_id": session_id,
        "updated_at": now,
    })
    return session


def _finish_session(session: dict, reports: list[dict]) -> dict:
    successful = [report for report in reports if report.get("status") == "completed"]
    aggregate = aggregate_judge_reports(successful, official_score=session.get("official_score"))
    status = "completed" if len(successful) == session.get("judge_count") else "partial_failed"
    if len(successful) < 3:
        status = "failed"

    session.update({
        "status": status,
        "judge_reports": reports,
        "aggregate": aggregate,
        "jury_raw_avg": aggregate.get("raw_average_score"),
        "jury_trimmed_avg": aggregate.get("trimmed_average_score"),
        "score_diff_from_official": aggregate.get("score_diff_from_official"),
        "completed_at": _now(),
        "updated_at": _now(),
    })
    _write_json(_session_path(session["jury_session_id"]), session)
    try:
        from app.services.report_service import refresh_report_after_jury
        refresh_report_after_jury(session.get("meeting_id"))
    except Exception:
        logger.exception("[%s] 评审团完成后重出报告失败", session.get("meeting_id"))
    return session


def run_jury_review(
    meeting_id: str,
    official_result: dict | None = None,
    project_info: dict | None = None,
    provider: str = "deepseek",
    ppt_recognition: bool = False,
    memory_summary: dict | None = None,
    dispute_review_context: dict | None = None,
) -> dict:
    official = official_result or load_official_result(meeting_id)
    session = _build_session(
        meeting_id,
        official,
        project_info,
        provider,
        ppt_recognition,
        memory_summary=memory_summary,
        dispute_review_context=dispute_review_context,
    )
    snapshot = _read_json(session["evidence_snapshot_path"])

    reports: list[dict] = []
    provider_channels = resolve_jury_provider_channels(provider)
    max_workers = max(1, min(settings.AI_JURY_MAX_WORKERS, len(session["members"])))
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_map = {
            executor.submit(
                _score_member,
                snapshot,
                member,
                provider_for_member(member, provider_channels),
                ppt_recognition,
            ): member
            for member in session["members"]
        }
        member_timeout = jury_member_total_timeout_seconds(
            settings.AI_JURY_MEMBER_TIMEOUT_SECONDS,
            settings.AI_JURY_MEMBER_RETRIES,
        )
        done, not_done = concurrent.futures.wait(
            future_map,
            timeout=member_timeout,
            return_when=concurrent.futures.ALL_COMPLETED,
        )
        for future in done:
            reports.append(future.result())
            partial = dict(session)
            partial["judge_reports"] = sorted(reports, key=lambda item: item.get("seat_no", 0))
            partial["updated_at"] = _now()
            _write_json(_session_path(session["jury_session_id"]), partial)
        for future in not_done:
            member = future_map[future]
            future.cancel()
            reports.append(_failed_member_report(
                member,
                provider_for_member(member, provider_channels),
                _now(),
                f"评委报告生成超时（>{member_timeout}秒）",
            ))
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    reports.sort(key=lambda item: item.get("seat_no", 0))
    return _finish_session(session, reports)


def start_jury_review_background(
    meeting_id: str,
    official_result: dict | None = None,
    project_info: dict | None = None,
    provider: str = "deepseek",
    ppt_recognition: bool = False,
    memory_summary: dict | None = None,
    dispute_review_context: dict | None = None,
) -> dict:
    official = official_result or load_official_result(meeting_id)
    session = _build_session(
        meeting_id,
        official,
        project_info,
        provider,
        ppt_recognition,
        memory_summary=memory_summary,
        dispute_review_context=dispute_review_context,
    )

    def _runner():
        try:
            snapshot = _read_json(session["evidence_snapshot_path"])
            reports = []
            provider_channels = resolve_jury_provider_channels(provider)
            max_workers = max(1, min(settings.AI_JURY_MAX_WORKERS, len(session["members"])))
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
            try:
                future_map = {
                    executor.submit(
                        _score_member,
                        snapshot,
                        member,
                        provider_for_member(member, provider_channels),
                        ppt_recognition,
                    ): member
                    for member in session["members"]
                }
                member_timeout = jury_member_total_timeout_seconds(
                    settings.AI_JURY_MEMBER_TIMEOUT_SECONDS,
                    settings.AI_JURY_MEMBER_RETRIES,
                )
                done, not_done = concurrent.futures.wait(
                    future_map,
                    timeout=member_timeout,
                    return_when=concurrent.futures.ALL_COMPLETED,
                )
                for future in done:
                    reports.append(future.result())
                    partial = get_latest_jury_session(meeting_id) or dict(session)
                    partial["judge_reports"] = sorted(reports, key=lambda item: item.get("seat_no", 0))
                    partial["updated_at"] = _now()
                    _write_json(_session_path(session["jury_session_id"]), partial)
                for future in not_done:
                    member = future_map[future]
                    future.cancel()
                    reports.append(_failed_member_report(
                        member,
                        provider_for_member(member, provider_channels),
                        _now(),
                        f"评委报告生成超时（>{member_timeout}秒）",
                    ))
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            reports.sort(key=lambda item: item.get("seat_no", 0))
            _finish_session(session, reports)
        except Exception as exc:
            session.update({
                "status": "failed",
                "error_message": str(exc),
                "traceback": traceback.format_exc(),
                "completed_at": _now(),
                "updated_at": _now(),
            })
            _write_json(_session_path(session["jury_session_id"]), session)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    return session


def public_jury_result(session: dict | None) -> dict:
    if not session:
        return {"status": "empty"}

    aggregate = session.get("aggregate") or {}
    system_evidence_summary = session.get("official_evidence_summary") or _load_system_evidence_summary(session.get("meeting_id"))
    members = []
    reports_by_code = {
        report.get("persona_code"): report
        for report in session.get("judge_reports", [])
    }
    removed_high = (aggregate.get("removed_high") or {}).get("persona_code")
    removed_low = (aggregate.get("removed_low") or {}).get("persona_code")
    for member in session.get("members", []):
        report = reports_by_code.get(member.get("code"), {})
        persona_view = _normalize_persona_view(report.get("persona_view", {}))
        members.append({
            "member_id": member.get("seat_no"),
            "seat_no": member.get("seat_no"),
            "persona_code": member.get("code"),
            "role_label": member.get("role_label") or member.get("name"),
            "short_label": member.get("short_label"),
            "overall_score": report.get("overall_score"),
            "status": report.get("status", "pending"),
            "removed_role": (
                "highest" if member.get("code") == removed_high
                else "lowest" if member.get("code") == removed_low
                else ""
            ),
            "summary": _judge_summary(report, member),
            "persona_view": persona_view,
            "critical_issues": (report.get("critical_issues") or [])[:3],
            "dimensions": report.get("dimensions", {}),
            "highlights": report.get("highlights", []),
            "improvement_priorities": report.get("improvement_priorities", []),
            "evidence_summary": system_evidence_summary or report.get("evidence_summary", {}),
            "model": report.get("model", ""),
            "provider": report.get("provider", ""),
            "tokens_used": report.get("tokens_used", {}),
            "error_message": report.get("error_message", ""),
        })

    return {
        "meeting_id": session.get("meeting_id"),
        "jury_session_id": session.get("jury_session_id"),
        "judge_count": session.get("judge_count") or aggregate.get("judge_count"),
        "status": session.get("status"),
        "review_mode": session.get("review_mode") or "dispute_review",
        "dispute_review_context": session.get("dispute_review_context") or {},
        "official_score": session.get("official_score"),
        "jury": {
            "raw_average_score": aggregate.get("raw_average_score"),
            "trimmed_average_score": aggregate.get("trimmed_average_score"),
            "trimmed_total_score": aggregate.get("trimmed_total_score"),
            "trimmed_count": aggregate.get("trimmed_count"),
            "score_diff_from_official": aggregate.get("score_diff_from_official"),
            "highest_score": aggregate.get("highest_score"),
            "lowest_score": aggregate.get("lowest_score"),
            "removed_high": aggregate.get("removed_high"),
            "removed_low": aggregate.get("removed_low"),
            "successful_count": aggregate.get("successful_count"),
            "judge_count": session.get("judge_count") or aggregate.get("judge_count"),
        },
        "members": members,
        "aggregate": {
            "dimension_stats": aggregate.get("dimension_stats", []),
            "consensus_issues": aggregate.get("consensus_issues", []),
        },
        "evidence_summary": system_evidence_summary,
        "started_at": session.get("started_at"),
        "completed_at": session.get("completed_at"),
        "error_message": session.get("error_message"),
    }


def _judge_summary(report: dict, member: dict) -> str:
    view = _normalize_persona_view(report.get("persona_view") or {})
    concerns = view.get("top_concerns") or []
    if concerns:
        return str(concerns[0])
    issues = report.get("critical_issues") or []
    if issues:
        first = issues[0]
        if isinstance(first, dict):
            return str(first.get("issue") or first.get("text") or member.get("prompt_modifier", ""))
        return str(first)
    return member.get("prompt_modifier", "等待评委报告生成。")


def _normalize_persona_view(view: dict | None) -> dict:
    normalized = dict(view or {})
    normalized["top_concerns"] = _as_list(normalized.get("top_concerns"))
    return normalized


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        parts = [
            part.strip()
            for part in re.split(r"[、,，;；\n]+", value)
            if part.strip()
        ]
        return parts or [value]
    return [value]


def _load_system_evidence_summary(meeting_id: str | int | None) -> dict:
    if meeting_id is None:
        return {}
    try:
        return build_system_evidence_summary(load_official_result(str(meeting_id)))
    except Exception:
        return {}
