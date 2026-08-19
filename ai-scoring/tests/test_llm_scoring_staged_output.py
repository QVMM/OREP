import json
from types import SimpleNamespace

from app.services import llm_scoring_service


ITEMS = {
    "skill_level": ("技能水平", [("操作规范性", 10), ("技能熟练度", 15), ("任务难易度", 15), ("技术先进性", 15), ("现场讲解效果", 5)]),
    "professionalism": ("职业素养", [("职业道德与行为规范", 4), ("工匠精神", 3), ("安全意识", 3)]),
    "application_value": ("应用价值", [("实用性", 4), ("经济性", 3), ("可持续性", 3)]),
    "teamwork": ("团队合作", [("团队精神", 5), ("沟通协作", 5)]),
    "innovation": ("创新创意", [("创新意识", 4), ("创新成效", 6)]),
}


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def model_response(payload, *, finish_reason="stop", completion_tokens=100):
    content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=200, completion_tokens=completion_tokens, total_tokens=200 + completion_tokens),
    )


def core_payload():
    dimensions = {}
    for key, (name, item_specs) in ITEMS.items():
        items = [
            {"name": item_name, "max_score": max_score, "score": max_score / 2, "reason": f"{item_name}证据", "improvement": f"补{item_name}证据"}
            for item_name, max_score in item_specs
        ]
        dimensions[key] = {"name": name, "max_score": sum(item["max_score"] for item in items), "score": 0, "items": items}
    return {
        "overall_score": 0,
        "score_overview": {"diagnosis": "证据完整度一般", "highlights": ["演示"], "key_issues": ["数据"]},
        "dimensions": dimensions,
        "highlights": ["有演示"],
        "critical_issues": ["数据不足"],
        "evidence_summary": {"verbal_evidence_count": 8, "visual_evidence_count": 3, "cross_validated_count": 2},
        "improvement_priorities": [{"priority": 1, "dimension": "应用价值", "issue": "数据不足", "suggestion": "补数据"}],
    }


def evidence_payload():
    return {
        "evidence_audit": [{"level": "强证据", "claim": "演示", "source": "12:30", "impact": "技能熟练度"}],
        "audio_visual_fusion": {"summary": "一致", "contradictions": [], "metrics": []},
        "pitch_structure_benchmark": [{"stage": "方案展示", "time_range": "10-20min", "score": 7, "actual": "完成", "gap": "数据少", "fix": "补数据"}],
        "judge_questioning": [{"judge_type": "规范审查型", "focus": "标准", "question": "版本？", "why_it_matters": "影响规范", "prep_evidence": "标准文件"}],
    }


def jury_payload():
    return {
        "jury_review": [
            {"judge_code": f"J{i}", "judge_type": f"评委{i}", "score": 50 + i, "focus": "关注", "rubric_focus": "观测点", "comment": "独立点评", "recognition": "认可", "concern": "担忧", "challenge_question": "追问"}
            for i in range(1, 10)
        ],
        "action_plan": [{"priority": "P0", "title": "补证据", "problem": "数据少", "method": "补报告", "owner": "技术", "timebox": "3天", "acceptance": "可追溯"}],
        "team_optimization": [{"priority": "P0", "role": "主讲", "issue": "重点弱", "training": "限时", "target": "讲清"}],
        "final_verdict": {"summary": "可提升", "jury_summary": "证据不足", "defensible_strengths": ["演示"], "critical_deductions": ["数据"], "next_round_focus": ["补证据"], "priority_actions": []},
    }


def score(monkeypatch, responses):
    client = FakeClient(responses)
    monkeypatch.setattr(llm_scoring_service, "get_client", lambda provider: client)
    result = llm_scoring_service.score_roadshow(
        {"duration": 3270, "segments": [{"speaker": "选手1", "start": 0, "text": "我们完成了现场演示。"}]},
        {"speech_rate": {"global_chars_per_minute": 220}, "pauses": {"total_pauses": 2}, "fillers": {"total_fillers": 1}, "prosody": {"f0_std_hz": 20}},
        {"project_name": "测试项目", "track": "新一代信息技术赛道", "team_size": 4},
        ppt_recognition=False,
    )
    return client, result


def _core_skill_payload():
    full = core_payload()
    return {"dimensions": {"skill_level": full["dimensions"]["skill_level"]}}


def _core_support_payload():
    full = core_payload()
    dims = {
        key: full["dimensions"][key]
        for key in ("professionalism", "application_value", "teamwork", "innovation")
    }
    return {"dimensions": dims}


def _core_overview_payload():
    full = core_payload()
    return {
        "score_overview": full["score_overview"],
        "highlights": full["highlights"],
        "critical_issues": full["critical_issues"],
        "evidence_summary": full["evidence_summary"],
        "improvement_priorities": full["improvement_priorities"],
    }


def test_score_roadshow_runs_segmented_core_then_evidence_and_jury(monkeypatch):
    client, result = score(monkeypatch, [
        model_response(_core_skill_payload(), completion_tokens=400),
        model_response(_core_support_payload(), completion_tokens=400),
        model_response(_core_overview_payload(), completion_tokens=200),
        model_response(evidence_payload(), completion_tokens=900),
        model_response(jury_payload(), completion_tokens=1100),
    ])

    # 3 core batches + evidence + jury
    assert len(client.chat.completions.calls) == 5
    assert result["overall_score"] == 50.0
    assert sum(len(dim["items"]) for dim in result["dimensions"].values()) == 15
    assert len(result["jury_review"]) == 9
    assert result["status"] == "completed"
    assert result["generation_meta"]["core"]["status"] == "completed"
    assert result["generation_meta"]["core"]["mode"] == "segmented_dimensions"
    assert result["tokens_used"]["completion_tokens"] == 3000


def test_core_truncation_exhausts_skill_batch_returns_null_score(monkeypatch):
    # skill batch fails all 3 attempts → core incomplete
    _, result = score(monkeypatch, [
        model_response('{"dimensions":', finish_reason="length", completion_tokens=8000),
        model_response('{"dimensions":', finish_reason="length", completion_tokens=8000),
        model_response('{"dimensions":', finish_reason="length", completion_tokens=8000),
    ])

    assert result["overall_score"] is None
    assert result["dimensions"] == {}
    assert result["status"] == "review_required"
    assert result["error_code"] == "core_scoring_incomplete"
    assert result["generation_meta"]["core"]["attempts"] == 3


def test_deep_stage_failure_keeps_core_score_but_marks_report_for_review(monkeypatch):
    client, result = score(monkeypatch, [
        model_response(_core_skill_payload()),
        model_response(_core_support_payload()),
        model_response(_core_overview_payload()),
        model_response("not-json"),
        model_response("still-not-json"),
    ])

    assert len(client.chat.completions.calls) == 5
    assert result["overall_score"] == 50.0
    assert result["status"] == "scoring_completed_report_review_required"
    assert result["error_code"] == "evidence_analysis_incomplete"
    assert result["generation_meta"]["evidence"]["status"] == "failed"
    assert "jury" not in result["generation_meta"]


def test_comparison_mode_preserves_null_review_score(monkeypatch):
    monkeypatch.setattr(llm_scoring_service, "score_roadshow", lambda *args, **kwargs: {
        "overall_score": None,
        "status": "review_required",
        "dimensions": {},
    })

    result = llm_scoring_service.score_with_comparison({}, {}, {})

    assert result["comparison"]["recommended_score"] is None
    assert result["comparison"]["consistency"] == "待复核"
