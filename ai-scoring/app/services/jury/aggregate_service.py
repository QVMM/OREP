"""Aggregate independent AI jury reports."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, pstdev
from typing import Any


def _score(report: dict) -> float | None:
    try:
        return float(report.get("overall_score"))
    except (TypeError, ValueError):
        return None


def _round2(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value) + 1e-9, 2)


def _public_report_ref(report: dict | None) -> dict | None:
    if not report:
        return None
    return {
        "id": report.get("id"),
        "member_id": report.get("member_id"),
        "persona_code": report.get("persona_code"),
        "overall_score": _round2(_score(report)),
    }


def _dimension_stats(reports: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        dimensions = report.get("dimensions") or {}
        for key, dimension in dimensions.items():
            try:
                score = float(dimension.get("score"))
            except (TypeError, ValueError, AttributeError):
                continue
            buckets[key].append({
                "score": score,
                "name": dimension.get("name") or key,
                "max_score": dimension.get("max_score") or dimension.get("maxScore"),
            })

    stats = []
    for key, values in buckets.items():
        scores = [item["score"] for item in values]
        stats.append({
            "key": key,
            "name": values[0]["name"],
            "max_score": values[0]["max_score"],
            "average_score": _round2(mean(scores)),
            "highest_score": _round2(max(scores)),
            "lowest_score": _round2(min(scores)),
            "range": _round2(max(scores) - min(scores)),
            "stddev": _round2(pstdev(scores)) if len(scores) > 1 else 0.00,
            "judge_count": len(scores),
        })

    stats.sort(key=lambda item: item["range"], reverse=True)
    return stats


def _consensus_issues(reports: list[dict], min_count: int = 2) -> list[dict]:
    counter: Counter[str] = Counter()
    personas: dict[str, set[str]] = defaultdict(set)
    for report in reports:
        persona = report.get("persona_code") or ""
        for issue in report.get("critical_issues") or []:
            if isinstance(issue, dict):
                text = str(issue.get("issue") or issue.get("text") or "")
            else:
                text = str(issue)
            normalized = text.strip()
            if not normalized:
                continue
            counter[normalized] += 1
            if persona:
                personas[normalized].add(persona)

    return [
        {
            "issue": issue,
            "count": count,
            "personas": sorted(personas.get(issue, set())),
        }
        for issue, count in counter.most_common()
        if count >= min_count
    ]


def aggregate_judge_reports(reports: list[dict], official_score: float | int | None = None) -> dict:
    """Build jury score statistics and disagreement data.

    The official score is used only after independent reports exist. It is not
    part of any judge input.
    """
    scored_reports = [report for report in reports if _score(report) is not None]
    scored_reports.sort(key=lambda item: _score(item) or 0)
    scores = [_score(report) or 0 for report in scored_reports]

    removed_low = scored_reports[0] if len(scored_reports) >= 3 else None
    removed_high = scored_reports[-1] if len(scored_reports) >= 3 else None
    kept = scored_reports[1:-1] if len(scored_reports) >= 3 else scored_reports
    kept_scores = [_score(report) or 0 for report in kept]

    raw_average = mean(scores) if scores else None
    trimmed_average = mean(kept_scores) if kept_scores else None
    official = float(official_score) if official_score is not None else None

    return {
        "judge_count": len(reports),
        "successful_count": len(scored_reports),
        "raw_average_score": _round2(raw_average),
        "trimmed_average_score": _round2(trimmed_average),
        "trimmed_total_score": _round2(sum(kept_scores)) if kept_scores else None,
        "trimmed_count": len(kept_scores),
        "highest_score": _round2(max(scores)) if scores else None,
        "lowest_score": _round2(min(scores)) if scores else None,
        "removed_low": _public_report_ref(removed_low),
        "removed_high": _public_report_ref(removed_high),
        "score_diff_from_official": (
            _round2(trimmed_average - official)
            if trimmed_average is not None and official is not None
            else None
        ),
        "dimension_stats": _dimension_stats(scored_reports),
        "consensus_issues": _consensus_issues(scored_reports),
    }
