"""Prompt builders and deterministic contracts for staged five-dimension scoring."""

from __future__ import annotations

import copy
import json


EXPECTED_DIMENSIONS = {
    "skill_level": {
        "name": "技能水平",
        "items": {
            "操作规范性": 10.0,
            "技能熟练度": 15.0,
            "任务难易度": 15.0,
            "技术先进性": 15.0,
            "现场讲解效果": 5.0,
        },
    },
    "professionalism": {
        "name": "职业素养",
        "items": {"职业道德与行为规范": 4.0, "工匠精神": 3.0, "安全意识": 3.0},
    },
    "application_value": {
        "name": "应用价值",
        "items": {"实用性": 4.0, "经济性": 3.0, "可持续性": 3.0},
    },
    "teamwork": {
        "name": "团队合作",
        "items": {"团队精神": 5.0, "沟通协作": 5.0},
    },
    "innovation": {
        "name": "创新创意",
        "items": {"创新意识": 4.0, "创新成效": 6.0},
    },
}


CORE_OUTPUT_SCHEMA = r"""{
  "overall_score": 0-100（仅供参考，系统会按15项重算）, 
  "score_overview": {"diagnosis": "一句总诊断", "highlights": ["标签"], "key_issues": ["标签"]},
  "dimensions": {
    "skill_level": {"name":"技能水平","max_score":60,"score":0,"items":[
      {"name":"操作规范性","max_score":10,"score":0,"reason":"带原文/时间/画面依据的完整理由","improvement":"具体可执行建议"},
      {"name":"技能熟练度","max_score":15,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"任务难易度","max_score":15,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"技术先进性","max_score":15,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"现场讲解效果","max_score":5,"score":0,"reason":"完整理由","improvement":"具体建议"}
    ]},
    "professionalism": {"name":"职业素养","max_score":10,"score":0,"items":[
      {"name":"职业道德与行为规范","max_score":4,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"工匠精神","max_score":3,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"安全意识","max_score":3,"score":0,"reason":"完整理由","improvement":"具体建议"}
    ]},
    "application_value": {"name":"应用价值","max_score":10,"score":0,"items":[
      {"name":"实用性","max_score":4,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"经济性","max_score":3,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"可持续性","max_score":3,"score":0,"reason":"完整理由","improvement":"具体建议"}
    ]},
    "teamwork": {"name":"团队合作","max_score":10,"score":0,"items":[
      {"name":"团队精神","max_score":5,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"沟通协作","max_score":5,"score":0,"reason":"完整理由","improvement":"具体建议"}
    ]},
    "innovation": {"name":"创新创意","max_score":10,"score":0,"items":[
      {"name":"创新意识","max_score":4,"score":0,"reason":"完整理由","improvement":"具体建议"},
      {"name":"创新成效","max_score":6,"score":0,"reason":"完整理由","improvement":"具体建议"}
    ]}
  },
  "highlights": ["引用证据的亮点"],
  "critical_issues": ["引用证据或明确证据缺口的问题"],
  "evidence_summary": {"verbal_evidence_count":0,"visual_evidence_count":0,"cross_validated_count":0},
  "improvement_priorities": [{"priority":1,"dimension":"维度名","issue":"问题","suggestion":"建议"}]
}"""


EVIDENCE_OUTPUT_SCHEMA = r"""{
  "evidence_audit": [
    {"level":"强证据|弱证据|缺失证据|矛盾证据","claim":"结论或扣分点","source":"时间点/原文/画面摘要","impact":"维度或观测点"}
  ],
  "audio_visual_fusion": {
    "summary":"音画一致性综合判断",
    "contradictions":[{"time":"时间点或阶段","description":"矛盾描述","audio_score":null,"visual_score":null,"gap":"差距"}],
    "metrics":[{"name":"指标","average":"均值或结论","low":"风险","high":"亮点","trend":"趋势"}]
  },
  "pitch_structure_benchmark": [
    {"stage":"破冰钩子|问题共鸣|方案展示|证据验证|商业闭环|团队致胜|有力收尾","time_range":"时间段","score":0,"actual":"实际表现","gap":"差距","fix":"改进"}
  ],
  "judge_questioning": [
    {"judge_type":"评委类型","focus":"关注点","question":"可能追问","why_it_matters":"影响原因","prep_evidence":"需准备证据"}
  ]
}"""


JURY_OUTPUT_SCHEMA = r"""{
  "jury_review": [
    {"judge_code":"独立且不重复的代码","judge_type":"评委类型","score":0,"focus":"核心关注","rubric_focus":"重点评分项","comment":"基于真实证据的独立点评","recognition":"认可点","concern":"担忧点","challenge_question":"可能追问"}
  ],
  "action_plan": [
    {"priority":"P0|P1|P2","title":"行动标题","problem":"问题","method":"具体做法","owner":"负责角色","timebox":"时间建议","acceptance":"验收标准","observation_codes":["对应观测点代码，无法确定时为空数组"],"criterion_codes":["对应评分规则代码，无法确定时为空数组"],"dimension_code":"对应评分维度代码，无法确定时为空","source_issue_key":"对应问题键，无法确定时为空","impact_type":"deduction_recovery|evidence_unlock|performance_improvement|unlinked"}
  ],
  "team_optimization": [
    {"priority":"P0|P1|P2","role":"角色","issue":"短板","training":"训练动作","target":"验收目标"}
  ],
  "final_verdict": {
    "summary":"一句话总评","jury_summary":"九评委综合评价","defensible_strengths":["优势"],"critical_deductions":["扣分项"],"next_round_focus":["下轮重点"],
    "priority_actions":[{"priority":"P0|P1|P2","item":"改进项","owner":"负责人角色","acceptance":"验收标准；不得自行估算分数"}]
  }
}
注意：jury_review 必须恰好包含9位关注点不同的独立评委，不得复制或合并。"""


def build_evidence_snapshot(
    *,
    project_info: dict,
    duration_seconds: float,
    transcript_text: str,
    speech_quality: dict,
    audio_description: str,
    fusion_description: str = "",
    visual_evidence: str = "",
    duration_note: str | None = None,
    ppt_recognition: bool = False,
    persona_context: dict | None = None,
) -> str:
    snapshot = [
        "## 路演与评分证据快照（A/B/C阶段必须使用同一快照）",
        f"- 参赛项目：{project_info.get('project_name', '未命名项目')}",
        f"- 参赛赛道：{project_info.get('track', '未指定赛道')}",
        f"- 团队人数：{project_info.get('team_size', 4)}人",
        f"- 路演时长：{round(duration_seconds, 1)}秒（约{round(duration_seconds / 60, 1)}分钟）",
        f"- 音频来源：{audio_description}",
        "- 赛制口径：按职业院校技能大赛60分钟路演分析，50-60分钟为合理完成区间，约54分钟不得按10-15分钟商业路演判超时。",
        "",
        "## 路演全文（按说话人与时间）",
        transcript_text,
        "",
        "## 语音质量数据",
        json.dumps(speech_quality or {}, ensure_ascii=False, separators=(",", ":")),
    ]
    if duration_note:
        snapshot.extend(["", "## 额外时长说明", duration_note])
    if fusion_description:
        snapshot.extend(["", fusion_description])
    if visual_evidence:
        snapshot.extend(["", visual_evidence])
    if not ppt_recognition:
        snapshot.extend([
            "",
            "## 模式约束",
            "本次无可用PPT视觉识别时，不得编造画面，也不得仅因缺少PPT额外扣分；按现有语音和代码演示证据保守判断。",
        ])
    if persona_context:
        snapshot.extend([
            "",
            "## 独立评委视角",
            json.dumps(persona_context, ensure_ascii=False, separators=(",", ":")),
            "该视角只影响关注重点和建议表达，不得改变统一评分规则。最终输出额外包含 persona_view。",
        ])
    return "\n".join(snapshot)


def build_core_prompt(snapshot: str) -> str:
    return (
        f"{snapshot}\n\n"
        "## 阶段A：核心评分\n"
        "只生成核心评分。15个观测点一个不能少。"
        "每项 reason/improvement 各用1-2句中文写清依据与建议，必须可追溯到证据，禁止空话，禁止省略号截断字段。"
        "后续阶段无权改分。严格输出以下JSON，不要输出其他文字：\n"
        f"{CORE_OUTPUT_SCHEMA}"
    )


def build_core_dimensions_schema(dimension_keys: list[str]) -> str:
    """Compact schema for one or more dimensions only."""
    dims = []
    for key in dimension_keys:
        expected = EXPECTED_DIMENSIONS[key]
        items = ", ".join(
            f'{{"name":"{name}","max_score":{max_score},"score":0,'
            f'"reason":"1-2句含证据","improvement":"1-2句可执行建议"}}'
            for name, max_score in expected["items"].items()
        )
        dims.append(
            f'"{key}":{{"name":"{expected["name"]}","max_score":'
            f'{round(sum(expected["items"].values()), 2)},"score":0,"items":[{items}]}}'
        )
    return '{"dimensions":{' + ",".join(dims) + "}}"


def build_core_dimensions_prompt(snapshot: str, dimension_keys: list[str]) -> str:
    names = "、".join(EXPECTED_DIMENSIONS[key]["name"] for key in dimension_keys)
    return (
        f"{snapshot}\n\n"
        f"## 阶段A-维度批：仅评分 {names}\n"
        "只输出本批次 dimensions 中的观测点；每个 reason/improvement 各 1-2 句，"
        "必须引用证据快照中的时间/原文/画面，不得编造，禁止省略号，禁止输出其他维度。\n"
        f"严格输出：\n{build_core_dimensions_schema(dimension_keys)}"
    )


def build_core_overview_prompt(snapshot: str, dimensions: dict) -> str:
    return (
        f"{snapshot}\n\n"
        "## 已完成的维度评分（只能引用，不得改分）\n"
        f"{json.dumps(dimensions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 阶段A-总览\n"
        "基于已有维度分与证据快照，补齐总览字段；不得改写 dimensions 分数。\n"
        "严格输出：\n"
        '{"score_overview":{"diagnosis":"一句总诊断","highlights":["标签"],"key_issues":["标签"]},'
        '"highlights":["引用证据的亮点"],"critical_issues":["引用证据或证据缺口的问题"],'
        '"evidence_summary":{"verbal_evidence_count":0,"visual_evidence_count":0,"cross_validated_count":0},'
        '"improvement_priorities":[{"priority":1,"dimension":"维度名","issue":"问题","suggestion":"建议"}]}'
    )


def validate_core_dimensions_batch(payload: dict, expected_keys: list[str]) -> dict:
    """Validate a partial core payload that only contains selected dimensions."""
    result = copy.deepcopy(payload)
    dimensions = result.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(expected_keys):
        raise ValueError("core_dimensions_batch_incomplete")
    # Reuse full validator shape by filling missing dims with empty placeholders
    # is unsafe; validate each selected dim against EXPECTED_DIMENSIONS.
    for dimension_key in expected_keys:
        expected = EXPECTED_DIMENSIONS[dimension_key]
        dimension = dimensions[dimension_key]
        if not isinstance(dimension, dict):
            raise ValueError("core_dimension_invalid")
        items = dimension.get("items")
        expected_items = expected["items"]
        if not isinstance(items, list) or len(items) != len(expected_items):
            raise ValueError("core_items_incomplete")
        item_map = {item.get("name"): item for item in items if isinstance(item, dict)}
        if set(item_map) != set(expected_items) or len(item_map) != len(items):
            raise ValueError("core_items_incomplete")
        dimension_score = 0.0
        for item_name, expected_max in expected_items.items():
            item = item_map[item_name]
            max_score = _number(item.get("max_score"), "core_item_max_invalid")
            score = _number(item.get("score"), "core_item_score_invalid")
            if abs(max_score - expected_max) > 0.001:
                raise ValueError("core_item_max_invalid")
            if score < 0 or score > expected_max:
                raise ValueError("core_item_score_out_of_range")
            if not _has_text(item.get("reason")) or not _has_text(item.get("improvement")):
                raise ValueError("core_item_explanation_incomplete")
            item["max_score"] = expected_max
            item["score"] = round(score, 2)
            dimension_score += item["score"]
        dimension["name"] = expected["name"]
        dimension["max_score"] = round(sum(expected_items.values()), 2)
        dimension["score"] = round(dimension_score, 2)
        dimension["items"] = [item_map[name] for name in expected_items]
    result["dimensions"] = {key: dimensions[key] for key in expected_keys}
    return result


def validate_core_overview(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    if not isinstance(result.get("score_overview"), dict) or not result["score_overview"]:
        raise ValueError("core_score_overview_incomplete")
    for field in ("highlights", "critical_issues", "improvement_priorities"):
        if not isinstance(result.get(field), list) or not result[field]:
            raise ValueError(f"core_{field}_incomplete")
    evidence_summary = result.get("evidence_summary")
    if not isinstance(evidence_summary, dict) or not evidence_summary:
        raise ValueError("core_evidence_summary_incomplete")
    return result


def build_evidence_prompt(snapshot: str, core: dict) -> str:
    return (
        f"{snapshot}\n\n"
        "## 已通过门禁的阶段A核心评分（只能引用，不得重评分）\n"
        f"{json.dumps(core, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 阶段B：证据与结构深度分析\n"
        "完整生成四个模块，结论必须引用阶段A观测点与共享证据，不得输出或改写overall_score、dimensions。"
        "严格输出以下JSON，不要输出其他文字：\n"
        f"{EVIDENCE_OUTPUT_SCHEMA}"
    )


def build_jury_prompt(snapshot: str, core: dict, evidence: dict, *, require_persona_view: bool = False) -> str:
    persona_instruction = (
        "并额外输出 persona_view={persona_code,role_label,top_concerns,score_reasoning_style,optimization_angle}。"
        if require_persona_view else ""
    )
    return (
        f"{snapshot}\n\n"
        "## 已通过门禁的阶段A核心评分（不得改分）\n"
        f"{json.dumps(core, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 已通过门禁的阶段B证据与结构结论\n"
        f"{json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 阶段C：九评委与行动方案\n"
        "完整生成恰好9位不同关注点的独立评委，以及行动计划、团队优化和最终结论。"
        "不得输出或改写overall_score、dimensions。" + persona_instruction +
        "严格输出以下JSON，不要输出其他文字：\n" + JURY_OUTPUT_SCHEMA
    )


def validate_core_output(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    dimensions = result.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(EXPECTED_DIMENSIONS):
        raise ValueError("core_dimensions_incomplete")

    overall = 0.0
    observed_names: list[str] = []
    for dimension_key, expected in EXPECTED_DIMENSIONS.items():
        dimension = dimensions[dimension_key]
        if not isinstance(dimension, dict):
            raise ValueError("core_dimension_invalid")
        items = dimension.get("items")
        expected_items = expected["items"]
        if not isinstance(items, list) or len(items) != len(expected_items):
            raise ValueError("core_items_incomplete")
        item_map = {item.get("name"): item for item in items if isinstance(item, dict)}
        if set(item_map) != set(expected_items) or len(item_map) != len(items):
            raise ValueError("core_items_incomplete")

        dimension_score = 0.0
        for item_name, expected_max in expected_items.items():
            item = item_map[item_name]
            max_score = _number(item.get("max_score"), "core_item_max_invalid")
            score = _number(item.get("score"), "core_item_score_invalid")
            if abs(max_score - expected_max) > 0.001:
                raise ValueError("core_item_max_invalid")
            if score < 0 or score > expected_max:
                raise ValueError("core_item_score_out_of_range")
            if not _has_text(item.get("reason")) or not _has_text(item.get("improvement")):
                raise ValueError("core_item_explanation_incomplete")
            item["max_score"] = expected_max
            item["score"] = round(score, 2)
            dimension_score += item["score"]
            observed_names.append(item_name)

        dimension["name"] = expected["name"]
        dimension["max_score"] = round(sum(expected_items.values()), 2)
        dimension["score"] = round(dimension_score, 2)
        dimension["items"] = [item_map[name] for name in expected_items]
        overall += dimension["score"]

    if len(observed_names) != 15 or len(set(observed_names)) != 15:
        raise ValueError("core_items_incomplete")
    for field in ("score_overview", "evidence_summary"):
        if not isinstance(result.get(field), dict) or not result[field]:
            raise ValueError(f"core_{field}_incomplete")
    for field in ("highlights", "critical_issues", "improvement_priorities"):
        if not isinstance(result.get(field), list) or not result[field]:
            raise ValueError(f"core_{field}_incomplete")

    result["overall_score"] = round(overall, 2)
    return result


def validate_evidence_output(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    required = {
        "evidence_audit": list,
        "audio_visual_fusion": dict,
        "pitch_structure_benchmark": list,
        "judge_questioning": list,
    }
    if any(not isinstance(result.get(field), kind) or not result[field] for field, kind in required.items()):
        raise ValueError("evidence_modules_incomplete")
    return result


def validate_jury_output(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    jury = result.get("jury_review")
    if not isinstance(jury, list) or len(jury) != 9:
        raise ValueError("jury_count_must_be_9")
    required_judge_fields = (
        "judge_code", "judge_type", "score", "focus", "rubric_focus", "comment",
        "recognition", "concern", "challenge_question",
    )
    codes = []
    for judge in jury:
        if not isinstance(judge, dict) or any(not _has_text(judge.get(field)) for field in required_judge_fields if field != "score"):
            raise ValueError("jury_member_incomplete")
        score = _number(judge.get("score"), "jury_score_invalid")
        if score < 0 or score > 100:
            raise ValueError("jury_score_invalid")
        judge["score"] = round(score, 2)
        codes.append(str(judge["judge_code"]).strip())
    if len(set(codes)) != 9:
        raise ValueError("jury_members_must_be_independent")
    for field, kind in (("action_plan", list), ("team_optimization", list), ("final_verdict", dict)):
        if not isinstance(result.get(field), kind) or not result[field]:
            raise ValueError("jury_action_modules_incomplete")
    return result


def merge_staged_outputs(core: dict, evidence: dict, jury: dict) -> dict:
    result = copy.deepcopy(core)
    for field in ("evidence_audit", "audio_visual_fusion", "pitch_structure_benchmark", "judge_questioning"):
        result[field] = copy.deepcopy(evidence[field])
    for field in ("jury_review", "action_plan", "team_optimization", "final_verdict", "persona_view"):
        if field in jury:
            result[field] = copy.deepcopy(jury[field])
    result["status"] = "completed"
    result["score_authority"] = "staged_llm_recomputed"
    return result


def _number(value, error_code: str) -> float:
    if isinstance(value, bool):
        raise ValueError(error_code)
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(error_code) from None


def _has_text(value) -> bool:
    return value is not None and bool(str(value).strip())
