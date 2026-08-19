"""High-quality report prose grounded on the authoritative rule ledger.

Design goals:
1. Intelligence stays high — a full coach/jury style JSON report from the LLM.
2. Score truth stays locked — overall/dimension scores always come from the rule ledger.
3. Fail closed on scoring — if the model invents scores, they are overwritten.
4. Fail open on prose — if generation fails, keep the deterministic ledger narrative.
"""

from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_REPORT_VERSION = "ledger-grounded-report-v2-session"
_PROSE_FIELDS = (
    "score_overview",
    "highlights",
    "critical_issues",
    "evidence_summary",
    "evidence_audit",
    "jury_review",
    "audio_visual_fusion",
    "pitch_structure_benchmark",
    "judge_questioning",
    "action_plan",
    "team_optimization",
    "final_verdict",
    "improvement_priorities",
)
_STAGE_A_FIELDS = (
    "score_overview",
    "highlights",
    "critical_issues",
    "evidence_audit",
    "action_plan",
    "improvement_priorities",
    "team_optimization",
)
_STAGE_B1_FIELDS = (
    "jury_review",
)
_STAGE_B2_FIELDS = (
    "audio_visual_fusion",
    "pitch_structure_benchmark",
    "judge_questioning",
    "final_verdict",
    "evidence_summary",
)
_STAGE_B_FIELDS = _STAGE_B1_FIELDS + _STAGE_B2_FIELDS


def enrich_with_ledger_grounded_report(
    *,
    ai_score: dict,
    rule_payload: dict,
    evidence_extraction: dict | None,
    asr_result: dict | None,
    speech_quality: dict | None,
    project_info: dict | None,
    fusion_context: dict | None = None,
    provider: str = "deepseek",
    meeting_id: str | None = None,
) -> dict:
    """Generate coach-grade report text while freezing authoritative scores.

    Session stages (to avoid long-body connection drops):
      A) diagnosis + actions
      B1) nine jury reviews for personas sampled from the backend pool
      B2) structure + final verdict
    """
    base = deepcopy(ai_score or {})
    if (rule_payload or {}).get("scoreAuthority") != "structured_rule_engine":
        return base
    if not getattr(settings, "LLM_LEDGER_GROUNDED_REPORT_ENABLED", True):
        base.setdefault("narrative_source", base.get("narrative_source") or "rule-ledger-narrative-v1")
        return base

    try:
        from app.services.llm_scoring_service import MODEL_MAP, PROVIDER_LABELS, get_client
        from app.services.llm_stage_runner import StageGenerationError, run_json_stage
    except Exception as exc:
        logger.warning("ledger grounded report imports failed: %s", exc)
        return base

    if provider not in MODEL_MAP:
        provider = "deepseek"
    model_name = MODEL_MAP.get(provider, settings.DEEPSEEK_MODEL or "deepseek-v4-pro")
    provider_label = PROVIDER_LABELS.get(provider, provider)
    client = get_client(provider)

    from app.services.scoring.evidence_memory_session import build_report_memory_pack

    # Same seed scheme as independent AI jury: sample N personas from the pool.
    assigned_personas, jury_seed_meta = _select_report_jury_personas(
        meeting_id=meeting_id,
        rule_payload=rule_payload,
        project_info=project_info,
        ai_score=base,
    )

    memory_pack = build_report_memory_pack(
        rule_payload=rule_payload,
        evidence_extraction=evidence_extraction or {},
        asr_result=asr_result or {},
        max_evidence=12,
        max_losses=12,
    )
    fact_pack = {
        "project": {
            "projectName": (project_info or {}).get("project_name") or (project_info or {}).get("projectName"),
            "track": (project_info or {}).get("track") or (evidence_extraction or {}).get("trackName"),
            "teamSize": (project_info or {}).get("team_size") or (project_info or {}).get("teamSize"),
            "durationSec": (asr_result or {}).get("duration"),
        },
        "speechQuality": {
            "speechRate": ((speech_quality or {}).get("speech_rate") or {}).get("avg_wpm")
            or ((speech_quality or {}).get("speech_rate") or {}).get("wpm"),
            "pauseCount": ((speech_quality or {}).get("pauses") or {}).get("count"),
            "fillerCount": ((speech_quality or {}).get("fillers") or {}).get("count"),
        },
        "seedHighlights": list(base.get("highlights") or [])[:6],
        "seedCriticalIssues": list(base.get("critical_issues") or [])[:6],
        "seedActionPlan": [
            {
                "title": row.get("title"),
                "problem": row.get("problem"),
                "method": row.get("method"),
                "priority": row.get("priority"),
                "observationCode": row.get("observationCode"),
            }
            for row in list(base.get("action_plan") or [])[:8]
            if isinstance(row, dict)
        ],
        "allowedObservationCodes": sorted({
            str(row.get("observationCode"))
            for row in list((rule_payload or {}).get("observations") or [])
            if isinstance(row, dict) and row.get("observationCode")
        }),
        "assignedJury": _persona_roster_for_prompt(assigned_personas),
        **memory_pack,
    }

    stage_tokens = max(
        1800,
        int(getattr(settings, "LLM_LEDGER_GROUNDED_REPORT_STAGE_MAX_TOKENS", 3500) or 3500),
    )
    stage_timeout = float(
        getattr(settings, "LLM_LEDGER_GROUNDED_REPORT_STAGE_TIMEOUT_SECONDS", 150) or 150
    )
    generation_meta = dict(base.get("generation_meta") or {})
    combined: dict[str, Any] = {}
    total_meta = {
        "status": "partial",
        "source": _REPORT_VERSION,
        "stages": {},
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "jury_selection": jury_seed_meta,
    }

    # ---- Stage A: diagnosis + actions (must succeed for useful report) ----
    try:
        stage_a, meta_a = run_json_stage(
            client=client,
            model=model_name,
            stage="ledger_report_stage_a",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是OREP路演教练。本阶段只写诊断、亮点、关键问题、证据审计、行动计划、团队优化。"
                        "禁止输出总分或改写权威分。只输出JSON。"
                    ),
                },
                {"role": "user", "content": _build_stage_a_prompt(fact_pack)},
            ],
            max_tokens=stage_tokens,
            timeout=stage_timeout,
            validator=lambda data: _validate_stage_a(data, fact_pack),
            temperature=0.3,
            max_attempts=2,
        )
        for field in _STAGE_A_FIELDS:
            if field in stage_a:
                combined[field] = stage_a[field]
        total_meta["stages"]["A"] = {"status": "completed", **(meta_a or {})}
        total_meta["prompt_tokens"] += int((meta_a or {}).get("prompt_tokens") or 0)
        total_meta["completion_tokens"] += int((meta_a or {}).get("completion_tokens") or 0)
        total_meta["total_tokens"] += int((meta_a or {}).get("total_tokens") or 0)
    except StageGenerationError as exc:
        logger.warning("ledger report stage A failed: %s", exc)
        generation_meta["ledger_grounded_report"] = {
            "status": "failed",
            "error": f"stage_a:{exc}",
            "source": _REPORT_VERSION,
            **(exc.meta or {}),
        }
        base["generation_meta"] = generation_meta
        return base
    except Exception as exc:
        logger.warning("ledger report stage A unexpected failure: %s", exc)
        generation_meta["ledger_grounded_report"] = {
            "status": "failed",
            "error": f"stage_a:{exc}",
            "source": _REPORT_VERSION,
        }
        base["generation_meta"] = generation_meta
        return base

    stage_a_snapshot = _stage_a_snapshot_for_b(combined)
    stage_b_tokens = max(stage_tokens, 4500)
    jury_llm_ok = False
    structure_llm_ok = False

    # ---- Stage B1: nine jury only for the sampled persona roster ----
    try:
        stage_b1, meta_b1 = run_json_stage(
            client=client,
            model=model_name,
            stage="ledger_report_stage_b1_jury",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是OREP九评委独立评审专家。本阶段只输出 jury_review。"
                        "评委名单已由系统从人格库抽样，必须严格使用给定 judge_code/judge_type，禁止自造或替换人格。"
                        "正式总分不可改写。九评委 score 仅为诊断分。只输出JSON。"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_stage_b1_prompt(
                        fact_pack,
                        stage_a_snapshot,
                        assigned_personas=assigned_personas,
                    ),
                },
            ],
            max_tokens=stage_b_tokens,
            timeout=stage_timeout,
            validator=lambda data: _validate_stage_b1(
                data, rule_payload, assigned_personas=assigned_personas
            ),
            temperature=0.35,
            max_attempts=2,
        )
        combined["jury_review"] = stage_b1.get("jury_review") or []
        jury_llm_ok = True
        total_meta["stages"]["B1"] = {"status": "completed", **(meta_b1 or {})}
        total_meta["prompt_tokens"] += int((meta_b1 or {}).get("prompt_tokens") or 0)
        total_meta["completion_tokens"] += int((meta_b1 or {}).get("completion_tokens") or 0)
        total_meta["total_tokens"] += int((meta_b1 or {}).get("total_tokens") or 0)
    except StageGenerationError as exc:
        logger.warning("ledger report stage B1 jury failed: %s", exc)
        total_meta["stages"]["B1"] = {"status": "failed", "error": str(exc), **(exc.meta or {})}
        combined["jury_review"] = _fallback_jury_review(
            combined, rule_payload, assigned_personas=assigned_personas
        )
    except Exception as exc:
        logger.warning("ledger report stage B1 unexpected failure: %s", exc)
        total_meta["stages"]["B1"] = {"status": "failed", "error": str(exc)}
        combined["jury_review"] = _fallback_jury_review(
            combined, rule_payload, assigned_personas=assigned_personas
        )

    # ---- Stage B2: structure + final verdict ----
    try:
        stage_b2, meta_b2 = run_json_stage(
            client=client,
            model=model_name,
            stage="ledger_report_stage_b2_structure",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是OREP结构复盘与总评专家。本阶段只写音视频融合、路演结构、评委追问、最终结论与证据摘要。"
                        "正式总分不可改写。只输出JSON。"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_stage_b2_prompt(
                        fact_pack,
                        stage_a_snapshot=stage_a_snapshot,
                        jury_snapshot=_jury_snapshot_for_b2(combined.get("jury_review") or []),
                    ),
                },
            ],
            max_tokens=stage_tokens,
            timeout=stage_timeout,
            validator=lambda data: _validate_stage_b2(data, rule_payload),
            temperature=0.3,
            max_attempts=2,
        )
        for field in _STAGE_B2_FIELDS:
            if field in stage_b2:
                combined[field] = stage_b2[field]
        structure_llm_ok = True
        total_meta["stages"]["B2"] = {"status": "completed", **(meta_b2 or {})}
        total_meta["prompt_tokens"] += int((meta_b2 or {}).get("prompt_tokens") or 0)
        total_meta["completion_tokens"] += int((meta_b2 or {}).get("completion_tokens") or 0)
        total_meta["total_tokens"] += int((meta_b2 or {}).get("total_tokens") or 0)
    except StageGenerationError as exc:
        logger.warning("ledger report stage B2 structure failed: %s", exc)
        total_meta["stages"]["B2"] = {"status": "failed", "error": str(exc), **(exc.meta or {})}
        combined.setdefault("final_verdict", _fallback_final_verdict(combined, rule_payload))
    except Exception as exc:
        logger.warning("ledger report stage B2 unexpected failure: %s", exc)
        total_meta["stages"]["B2"] = {"status": "failed", "error": str(exc)}
        combined.setdefault("final_verdict", _fallback_final_verdict(combined, rule_payload))

    if jury_llm_ok and structure_llm_ok:
        total_meta["status"] = "completed"
    elif jury_llm_ok or structure_llm_ok:
        total_meta["status"] = "partial"
    else:
        total_meta["status"] = "stage_a_only"
        combined.setdefault("final_verdict", _fallback_final_verdict(combined, rule_payload))
        combined.setdefault(
            "jury_review",
            _fallback_jury_review(combined, rule_payload, assigned_personas=assigned_personas),
        )

    combined["overall_score"] = rule_payload.get("finalScore")
    combined["score_authority"] = "structured_rule_engine"
    merged = _merge_locked_report(base, combined, rule_payload)
    merged["model"] = f"{provider_label} ({model_name}) + rule-ledger"
    merged["provider"] = provider
    merged["score_authority"] = "structured_rule_engine"
    merged["narrative_source"] = _REPORT_VERSION
    merged["jury_personas"] = _persona_roster_for_prompt(assigned_personas)
    generation_meta["ledger_grounded_report"] = total_meta
    merged["generation_meta"] = generation_meta
    tokens = merged.get("tokens_used") or {}
    merged["tokens_used"] = {
        "prompt_tokens": int(tokens.get("prompt_tokens") or 0) + total_meta["prompt_tokens"],
        "completion_tokens": int(tokens.get("completion_tokens") or 0) + total_meta["completion_tokens"],
        "total_tokens": int(tokens.get("total_tokens") or 0) + total_meta["total_tokens"],
    }
    return merged


def _build_fact_pack(
    *,
    rule_payload: dict,
    evidence_extraction: dict,
    asr_result: dict,
    speech_quality: dict,
    project_info: dict,
    fusion_context: dict,
    seed_score: dict,
) -> dict[str, Any]:
    observations = [
        {
            "observationCode": row.get("observationCode"),
            "observationName": row.get("observationName"),
            "dimensionCode": row.get("dimensionCode"),
            "maxScore": row.get("maxScore"),
            "finalScore": row.get("finalScore"),
            "baseScore": row.get("baseScore") or row.get("performanceScore"),
            "scoreCap": row.get("scoreCap"),
            "evidenceLevel": row.get("evidenceLevel"),
            "performanceReason": row.get("performanceReason") or row.get("modelReason"),
            "evidenceReason": row.get("evidenceReason"),
        }
        for row in list(rule_payload.get("observations") or [])
        if isinstance(row, dict)
    ]
    losses = sorted(
        [
            {
                "causeCode": row.get("causeCode"),
                "observationCode": row.get("observationCode"),
                "observationName": row.get("observationName"),
                "dimensionCode": row.get("dimensionCode"),
                "lossType": row.get("lossType"),
                "points": row.get("points"),
                "reason": row.get("reason"),
                "penaltyRuleCode": row.get("penaltyRuleCode"),
                "evidenceAnchorIds": list(row.get("evidenceAnchorIds") or []),
            }
            for row in list(rule_payload.get("lossLedger") or [])
            if isinstance(row, dict) and float(row.get("points") or 0) > 0
        ],
        key=lambda row: -float(row.get("points") or 0),
    )
    anchors = []
    for row in list(rule_payload.get("evidenceAnchors") or [])[:40]:
        if not isinstance(row, dict):
            continue
        anchors.append({
            "id": row.get("id"),
            "title": row.get("anchorTitle") or row.get("sourceRef"),
            "text": row.get("evidenceText") or row.get("text"),
            "sourceRef": row.get("sourceRef"),
            "startMs": row.get("startMs"),
            "observationCodes": list(row.get("observationCodes") or []),
            "riskTone": row.get("riskTone"),
        })
    seed_actions = [
        {
            "title": row.get("title"),
            "problem": row.get("problem"),
            "method": row.get("method"),
            "priority": row.get("priority"),
            "observationCode": row.get("observationCode"),
            "observationCodes": list(row.get("observationCodes") or []),
            "sourceIssueKey": row.get("sourceIssueKey"),
        }
        for row in list(seed_score.get("action_plan") or [])[:12]
        if isinstance(row, dict)
    ]
    return {
        "project": {
            "projectName": project_info.get("project_name") or project_info.get("projectName"),
            "track": project_info.get("track") or evidence_extraction.get("trackName"),
            "teamSize": project_info.get("team_size") or project_info.get("teamSize"),
            "durationSec": asr_result.get("duration"),
        },
        "authoritativeScore": {
            "overallScore": rule_payload.get("finalScore"),
            "dimensionScores": rule_payload.get("dimensionScores") or {},
            "dimensionMaxScores": rule_payload.get("dimensionMaxScores") or {},
            "performanceGap": rule_payload.get("performanceGap"),
            "evidenceLimitedGap": rule_payload.get("evidenceLimitedGap"),
            "effectiveHardPenalty": rule_payload.get("effectiveHardPenalty"),
            "reconciliation": rule_payload.get("reconciliation") or {},
            "scorePolicyVersion": rule_payload.get("scorePolicyVersion"),
            "ruleFingerprint": rule_payload.get("ruleFingerprint") or rule_payload.get("scoringFingerprint"),
        },
        "observations": observations,
        "lossLedger": losses[:25],
        "evidenceAnchors": anchors,
        "seedActionPlan": seed_actions,
        "seedHighlights": list(seed_score.get("highlights") or [])[:8],
        "seedCriticalIssues": list(seed_score.get("critical_issues") or [])[:8],
        "speechQuality": {
            "speechRate": (speech_quality.get("speech_rate") or {}).get("avg_wpm")
            or (speech_quality.get("speech_rate") or {}).get("wpm"),
            "pauseCount": (speech_quality.get("pauses") or {}).get("count"),
            "fillerCount": (speech_quality.get("fillers") or {}).get("count"),
        },
        "fusionSummary": (fusion_context or {}).get("screen_content_summary") or {},
        "fusionContradictions": list((fusion_context or {}).get("contradictions") or [])[:8],
        "transcriptExcerpts": _transcript_excerpts(asr_result, losses, anchors),
        "allowedObservationCodes": sorted({
            str(row.get("observationCode"))
            for row in observations
            if row.get("observationCode")
        }),
    }


def _transcript_excerpts(asr_result: dict, losses: list[dict], anchors: list[dict]) -> list[dict]:
    segments = [
        seg for seg in list((asr_result or {}).get("segments") or [])
        if isinstance(seg, dict) and str(seg.get("text") or "").strip()
    ]
    if not segments:
        text = str((asr_result or {}).get("transcript") or "").strip()
        if not text:
            return []
        return [{"label": "full_head", "text": text[:2500]}]

    targets_sec: list[float] = []
    for anchor in anchors:
        if anchor.get("startMs") is not None:
            try:
                targets_sec.append(float(anchor["startMs"]) / 1000.0)
            except (TypeError, ValueError):
                pass
    # Always include opening / middle / closing.
    duration = float((asr_result or {}).get("duration") or 0)
    if duration <= 0 and segments:
        try:
            duration = float(segments[-1].get("end") or segments[-1].get("start") or 0)
        except (TypeError, ValueError):
            duration = 0
    for ratio in (0.05, 0.5, 0.9):
        targets_sec.append(duration * ratio)

    excerpts = []
    used = set()
    for target in targets_sec[:12]:
        best = min(
            segments,
            key=lambda seg: abs(_seg_start(seg) - float(target or 0)),
        )
        key = id(best)
        if key in used:
            continue
        used.add(key)
        start = _seg_start(best)
        speaker = best.get("displaySpeaker") or best.get("speaker") or ""
        excerpts.append({
            "time": _format_mmss(start),
            "speaker": speaker,
            "text": str(best.get("text") or "").strip()[:280],
        })
        if len(excerpts) >= 10:
            break
    if len(excerpts) < 4:
        step = max(1, len(segments) // 4)
        for seg in segments[::step][:4]:
            excerpts.append({
                "time": _format_mmss(_seg_start(seg)),
                "speaker": seg.get("displaySpeaker") or seg.get("speaker") or "",
                "text": str(seg.get("text") or "").strip()[:280],
            })
    return excerpts[:12]


def _seg_start(segment: dict) -> float:
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
    return f"{minutes:02d}:{secs:02d}"


def _lean_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _stage_pack_a(fact_pack: dict) -> dict[str, Any]:
    """Lean pack for diagnosis/actions — keep losses + observations, drop noise."""
    return {
        "project": fact_pack.get("project") or {},
        "speechQuality": fact_pack.get("speechQuality") or {},
        "authoritativeScore": fact_pack.get("authoritativeScore") or {},
        "runningSummary": fact_pack.get("runningSummary") or "",
        "topLosses": list(fact_pack.get("topLosses") or [])[:10],
        "observations": list(fact_pack.get("observations") or [])[:12],
        "evidenceItems": list(fact_pack.get("evidenceItems") or [])[:8],
        "seedHighlights": list(fact_pack.get("seedHighlights") or [])[:5],
        "seedCriticalIssues": list(fact_pack.get("seedCriticalIssues") or [])[:5],
        "seedActionPlan": list(fact_pack.get("seedActionPlan") or [])[:6],
        "allowedObservationCodes": list(fact_pack.get("allowedObservationCodes") or []),
    }


def _stage_pack_b(fact_pack: dict, stage_a_snapshot: dict) -> dict[str, Any]:
    """Lean pack for jury/structure — avoid re-sending full evidence dump."""
    return {
        "authoritativeScore": fact_pack.get("authoritativeScore") or {},
        "runningSummary": fact_pack.get("runningSummary") or "",
        "topLosses": list(fact_pack.get("topLosses") or [])[:8],
        "observations": [
            {
                "observationCode": row.get("observationCode"),
                "observationName": row.get("observationName"),
                "finalScore": row.get("finalScore"),
                "maxScore": row.get("maxScore"),
                "evidenceLevel": row.get("evidenceLevel"),
            }
            for row in list(fact_pack.get("observations") or [])[:12]
            if isinstance(row, dict)
        ],
        "stageA": stage_a_snapshot,
    }


def _stage_a_snapshot_for_b(combined: dict) -> dict[str, Any]:
    actions = []
    for row in list(combined.get("action_plan") or [])[:5]:
        if not isinstance(row, dict):
            continue
        actions.append({
            "priority": row.get("priority"),
            "title": row.get("title"),
            "problem": str(row.get("problem") or "")[:80],
            "method": str(row.get("method") or "")[:100],
        })
    overview = combined.get("score_overview") or {}
    return {
        "diagnosis": str((overview.get("diagnosis") if isinstance(overview, dict) else "") or "")[:220],
        "highlights": [
            str(item)[:80] for item in list(combined.get("highlights") or [])[:4]
        ],
        "critical_issues": [
            str(item)[:100] for item in list(combined.get("critical_issues") or [])[:5]
        ],
        "action_plan": actions,
    }


def _build_stage_a_prompt(fact_pack: dict) -> str:
    pack = _stage_pack_a(fact_pack)
    auth = pack.get("authoritativeScore") or {}
    return (
        "【阶段A：诊断与行动】\n"
        f"权威总分={auth.get('overallScore')}（不可改写，不得输出 overall_score 字段）。\n"
        "只输出JSON，字段：score_overview{diagnosis,highlights,key_issues},"
        "highlights[], critical_issues[], evidence_audit[], action_plan[],"
        "improvement_priorities[], team_optimization[]。\n"
        "action_plan 项：priority,title,problem,method,owner,timebox,acceptance,observation_codes[]。\n"
        "要求：诊断解释为什么是这个分；关键问题优先对应 topLosses；行动可执行且可验收；禁止 expected_gain/分数改写。\n"
        f"记忆与账本：{_lean_json(pack)}\n"
    )


def _build_stage_b_prompt(
    fact_pack: dict,
    stage_a_snapshot: dict,
    assigned_personas: list[dict] | None = None,
) -> str:
    """Legacy combined B prompt (tests / tools). Prefer B1+B2."""
    return _build_stage_b1_prompt(
        fact_pack, stage_a_snapshot, assigned_personas=assigned_personas
    )


def _build_stage_b1_prompt(
    fact_pack: dict,
    stage_a_snapshot: dict,
    assigned_personas: list[dict] | None = None,
) -> str:
    pack = _stage_pack_b(fact_pack, stage_a_snapshot)
    roster = _persona_roster_for_prompt(assigned_personas or fact_pack.get("assignedJury") or [])
    pack["assignedJury"] = roster
    auth = pack.get("authoritativeScore") or {}
    codes = ",".join(str(row.get("judge_code") or "") for row in roster)
    return (
        "【阶段B1：九评委独立评审】\n"
        f"权威总分={auth.get('overallScore')}（不可改写；score 为诊断分，建议权威分±8）。\n"
        f"本场评委已从人格库抽样（共{len(roster)}位），必须且只能按 assignedJury 名单输出，"
        f"judge_code 顺序与集合必须完全一致：{codes}。禁止自创、替换、遗漏人格。\n"
        "只输出 JSON：{\"jury_review\":[...]}。\n"
        "每项字段：judge_code,judge_type,score,focus,rubric_focus,"
        "comment(<=80字),recognition(<=40字),concern(<=40字),challenge_question(<=50字)。\n"
        "judge_type 使用名单中的 name；focus 对齐 short_label/prompt_modifier。\n"
        "每位评委关注点不同，必须指向真实亮点或账本缺口。\n"
        f"输入：{_lean_json(pack)}\n"
    )


def _build_stage_b2_prompt(
    fact_pack: dict,
    stage_a_snapshot: dict,
    jury_snapshot: list[dict],
) -> str:
    pack = {
        "authoritativeScore": fact_pack.get("authoritativeScore") or {},
        "runningSummary": fact_pack.get("runningSummary") or "",
        "topLosses": list(fact_pack.get("topLosses") or [])[:6],
        "stageA": stage_a_snapshot,
        "jurySnapshot": jury_snapshot,
    }
    auth = pack.get("authoritativeScore") or {}
    return (
        "【阶段B2：结构复盘与总评】\n"
        f"权威总分={auth.get('overallScore')}（不可改写）。\n"
        "只输出 JSON 字段：audio_visual_fusion{summary,contradictions[],metrics[]},"
        "pitch_structure_benchmark[{section,score_or_level,comment}],"
        "judge_questioning[{judge_type,focus,question,why_it_matters,prep_evidence}](4-6条),"
        "final_verdict{summary,jury_summary,defensible_strengths[],critical_deductions[],next_round_focus[],priority_actions[]},"
        "evidence_summary{covered[],missing[],risks[]}。\n"
        "文案简洁，直接可给教练用。\n"
        f"输入：{_lean_json(pack)}\n"
    )


def _jury_snapshot_for_b2(jury: list) -> list[dict]:
    rows = []
    for row in jury[:9]:
        if not isinstance(row, dict):
            continue
        rows.append({
            "judge_code": row.get("judge_code"),
            "judge_type": row.get("judge_type"),
            "score": row.get("score"),
            "focus": row.get("focus"),
            "concern": str(row.get("concern") or "")[:60],
        })
    return rows


def _as_text_list(items, *, limit: int = 12) -> list[str]:
    out: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(
                item.get("description")
                or item.get("title")
                or item.get("issue")
                or item.get("text")
                or item.get("summary")
                or ""
            ).strip()
            if not text and item.get("observationCode"):
                text = str(item.get("observationCode"))
        else:
            text = str(item or "").strip()
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _select_report_jury_personas(
    *,
    meeting_id: str | None,
    rule_payload: dict | None,
    project_info: dict | None,
    ai_score: dict | None,
) -> tuple[list[dict], dict[str, Any]]:
    """Sample N personas from the backend/local pool — same mechanism as AI jury."""
    from app.services.jury.persona_repository import load_personas
    from app.services.jury.personas import select_personas

    count = max(1, int(getattr(settings, "AI_JURY_COUNT", 9) or 9))
    seed = _jury_selection_seed(
        meeting_id=meeting_id,
        rule_payload=rule_payload,
        project_info=project_info,
        ai_score=ai_score,
    )
    pool = [persona for persona in load_personas() if persona.get("enabled", True)]
    if not pool:
        from app.services.jury.personas import PERSONAS

        pool = [dict(item) for item in PERSONAS]
    selected = select_personas(seed, count=min(count, len(pool)), pool=pool)
    meta = {
        "seed": seed,
        "pool_size": len(pool),
        "selected_count": len(selected),
        "selected_codes": [str(item.get("code") or "") for item in selected],
        "source": "persona_pool_sample",
    }
    return selected, meta


def _jury_selection_seed(
    *,
    meeting_id: str | None,
    rule_payload: dict | None,
    project_info: dict | None,
    ai_score: dict | None,
) -> str:
    # Align with independent jury review sessions when meeting_id is known.
    if meeting_id:
        return f"{meeting_id}:ai_jury_v1"
    score_instance = None
    if isinstance(rule_payload, dict):
        score_instance = rule_payload.get("scoreInstanceId") or rule_payload.get("score_instance_id")
    if not score_instance and isinstance(ai_score, dict):
        score_instance = ai_score.get("score_instance_id") or ai_score.get("scoreInstanceId")
    if score_instance:
        return f"score:{score_instance}:ai_jury_v1"
    project_name = ""
    if isinstance(project_info, dict):
        project_name = str(
            project_info.get("project_name") or project_info.get("projectName") or ""
        )
    fingerprint = ""
    if isinstance(rule_payload, dict):
        fingerprint = str(
            rule_payload.get("ruleFingerprint")
            or rule_payload.get("scoringFingerprint")
            or ""
        )
    return f"anon:{project_name}:{fingerprint}:ai_jury_v1"


def _persona_roster_for_prompt(personas: list[dict] | None) -> list[dict[str, Any]]:
    rows = []
    for persona in personas or []:
        if not isinstance(persona, dict):
            continue
        code = str(persona.get("code") or persona.get("judge_code") or "").strip()
        if not code:
            continue
        profile = persona.get("judge_profile") or {}
        rows.append({
            "seat_no": persona.get("seat_no") or len(rows) + 1,
            "judge_code": code,
            "name": persona.get("name") or persona.get("role_label") or code,
            "short_label": persona.get("short_label") or profile.get("short_label") or "",
            "focus_dimensions": list(persona.get("focus_dimensions") or [])[:4],
            "prompt_modifier": str(persona.get("prompt_modifier") or "")[:120],
            "display_name": persona.get("display_name") or f"{code}",
        })
    return rows


def _persona_by_code(personas: list[dict] | None) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    for persona in personas or []:
        if not isinstance(persona, dict):
            continue
        code = str(persona.get("code") or persona.get("judge_code") or "").strip().upper()
        if code:
            mapping[code] = persona
    return mapping


def _validate_stage_a(payload: dict, fact_pack: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("stage_a_not_object")
    overview = payload.get("score_overview")
    if not isinstance(overview, dict) or len(str(overview.get("diagnosis") or "").strip()) < 24:
        raise ValueError("stage_a_diagnosis_incomplete")
    payload["highlights"] = _as_text_list(payload.get("highlights"))
    payload["critical_issues"] = _as_text_list(payload.get("critical_issues"))
    if not payload["highlights"]:
        raise ValueError("stage_a_highlights_incomplete")
    if not payload["critical_issues"]:
        raise ValueError("stage_a_critical_incomplete")
    if not isinstance(payload.get("action_plan"), list) or not payload["action_plan"]:
        raise ValueError("stage_a_action_plan_incomplete")
    if not isinstance(payload.get("improvement_priorities"), list) or not payload["improvement_priorities"]:
        raise ValueError("stage_a_priorities_incomplete")
    payload["action_plan"] = _clean_actions(payload.get("action_plan"), fact_pack)
    if not payload["action_plan"]:
        raise ValueError("stage_a_action_plan_empty")
    payload.setdefault("team_optimization", [])
    payload.setdefault("evidence_audit", [])
    return payload


def _validate_stage_b(
    payload: dict,
    rule_payload: dict,
    assigned_personas: list[dict] | None = None,
) -> dict:
    """Legacy combined B validator."""
    payload = _validate_stage_b1(payload, rule_payload, assigned_personas=assigned_personas)
    return _validate_stage_b2(payload, rule_payload)


def _validate_stage_b1(
    payload: dict,
    rule_payload: dict,
    assigned_personas: list[dict] | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("stage_b_not_object")
    jury = payload.get("jury_review")
    expected_count = len(assigned_personas) if assigned_personas else 9
    if not isinstance(jury, list) or not jury:
        raise ValueError("stage_b_jury_incomplete")

    by_code: dict[str, dict] = {}
    for row in jury:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        for key in ("comment", "recognition", "concern", "challenge_question", "focus", "rubric_focus"):
            if key in item:
                item[key] = str(item.get(key) or "").strip()
        code = str(item.get("judge_code") or "").strip().upper()
        if not code:
            continue
        item["judge_code"] = code
        by_code[code] = item

    if assigned_personas:
        ordered = []
        persona_map = _persona_by_code(assigned_personas)
        for persona in assigned_personas:
            code = str(persona.get("code") or "").strip().upper()
            if not code:
                continue
            item = by_code.get(code)
            if not item:
                raise ValueError(f"stage_b_jury_missing_assigned:{code}")
            # Lock identity fields to the sampled persona roster.
            item["judge_code"] = code
            item["judge_type"] = (
                persona.get("name")
                or persona.get("role_label")
                or item.get("judge_type")
                or f"{code}评委"
            )
            if not item.get("focus"):
                item["focus"] = persona.get("short_label") or ""
            if not item.get("rubric_focus"):
                dims = persona.get("focus_dimensions") or []
                item["rubric_focus"] = "、".join(str(d) for d in dims[:3]) if dims else item.get("focus")
            item["seat_no"] = persona.get("seat_no")
            item["display_name"] = persona.get("display_name") or f"{code}"
            item["persona_source"] = "pool_sample"
            ordered.append(item)
        if len(ordered) < expected_count:
            raise ValueError("stage_b_jury_less_than_assigned")
        payload["jury_review"] = ordered
        return payload

    # No assigned roster (legacy tests): keep unique rows, pad identity lightly.
    cleaned = []
    seen = set()
    for row in jury:
        if not isinstance(row, dict):
            continue
        code = str(row.get("judge_code") or "").strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        item = dict(row)
        item["judge_code"] = code
        if not str(item.get("judge_type") or "").strip():
            item["judge_type"] = f"{code}评委"
        cleaned.append(item)
        if len(cleaned) >= expected_count:
            break
    if len(cleaned) < expected_count:
        raise ValueError("stage_b_jury_less_than_9")
    payload["jury_review"] = cleaned
    return payload


def _validate_stage_b2(payload: dict, rule_payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("stage_b2_not_object")
    if not isinstance(payload.get("final_verdict"), dict):
        raise ValueError("stage_b_final_verdict_incomplete")
    summary = str((payload.get("final_verdict") or {}).get("summary") or "").strip()
    if len(summary) < 12:
        raise ValueError("stage_b_final_summary_shallow")
    payload.setdefault(
        "audio_visual_fusion",
        {"summary": "本轮以转写与证据账本为主做保守融合判断。", "contradictions": [], "metrics": []},
    )
    payload.setdefault("pitch_structure_benchmark", [])
    payload.setdefault("judge_questioning", [])
    payload.setdefault("evidence_summary", {})
    return payload


def _clean_actions(action_plan, fact_pack: dict) -> list[dict]:
    allowed = set(fact_pack.get("allowedObservationCodes") or [])
    cleaned = []
    for row in action_plan or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        codes = []
        raw_codes = item.get("observation_codes") or item.get("observationCodes") or item.get("observationCode")
        if isinstance(raw_codes, list):
            codes = [str(code) for code in raw_codes if str(code) in allowed]
        elif raw_codes and str(raw_codes) in allowed:
            codes = [str(raw_codes)]
        item["observation_codes"] = codes
        if codes and not item.get("observationCode"):
            item["observationCode"] = codes[0]
        for key in list(item.keys()):
            lower = key.lower()
            if ("score" in lower or "gain" in lower or "recover" in lower) and key not in {
                "observationCode",
                "observation_codes",
            }:
                item.pop(key, None)
        if not str(item.get("method") or item.get("action") or "").strip():
            continue
        if not str(item.get("title") or item.get("problem") or "").strip():
            continue
        cleaned.append(item)
    return cleaned[:12]


def _fallback_final_verdict(stage_a: dict, rule_payload: dict) -> dict:
    highlights = list(stage_a.get("highlights") or [])[:3] or ["已完成完整路演展示"]
    issues = list(stage_a.get("critical_issues") or [])[:3] or ["关键证据仍需补齐"]
    score = rule_payload.get("finalScore")
    return {
        "summary": f"权威综合分 {score} 分。{highlights[0]}，但{issues[0]}。",
        "jury_summary": "九评委阶段未完整生成，以下结论以账本与阶段A诊断为准。",
        "defensible_strengths": highlights,
        "critical_deductions": issues,
        "next_round_focus": issues[:2],
        "priority_actions": [
            {
                "priority": "P0",
                "item": (stage_a.get("action_plan") or [{}])[0].get("title") or "补齐关键证据",
                "owner": "项目负责人",
                "acceptance": (stage_a.get("action_plan") or [{}])[0].get("acceptance") or "下一轮可核验",
            }
        ],
    }


def _fallback_jury_review(
    stage_a: dict,
    rule_payload: dict,
    assigned_personas: list[dict] | None = None,
) -> list[dict]:
    score = float(rule_payload.get("finalScore") or 0)
    highlights = list(stage_a.get("highlights") or ["完成路演"]) or ["完成路演"]
    issues = list(stage_a.get("critical_issues") or ["证据不足"]) or ["证据不足"]
    personas = list(assigned_personas or [])
    if not personas:
        # Last-resort sample so fallback still comes from the pool, not a fixed set.
        try:
            personas, _ = _select_report_jury_personas(
                meeting_id=None,
                rule_payload=rule_payload,
                project_info=None,
                ai_score=None,
            )
        except Exception:
            from app.services.jury.personas import PERSONAS, select_personas

            personas = select_personas("fallback:ai_jury_v1", count=9, pool=PERSONAS)
    rows = []
    for idx, persona in enumerate(personas):
        code = str(persona.get("code") or f"J{idx+1}").strip().upper()
        label = persona.get("name") or persona.get("role_label") or f"{code}评委"
        focus = persona.get("short_label") or "综合表现"
        rows.append({
            "judge_code": code,
            "judge_type": label,
            "score": round(max(0, min(100, score + (idx % 3 - 1) * 2)), 1),
            "focus": focus,
            "rubric_focus": "、".join(str(d) for d in list(persona.get("focus_dimensions") or [])[:3]) or focus,
            "comment": f"认可{highlights[idx % len(highlights)]}，需追问{issues[idx % len(issues)]}。",
            "recognition": highlights[idx % len(highlights)],
            "concern": issues[idx % len(issues)],
            "challenge_question": f"请用证据说明：{issues[idx % len(issues)]}如何在下一轮闭环？",
            "score_authority": "diagnostic_only",
            "seat_no": persona.get("seat_no") or idx + 1,
            "display_name": persona.get("display_name") or f"{idx + 1}号评委 {code}",
            "persona_source": "pool_sample_fallback",
        })
    return rows


def _validate_and_lock_report(payload: dict, rule_payload: dict, fact_pack: dict) -> dict:
    """Legacy single-shot validator kept for tests/tools."""
    if not isinstance(payload, dict):
        raise ValueError("report_not_object")
    payload = _validate_stage_a(payload, fact_pack)
    if "final_verdict" in payload or "jury_review" in payload:
        # soft path for combined payloads
        if not isinstance(payload.get("final_verdict"), dict):
            payload["final_verdict"] = _fallback_final_verdict(payload, rule_payload)
        if not isinstance(payload.get("jury_review"), list) or len(payload.get("jury_review") or []) < 9:
            payload["jury_review"] = _fallback_jury_review(payload, rule_payload)
    payload["overall_score"] = rule_payload.get("finalScore")
    payload["score_authority"] = "structured_rule_engine"
    return payload


def _merge_locked_report(base: dict, payload: dict, rule_payload: dict) -> dict:
    merged = deepcopy(base)
    for field in _PROSE_FIELDS:
        if field in payload and payload[field] not in (None, [], {}):
            merged[field] = payload[field]

    # Always freeze score truth from rule engine.
    merged["overall_score"] = rule_payload.get("finalScore")
    merged["raw_overall_score"] = rule_payload.get("llmRawScore", merged.get("raw_overall_score"))
    dim_scores = rule_payload.get("dimensionScores") or {}
    dim_max = rule_payload.get("dimensionMaxScores") or {}
    if dim_scores:
        merged["dimensions"] = {
            code: {
                "score": score,
                "max_score": dim_max.get(code),
                "source": "structured_rule_engine",
                "name": code,
            }
            for code, score in dim_scores.items()
        }

    # Jury scores are diagnostic only and should orbit the official total.
    official = float(rule_payload.get("finalScore") or 0)
    jury = merged.get("jury_review")
    if isinstance(jury, list):
        fixed_jury = []
        for index, row in enumerate(jury):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            try:
                model_score = float(item.get("score"))
            except (TypeError, ValueError):
                model_score = official
            # Clamp diagnostic jury score near official score to avoid dual-score illusion.
            item["score"] = round(max(0.0, min(100.0, official + max(-8.0, min(8.0, model_score - official)))), 1)
            item["score_authority"] = "diagnostic_only"
            fixed_jury.append(item)
        if fixed_jury:
            merged["jury_review"] = fixed_jury

    overview = merged.get("score_overview")
    if isinstance(overview, dict):
        overview = dict(overview)
        overview["total_score"] = rule_payload.get("finalScore")
        overview["authority"] = "structured_rule_engine"
        # Ensure diagnosis mentions the official score once.
        diagnosis = str(overview.get("diagnosis") or "")
        official_text = str(rule_payload.get("finalScore"))
        if official_text and official_text not in diagnosis:
            overview["diagnosis"] = f"权威综合分 {official_text} 分。{diagnosis}"
        merged["score_overview"] = overview

    final_verdict = merged.get("final_verdict")
    if isinstance(final_verdict, dict):
        final_verdict = dict(final_verdict)
        final_verdict["score_authority"] = "structured_rule_engine"
        merged["final_verdict"] = final_verdict

    return merged
