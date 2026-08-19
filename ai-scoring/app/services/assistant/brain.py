"""
竞赛助手 · Brain 层（Grok 式理解逻辑的 OREP 落地）

市面智能助手（Grok / ChatGPT / Claude）体感「聪明」的共性，可拆成 6 条可工程化规则：

1. Understand-before-act：先结构化理解目标，再决定工具与回答形态
2. Multi-turn slots：用「这个 / 那份报告 / 生成一份」从历史补全指代
3. Mode routing：同一模型，不同 goal 换不同作答契约（教练 / 改稿 / 评分复盘 / 产物）
4. Tool gating：贵工具（评分、重解析）只在目标需要时打开
5. Dual channel：聊天给人看的叙述 ≠ 可下载产物的数据结构
6. Answer-first + assumptions：残句先给可用产出并标明假设，而不是空问卷

本模块只做「计划」：输出 BrainPlan。真正的 LLM 调用与文件渲染仍在 orchestrator。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


# ── 正则库 ──────────────────────────────────────────────────────────

SCORE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"评分",
        r"打分",
        r"得分",
        r"扣分",
        r"分数",
        r"AI\s*分",
        r"最近.*分",
        r"上[次轮场].*分",
        r"复盘分",
        r"评分结果",
        r"根据评分",
        r"按评分",
        r"路演评分",
        r"评分报告",
        r"以.*报告为准",
        r"就以.*报告",
    ]
]

# 显式要「文件/导出」才进产物通道；单独「提纲/大纲」默认只聊天
ARTIFACT_EXPLICIT = re.compile(
    r"(导出|下载|生成\s*(一份|个|一版)?\s*)?(pptx?|pdf|docx?|xlsx|excel|word|幻灯片)"
    r"|(导出|下载).{0,8}(文件|文稿|文档|表格|ppt|pptx|pdf|word|docx|excel)"
    r"|保存为.{0,6}(ppt|pdf|word|docx|excel|md)"
    r"|可下载"
    r"|生成一份\s*ppt"
    r"|做[一份一版]?\s*(ppt|pptx|幻灯片|word|pdf)",
    re.I,
)

PPT_HINT = re.compile(r"\bpptx?\b|幻灯片|路演\s*ppt|答辩\s*ppt", re.I)
DOC_HINT = re.compile(r"\bdocx?\b|\bword\b|申报书|文稿|讲稿(?!提纲)", re.I)
XLSX_HINT = re.compile(r"\bxlsx\b|excel|表格|训练计划|周计划", re.I)
PDF_HINT = re.compile(r"\bpdf\b", re.I)
MD_HINT = re.compile(r"markdown|\.md\b|md\s*文件", re.I)

REWRITE_HINT = re.compile(
    r"润色|改写|改一版|优化|重写|精简|压缩|更口语|帮我改|改开场|改讲稿", re.I
)
PLAN_HINT = re.compile(r"训练计划|周计划|日程|备赛计划|分工|todo|待办", re.I)
# 大计划 / 大改稿：先草案后确认
LIGHT_CONFIRM_PLAN = re.compile(
    r"本周计划|周计划|训练计划|备赛计划|冲刺计划|完整计划|详细计划|一周安排|本周安排",
    re.I,
)
LIGHT_CONFIRM_REWRITE = re.compile(
    r"全文|完整版|整篇|大改|重写整|完整讲稿|整份讲稿|完整开场|大改讲稿|整稿",
    re.I,
)
CONFIRM_EXPAND = re.compile(
    r"展开完整|确认展开|按草案展开|继续展开|展开全文|生成完整版|要完整版|确认.*完整",
    re.I,
)
OUTLINE_HINT = re.compile(r"提纲|大纲|目录|结构|页数", re.I)
SCRIPT_HINT = re.compile(r"讲稿|演讲稿|逐字稿|路演词|答辩词|开场", re.I)
RAG_HINT = re.compile(
    r"知识库|资源中心|讲稿|材料|文档|资料|结合.*库|根据.*资料|依据|参考", re.I
)

LEARNING_HINT = re.compile(
    r"训练营|今日训练|今天学什么|今天学啥|学习进度|集训|训练计划|学习资源|本周训练|训练日|学完|学习内容"
    r"|今日学习|今天的学习|训练营.*今天|今天.*训练",
    re.I,
)
TASK_HINT = re.compile(
    r"任务|待办|截止|看板|我的任务|项目任务|作业提交|交付|负责人|todo|待完成|未完成.*任务",
    re.I,
)
COLLAB_HINT = re.compile(
    r"协作|协同|求助|待我处理|协作请求|协同事项|谁找我|待处理协作"
    r"|有没有.*协作|协作.*待办|待处理.*协作|协作.*消息",
    re.I,
)
# 「今天有什么事可做」类：应同时打开训练营 + 任务 + 协同，禁止空口编通用时间表
DAILY_AGENDA_HINT = re.compile(
    r"今天有什么事|今天做什么|今天干什么|今天干嘛|今天有啥|今天忙什么|今天怎么安排"
    r"|今日安排|今天安排|今日待办|今天待办|今日可做|今天优先|接下来做什么|我该做什么"
    r"|有什么事可以做|有啥可以做|可以做点什么|今天工作|今日工作|今天要做|今天得做"
    r"|今天有哪些事|今日有哪些|今天事项|今日事项|今天任务清单|今日任务",
    re.I,
)

# 残句 / 未完成输入（明显半截：以「生成一份X的」结尾且很短）
INCOMPLETE_HINT = re.compile(
    r"^(生成一份|写一份|做一份|帮我写|帮我做|给我一版|生成|写|做)[\w\u4e00-\u9fff]{0,12}的?$"
    r"|^(生成一份|写一份).{0,16}$",
    re.I,
)

# 指代：绑定上轮内容
REF_LAST = re.compile(
    r"就以这|以这[个份].*为准|按这[个份]|上面[的这]|刚才[的这]|同上|继续"
    r"|基于[上前][文轮]|根据上面|按上面|用这[个份]|那份报告|这个报告|该报告",
    re.I,
)

PROJECT_NAME = re.compile(
    r"(?:项目(?:名称|名)?|作品)[：:\s]*([《\"]?)([^《\"\n]{2,40})(\1|》|\")?"
    r"|《([^》]{2,40})》"
)


@dataclass
class BrainPlan:
    """一次 run 的理解结果 + 作答/工具契约。"""

    # 粗目标
    goal: str = "answer"  # answer|rewrite|plan|score_review|artifact|clarify
    # 话题域
    domain: str = "general"  # roadshow|script|plan|score|docs|general
    # 工具门闩
    need_scores: bool = False
    need_rag: bool = False
    need_learning: bool = False
    need_tasks: bool = False
    need_collab: bool = False
    task_id_hint: int | None = None
    # 产物（none 表示纯聊天）
    artifact: str | None = None  # md|docx|pptx|xlsx|pdf|None
    artifact_mode: str = "chat"  # chat|outline|full|deck
    # 上下文来源
    source_priority: list[str] = field(default_factory=list)
    # 完整度
    completeness: str = "ok"  # ok|incomplete_utterance|underspecified
    assumptions: list[str] = field(default_factory=list)
    # UI 步骤标签
    labels: list[str] = field(default_factory=list)
    # 注入 system 的契约（核心：让模型「换脑子」）
    system_addendum: str = ""
    # 兼容旧字段
    need_doc_gen: bool = False
    # 调试/展示
    rationale: list[str] = field(default_factory=list)
    resolved_from_history: bool = False
    project_hint: str | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    soft_intent: bool = False
    # P1：大计划/大改稿先草案卡
    need_light_confirm: bool = False
    light_confirm_kind: str | None = None  # plan | rewrite
    # P1：强制依据脚注（训练营/评分/资料等）
    force_evidence: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        """SSE intent 事件 & 前端展示用（兼容旧 needScores 等）。"""
        return {
            "goal": self.goal,
            "domain": self.domain,
            "needScores": self.need_scores,
            "needRag": self.need_rag,
            "needLearning": self.need_learning,
            "needTasks": self.need_tasks,
            "needCollab": self.need_collab,
            "taskIdHint": self.task_id_hint,
            "needDocGen": self.need_doc_gen,
            "artifact": self.artifact,
            "artifactMode": self.artifact_mode,
            "labels": self.labels,
            "completeness": self.completeness,
            "assumptions": self.assumptions,
            "sourcePriority": self.source_priority,
            "projectHint": self.project_hint,
            "resolvedFromHistory": self.resolved_from_history,
            "rationale": self.rationale[:6],
            "slots": self.slots,
            "softIntent": self.soft_intent,
            "needLightConfirm": self.need_light_confirm,
            "lightConfirmKind": self.light_confirm_kind,
            "forceEvidence": self.force_evidence,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _last_user_and_history(messages: list[dict[str, Any]] | None) -> tuple[str, list[dict[str, str]]]:
    msgs = messages or []
    user_text = ""
    history: list[dict[str, str]] = []
    for m in msgs:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    for m in reversed(history):
        if m["role"] == "user":
            user_text = m["content"]
            break
    return user_text, history


def _history_blob(history: list[dict[str, str]], *, max_chars: int = 6000) -> str:
    parts: list[str] = []
    for m in history[-8:]:
        parts.append(f"{m['role']}: {m['content'][:1200]}")
    blob = "\n".join(parts)
    return blob[-max_chars:]


def _extract_project_hint(text: str, history_blob: str) -> str | None:
    for src in (text, history_blob):
        m = PROJECT_NAME.search(src or "")
        if m:
            name = m.group(2) or m.group(4)
            if name:
                return name.strip()[:40]
        # 兜底：智能大棚类专名
        m2 = re.search(r"([\u4e00-\u9fff]{2,20}(?:系统|平台|方案|项目))", src or "")
        if m2 and any(k in m2.group(1) for k in ("大棚", "农业", "监测", "智慧", "智能")):
            return m2.group(1)
    return None


def _detect_artifact(text: str) -> tuple[str | None, str]:
    """返回 (artifact|None, mode). mode: chat|outline|full|deck"""
    t = text or ""
    explicit = bool(ARTIFACT_EXPLICIT.search(t))
    wants_outline = bool(OUTLINE_HINT.search(t)) and not explicit

    if PPT_HINT.search(t) or re.search(r"生成一份\s*ppt|做.*幻灯片", t, re.I):
        if explicit or re.search(r"ppt|幻灯片", t, re.I):
            # 「生成一份ppt」→ deck；「写个提纲」→ outline chat
            if explicit or re.search(r"生成|导出|下载|做", t):
                return "pptx", "deck"
        if wants_outline:
            return None, "outline"
        return "pptx", "deck"

    if XLSX_HINT.search(t) and (explicit or re.search(r"训练计划|周计划|表格|excel|xlsx", t, re.I)):
        if explicit or re.search(r"训练计划|周计划|excel|xlsx|表格", t, re.I):
            return "xlsx", "full"

    if PDF_HINT.search(t) and explicit:
        return "pdf", "full"

    if DOC_HINT.search(t) and (explicit or re.search(r"申报书|文稿|讲稿|word|docx", t, re.I)):
        if explicit or re.search(r"申报书|生成.*文稿|导出|word|docx", t, re.I):
            return "docx", "full"

    if MD_HINT.search(t) and explicit:
        return "md", "full"

    # 「生成一份讲稿/计划」——聊天完整产出，可选附 md/docx
    if re.search(r"生成|写一份|做一份|整理成", t) and SCRIPT_HINT.search(t):
        return "docx", "full"  # 讲稿默认可下载 word+md
    if PLAN_HINT.search(t) and re.search(r"生成|写|导出|整理", t):
        return "xlsx", "full"

    if wants_outline:
        return None, "outline"

    return None, "chat"


def _detect_goal(
    text: str,
    *,
    need_scores: bool,
    artifact: str | None,
    artifact_mode: str,
) -> str:
    t = text or ""
    if artifact in ("pptx", "docx", "xlsx", "pdf", "md") and artifact_mode in ("deck", "full"):
        return "artifact"
    if need_scores and (
        re.search(r"根据|依据|结合|针对|按|改进|完善|复盘|优化", t)
        or "报告" in t
    ):
        return "score_review"
    if REWRITE_HINT.search(t):
        return "rewrite"
    if PLAN_HINT.search(t):
        return "plan"
    if artifact_mode == "outline" or OUTLINE_HINT.search(t):
        return "answer"
    if INCOMPLETE_HINT.search(t.strip()) and len(t.strip()) < 40:
        return "clarify"
    return "answer"


def _build_system_addendum(plan: "BrainPlan") -> str:
    lines: list[str] = [
        "",
        "## 本轮 Brain 契约（必须遵守）",
        f"- 目标 goal={plan.goal} · 领域 domain={plan.domain} · 完整度={plan.completeness}",
    ]
    if plan.project_hint:
        lines.append(f"- 项目线索：{plan.project_hint}（可直接用于标题与称呼，勿再空泛写「某项目」）")
    if plan.assumptions:
        lines.append("- 本轮假设（若与用户不符，在文末用一句话请用户纠正）：")
        for a in plan.assumptions[:5]:
            lines.append(f"  · {a}")
    if plan.source_priority:
        lines.append(
            "- 上下文优先级："
            + " > ".join(plan.source_priority)
            + "。指代「这个/报告/上面」时优先使用高优先级来源，禁止假装没看到。"
        )

    # 分 goal 的作答合同
    if plan.goal == "score_review":
        lines += [
            "- 【评分复盘模式】先给「诊断 → 改法 → 可粘贴产出」三段；数字只能来自评分工具结果，禁止编造分数。",
            "- 每条扣分对应 1 条可执行改法；最后给一版改后样例（开场或片段），不要只列原则。",
        ]
    elif plan.goal == "rewrite":
        lines += [
            "- 【改稿模式】若用户已给原文：直接输出改后全文 + ≤3 条改动说明。",
            "- 若未给原文：先给一版可替换空位的示例，再请用户贴原文。",
        ]
    elif plan.goal == "plan":
        if "daily_agenda" in (plan.rationale or []):
            lines += [
                "- 【今日待办模式】用户在问「今天有什么事/能做什么」。",
                "  必须只根据本轮平台工具结果作答：①训练营今日 ②我的任务 ③协同待处理。",
                "  按优先级列出真实事项（标题、团队、状态、截止/来源）；进行中优先，其次待开始。",
                "  禁止编造与站内数据无关的通用时间表（如「上午9:00明确选题」「下午收集论文」）。",
                "  工具显示暂无安排或空列表时如实说明；可给 1～2 条基于空态的引导，不要假装有具体赛项任务。",
                "  不要一上来追问赛项名称来代替读取工具；有工具数据就直接给清单。",
            ]
        else:
            lines += [
                "- 【计划模式】输出按天/职责可执行条目；含目标、动作、验收标准；避免鸡汤。",
                "- 若本轮提供了任务/训练营/协同工具结果，计划必须挂在真实事项上，禁止空头通用备赛日程。",
            ]
    elif plan.goal == "artifact" and plan.artifact == "pptx":
        lines += [
            "- 【PPT 成片模式】你写的是「可直接做成幻灯片」的正文，不是教练说明文。",
            "- 必须用 Markdown：一级标题=# 整份标题；每个 ## 就是一页幻灯片标题；其下只用 - 要点。",
            "- 约束：12～15 页为宜；每页 3～6 条要点；每条 ≤28 字；禁止表格管道符、禁止 ---、禁止「如需我…」客服句。",
            "- 禁止把「第5-8页」写成一个标题——功能演示必须拆成多页（每页一个模块）。",
            "- 第 1 个 ## 必须是封面信息（项目名/团队占位/一句话理念）；倒数可有致谢；不要「制作建议」页。",
            "- 聊天里不要另写一长段元分析；要点写在 ## 页里即可。",
        ]
    elif plan.goal == "artifact" and plan.artifact in ("docx", "md", "pdf"):
        lines += [
            "- 【文稿成片模式】输出完整可交付 Markdown：标题层级清晰，可直接存 Word/PDF。",
            "- 先正文后极短说明；不要把操作指南和正文混在一起。",
        ]
    elif plan.goal == "artifact" and plan.artifact == "xlsx":
        lines += [
            "- 【表格计划模式】用列表输出「事项：说明」或「Day N：动作」，便于导入表格。",
            "- 每条一行，避免大段散文。",
        ]
    elif plan.goal == "clarify":
        lines += [
            "- 【残句补全模式】用户输入可能不完整：先按最常见备赛需求给一版可用框架/示例，",
            "  标明假设；文末用一句话问清缺失槽位（项目名/用途：讲稿|PPT|计划|评分复盘）。",
            "- 禁止只回复「请补充信息」而不给任何可用内容。",
        ]
    else:
        lines += [
            "- 【对话模式】先给可用产出，再补需要确认的点；像教练，不鸡汤。",
        ]

    if plan.artifact_mode == "outline" and plan.goal != "artifact":
        lines += [
            "- 用户要的是「结构/提纲」：给清晰层级大纲即可，不要擅自导出文件口吻，除非用户要下载。",
        ]

    if not plan.need_scores:
        lines += [
            "- 本轮未开启评分工具：禁止编造具体分数、扣分项或声称已读取评分。",
        ]
    else:
        lines += [
            "- 本轮已/将提供评分工具结果：只引用工具块中的数字与扣分，可分析不可篡改。",
        ]

    if plan.need_learning:
        lines += [
            "- 本轮将提供训练营学习工具结果：今日/计划以工具摘要为准；可引导 /training/today；禁止编造学习完成状态。",
        ]
    if plan.need_tasks:
        lines += [
            "- 本轮将提供任务工具结果：标题/状态/截止以工具为准；本阶段只读，禁止声称已创建或修改任务。",
        ]
    if plan.need_collab:
        lines += [
            "- 本轮将提供协同工具结果：待办数量与事项列表以工具为准；本阶段只读，禁止代用户接受/拒绝协作。",
            "- 若工具块含「【系统核对·必须遵守】」或「待我处理」表格数字：必须原样引用，直接回答有没有待处理。",
            "- 仅当工具块以「（竞赛大脑站内协同读取失败」开头时，才可请用户稍后重试；一旦出现系统核对数字，绝不能改口成工具不可用。",
            "- 「待我处理」与「我发起的」含义不同：待我处理=0 时仍可列出我发起的事项，不要混为一谈。",
        ]

    if plan.need_rag:
        lines += [
            "- 若提供了参考资料，优先依据资料，并写「依据《资料名》」。",
        ]

    if plan.force_evidence:
        lines += [
            "- 【强制依据】本轮若使用了评分/训练营/任务/协同/资料工具结果：",
            "  回答**正文结束后**必须单独一节「## 依据」，用列表点名来源标题（与工具块一致），例如：",
            "  - 依据：最近 AI 评分 · 总分 xx",
            "  - 依据：今日训练 · 《任务名》",
            "  - 依据：资料《文件名》",
            "  无工具数据时写「本轮未读到站内评分/训练/资料」，禁止编造依据条目。",
        ]

    if plan.need_light_confirm:
        kind = plan.light_confirm_kind or "plan"
        if kind == "rewrite":
            lines += [
                "- 【Plan 轻确认 · 改稿草案】用户尚未确认展开完整版。",
                "  **只输出草案**，禁止直接给出完整改后全文：",
                "  1. 一句话目标（改什么、口语/时长方向）",
                "  2. 3～6 条改写纲要（条目式，非全文）",
                "  3. 关键假设（≤3 条）",
                "  4. 文末固定句：「确认后点击下方「展开完整版」，或回复：展开完整改稿」",
                "  全文控制在约 250 字内；不要写长段改后正文。",
            ]
        else:
            lines += [
                "- 【Plan 轻确认 · 计划草案】用户尚未确认展开完整版。",
                "  **只输出草案**，禁止直接输出完整按天长计划：",
                "  1. 一句话本周目标",
                "  2. 3～6 条优先事项纲要（动作 | 建议时长 | 验收一句话）— 可用短表",
                "  3. 关键假设（≤3 条）",
                "  4. 文末固定句：「确认后点击下方「展开完整版」，或回复：展开完整计划」",
                "  全文控制在约 280 字内；不要展开到每天时段明细。",
            ]

    return "\n".join(lines)


def plan_turn(
    *,
    user_text: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    has_resources: bool = False,
    options: dict[str, Any] | None = None,
    prior_slots: dict[str, Any] | None = None,
) -> BrainPlan:
    """
    从当前用户句 + 最近消息 + 持久化 slots，产出 BrainPlan。
    规则为主；调用方可再跑 soft_intent 纠偏。
    """
    from app.services.assistant.slots import extract_from_messages, slots_system_block

    options = options or {}
    text, history = _last_user_and_history(messages)
    if user_text:
        text = user_text
    text = (text or "").strip()
    hist_blob = _history_blob(history)
    plan = BrainPlan()

    # 0) 会话 Slot：持久化 prior ∪ 历史抽取
    session_slots = extract_from_messages(history, prior=prior_slots or options.get("sessionSlots"))
    plan.slots = session_slots.to_dict()
    if session_slots.project_name:
        plan.project_hint = session_slots.project_name

    # 1) 指代：合并历史语义（必须有历史，且命中指代词或极短续写指令）
    has_prior = any(m.get("role") == "assistant" for m in history[:-1]) or len(history) >= 2
    short_continue = (
        has_prior
        and len(text) <= 18
        and bool(re.search(r"^(继续|同样|再来|按上面|生成一份|导出|写一份)", text))
    )
    if has_prior and (REF_LAST.search(text) or short_continue):
        plan.resolved_from_history = True
        plan.rationale.append("检测到指代/短指令，合并最近对话上下文")
        merged = text + "\n" + hist_blob[-2000:]
    else:
        merged = text

    # 2) 评分门闩
    plan.need_scores = any(p.search(merged) for p in SCORE_PATTERNS)
    if options.get("forceScores") is True:
        plan.need_scores = True
    # 「就以这个报告为准」且历史里出现评分/报告 → 开评分
    if re.search(r"报告", text) and re.search(r"评分|扣分|得分|路演评分", hist_blob):
        plan.need_scores = True
        plan.rationale.append("报告指代指向历史评分上下文")

    # 3) RAG
    plan.need_rag = has_resources or bool(RAG_HINT.search(merged))
    if plan.resolved_from_history and re.search(r"资料|讲稿|报告|文档", hist_blob):
        plan.need_rag = True

    # 3b) 学习 / 任务 / 协同（只读工具门闩）
    plan.need_learning = bool(LEARNING_HINT.search(merged))
    plan.need_tasks = bool(TASK_HINT.search(merged))
    plan.need_collab = bool(COLLAB_HINT.search(merged))
    daily_agenda = bool(DAILY_AGENDA_HINT.search(text) or DAILY_AGENDA_HINT.search(merged))
    if daily_agenda:
        # 今日待办：三路并行，避免只闲聊编「上午选题下午写文档」假日程
        plan.need_learning = True
        plan.need_tasks = True
        plan.need_collab = True
        plan.rationale.append("daily_agenda")
    # 教师端 audience：工作台/待批/未交等运营问句必须开工具门闩
    if str(options.get("audience") or "").lower() == "teacher":
        plan.need_learning = True
        plan.need_tasks = True
        plan.rationale.append("teacher_audience_tools")
    # 「我的任务」类不误开训练营（今日待办除外）
    if (
        plan.need_tasks
        and not daily_agenda
        and not LEARNING_HINT.search(text)
        and re.search(r"项目|看板|截止|负责人", text)
        and str(options.get("audience") or "").lower() != "teacher"
    ):
        plan.need_learning = False
    # 提取 taskId=123 或 任务 123
    m_tid = re.search(r"(?:taskId|任务\s*(?:id|ID)?)\s*[=:：]?\s*(\d{1,12})", text)
    if m_tid:
        try:
            plan.task_id_hint = int(m_tid.group(1))
            plan.need_tasks = True
        except ValueError:
            pass
    if plan.need_learning:
        plan.rationale.append("need_learning")
        plan.source_priority.append("learning_tool")
    if plan.need_tasks:
        plan.rationale.append("need_tasks")
        plan.source_priority.append("tasks_tool")
    if plan.need_collab:
        plan.rationale.append("need_collab")
        plan.source_priority.append("collab_tool")

    # 4) 产物
    artifact, mode = _detect_artifact(merged)
    # 短句「生成一份ppt」以当前句为准
    a2, m2 = _detect_artifact(text)
    if a2:
        artifact, mode = a2, m2
    if options.get("forceArtifact"):
        artifact = str(options["forceArtifact"])
        mode = str(options.get("artifactMode") or "full")

    plan.artifact = artifact
    plan.artifact_mode = mode
    plan.need_doc_gen = artifact is not None and mode in ("full", "deck")

    # 5) 领域
    if plan.need_scores or re.search(r"评分|扣分", merged):
        plan.domain = "score"
    elif artifact == "pptx" or re.search(r"路演|答辩|ppt", merged, re.I):
        plan.domain = "roadshow"
    elif SCRIPT_HINT.search(merged):
        plan.domain = "script"
    elif PLAN_HINT.search(merged):
        plan.domain = "plan"
    elif artifact:
        plan.domain = "docs"

    # 6) goal
    plan.goal = _detect_goal(
        merged, need_scores=plan.need_scores, artifact=artifact, artifact_mode=mode
    )
    # 今日待办：在通用 goal 检测之后强制 plan（否则会被 answer 覆盖）
    if daily_agenda and plan.goal in ("answer", "plan"):
        plan.goal = "plan"
        plan.domain = "plan"
    # 残句覆盖：仅当没有明确产物/改稿/计划意图时
    if (
        INCOMPLETE_HINT.search(text)
        and len(text) <= 20
        and not artifact
        and plan.goal not in ("rewrite", "plan", "score_review")
        and not OUTLINE_HINT.search(text)
        and not SCRIPT_HINT.search(text)
    ):
        plan.goal = "clarify"
        plan.completeness = "incomplete_utterance"
        plan.assumptions.append("按技能大赛路演/项目介绍的常见需求先给框架")
        plan.rationale.append("输入疑似未完成短句")
    elif len(text) < 6 and not plan.resolved_from_history:
        plan.completeness = "underspecified"

    # 7) 来源优先级
    if plan.need_scores:
        plan.source_priority.append("score_tool")
    if has_resources:
        plan.source_priority.append("selected_resources")
    if plan.resolved_from_history:
        plan.source_priority.append("recent_assistant_output")
    plan.source_priority.append("user_message")

    # 8) 项目名：Slot 优先，其次正则
    hint = plan.project_hint or _extract_project_hint(text, hist_blob)
    if not hint and session_slots.project_name:
        hint = session_slots.project_name
    plan.project_hint = hint
    if plan.project_hint:
        plan.rationale.append(f"项目线索={plan.project_hint}")

    # Slot 强化工具门闩
    if session_slots.prefer_scores and re.search(r"报告|继续|按这|完善|改进|生成", text):
        if re.search(r"报告|评分|完善|改进|ppt|讲稿", text + hist_blob[:500], re.I):
            plan.need_scores = True
            plan.rationale.append("slot.prefer_scores → 开启评分")
    if session_slots.last_artifact and re.search(r"^(再来一份|同样格式|继续导出|再导出)", text):
        plan.artifact = session_slots.last_artifact
        plan.artifact_mode = "deck" if plan.artifact == "pptx" else "full"
        plan.need_doc_gen = True
        plan.goal = "artifact"
        plan.assumptions.append(f"沿用上次产物格式：{plan.artifact}")

    # 同步 domain
    if session_slots.domain and plan.domain == "general":
        plan.domain = session_slots.domain

    # 更新 slots 本轮产物
    if plan.artifact:
        session_slots.last_artifact = plan.artifact
    if plan.need_scores:
        session_slots.prefer_scores = True
    if plan.project_hint:
        session_slots.project_name = plan.project_hint
    if plan.domain:
        session_slots.domain = plan.domain
    plan.slots = session_slots.to_dict()

    # 9) 假设
    if plan.goal == "artifact" and plan.artifact == "pptx":
        plan.assumptions.append("默认职业技能大赛路演 PPT，约 12–15 页")
        if plan.need_scores or session_slots.prefer_scores:
            plan.assumptions.append("结构优先响应评分报告中的扣分与建议")
    if plan.goal == "score_review":
        plan.assumptions.append("以工具返回的最近评分为准，不做虚构打分")
        if re.search(r"详细|完整|markdown|md\b|报告全文|报告内容|评分报告", text, re.I):
            plan.assumptions.append("用户要完整评分报告 Markdown，应输出工具 reportMarkdown 全文")
    if plan.resolved_from_history and plan.goal in ("artifact", "score_review", "rewrite"):
        plan.assumptions.append("沿用本会话已出现的项目与报告口径，不重新编造背景")
    if session_slots.project_name:
        plan.assumptions.append(f"项目沿用「{session_slots.project_name}」")

    # 10) labels（步骤条）
    labels: list[str] = []
    if plan.need_scores:
        labels.append("读取评分")
    if plan.need_learning:
        labels.append("读取训练营")
    if plan.need_tasks:
        labels.append("读取任务")
    if plan.need_collab:
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
    if session_slots.project_name or session_slots.report_title:
        labels.append("会话记忆")
    plan.labels = labels

    # 10b) Plan 轻确认 + 强制依据
    user_confirmed = bool(CONFIRM_EXPAND.search(text))
    is_daily = "daily_agenda" in (plan.rationale or [])
    if not user_confirmed:
        # 周计划/训练计划：goal 可能是 plan，也可能被识别成 xlsx artifact
        wants_big_plan = bool(LIGHT_CONFIRM_PLAN.search(merged)) and not is_daily
        if wants_big_plan and plan.goal in ("plan", "artifact", "answer"):
            plan.need_light_confirm = True
            plan.light_confirm_kind = "plan"
            plan.rationale.append("light_confirm:plan")
            plan.labels = list(plan.labels) + ["计划草案"]
            # 轻确认阶段先不落文件，展开后再产物
            if plan.goal == "artifact" and plan.artifact == "xlsx":
                plan.need_doc_gen = False
                plan.rationale.append("light_confirm_defer_xlsx")
        elif plan.goal == "rewrite" and (
            LIGHT_CONFIRM_REWRITE.search(merged) or len(text) >= 120
        ):
            plan.need_light_confirm = True
            plan.light_confirm_kind = "rewrite"
            plan.rationale.append("light_confirm:rewrite")
            plan.labels = list(plan.labels) + ["改稿草案"]
        if re.search(r"/今日", text) and LIGHT_CONFIRM_PLAN.search(merged) and not is_daily:
            plan.need_light_confirm = True
            plan.light_confirm_kind = plan.light_confirm_kind or "plan"
    else:
        plan.rationale.append("user_confirmed_expand")

    plan.force_evidence = bool(
        plan.need_scores
        or plan.need_learning
        or plan.need_tasks
        or plan.need_collab
        or plan.need_rag
        or has_resources
        or plan.goal == "score_review"
    )
    if plan.force_evidence:
        plan.rationale.append("force_evidence")

    # 11) system 契约 + Slot 块
    plan.system_addendum = _build_system_addendum(plan) + slots_system_block(session_slots)
    plan.rationale.append(f"goal={plan.goal} artifact={plan.artifact}/{plan.artifact_mode}")
    return plan


# ── 产物后处理：聊天正文 → 更适合渲染的文本 ─────────────────────────

_META_LINE = re.compile(
    r"^(?:---+\s*|如需我|如果你愿意|请告知|建议总页数|PPT制作与演示|核心建议[：:]|制作建议)",
    re.I,
)
_TABLE_LINE = re.compile(r"^\|.+\|$")
_PAGE_RANGE = re.compile(r"第\s*(\d+)\s*[-~～到至]\s*(\d+)\s*页")


def prepare_artifact_markdown(text: str, *, artifact: str | None, title: str | None = None) -> str:
    """
    渲染前清洗：去掉客服句、水平线、元建议节、表格管道符。
    不调用 LLM，保证稳定。
    """
    if not text:
        return text
    lines_out: list[str] = []
    if title and artifact == "pptx" and not re.search(r"^#\s+", text, re.M):
        lines_out.append(f"# {title}")

    skip_section = False
    seen_h2 = False

    for raw in text.replace("\r\n", "\n").split("\n"):
        st = raw.strip()
        if not st:
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            continue
        if st in ("---", "***", "___"):
            continue
        if _META_LINE.match(st):
            continue

        is_heading = bool(re.match(r"^#{1,3}\s+", st))
        if is_heading:
            if re.search(r"制作与演示|制作建议|演示核心建议|结构与内容要点", st):
                skip_section = True
                continue
            skip_section = False
            if st.startswith("##"):
                seen_h2 = True
            if artifact == "pptx" and _PAGE_RANGE.search(st):
                st = re.sub(_PAGE_RANGE, "核心功能演示", st)
                st = re.sub(r"[：:]\s*核心功能.*$", "", st)
            lines_out.append(st)
            continue

        if skip_section:
            continue

        if st.startswith(">"):
            inner = st.lstrip("> ").strip()
            if artifact == "pptx" or re.search(r"建议总页数|依据《|本PPT结构", inner):
                continue
            lines_out.append(inner)
            continue

        if _TABLE_LINE.match(st):
            cells = [c.strip() for c in st.strip("|").split("|")]
            cells = [c for c in cells if c and not re.match(r"^[-:]+$", c)]
            if len(cells) >= 2:
                lines_out.append(f"- {' · '.join(cells[:4])}")
            continue

        # PPT：第一个 ## 之前的散文丢掉，避免空「内容」页
        if artifact == "pptx" and not seen_h2 and not re.match(r"^[-*]\s+|^\d+[\.、]", st):
            continue

        lines_out.append(st)

    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines_out)).strip()
    return cleaned


def default_artifact_title(plan: BrainPlan) -> str:
    if plan.project_hint and plan.artifact == "pptx":
        return f"{plan.project_hint} · 路演提纲"
    if plan.project_hint and plan.artifact in ("docx", "md", "pdf"):
        return f"{plan.project_hint} · 文稿"
    if plan.artifact == "pptx":
        return "路演PPT提纲"
    if plan.artifact == "xlsx":
        return "训练计划"
    return "竞赛助手文稿"
