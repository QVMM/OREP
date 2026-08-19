# AI Scoring Technical Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working slice of OREP's continuous scoring optimization: official-rubric scoring metadata, demo evidence grading, and technical ceiling calibration that prevents "all prior issues fixed" from becoming an automatic 100.

**Architecture:** Add a pure Python calibration layer after the existing LLM scoring step. The current LLM prompt already outputs the official 15-item rubric; the new services will normalize those scores, infer demo evidence level from visual/fusion evidence, compute technical and competition ceilings, and attach a structured `score_calibration` object to `result_*.json`.

**Tech Stack:** Python FastAPI service code under `ai-scoring/app/services`, pytest under `ai-scoring/tests`, existing result JSON pipeline in `pipeline_service.py`.

---

## Scope Check

The full product scheme covers at least five subsystems:

- AI scoring calibration
- Long-term score memory storage
- Historical issue recheck
- Report/front-end presentation
- 16-personality jury memory-aware review

This plan implements the first deployable slice only: **technical/demo calibration inside the AI scoring pipeline**. It creates the data contract later features will consume without requiring database migrations yet.

---

## File Structure

- Create `ai-scoring/app/services/official_rubric_service.py`
  - Defines the official 2025 scoring rubric, item keys, max scores, and helpers to normalize LLM dimension output.
- Create `ai-scoring/app/services/demo_evidence_service.py`
  - Infers现场演示 evidence level from fusion/video payloads and text signals.
- Create `ai-scoring/app/services/competition_calibration_service.py`
  - Computes `TechnicalCeilingScore`, `CompetitionCeilingScore`, final capped score, and explanation cards.
- Modify `ai-scoring/app/services/pipeline_service.py`
  - Calls the calibration service after LLM score and duration cap logic in both normal and dual-video pipelines.
- Create `ai-scoring/tests/test_competition_calibration_service.py`
  - Unit tests for score normalization, evidence-level detection, technical ceiling, and final capping.

---

### Task 1: Official Rubric Normalization

**Files:**
- Create: `ai-scoring/app/services/official_rubric_service.py`
- Test: `ai-scoring/tests/test_competition_calibration_service.py`

- [ ] **Step 1: Write the failing test**

Add this to `ai-scoring/tests/test_competition_calibration_service.py`:

```python
from app.services.official_rubric_service import normalize_official_rubric


def test_normalize_official_rubric_preserves_skill_level_60_points():
    ai_score = {
        "overall_score": 88,
        "dimensions": {
            "skill_level": {
                "name": "技能水平",
                "max_score": 60,
                "score": 50,
                "items": [
                    {"name": "操作规范性", "max_score": 10, "score": 8},
                    {"name": "技能熟练度", "max_score": 15, "score": 12},
                    {"name": "任务难易度", "max_score": 15, "score": 13},
                    {"name": "技术先进性", "max_score": 15, "score": 12},
                    {"name": "现场讲解效果", "max_score": 5, "score": 5},
                ],
            }
        },
    }

    rubric = normalize_official_rubric(ai_score)

    assert rubric["total_score"] == 50.0
    assert rubric["dimensions"]["skill_level"]["score"] == 50.0
    assert rubric["dimensions"]["skill_level"]["max_score"] == 60.0
    assert rubric["dimensions"]["skill_level"]["items"][1]["key"] == "skill_fluency"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py::test_normalize_official_rubric_preserves_skill_level_60_points -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.services.official_rubric_service'`.

- [ ] **Step 3: Implement minimal service**

Create `ai-scoring/app/services/official_rubric_service.py` with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

---

### Task 2: Demo Evidence Level Detection

**Files:**
- Create: `ai-scoring/app/services/demo_evidence_service.py`
- Test: `ai-scoring/tests/test_competition_calibration_service.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
from app.services.demo_evidence_service import analyze_demo_evidence


def test_demo_evidence_detects_demo_with_runtime_and_test_data():
    result = {
        "asr": {"transcript": "下面进入现场演示，系统成功运行，响应时间降低40%。"},
        "video_analysis": {
            "per_frame": [
                {"screen_content": {"screen_type": "系统界面", "text": "运行成功 响应时间 200ms"}},
                {"screen_content": {"screen_type": "测试报告", "text": "benchmark 准确率 92%"}},
            ]
        },
        "fusion": {"screen_content_summary": {"screen_type_distribution": {"系统界面": 1, "测试报告": 1}}},
    }

    evidence = analyze_demo_evidence(result)

    assert evidence["has_demo"] is True
    assert evidence["has_runtime_result"] is True
    assert evidence["has_test_data"] is True
    assert evidence["level"] == "full_channel"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py::test_demo_evidence_detects_demo_with_runtime_and_test_data -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.services.demo_evidence_service'`.

- [ ] **Step 3: Implement minimal service**

Create `ai-scoring/app/services/demo_evidence_service.py` with:

```python
"""Infer on-site demo evidence strength from scoring result payloads."""

from __future__ import annotations


DEMO_KEYWORDS = ("现场演示", "演示", "实操", "操作", "运行", "系统界面", "设备", "功能")
RUNTIME_KEYWORDS = ("成功", "结果", "运行成功", "完成", "日志", "输出", "识别结果", "控制")
TEST_KEYWORDS = ("测试", "benchmark", "准确率", "响应时间", "性能", "并发", "错误率", "报告", "ms", "%")
FAILURE_KEYWORDS = ("报错", "失败", "中断", "卡顿", "崩溃", "无法打开", "超时")


def _collect_text(result: dict) -> str:
    parts = []
    asr = result.get("asr") or {}
    parts.append(str(asr.get("transcript") or ""))
    video = result.get("video_analysis") or {}
    for frame in video.get("per_frame") or []:
        screen = frame.get("screen_content") or {}
        parts.append(str(screen.get("screen_type") or ""))
        parts.append(str(screen.get("text") or screen.get("visible_text") or ""))
    fusion = result.get("fusion") or {}
    summary = fusion.get("screen_content_summary") or {}
    parts.append(str(summary.get("screen_type_distribution") or ""))
    return " ".join(parts)


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def analyze_demo_evidence(result: dict) -> dict:
    text = _collect_text(result or {})
    has_demo = _has_any(text, DEMO_KEYWORDS)
    has_runtime_result = _has_any(text, RUNTIME_KEYWORDS)
    has_test_data = _has_any(text, TEST_KEYWORDS)
    has_failure = _has_any(text, FAILURE_KEYWORDS)

    if has_demo and has_runtime_result and has_test_data:
        level = "full_channel"
        score_band = "95-100"
    elif has_demo and has_runtime_result:
        level = "demo_runtime"
        score_band = "80-95"
    elif has_demo:
        level = "demo_only"
        score_band = "60-80"
    else:
        level = "verbal_or_ppt_only"
        score_band = "40-60"

    return {
        "has_demo": has_demo,
        "has_runtime_result": has_runtime_result,
        "has_test_data": has_test_data,
        "has_failure": has_failure,
        "level": level,
        "score_band": score_band,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

---

### Task 3: Competition Calibration and Technical Ceiling

**Files:**
- Create: `ai-scoring/app/services/competition_calibration_service.py`
- Test: `ai-scoring/tests/test_competition_calibration_service.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
from app.services.competition_calibration_service import calibrate_ai_score


def test_calibration_caps_score_when_demo_evidence_is_missing():
    result = {
        "ai_score": {
            "overall_score": 96,
            "dimensions": {
                "skill_level": {"name": "技能水平", "max_score": 60, "score": 56, "items": []},
                "professionalism": {"name": "职业素养", "max_score": 10, "score": 10, "items": []},
                "application_value": {"name": "应用价值", "max_score": 10, "score": 10, "items": []},
                "teamwork": {"name": "团队合作", "max_score": 10, "score": 10, "items": []},
                "innovation": {"name": "创新创意", "max_score": 10, "score": 10, "items": []},
            },
        },
        "asr": {"transcript": "我们介绍了技术方案和PPT。"},
        "video_analysis": {"per_frame": [{"screen_content": {"screen_type": "PPT幻灯片", "text": "技术方案"}}]},
    }

    calibrated = calibrate_ai_score(result)

    assert calibrated["final_score"] == 85.0
    assert calibrated["technical_ceiling_score"] == 85.0
    assert "缺少现场演示证据" in calibrated["ceiling_reasons"][0]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py::test_calibration_caps_score_when_demo_evidence_is_missing -q
```

Expected: fails with `ModuleNotFoundError: No module named 'app.services.competition_calibration_service'`.

- [ ] **Step 3: Implement minimal service**

Create `ai-scoring/app/services/competition_calibration_service.py` with:

```python
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
        "skill_score": skill_score,
        "skill_max_score": 60.0,
        "demo_evidence": demo_evidence,
        "technical_ceiling_score": technical_ceiling,
        "competition_ceiling_score": competition_ceiling,
        "final_score": round(final_score, 2),
        "ceiling_applied": round(final_score, 2) < original_score,
        "ceiling_reasons": reasons,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command. Expected: PASS.

---

### Task 4: Attach Calibration to Pipeline Results

**Files:**
- Modify: `ai-scoring/app/services/pipeline_service.py`
- Test: `ai-scoring/tests/test_competition_calibration_service.py`

- [ ] **Step 1: Write the failing test**

Append:

```python
from app.services.competition_calibration_service import apply_calibration_to_result


def test_apply_calibration_updates_ai_score_and_keeps_original_score():
    result = {
        "ai_score": {
            "overall_score": 96,
            "dimensions": {
                "skill_level": {"name": "技能水平", "max_score": 60, "score": 56, "items": []},
                "professionalism": {"name": "职业素养", "max_score": 10, "score": 10, "items": []},
                "application_value": {"name": "应用价值", "max_score": 10, "score": 10, "items": []},
                "teamwork": {"name": "团队合作", "max_score": 10, "score": 10, "items": []},
                "innovation": {"name": "创新创意", "max_score": 10, "score": 10, "items": []},
            },
        },
        "asr": {"transcript": "PPT介绍技术方案。"},
        "video_analysis": {"per_frame": []},
    }

    updated = apply_calibration_to_result(result)

    assert updated["ai_score"]["overall_score"] == 85.0
    assert updated["ai_score"]["raw_overall_score"] == 96.0
    assert updated["score_calibration"]["ceiling_applied"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py::test_apply_calibration_updates_ai_score_and_keeps_original_score -q
```

Expected: fails because `apply_calibration_to_result` does not exist.

- [ ] **Step 3: Implement helper and pipeline call**

Add this function to `competition_calibration_service.py`:

```python
def apply_calibration_to_result(result: dict) -> dict:
    calibration = calibrate_ai_score(result)
    ai_score = result.setdefault("ai_score", {})
    ai_score["raw_overall_score"] = calibration["original_score"]
    ai_score["overall_score"] = calibration["final_score"]
    ai_score["score_calibrated"] = calibration["ceiling_applied"]
    result["score_calibration"] = calibration
    return result
```

Modify `pipeline_service.py`:

```python
from app.services.competition_calibration_service import apply_calibration_to_result
```

After duration cap/floor logic in both scoring pipelines, add:

```python
        if not skip_llm:
            result = apply_calibration_to_result(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py -q
```

Expected: all tests in the file pass.

---

### Task 5: Verification

**Files:**
- Test only

- [ ] **Step 1: Run focused tests**

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m pytest tests/test_competition_calibration_service.py tests/test_pipeline_video_payload.py tests/test_ai_jury_services.py -q
```

Expected: pass.

- [ ] **Step 2: Inspect imports**

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring
python -m compileall app/services/official_rubric_service.py app/services/demo_evidence_service.py app/services/competition_calibration_service.py app/services/pipeline_service.py
```

Expected: no syntax errors.

---

## Later Phase Backlog

These are intentionally not implemented in this P0 slice:

- Database-backed `score_memory_item`, `score_evidence_anchor`, and `improvement_task`.
- Historical issue recheck against previous assessment rounds.
- Frontend display of skill score, demo level, and calibration reasons.
- Jury prompt/schema update to include official rubric and demo review output.
- PDF report layout changes.

Each of those should get its own implementation plan after P0 is verified.

---

## Self-Review

- Spec coverage: P0 covers official rubric normalization, gradient evidence detection, demo-first technical ceiling, and pipeline result attachment.
- Known gap: long-term memory storage is not included; this is deliberate because it needs schema/API work and should be a separate plan.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: all new services exchange plain dictionaries and match existing pipeline result shape.
