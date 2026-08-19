import pytest

from app.services.pipeline_service import (
    LLMScoringIncomplete,
    _build_ai_score_payload,
    _ensure_llm_result_complete,
)


def test_pipeline_payload_preserves_staged_audit_and_does_not_default_null_to_zero():
    raw = {
        "overall_score": None,
        "status": "review_required",
        "score_authority": "none",
        "error_code": "core_scoring_incomplete",
        "generation_meta": {"core": {"status": "failed", "attempts": 2}},
        "dimensions": {},
        "critical_issues": ["评分生成未完成"],
    }

    payload = _build_ai_score_payload(raw)

    assert payload["overall_score"] is None
    assert payload["status"] == "review_required"
    assert payload["generation_meta"]["core"]["attempts"] == 2


def test_pipeline_stops_before_report_when_any_staged_output_requires_review():
    with pytest.raises(LLMScoringIncomplete, match="core_scoring_incomplete"):
        _ensure_llm_result_complete({
            "overall_score": None,
            "status": "review_required",
            "error_code": "core_scoring_incomplete",
        })

    with pytest.raises(LLMScoringIncomplete, match="jury_action_analysis_incomplete"):
        _ensure_llm_result_complete({
            "overall_score": 63.5,
            "status": "scoring_completed_report_review_required",
            "error_code": "jury_action_analysis_incomplete",
        })


def test_pipeline_accepts_only_complete_staged_output():
    _ensure_llm_result_complete({
        "overall_score": 63.5,
        "status": "completed",
        "generation_meta": {
            "core": {"status": "completed"},
            "evidence": {"status": "completed"},
            "jury": {"status": "completed"},
        },
    })
