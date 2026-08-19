"""
模糊意图二次纠偏（P2b）

仅在规则 Brain 不确定时调用小温度 LLM，超时/失败则保持规则结果。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.assistant.artifact_schema import extract_json_object

logger = logging.getLogger(__name__)

VALID_GOALS = {"answer", "rewrite", "plan", "score_review", "artifact", "clarify"}
VALID_ARTIFACTS = {None, "md", "docx", "pptx", "xlsx", "pdf"}


def needs_soft_intent(plan: Any, user_text: str) -> bool:
    """是否值得花一次轻量 LLM 纠偏。"""
    t = (user_text or "").strip()
    if not t:
        return False
    # 已非常明确的产物/评分指令 → 不浪费
    if plan.goal == "artifact" and plan.artifact and plan.need_doc_gen:
        if re.search(r"ppt|pptx|excel|xlsx|docx|pdf|导出|下载", t, re.I):
            return False
    if plan.goal == "score_review" and plan.need_scores:
        if re.search(r"评分|扣分|报告", t):
            return False
    if plan.goal == "rewrite" and re.search(r"润色|改写|改开场", t):
        return False

    if getattr(plan, "completeness", "ok") in ("incomplete_utterance", "underspecified"):
        return True
    if plan.goal == "clarify":
        return True
    # 短指令 + 指代
    if len(t) <= 24 and re.search(r"这个|那份|继续|再|按上面|生成一份$", t):
        return True
    # 规则同时像多种目标
    signals = 0
    if re.search(r"讲稿|开场|润色", t):
        signals += 1
    if re.search(r"ppt|幻灯片|提纲", t, re.I):
        signals += 1
    if re.search(r"计划|excel|表格", t, re.I):
        signals += 1
    if re.search(r"评分|扣分", t):
        signals += 1
    if signals >= 2:
        return True
    return False


def refine_intent_with_llm(
    *,
    client: Any,
    model: str,
    user_text: str,
    plan_public: dict[str, Any],
    slots: dict[str, Any] | None = None,
    history_tail: str = "",
    temperature: float = 0.1,
) -> dict[str, Any] | None:
    """
    返回 partial override:
    {goal, needScores, needDocGen, artifact, artifactMode, assumptions?, rationale?}
    失败返回 None。
    """
    system = (
        "你是竞赛助手意图分类器。只输出一个 JSON 对象，不要解释。\n"
        "字段：\n"
        '{"goal":"answer|rewrite|plan|score_review|artifact|clarify",'
        '"needScores":bool,"needDocGen":bool,'
        '"artifact":null|"md"|"docx"|"pptx"|"xlsx"|"pdf",'
        '"artifactMode":"chat|outline|full|deck",'
        '"assumptions":["..."]}\n'
        "规则：\n"
        "1. 用户要可下载 ppt/pptx/幻灯片 → goal=artifact, artifact=pptx, mode=deck, needDocGen=true\n"
        "2. 只要提纲/大纲、不说导出 → needDocGen=false, mode=outline\n"
        "3. 提到根据评分/报告改进 → needScores=true, goal 多为 score_review\n"
        "4. 残句如「生成一份智慧农业的」→ clarify，assumptions 写清默认假设\n"
        "5. 沿用 session slots 里的项目名，不要清空\n"
        "6. 只输出 JSON"
    )
    user = (
        f"当前用户话：{user_text}\n\n"
        f"规则预判：{json.dumps(plan_public, ensure_ascii=False)}\n\n"
        f"会话 slots：{json.dumps(slots or {}, ensure_ascii=False)}\n\n"
        f"最近对话摘录：\n{(history_tail or '')[:2500]}"
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=False,
            temperature=temperature,
            # 部分网关支持；忽略失败
            **({} if True else {}),
        )
        content = ""
        if resp.choices:
            content = resp.choices[0].message.content or ""
        obj = extract_json_object(content)
        if not obj:
            return None
        goal = str(obj.get("goal") or "").strip()
        if goal not in VALID_GOALS:
            return None
        artifact = obj.get("artifact")
        if artifact in ("", "null", "none", "None"):
            artifact = None
        if artifact is not None:
            artifact = str(artifact).lower().strip()
            if artifact not in ("md", "docx", "pptx", "xlsx", "pdf"):
                artifact = None
        mode = str(obj.get("artifactMode") or obj.get("artifact_mode") or "chat")
        if mode not in ("chat", "outline", "full", "deck"):
            mode = "chat"
        need_scores = bool(obj.get("needScores") if "needScores" in obj else obj.get("need_scores"))
        need_doc = bool(obj.get("needDocGen") if "needDocGen" in obj else obj.get("need_doc_gen"))
        if artifact and mode in ("full", "deck"):
            need_doc = True
        assumptions = obj.get("assumptions") or []
        if not isinstance(assumptions, list):
            assumptions = []
        return {
            "goal": goal,
            "needScores": need_scores,
            "needDocGen": need_doc,
            "artifact": artifact,
            "artifactMode": mode,
            "assumptions": [str(a)[:80] for a in assumptions if a][:4],
            "rationale": ["soft_intent_llm"],
        }
    except Exception as e:
        logger.warning("soft intent failed: %s", e)
        return None


def apply_soft_override(plan: Any, override: dict[str, Any] | None) -> Any:
    """就地修改 BrainPlan。"""
    if not override:
        return plan
    plan.goal = override.get("goal") or plan.goal
    if "needScores" in override:
        plan.need_scores = bool(override["needScores"])
    if "needDocGen" in override:
        plan.need_doc_gen = bool(override["needDocGen"])
    if "artifact" in override:
        plan.artifact = override.get("artifact")
    if "artifactMode" in override:
        plan.artifact_mode = override.get("artifactMode") or plan.artifact_mode
    # 产物一致性
    if plan.artifact and plan.artifact_mode in ("full", "deck"):
        plan.need_doc_gen = True
        plan.goal = "artifact"
    if plan.artifact == "pptx" and plan.need_doc_gen:
        plan.artifact_mode = "deck"
    for a in override.get("assumptions") or []:
        if a and a not in plan.assumptions:
            plan.assumptions.append(a)
    plan.rationale.append("soft_intent applied")
    # 重建 labels（必须保留学习/任务/协同门闩标签，否则 UI 与工具不一致）
    labels: list[str] = []
    if plan.need_scores:
        labels.append("读取评分")
    if getattr(plan, "need_learning", False):
        labels.append("读取训练营")
    if getattr(plan, "need_tasks", False):
        labels.append("读取任务")
    if getattr(plan, "need_collab", False):
        labels.append("读取协同")
    if plan.need_rag:
        labels.append("检索资料")
    if plan.goal == "rewrite":
        labels.append("改稿")
    elif plan.goal == "plan":
        labels.append("排计划")
    elif plan.goal == "score_review":
        labels.append("评分复盘")
    elif plan.goal == "artifact":
        labels.append(f"生成{plan.artifact or '文件'}")
    elif plan.goal == "clarify":
        labels.append("补全意图")
    else:
        labels.append("对话")
    if plan.resolved_from_history:
        labels.append("沿用上下文")
    if plan.slots and any(plan.slots.get(k) for k in ("project_name", "report_title", "team_name", "track")):
        labels.append("会话记忆")
    labels.append("意图纠偏")
    plan.labels = labels
    return plan
