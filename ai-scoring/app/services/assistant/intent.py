"""竞赛助手意图门闩 —— 兼容层。

新逻辑在 brain.plan_turn；本模块保留 detect_intent 供旧调用/测试使用。
"""
from __future__ import annotations

from typing import Any

from app.services.assistant.brain import plan_turn


def detect_intent(
    text: str,
    *,
    has_resources: bool = False,
    options: dict[str, Any] | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    返回公开意图字典（兼容 needScores / needRag / needDocGen / labels）。
    推荐调用方改用 brain.plan_turn 拿完整 BrainPlan。
    """
    msgs = list(messages or [])
    if text and not any(m.get("role") == "user" for m in msgs):
        msgs = msgs + [{"role": "user", "content": text}]
    elif text and msgs:
        # 确保末条用户句一致
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i].get("role") == "user":
                msgs[i] = {**msgs[i], "content": text}
                break
        else:
            msgs.append({"role": "user", "content": text})

    plan = plan_turn(
        user_text=text,
        messages=msgs,
        has_resources=has_resources,
        options=options,
    )
    return plan.to_public_dict()
