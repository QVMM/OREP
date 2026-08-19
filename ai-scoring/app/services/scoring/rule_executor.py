"""Deterministic authoritative scoring with single-attribution loss ledgers."""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP


_ZERO = Decimal("0")
_POLICY_VERSION = "score-policy-v2-single-attribution"
_RECOVERED_STATUSES = {"fixed", "verified", "recovered"}
_INACTIVE_DEDUCTION_STATUSES = {"invalid", "recovered"}
_SUBTRACTIVE_EFFECT = "subtractive"


def execute_rule_score(observations, deductions, recoveries=None):
    canonical_observations = list(observations or [])
    canonical_deductions = list(deductions or [])
    canonical_recoveries = list(recoveries or [])
    _validate_unique_observation_codes(canonical_observations)

    deductions_by_observation = defaultdict(list)
    deductions_by_id = {}
    active_hard_deductions = []
    for item in canonical_deductions:
        deduction_id = str(item.get("deductionId") or "").strip()
        if deduction_id:
            deductions_by_id[deduction_id] = item
        status = str(item.get("status") or "").strip().lower()
        score_effect = str(item.get("scoreEffect") or "diagnostic_only").strip().lower()
        if status not in _INACTIVE_DEDUCTION_STATUSES and score_effect == _SUBTRACTIVE_EFFECT:
            deductions_by_observation[item.get("observationCode")].append(item)
            active_hard_deductions.append(item)
    # Stable application order: larger hard penalties first, then cause/id.
    # Prevents "input list order" from changing clamped totals.
    for observation_code, rows in list(deductions_by_observation.items()):
        deductions_by_observation[observation_code] = sorted(
            rows,
            key=lambda row: (
                -_non_negative(row.get("deductedPoints")),
                str(row.get("causeCode") or ""),
                str(row.get("deductionId") or ""),
            ),
        )
    _validate_unique_hard_violation_causes(active_hard_deductions)

    recoveries_by_deduction = defaultdict(lambda: _ZERO)
    for recovery in canonical_recoveries:
        status = str(recovery.get("recoveryStatus") or "").strip().lower()
        if status not in _RECOVERED_STATUSES:
            continue
        source_id = str(recovery.get("sourceDeductionId") or "").strip()
        source = deductions_by_id.get(source_id)
        if source is None:
            continue
        requested = _non_negative(recovery.get("requestedRecoverPoints"))
        allowed = _non_negative(source.get("maxRecoverablePoints"))
        recoveries_by_deduction[source_id] += min(requested, allowed)

    scored_observations = []
    loss_ledger = []
    dimension_scores = defaultdict(lambda: _ZERO)
    dimension_max_scores = defaultdict(lambda: _ZERO)
    totals = defaultdict(lambda: _ZERO)

    for item in canonical_observations:
        code = str(item.get("observationCode") or "").strip()
        dimension = item.get("dimensionCode") or "unassigned"
        max_score = _non_negative(item.get("maxScore"))
        performance_score = _bounded_score(item.get("baseScore"), max_score, "baseScore")
        score_cap = _bounded_score(item.get("scoreCap"), max_score, "scoreCap")
        score_before_penalty = min(performance_score, score_cap)

        performance_gap = max_score - performance_score
        evidence_limited_gap = max(_ZERO, performance_score - score_cap)
        gross_hard_penalty, recovered, hard_rows = _effective_hard_penalties(
            deductions_by_observation.get(code, []),
            recoveries_by_deduction,
            score_before_penalty,
        )
        effective_hard_penalty = gross_hard_penalty - recovered
        final_score = score_before_penalty - effective_hard_penalty
        ledger_context = {
            "observationName": item.get("observationName"),
            "dimensionCode": dimension,
        }

        if performance_gap > _ZERO:
            loss_ledger.append({
                **ledger_context,
                "causeCode": f"{code}:performance_gap",
                "observationCode": code,
                "lossType": "performance_gap",
                "points": _number(performance_gap),
                "reason": item.get("performanceReason") or item.get("modelReason") or "本轮表现未完全达到观测点要求",
                "evidenceAnchorIds": list(item.get("evidenceAnchorIds") or []),
                "consumedBy": "performance_score",
            })
        if evidence_limited_gap > _ZERO:
            loss_ledger.append({
                **ledger_context,
                "causeCode": f"{code}:evidence_limited",
                "observationCode": code,
                "lossType": "evidence_limited",
                "points": _number(evidence_limited_gap),
                "reason": item.get("evidenceReason") or item.get("supportSummary") or "当前证据仅能支持到较低确认上限",
                "evidenceAnchorIds": list(item.get("evidenceAnchorIds") or []),
                "consumedBy": "evidence_cap",
            })
        loss_ledger.extend({**ledger_context, **row} for row in hard_rows)

        scored = dict(item)
        scored.update({
            "maxScore": _number(max_score),
            "baseScore": _number(performance_score),
            "performanceScore": _number(performance_score),
            "scoreCap": _number(score_cap),
            "scoreBeforePenalty": _number(score_before_penalty),
            "performanceGap": _number(performance_gap),
            "evidenceLimitedGap": _number(evidence_limited_gap),
            "deductedScore": _number(gross_hard_penalty),
            "recoveredScore": _number(recovered),
            "effectiveHardPenalty": _number(effective_hard_penalty),
            "finalScore": _number(final_score),
        })
        scored_observations.append(scored)
        dimension_scores[dimension] += final_score
        dimension_max_scores[dimension] += max_score
        totals["ruleMaxScore"] += max_score
        totals["baseScore"] += performance_score
        totals["performanceGap"] += performance_gap
        totals["evidenceLimitedGap"] += evidence_limited_gap
        totals["deductedScore"] += gross_hard_penalty
        totals["recoveredScore"] += recovered
        totals["effectiveHardPenalty"] += effective_hard_penalty
        totals["currentScoreCap"] += score_cap
        totals["finalScore"] += final_score

    total_loss = totals["performanceGap"] + totals["evidenceLimitedGap"] + totals["effectiveHardPenalty"]
    if totals["ruleMaxScore"] != totals["finalScore"] + total_loss:
        raise ValueError("loss ledger does not reconcile with final score")

    dimension_result = {key: _number(value) for key, value in dimension_scores.items()}
    dimension_max_result = {key: _number(value) for key, value in dimension_max_scores.items()}
    reconciliation = {
        "ruleMaxScore": _number(totals["ruleMaxScore"]),
        "baseScore": _number(totals["baseScore"]),
        "performanceGap": _number(totals["performanceGap"]),
        "evidenceLimitedGap": _number(totals["evidenceLimitedGap"]),
        "deductedScore": _number(totals["deductedScore"]),
        "recoveredScore": _number(totals["recoveredScore"]),
        "effectiveHardPenalty": _number(totals["effectiveHardPenalty"]),
        "currentScoreCap": _number(totals["currentScoreCap"]),
        "totalLoss": _number(total_loss),
        "finalScore": _number(totals["finalScore"]),
        "dimensionScoreTotal": _number(sum(dimension_scores.values(), _ZERO)),
    }
    return {
        "scoreAuthority": "structured_rule_engine",
        "scorePolicyVersion": _POLICY_VERSION,
        "baseScore": reconciliation["baseScore"],
        "performanceGap": reconciliation["performanceGap"],
        "evidenceLimitedGap": reconciliation["evidenceLimitedGap"],
        "deductedScore": reconciliation["deductedScore"],
        "recoveredScore": reconciliation["recoveredScore"],
        "effectiveHardPenalty": reconciliation["effectiveHardPenalty"],
        "currentScoreCap": reconciliation["currentScoreCap"],
        "finalScore": reconciliation["finalScore"],
        "dimensionScores": dimension_result,
        "dimensionMaxScores": dimension_max_result,
        "observations": scored_observations,
        "deductions": canonical_deductions,
        "lossLedger": loss_ledger,
        "reconciliation": reconciliation,
    }


def _effective_hard_penalties(deductions, recoveries_by_deduction, available_score):
    remaining = available_score
    gross_total = _ZERO
    recovered_total = _ZERO
    ledger_rows = []
    for row in deductions:
        if remaining <= _ZERO:
            break
        deduction_id = str(row.get("deductionId") or "").strip()
        gross = min(_non_negative(row.get("deductedPoints")), remaining)
        recovered = min(recoveries_by_deduction[deduction_id], gross)
        net = gross - recovered
        gross_total += gross
        recovered_total += recovered
        remaining -= gross
        if net <= _ZERO:
            continue
        ledger_rows.append({
            "causeCode": str(row.get("causeCode") or deduction_id).strip(),
            "observationCode": row.get("observationCode"),
            "lossType": "hard_violation",
            "points": _number(net),
            "reason": row.get("reason") or "发生赛事规则明确规定的独立违规事件",
            "evidenceAnchorIds": list(row.get("evidenceAnchorIds") or []),
            "consumedBy": "hard_penalty",
            "penaltyRuleCode": row.get("deductionRuleCode") or row.get("penaltyRuleCode") or deduction_id,
        })
    return gross_total, recovered_total, ledger_rows


def _validate_unique_observation_codes(observations):
    seen = set()
    for item in observations:
        code = str(item.get("observationCode") or "").strip()
        if not code:
            raise ValueError("observationCode must not be blank")
        if code in seen:
            raise ValueError(f"duplicate observationCode {code}")
        seen.add(code)


def _validate_unique_hard_violation_causes(deductions):
    seen = set()
    for item in deductions:
        cause_code = str(item.get("causeCode") or item.get("deductionId") or "").strip()
        if not cause_code:
            raise ValueError("hard violation causeCode must not be blank")
        if cause_code in seen:
            raise ValueError(f"duplicate causeCode {cause_code}")
        seen.add(cause_code)


def _bounded_score(value, max_score, field_name):
    number = _non_negative(value)
    if number > max_score:
        raise ValueError(f"{field_name} must be between 0 and maxScore")
    return number


def _non_negative(value):
    if value is None or value == "":
        return _ZERO
    number = Decimal(str(value))
    if number < _ZERO:
        raise ValueError("score values must be non-negative")
    return number


def _number(value):
    return float(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
