"""
路演训练建议生成服务。
把评分结果中的语音停顿、转写上下文和扣分项交给大模型，生成面向参赛队的训练建议。
"""
import json
import logging
import os
import re
from datetime import datetime, timezone

from app.config import settings
from app.services.llm_scoring_service import MODEL_MAP, get_client, _sanitize_competition_duration

logger = logging.getLogger(__name__)
EXPRESSION_CACHE_VERSION = "expression-coaching-v2"
PRESENTATION_CACHE_VERSION = "presentation-coaching-v2"
ACTION_PLAN_CACHE_VERSION = "action-plan-coaching-v2"


EXPRESSION_COACH_PROMPT = """你是一名职业院校技能大赛路演表达教练。请基于真实评分数据，为参赛队生成表达节奏训练建议。

要求：
1. 只能依据输入的停顿片段、转写上下文、评分扣分项和改进优先级分析，不要编造不存在的事实。
2. 建议要面向职业院校技能大赛路演彩排，可执行、具体、专业。
3. 不要把原文简单截断后当作建议；建议必须解释为什么停顿、怎么训练、下一次怎么处理。
4. 如果是成员交接、设备等待、功能演示、代码讲解、问答故障等场景，要分别给出不同训练动作。
5. 本系统面向职业院校技能大赛路演评分，默认赛制按 60 分钟路演分析；50-60 分钟属于合理完成区间。禁止按商业路演、创业路演或 10-15 分钟路演口径给建议。
6. 当路演时长约 54 分钟时，不得写“超时”“时间严重超时”“应精简至10-15分钟”等结论；如需评价节奏，只能指出具体环节分配不均、代码讲解冗长、故障冷场、转场空档等可观察问题。
7. 输出必须是合法 JSON，不要输出 JSON 之外的文字。

输出格式：
{
  "summary_title": "一句话诊断标题",
  "summary": "80-140字总体判断",
  "cards": [
    {"label": "节奏判断", "value": "简短指标", "advice": "一句训练建议"},
    {"label": "停顿风险", "value": "简短指标", "advice": "一句训练建议"},
    {"label": "口头禅", "value": "简短指标", "advice": "一句训练建议"},
    {"label": "训练优先级", "value": "简短指标", "advice": "一句训练建议"}
  ],
  "moments": [
    {
      "id": "输入片段id",
      "time": "MM:SS",
      "title": "该片段的问题标题",
      "original": "保留输入中的原始上下文摘要",
      "coach_advice": "针对该片段的训练动作，必须具体到路演彩排怎么做"
    }
  ],
  "training": [
    {"title": "训练动作标题", "detail": "训练方法，必须可执行"}
  ]
}
"""


PRESENTATION_COACH_PROMPT = """你是一名职业院校技能大赛路演现场呈现教练，同时熟悉评委视角、功能演示复盘和团队站位训练。请基于真实评分数据，为参赛队生成“现场呈现”复盘建议。

这里的“现场呈现”不是泛泛评价画面好不好，而是回答三个问题：
1. 评委在关键环节是否能同时看懂“主讲人在讲什么、屏幕在证明什么、团队动作在服务什么”。
2. 哪些片段会让评委理解成本升高，例如讲解和屏幕不同步、成员遮挡屏幕、站位不服务当前主讲、代码/界面缺少价值解释、转场没有承接话术。
3. 下一轮彩排中，选手应该如何改站位、指屏幕、切页面、交接、补一句话术。

要求：
1. 只能依据输入的关键帧摘要、屏幕识别、音画融合时间窗、语音片段和评分扣分项分析，不要编造不存在的事实。
2. 面向职业院校技能大赛路演队伍，建议必须具体、可训练、可执行。
3. 不要输出“回看该片段”这种空泛建议，必须给出下一轮怎么做。
4. 本系统默认赛制按 60 分钟路演分析；50-60 分钟属于合理完成区间。禁止按商业路演、创业路演或 10-15 分钟路演口径给建议。
5. 当路演时长约 54 分钟时，不得写“超时”“时间严重超时”“应精简至10-15分钟”等结论；如需评价节奏，只能指出具体环节分配、故障冷场、演示转场等可观察问题。
6. 不得建议使用输入中没有出现的资源或设备，例如“备用录播视频”“白板”“激光笔”“额外屏幕”。如果需要指示动作，只能使用常规站位、手势指向、屏幕切换、口头承接、成员交接、PPT页面补充这类默认可执行动作。
7. 输出必须是合法 JSON，不要输出 JSON 之外的文字。

输出格式：
{
  "summary_title": "一句话诊断标题",
  "summary": "100-160字总体判断，必须站在评委理解成本视角",
  "judge_risk": {
    "level": "低|中|高",
    "focus": "最需要影响评委理解的一个呈现问题",
    "next_rehearsal_goal": "下一轮彩排的目标"
  },
  "phase_diagnostics": [
    {
      "id": "phase-0",
      "phase": "环节名称",
      "time_range": "MM:SS-MM:SS",
      "current_observation": "当前真实表现",
      "judge_view": "评委可能如何理解或卡住",
      "contestant_action": "下一轮选手应该怎么站、怎么指、怎么切屏或怎么交接",
      "recommended_line": "建议现场补充的一句话术"
    }
  ],
  "action_prescriptions": [
    {
      "title": "动作处方标题",
      "scenario": "适用场景",
      "standard_action": "标准动作",
      "line": "配套话术"
    }
  ],
  "moments": [
    {
      "id": "输入片段id",
      "time": "MM:SS",
      "position_seconds": 486,
      "title": "片段标题",
      "judge_view": "评委此时看到/听到什么",
      "problem": "为什么影响理解",
      "next_action": "下一轮具体动作",
      "recommended_line": "建议补充话术"
    }
  ]
}
"""


ACTION_PLAN_COACH_PROMPT = """你是一名职业院校技能大赛路演总教练。请基于真实评分结果，把前面所有分析收束成“下一轮提分作战台”。

这一页不是重复问题列表，也不是泛泛建议，而是要告诉参赛队：
1. 下一轮彩排先改什么，为什么先改它。
2. 每个提分任务如何落地到 PPT、讲解词、演示动作、团队配合或数据证据。
3. 改完后如何验收，什么结果算合格。

要求：
1. 只能依据输入的评分维度、扣分项、语音表现、现场呈现、屏幕证据、关键片段和转写上下文分析，不要编造不存在的事实。
2. 不要重复“表达节奏”“现场呈现”页面已有的诊断标题，要把它们转成训练任务和验收标准。
3. 建议必须面向职业院校技能大赛 60 分钟路演彩排，具体、可执行、可验收。
4. 50-60 分钟属于合理完成区间。不得写“超时”“时间严重超时”“应精简至10-15分钟”等结论。可以建议优化环节分配、压缩冗余代码讲解、减少故障冷场。
5. 不得建议使用输入中没有出现的资源或设备，例如“备用录播视频”“白板”“激光笔”“额外屏幕”。允许建议补充 PPT 页面、图表、流程图、口头承接、屏幕切换、成员交接和站位调整。
6. 输出必须是合法 JSON，不要输出 JSON 之外的文字。

输出格式：
{
  "summary_title": "一句话作战目标",
  "summary": "100-160字说明这套提分方案为什么这样排序",
  "score_focus": {
    "current_score": 65.75,
    "focus": "最核心提分抓手",
    "rehearsal_goal": "下一轮彩排目标"
  },
  "priority_map": [
    {
      "id": "priority-1",
      "rank": 1,
      "title": "提分点标题",
      "score_dimension": "影响评分维度",
      "impact": "高|中|低",
      "difficulty": "低|中|高",
      "evidence_basis": "对应证据，不超过60字",
      "why_first": "为什么优先处理"
    }
  ],
  "training_tasks": [
    {
      "id": "task-1",
      "title": "训练任务标题",
      "related_dimensions": ["技能水平"],
      "why_it_matters": "为什么影响得分",
      "evidence": "来自本次评分的证据",
      "change_actions": ["具体修改动作1", "具体修改动作2", "具体修改动作3"],
      "rehearsal_method": "下一轮彩排怎么练",
      "acceptance_standard": "什么结果算通过"
    }
  ],
  "script_rewrites": [
    {
      "id": "rewrite-1",
      "time": "MM:SS",
      "scenario": "适用场景",
      "original_problem": "原问题或原表达摘要",
      "suggested_line": "建议替换话术",
      "delivery_note": "说这句话时的现场动作或语气"
    }
  ],
  "material_checklist": [
    {
      "item": "材料项",
      "current_gap": "当前缺口",
      "required_change": "需要补什么",
      "done_standard": "完成标准"
    }
  ],
  "rehearsal_schedule": [
    {
      "segment": "训练段",
      "time_range": "MM:SS-MM:SS",
      "goal": "该段目标",
      "owner": "负责人或角色",
      "pass_standard": "通过标准"
    }
  ],
  "validation_checklist": [
    "验收项1"
  ]
}
"""


def get_expression_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek") -> dict:
    result = _load_result(meeting_id)
    cache_path = _coaching_cache_path(meeting_id, "expression")
    cache_key = _cache_key(result, EXPRESSION_CACHE_VERSION)

    if not refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("cache_key") == cache_key and cached.get("source") == "llm":
                return cached
        except Exception:
            logger.warning("表达训练建议缓存读取失败，将重新生成", exc_info=True)

    coaching = _generate_expression_coaching(result, provider)
    coaching.update({
        "meeting_id": meeting_id,
        "source": "llm",
        "provider": provider,
        "cache_key": cache_key,
        "generated_at": datetime.now(timezone.utc).isoformat()
    })

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(coaching, f, ensure_ascii=False, indent=2)
    return coaching


def get_presentation_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek") -> dict:
    result = _load_result(meeting_id)
    cache_path = _coaching_cache_path(meeting_id, "presentation")
    cache_key = _cache_key(result, PRESENTATION_CACHE_VERSION)

    if not refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("cache_key") == cache_key and cached.get("source") == "llm":
                return cached
        except Exception:
            logger.warning("现场呈现建议缓存读取失败，将重新生成", exc_info=True)

    coaching = _generate_presentation_coaching(result, provider)
    coaching.update({
        "meeting_id": meeting_id,
        "source": "llm",
        "provider": provider,
        "cache_key": cache_key,
        "generated_at": datetime.now(timezone.utc).isoformat()
    })

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(coaching, f, ensure_ascii=False, indent=2)
    return coaching


def get_action_plan_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek") -> dict:
    result = _load_result(meeting_id)
    cache_path = _coaching_cache_path(meeting_id, "action_plan")
    cache_key = _cache_key(result, ACTION_PLAN_CACHE_VERSION)

    if not refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("cache_key") == cache_key and cached.get("source") == "llm":
                return cached
        except Exception:
            logger.warning("提分方案缓存读取失败，将重新生成", exc_info=True)

    coaching = _generate_action_plan_coaching(result, provider)
    coaching.update({
        "meeting_id": meeting_id,
        "source": "llm",
        "provider": provider,
        "cache_key": cache_key,
        "generated_at": datetime.now(timezone.utc).isoformat()
    })

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(coaching, f, ensure_ascii=False, indent=2)
    return coaching


def _load_result(meeting_id: str) -> dict:
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"会议 {meeting_id} 的评分结果不存在")
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _coaching_cache_path(meeting_id: str, kind: str) -> str:
    return os.path.join(settings.UPLOAD_DIR, "results", f"{kind}_coaching_{meeting_id}.json")


def _cache_key(result: dict, version: str) -> str:
    return "|".join([
        version,
        str(result.get("completed_at") or ""),
        str(result.get("asr", {}).get("segment_count") or ""),
        str(result.get("video_analysis", {}).get("frame_count") or ""),
        str(len(result.get("fusion", {}).get("timeline") or [])),
        str(result.get("speech_quality", {}).get("duration") or result.get("asr", {}).get("duration") or ""),
        str(result.get("ai_score", {}).get("overall_score") or "")
    ])


def _generate_expression_coaching(result: dict, provider: str) -> dict:
    client = get_client(provider)
    model = MODEL_MAP.get(provider, MODEL_MAP["deepseek"])
    payload = _build_expression_payload(result)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXPRESSION_COACH_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        temperature=0.2,
        max_tokens=2800
    )
    content = response.choices[0].message.content or ""
    parsed = _parse_json_object(content)
    normalized = _normalize_expression_coaching(parsed, payload)
    duration = payload.get("meeting", {}).get("duration_seconds") or 0
    normalized = _sanitize_competition_duration(normalized, duration)
    return _sanitize_expression_duration_wording(normalized, duration)


def _generate_presentation_coaching(result: dict, provider: str) -> dict:
    client = get_client(provider)
    model = MODEL_MAP.get(provider, MODEL_MAP["deepseek"])
    payload = _build_presentation_payload(result)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PRESENTATION_COACH_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        temperature=0.2,
        max_tokens=3600
    )
    content = response.choices[0].message.content or ""
    parsed = _parse_json_object(content)
    normalized = _normalize_presentation_coaching(parsed, payload)
    duration = payload.get("meeting", {}).get("duration_seconds") or 0
    normalized = _sanitize_competition_duration(normalized, duration)
    return _sanitize_expression_duration_wording(normalized, duration)


def _generate_action_plan_coaching(result: dict, provider: str) -> dict:
    client = get_client(provider)
    model = MODEL_MAP.get(provider, MODEL_MAP["deepseek"])
    payload = _build_action_plan_payload(result)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ACTION_PLAN_COACH_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ],
        temperature=0.2,
        max_tokens=4200
    )
    content = response.choices[0].message.content or ""
    parsed = _parse_json_object(content)
    normalized = _normalize_action_plan_coaching(parsed, payload)
    duration = payload.get("meeting", {}).get("duration_seconds") or 0
    normalized = _sanitize_competition_duration(normalized, duration)
    return _sanitize_expression_duration_wording(normalized, duration)


def _build_expression_payload(result: dict) -> dict:
    speech = result.get("speech_quality", {}) or {}
    pauses = speech.get("pauses", {}) or {}
    fillers = speech.get("fillers", {}) or {}
    rate = speech.get("speech_rate", {}) or {}
    ai_score = result.get("ai_score", {}) or {}
    segments = result.get("asr", {}).get("segments") or []

    top_pauses = sorted(
        [item for item in pauses.get("details", []) if float(item.get("duration") or 0) >= 3],
        key=lambda item: float(item.get("duration") or 0),
        reverse=True
    )[:8]

    moments = []
    for index, pause in enumerate(top_pauses):
        seconds = float(pause.get("position_seconds") or 0)
        moments.append({
            "id": f"pause-{index}",
            "time": _format_time(seconds),
            "position_seconds": seconds,
            "duration": pause.get("duration"),
            "severity": pause.get("severity"),
            "context_before": pause.get("context_before", ""),
            "context_after": pause.get("context_after", ""),
            "nearby_transcript": _transcript_around(segments, seconds)
        })

    return {
        "meeting": {
            "duration_seconds": result.get("audio_info", {}).get("duration") or result.get("asr", {}).get("duration"),
            "overall_score": ai_score.get("overall_score"),
            "asr_source": result.get("asr", {}).get("source"),
        },
        "speech_metrics": {
            "global_chars_per_minute": rate.get("global_chars_per_minute"),
            "global_rating": rate.get("global_rating"),
            "ideal_range": rate.get("ideal_range"),
            "total_pauses": pauses.get("total_pauses"),
            "avg_pause_duration": pauses.get("avg_pause_duration"),
            "longest_pause": pauses.get("longest_pause"),
            "total_fillers": fillers.get("total_fillers"),
            "filler_rate_percent": fillers.get("filler_rate_percent"),
            "filler_types": fillers.get("filler_types", [])[:8],
            "overall_rating": speech.get("overall_rating"),
        },
        "critical_issues": ai_score.get("critical_issues", [])[:5],
        "improvement_priorities": ai_score.get("improvement_priorities", [])[:5],
        "moments": moments
    }


def _build_presentation_payload(result: dict) -> dict:
    video = result.get("video_analysis", {}) or {}
    aggregates = video.get("aggregates", {}) or {}
    screen_summary = aggregates.get("screen_content_summary", {}) or {}
    fusion = result.get("fusion", {}) or {}
    timeline = fusion.get("timeline") or []
    contradictions = fusion.get("contradictions") or []
    ai_score = result.get("ai_score", {}) or {}
    segments = result.get("asr", {}).get("segments") or []

    moments = []
    for index, item in enumerate(_select_presentation_moments(timeline, contradictions)):
        seconds = _moment_seconds(item)
        moments.append({
            "id": f"presentation-{index}",
            "time": _format_time(seconds),
            "position_seconds": round(seconds, 2),
            "source_type": item.get("_source_type"),
            "kind": item.get("kind"),
            "description": item.get("description"),
            "visual_score": item.get("visual_score"),
            "audio_score": item.get("audio_score"),
            "fusion_score": item.get("fusion_score"),
            "scene_type": item.get("scene_type"),
            "scene_has_screen": item.get("scene_has_screen"),
            "scene_people": item.get("scene_people"),
            "visual_impression": _clip(item.get("visual_impression"), 180),
            "gesture_desc": _clip(item.get("gesture_desc"), 120),
            "posture_desc": _clip(item.get("posture_desc"), 120),
            "eye_direction": item.get("eye_direction"),
            "text_preview": _clip(item.get("text_preview"), 180),
            "nearby_transcript": _clip(_transcript_around(segments, seconds), 260)
        })

    visible_texts = []
    for item in (screen_summary.get("visible_texts") or [])[:36]:
        visible_texts.append({
            "time": _format_time(float(item.get("timestamp_min") or 0) * 60),
            "text": _clip(item.get("text"), 160)
        })

    return {
        "meeting": {
            "duration_seconds": result.get("audio_info", {}).get("duration") or result.get("asr", {}).get("duration"),
            "overall_score": ai_score.get("overall_score"),
            "video_source": video.get("source"),
            "frame_count": video.get("frame_count"),
            "captured_frame_count": video.get("captured_frame_count")
        },
        "score_context": {
            "critical_issues": ai_score.get("critical_issues", [])[:5],
            "improvement_priorities": ai_score.get("improvement_priorities", [])[:5],
            "highlights": ai_score.get("highlights", [])[:5],
        },
        "visual_metrics": {
            "avg_gesture": aggregates.get("avg_gesture"),
            "avg_posture": aggregates.get("avg_posture"),
            "avg_expression": aggregates.get("avg_expression"),
            "avg_eye_contact": aggregates.get("avg_eye_contact"),
            "avg_visual_composite": aggregates.get("avg_visual_composite"),
            "scene_type_distribution": aggregates.get("scene_type_distribution"),
            "eye_direction_distribution": aggregates.get("eye_direction_distribution"),
        },
        "screen_evidence": {
            "screen_type_distribution": screen_summary.get("screen_type_distribution"),
            "content_type_counts": screen_summary.get("content_type_counts"),
            "has_ppt_evidence": screen_summary.get("has_ppt_evidence"),
            "evidence_diversity_score": screen_summary.get("evidence_diversity_score"),
            "visible_texts": visible_texts,
        },
        "fusion": {
            "summary": fusion.get("summary"),
            "contradiction_count": len(contradictions),
            "trend_summary": fusion.get("trends"),
        },
        "moments": moments
    }


def _build_action_plan_payload(result: dict) -> dict:
    ai_score = result.get("ai_score", {}) or {}
    speech = result.get("speech_quality", {}) or {}
    video = result.get("video_analysis", {}) or {}
    aggregates = video.get("aggregates", {}) or {}
    screen_summary = (aggregates.get("screen_content_summary") or {})
    fusion = result.get("fusion", {}) or {}
    timeline = fusion.get("timeline") or []
    contradictions = fusion.get("contradictions") or []
    segments = result.get("asr", {}).get("segments") or []

    dimensions = []
    for key, dim in (ai_score.get("dimensions") or {}).items():
        dimensions.append({
            "key": key,
            "name": dim.get("name") or key,
            "score": dim.get("score"),
            "max_score": dim.get("max_score") or dim.get("maxScore"),
            "items": [
                {
                    "name": item.get("name"),
                    "score": item.get("score"),
                    "comment": _clip(item.get("comment") or item.get("analysis") or item.get("suggestion"), 140)
                }
                for item in (dim.get("items") or [])[:5]
                if isinstance(item, dict)
            ],
            "improvement": dim.get("improvement") or dim.get("suggestions") or []
        })

    pauses = sorted(
        [item for item in (speech.get("pauses", {}) or {}).get("details", []) if NumberSafe(item.get("duration")) >= 3],
        key=lambda item: NumberSafe(item.get("duration")),
        reverse=True
    )[:8]
    pause_moments = []
    for index, pause in enumerate(pauses):
        seconds = NumberSafe(pause.get("position_seconds"))
        pause_moments.append({
            "id": f"pause-{index}",
            "time": _format_time(seconds),
            "position_seconds": seconds,
            "duration": pause.get("duration"),
            "severity": pause.get("severity"),
            "context": _clip(f"{pause.get('context_before', '')} / {pause.get('context_after', '')}".strip(" /"), 220)
        })

    presentation_moments = []
    for index, item in enumerate(_select_presentation_moments(timeline, contradictions)[:10]):
        seconds = _moment_seconds(item)
        presentation_moments.append({
            "id": f"presentation-{index}",
            "time": _format_time(seconds),
            "position_seconds": round(seconds, 2),
            "source_type": item.get("_source_type"),
            "kind": item.get("kind"),
            "description": item.get("description"),
            "visual_score": item.get("visual_score"),
            "audio_score": item.get("audio_score"),
            "fusion_score": item.get("fusion_score"),
            "visual_impression": _clip(item.get("visual_impression"), 180),
            "text_preview": _clip(item.get("text_preview"), 180),
            "nearby_transcript": _clip(_transcript_around(segments, seconds), 260)
        })

    visible_texts = []
    for item in (screen_summary.get("visible_texts") or [])[:30]:
        visible_texts.append({
            "time": _format_time(NumberSafe(item.get("timestamp_min")) * 60),
            "text": _clip(item.get("text"), 140)
        })

    return {
        "meeting": {
            "duration_seconds": result.get("audio_info", {}).get("duration") or result.get("asr", {}).get("duration"),
            "overall_score": ai_score.get("overall_score"),
            "asr_source": result.get("asr", {}).get("source"),
            "video_source": video.get("source"),
            "frame_count": video.get("frame_count"),
            "transcript_segments": result.get("asr", {}).get("segment_count"),
        },
        "score": {
            "dimensions": dimensions,
            "critical_issues": ai_score.get("critical_issues", [])[:6],
            "improvement_priorities": ai_score.get("improvement_priorities", [])[:8],
            "highlights": ai_score.get("highlights", [])[:5],
        },
        "speech": {
            "speech_rate": speech.get("speech_rate"),
            "pauses_summary": {
                "total_pauses": (speech.get("pauses", {}) or {}).get("total_pauses"),
                "longest_pause": (speech.get("pauses", {}) or {}).get("longest_pause"),
                "avg_pause_duration": (speech.get("pauses", {}) or {}).get("avg_pause_duration"),
            },
            "fillers": speech.get("fillers"),
            "pause_moments": pause_moments
        },
        "presentation": {
            "visual_metrics": {
                "avg_gesture": aggregates.get("avg_gesture"),
                "avg_posture": aggregates.get("avg_posture"),
                "avg_expression": aggregates.get("avg_expression"),
                "avg_eye_contact": aggregates.get("avg_eye_contact"),
                "avg_visual_composite": aggregates.get("avg_visual_composite"),
            },
            "screen_content_counts": screen_summary.get("content_type_counts"),
            "screen_type_distribution": screen_summary.get("screen_type_distribution"),
            "visible_texts": visible_texts,
            "fusion_summary": fusion.get("summary"),
            "contradiction_count": len(contradictions),
            "moments": presentation_moments
        }
    }


def _select_presentation_moments(timeline: list, contradictions: list) -> list:
    selected = []
    for item in contradictions[:8]:
        enriched = dict(item)
        enriched["_source_type"] = "contradiction"
        selected.append(enriched)

    sorted_timeline = sorted(
        [item for item in timeline if isinstance(item, dict)],
        key=lambda item: NumberSafe(item.get("fusion_score")),
    )
    for item in sorted_timeline[:6]:
        enriched = dict(item)
        enriched["_source_type"] = "low_fusion"
        selected.append(enriched)

    best_timeline = sorted(
        [item for item in timeline if isinstance(item, dict)],
        key=lambda item: NumberSafe(item.get("fusion_score")),
        reverse=True
    )
    for item in best_timeline[:4]:
        enriched = dict(item)
        enriched["_source_type"] = "strong_sample"
        selected.append(enriched)

    unique = []
    seen = set()
    for item in selected:
        seconds = round(_moment_seconds(item))
        if seconds in seen:
            continue
        seen.add(seconds)
        unique.append(item)
    return unique[:14]


def NumberSafe(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _moment_seconds(item: dict) -> float:
    if "position_seconds" in item:
        return NumberSafe(item.get("position_seconds"))
    return NumberSafe(item.get("time_min")) * 60


def _clip(value, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _transcript_around(segments: list, seconds: float) -> str:
    texts = []
    for segment in segments:
        start = float(segment.get("start") or 0)
        if abs(start - seconds) <= 18:
            text = str(segment.get("text") or "").strip()
            if text:
                texts.append(text)
    return " / ".join(texts[:5])


def _normalize_expression_coaching(data: dict, payload: dict) -> dict:
    moments_by_id = {item["id"]: item for item in payload.get("moments", [])}
    moments = []
    for item in data.get("moments", []):
        if not isinstance(item, dict):
            continue
        source = moments_by_id.get(item.get("id"), {})
        moments.append({
            "id": item.get("id") or source.get("id") or f"moment-{len(moments)}",
            "time": item.get("time") or source.get("time") or "",
            "title": item.get("title") or _default_moment_title(source),
            "original": item.get("original") or _default_original(source),
            "coach_advice": item.get("coach_advice") or ""
        })

    return {
        "summary_title": data.get("summary_title") or "表达节奏训练建议",
        "summary": data.get("summary") or "",
        "cards": _normalize_list(data.get("cards"), 4),
        "moments": moments,
        "training": _normalize_list(data.get("training"), 6),
    }


def _normalize_presentation_coaching(data: dict, payload: dict) -> dict:
    moments_by_id = {item["id"]: item for item in payload.get("moments", [])}
    moments = []
    for item in data.get("moments", []):
        if not isinstance(item, dict):
            continue
        source = moments_by_id.get(item.get("id"), {})
        seconds = item.get("position_seconds")
        if seconds is None:
            seconds = source.get("position_seconds")
        moments.append({
            "id": item.get("id") or source.get("id") or f"moment-{len(moments)}",
            "time": item.get("time") or source.get("time") or _format_time(NumberSafe(seconds)),
            "position_seconds": NumberSafe(seconds),
            "title": item.get("title") or "现场呈现复盘片段",
            "judge_view": item.get("judge_view") or "",
            "problem": item.get("problem") or "",
            "next_action": item.get("next_action") or "",
            "recommended_line": item.get("recommended_line") or "",
        })

    return {
        "summary_title": data.get("summary_title") or "现场呈现复盘建议",
        "summary": data.get("summary") or "",
        "judge_risk": _normalize_dict(data.get("judge_risk")),
        "phase_diagnostics": _normalize_list(data.get("phase_diagnostics"), 6),
        "action_prescriptions": _normalize_list(data.get("action_prescriptions"), 6),
        "moments": moments[:8],
    }


def _normalize_action_plan_coaching(data: dict, payload: dict) -> dict:
    score_focus = _normalize_dict(data.get("score_focus"))
    if "current_score" not in score_focus:
        score_focus["current_score"] = payload.get("meeting", {}).get("overall_score")

    return {
        "summary_title": data.get("summary_title") or "下一轮提分作战台",
        "summary": data.get("summary") or "",
        "score_focus": score_focus,
        "priority_map": _normalize_list(data.get("priority_map"), 5),
        "training_tasks": _normalize_list(data.get("training_tasks"), 5),
        "script_rewrites": _normalize_list(data.get("script_rewrites"), 6),
        "material_checklist": _normalize_list(data.get("material_checklist"), 8),
        "rehearsal_schedule": _normalize_list(data.get("rehearsal_schedule"), 8),
        "validation_checklist": [
            str(item).strip()
            for item in (data.get("validation_checklist") or [])
            if str(item).strip()
        ][:10],
    }


def _normalize_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _normalize_list(value, max_len: int) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)][:max_len]


def _default_moment_title(source: dict) -> str:
    if not source:
        return "需复盘片段"
    return f"{source.get('duration', '-')}s {source.get('severity', '')}停顿".strip()


def _default_original(source: dict) -> str:
    before = source.get("context_before", "")
    after = source.get("context_after", "")
    return f"{before} / {after}".strip(" /")


def _parse_json_object(content: str) -> dict:
    try:
        return json.loads(content, strict=False)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            raise ValueError("模型未返回合法 JSON")
        return json.loads(match.group(), strict=False)


def _sanitize_expression_duration_wording(value, duration_seconds: float):
    duration_minutes = float(duration_seconds or 0) / 60
    if not 50 <= duration_minutes <= 60:
        return value
    if isinstance(value, dict):
        return {key: _sanitize_expression_duration_wording(item, duration_seconds) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_expression_duration_wording(item, duration_seconds) for item in value]
    if isinstance(value, str):
        return (
            value
            .replace("54.4分钟超时", "54.4分钟符合60分钟赛制")
            .replace("54.4 分钟超时", "54.4 分钟符合60分钟赛制")
            .replace("54分钟超时", "54分钟符合60分钟赛制")
            .replace("54 分钟超时", "54 分钟符合60分钟赛制")
            .replace("超时导致", "环节分配不均导致")
            .replace("导致超时", "导致局部节奏拖长")
            .replace("每个模块超时", "每个模块超过预设时长")
            .replace("每个环节超时", "每个环节超过预设时长")
            .replace("不超时", "不超过预设时长")
            .replace("压缩至58-60分钟", "调整到50-60分钟赛制内")
            .replace("压缩到58-60分钟", "调整到50-60分钟赛制内")
            .replace("压缩时间", "优化时间分配")
            .replace("压缩后", "优化后")
            .replace("虽未超时但", "符合60分钟赛制，但")
            .replace("虽然未超时但", "符合60分钟赛制，但")
            .replace("虽未超时，", "符合60分钟赛制，")
            .replace("虽然未超时，", "符合60分钟赛制，")
            .replace("未超时", "符合60分钟赛制")
            .replace("超时", "超过预设时长")
        )
    return value


def _format_time(seconds: float) -> str:
    total = int(seconds or 0)
    return f"{total // 60:02d}:{total % 60:02d}"
