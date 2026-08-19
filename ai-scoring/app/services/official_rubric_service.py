"""Official 2025 competition rubric helpers for OREP scoring."""

from __future__ import annotations

from copy import deepcopy


RUBRIC_DIMENSIONS = {
    "skill_level": {
        "name": "技能水平",
        "max_score": 60.0,
        "items": {
            "操作规范性": ("operation_norms", 10.0),
            "技能熟练度": ("skill_fluency", 15.0),
            "任务难易度": ("task_difficulty", 15.0),
            "技术先进性": ("technical_advancement", 15.0),
            "现场讲解效果": ("onsite_explanation", 5.0),
        },
    },
    "professionalism": {"name": "职业素养", "max_score": 10.0, "items": {}},
    "application_value": {"name": "应用价值", "max_score": 10.0, "items": {}},
    "teamwork": {"name": "团队合作", "max_score": 10.0, "items": {}},
    "innovation": {"name": "创新创意", "max_score": 10.0, "items": {}},
}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def normalize_official_rubric(ai_score: dict) -> dict:
    dimensions = deepcopy((ai_score or {}).get("dimensions") or {})
    normalized = {}
    total_score = 0.0

    for dim_key, spec in RUBRIC_DIMENSIONS.items():
        dim = dimensions.get(dim_key) or {}
        items = []
        item_total = 0.0
        for item in dim.get("items") or []:
            name = item.get("name") or ""
            item_key, default_max = spec.get("items", {}).get(name, (name, item.get("max_score", 0)))
            score = _safe_float(item.get("score"))
            max_score = _safe_float(item.get("max_score"), _safe_float(default_max))
            item_total += score
            copied = deepcopy(item)
            copied["key"] = item_key
            copied["score"] = score
            copied["max_score"] = max_score
            items.append(copied)

        score = round(item_total if items else _safe_float(dim.get("score")), 2)
        max_score = _safe_float(dim.get("max_score"), spec["max_score"])
        normalized[dim_key] = {
            "name": dim.get("name") or spec["name"],
            "score": score,
            "max_score": max_score,
            "items": items,
        }
        total_score += score

    return {
        "total_score": round(total_score, 2),
        "dimensions": normalized,
    }
