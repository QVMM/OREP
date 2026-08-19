"""Rule-backed score impact ranges for actionable coaching tasks.

The model may describe an action, but only the deterministic rule executor may
publish the score impact shown to users.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher
import re

from app.services.scoring.rule_executor import execute_rule_score


_CALCULATION_VERSION = "score-impact-v1"
_GOAL_SCORE = 100.0
_PERFORMANCE_LEVELS = (0.0, 0.3, 0.5, 0.8, 1.0)
_MODEL_SCORE_FIELDS = {
    "expected_gain",
    "expectedGain",
    "expected_recover_points",
    "expectedRecoverPoints",
    "recoverableScore",
    "recoverable_score",
}
_EVIDENCE_HINTS = ("证据", "来源", "报告", "证明", "数据", "材料", "授权", "license", "知识产权", "测试")
_PERFORMANCE_HINTS = ("表达", "语速", "节奏", "演示", "讲解", "稳定", "临场", "说服", "操作")


def build_score_impact_projection(
    action_plan,
    observations,
    deductions,
    *,
    loss_ledger=None,
    rule_hash=None,
    scoring_fingerprint=None,
):
    """Return a normalized action plan and its rule-backed portfolio projection."""

    tasks = [_without_model_score_claims(item) for item in list(action_plan or []) if isinstance(item, dict)]
    canonical_observations = [
        deepcopy(item)
        for item in list(observations or [])
        if isinstance(item, dict) and str(item.get("observationCode") or "").strip()
    ]
    canonical_deductions = [deepcopy(item) for item in list(deductions or []) if isinstance(item, dict)]
    canonical_losses = [deepcopy(item) for item in list(loss_ledger or []) if isinstance(item, dict)]
    use_loss_contract = loss_ledger is not None
    loss_by_id = {
        str(item.get("lossId")): item
        for item in canonical_losses
        if str(item.get("lossId") or "").strip()
    }
    if not canonical_observations:
        return (
            [_with_unlinked_impact(item, "no_scoring_rule_link") for item in tasks],
            _empty_projection(
                len(tasks),
                rule_hash,
                scoring_fingerprint,
                use_loss_contract=use_loss_contract,
            ),
        )

    baseline = execute_rule_score(canonical_observations, canonical_deductions)
    current_score = _round1(baseline.get("finalScore"))
    observation_map = {
        str(item.get("observationCode")).strip(): item
        for item in baseline.get("observations", [])
    }
    scored_tasks = []
    portfolio_lower = _empty_scenario()
    portfolio_upper = _empty_scenario()

    for task in tasks:
        covered_losses = _covered_losses(task, loss_by_id) if use_loss_contract else []
        if use_loss_contract:
            observation_codes = _unique_strings(
                row.get("observationCode") for row in covered_losses
                if str(row.get("observationCode") or "") in observation_map
            )
            matched_deductions = _deductions_for_losses(covered_losses, canonical_deductions)
        else:
            observation_codes, matched_deductions = _resolve_task_links(
                task,
                observation_map,
                canonical_deductions,
            )
        enriched = dict(task)
        if use_loss_contract:
            enriched["coveredLossIds"] = [row["lossId"] for row in covered_losses]
            enriched["coveredGapPoints"] = _round1(sum(float(row.get("points") or 0) for row in covered_losses))
            enriched["observationCodes"] = observation_codes
        if not observation_codes:
            scored_tasks.append(_with_unlinked_impact(enriched, "no_scoring_rule_link"))
            continue

        if use_loss_contract:
            impact_type = _impact_type_for_losses(covered_losses)
            lower_scenario, upper_scenario = _build_loss_scenarios(
                covered_losses,
                observation_map,
                matched_deductions,
            )
        else:
            impact_type = _resolve_impact_type(task, observation_codes, observation_map, matched_deductions)
            lower_scenario, upper_scenario = _build_task_scenarios(
                impact_type,
                observation_codes,
                observation_map,
                matched_deductions,
            )
        lower_score = _score_scenario(canonical_observations, canonical_deductions, lower_scenario)
        upper_score = _score_scenario(canonical_observations, canonical_deductions, upper_scenario)
        lower_gain = max(0.0, _round1(lower_score - current_score))
        upper_gain = max(lower_gain, _round1(upper_score - current_score))
        if upper_gain <= 0:
            scored_tasks.append(_with_unlinked_impact(enriched, "no_rule_backed_score_gain"))
            continue

        dimension_codes = {
            str(observation_map[code].get("dimensionCode") or "").strip()
            for code in observation_codes
            if code in observation_map
        }
        dimension_codes.discard("")
        criterion_codes = _as_strings(task.get("criterionCodes") or task.get("criterion_codes"))
        budget_keys = (
            _unique_strings(row.get("scoreBudgetKey") for row in covered_losses)
            if use_loss_contract
            else [f"{code}:{impact_type}" for code in observation_codes]
        )
        enriched["observationCodes"] = observation_codes
        if len(observation_codes) == 1:
            enriched["observationCode"] = observation_codes[0]
        enriched["scoreImpact"] = {
            "impactType": impact_type,
            "lower": lower_gain,
            "upper": upper_gain,
            "predictedScoreAfterLower": _round1(current_score + lower_gain),
            "predictedScoreAfterUpper": _round1(current_score + upper_gain),
            "scoreLinkStatus": "linked",
            "observationCodes": observation_codes,
            "criterionCodes": criterion_codes,
            "dimensionCode": next(iter(dimension_codes)) if len(dimension_codes) == 1 else None,
            "scoreBudgetKeys": budget_keys,
            "calculationVersion": "score-impact-v2" if use_loss_contract else _CALCULATION_VERSION,
            "ruleHash": rule_hash,
        }
        scored_tasks.append(enriched)
        _merge_scenario(portfolio_lower, lower_scenario)
        _merge_scenario(portfolio_upper, upper_scenario)

    linked_count = sum(
        1
        for item in scored_tasks
        if (item.get("scoreImpact") or {}).get("scoreLinkStatus") == "linked"
    )
    if linked_count:
        portfolio_lower_score = _score_scenario(
            canonical_observations,
            canonical_deductions,
            portfolio_lower,
        )
        portfolio_upper_score = _score_scenario(
            canonical_observations,
            canonical_deductions,
            portfolio_upper,
        )
        gain_lower = max(0.0, _round1(portfolio_lower_score - current_score))
        gain_upper = max(gain_lower, _round1(portfolio_upper_score - current_score))
        predicted_lower = min(_GOAL_SCORE, _round1(current_score + gain_lower))
        predicted_upper = min(_GOAL_SCORE, _round1(current_score + gain_upper))
    else:
        gain_lower = gain_upper = 0.0
        predicted_lower = predicted_upper = current_score

    projection = {
        "goalScore": _GOAL_SCORE,
        "currentScore": current_score,
        "fullGap": max(0.0, _round1(_GOAL_SCORE - current_score)),
        "predictedScoreLower": predicted_lower,
        "predictedScoreUpper": predicted_upper,
        "predictedGainLower": gain_lower,
        "predictedGainUpper": gain_upper,
        "scoredTodoCount": linked_count,
        "unlinkedAdviceCount": len(scored_tasks) - linked_count,
        "calculationVersion": "score-impact-v2" if use_loss_contract else _CALCULATION_VERSION,
        "ruleHash": rule_hash,
        "scoringFingerprint": scoring_fingerprint,
    }
    if use_loss_contract:
        covered_loss_ids = {
            row["lossId"]
            for task in scored_tasks
            for row in _covered_losses(task, loss_by_id)
        }
        projection.update({
            "diagnosticTodoCount": len(scored_tasks) - linked_count,
            "scenarioScope": "all_known_tasks_minimum_acceptance",
            "coveredGapPoints": _round1(sum(
                float(loss_by_id[loss_id].get("points") or 0)
                for loss_id in covered_loss_ids
            )),
            "coverageRate": round(len(covered_loss_ids) / len(loss_by_id), 4) if loss_by_id else 1.0,
        })
    return scored_tasks, projection


def _covered_losses(task, loss_by_id):
    return [
        loss_by_id[loss_id]
        for loss_id in _as_strings(task.get("coveredLossIds"))
        if loss_id in loss_by_id
    ]


def _deductions_for_losses(losses, deductions):
    keys = {
        str(value)
        for loss in losses
        for value in (
            loss.get("deductionId"),
            loss.get("causeCode"),
            loss.get("penaltyRuleCode"),
        )
        if value
    }
    return [row for row in deductions if keys & _deduction_keys(row)]


def _impact_type_for_losses(losses):
    types = {str(row.get("lossType") or "") for row in losses}
    impacts = set()
    if "performance_gap" in types:
        impacts.add("performance_improvement")
    if "evidence_limited" in types:
        impacts.add("evidence_unlock")
    if "hard_violation" in types:
        impacts.add("deduction_recovery")
    return next(iter(impacts)) if len(impacts) == 1 else "mixed"


def _build_loss_scenarios(losses, observation_map, matched_deductions):
    lower = _empty_scenario()
    upper = _empty_scenario()
    type_to_impact = {
        "performance_gap": "performance_improvement",
        "evidence_limited": "evidence_unlock",
        "hard_violation": "deduction_recovery",
    }
    for loss_type, impact_type in type_to_impact.items():
        rows = [row for row in losses if row.get("lossType") == loss_type]
        if not rows:
            continue
        codes = _unique_strings(
            row.get("observationCode") for row in rows
            if str(row.get("observationCode") or "") in observation_map
        )
        task_lower, task_upper = _build_task_scenarios(
            impact_type,
            codes,
            observation_map,
            matched_deductions if loss_type == "hard_violation" else [],
        )
        _merge_scenario(lower, task_lower)
        _merge_scenario(upper, task_upper)
    return lower, upper


def _resolve_task_links(task, observation_map, deductions):
    explicit_codes = _as_strings(
        task.get("observationCodes")
        or task.get("observation_codes")
        or task.get("observationCode")
        or task.get("observation_code")
    )
    observation_codes = [code for code in explicit_codes if code in observation_map]
    source_key = str(task.get("sourceIssueKey") or task.get("source_issue_key") or "").strip()
    matched_deductions = [
        item
        for item in deductions
        if source_key and source_key in _deduction_keys(item)
    ]
    for item in matched_deductions:
        code = str(item.get("observationCode") or "").strip()
        if code in observation_map and code not in observation_codes:
            observation_codes.append(code)

    if not observation_codes:
        candidate = _best_text_observation(task, observation_map)
        if candidate:
            observation_codes.append(candidate)
    return observation_codes, matched_deductions


def _resolve_impact_type(task, observation_codes, observation_map, matched_deductions):
    requested = str(task.get("impactType") or task.get("impact_type") or "").strip().lower()
    aliases = {
        "deduction": "deduction_recovery",
        "deduction_recovery": "deduction_recovery",
        "recovery": "deduction_recovery",
        "evidence": "evidence_unlock",
        "evidence_unlock": "evidence_unlock",
        "performance": "performance_improvement",
        "performance_improvement": "performance_improvement",
    }
    if matched_deductions:
        return "deduction_recovery"
    if requested in aliases:
        return aliases[requested]

    text = _task_text(task).lower()
    evidence_hits = sum(hint in text for hint in _EVIDENCE_HINTS)
    performance_hits = sum(hint in text for hint in _PERFORMANCE_HINTS)
    has_evidence_bottleneck = any(
        float(observation_map[code].get("scoreCap") or 0)
        < float(observation_map[code].get("baseScore") or 0)
        for code in observation_codes
    )
    if evidence_hits > performance_hits and has_evidence_bottleneck:
        return "evidence_unlock"
    if performance_hits:
        return "performance_improvement"
    has_performance_gap = any(
        float(observation_map[code].get("performanceGap") or 0) > 0
        for code in observation_codes
    )
    return "performance_improvement" if has_performance_gap else "evidence_unlock"


def _build_task_scenarios(impact_type, observation_codes, observation_map, matched_deductions):
    lower = _empty_scenario()
    upper = _empty_scenario()
    if impact_type == "deduction_recovery":
        for item in matched_deductions:
            deduction_id = str(item.get("deductionId") or "").strip()
            allowed = min(
                float(item.get("deductedPoints") or 0),
                float(item.get("maxRecoverablePoints") or 0),
            )
            if deduction_id and allowed > 0:
                recovery = {
                    "sourceDeductionId": deduction_id,
                    "recoveryStatus": "verified",
                    "requestedRecoverPoints": allowed,
                }
                lower["recoveries"][deduction_id] = recovery
                upper["recoveries"][deduction_id] = recovery
        return lower, upper

    for code in observation_codes:
        observation = observation_map[code]
        max_score = float(observation.get("maxScore") or 0)
        base_score = float(observation.get("baseScore") or 0)
        score_cap = float(observation.get("scoreCap") or 0)
        if impact_type == "evidence_unlock":
            target_cap = min(max_score, base_score)
            lower_cap = score_cap + ((target_cap - score_cap) / 2)
            lower["observations"][code] = {"scoreCap": max(score_cap, lower_cap)}
            upper["observations"][code] = {"scoreCap": max(score_cap, target_cap)}
        else:
            current_ratio = base_score / max_score if max_score > 0 else 0
            lower_ratio = _next_level(current_ratio)
            upper_ratio = _next_level(lower_ratio)
            lower_base = max(base_score, max_score * lower_ratio)
            upper_base = max(lower_base, max_score * upper_ratio)
            lower["observations"][code] = {
                "baseScore": lower_base,
                "scoreCap": max(score_cap, lower_base),
            }
            upper["observations"][code] = {
                "baseScore": upper_base,
                "scoreCap": max(score_cap, upper_base),
            }
    return lower, upper


def _score_scenario(observations, deductions, scenario):
    changed = deepcopy(observations)
    changes = scenario.get("observations") or {}
    for item in changed:
        code = str(item.get("observationCode") or "").strip()
        item.update(changes.get(code) or {})
    recoveries = list((scenario.get("recoveries") or {}).values())
    return float(execute_rule_score(changed, deductions, recoveries).get("finalScore") or 0)


def _merge_scenario(target, source):
    for code, updates in (source.get("observations") or {}).items():
        current = target["observations"].setdefault(code, {})
        for field, value in updates.items():
            current[field] = max(float(current.get(field) or 0), float(value or 0))
    target["recoveries"].update(source.get("recoveries") or {})


def _best_text_observation(task, observation_map):
    title_text = _normalized_text(task.get("title"))
    task_text = _normalized_text(_task_text(task))
    if len(task_text) < 4:
        return None
    candidates = []
    for code, item in observation_map.items():
        observation_text = _normalized_text(" ".join(str(item.get(key) or "") for key in (
            "observationName",
            "performanceReason",
            "evidenceReason",
            "supportSummary",
        )))
        if not observation_text:
            continue
        candidates.append((
            _text_similarity(title_text, observation_text) if len(title_text) >= 4 else 0.0,
            _text_similarity(task_text, observation_text),
            code,
        ))
    if not candidates:
        return None

    # Legacy plans lack observation codes. Only accept a title-based inference
    # when one candidate is both materially similar and clearly ahead of the
    # runner-up; this keeps ambiguous coaching advice outside score promises.
    by_title = sorted(candidates, reverse=True)
    best_title, _, best_title_code = by_title[0]
    second_title = by_title[1][0] if len(by_title) > 1 else 0.0
    if best_title >= 0.25 and best_title - second_title >= 0.08:
        return best_title_code

    by_full_text = sorted(candidates, key=lambda item: item[1], reverse=True)
    _, best_full, best_full_code = by_full_text[0]
    second_full = by_full_text[1][1] if len(by_full_text) > 1 else 0.0
    if best_full >= 0.34 and best_full - second_full >= 0.08:
        return best_full_code
    return None


def _text_similarity(left, right):
    sequence = SequenceMatcher(None, left, right).ratio()
    left_pairs = _ngrams(left, 2)
    right_pairs = _ngrams(right, 2)
    overlap = len(left_pairs & right_pairs) / max(1, min(len(left_pairs), len(right_pairs)))
    return max(sequence, overlap)


def _task_text(task):
    return " ".join(str(task.get(key) or "") for key in (
        "title",
        "problem",
        "reason",
        "method",
        "acceptance",
    ))


def _normalized_text(value):
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(value or "").lower())


def _ngrams(value, size):
    return {value[index:index + size] for index in range(max(0, len(value) - size + 1))}


def _deduction_keys(item):
    return {
        str(item.get(key) or "").strip()
        for key in ("deductionId", "causeCode", "penaltyRuleCode", "deductionRuleCode")
        if str(item.get(key) or "").strip()
    }


def _next_level(current):
    for level in _PERFORMANCE_LEVELS:
        if level > current + 1e-9:
            return level
    return 1.0


def _without_model_score_claims(item):
    return {key: deepcopy(value) for key, value in item.items() if key not in _MODEL_SCORE_FIELDS}


def _with_unlinked_impact(task, reason):
    result = dict(task)
    result["scoreImpact"] = {
        "scoreLinkStatus": "unlinked",
        "lower": None,
        "upper": None,
        "reason": reason,
    }
    return result


def _empty_projection(unlinked_count, rule_hash, scoring_fingerprint, *, use_loss_contract=False):
    projection = {
        "goalScore": _GOAL_SCORE,
        "currentScore": None,
        "fullGap": None,
        "predictedScoreLower": None,
        "predictedScoreUpper": None,
        "predictedGainLower": None,
        "predictedGainUpper": None,
        "scoredTodoCount": 0,
        "unlinkedAdviceCount": unlinked_count,
        "calculationVersion": "score-impact-v2" if use_loss_contract else _CALCULATION_VERSION,
        "ruleHash": rule_hash,
        "scoringFingerprint": scoring_fingerprint,
    }
    if use_loss_contract:
        projection.update({
            "diagnosticTodoCount": unlinked_count,
            "scenarioScope": "all_known_tasks_minimum_acceptance",
            "coveredGapPoints": 0.0,
            "coverageRate": 0.0,
        })
    return projection


def _empty_scenario():
    return {"observations": {}, "recoveries": {}}


def _as_strings(value):
    if value is None or value == "":
        return []
    values = value if isinstance(value, (list, tuple, set)) else [value]
    return [str(item).strip() for item in values if str(item).strip()]


def _unique_strings(values):
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _round1(value):
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
