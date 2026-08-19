"""
AI 图表生成器 V5 — OREP 路演评审报告
方案：LLM 生成结构化 JSON → reportlab 渲染极简表格
风格：SpaceX 极简 — 黑白灰、细线、留白、排版即视觉
"""
import json
import os
import re
from typing import Optional

from app.config import settings


def _call_llm(system: str, user: str) -> str:
    """调用 DeepSeek LLM，带重试"""
    import httpx
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
    }
    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"

    for attempt in range(3):
        sys = system
        if attempt > 0:
            sys += "\n\n重要：只使用标准 ASCII 引号，不要中文引号。确保 JSON 格式完全正确。"
        payload = {
            "model": settings.DEEPSEEK_MODEL or "deepseek-v4-pro",
            "temperature": 0.1 if attempt > 0 else 0.2,
            "max_tokens": 8192,
            "messages": [
                {"role": "system", "content": sys},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        resp = httpx.post(url, json=payload, headers=headers, timeout=180)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        try:
            _parse_llm_json(raw)
            return raw
        except Exception as e:
            print(f'[DiagramGen] JSON parse failed (attempt {attempt+1}): {e}')
            if attempt == 2:
                raise
    raise RuntimeError("LLM failed after 3 attempts")


def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```\w*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    brace_count = 0
    start = raw.find('{')
    if start < 0:
        raise ValueError("No JSON found")
    for i, c in enumerate(raw[start:], start):
        if c == '{': brace_count += 1
        elif c == '}': brace_count -= 1
        if brace_count == 0:
            return json.loads(raw[start:i+1])
    raise ValueError("Incomplete JSON")


def _extract_data(result: dict) -> dict:
    profile = result.get('character_profile', {})
    speech = result.get('speech_quality', {})
    video = result.get('video_analysis', {}).get('aggregates', {})
    fusion = result.get('fusion', {})
    dims = result.get('ai_score', {}).get('dimensions', {})
    timeline = fusion.get('timeline', [])
    step = max(1, len(timeline) // 20)

    return {
        'profile': profile.get('profile_markdown', '')[:3000],
        'per_speaker': speech.get('speech_rate', {}).get('per_speaker', {}),
        'speech_grade': speech.get('overall_rating', {}).get('grade'),
        'video_avg': {k: video.get(k) for k in ['avg_gesture','avg_posture','avg_expression','avg_eye_contact']},
        'eye_direction': video.get('eye_direction_distribution'),
        'fusion_summary': fusion.get('summary', {}),
        'dimensions': {k: {'score': v.get('score'), 'max': v.get('max_score',100),
                           'evidence': v.get('evidence','')[:300],
                           'suggestions': v.get('suggestions',[])[:3]}
                       for k, v in dims.items()},
        'overall_score': result.get('ai_score',{}).get('overall_score'),
        'duration_min': result.get('asr',{}).get('duration',0)/60,
        'sampled_timeline': [{'time_min':w.get('time_min'),'fusion':w.get('fusion_score'),
                              'scene':w.get('scene_type'),'speaker':w.get('active_speaker'),
                              'speech_rate':w.get('speech_rate'),'text':(w.get('text_preview') or '')[:60]}
                             for i,w in enumerate(timeline) if i%step==0],
    }


# ═══════════════════════════════════════════════════════════
# LLM Prompts（职业技能大赛专用，无提问环节）
# ═══════════════════════════════════════════════════════════

_TEAM_PROMPT = """你是职业技能大赛路演辅导专家。封闭式路演，无提问环节，裁判不与选手交流。
话术必须专业、技术驱动，绝对禁止：投票、扫码、加微信、成为合伙人等营销话术。

根据分析数据给出团队分工优化方案，输出 JSON：
{
  "title": "团队分工优化路线图",
  "key_insight": "核心洞察",
  "phases": [
    {
      "id": "P0",
      "label": "立即调整",
      "actions": [
        {"action": "具体动作（15字内）", "owner": "负责角色", "detail": "怎么做（含话术示例）", "metric": "验收标准"}
      ]
    }
  ]
}
3个phase(P0/P1/P2)，每个3-4个action。话术示例必须适合封闭式职业技能大赛。"""

_STRUCTURE_PROMPT = """你是职业技能大赛路演叙事结构专家。封闭式路演，无提问环节，话术专业、技术驱动。

分析路演是否符合"黄金结构"，输出 JSON：
{
  "title": "路演结构对标分析",
  "verdict": "总评",
  "phases": [
    {"name": "破冰钩子", "time": "0-3min", "gold": "黄金标准", "actual": "实际表现", "gap": "差距", "fix": "改进方案", "example": "话术示例", "score": 7, "status": "good"}
  ]
}
7个阶段：破冰钩子(0-3min)、问题共鸣(3-8min)、方案展示(8-20min)、证据验证(20-35min)、商业闭环(35-45min)、团队致胜(45-52min)、有力收尾(52-60min)。
注意：无提问环节，不需要准备技术问答。example 适合封闭式大赛。"""

_ACTION_PROMPT = """你是职业技能大赛路演改进方案总设计师。封闭式路演，无提问环节。

输出 JSON：
{
  "title": "路演改进行动计划",
  "outcome": "预期效果",
  "critical_path": [
    {"step":1,"action":"行动","owner":"谁","when":"时间","how":"怎么做（含话术）","verify":"验收","impact":"提升"}
  ],
  "parallel_tracks": [
    {"track":"任务线","items":[{"action":"...","owner":"...","when":"...","how":"..."}]}
  ],
  "synergy": "分工和结构优化的协同效应"
}
critical_path 6-8步，parallel_tracks 1-2条线。how中话术适合封闭式大赛，无提问环节。"""


# ═══════════════════════════════════════════════════════════
# 生成入口（返回 JSON spec）
# ═══════════════════════════════════════════════════════════

def generate_team_topology(result: dict) -> Optional[dict]:
    data = _extract_data(result)
    try:
        raw = _call_llm(_TEAM_PROMPT, json.dumps(data, ensure_ascii=False))
        return _parse_llm_json(raw)
    except Exception as e:
        print(f'[DiagramGen] 团队方案失败: {e}')
        return None


def generate_timeline_flowchart(result: dict) -> Optional[dict]:
    data = _extract_data(result)
    try:
        raw = _call_llm(_STRUCTURE_PROMPT, json.dumps(data, ensure_ascii=False))
        return _parse_llm_json(raw)
    except Exception as e:
        print(f'[DiagramGen] 结构分析失败: {e}')
        return None


def generate_improvement_mindmap(result: dict) -> Optional[dict]:
    data = _extract_data(result)
    try:
        raw = _call_llm(_ACTION_PROMPT, json.dumps(data, ensure_ascii=False))
        return _parse_llm_json(raw)
    except Exception as e:
        print(f'[DiagramGen] 行动计划失败: {e}')
        return None


def generate_all_diagrams(result: dict) -> dict:
    specs = {}
    print('[DiagramGen] 生成团队分工优化方案...')
    s = generate_team_topology(result)
    if s: specs['team_topology'] = s

    print('[DiagramGen] 生成路演结构对标分析...')
    s = generate_timeline_flowchart(result)
    if s: specs['timeline_flowchart'] = s

    print('[DiagramGen] 生成改进行动计划...')
    s = generate_improvement_mindmap(result)
    if s: specs['improvement_mindmap'] = s

    return specs
