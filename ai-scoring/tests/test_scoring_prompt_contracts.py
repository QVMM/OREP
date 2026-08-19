import copy

import pytest

from app.services.scoring_prompt_contracts import (
    JURY_OUTPUT_SCHEMA,
    merge_staged_outputs,
    validate_core_output,
    validate_evidence_output,
    validate_jury_output,
)
from app.services.llm_scoring_service import OUTPUT_FORMAT, _backfill_reference_report_sections


def test_action_plan_contract_requests_rule_links_but_never_model_score_claims():
    assert '"observation_codes"' in JURY_OUTPUT_SCHEMA
    assert '"criterion_codes"' in JURY_OUTPUT_SCHEMA
    assert '"dimension_code"' in JURY_OUTPUT_SCHEMA
    assert '"impact_type"' in JURY_OUTPUT_SCHEMA
    assert '"expected_gain"' not in JURY_OUTPUT_SCHEMA


def test_legacy_full_prompt_uses_the_same_rule_link_contract():
    assert '"observation_codes"' in OUTPUT_FORMAT
    assert '"criterion_codes"' in OUTPUT_FORMAT
    assert '"impact_type"' in OUTPUT_FORMAT
    assert '"expected_gain"' not in OUTPUT_FORMAT


def test_reference_backfill_never_invents_expected_gain():
    result = {
        "score_overview": {"diagnosis": "演示需要加固"},
        "highlights": ["方案完整"],
        "critical_issues": ["演示故障"],
        "improvement_priorities": [{
            "priority": 1,
            "dimension": "技能水平",
            "issue": "演示故障",
            "suggestion": "完成五次稳定性测试",
        }],
    }

    _backfill_reference_report_sections(result)

    action = result["final_verdict"]["priority_actions"][0]
    assert "expected_gain" not in action
    assert action["acceptance"]


ITEMS = {
    "skill_level": ("技能水平", [("操作规范性", 10), ("技能熟练度", 15), ("任务难易度", 15), ("技术先进性", 15), ("现场讲解效果", 5)]),
    "professionalism": ("职业素养", [("职业道德与行为规范", 4), ("工匠精神", 3), ("安全意识", 3)]),
    "application_value": ("应用价值", [("实用性", 4), ("经济性", 3), ("可持续性", 3)]),
    "teamwork": ("团队合作", [("团队精神", 5), ("沟通协作", 5)]),
    "innovation": ("创新创意", [("创新意识", 4), ("创新成效", 6)]),
}


def core_output():
    dimensions = {}
    for key, (name, item_specs) in ITEMS.items():
        items = [
            {
                "name": item_name,
                "max_score": max_score,
                "score": max_score / 2,
                "reason": f"证据支持{item_name}",
                "improvement": f"补齐{item_name}证据",
            }
            for item_name, max_score in item_specs
        ]
        dimensions[key] = {
            "name": name,
            "max_score": sum(item["max_score"] for item in items),
            "score": 999,
            "items": items,
        }
    return {
        "overall_score": 999,
        "score_overview": {"diagnosis": "证据完整度一般", "highlights": ["演示"], "key_issues": ["数据"]},
        "dimensions": dimensions,
        "highlights": ["有现场演示"],
        "critical_issues": ["缺少量化数据"],
        "evidence_summary": {"verbal_evidence_count": 10, "visual_evidence_count": 4, "cross_validated_count": 2},
        "improvement_priorities": [{"priority": 1, "dimension": "应用价值", "issue": "数据不足", "suggestion": "补数据"}],
    }


def evidence_output():
    return {
        "evidence_audit": [{"level": "强证据", "claim": "演示完成", "source": "12:30画面", "impact": "技能熟练度"}],
        "audio_visual_fusion": {"summary": "音画一致", "contradictions": [], "metrics": []},
        "pitch_structure_benchmark": [{"stage": "方案展示", "time_range": "10-20min", "score": 7, "actual": "完成", "gap": "数据少", "fix": "补数据"}],
        "judge_questioning": [{"judge_type": "规范审查型", "focus": "标准", "question": "标准版本？", "why_it_matters": "影响规范性", "prep_evidence": "标准文件"}],
    }


def jury_output():
    return {
        "jury_review": [
            {
                "judge_code": f"J{index}",
                "judge_type": f"评委{index}",
                "score": 50 + index,
                "focus": "关注点",
                "rubric_focus": "观测点",
                "comment": "基于证据的独立点评",
                "recognition": "认可",
                "concern": "担忧",
                "challenge_question": "追问",
            }
            for index in range(1, 10)
        ],
        "action_plan": [{"priority": "P0", "title": "补证据", "problem": "数据少", "method": "补测试报告", "owner": "技术", "timebox": "3天", "acceptance": "报告可追溯"}],
        "team_optimization": [{"priority": "P0", "role": "主讲", "issue": "重点不突出", "training": "限时表达", "target": "3分钟讲清"}],
        "final_verdict": {"summary": "可提升", "jury_summary": "九评委认为证据不足", "defensible_strengths": ["演示"], "critical_deductions": ["数据"], "next_round_focus": ["补证据"], "priority_actions": []},
    }


def test_core_contract_requires_all_15_items_and_recomputes_scores():
    result = validate_core_output(core_output())

    assert sum(len(dim["items"]) for dim in result["dimensions"].values()) == 15
    assert result["overall_score"] == 50.0
    assert sum(dim["score"] for dim in result["dimensions"].values()) == 50.0


def test_core_contract_rejects_missing_observation_instead_of_backfilling():
    payload = core_output()
    payload["dimensions"]["skill_level"]["items"].pop()

    with pytest.raises(ValueError, match="core_items_incomplete"):
        validate_core_output(payload)


def test_evidence_and_jury_contracts_reject_missing_modules_or_judges():
    incomplete_evidence = evidence_output()
    incomplete_evidence.pop("judge_questioning")
    with pytest.raises(ValueError, match="evidence_modules_incomplete"):
        validate_evidence_output(incomplete_evidence)

    incomplete_jury = jury_output()
    incomplete_jury["jury_review"].pop()
    with pytest.raises(ValueError, match="jury_count_must_be_9"):
        validate_jury_output(incomplete_jury)


def test_merge_does_not_allow_later_stages_to_override_scores():
    core = validate_core_output(core_output())
    evidence = evidence_output()
    evidence["overall_score"] = 1
    jury = jury_output()
    jury["dimensions"] = {"fake": {"score": 100}}

    result = merge_staged_outputs(core, evidence, jury)

    assert result["overall_score"] == 50.0
    assert "fake" not in result["dimensions"]
    assert len(result["jury_review"]) == 9
