"""Session-style evidence extraction for long roadshows.

Inspired by CLI agent session management:
- Never dump the full 50+ minute transcript into one LLM call.
- Scan the media in time windows (working memory).
- Persist cumulative facts (session memory).
- Synthesize each observation from memory, not from raw full text.
"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_MEMORY_VERSION = "evidence-memory-session-v1"
_LEVEL_ORDER = {"E0": 0, "E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5}
_PERF_ORDER = {
    "not_demonstrated": 0,
    "partial": 1,
    "substantial": 2,
    "complete": 3,
}


def is_scan_incomplete(window_count: int, failure_count: int) -> bool:
    windows = max(0, int(window_count or 0))
    failures = max(0, int(failure_count or 0))
    if windows <= 0 or failures <= 0:
        return False
    threshold = max(1, int(getattr(settings, "LLM_EVIDENCE_INCOMPLETE_MIN_FAILED_WINDOWS", 2) or 2))
    return failures >= min(threshold, windows)


def is_extraction_incomplete(extraction: dict | None) -> bool:
    if not isinstance(extraction, dict):
        return False
    quality = extraction.get("extractionQuality") or {}
    if quality.get("incomplete") is True:
        return True
    return is_scan_incomplete(quality.get("windowCount") or 0, quality.get("scanFailureCount") or 0)


def extraction_incomplete_error(extraction: dict | None) -> str:
    quality = (extraction or {}).get("extractionQuality") or {}
    failed = int(quality.get("scanFailureCount") or 0)
    return f"extraction_incomplete:{failed}"


def extraction_incomplete_message(extraction: dict | None) -> str:
    quality = (extraction or {}).get("extractionQuality") or {}
    failed = int(quality.get("scanFailureCount") or 0)
    return f"本场有 {failed} 窗证据未建成，正式分未入库，请重评"


def should_use_memory_session(asr_result: dict | None) -> bool:
    segments = (asr_result or {}).get("segments") or []
    duration = float((asr_result or {}).get("duration") or 0)
    text_chars = sum(len(str(seg.get("text") or "")) for seg in segments if isinstance(seg, dict))
    if not text_chars:
        text_chars = len(str((asr_result or {}).get("transcript") or ""))
    min_duration = float(getattr(settings, "LLM_EVIDENCE_MEMORY_MIN_DURATION_SEC", 900) or 900)
    min_chars = int(getattr(settings, "LLM_EVIDENCE_MEMORY_MIN_CHARS", 6000) or 6000)
    return duration >= min_duration or text_chars >= min_chars or len(segments) >= 80


def extract_with_memory_session(
    *,
    client,
    model_name: str,
    track_rule: dict[str, Any],
    asr_result: dict,
    fusion_context: dict | None = None,
    scoring_context: dict | None = None,
    provider: str = "deepseek",
) -> dict[str, Any]:
    """Run windowed scan + memory merge + observation synthesis."""
    from app.services.evidence_extraction_service import extract_evidence_from_llm_payload
    from app.services.llm_scoring_service import chat_completion_kwargs

    windows = _build_time_windows(asr_result, fusion_context)
    obs_catalog = _observation_catalog(track_rule)
    memory = _new_memory(track_rule, windows)
    attempt_log: list[dict[str, Any]] = []
    timeout = float(getattr(settings, "LLM_EVIDENCE_REQUEST_TIMEOUT_SECONDS", 120) or 120)
    max_tokens = max(1200, int(getattr(settings, "LLM_EVIDENCE_MEMORY_MAX_TOKENS", 2500) or 2500))
    retry_tokens = max(
        max_tokens + 1,
        int(getattr(settings, "LLM_EVIDENCE_MEMORY_RETRY_MAX_TOKENS", 4000) or 4000),
    )

    # Phase 1: scan each window into session memory.
    for index, window in enumerate(windows, start=1):
        prompt = _scan_prompt(
            obs_catalog=obs_catalog,
            window=window,
            memory=memory,
            window_index=index,
            window_total=len(windows),
        )
        payload, metas = _json_call_with_retry(
            client=client,
            model_name=model_name,
            system=(
                "你是OREP路演证据扫描器。当前只看本时间窗，更新会话记忆。"
                "禁止输出总分/维度分。只输出JSON。"
            ),
            user=prompt,
            max_tokens=max_tokens,
            retry_tokens=retry_tokens,
            timeout=timeout,
            stage=f"memory_scan_{index}",
        )
        attempt_log.extend(metas)
        if payload is None:
            last = metas[-1] if metas else {}
            memory["scanFailures"].append({
                "windowId": window["windowId"],
                "timeRange": window.get("timeRange"),
                "startSec": window.get("startSec"),
                "endSec": window.get("endSec"),
                "error": last.get("error") or last.get("finish_reason") or "scan_failed",
            })
            continue
        _merge_scan_into_memory(memory, payload, window)

    # Phase 2: synthesize each observation from memory only.
    final_payload = {
        "claims": list(memory.get("claims") or []),
        "evidenceItems": list(memory.get("evidenceItems") or []),
        "observationEvidence": [],
        "deductionCandidates": list(memory.get("deductionCandidates") or []),
        "recoveryCandidates": list(memory.get("recoveryCandidates") or []),
        "riskFlags": list(memory.get("riskFlags") or []),
        "extractionQuality": {"jsonParseable": True, "strategy": "memory_session"},
    }
    batch_size = max(1, int(getattr(settings, "LLM_EVIDENCE_MEMORY_OBS_BATCH", 3) or 3))
    for start in range(0, len(obs_catalog), batch_size):
        batch = obs_catalog[start:start + batch_size]
        prompt = _synthesize_prompt(batch, memory, failed_windows=memory.get("scanFailures") or [])
        payload, meta = _json_call(
            client=client,
            model_name=model_name,
            system=(
                "你是OREP观测点合成器。只能使用会话记忆中的证据，禁止编造时间点与原文。"
                "禁止输出总分。只输出JSON。"
            ),
            user=prompt,
            max_tokens=max_tokens,
            timeout=timeout,
            stage=f"memory_synth_{start // batch_size + 1}",
        )
        attempt_log.append(meta)
        if payload is None:
            # Conservative fallback from memory notes.
            for obs in batch:
                final_payload["observationEvidence"].append(
                    _fallback_observation_from_memory(obs, memory)
                )
            continue
        for item in payload.get("observationEvidence") or []:
            if isinstance(item, dict):
                final_payload["observationEvidence"].append(item)
        for key in ("deductionCandidates", "recoveryCandidates", "riskFlags", "claims", "evidenceItems"):
            for item in payload.get(key) or []:
                if isinstance(item, dict):
                    final_payload.setdefault(key, []).append(item)

    extraction = extract_evidence_from_llm_payload(
        json.dumps(final_payload, ensure_ascii=False),
        track_rule,
    )
    quality = extraction.setdefault("extractionQuality", {})
    quality["strategy"] = "memory_session"
    quality["memoryVersion"] = _MEMORY_VERSION
    quality["windowCount"] = len(windows)
    quality["scanFailureCount"] = len(memory.get("scanFailures") or [])
    quality["incomplete"] = is_scan_incomplete(len(windows), quality["scanFailureCount"])
    if quality["incomplete"]:
        quality["publicationEligible"] = False
        extraction["status"] = "review_required"
    quality["memoryStats"] = {
        "evidenceItemCount": len(memory.get("evidenceItems") or []),
        "claimCount": len(memory.get("claims") or []),
        "noteCount": sum(len(v.get("signals") or []) for v in (memory.get("observationNotes") or {}).values()),
        "runningSummaryChars": len(str(memory.get("runningSummary") or "")),
    }
    quality["attemptLog"] = attempt_log
    extraction["model"] = model_name
    extraction["provider"] = provider
    extraction["tokensUsed"] = {
        "promptTokens": sum(int(item.get("promptTokens") or 0) for item in attempt_log),
        "completionTokens": sum(int(item.get("completionTokens") or 0) for item in attempt_log),
        "totalTokens": sum(int(item.get("totalTokens") or 0) for item in attempt_log),
    }
    extraction["sessionMemory"] = {
        "version": _MEMORY_VERSION,
        "runningSummary": memory.get("runningSummary"),
        "windowIds": [w.get("windowId") for w in windows],
        "scanFailures": memory.get("scanFailures") or [],
    }
    return extraction


def build_report_memory_pack(
    *,
    rule_payload: dict,
    evidence_extraction: dict | None,
    asr_result: dict | None = None,
    max_evidence: int = 12,
    max_losses: int = 12,
) -> dict[str, Any]:
    """Compact pack for deep report generation — no full transcript dump."""
    extraction = evidence_extraction or {}
    losses = []
    for row in sorted(
        [
            row for row in list((rule_payload or {}).get("lossLedger") or [])
            if isinstance(row, dict) and float(row.get("points") or 0) > 0
        ],
        key=lambda row: -float(row.get("points") or 0),
    )[:max_losses]:
        losses.append({
            "observationCode": row.get("observationCode"),
            "observationName": row.get("observationName"),
            "dimensionCode": row.get("dimensionCode"),
            "lossType": row.get("lossType"),
            "points": row.get("points"),
            "reason": str(row.get("reason") or "")[:140],
        })
    evidence_items = []
    for item in list(extraction.get("evidenceItems") or [])[:max_evidence]:
        if not isinstance(item, dict):
            continue
        evidence_items.append({
            "evidenceId": item.get("evidenceId") or item.get("id"),
            "sourceRef": item.get("sourceRef"),
            "text": str(item.get("text") or "")[:120],
            "sourceType": item.get("sourceType"),
        })
    obs = []
    for row in list((rule_payload or {}).get("observations") or [])[:16]:
        if not isinstance(row, dict):
            continue
        obs.append({
            "observationCode": row.get("observationCode"),
            "observationName": row.get("observationName"),
            "finalScore": row.get("finalScore"),
            "maxScore": row.get("maxScore"),
            "evidenceLevel": row.get("evidenceLevel"),
            "performanceLevel": row.get("performanceLevel") or row.get("achievementLevel"),
            "performanceReason": str(row.get("performanceReason") or "")[:90],
            "evidenceReason": str(row.get("evidenceReason") or "")[:90],
        })
    session_memory = extraction.get("sessionMemory") or {}
    summary = session_memory.get("runningSummary") or _fallback_summary_from_asr(asr_result)
    return {
        "runningSummary": str(summary or "")[:700],
        "authoritativeScore": {
            "overallScore": rule_payload.get("finalScore"),
            "dimensionScores": rule_payload.get("dimensionScores") or {},
            "dimensionMaxScores": rule_payload.get("dimensionMaxScores") or {},
            "performanceGap": rule_payload.get("performanceGap"),
            "evidenceLimitedGap": rule_payload.get("evidenceLimitedGap"),
            "effectiveHardPenalty": rule_payload.get("effectiveHardPenalty"),
        },
        "topLosses": losses,
        "observations": obs,
        "evidenceItems": evidence_items,
        "windowIds": list(session_memory.get("windowIds") or [])[:12],
    }


def _new_memory(track_rule: dict[str, Any], windows: list[dict]) -> dict[str, Any]:
    notes = {}
    for item in track_rule.get("observations") or []:
        code = str(item.get("observationCode") or "").strip()
        if not code:
            continue
        notes[code] = {
            "observationCode": code,
            "observationName": item.get("observationName"),
            "signals": [],
            "bestEvidenceLevel": "E0",
            "bestPerformanceLevel": "not_demonstrated",
            "quotes": [],
        }
    return {
        "version": _MEMORY_VERSION,
        "runningSummary": "",
        "claims": [],
        "evidenceItems": [],
        "deductionCandidates": [],
        "recoveryCandidates": [],
        "riskFlags": [],
        "observationNotes": notes,
        "scanFailures": [],
        "processedWindows": [],
        "windowCount": len(windows),
    }


def _observation_catalog(track_rule: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = []
    for item in track_rule.get("observations") or []:
        if not isinstance(item, dict):
            continue
        catalog.append({
            "observationCode": item.get("observationCode"),
            "observationName": item.get("observationName"),
            "dimensionCode": item.get("dimensionCode"),
            "requiredInfo": list(item.get("requiredInfo") or [])[:3],
            "acceptableEvidence": list(item.get("acceptableEvidence") or [])[:3],
            "evidenceCaps": item.get("evidenceCaps"),
            "maxScore": item.get("maxScore"),
        })
    return catalog


def _build_time_windows(asr_result: dict, fusion_context: dict | None) -> list[dict[str, Any]]:
    segments = [seg for seg in (asr_result or {}).get("segments") or [] if isinstance(seg, dict) and str(seg.get("text") or "").strip()]
    duration = float((asr_result or {}).get("duration") or 0)
    if duration <= 0 and segments:
        duration = max(_seg_end(seg) for seg in segments)
    window_sec = float(getattr(settings, "LLM_EVIDENCE_MEMORY_WINDOW_SEC", 600) or 600)
    max_windows = int(getattr(settings, "LLM_EVIDENCE_MEMORY_MAX_WINDOWS", 8) or 8)
    if duration <= 0:
        duration = window_sec
    # Cap windows for cost/latency, keep even coverage.
    raw_count = max(1, int((duration + window_sec - 1) // window_sec))
    count = min(max_windows, raw_count)
    actual_window = duration / count if count else duration

    timeline = []
    for item in (fusion_context or {}).get("timeline") or []:
        if isinstance(item, dict):
            timeline.append(item)

    windows = []
    for index in range(count):
        start = index * actual_window
        end = (index + 1) * actual_window if index < count - 1 else duration
        segs = [
            seg for seg in segments
            if _seg_start(seg) < end and _seg_end(seg) >= start
        ]
        # Keep window text lean.
        text_lines = []
        char_budget = int(getattr(settings, "LLM_EVIDENCE_MEMORY_WINDOW_CHARS", 3500) or 3500)
        used = 0
        for seg in segs:
            line = f"[{_mmss(_seg_start(seg))}] {str(seg.get('text') or '').strip()}"
            if used + len(line) + 1 > char_budget:
                # keep tail of window too
                break
            text_lines.append(line)
            used += len(line) + 1
        if segs and len(text_lines) < len(segs):
            # append last few lines if budget remains
            for seg in segs[-3:]:
                line = f"[{_mmss(_seg_start(seg))}] {str(seg.get('text') or '').strip()}"
                if line not in text_lines:
                    text_lines.append(line)

        visual_bits = []
        for item in timeline:
            ts = _timeline_seconds(item)
            if start <= ts < end:
                bit = str(item.get("visual_impression") or item.get("text_preview") or "").strip()
                if bit:
                    visual_bits.append(f"[{_mmss(ts)}] {bit[:100]}")
            if len(visual_bits) >= 4:
                break

        windows.append({
            "windowId": f"W{index + 1}",
            "startSec": round(start, 1),
            "endSec": round(end, 1),
            "timeRange": f"{_mmss(start)}-{_mmss(end)}",
            "transcript": "\n".join(text_lines),
            "visualNotes": visual_bits,
            "segmentCount": len(segs),
        })
    return windows


def _scan_prompt(*, obs_catalog, window, memory, window_index, window_total) -> str:
    compact_obs = [
        {
            "observationCode": item["observationCode"],
            "observationName": item["observationName"],
            "requiredInfo": item.get("requiredInfo") or [],
        }
        for item in obs_catalog
    ]
    notes_digest = []
    for code, note in (memory.get("observationNotes") or {}).items():
        if note.get("signals") or note.get("quotes"):
            notes_digest.append({
                "observationCode": code,
                "bestEvidenceLevel": note.get("bestEvidenceLevel"),
                "bestPerformanceLevel": note.get("bestPerformanceLevel"),
                "signalCount": len(note.get("signals") or []),
                "latestSignal": (note.get("signals") or [""])[-1][:80],
            })
    return (
        f"当前时间窗 {window_index}/{window_total}: {window['timeRange']} ({window['windowId']})\n"
        "任务：只根据本窗内容更新记忆，不要重复全文。\n"
        "输出JSON字段：\n"
        "{\n"
        '  "windowSummary": "本窗1-2句摘要",\n'
        '  "claims": [{"claimId":"C..","text":"...","observationCodes":["O01"]}],\n'
        '  "evidenceItems": [{"evidenceId":"E..","sourceRef":"transcript@MM:SS|timeline@MM:SS","text":"原文或画面","sourceType":"transcript|timeline","confidence":0.0}],\n'
        '  "observationSignals": [{"observationCode":"O01","signal":"本窗看到了什么","suggestedEvidenceLevel":"E0-E5","suggestedPerformanceLevel":"not_demonstrated|partial|substantial|complete","quote":"短引用"}],\n'
        '  "riskFlags": [{"code":"...","message":"..."}],\n'
        '  "deductionCandidates": []\n'
        "}\n"
        "规则：\n"
        "1) sourceRef 必须能对应本窗时间；\n"
        "2) 没看到就不要硬写 substantial/complete；\n"
        "3) 有现场演示/数据/操作时要写进 observationSignals；\n"
        "4) 证据 text 尽量短，但可定位。\n\n"
        f"观测点目录：{json.dumps(compact_obs, ensure_ascii=False)}\n"
        f"已有记忆摘要：{memory.get('runningSummary') or '（空）'}\n"
        f"已有观测点摘要：{json.dumps(notes_digest[:20], ensure_ascii=False)}\n"
        f"本窗视觉笔记：{json.dumps(window.get('visualNotes') or [], ensure_ascii=False)}\n"
        f"本窗转写：\n{window.get('transcript') or '（本窗无有效转写）'}\n"
    )


def _synthesize_prompt(batch: list[dict], memory: dict, failed_windows: list | None = None) -> str:
    related_codes = {str(item.get("observationCode") or "") for item in batch}
    related_evidence = []
    for item in memory.get("evidenceItems") or []:
        # keep all evidence for small inventory; model will choose
        related_evidence.append({
            "evidenceId": item.get("evidenceId"),
            "sourceRef": item.get("sourceRef"),
            "text": str(item.get("text") or "")[:180],
            "sourceType": item.get("sourceType"),
        })
        if len(related_evidence) >= 40:
            break
    notes = {
        code: {
            "bestEvidenceLevel": note.get("bestEvidenceLevel"),
            "bestPerformanceLevel": note.get("bestPerformanceLevel"),
            "signals": (note.get("signals") or [])[-5:],
            "quotes": (note.get("quotes") or [])[-5:],
        }
        for code, note in (memory.get("observationNotes") or {}).items()
        if code in related_codes
    }
    return (
        "根据会话记忆，为本批观测点给出最终 observationEvidence。\n"
        "要求：\n"
        "1) 每个观测点必须输出 evidenceLevel、performanceLevel、performanceReason、evidenceReason、evidenceIds、confidence；\n"
        "2) performanceLevel 只看现场达成，不要因为缺第三方材料就判 not_demonstrated；\n"
        "3) 有转写/演示证据时至少 partial；完整演示链路可达 substantial；\n"
        "4) evidenceIds 只能使用记忆中的 evidenceId；\n"
        "5) 禁止输出总分。\n"
        "6) 失败窗里的时段没有扫描成功：禁止用邻窗推断那些时段的时间点或原文，不得编造 sourceRef。\n"
        "输出JSON：{\"observationEvidence\":[...],\"deductionCandidates\":[],\"riskFlags\":[]}\n\n"
        f"失败窗：{json.dumps(failed_windows or [], ensure_ascii=False)}\n"
        f"会话摘要：{memory.get('runningSummary') or ''}\n"
        f"本批观测点：{json.dumps(batch, ensure_ascii=False)}\n"
        f"相关记忆笔记：{json.dumps(notes, ensure_ascii=False)}\n"
        f"证据库存：{json.dumps(related_evidence, ensure_ascii=False)}\n"
    )


def _merge_scan_into_memory(memory: dict, payload: dict, window: dict) -> None:
    summary = str(payload.get("windowSummary") or "").strip()
    if summary:
        prev = str(memory.get("runningSummary") or "").strip()
        piece = f"[{window.get('timeRange')}] {summary}"
        memory["runningSummary"] = (prev + " " + piece).strip()[:1800]

    for item in payload.get("claims") or []:
        if isinstance(item, dict) and str(item.get("text") or "").strip():
            row = dict(item)
            row.setdefault("claimId", f"{window['windowId']}-C{len(memory['claims']) + 1}")
            memory["claims"].append(row)

    for item in payload.get("evidenceItems") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        row = dict(item)
        row.setdefault("evidenceId", f"{window['windowId']}-E{len(memory['evidenceItems']) + 1}")
        row["text"] = text[:240]
        row.setdefault("sourceRef", f"transcript@{_mmss(window.get('startSec') or 0)}")
        row.setdefault("sourceType", "transcript")
        row.setdefault("confidence", 0.7)
        memory["evidenceItems"].append(row)

    for item in payload.get("deductionCandidates") or []:
        if isinstance(item, dict):
            memory["deductionCandidates"].append(item)
    for item in payload.get("riskFlags") or []:
        if isinstance(item, dict):
            memory["riskFlags"].append(item)

    for signal in payload.get("observationSignals") or []:
        if not isinstance(signal, dict):
            continue
        code = str(signal.get("observationCode") or "").strip()
        note = (memory.get("observationNotes") or {}).get(code)
        if not note:
            continue
        text = str(signal.get("signal") or "").strip()
        if text:
            note["signals"].append(f"[{window.get('timeRange')}] {text[:120]}")
            note["signals"] = note["signals"][-8:]
        quote = str(signal.get("quote") or "").strip()
        if quote:
            note["quotes"].append(quote[:120])
            note["quotes"] = note["quotes"][-8:]
        note["bestEvidenceLevel"] = _max_level(
            note.get("bestEvidenceLevel"),
            signal.get("suggestedEvidenceLevel"),
        )
        note["bestPerformanceLevel"] = _max_perf(
            note.get("bestPerformanceLevel"),
            signal.get("suggestedPerformanceLevel"),
        )

    memory["processedWindows"].append(window.get("windowId"))


def _fallback_observation_from_memory(obs: dict, memory: dict) -> dict:
    code = str(obs.get("observationCode") or "")
    note = (memory.get("observationNotes") or {}).get(code) or {}
    evidence_ids = [
        str(item.get("evidenceId"))
        for item in memory.get("evidenceItems") or []
        if item.get("evidenceId")
    ][:3]
    level = note.get("bestEvidenceLevel") or ("E1" if evidence_ids else "E0")
    performance = note.get("bestPerformanceLevel") or ("partial" if evidence_ids else "not_demonstrated")
    reason = "；".join((note.get("signals") or [])[-2:]) or "本轮记忆中证据有限"
    return {
        "observationCode": code,
        "observationName": obs.get("observationName"),
        "evidenceLevel": level,
        "performanceLevel": performance,
        "performanceReason": reason,
        "evidenceReason": reason,
        "evidenceIds": evidence_ids if level != "E0" else [],
        "confidence": 0.55 if evidence_ids else 0.2,
        "supportSummary": reason,
    }


def _json_call(*, client, model_name, system, user, max_tokens, timeout, stage):
    from app.services.llm_scoring_service import chat_completion_kwargs

    meta = {
        "stage": stage,
        "attempt": 1,
        "max_tokens": max_tokens,
        "promptTokens": 0,
        "completionTokens": 0,
        "totalTokens": 0,
        "responseChars": 0,
        "truncated": False,
        "error": None,
    }
    try:
        response = client.chat.completions.create(
            **chat_completion_kwargs(
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
        )
        choice = response.choices[0]
        content = getattr(choice.message, "content", "") or ""
        usage = getattr(response, "usage", None)
        meta["finish_reason"] = getattr(choice, "finish_reason", None)
        meta["promptTokens"] = int(getattr(usage, "prompt_tokens", 0) or 0)
        meta["completionTokens"] = int(getattr(usage, "completion_tokens", 0) or 0)
        meta["totalTokens"] = int(getattr(usage, "total_tokens", 0) or 0)
        meta["responseChars"] = len(content)
        if str(meta["finish_reason"] or "") == "length":
            meta["truncated"] = True
        if not content:
            meta["error"] = "empty_content"
            return None, meta
        # strip fences if any
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            meta["error"] = "not_object"
            return None, meta
        return payload, meta
    except Exception as exc:
        meta["error"] = str(exc) or exc.__class__.__name__
        logger.warning("memory session call failed stage=%s err=%s", stage, meta["error"])
        return None, meta


def _should_retry_scan(meta: dict | None) -> bool:
    if not isinstance(meta, dict):
        return False
    if meta.get("truncated") or str(meta.get("finish_reason") or "") == "length":
        return True
    error = str(meta.get("error") or "")
    needles = (
        "unterminated",
        "expecting",
        "delimiter",
        "json",
        "empty_content",
        "not_object",
    )
    lowered = error.lower()
    return any(item in lowered for item in needles)


def _json_call_with_retry(
    *,
    client,
    model_name,
    system,
    user,
    max_tokens,
    retry_tokens,
    timeout,
    stage,
) -> tuple[dict | None, list[dict]]:
    payload, meta = _json_call(
        client=client,
        model_name=model_name,
        system=system,
        user=user,
        max_tokens=max_tokens,
        timeout=timeout,
        stage=stage,
    )
    metas = [meta]
    if payload is not None or not _should_retry_scan(meta):
        return payload, metas
    retry_payload, retry_meta = _json_call(
        client=client,
        model_name=model_name,
        system=system,
        user=user,
        max_tokens=max(int(retry_tokens or 0), int(max_tokens or 0) + 1),
        timeout=timeout,
        stage=stage,
    )
    retry_meta["attempt"] = 2
    metas.append(retry_meta)
    return retry_payload, metas


def _fallback_summary_from_asr(asr_result: dict | None) -> str:
    segs = [s for s in (asr_result or {}).get("segments") or [] if isinstance(s, dict) and s.get("text")]
    if not segs:
        return str((asr_result or {}).get("transcript") or "")[:500]
    head = str(segs[0].get("text") or "")[:80]
    tail = str(segs[-1].get("text") or "")[:80]
    mid = str(segs[len(segs)//2].get("text") or "")[:80]
    return f"开场：{head}；中段：{mid}；结尾：{tail}"


def _seg_start(seg: dict) -> float:
    if seg.get("startMs") is not None:
        try:
            return max(0.0, float(seg["startMs"]) / 1000.0)
        except (TypeError, ValueError):
            pass
    try:
        return max(0.0, float(seg.get("start") or 0))
    except (TypeError, ValueError):
        return 0.0


def _seg_end(seg: dict) -> float:
    if seg.get("endMs") is not None:
        try:
            return max(_seg_start(seg), float(seg["endMs"]) / 1000.0)
        except (TypeError, ValueError):
            pass
    try:
        return max(_seg_start(seg), float(seg.get("end") or 0))
    except (TypeError, ValueError):
        return _seg_start(seg)


def _timeline_seconds(item: dict) -> float:
    for key in ("time_sec", "time_seconds", "timestamp", "start"):
        if item.get(key) is not None:
            try:
                return float(item[key])
            except (TypeError, ValueError):
                pass
    try:
        return float(item.get("time_min") or 0) * 60.0
    except (TypeError, ValueError):
        return 0.0


def _mmss(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0))))
    return f"{total // 60:02d}:{total % 60:02d}"


def _max_level(current, candidate) -> str:
    cur = str(current or "E0").upper()
    cand = str(candidate or "E0").upper()
    if _LEVEL_ORDER.get(cand, 0) > _LEVEL_ORDER.get(cur, 0):
        return cand
    return cur if cur in _LEVEL_ORDER else "E0"


def _max_perf(current, candidate) -> str:
    cur = str(current or "not_demonstrated").lower()
    cand = str(candidate or "not_demonstrated").lower()
    if _PERF_ORDER.get(cand, 0) > _PERF_ORDER.get(cur, 0):
        return cand
    return cur if cur in _PERF_ORDER else "not_demonstrated"
