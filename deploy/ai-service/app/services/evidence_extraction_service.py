"""LLM evidence extraction helpers for pilot track-rule scoring.

This module keeps LLM output on the evidence side of the boundary. It parses
claims, evidence anchors, observation evidence, deductions, recoveries, and
risk flags, but deliberately drops any model-provided final scores.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

REQUIRED_TOP_LEVEL_KEYS = (
    "claims",
    "evidenceItems",
    "observationEvidence",
    "deductionCandidates",
    "recoveryCandidates",
    "riskFlags",
    "extractionQuality",
)
EVIDENCE_LEVEL_ORDER = ("E0", "E1", "E2", "E3", "E4", "E5")
EVIDENCE_LEVELS = set(EVIDENCE_LEVEL_ORDER)
ACHIEVEMENT_RATIOS = {
    "not_demonstrated": 0.0,
    "partial": 0.5,
    "substantial": 0.8,
    "complete": 1.0,
}
PERFORMANCE_RATIOS = ACHIEVEMENT_RATIOS
DEFAULT_CONFIDENCE_BY_EVIDENCE_LEVEL = {
    "E0": 0.0,
    "E1": 0.35,
    "E2": 0.55,
    "E3": 0.7,
    "E4": 0.85,
    "E5": 0.95,
}
PILOT_RULE_FILES = {
    "42": "track_42_ai_v1_2_engine_pilot.json",
    "track_42": "track_42_ai_v1_2_engine_pilot.json",
    "track_42_ai": "track_42_ai_v1_2_engine_pilot.json",
    "人工智能赛道": "track_42_ai_v1_2_engine_pilot.json",
    "27": "track_27_it_v1_2_engine_pilot.json",
    "track_27": "track_27_it_v1_2_engine_pilot.json",
    "track_27_it": "track_27_it_v1_2_engine_pilot.json",
    "新一代信息技术赛道": "track_27_it_v1_2_engine_pilot.json",
}
_RULE_FILE_INDEX: dict[str, str] | None = None


def rubrics_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "rubrics"


def load_pilot_track_rule(track: str | None) -> dict[str, Any]:
    key = (track or "").strip()
    file_name = _rule_file_index().get(key)
    if not file_name:
        normalized = key.lower()
        if "人工智能" in key or normalized in {"ai", "track-ai", "track_42"}:
            file_name = PILOT_RULE_FILES["人工智能赛道"]
        elif "新一代信息技术" in key or normalized in {"it", "track-it", "track_27"}:
            file_name = PILOT_RULE_FILES["新一代信息技术赛道"]
        elif normalized.startswith("track_"):
            file_name = _rule_file_index().get(normalized.removeprefix("track_"))
    if not file_name:
        raise ValueError(f"unsupported pilot track: {track}")

    path = rubrics_dir() / file_name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _rule_file_index() -> dict[str, str]:
    global _RULE_FILE_INDEX
    if _RULE_FILE_INDEX is not None:
        return _RULE_FILE_INDEX
    index = dict(PILOT_RULE_FILES)
    plan_path = rubrics_dir() / "track_expansion_plan_v1.json"
    try:
        with plan_path.open(encoding="utf-8") as f:
            plan = json.load(f)
        for batch in plan.get("batches") or []:
            for track in batch.get("tracks") or []:
                if not isinstance(track, dict):
                    continue
                if track.get("status") not in {"pilot_completed", "pilot_generated"}:
                    continue
                rule_file = track.get("structuredRuleFile")
                if not rule_file:
                    continue
                file_name = Path(rule_file).name
                track_id = str(track.get("trackId") or "").strip()
                track_name = str(track.get("trackName") or "").strip()
                if track_id:
                    index[track_id] = file_name
                    index[f"track_{track_id}"] = file_name
                if track_name:
                    index[track_name] = file_name
    except Exception as exc:
        logger.warning("扩展赛道规则索引加载失败，仅使用首批试点规则: %s", exc)
    _RULE_FILE_INDEX = index
    return index


def extract_evidence_from_llm_payload(content: str, track_rule: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = _parse_json_object(content)
    except Exception as exc:
        return _failed_extraction(track_rule, str(exc))

    normalized = {
        "status": "completed",
        "trackId": track_rule.get("trackId"),
        "trackName": track_rule.get("trackName"),
        "ruleVersion": track_rule.get("ruleVersion"),
        "ruleHash": track_rule.get("ruleHash"),
        "claims": _list_of_dicts(payload.get("claims")),
        "evidenceItems": _normalize_evidence_items(payload.get("evidenceItems")),
        "observationEvidence": [],
        "deductionCandidates": _normalize_candidates(payload.get("deductionCandidates")),
        "recoveryCandidates": _normalize_candidates(payload.get("recoveryCandidates")),
        "riskFlags": _normalize_candidates(payload.get("riskFlags")),
        "extractionQuality": _normalize_quality(payload.get("extractionQuality")),
    }
    evidence_ids = {
        str(item.get("evidenceId"))
        for item in normalized["evidenceItems"]
        if item.get("evidenceId") is not None and _has_evidence_payload(item)
    }
    evidence_items_by_id = {
        str(item.get("evidenceId")): item
        for item in normalized["evidenceItems"]
        if item.get("evidenceId") is not None
    }
    model_observations = _observation_items(payload.get("observationEvidence"))
    observed_by_code = {
        _normalize_observation_code(item.get("observationCode")): item
        for item in model_observations
        if _normalize_observation_code(item.get("observationCode"))
    }

    warnings = []
    for observation in track_rule.get("observations") or []:
        item, item_warnings = _normalize_observation_evidence(
            observation,
            observed_by_code.get(_normalize_observation_code(observation.get("observationCode"))),
            evidence_ids,
            evidence_items_by_id,
        )
        warnings.extend(item_warnings)
        normalized["observationEvidence"].append(item)

    for key in ("deductionCandidates", "recoveryCandidates", "riskFlags"):
        for item in normalized[key]:
            item.setdefault("sourceType", "llm_extraction")

    if normalized["evidenceItems"] and not any(
        item.get("evidenceIds")
        for item in normalized["observationEvidence"]
    ):
        warnings.append("evidence_inventory_unbound")

    normalized["extractionQuality"]["jsonParseable"] = True
    normalized["extractionQuality"]["observationCount"] = len(normalized["observationEvidence"])
    normalized["extractionQuality"]["modelObservationCount"] = len(model_observations)
    normalized["extractionQuality"]["matchedObservationCount"] = len(observed_by_code)
    has_blocking_contract_warning = any(
        warning == "evidence_inventory_unbound"
        or warning.endswith(":E0_with_bound_evidence")
        for warning in warnings
    )
    normalized["extractionQuality"]["publicationEligible"] = bool(
        normalized["observationEvidence"]
        and len(observed_by_code) == len(normalized["observationEvidence"])
        and not has_blocking_contract_warning
    )
    normalized["extractionQuality"]["warnings"] = warnings
    if not normalized["extractionQuality"]["publicationEligible"]:
        normalized["status"] = "review_required"
    elif warnings or _has_missing_observations(normalized["observationEvidence"]):
        normalized["status"] = "completed_with_warnings"

    return normalized


def build_empty_evidence_extraction(track_rule: dict[str, Any], reason: str = "not_extracted") -> dict[str, Any]:
    extraction = {
        "claims": [],
        "evidenceItems": [],
        "observationEvidence": [],
        "deductionCandidates": [],
        "recoveryCandidates": [],
        "riskFlags": [{"code": reason, "message": "证据抽取未生成，所有观测点按E0处理。", "sourceType": "system"}],
        "extractionQuality": {"jsonParseable": True, "fallback": True, "reason": reason},
    }
    return extract_evidence_from_llm_payload(json.dumps(extraction, ensure_ascii=False), track_rule)


def build_transcript_coverage(
    asr_result: dict | None,
    *,
    max_total_chars: int | None = None,
    max_part_chars: int | None = None,
    max_parts: int | None = None,
) -> dict[str, Any]:
    """Pack the full roadshow transcript for evidence extraction.

    Never keeps only the head of a long transcript. When the text exceeds the
    budget, content is packed into chronological time-bucket parts so opening,
    middle, and closing speech all remain visible to the model.
    """
    total_budget = max(
        1000,
        int(
            max_total_chars
            if max_total_chars is not None
            else getattr(settings, "LLM_EVIDENCE_TRANSCRIPT_MAX_CHARS", 48000)
        ),
    )
    part_budget = max(
        500,
        int(
            max_part_chars
            if max_part_chars is not None
            else getattr(settings, "LLM_EVIDENCE_TRANSCRIPT_PART_CHARS", 10000)
        ),
    )
    part_limit = max(
        1,
        int(
            max_parts
            if max_parts is not None
            else getattr(settings, "LLM_EVIDENCE_TRANSCRIPT_MAX_PARTS", 8)
        ),
    )

    lines = _timestamped_transcript_lines(asr_result)
    if not lines:
        raw = str((asr_result or {}).get("transcript") or "").strip()
        if not raw:
            return {
                "text": "",
                "parts": [],
                "totalChars": 0,
                "coverageMode": "empty",
                "truncated": False,
            }
        if len(raw) <= total_budget:
            return {
                "text": raw,
                "parts": [{"index": 1, "timeRange": "full", "text": raw, "chars": len(raw)}],
                "totalChars": len(raw),
                "coverageMode": "full_plain",
                "truncated": False,
            }
        # Plain text without timestamps: equal sequential chunks (still covers the tail).
        chunks = _chunk_plain_text(raw, min(part_budget, total_budget // max(1, part_limit)), part_limit)
        parts = [
            {"index": i + 1, "timeRange": f"chunk-{i + 1}", "text": chunk, "chars": len(chunk)}
            for i, chunk in enumerate(chunks)
        ]
        text = _format_transcript_parts(parts)
        return {
            "text": text,
            "parts": parts,
            "totalChars": len(text),
            "coverageMode": "plain_chunks",
            "truncated": len(raw) > sum(part["chars"] for part in parts),
        }

    full_text = "\n".join(lines)
    if len(full_text) <= total_budget:
        return {
            "text": full_text,
            "parts": [{"index": 1, "timeRange": "full", "text": full_text, "chars": len(full_text)}],
            "totalChars": len(full_text),
            "coverageMode": "full_timestamped",
            "truncated": False,
        }

    parts = _pack_timestamped_lines_into_parts(
        lines,
        total_budget=total_budget,
        part_budget=part_budget,
        max_parts=part_limit,
    )
    text = _format_transcript_parts(parts)
    return {
        "text": text,
        "parts": parts,
        "totalChars": len(text),
        "coverageMode": "time_bucket_parts",
        "truncated": False,
        "partCount": len(parts),
    }


def build_extraction_prompt(
    track_rule: dict[str, Any],
    asr_result: dict,
    fusion_context: dict | None = None,
    scoring_context: dict | None = None,
) -> str:
    observations = [
        {
            "observationCode": item.get("observationCode"),
            "observationName": item.get("observationName"),
            "requiredInfo": item.get("requiredInfo"),
            "acceptableEvidence": item.get("acceptableEvidence"),
            "evidenceCaps": item.get("evidenceCaps"),
        }
        for item in track_rule.get("observations", [])
    ]
    # Keep prompt lean enough for stable API connectivity on long roadshows.
    coverage = build_transcript_coverage(
        asr_result,
        max_total_chars=int(getattr(settings, "LLM_EVIDENCE_PROMPT_TRANSCRIPT_CHARS", 10000) or 10000),
        max_part_chars=int(getattr(settings, "LLM_EVIDENCE_TRANSCRIPT_PART_CHARS", 3500) or 3500),
        max_parts=int(getattr(settings, "LLM_EVIDENCE_TRANSCRIPT_MAX_PARTS", 4) or 4),
    )
    transcript = coverage.get("text") or ""
    fusion_summary = _compact_fusion_summary((fusion_context or {}).get("screen_content_summary") or {})
    fusion_timeline = _compact_fusion_timeline(
        (fusion_context or {}).get("timeline") or [],
        limit=int(getattr(settings, "LLM_EVIDENCE_FUSION_TIMELINE_LIMIT", 16) or 16),
    )
    evidence_location_hints = _core_evidence_location_hints(track_rule, scoring_context or {})[:12]
    coverage_note = ""
    if (coverage.get("partCount") or len(coverage.get("parts") or [])) > 1:
        coverage_note = (
            f"转写已按时间完整覆盖拆成 {coverage.get('partCount') or len(coverage.get('parts') or [])} 段"
            f"（模式={coverage.get('coverageMode')}）。必须综合开场、中段与结尾，禁止只依据第一段判断。\n"
        )
    # Observation schema is the largest fixed block; keep only scoring-critical fields.
    lean_observations = [
        {
            "observationCode": item.get("observationCode"),
            "observationName": item.get("observationName"),
            "requiredInfo": (item.get("requiredInfo") or [])[:4],
            "acceptableEvidence": (item.get("acceptableEvidence") or [])[:4],
            "evidenceCaps": item.get("evidenceCaps"),
        }
        for item in observations
    ]
    return (
        "你是OREP证据抽取器，不是评分员。只输出JSON，不输出最终总分、维度分或观测点正式分。\n"
        "必须输出claims、evidenceItems、observationEvidence、deductionCandidates、"
        "recoveryCandidates、riskFlags、extractionQuality。\n"
        "每个观测点必须有evidenceLevel；无证据必须显式E0；非E0必须绑定evidenceIds；"
        "E0不得绑定evidenceIds，已有相关证据时必须按证据强度选择E1-E5。\n"
        "每个观测点必须输出performanceLevel：not_demonstrated、partial、substantial、complete，"
        "并输出performanceReason；兼容旧字段时可同时输出achievementLevel和achievementReason。"
        "performanceLevel只描述当前视频可观察到的操作、结果、完整度和熟练度，evidenceLevel描述证据有多可信。"
        "达成程度与证据强度必须分开判断。"
        "performanceReason 禁止使用缺少第三方证明、书面材料、订单附件、后台截图或外部验收等证据缺失理由。\n"
        "evidenceItems 必须填写 sourceRef 和 text，并填写 sourceType 和 confidence（0到1）；"
        "生成evidenceItems后，至少一条相关证据必须绑定到observationEvidence.evidenceIds；"
        "禁止生成证据库存却让全部观测点保持空绑定。"
        "sourceRef 优先使用 timeline@MM:SS 或 transcript@MM:SS。\n"
        "observationEvidence 必须输出 confidence（0到1）；它表示对当前证据归纳的把握度，不参与成就程度判断。\n"
        "E4必须有场景验证证据，E5必须有独立可核验证据，否则降级。\n"
        "E3必须有内部量化证据，例如内部测试、成本测算、性能指标、样本数据、订单/交易/流水、转化率或运营复盘；"
        "如果只有流程、方法、口头解释或价值判断但缺少量化材料，必须降为E2。\n"
        "证据不足不得进入 deductionCandidates，只能降低evidenceLevel并写入evidenceReason。"
        "deductionCandidates只允许赛事明文规定的独立hard_violation；必须同时输出penaltyType=hard_violation、"
        "penaltyRuleCode、triggerFact、evidenceIds和deductedPoints，没有把握时不要输出。\n"
        f"赛道规则：{json.dumps(lean_observations, ensure_ascii=False)}\n"
        f"{coverage_note}"
        f"转写：{transcript}\n"
        f"融合摘要：{json.dumps(fusion_summary, ensure_ascii=False)}\n"
        f"融合时间线证据：{json.dumps(fusion_timeline, ensure_ascii=False)}\n"
        "候选证据定位线索：以下内容只用于定位可能的原文或画面，不包含可采信分数；"
        "必须回到转写或timeline核验后，才能生成evidenceItems并绑定观测点。"
        f"{json.dumps(evidence_location_hints, ensure_ascii=False)}"
    )


def _compact_fusion_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    texts = summary.get("visible_texts") or summary.get("visibleTexts") or []
    if isinstance(texts, list):
        texts = [str(item)[:60] for item in texts[:12] if str(item).strip()]
    return {
        key: value
        for key, value in {
            "visible_texts": texts,
            "screen_type": summary.get("screen_type") or summary.get("screenType"),
            "summary": str(summary.get("summary") or "")[:200],
        }.items()
        if value
    }


def _timestamped_transcript_lines(asr_result: dict | None) -> list[str]:
    segments = (asr_result or {}).get("segments") or []
    lines: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start_sec = _segment_start_seconds(segment)
        stamp = _format_mmss(start_sec)
        speaker = str(
            segment.get("displaySpeaker")
            or segment.get("speaker")
            or segment.get("rawSpeakerId")
            or ""
        ).strip()
        prefix = f"[{stamp}]"
        if speaker:
            prefix = f"[{stamp} {speaker}]"
        lines.append(f"{prefix} {text}")
    return lines


def _segment_start_seconds(segment: dict) -> float:
    if segment.get("startMs") is not None:
        try:
            return max(0.0, float(segment["startMs"]) / 1000.0)
        except (TypeError, ValueError):
            pass
    try:
        return max(0.0, float(segment.get("start") or 0))
    except (TypeError, ValueError):
        return 0.0


def _format_mmss(seconds: float) -> str:
    total = max(0, int(round(float(seconds or 0))))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_transcript_parts(parts: list[dict[str, Any]]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return str(parts[0].get("text") or "")
    blocks = []
    total = len(parts)
    for part in parts:
        index = part.get("index") or 0
        time_range = part.get("timeRange") or f"part-{index}"
        body = str(part.get("text") or "").strip()
        blocks.append(f"[转写分段 {index}/{total} {time_range}]\n{body}")
    return "\n\n".join(blocks)


def _chunk_plain_text(text: str, chunk_size: int, max_chunks: int) -> list[str]:
    size = max(500, int(chunk_size))
    limit = max(1, int(max_chunks))
    if len(text) <= size:
        return [text]
    # Equal-span chunks across the whole string so the tail is never dropped.
    span = max(size, int((len(text) + limit - 1) / limit))
    chunks = []
    for index in range(limit):
        start = index * span
        if start >= len(text):
            break
        end = min(len(text), start + span)
        chunks.append(text[start:end])
        if end >= len(text):
            break
    return chunks or [text[:size]]


def _pack_timestamped_lines_into_parts(
    lines: list[str],
    *,
    total_budget: int,
    part_budget: int,
    max_parts: int,
) -> list[dict[str, Any]]:
    """Split timestamped lines into chronological parts without dropping the tail."""
    if not lines:
        return []
    # First try sequential packing by part budget, then merge if too many parts.
    raw_parts: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + (1 if current else 0)
        if current and current_len + line_len > part_budget:
            raw_parts.append(current)
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += line_len
    if current:
        raw_parts.append(current)

    if len(raw_parts) > max_parts:
        # Merge adjacent parts evenly so max_parts still covers start→end.
        merged: list[list[str]] = []
        group_size = int((len(raw_parts) + max_parts - 1) / max_parts)
        for index in range(0, len(raw_parts), group_size):
            group = []
            for block in raw_parts[index:index + group_size]:
                group.extend(block)
            merged.append(group)
        raw_parts = merged[:max_parts]

    # Fit into total budget while keeping every part represented.
    per_part_budget = max(300, total_budget // max(1, len(raw_parts)))
    parts: list[dict[str, Any]] = []
    for index, block in enumerate(raw_parts, start=1):
        text = _fit_lines_to_budget(block, per_part_budget)
        time_range = _time_range_from_lines(block)
        parts.append({
            "index": index,
            "timeRange": time_range,
            "text": text,
            "chars": len(text),
        })
    return parts


def _fit_lines_to_budget(lines: list[str], budget: int) -> str:
    if not lines:
        return ""
    full = "\n".join(lines)
    if len(full) <= budget:
        return full
    # Keep head and tail of the bucket so both ends of the time range survive.
    if len(lines) == 1:
        return full[:budget]
    head: list[str] = []
    tail: list[str] = []
    used = 0
    left = 0
    right = len(lines) - 1
    take_head = True
    while left <= right:
        candidate = lines[left] if take_head else lines[right]
        extra = len(candidate) + (1 if (head or tail) else 0)
        if used + extra > budget:
            break
        if take_head:
            head.append(candidate)
            left += 1
        else:
            tail.insert(0, candidate)
            right -= 1
        used += extra
        take_head = not take_head
    kept = head + tail
    if not kept:
        return full[:budget]
    marker = "\n…\n" if left <= right else "\n"
    if head and tail and left <= right:
        return "\n".join(head) + marker + "\n".join(tail)
    return "\n".join(kept)


def _time_range_from_lines(lines: list[str]) -> str:
    stamps = []
    for line in lines:
        match = re.match(r"\[(\d{1,2}:\d{2}(?::\d{2})?)", str(line))
        if match:
            stamps.append(match.group(1))
    if not stamps:
        return "segment"
    if len(stamps) == 1:
        return stamps[0]
    return f"{stamps[0]}-{stamps[-1]}"


def extract_evidence(
    asr_result: dict,
    project_info: dict,
    fusion_context: dict | None = None,
    provider: str = "deepseek",
    scoring_context: dict | None = None,
) -> dict[str, Any]:
    track_rule = load_pilot_track_rule((project_info or {}).get("track"))
    transcript_coverage = build_transcript_coverage(asr_result)
    try:
        from app.services.llm_scoring_service import MODEL_MAP, get_client

        client = get_client(provider)
        model_name = MODEL_MAP.get(provider, settings.DEEPSEEK_MODEL or "deepseek-v4-pro")

        # Long roadshows: CLI-like session memory (window scan -> cumulative facts -> synthesize).
        if bool(getattr(settings, "LLM_EVIDENCE_MEMORY_SESSION_ENABLED", True)):
            from app.services.scoring.evidence_memory_session import (
                extract_with_memory_session,
                should_use_memory_session,
            )

            if should_use_memory_session(asr_result):
                logger.info(
                    "使用会话记忆式证据抽取: duration=%s segments=%s",
                    (asr_result or {}).get("duration"),
                    len((asr_result or {}).get("segments") or []),
                )
                extraction = extract_with_memory_session(
                    client=client,
                    model_name=model_name,
                    track_rule=track_rule,
                    asr_result=asr_result,
                    fusion_context=fusion_context,
                    scoring_context=scoring_context,
                    provider=provider,
                )
                _attach_transcript_coverage(
                    extraction.setdefault("extractionQuality", {}),
                    transcript_coverage,
                )
                return extraction

        prompt = build_extraction_prompt(track_rule, asr_result, fusion_context, scoring_context)
        model_max_tokens = max(
            4000,
            int(getattr(settings, "LLM_EVIDENCE_MODEL_MAX_OUTPUT_TOKENS", 384000) or 384000),
        )
        base_max_tokens = min(
            model_max_tokens,
            max(2000, int(getattr(settings, "LLM_EVIDENCE_MAX_TOKENS", 12000) or 12000)),
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是OREP证据抽取器。你只能抽取证据、证据等级、扣分候选、追回候选和风险。"
                    "禁止输出最终总分、维度分或正式观测点分。"
                    "必须输出完整可解析 JSON object，不要截断，不要输出 markdown 代码块。"
                ),
            },
            {"role": "user", "content": prompt},
        ]
        attempt_log: list[dict[str, Any]] = []
        single_shot_error = None
        # Large prompts are more reliable in observation batches than one giant request.
        force_batches = len(prompt) >= int(
            getattr(settings, "LLM_EVIDENCE_FORCE_BATCH_PROMPT_CHARS", 18000) or 18000
        )
        parse_failed = force_batches
        truncated = False
        extraction = None
        quality = {}
        if force_batches:
            attempt_log.append({
                "attempt": 0,
                "finish_reason": None,
                "max_tokens": base_max_tokens,
                "promptTokens": 0,
                "completionTokens": 0,
                "totalTokens": 0,
                "responseChars": 0,
                "truncated": False,
                "error": f"force_observation_batches:prompt_chars={len(prompt)}",
            })
            single_shot_error = f"force_observation_batches:prompt_chars={len(prompt)}"
        else:
            try:
                from app.services.llm_scoring_service import chat_completion_kwargs

                response = client.chat.completions.create(
                    **chat_completion_kwargs(
                        model=model_name,
                        messages=messages,
                        temperature=0.0,
                        max_tokens=base_max_tokens,
                        response_format={"type": "json_object"},
                        timeout=float(getattr(settings, "LLM_EVIDENCE_REQUEST_TIMEOUT_SECONDS", 180) or 180),
                    )
                )
                content, attempt_meta = _response_content_and_meta(response, base_max_tokens, attempt=1)
                attempt_log.append(attempt_meta)
                truncated = bool(attempt_meta["truncated"])
                extraction = None if truncated else extract_evidence_from_llm_payload(content, track_rule)
                quality = extraction.get("extractionQuality") if extraction else {}
                parse_failed = (
                    extraction is None
                    or extraction.get("status") == "failed"
                    or quality.get("jsonParseable") is False
                    or not content
                )
                if not content and not truncated:
                    single_shot_error = "empty_model_content"
                    parse_failed = True
            except Exception as exc:
                single_shot_error = str(exc) or exc.__class__.__name__
                attempt_meta = {
                    "attempt": 1,
                    "finish_reason": None,
                    "max_tokens": base_max_tokens,
                    "promptTokens": 0,
                    "completionTokens": 0,
                    "totalTokens": 0,
                    "responseChars": 0,
                    "truncated": False,
                    "error": f"single_shot_request_failed:{single_shot_error}",
                }
                attempt_log.append(attempt_meta)
                truncated = False
                extraction = None
                quality = {}
                parse_failed = True

        if parse_failed:
            reason = (
                f"single_shot_request_failed:{single_shot_error}"
                if single_shot_error
                else "response_truncated"
                if truncated
                else str(quality.get("error") or "json_parse_failed")
            )
            last_attempt = attempt_log[-1] if attempt_log else {
                "attempt": 1,
                "completionTokens": 0,
                "max_tokens": base_max_tokens,
            }
            last_attempt["error"] = reason
            logger.warning(
                "LLM证据抽取单次输出失败，切换观测点分批策略: reason=%s completion_tokens=%s max_tokens=%s",
                reason,
                last_attempt.get("completionTokens") or last_attempt.get("completion_tokens") or 0,
                base_max_tokens,
            )
            extraction = _extract_evidence_in_observation_batches(
                client=client,
                model_name=model_name,
                track_rule=track_rule,
                asr_result=asr_result,
                fusion_context=fusion_context,
                scoring_context=scoring_context,
                attempt_log=attempt_log,
            )
            batch_quality = extraction.setdefault("extractionQuality", {})
            batch_quality["retryCount"] = max(1, int(batch_quality.get("retryCount") or 0))
            batch_quality["fallbackReason"] = reason
        else:
            quality["strategy"] = "single_shot"

        extraction["model"] = model_name
        extraction["provider"] = provider
        extraction["tokensUsed"] = _summed_token_usage(attempt_log)
        quality_out = extraction.setdefault("extractionQuality", {})
        quality_out["attemptLog"] = list(attempt_log)
        _attach_transcript_coverage(quality_out, transcript_coverage)
        return extraction
    except Exception as exc:
        logger.warning("LLM证据抽取失败，进入失败态: %s", exc)
        failed = _failed_extraction(track_rule, str(exc))
        _attach_transcript_coverage(failed.setdefault("extractionQuality", {}), transcript_coverage)
        return failed


def _attach_transcript_coverage(quality: dict[str, Any], coverage: dict[str, Any] | None) -> None:
    if not isinstance(quality, dict) or not isinstance(coverage, dict):
        return
    quality["transcriptCoverage"] = {
        "coverageMode": coverage.get("coverageMode"),
        "totalChars": coverage.get("totalChars"),
        "partCount": coverage.get("partCount") or len(coverage.get("parts") or []),
        "truncated": bool(coverage.get("truncated")),
        "parts": [
            {
                "index": part.get("index"),
                "timeRange": part.get("timeRange"),
                "chars": part.get("chars"),
            }
            for part in (coverage.get("parts") or [])
            if isinstance(part, dict)
        ],
    }


def _extract_evidence_in_observation_batches(
    *,
    client,
    model_name: str,
    track_rule: dict[str, Any],
    asr_result: dict,
    fusion_context: dict | None,
    scoring_context: dict | None,
    attempt_log: list[dict[str, Any]],
) -> dict[str, Any]:
    observations = list(track_rule.get("observations") or [])
    batch_size = max(3, int(getattr(settings, "LLM_EVIDENCE_BATCH_SIZE", 5) or 5))
    model_max_tokens = max(
        4000,
        int(getattr(settings, "LLM_EVIDENCE_MODEL_MAX_OUTPUT_TOKENS", 384000) or 384000),
    )
    batch_max_tokens = min(
        model_max_tokens,
        max(1500, int(getattr(settings, "LLM_EVIDENCE_BATCH_MAX_TOKENS", 6000) or 6000)),
    )
    merged = {
        "claims": [],
        "evidenceItems": [],
        "observationEvidence": [],
        "deductionCandidates": [],
        "recoveryCandidates": [],
        "riskFlags": [],
        "extractionQuality": {"jsonParseable": True},
    }

    for batch_index, start in enumerate(range(0, len(observations), batch_size), start=1):
        batch_observations = observations[start:start + batch_size]
        batch_codes = [str(item.get("observationCode") or "") for item in batch_observations]
        batch_rule = {**track_rule, "observations": batch_observations}
        prompt = build_extraction_prompt(batch_rule, asr_result, fusion_context, scoring_context)
        batch_instruction = (
            f"\n分批范围：本次只处理以下观测点，不得输出其他观测点。\n"
            f"分批观测点：{','.join(batch_codes)}\n"
            "仍必须输出完整顶层 JSON object；各数组只包含本批内容。"
        )
        batch_payload = None
        last_error = "batch_generation_failed"
        for batch_attempt in range(1, 3):
            from app.services.llm_scoring_service import chat_completion_kwargs

            response = client.chat.completions.create(
                **chat_completion_kwargs(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是OREP证据抽取器。只输出完整 JSON object。"
                                "只处理指定观测点，不输出总分或观测点正式分。"
                            ),
                        },
                        {"role": "user", "content": prompt + batch_instruction},
                    ],
                    temperature=0.0,
                    max_tokens=batch_max_tokens,
                    response_format={"type": "json_object"},
                    timeout=float(getattr(settings, "LLM_EVIDENCE_REQUEST_TIMEOUT_SECONDS", 180) or 180),
                )
            )
            content, meta = _response_content_and_meta(
                response,
                batch_max_tokens,
                attempt=len(attempt_log) + 1,
            )
            meta["strategy"] = "observation_batch"
            meta["batch"] = batch_index
            meta["batchAttempt"] = batch_attempt
            meta["observationCodes"] = batch_codes
            attempt_log.append(meta)
            if meta["truncated"]:
                last_error = "batch_response_truncated"
                meta["error"] = last_error
                continue
            try:
                batch_payload = _parse_json_object(content)
            except Exception as exc:
                last_error = str(exc) or "batch_json_parse_failed"
                meta["error"] = last_error
                continue
            break

        if batch_payload is None:
            failed = _failed_extraction(track_rule, f"batch_{batch_index}_failed:{last_error}")
            failed["extractionQuality"]["strategy"] = "observation_batches"
            failed["extractionQuality"]["failedBatch"] = batch_index
            failed["extractionQuality"]["attemptLog"] = list(attempt_log)
            return failed
        _merge_batch_payload(merged, batch_payload, batch_index)

    extraction = extract_evidence_from_llm_payload(
        json.dumps(merged, ensure_ascii=False),
        track_rule,
    )
    quality = extraction.setdefault("extractionQuality", {})
    quality["strategy"] = "observation_batches"
    quality["batchCount"] = (len(observations) + batch_size - 1) // batch_size
    quality["retryCount"] = 1
    return extraction


def _merge_batch_payload(merged: dict[str, Any], payload: dict[str, Any], batch_index: int) -> None:
    prefix = f"B{batch_index}-"
    evidence_id_map: dict[str, str] = {}
    claim_id_map: dict[str, str] = {}

    for index, item in enumerate(_list_of_dicts(payload.get("claims"))):
        row = dict(item)
        old_id = str(row.get("claimId") or row.get("id") or f"C{index + 1}")
        new_id = prefix + old_id
        claim_id_map[old_id] = new_id
        if "claimId" in row:
            row["claimId"] = new_id
        else:
            row["id"] = new_id
        merged["claims"].append(row)

    for index, item in enumerate(_list_of_dicts(payload.get("evidenceItems"))):
        row = dict(item)
        old_id = str(row.get("evidenceId") or row.get("id") or f"E{index + 1}")
        new_id = prefix + old_id
        evidence_id_map[old_id] = new_id
        row["evidenceId"] = new_id
        row.pop("id", None)
        merged["evidenceItems"].append(row)

    for item in _observation_items(payload.get("observationEvidence")):
        row = dict(item)
        row["evidenceIds"] = [
            evidence_id_map.get(str(value), prefix + str(value))
            for value in row.get("evidenceIds") or []
        ]
        row["claimIds"] = [
            claim_id_map.get(str(value), prefix + str(value))
            for value in row.get("claimIds") or []
        ]
        merged["observationEvidence"].append(row)

    for key in ("deductionCandidates", "recoveryCandidates", "riskFlags"):
        for item in _list_of_dicts(payload.get(key)):
            row = dict(item)
            if "evidenceIds" in row:
                row["evidenceIds"] = [
                    evidence_id_map.get(str(value), prefix + str(value))
                    for value in row.get("evidenceIds") or []
                ]
            merged[key].append(row)


def _response_content_and_meta(response, max_tokens: int, *, attempt: int) -> tuple[str, dict[str, Any]]:
    choice = response.choices[0]
    content = getattr(choice.message, "content", "") or ""
    finish_reason = getattr(choice, "finish_reason", None)
    usage = getattr(response, "usage", None)
    completion_tokens = _usage_int(usage, "completion_tokens")
    prompt_tokens = _usage_int(usage, "prompt_tokens")
    total_tokens = _usage_int(usage, "total_tokens")
    return content, {
        "attempt": attempt,
        "finish_reason": finish_reason,
        "max_tokens": max_tokens,
        "promptTokens": prompt_tokens,
        "completionTokens": completion_tokens,
        "totalTokens": total_tokens,
        "responseChars": len(content),
        "truncated": _is_truncated_response(
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            max_tokens=max_tokens,
            content=content,
        ),
    }


def _summed_token_usage(attempt_log: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "promptTokens": sum(int(item.get("promptTokens") or 0) for item in attempt_log),
        "completionTokens": sum(int(item.get("completionTokens") or 0) for item in attempt_log),
        "totalTokens": sum(int(item.get("totalTokens") or 0) for item in attempt_log),
    }


def _parse_json_object(content: str) -> dict[str, Any]:
    text = _strip_code_fence(content or "")
    candidates = [text]
    repaired = _repair_json_text(text)
    if repaired != text:
        candidates.append(repaired)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        block = match.group()
        candidates.append(block)
        repaired_block = _repair_json_text(block)
        if repaired_block != block:
            candidates.append(repaired_block)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            result = json.loads(candidate)
        except Exception as exc:  # noqa: BLE001 - collect best error for caller
            last_error = exc
            continue
        if isinstance(result, dict):
            return result
        last_error = ValueError("证据抽取结果必须是 JSON object")
    if last_error is not None:
        raise last_error
    raise ValueError("无法解析证据抽取 JSON")


def _strip_code_fence(content: str) -> str:
    text = (content or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _repair_json_text(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return text
    # Remove trailing commas before object/array close.
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    # Normalize smart quotes that models occasionally emit.
    text = text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    return text


def _is_truncated_response(
    *,
    finish_reason: str | None,
    completion_tokens: int,
    max_tokens: int,
    content: str,
) -> bool:
    if str(finish_reason or "").lower() == "length":
        return True
    if completion_tokens >= max(1, int(max_tokens * 0.98)):
        return True
    # Incomplete top-level JSON is a strong truncation signal even when finish_reason is missing.
    stripped = (content or "").strip()
    if stripped.startswith("{") and not stripped.endswith("}"):
        return True
    return False


def _usage_int(usage: Any, field: str) -> int:
    value = getattr(usage, field, 0) if usage is not None else 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _failed_extraction(track_rule: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "trackId": track_rule.get("trackId"),
        "trackName": track_rule.get("trackName"),
        "ruleVersion": track_rule.get("ruleVersion"),
        "ruleHash": track_rule.get("ruleHash"),
        "claims": [],
        "evidenceItems": [],
        "observationEvidence": [],
        "deductionCandidates": [],
        "recoveryCandidates": [],
        "riskFlags": [{"code": "json_parse_failed", "message": error, "sourceType": "system"}],
        "extractionQuality": {"jsonParseable": False, "error": error},
    }


def _normalize_observation_evidence(
    rule_observation: dict[str, Any],
    model_item: dict[str, Any] | None,
    valid_evidence_ids: set[str],
    evidence_items_by_id: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    warnings = []
    code = rule_observation.get("observationCode")
    item = model_item or {}
    evidence_ids = [str(value) for value in item.get("evidenceIds") or [] if str(value) in valid_evidence_ids]
    claim_ids = [str(value) for value in item.get("claimIds") or []]
    level = str(item.get("evidenceLevel") or "E0").upper()
    if level not in EVIDENCE_LEVELS:
        level = "E0"
        warnings.append(f"{code}:unsupported_evidence_level")
    if level == "E0" and evidence_ids:
        # Bound evidence means at least slogan/weak support; never keep E0 with IDs.
        level = "E1"
        warnings.append(f"{code}:E0_upgraded_to_E1_with_bound_evidence")
    if level != "E0" and not evidence_ids:
        level = "E0"
        warnings.append(f"{code}:non_e0_without_evidence")
    level, gate_warnings = _apply_evidence_level_hard_gates(
        level,
        evidence_ids,
        item,
        evidence_items_by_id,
        code,
    )
    warnings.extend(gate_warnings)

    evidence_caps = rule_observation.get("evidenceCaps") or {}
    score_cap = _safe_float(evidence_caps.get(level), 0)
    raw_performance_level = str(
        item.get("performanceLevel")
        or item.get("achievementLevel")
        or "not_demonstrated"
    ).strip().lower()
    if raw_performance_level not in PERFORMANCE_RATIOS:
        raw_performance_level = "not_demonstrated"
        warnings.append(f"{code}:unsupported_achievement_level")
    raw_performance_reason = str(
        item.get("performanceReason")
        or item.get("achievementReason")
        or ""
    ).strip()
    evidence_reason = str(
        item.get("evidenceReason")
        or item.get("supportSummary")
        or ("当前无可核验证据" if level == "E0" else "")
    ).strip()
    if not evidence_reason:
        evidence_reason = "已找到相关现场依据，但仍需补充更完整、可复核的证明材料"
    performance_assessment_status = "assessed"
    if _is_external_evidence_only_performance_reason(raw_performance_reason):
        performance_level = "not_assessed"
        performance_ratio = 1.0
        performance_reason = "表现理由受证据缺失语义污染，本项未据此扣减表现分，需重新评估现场表现"
        evidence_reason = "；".join(value for value in (evidence_reason, raw_performance_reason) if value)
        performance_assessment_status = "review_required_evidence_contamination"
        warnings.append(f"{code}:performance_reason_evidence_contamination")
    else:
        performance_level = raw_performance_level
        performance_ratio = PERFORMANCE_RATIOS[performance_level]
        performance_reason = raw_performance_reason or (
            "当前未展示该观测点的有效达成内容" if performance_level == "not_demonstrated" else ""
        )
    max_score = _safe_float(rule_observation.get("maxScore"), 0)
    base_score = round(max_score * performance_ratio, 2)
    validity = item.get("validityStatus") or ("missing_evidence" if level == "E0" else "valid")
    return {
        "observationCode": code,
        "observationName": rule_observation.get("observationName"),
        "dimensionCode": rule_observation.get("dimensionCode"),
        "dimensionName": rule_observation.get("dimensionName"),
        "claimIds": claim_ids,
        "evidenceIds": evidence_ids,
        "evidenceLevel": level,
        "confidence": _clamp(_safe_float(
            item.get("confidence"),
            DEFAULT_CONFIDENCE_BY_EVIDENCE_LEVEL.get(level, 0),
        ), 0, 1),
        "supportSummary": item.get("supportSummary") or ("当前无可核验证据" if level == "E0" else ""),
        "evidenceReason": evidence_reason,
        "missingEvidence": item.get("missingEvidence") or _missing_evidence(rule_observation, level),
        "performanceLevel": performance_level,
        "performanceRatio": performance_ratio,
        "performanceReason": performance_reason,
        "performanceAssessmentStatus": performance_assessment_status,
        "achievementLevel": performance_level,
        "achievementRatio": performance_ratio,
        "achievementReason": performance_reason,
        "maxScore": max_score,
        "suggestedBaseScore": base_score,
        "suggestedScoreCap": score_cap,
        "validityStatus": validity,
        "sourceType": "llm_extraction" if model_item else "system_backfill",
    }, warnings


def _is_external_evidence_only_performance_reason(reason: str) -> bool:
    if not reason:
        return False
    missing_match = re.search(
        r"(缺少|未提供|未展示|没有|无|不足|缺乏).{0,24}"
        r"(第三方|订单|附件|证明|报告|截图|台账|记录|文档|书面材料|数据来源|验收|认证|授权|客户反馈|运营数据)",
        reason,
    )
    if not missing_match:
        return False
    deficit_text = reason[missing_match.start():]
    return not bool(re.search(
        r"操作|流程|步骤|技能|控制点|场景|协作|沟通|活动|计划|诊断|处理|运行|演示过程|使用过程",
        deficit_text,
    ))


def _apply_evidence_level_hard_gates(
    level: str,
    evidence_ids: list[str],
    item: dict[str, Any],
    evidence_items_by_id: dict[str, dict[str, Any]] | None,
    code: str | None,
) -> tuple[str, list[str]]:
    """Downgrade inflated evidence levels using server-side hard conditions.

    Cascade: E5 → E4 → E3 → E2. Warnings keep the original failing level so
    audits can see what the model claimed versus what rules allow.
    """
    warnings: list[str] = []
    current = str(level or "E0").upper()
    reasons = {
        "E5": "missing_independent_verification",
        "E4": "missing_scene_validation",
        "E3": "missing_internal_quantitative_evidence",
    }
    next_level = {"E5": "E4", "E4": "E3", "E3": "E2"}
    while current in next_level:
        if _has_hard_condition_evidence(current, evidence_ids, item, evidence_items_by_id):
            break
        warnings.append(f"{code}:{current}_downgraded_{reasons[current]}")
        current = next_level[current]
    return current, warnings


def _has_hard_condition_evidence(
    level: str,
    evidence_ids: list[str],
    item: dict[str, Any],
    evidence_items_by_id: dict[str, dict[str, Any]] | None = None,
) -> bool:
    """Return whether bound evidence can support the claimed evidence level."""
    if not evidence_ids:
        return False

    bound_items = []
    bound_texts = []
    bound_source_types = []
    for evidence_id in evidence_ids:
        row = (evidence_items_by_id or {}).get(str(evidence_id)) or {}
        if row:
            bound_items.append(row)
            bound_texts.append(str(row.get("text") or ""))
            bound_source_types.append(str(row.get("sourceType") or "").lower())

    # Prefer bound evidence inventory text; fall back to observation payload.
    observation_text = " ".join(
        str(item.get(key) or "")
        for key in (
            "supportSummary",
            "evidenceReason",
            "performanceReason",
            "achievementReason",
            "missingEvidence",
        )
    )
    text = " ".join(part for part in [*bound_texts, observation_text] if part).strip()
    if not text:
        text = json.dumps(item, ensure_ascii=False)

    if level == "E3":
        if re.search(
            r"(缺少|没有|未|无|不足|缺乏).{0,12}"
            r"(数据|指标|测算|测试|样本|订单|交易|流水|转化率|成本|复盘|台账|记录|反馈)",
            text,
        ):
            return False
        return bool(re.search(
            r"(\d+(\.\d+)?%?|数据|指标|测算|测试|样本|订单|交易|流水|转化率|成本|复盘|"
            r"台账|记录|反馈|销售|库存|GMV|ROI|CTR|CVR)",
            text,
            re.I,
        ))

    if level == "E4":
        if re.search(
            r"(缺少|没有|未|无|不足|缺乏).{0,12}"
            r"(现场|场景|用户|试点|演示|前后对比|运行|验证)",
            text,
        ):
            return False
        has_scene_words = bool(re.search(r"现场|场景|用户|试点|演示|前后对比|运行|实测|实操", text))
        has_scene_source = any(
            source in {
                "timeline",
                "frame",
                "frame_ocr",
                "visual",
                "screen",
                "screen_ocr",
                "video",
            }
            for source in bound_source_types
        )
        return has_scene_words or has_scene_source

    if level == "E5":
        if re.search(
            r"(缺少|没有|未|无|不足|缺乏).{0,12}"
            r"(第三方|客户验收|审计|认证|公开|benchmark|可复现)",
            text,
            re.I,
        ):
            return False
        has_independent_words = bool(re.search(
            r"第三方|客户验收|独立验收|审计|认证|公开|benchmark|可复现|权威报告",
            text,
            re.I,
        ))
        has_material_source = any(
            source in {"material", "document", "report", "certificate", "upload"}
            for source in bound_source_types
        )
        # Independent verification must be more than an empty material slot.
        return has_independent_words and (has_material_source or bool(bound_texts))

    return True


def _missing_evidence(rule_observation: dict[str, Any], level: str) -> list[str]:
    if level != "E0":
        return []
    values = rule_observation.get("acceptableEvidence") or []
    return [f"缺少{value}" for value in values[:3]]


def _normalize_evidence_items(value: Any) -> list[dict[str, Any]]:
    items = []
    for index, item in enumerate(_list_of_dicts(value)):
        evidence_id = item.get("evidenceId") or item.get("id") or f"e{index + 1}"
        items.append({
            "evidenceId": str(evidence_id),
            "sourceType": item.get("sourceType") or _source_type_from_ref(item.get("sourceRef")),
            "sourceRef": item.get("sourceRef") or "",
            "text": item.get("text") or item.get("summary") or "",
            "confidence": _clamp(_safe_float(item.get("confidence"), 0), 0, 1),
        })
    return items


def _source_type_from_ref(source_ref: Any) -> str:
    value = str(source_ref or "").strip().lower()
    if value.startswith("timeline@"):
        return "timeline"
    if value.startswith("transcript@"):
        return "transcript"
    if value:
        return "material"
    return "unknown"


def _compact_fusion_timeline(value: Any, limit: int = 24) -> list[dict[str, Any]]:
    """Sample a small evenly spaced set of timeline points for LLM prompts.

    Full 60-minute roadshows can produce 100+ frames; dumping all of them makes
    the extraction prompt explode (~80k chars) and triggers API connection errors.
    """
    items = _list_of_dicts(value)
    if not items:
        return []
    limit = max(6, int(limit or 24))
    if len(items) <= limit:
        sampled = items
    else:
        # Keep head/middle/tail coverage without flooding the prompt.
        indexes = sorted({
            0,
            len(items) - 1,
            *[
                min(len(items) - 1, int(round(i * (len(items) - 1) / (limit - 1))))
                for i in range(limit)
            ],
        })
        sampled = [items[i] for i in indexes[:limit]]

    compact = []
    for item in sampled:
        seconds = _timeline_seconds(item)
        visual = str(item.get("visual_impression") or "")[:120]
        preview = str(item.get("text_preview") or "")[:80]
        scene = str(item.get("scene_type") or "")[:40]
        row = {
            "sourceRef": f"timeline@{_format_mmss(seconds)}",
            "visualImpression": visual,
            "sceneType": scene,
            "textPreview": preview,
        }
        # Drop empty keys to keep JSON small.
        compact.append({key: value for key, value in row.items() if value})
    return compact


def _timeline_seconds(item: dict[str, Any]) -> float:
    if item.get("time_sec") is not None:
        return _safe_float(item.get("time_sec"), 0)
    if item.get("time_seconds") is not None:
        return _safe_float(item.get("time_seconds"), 0)
    return _safe_float(item.get("time_min"), 0) * 60


def _format_mmss(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def _has_evidence_payload(item: dict[str, Any]) -> bool:
    return bool(str(item.get("text") or "").strip() or str(item.get("sourceRef") or "").strip())


def _normalize_candidates(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in _list_of_dicts(value)]


def _observation_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    nested_items = value.get("items")
    if isinstance(nested_items, list):
        return [dict(item) for item in nested_items if isinstance(item, dict)]
    items = []
    for key, raw_item in value.items():
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        item.setdefault("observationCode", key)
        items.append(item)
    return items


def _core_evidence_location_hints(track_rule: dict[str, Any], scoring_context: dict[str, Any]) -> list[dict[str, str]]:
    code_by_name = {
        str(item.get("observationName") or "").strip(): str(item.get("observationCode") or "").strip()
        for item in track_rule.get("observations") or []
    }
    hints = []
    for dimension in (scoring_context.get("dimensions") or {}).values():
        if not isinstance(dimension, dict):
            continue
        for item in dimension.get("items") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            reason = str(item.get("reason") or "").strip()
            code = code_by_name.get(name)
            if code and reason:
                hints.append({
                    "observationCode": code,
                    "observationName": name,
                    "candidateEvidenceLocation": reason,
                })
    return hints


def _normalize_observation_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    match = re.fullmatch(r"O[-_ ]?(\d{1,2})", text)
    if match:
        return f"O{int(match.group(1)):02d}"
    return text


def _normalize_quality(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _has_missing_observations(observation_evidence: list[dict[str, Any]]) -> bool:
    return any(item.get("evidenceLevel") == "E0" for item in observation_evidence)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))
