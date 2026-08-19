"""Build user-facing scoring narrative from the authoritative rule ledger.

LLM stages may still produce diagnostic prose, but once a structured rule score
exists, the official total, dimensions, issues, priorities and action seeds must
come from the ledger — not from a second free-scoring pass.
"""

from __future__ import annotations

from copy import deepcopy


_NARRATIVE_VERSION = "rule-ledger-narrative-v1"
_LOSS_PRIORITY = {
    "hard_violation": 0,
    "evidence_limited": 1,
    "performance_gap": 2,
    "unresolved_gap": 3,
}


def apply_rule_ledger_narrative(
    ai_score: dict | None,
    rule_payload: dict | None,
    *,
    evidence_extraction: dict | None = None,
) -> dict:
    """Return ai_score with official score fields rewritten from rule payload."""
    source = deepcopy(ai_score or {})
    payload = rule_payload or {}
    if payload.get("scoreAuthority") != "structured_rule_engine":
        source.setdefault("score_authority", source.get("score_authority") or "legacy_llm")
        return source

    final_score = payload.get("finalScore")
    llm_raw = payload.get("llmRawScore")
    if llm_raw is None:
        llm_raw = source.get("raw_overall_score", source.get("overall_score"))

    source["overall_score"] = final_score
    source["raw_overall_score"] = llm_raw
    source["score_authority"] = "structured_rule_engine"
    source["narrative_source"] = _NARRATIVE_VERSION
    source["rule_engine_score"] = payload.get("ruleEngineScore", final_score)
    source["score_diff"] = payload.get("scoreDiff")
    source["scoring_fingerprint"] = payload.get("scoringFingerprint")
    source["rule_fingerprint"] = payload.get("ruleFingerprint") or payload.get("scoringFingerprint")
    source["evidence_snapshot_hash"] = payload.get("evidenceSnapshotHash")
    source["score_instance_id"] = payload.get("scoreInstanceId")

    dimensions = _dimensions_from_rule(payload)
    if dimensions:
        source["dimensions"] = dimensions

    observations = list(payload.get("observations") or [])
    loss_ledger = [
        row for row in list(payload.get("lossLedger") or [])
        if isinstance(row, dict) and float(row.get("points") or 0) > 0
    ]
    sorted_losses = sorted(
        loss_ledger,
        key=lambda row: (
            _LOSS_PRIORITY.get(str(row.get("lossType") or ""), 9),
            -float(row.get("points") or 0),
            str(row.get("causeCode") or ""),
        ),
    )

    highlights = _highlights_from_observations(observations)
    if highlights:
        source["highlights"] = highlights

    critical = _critical_issues_from_losses(sorted_losses)
    if critical:
        source["critical_issues"] = critical

    priorities = _improvement_priorities_from_losses(sorted_losses)
    if priorities:
        source["improvement_priorities"] = priorities

    action_plan = _action_plan_from_losses(sorted_losses, source.get("action_plan"))
    if action_plan:
        source["action_plan"] = action_plan

    source["score_overview"] = _score_overview(payload, final_score, evidence_extraction)

    generation_meta = dict(source.get("generation_meta") or {})
    generation_meta["narrative"] = {
        "status": "completed",
        "source": _NARRATIVE_VERSION,
        "lossItemCount": len(sorted_losses),
        "observationCount": len(observations),
    }
    source["generation_meta"] = generation_meta
    # Deep jury prose may remain for reading, but must not claim scoring authority.
    if source.get("jury_review") and isinstance(source["jury_review"], dict):
        source["jury_review"] = {
            **source["jury_review"],
            "score_authority": "diagnostic_only",
            "note": "评审团文字为诊断参考，正式分以规则引擎账本为准",
        }
    return source


def apply_rule_ledger_to_pipeline_result(result: dict) -> dict:
    """In-place friendly helper for the scoring pipeline after evidence extraction."""
    pipeline = dict(result or {})
    evidence_extraction = pipeline.get("evidence_extraction") or {}
    if not evidence_extraction:
        return pipeline

    quality = evidence_extraction.get("extractionQuality") or {}
    not_publishable = (
        evidence_extraction.get("status") in {"failed", "review_required"}
        or quality.get("publicationEligible") is False
    )
    if not_publishable:
        ai_score = dict(pipeline.get("ai_score") or {})
        ai_score["score_authority"] = "review_required"
        ai_score["narrative_source"] = "evidence_extraction_not_publishable"
        pipeline["ai_score"] = ai_score
        return pipeline

    from app.services.pipeline_payloads import build_rule_engine_shadow_payload

    try:
        shadow = build_rule_engine_shadow_payload(pipeline)
    except Exception:
        return pipeline

    pipeline["rule_engine_shadow"] = shadow
    if shadow.get("scoreAuthority") != "structured_rule_engine":
        return pipeline

    pipeline["ai_score"] = apply_rule_ledger_narrative(
        pipeline.get("ai_score") or {},
        shadow,
        evidence_extraction=evidence_extraction,
    )
    return pipeline


def _dimensions_from_rule(payload: dict) -> dict:
    scores = payload.get("dimensionScores") or {}
    max_scores = payload.get("dimensionMaxScores") or {}
    if not scores:
        return {}
    result = {}
    for code, score in scores.items():
        result[str(code)] = {
            "score": score,
            "max_score": max_scores.get(code),
            "source": "structured_rule_engine",
            "name": str(code),
        }
    return result


def _highlights_from_observations(observations: list[dict]) -> list[str]:
    highlights = []
    ranked = sorted(
        [row for row in observations if isinstance(row, dict)],
        key=lambda row: (
            -(float(row.get("finalScore") or 0) / max(float(row.get("maxScore") or 1), 1e-6)),
            str(row.get("observationCode") or ""),
        ),
    )
    for row in ranked:
        max_score = float(row.get("maxScore") or 0)
        final_score = float(row.get("finalScore") or 0)
        if max_score <= 0 or final_score / max_score < 0.8:
            continue
        name = row.get("observationName") or row.get("observationCode") or "观测点"
        level = row.get("evidenceLevel") or "—"
        highlights.append(
            f"{name}表现较好（{final_score:.1f}/{max_score:.1f}，证据等级 {level}）"
        )
        if len(highlights) >= 5:
            break
    return highlights


def _critical_issues_from_losses(sorted_losses: list[dict]) -> list[str]:
    issues = []
    for row in sorted_losses:
        points = float(row.get("points") or 0)
        if points <= 0:
            continue
        if row.get("lossType") != "hard_violation" and points < 2.0:
            continue
        name = row.get("observationName") or row.get("observationCode") or "观测点"
        reason = str(row.get("reason") or row.get("lossType") or "存在失分").strip()
        issues.append(f"{name}：{reason}（-{points:.1f}）")
        if len(issues) >= 8:
            break
    return issues


def _improvement_priorities_from_losses(sorted_losses: list[dict]) -> list[dict]:
    priorities = []
    for index, row in enumerate(sorted_losses[:8], start=1):
        loss_type = str(row.get("lossType") or "")
        name = row.get("observationName") or row.get("observationCode") or "观测点"
        if loss_type == "evidence_limited":
            suggestion = f"补齐{name}的可定位、可复核证据链"
        elif loss_type == "hard_violation":
            suggestion = f"消除{name}对应的规则违规风险并准备验收材料"
        else:
            suggestion = f"提升{name}的现场演示完整度与达成度"
        priorities.append({
            "priority": index,
            "dimension": row.get("dimensionCode") or "",
            "issue": row.get("reason") or f"{name}尚未达到满分要求",
            "suggestion": suggestion,
            "observationCode": row.get("observationCode"),
            "lossType": loss_type,
            "covered_points": float(row.get("points") or 0),
        })
    return priorities


def _action_plan_from_losses(sorted_losses: list[dict], existing_plan) -> list[dict]:
    """Prefer ledger-seeded actions; keep model wording only when it already links observations."""
    existing = [row for row in list(existing_plan or []) if isinstance(row, dict)]
    linked_existing = []
    for row in existing:
        if (
            row.get("observationCode")
            or row.get("observationCodes")
            or row.get("coveredLossIds")
            or row.get("sourceIssueKey")
        ):
            linked_existing.append(row)
    if linked_existing:
        # Keep model actions that already claim a scoring link; ledger fallback fills gaps later.
        return linked_existing[:12]

    actions = []
    for row in sorted_losses[:12]:
        loss_type = str(row.get("lossType") or "performance_gap")
        name = row.get("observationName") or row.get("observationCode") or "观测点"
        points = float(row.get("points") or 0)
        if loss_type == "evidence_limited":
            title = f"补齐{name}的可核验证据"
            method = str(row.get("trainingTaskTemplate") or "").strip() or (
                f"围绕{name}补齐过程记录、结果材料和可定位证据。"
            )
        elif loss_type == "hard_violation":
            title = f"消除{name}的规则违规风险"
            method = str(row.get("trainingTaskTemplate") or "").strip() or (
                f"针对{name}的违规触发事实完成整改，并准备下一轮验收说明。"
            )
        else:
            title = f"提升{name}的现场达成度"
            method = str(row.get("trainingTaskTemplate") or "").strip() or (
                f"围绕{name}补齐演示、讲解与结果闭环，确保现场可核验。"
            )
        actions.append({
            "priority": "P0" if points >= 5 else "P1" if points >= 2 else "P2",
            "title": title,
            "problem": row.get("reason") or f"{name}尚未达到规则要求",
            "method": method,
            "observationCode": row.get("observationCode"),
            "observationCodes": [row.get("observationCode")] if row.get("observationCode") else [],
            "sourceIssueKey": row.get("causeCode") or row.get("penaltyRuleCode") or row.get("observationCode"),
            "lossTypes": [loss_type],
            "sourceKind": "rule-ledger-narrative",
        })
    return actions


def _score_overview(payload: dict, final_score, evidence_extraction: dict | None) -> dict:
    reconciliation = payload.get("reconciliation") or {}
    total_loss = reconciliation.get("totalLoss")
    if total_loss is None and final_score is not None:
        total_loss = round(100.0 - float(final_score), 1)
    track = ""
    if isinstance(evidence_extraction, dict):
        track = evidence_extraction.get("trackName") or evidence_extraction.get("trackId") or ""
    return {
        "total_score": final_score,
        "authority": "structured_rule_engine",
        "diagnosis": (
            f"{'赛道 ' + str(track) + '：' if track else ''}"
            f"规则引擎权威分 {final_score} 分，距离满分差距约 {total_loss} 分；"
            f"表现差距 {payload.get('performanceGap')}，"
            f"证据上限 {payload.get('evidenceLimitedGap')}，"
            f"硬性处罚 {payload.get('effectiveHardPenalty')}。"
            "正式分以失分账本为准，大模型文字仅作解释参考。"
        ),
        "performance_gap": payload.get("performanceGap"),
        "evidence_limited_gap": payload.get("evidenceLimitedGap"),
        "effective_hard_penalty": payload.get("effectiveHardPenalty"),
        "total_loss": total_loss,
    }
