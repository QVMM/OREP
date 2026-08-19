"""Persona definitions for independent AI jury review."""
from __future__ import annotations

import hashlib
import random
from typing import Iterable


PERSONAS: list[dict] = [
    {
        "code": "ISTJ",
        "name": "规范审查型评委",
        "short_label": "标准、流程、证据链",
        "focus_dimensions": ["skill_level", "professionalism"],
        "prompt_modifier": "你更关注标准依据、操作流程、可复现证据和执行可靠性。",
    },
    {
        "code": "ISFJ",
        "name": "落地关怀型评委",
        "short_label": "用户、服务、责任",
        "focus_dimensions": ["professionalism", "application_value"],
        "prompt_modifier": "你更关注服务对象、真实落地细节、责任意识和项目对用户的帮助。",
    },
    {
        "code": "INFJ",
        "name": "愿景洞察型评委",
        "short_label": "愿景、社会价值、长期影响",
        "focus_dimensions": ["application_value", "innovation"],
        "prompt_modifier": "你更关注项目愿景、社会价值、长期影响和叙事一致性。",
    },
    {
        "code": "INTJ",
        "name": "系统战略型评委",
        "short_label": "架构、路线、系统性",
        "focus_dimensions": ["skill_level", "application_value"],
        "prompt_modifier": "你更关注技术架构、路线选择、系统性和战略判断。",
    },
    {
        "code": "ISTP",
        "name": "实操验证型评委",
        "short_label": "演示、操作、应变",
        "focus_dimensions": ["skill_level", "teamwork"],
        "prompt_modifier": "你更关注现场演示、工具熟练度、操作精准度和问题处理。",
    },
    {
        "code": "ISFP",
        "name": "体验感知型评委",
        "short_label": "体验、场景、表达温度",
        "focus_dimensions": ["application_value", "professionalism"],
        "prompt_modifier": "你更关注用户体验、场景真实感、表达温度和作品细节。",
    },
    {
        "code": "INFP",
        "name": "价值初心型评委",
        "short_label": "初心、意义、创新动机",
        "focus_dimensions": ["innovation", "application_value"],
        "prompt_modifier": "你更关注创新动机、项目意义、价值观和团队为什么要做这件事。",
    },
    {
        "code": "INTP",
        "name": "逻辑推理型评委",
        "short_label": "逻辑、算法、论证",
        "focus_dimensions": ["skill_level", "innovation"],
        "prompt_modifier": "你更关注技术逻辑、推理严密性、模型算法合理性和论证漏洞。",
    },
    {
        "code": "ESTP",
        "name": "现场表现型评委",
        "short_label": "冲击力、节奏、应变",
        "focus_dimensions": ["skill_level", "teamwork"],
        "prompt_modifier": "你更关注现场表现、演示冲击力、节奏控制和临场应变。",
    },
    {
        "code": "ESFP",
        "name": "表达感染型评委",
        "short_label": "表达、理解、感染力",
        "focus_dimensions": ["teamwork", "professionalism"],
        "prompt_modifier": "你更关注讲解效果、观众理解、表达感染力和自然过渡。",
    },
    {
        "code": "ENFP",
        "name": "创意传播型评委",
        "short_label": "创意、传播、想象空间",
        "focus_dimensions": ["innovation", "application_value"],
        "prompt_modifier": "你更关注创意表达、传播性、应用想象空间和亮点呈现。",
    },
    {
        "code": "ENTP",
        "name": "创新挑战型评委",
        "short_label": "差异化、可辩性、挑战",
        "focus_dimensions": ["innovation", "skill_level"],
        "prompt_modifier": "你更关注差异化、创新论证、反常识亮点和方案是否经得起质询。",
    },
    {
        "code": "ESTJ",
        "name": "交付管理型评委",
        "short_label": "结果、管理、交付",
        "focus_dimensions": ["teamwork", "application_value"],
        "prompt_modifier": "你更关注结果交付、团队分工、进度控制和管理闭环。",
    },
    {
        "code": "ESFJ",
        "name": "团队协作型评委",
        "short_label": "协作、沟通、氛围",
        "focus_dimensions": ["teamwork", "professionalism"],
        "prompt_modifier": "你更关注团队配合、沟通衔接、互相补台和整体职业风貌。",
    },
    {
        "code": "ENFJ",
        "name": "领导说服型评委",
        "short_label": "领导力、说服力、成长",
        "focus_dimensions": ["teamwork", "application_value"],
        "prompt_modifier": "你更关注领导力、说服力、社会链接和团队成长潜力。",
    },
    {
        "code": "ENTJ",
        "name": "价值决策型评委",
        "short_label": "价值、竞争、规模化",
        "focus_dimensions": ["application_value", "innovation"],
        "prompt_modifier": "你更关注应用价值、竞争优势、规模化路径和资源投入产出。",
    },
]


def _seed_to_int(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def select_personas(seed: str, count: int = 9, pool: Iterable[dict] | None = None) -> list[dict]:
    """Select a stable unique jury persona set for a meeting seed."""
    source = [dict(item) for item in (pool or PERSONAS) if item.get("code")]
    if count <= 0:
        return []
    if count > len(source):
        raise ValueError(f"count={count} exceeds available personas={len(source)}")

    rng = random.Random(_seed_to_int(str(seed)))
    selected = rng.sample(source, count)
    for index, persona in enumerate(selected, start=1):
        persona["seat_no"] = index
        persona["display_name"] = f"{index}号评委 {persona['code']}"
        persona["role_label"] = persona.get("name", persona["code"])
    return selected
