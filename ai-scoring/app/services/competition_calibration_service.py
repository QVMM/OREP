"""Competition score calibration for technical/demo-first scoring."""

from __future__ import annotations

from copy import deepcopy

from app.services.demo_evidence_service import analyze_demo_evidence
from app.services.official_rubric_service import normalize_official_rubric


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _technical_ceiling(skill_score: float, demo_evidence: dict) -> tuple[float, list[str]]:
    reasons = []
    ceiling = 100.0
    if not demo_evidence.get("has_demo"):
        ceiling = min(ceiling, 85.0)
        reasons.append("缺少现场演示证据，技能水平不能支撑95+或满分。")
    elif demo_evidence.get("has_failure"):
        ceiling = min(ceiling, 78.0)
        reasons.append("现场演示出现失败/中断/卡顿证据，技术上限受限。")
    elif not demo_evidence.get("has_runtime_result"):
        ceiling = min(ceiling, 88.0)
        reasons.append("有演示迹象但缺少核心功能运行结果，技术上限不宜超过88。")
    elif not demo_evidence.get("has_test_data"):
        ceiling = min(ceiling, 92.0)
        reasons.append("现场演示跑通但缺少测试数据或性能结果，暂不进入95+。")

    if skill_score < 45:
        ceiling = min(ceiling, 82.0)
        reasons.append("技能水平低于45/60，最终总分通常不应超过82。")
    elif skill_score < 50:
        ceiling = min(ceiling, 88.0)
        reasons.append("技能水平低于50/60，最终总分通常不应超过88。")

    return round(ceiling, 2), reasons


def calibrate_ai_score(result: dict) -> dict:
    working = result or {}
    ai_score = deepcopy(working.get("ai_score") or {})
    official_rubric = normalize_official_rubric(ai_score)
    demo_evidence = analyze_demo_evidence(working)
    skill_score = _safe_float(official_rubric["dimensions"]["skill_level"]["score"])
    technical_ceiling, reasons = _technical_ceiling(skill_score, demo_evidence)
    competition_ceiling = technical_ceiling
    original_score = _safe_float(ai_score.get("overall_score") or official_rubric["total_score"])
    final_score = min(original_score, competition_ceiling, technical_ceiling)

    return {
        "original_score": original_score,
        "official_rubric_score": official_rubric["total_score"],
        "official_rubric": official_rubric,
        "skill_score": skill_score,
        "skill_max_score": 60.0,
        "demo_evidence": demo_evidence,
        "technical_ceiling_score": technical_ceiling,
        "competition_ceiling_score": competition_ceiling,
        "final_score": round(final_score, 2),
        "ceiling_applied": round(final_score, 2) < original_score,
        "ceiling_reasons": reasons,
    }


def apply_calibration_to_result(result: dict) -> dict:
    calibration = calibrate_ai_score(result)
    ai_score = result.setdefault("ai_score", {})
    ai_score["raw_overall_score"] = calibration["original_score"]
    ai_score["overall_score"] = calibration["final_score"]
    ai_score["score_calibrated"] = calibration["ceiling_applied"]
    result["score_calibration"] = calibration
    return result
