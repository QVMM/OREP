"""Validate score reconciliation and full remediation coverage."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP


def validate_remediation_coverage(
    *,
    current_score,
    loss_ledger,
    tasks,
    rule_hash=None,
    scoring_fingerprint=None,
):
    losses = [row for row in list(loss_ledger or []) if isinstance(row, dict)]
    valid_losses = [row for row in losses if str(row.get("lossId") or "").strip()]
    loss_by_id = {str(row["lossId"]): row for row in valid_losses}
    all_ids = set(loss_by_id)
    covered_ids = {
        str(loss_id)
        for task in list(tasks or [])
        if isinstance(task, dict)
        for loss_id in list(task.get("coveredLossIds") or [])
        if str(loss_id) in all_ids
    }
    full_gap = _round1(100.0 - float(current_score))
    ledger_points = _round1(sum(float(row.get("points") or 0) for row in valid_losses))
    uncovered = sorted(all_ids - covered_ids)
    covered_gap = _round1(sum(
        float(loss_by_id[loss_id].get("points") or 0)
        for loss_id in covered_ids
    ))
    budget_counts = Counter(
        str(row.get("scoreBudgetKey") or "").strip()
        for row in valid_losses
        if str(row.get("scoreBudgetKey") or "").strip()
    )
    duplicate_budget_keys = sorted(key for key, count in budget_counts.items() if count > 1)
    duplicate_loss_ids = len(valid_losses) != len(losses) or len(loss_by_id) != len(valid_losses)
    reconciliation_error = _round1(ledger_points - full_gap)
    coverage_rate = round(len(covered_ids) / len(all_ids), 4) if all_ids else (1.0 if full_gap == 0 else 0.0)
    complete = (
        abs(reconciliation_error) <= 0.1
        and not uncovered
        and not duplicate_budget_keys
        and not duplicate_loss_ids
    )
    return {
        "currentScore": _round1(current_score),
        "fullGap": full_gap,
        "ledgerPoints": ledger_points,
        "lossItemCount": len(valid_losses),
        "remediationTaskCount": len([row for row in list(tasks or []) if isinstance(row, dict)]),
        "coveredLossItemCount": len(covered_ids),
        "coveredGapPoints": covered_gap,
        "coverageRate": coverage_rate,
        "uncoveredLossIds": uncovered,
        "unresolvedDuplicateBudgetKeys": duplicate_budget_keys,
        "reconciliationError": reconciliation_error,
        "status": "complete" if complete else "incomplete",
        "calculationVersion": "remediation-coverage-v1",
        "ruleHash": rule_hash,
        "scoringFingerprint": scoring_fingerprint,
    }


def _round1(value):
    return float(Decimal(str(value or 0)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))

