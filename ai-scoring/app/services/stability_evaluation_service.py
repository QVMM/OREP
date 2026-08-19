"""Pilot stability evaluation and expert calibration helpers."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any


PILOT_TRACKS = ("track_42_ai", "track_27_it")
MIN_SAMPLES_PER_TRACK = 20
REQUIRED_SAMPLE_TYPES = {
    "high_score",
    "middle_score",
    "low_score",
    "low_evidence",
    "demo_failure",
    "material_sufficient",
    "slogan_packaging",
    "boundary_dispute",
}

PILOT_THRESHOLDS = {
    "ruleEngineScoreConsistencyRate": 1.0,
    "jsonParseSuccessRate": 0.98,
    "unsupportedClaimRate": 0.0,
    "e4e5HardConditionViolationRate": 0.0,
    "anchorAccuracyRate": 0.85,
    "deductionConsistencyRate": 0.80,
    "totalScoreMae": 8.0,
}


def validate_pilot_dataset_manifest(manifest: dict[str, Any] | None) -> dict[str, Any]:
    """Validate whether the frozen pilot sample manifest can be used for stage-7 admission."""
    tracks = (manifest or {}).get("tracks") or {}
    blocking_reasons: list[str] = []
    track_stats: dict[str, dict[str, Any]] = {}

    for track_id in PILOT_TRACKS:
        samples = _as_list(tracks.get(track_id))
        sample_types = {str(sample.get("sampleType") or "") for sample in samples if isinstance(sample, dict)}
        missing_types = sorted(REQUIRED_SAMPLE_TYPES - sample_types)
        missing_fields = _missing_sample_contracts(samples)

        track_stats[track_id] = {
            "sampleCount": len(samples),
            "sampleTypes": sorted(item for item in sample_types if item),
            "missingSampleTypes": missing_types,
            "missingFieldCount": len(missing_fields),
        }
        if len(samples) < MIN_SAMPLES_PER_TRACK:
            blocking_reasons.append(f"{track_id} needs at least 20 frozen samples")
        for sample_type in missing_types:
            blocking_reasons.append(f"{track_id} must cover {sample_type}")
        blocking_reasons.extend(f"{track_id}:{reason}" for reason in missing_fields)

    return {
        "status": "ready" if not blocking_reasons else "not_ready",
        "trackStats": track_stats,
        "blockingReasons": blocking_reasons,
    }


def evaluate_quality_report(samples: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Build a repeatable scoring quality report from frozen pilot evaluation runs."""
    safe_samples = [sample for sample in _as_list(samples) if isinstance(sample, dict)]
    runs = [run for sample in safe_samples for run in _as_list(sample.get("runs")) if isinstance(run, dict)]
    observations = [
        observation
        for run in runs
        for observation in _as_list(run.get("observationEvidence"))
        if isinstance(observation, dict)
    ]

    metrics = {
        "ruleEngineScoreConsistencyRate": _score_consistency_rate(safe_samples),
        "jsonParseSuccessRate": _ratio([bool(run.get("jsonParsed")) for run in runs]),
        "unsupportedClaimRate": _safe_divide(sum(_number(run.get("unsupportedClaims")) for run in runs), len(runs)),
        "e4e5HardConditionViolationRate": _safe_divide(
            sum(1 for observation in observations if _e4e5_hard_condition_violated(observation)),
            len(observations),
        ),
        "anchorAccuracyRate": _ratio([bool(observation.get("anchorAccurate")) for observation in observations]),
        "deductionConsistencyRate": _deduction_consistency_rate(safe_samples),
        "totalScoreMae": _total_score_mae(safe_samples),
        "dimensionScoreMae": _dimension_score_mae(safe_samples),
        "humanReviewTriggerCount": sum(1 for run in runs if run.get("needsHumanReview")),
        "newOldScoreDiffs": [
            _number(run.get("ruleEngineScore")) - _number(run.get("oldLlmScore"))
            for run in runs
            if run.get("ruleEngineScore") is not None and run.get("oldLlmScore") is not None
        ],
    }
    failing_metrics = _failing_metrics(metrics)
    failing_samples = _failing_samples(safe_samples)

    return {
        "generatedAt": datetime.now().isoformat(),
        "sampleCount": len(safe_samples),
        "trackDistribution": dict(Counter(str(sample.get("trackId") or "unknown") for sample in safe_samples)),
        "metrics": metrics,
        "status": "ready" if not failing_metrics and not failing_samples else "not_ready",
        "failingMetrics": failing_metrics,
        "failingSamples": failing_samples,
        "remediationTasks": _remediation_tasks(failing_metrics, failing_samples),
    }


def validate_expert_calibration_record(record: dict[str, Any] | None) -> dict[str, Any]:
    """Validate a human expert correction record without mutating historical reports."""
    source = record or {}
    errors: list[str] = []
    required_fields = ("sampleId", "reviewer", "reviewedAt", "reason", "affectedObservations", "ruleVersion")
    for field in required_fields:
        if not source.get(field):
            errors.append(f"{field} is required")
    if source.get("correctionType") not in {"sample_annotation", "rule_change_suggestion"}:
        errors.append("correctionType must be sample_annotation or rule_change_suggestion")
    if source.get("affectedObservations") is not None and not _as_list(source.get("affectedObservations")):
        errors.append("affectedObservations must not be empty")
    return {
        "valid": not errors,
        "errors": errors,
    }


def _missing_sample_contracts(samples: list[Any]) -> list[str]:
    required = (
        "sampleId",
        "inputSnapshotHash",
        "ruleVersion",
        "humanReferenceScore",
        "humanDeductionNotes",
        "verifiableEvidencePoints",
    )
    missing = []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            missing.append(f"samples[{index}] must be an object")
            continue
        for field in required:
            value = sample.get(field)
            if value in (None, "", []):
                missing.append(f"{sample.get('sampleId') or index} missing {field}")
    return missing


def _score_consistency_rate(samples: list[dict[str, Any]]) -> float:
    checks = []
    for sample in samples:
        scores = [_number(run.get("ruleEngineScore")) for run in _as_list(sample.get("runs")) if run.get("ruleEngineScore") is not None]
        if not scores:
            checks.append(False)
        else:
            checks.append(max(scores) - min(scores) == 0)
    return _ratio(checks)


def _deduction_consistency_rate(samples: list[dict[str, Any]]) -> float:
    checks = []
    for sample in samples:
        deduction_sets = [set(_as_list(run.get("deductions"))) for run in _as_list(sample.get("runs")) if isinstance(run, dict)]
        if not deduction_sets:
            checks.append(False)
        else:
            checks.append(all(item == deduction_sets[0] for item in deduction_sets))
    return _ratio(checks)


def _total_score_mae(samples: list[dict[str, Any]]) -> float:
    errors = []
    for sample in samples:
        reference = sample.get("humanReferenceScore")
        scores = [_number(run.get("ruleEngineScore")) for run in _as_list(sample.get("runs")) if run.get("ruleEngineScore") is not None]
        if reference is None or not scores:
            continue
        errors.append(abs(mean(scores) - _number(reference)))
    return round(mean(errors)) if errors else 0


def _dimension_score_mae(samples: list[dict[str, Any]]) -> float:
    errors = []
    for sample in samples:
        expert = sample.get("expertDimensionScores") or {}
        if not isinstance(expert, dict):
            continue
        for run in _as_list(sample.get("runs")):
            scores = run.get("dimensionScores") if isinstance(run, dict) else {}
            if not isinstance(scores, dict):
                continue
            for key, expert_score in expert.items():
                if key in scores:
                    errors.append(abs(_number(scores[key]) - _number(expert_score)))
    return round(mean(errors), 2) if errors else 0


def _e4e5_hard_condition_violated(observation: dict[str, Any]) -> bool:
    level = str(observation.get("evidenceLevel") or "").upper()
    if level not in {"E4", "E5"}:
        return False
    required_anchor_count = 3 if level == "E5" else 2
    if _number(observation.get("anchorCount")) < required_anchor_count:
        return True
    if observation.get("lowConfidence") is True:
        return True
    return False


def _failing_metrics(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    failing = []
    for key, threshold in PILOT_THRESHOLDS.items():
        value = metrics.get(key)
        if value is None:
            continue
        if key.endswith("Rate") and key not in {"unsupportedClaimRate", "e4e5HardConditionViolationRate"}:
            failed = value < threshold
        elif key in {"unsupportedClaimRate", "e4e5HardConditionViolationRate", "totalScoreMae"}:
            failed = value > threshold
        else:
            failed = False
        if failed:
            failing.append({"metric": key, "value": value, "threshold": threshold})
    return failing


def _failing_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failing = []
    for sample in samples:
        reasons = []
        scores = [_number(run.get("ruleEngineScore")) for run in _as_list(sample.get("runs")) if run.get("ruleEngineScore") is not None]
        if scores and max(scores) - min(scores) != 0:
            reasons.append("同一证据快照下规则引擎总分波动不为0")
        if sample.get("humanReferenceScore") is not None and scores and abs(mean(scores) - _number(sample.get("humanReferenceScore"))) > 8:
            reasons.append("总分相对专家参考分 MAE 超过8分")
        if any(
            _e4e5_hard_condition_violated(observation)
            for run in _as_list(sample.get("runs"))
            for observation in _as_list(run.get("observationEvidence") if isinstance(run, dict) else [])
            if isinstance(observation, dict)
        ):
            reasons.append("E4/E5 硬条件违规")
        if reasons:
            failing.append({
                "sampleId": sample.get("sampleId"),
                "trackId": sample.get("trackId"),
                "reasons": reasons,
            })
    return failing


def _remediation_tasks(failing_metrics: list[dict[str, Any]], failing_samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = []
    if failing_metrics:
        tasks.append({
            "title": "复核未达标稳定性指标",
            "owner": "规则/证据校准负责人",
            "acceptanceCriteria": "复测报告中核心指标达到试点准入标准",
            "metrics": [item["metric"] for item in failing_metrics],
        })
    for sample in failing_samples:
        tasks.append({
            "title": f"复核样本 {sample.get('sampleId')}",
            "owner": "规则/证据校准负责人",
            "acceptanceCriteria": "修正证据等级、扣分项或规则阈值后重新评测该样本",
            "sampleId": sample.get("sampleId"),
            "reasons": sample.get("reasons", []),
        })
    return tasks


def _ratio(values: list[bool]) -> float:
    if not values:
        return 0
    return sum(1 for value in values if value) / len(values)


def _safe_divide(numerator: float, denominator: int) -> float:
    if not denominator:
        return 0
    return numerator / denominator


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]
