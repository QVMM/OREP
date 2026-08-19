"""Normalize authoritative score losses into stable report facts."""

from __future__ import annotations

from copy import deepcopy
import hashlib


_ACTIONABLE_TYPES = {"performance_gap", "evidence_limited", "hard_violation"}


def normalize_loss_ledger(*, rule_result, rule_hash, scoring_fingerprint):
    """Return report-specific loss instances with cross-report semantic keys."""

    observations = {
        str(item.get("observationCode") or "").strip(): item
        for item in list((rule_result or {}).get("observations") or [])
        if isinstance(item, dict) and str(item.get("observationCode") or "").strip()
    }
    deductions = _deductions_by_cause((rule_result or {}).get("deductions") or [])
    normalized = []
    seen_loss_ids = set()

    for row in list((rule_result or {}).get("lossLedger") or []):
        if not isinstance(row, dict):
            continue
        points = float(row.get("points") or 0)
        if points <= 0:
            continue
        code = str(row.get("observationCode") or "unassigned").strip() or "unassigned"
        loss_type = str(row.get("lossType") or "unresolved_gap").strip() or "unresolved_gap"
        cause_code = str(row.get("causeCode") or f"{code}:{loss_type}").strip()
        observation = observations.get(code) or {}
        deduction = deductions.get(cause_code) or deductions.get(str(row.get("penaltyRuleCode") or "")) or {}
        loss_id = _stable_loss_id(scoring_fingerprint, cause_code)
        if loss_id in seen_loss_ids:
            raise ValueError(f"duplicate loss identity for causeCode {cause_code}")
        seen_loss_ids.add(loss_id)

        item = deepcopy(row)
        item.update({
            "lossId": loss_id,
            "lossKey": f"{rule_hash}:{cause_code}",
            "causeCode": cause_code,
            "observationCode": code,
            "observationName": observation.get("observationName"),
            "dimensionCode": observation.get("dimensionCode") or row.get("dimensionCode") or "unassigned",
            "trackDefinition": observation.get("trackDefinition"),
            "requiredInfo": list(observation.get("requiredInfo") or []),
            "acceptableEvidence": list(observation.get("acceptableEvidence") or []),
            "trainingTaskTemplate": observation.get("trainingTaskTemplate"),
            "lossType": loss_type,
            "points": points,
            "evidenceAnchorIds": list(row.get("evidenceAnchorIds") or []),
            "scoreBudgetKey": _score_budget_key(code, loss_type, row, deduction),
            "actionability": "actionable" if loss_type in _ACTIONABLE_TYPES else "review_required",
            "ruleHash": rule_hash,
            "scoringFingerprint": scoring_fingerprint,
        })
        if loss_type == "hard_violation":
            item["penaltyRuleCode"] = (
                row.get("penaltyRuleCode")
                or deduction.get("penaltyRuleCode")
                or deduction.get("deductionRuleCode")
            )
            item["deductionId"] = deduction.get("deductionId")
            item["maxRecoverablePoints"] = float(deduction.get("maxRecoverablePoints") or 0)
        normalized.append(item)
    return normalized


def _deductions_by_cause(deductions):
    result = {}
    for row in deductions:
        if not isinstance(row, dict):
            continue
        for key in (
            row.get("causeCode"),
            row.get("penaltyRuleCode"),
            row.get("deductionRuleCode"),
            row.get("deductionId"),
        ):
            if key:
                result[str(key)] = row
    return result


def _stable_loss_id(scoring_fingerprint, cause_code):
    seed = f"{scoring_fingerprint}|{cause_code}".encode("utf-8")
    return f"loss-{hashlib.sha256(seed).hexdigest()[:24]}"


def _score_budget_key(code, loss_type, row, deduction):
    if loss_type == "performance_gap":
        return f"{code}:performance_score"
    if loss_type == "evidence_limited":
        return f"{code}:evidence_cap"
    if loss_type == "hard_violation":
        penalty = (
            deduction.get("penaltyRuleCode")
            or row.get("penaltyRuleCode")
            or deduction.get("deductionRuleCode")
            or row.get("causeCode")
            or "unassigned"
        )
        return f"{code}:hard_violation:{penalty}"
    return f"{code}:{loss_type}"
