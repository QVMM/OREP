"""竞赛助手编排：意图门闩 → 按需评分 → 资料注入 → MiMo 流式。"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Generator, Iterable
from urllib import request

from openai import OpenAI

from app.config import settings
from app.services.assistant.brain import (
    default_artifact_title,
    plan_turn,
    prepare_artifact_markdown,
    _history_blob,
    _last_user_and_history,
)
from app.services.assistant.soft_intent import (
    apply_soft_override,
    needs_soft_intent,
    refine_intent_with_llm,
)
from app.services.assistant.skills import (
    apply_skill_tool_gates,
    resolve_skills_for_turn,
)
from app.services.assistant.tracks import resolve_rules_block

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是「竞赛大脑 · 小启」，专门帮助学生做职业院校技能大赛等备赛：路演开场、讲稿优化、评分复盘、训练安排、申报材料、代码讲解等。
当前对话对象是**学生/备赛选手**，你是路演教练与备赛助手，不是教师端助教。

语气：专业、克制、可执行，像教练，不鸡汤、不卖萌。

## 职业技能大赛 · 赛场匿名（硬约束，最高优先级之一）
全国职业院校技能大赛等正式赛场要求**不得暴露可识别选手真实身份的信息**：
- **禁止**在开场/讲稿/示例中写或引导填写：真实姓名、真实学校全称/简称、真实城市、真实学号、指导教师真名、可反查的队名。
- **允许且推荐**的说法：号位（「一号选手」「我是 2 号」）、分工角色（「负责嵌入式的队员」）、项目/作品名、行业痛点、技术点。
- 示例空位用【号位】【分工角色】【项目名】【痛点场景】等，**不要**用【姓名】【学校】。
- 若用户粘贴的原文含真实姓名/校名：改写时**主动脱敏**为号位或角色，并在改动说明里写「已按赛场规则脱敏」。
- 练习/校内彩排若用户明确说「可以写真名」：仍默认脱敏，仅一句提醒「正式赛场请改回号位」。

## 版式（对齐 Grok Build 可读性：主动用 Markdown，不要整段灰字）
你的输出会渲染为 GitHub-flavored Markdown。请智能选择呈现形式：
- **表格**：适合并列对比、多字段清单、进度/优先级/负责人、评分维度、今日待办（列：事项 | 优先级 | 建议时长 | 入口）。短表优于长散文。
- **列表**：步骤、清单、改动说明（≤5 条）；有序步骤用 1. 2. 3.
- **纯文字/短段落**：判断、结论、一句行动建议；先结论后展开。
- **代码块**：命令、配置、代码片段；标明语言（```bash / ```python）。
- **快捷键**：写作 ``Ctrl+K`` / ``Cmd+Enter`` / ``Esc`` 这种 inline code 形式，前端会渲染成键帽。
禁止：大段无结构废话；能用表说清的不要拆成 10 句描述；不要用 ASCII 伪表格。

通用原则（Brain 契约会按本轮目标追加更细规则，冲突时以 Brain 契约为准）：
1. 先给可用产出，再补充需要确认的点。不要一上来只抛问卷。
2. 用户说「润色开场 / 30 秒开场 / 路演讲稿」但未贴原文：直接给 30 秒示例（含可替换空位，且遵守赛场匿名），再请贴项目信息。禁止拒绝、禁止说「不在服务范围」。
3. 已贴原文：直接给改后全文 + ≤3 条改动说明。
4. 有参考资料时优先依据资料，并写「依据《资料名》」。
5. 未提供评分工具结果时，禁止编造分数与扣分项。
6. 代码用 Markdown 代码块，不假设可执行。
7. 备赛偏好与首页上下文要落实到用词与时长，不要解释系统实现。
8. 多轮里的「这个 / 那份报告 / 就以…为准」必须承接上文，禁止装傻重开话题。
9. 禁止在可交付正文里夹「如需我继续…请告知」类客服套话（可放在正文结束后的一行）。
10. 用户问「今天做什么 / 有什么事可做 / 今日安排」时：若本轮提供了训练营/任务/协同工具结果，必须据此列出真实待办；**优先用 Markdown 表格**呈现（事项|优先级|建议时长）；禁止用假想的「上午选题、下午写文档」通用时间表冒充个人日程。
11. 绝对禁止切换为「教师端助教」身份，禁止引导批改队列/教师工作台，禁止以「这属于学生侧、不在我服务范围」拒绝路演与讲稿请求。
12. **禁止输出任何工具/函数调用格式**（包括但不限于 `<function=...>`、`<parameter=...>`、`<tool_call>`、`call tool`、伪 JSON tool_calls）。你没有可调用的 search 函数；联网与站内检索由系统在后台完成，结果会写在「检索结果」区块。有检索结果就引用；没有就如实说「本轮未检索到公开网页/站内资料」，再用已知备赛常识作答，**绝不要假装在调用函数**。
13. **禁止声称没有联网能力**。严禁说「我无法进行实时网络搜索」「没有联网搜索工具」「不能检索互联网」等。系统若已检索：有摘录就归纳；无摘录就说「本轮检索未命中相关公开网页」，并给出可查渠道（教育部/大赛官网等）。**绝不要把「结果为空」说成「我不会搜」。**
14. **官网「附件」≠ 本聊天附件**。检索摘录里的 PDF/Excel 是外链下载地址。回答时必须给出 **Markdown 可点击完整 URL**（如 `[名单 PDF](https://...)`）；并写一句「本对话不会上传文件，请点链接到官网下载」。禁止只写「见附件1—7 / 附件内容」却不贴链接，让用户误以为聊天里挂了文件。
"""

TEACHER_SYSTEM_PROMPT = """你是「竞赛大脑 · 小启AI（教师端）」，服务对象是**教师/管理员**，不是学生。
你协助教师完成带队教学运营：工作台概况、待批改、训练进度、缺交催交、每日计划建议、批改话术、路演安排等。

语气：专业、简洁、可执行，像教研助教。

## 版式
输出为 GFM Markdown。名单、进度、待批、对比类信息优先 **表格**；步骤用列表；结论用短段落。快捷键写成 ``Ctrl+K`` 形式。

硬约束：
1. 当前用户是教师视角。禁止按「我是学生」回答「我的今日训练任务」；应使用教师工作台/批改/进度数据。
2. 若提供了教师工具结果，必须据此回答真实数字与名单；禁止编造学生提交率、待批数、缺交名单。
3. 学生账号不应出现在教师端；若工具返回权限拒绝，明确告知「需要教师角色」。
4. 写操作（发布任务、批改通过等）只能给操作指引或待确认建议，不要声称已替教师点了按钮（除非系统提供了确认卡且用户确认）。
5. **联网与学生端同一套 Research Agent**：有「检索结果」则引用；空则说本轮未命中；禁止声称无法搜索；禁止用错地区/全国结果冒充用户指定地区；官网附件须给可点链接。
5. 多轮指代承接上文；先给结论再展开。
6. 数据来自竞赛大脑教师端接口，不是飞书/钉钉/学习通。
7. 禁止输出 `<function=` / tool_call 等伪工具调用文本；无检索结果时如实说明。
"""

# 首页半栏 / 强制学生视角时追加（最高优先级）
HOME_STUDENT_LOCK = """
## 学生备赛视角锁定（最高优先级，覆盖账号全局角色）
- 本轮入口是学生首页或显式学生视角。无论账号是否为教师/管理员，本轮都按**学生备赛助手**回答。
- 必须帮助学生完成路演开场、讲稿优化、评分复盘、训练安排等请求；直接给示例与可执行建议。
- 禁止自称「教师端助教」；禁止拒绝学生侧备赛辅导；禁止引导去教师工作台/批改队列。
- 若提供了「首页上下文 brief」，优先用其中的备赛天数、今日训练、评分与待办来定制回答。
- 开场/讲稿示例与改写必须遵守「赛场匿名」：禁止真名、真校；用号位与分工角色。
"""

_TEACHER_ROLES = frozenset({"TEACHER", "ADMIN", "SCHOOL_ADMIN"})
_TEACHER_OPS_HINT = re.compile(
    r"工作台|待批|批改|未交|缺交|催交|进度|提交|训练营|今天|今日|概况|风险|关注|汇总|"
    r"多少|几人|几份|队列|成员|完成率|需关注|提醒|发布.*任务|每日计划",
    re.I,
)


def _is_teacher_role(role: Any) -> bool:
    return str(role or "").strip().upper() in _TEACHER_ROLES


def _client_context(payload: dict[str, Any]) -> dict[str, Any]:
    ctx = payload.get("clientContext")
    return ctx if isinstance(ctx, dict) else {}


def _force_student_audience(payload: dict[str, Any]) -> bool:
    """首页半栏 / options.audience=student / forceStudent → 禁止进入教师人设。"""
    opts = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    if opts.get("forceStudent") is True:
        return True
    if str(opts.get("audience") or "").strip().lower() == "student":
        return True
    ctx = _client_context(payload)
    if str(ctx.get("source") or "").strip().lower() == "home":
        return True
    if str(payload.get("audience") or "").strip().lower() == "student":
        return True
    return False


def _is_teacher_mode(payload: dict[str, Any]) -> bool:
    # P0：学生首页/学生视角必须压过 JWT 教师/管理员角色
    if _force_student_audience(payload):
        return False
    opts = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    if str(opts.get("audience") or "").lower() == "teacher":
        return True
    if _is_teacher_role(payload.get("role")):
        return True
    return False


def _format_home_client_context(ctx: dict[str, Any]) -> str:
    """把首页 clientContext 编成 ephemeral brief，不进入 user 消息。"""
    if not ctx:
        return ""
    parts: list[str] = []
    camp = ctx.get("camp") if isinstance(ctx.get("camp"), dict) else {}
    if camp:
        name = camp.get("campName") or camp.get("name") or "训练营"
        day = camp.get("currentDay")
        total = camp.get("totalDays")
        remain = camp.get("remainingDays")
        bits = [f"备赛营：{name}"]
        if day is not None or total is not None:
            bits.append(f"第 {day or '—'} / {total or '—'} 天")
        if remain is not None:
            bits.append(f"剩余 {remain} 天")
        parts.append("，".join(bits) + "。")
    today = ctx.get("todayTraining") if isinstance(ctx.get("todayTraining"), dict) else {}
    if today:
        if today.get("hasTrainingDay"):
            title = today.get("title") or ""
            primary = today.get("primaryTask") if isinstance(today.get("primaryTask"), dict) else {}
            pt = primary.get("title") or ""
            parts.append(f"今日训练：{title or pt or '已安排'}。")
            if pt and pt != title:
                parts.append(f"今日唯一任务：{pt}。")
        else:
            parts.append("今日暂无训练日安排。")
    score = ctx.get("latestScore") if isinstance(ctx.get("latestScore"), dict) else {}
    if score and score.get("hasReport"):
        try:
            overall = float(score.get("overallScore"))
            parts.append(f"最近 AI 评分综合 {overall:.1f}/100。")
        except (TypeError, ValueError):
            parts.append("最近有 AI 评分报告。")
    elif score is not None:
        parts.append("尚无最近完成的 AI 评分报告。")
    actions = ctx.get("nextActions") if isinstance(ctx.get("nextActions"), list) else []
    titles = [str(a.get("title") or "").strip() for a in actions if isinstance(a, dict)]
    titles = [t for t in titles if t][:3]
    if titles:
        parts.append("待办提示：" + "；".join(titles) + "。")
    brief = payload_brief if (payload_brief := str(ctx.get("brief") or "").strip()) else ""
    if brief:
        parts.append(brief)
    return " ".join(parts).strip()


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    normalized = base_url.strip().rstrip("/")
    suffix = "/chat/completions"
    if normalized.lower().endswith(suffix):
        normalized = normalized[: -len(suffix)].rstrip("/")
    return normalized or None


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _normalize_backend_base(url: str | None) -> str | None:
    if not url:
        return None
    backend = str(url).strip().rstrip("/")
    if "/api/" in backend:
        backend = backend.split("/api/")[0].rstrip("/")
    # 容器内 127.0.0.1 指向 AI 自己，不是 Spring；改写为 compose 服务名
    if "127.0.0.1" in backend or "localhost" in backend:
        rewrite = (
            getattr(settings, "BACKEND_INTERNAL_URL", None)
            or getattr(settings, "BACKEND_CALLBACK_URL", None)
            or "http://backend:8080"
        )
        rewrite = str(rewrite).strip()
        if "/api/" in rewrite:
            rewrite = rewrite.split("/api/")[0]
        backend = rewrite.rstrip("/")
        logger.info("score-summary backend rewritten from loopback to %s", backend)
    return backend or None


def _fetch_score_summary(payload: dict[str, Any]) -> list[dict[str, Any]]:
    backend = _normalize_backend_base(
        payload.get("backendBaseUrl")
        or getattr(settings, "BACKEND_INTERNAL_URL", None)
        or getattr(settings, "BACKEND_CALLBACK_URL", None)
        or "http://backend:8080"
    )
    token = payload.get("internalToken") or getattr(settings, "ASSISTANT_INTERNAL_TOKEN", "")
    user_id = payload.get("userId")
    team_id = payload.get("teamId")
    if not backend or not user_id:
        logger.warning("score summary skipped: backend=%s userId=%s", backend, user_id)
        return []
    # 完整 reportMarkdown 体积较大，默认只取最近 2 条
    qs = f"userId={user_id}&limit=2"
    if team_id is not None:
        qs += f"&teamId={team_id}"
    url = f"{backend}/api/assistant/internal/score-summary?{qs}"
    req = request.Request(url, headers={"X-Internal-Token": str(token)})
    try:
        with request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            data = body.get("data") if isinstance(body, dict) else body
            if isinstance(data, dict):
                items = data.get("items") or []
                logger.info("score summary fetched %s items for user=%s team=%s", len(items), user_id, team_id)
                return items if isinstance(items, list) else []
    except Exception as e:
        logger.warning("score summary fetch failed url=%s err=%s", url, e)
    return []


def _format_scores(items: list[dict[str, Any]]) -> str:
    if not items:
        return "未找到可用的评分记录。"
    lines = [
        "以下是用户最近评分工具结果（可直接引用，禁止篡改分数与扣分描述）。",
        "若用户索要「评分报告 / Markdown / 详细报告 / md」，优先完整输出下方 reportMarkdown，不要只回总分摘要。",
        "",
    ]
    for i, item in enumerate(items, 1):
        score = item.get("overallScore")
        if score is None:
            score = item.get("overall_score")
        track = item.get("track") or item.get("trackName") or "未标注赛道"
        scored_at = item.get("scoredAt") or item.get("scored_at") or item.get("createdAt") or ""
        lines.append(
            f"### 记录 {i} · 总分={score} · 赛道={track} · 完成={scored_at} "
            f"· sessionId={item.get('sessionId')} · reportId={item.get('reportId')}"
        )
        md = item.get("reportMarkdown") or item.get("report_markdown")
        if isinstance(md, str) and md.strip():
            # 完整报告 MD：直接给模型，便于用户要「详细报告」时原样输出
            lines.append("")
            lines.append("#### reportMarkdown（完整评分报告，用户要报告时请几乎原样输出）")
            lines.append("")
            lines.append(md.strip())
            lines.append("")
            continue
        # 无完整 MD 时退回摘要 + 扣分
        deductions = item.get("topDeductions") or []
        for d in deductions[:8]:
            if isinstance(d, dict):
                lines.append(
                    f"   - 扣分：{d.get('title')} ({d.get('points')}) 建议：{d.get('hint') or ''}"
                )
        issues = item.get("criticalIssues") or item.get("critical_issues") or []
        if isinstance(issues, list) and issues:
            lines.append("   关键问题：")
            for issue in issues[:6]:
                lines.append(f"   - {issue if not isinstance(issue, dict) else issue}")
    return "\n".join(lines)


def _internal_get(
    path: str,
    payload: dict[str, Any],
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 12,
    retries: int = 2,
) -> dict[str, Any] | None:
    """调用 backend /api/assistant/internal/* 只读工具。失败自动重试，避免瞬时重启/抖动被模型说成「读失败」。"""
    import time
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlencode

    backend = _normalize_backend_base(
        payload.get("backendBaseUrl")
        or getattr(settings, "BACKEND_INTERNAL_URL", None)
        or getattr(settings, "BACKEND_CALLBACK_URL", None)
        or "http://backend:8080"
    )
    token = payload.get("internalToken") or getattr(settings, "ASSISTANT_INTERNAL_TOKEN", "")
    if not backend:
        logger.warning("internal tool %s skipped: empty backend base", path)
        return None
    if not token:
        logger.warning("internal tool %s skipped: empty X-Internal-Token", path)
        return None
    q = urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{backend}/api/assistant/internal/{path.lstrip('/')}?{q}"
    last_err: Exception | None = None
    attempts = max(1, int(retries) + 1)
    for attempt in range(1, attempts + 1):
        req = request.Request(url, headers={"X-Internal-Token": str(token), "Accept": "application/json"})
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw)
            data = body.get("data") if isinstance(body, dict) else body
            if not isinstance(data, dict):
                logger.warning(
                    "internal tool %s bad payload type=%s attempt=%s/%s url=%s",
                    path,
                    type(data).__name__,
                    attempt,
                    attempts,
                    url,
                )
                return None
            return data
        except HTTPError as e:
            last_err = e
            logger.warning(
                "internal tool %s HTTP %s attempt=%s/%s url=%s",
                path,
                e.code,
                attempt,
                attempts,
                url,
            )
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            last_err = e
            logger.warning(
                "internal tool %s failed attempt=%s/%s url=%s err=%s",
                path,
                attempt,
                attempts,
                url,
                e,
            )
        except Exception as e:
            last_err = e
            logger.warning(
                "internal tool %s unexpected attempt=%s/%s url=%s err=%s",
                path,
                attempt,
                attempts,
                url,
                e,
            )
        if attempt < attempts:
            time.sleep(0.25 * attempt)
    if last_err is not None:
        logger.warning("internal tool %s gave up after %s attempts: %s", path, attempts, last_err)
    return None


def _collab_fact_card(summary: dict[str, Any]) -> str:
    """从协同工具结构化 data 抽出不可忽视的数字结论，降低模型胡写「读取失败」。"""
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    if not data:
        return ""
    action = data.get("actionRequired")
    mine = data.get("createdByMe")
    progress = data.get("inProgress")
    completed = data.get("completed")
    total = data.get("total")
    role = data.get("resolvedRole") or ""
    lines = [
        "【系统核对·必须遵守】以下数字来自竞赛大脑站内协同工作台，已成功读取：",
        f"- 待我处理（ACTION_REQUIRED）= {action}",
        f"- 我发起的（CREATED_BY_ME）= {mine}",
        f"- 进行中 = {progress}；已完成 = {completed}；合计可见 = {total}",
    ]
    if role:
        lines.append(f"- 解析角色 = {role}")
    lines.append(
        "回答时必须直接使用上述数字；若待我处理=0，明确说「当前没有待你处理的协作」，"
        "可补充「我发起的」列表；禁止声称工具不可用或让用户稍后重试；禁止编造飞书/钉钉。"
    )
    return "\n".join(lines)


def _fetch_context_tools(payload: dict[str, Any], plan: Any) -> list[tuple[str, str]]:
    """
    按 Brain 门闩拉取学习/任务/协同/教师工作台只读上下文。
    返回 [(step_title, markdown_block), ...]
    教师模式：默认拉 teacher-workbench，按问句叠加批改/进度。
    """
    blocks: list[tuple[str, str]] = []
    tenant_id = payload.get("tenantId")
    user_id = payload.get("userId")
    team_id = payload.get("teamId")
    role = payload.get("role") or "STUDENT"
    base = {
        "tenantId": tenant_id,
        "userId": user_id,
        "role": role,
    }
    if tenant_id is None or user_id is None:
        logger.warning(
            "context tools skipped missing ids: keys=%s tenantId=%s userId=%s",
            list(payload.keys()),
            tenant_id,
            user_id,
        )
        return [(
            "读取平台数据…",
            "（内部错误：缺少用户上下文，无法读取竞赛大脑内的训练营/任务/协同。"
            "请刷新页面重试。禁止猜测飞书、钉钉、腾讯文档等外部平台。）",
        )]

    teacher_mode = _is_teacher_mode(payload)
    user_text = ""
    msgs = payload.get("messages") or []
    if msgs:
        last = msgs[-1] if isinstance(msgs[-1], dict) else {}
        user_text = str(last.get("content") or last.get("contentText") or "")

    if teacher_mode:
        logger.info(
            "teacher tools: workbench userId=%s role=%s text=%s",
            user_id,
            role,
            (user_text or "")[:80],
        )
        wb = _internal_get("teacher-workbench", payload, base)
        if wb and wb.get("markdown"):
            blocks.append(("正在读取教师工作台…", str(wb["markdown"])))
        else:
            blocks.append((
                "正在读取教师工作台…",
                "（教师工作台读取失败或无数据。可能原因：账号无教师权限、未关联项目/训练营、"
                "或后端内部工具不可用。禁止编造待批/未交数字，禁止引导去学习通/腾讯文档。）",
            ))
        if _TEACHER_OPS_HINT.search(user_text or "") or getattr(plan, "need_tasks", False):
            rq = _internal_get("teacher-review-queue", payload, base)
            if rq and rq.get("markdown"):
                blocks.append(("正在读取批改概况…", str(rq["markdown"])))
        if re.search(r"进度|缺交|完成率|风险|成员|关注|未交|催交|汇总|工作台", user_text or "", re.I) or getattr(
            plan, "need_learning", False
        ):
            prog = _internal_get("teacher-camp-progress", payload, base)
            if prog and prog.get("markdown"):
                blocks.append(("正在读取训练进度…", str(prog["markdown"])))
    elif getattr(plan, "need_learning", False):
        today = _internal_get("learning-today", payload, base)
        if today and today.get("markdown"):
            blocks.append(("正在读取训练营今日…", str(today["markdown"])))
        else:
            blocks.append(("正在读取训练营今日…", "（训练营今日数据暂不可用或为空。）"))
        if re.search(r"计划|整周|本周|安排|进度", user_text):
            plan_data = _internal_get("learning-plan", payload, base)
            if plan_data and plan_data.get("markdown"):
                blocks.append(("正在读取训练营计划…", str(plan_data["markdown"])))

    if getattr(plan, "need_tasks", False) and not teacher_mode:
        params = {**base, "teamId": team_id}
        tasks = _internal_get("my-tasks", payload, params)
        if tasks and tasks.get("markdown"):
            blocks.append(("正在读取我的任务…", str(tasks["markdown"])))
        else:
            blocks.append(("正在读取我的任务…", "（当前没有可见任务，或读取失败。）"))
        tid = getattr(plan, "task_id_hint", None)
        if tid:
            resolved_team = team_id
            if not resolved_team and isinstance(tasks, dict):
                data = tasks.get("data") or {}
                for t in data.get("tasks") or []:
                    if isinstance(t, dict) and str(t.get("id")) == str(tid):
                        resolved_team = t.get("teamId")
                        break
            if resolved_team:
                detail = _internal_get(
                    "task-detail",
                    payload,
                    {**base, "teamId": resolved_team, "taskId": tid},
                )
                if detail and detail.get("markdown"):
                    blocks.append(("正在读取任务详情…", str(detail["markdown"])))

    if getattr(plan, "need_collab", False):
        # 协同不按会话 teamId 过滤：与侧栏「协作」默认看全部可见团队一致
        # collab-summary 内部会连拉多个 view，给更长超时 + 重试
        summary = _internal_get("collab-summary", payload, base, timeout=20, retries=2)
        if summary and summary.get("markdown"):
            md = str(summary["markdown"])
            fact = _collab_fact_card(summary)
            if fact:
                md = fact + "\n\n" + md
            blocks.append(("正在读取协同工作台…", md))
            data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
            logger.info(
                "collab-summary ok userId=%s action=%s mine=%s progress=%s",
                user_id,
                data.get("actionRequired"),
                data.get("createdByMe"),
                data.get("inProgress"),
            )
        else:
            logger.warning(
                "collab-summary empty userId=%s tenantId=%s backend=%s hasToken=%s",
                user_id,
                tenant_id,
                payload.get("backendBaseUrl") or getattr(settings, "BACKEND_INTERNAL_URL", None),
                bool(payload.get("internalToken") or getattr(settings, "ASSISTANT_INTERNAL_TOKEN", "")),
            )
            blocks.append((
                "正在读取协同工作台…",
                "（竞赛大脑站内协同读取失败。请如实告知用户稍后重试；"
                "禁止猜测飞书/钉钉等外部平台。）",
            ))

    return blocks


def _post_json(path: str, payload: dict[str, Any], body: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    from urllib.parse import urlencode

    backend = _normalize_backend_base(
        payload.get("backendBaseUrl")
        or getattr(settings, "BACKEND_INTERNAL_URL", None)
        or getattr(settings, "BACKEND_CALLBACK_URL", None)
        or "http://backend:8080"
    )
    token = payload.get("internalToken") or getattr(settings, "ASSISTANT_INTERNAL_TOKEN", "")
    if not backend:
        return None
    q = urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{backend}/api/assistant/internal/{path.lstrip('/')}?{q}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "X-Internal-Token": str(token),
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with request.urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
            data_obj = raw.get("data") if isinstance(raw, dict) else raw
            return data_obj if isinstance(data_obj, dict) else None
    except Exception as e:
        logger.warning("internal post %s failed: %s", path, e)
        return None


def _detect_and_propose_actions(payload: dict[str, Any], plan: Any, user_text: str) -> list[dict[str, Any]]:
    """
    识别写意图 → 创建确认提案（不执行）。
    支持：接受/拒绝/撤回协作；创建任务；标记学习完成。
    """
    text = (user_text or "").strip()
    if not text:
        return []
    tenant_id = payload.get("tenantId")
    user_id = payload.get("userId")
    team_id = payload.get("teamId")
    session_id = payload.get("sessionId")
    run_id = payload.get("runId")
    if not tenant_id or not user_id:
        return []

    proposals: list[dict[str, Any]] = []

    def propose(action_type: str, title: str, summary: str, args: dict[str, Any]) -> None:
        body = {
            "actionType": action_type,
            "title": title,
            "summary": summary,
            "args": args,
            "sessionId": session_id,
            "runId": run_id,
        }
        res = _post_json(
            "actions/propose",
            payload,
            body,
            {"tenantId": tenant_id, "userId": user_id},
        )
        if res and res.get("proposalId"):
            proposals.append(res)

    # 协作：接受 / 拒绝 / 撤回  requestId
    m_req = re.search(r"(?:requestId|请求\s*(?:id|ID)?|协作\s*(?:id|ID)?)\s*[=:：#]?\s*(\d{1,12})", text, re.I)
    request_id = int(m_req.group(1)) if m_req else None
    if request_id and re.search(r"接受|同意|通过", text):
        propose(
            "collab_accept",
            "接受协作请求",
            f"将接受协作请求 #{request_id}。确认后才会真正执行。",
            {"requestId": request_id},
        )
    elif request_id and re.search(r"拒绝|不同意|驳回", text):
        propose(
            "collab_decline",
            "拒绝协作请求",
            f"将拒绝协作请求 #{request_id}。确认后才会真正执行。",
            {"requestId": request_id},
        )
    elif request_id and re.search(r"撤回|取消申请", text):
        propose(
            "collab_withdraw",
            "撤回协作请求",
            f"将撤回你发起的协作请求 #{request_id}。确认后才会真正执行。",
            {"requestId": request_id},
        )

    # 创建任务：「创建任务 xxx」且有团队
    m_task = re.search(
        r"(?:创建|新建|加一个)任务[：:\s]*[《\"']?([^《\"'\n]{2,80})[》\"']?",
        text,
    )
    if m_task and team_id and re.search(r"创建|新建|加一个", text):
        title = m_task.group(1).strip()
        propose(
            "create_task",
            "创建项目任务",
            f"将在当前绑定团队（teamId={team_id}）创建任务「{title}」。确认后才会创建。",
            {"teamId": int(team_id), "title": title, "ownerUserId": int(user_id)},
        )

    # 标记学习完成
    m_learn = re.search(r"(?:resourceId|资源\s*(?:id|ID)?)\s*[=:：#]?\s*(\d{1,12})", text, re.I)
    if m_learn and re.search(r"完成|学完|标记完成", text):
        rid = int(m_learn.group(1))
        propose(
            "complete_learning",
            "标记学习完成",
            f"将把学习资源 #{rid} 标记为已完成。确认后才会更新进度。",
            {"resourceId": rid},
        )

    return proposals


def _format_resource_block(contexts: list[dict[str, Any]]) -> str:
    if not contexts:
        return ""
    parts = ["## 参考资料（来自资源中心/用户选材，请优先依据这些内容）"]
    for i, ctx in enumerate(contexts, 1):
        title = ctx.get("title") or f"资料{i}"
        rid = ctx.get("resourceId") or ctx.get("fileId") or ""
        snippet = (ctx.get("snippet") or "").strip()
        if len(snippet) > 8000:
            snippet = snippet[:8000] + "\n…(已截断)"
        parts.append(f"### [{i}] {title} (id={rid})\n{snippet}")
    return "\n\n".join(parts)


def _format_research_block(payload: dict[str, Any]) -> str:
    """Java 端 enrichWithModeResearch 写入的 researchBlock / researchCitations。"""
    raw = payload.get("researchBlock")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    cites = payload.get("researchCitations")
    if not isinstance(cites, list) or not cites:
        return ""
    lines = ["## 检索结果（联网/站内，请优先引用，勿编造链接）"]
    for i, c in enumerate(cites[:8], 1):
        if not isinstance(c, dict):
            continue
        st = str(c.get("sourceType") or "web")
        title = str(c.get("title") or "来源")
        snip = str(c.get("snippet") or c.get("pageText") or "").strip()
        url = str(c.get("url") or "").strip()
        line = f"{i}. [{st}] {title}"
        if snip:
            line += f" — {snip[:160]}"
        if url:
            line += f" URL:{url}"
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""


_FAKE_TOOL_RE = re.compile(
    r"(?is)"
    r"(?:```[\w]*\s*)?"
    r"(?:<function\s*=\s*[^>\n]+>[\s\S]*?(?:</function>|(?=\n\n|\Z)))"
    r"|(?:<tool_call>[\s\S]*?</tool_call>)"
    r"|(?:<parameter\s*=\s*[^>\n]+>[\s\S]*?(?:</parameter>|(?=\n|$)))"
    r"|(?:^\s*call\s+tool\b[^\n]*$)"
    r"|(?:^\s*tool_calls?\s*[:=].*$)",
    re.M,
)


def _strip_fake_tool_calls(text: str) -> str:
    """去掉模型幻觉的 function/tool 调用伪代码。"""
    if not text:
        return text
    cleaned = _FAKE_TOOL_RE.sub("", text)
    # 残留的单独 parameter 行
    cleaned = re.sub(r"(?im)^\s*<parameter\s*=\s*[^>\n]+>.*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*</?function[^>]*>\s*$", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


_SEARCH_DENIAL_RE = re.compile(
    r"(?is)"
    r"(?:我(?:目前|现在)?(?:无法|不能|没法)(?:进行)?实时?(?:网络|互联网|联网)?搜索"
    r"|我没有联网(?:搜索)?工具"
    r"|无法进行实时网络搜索"
    r"|无法实时(?:搜索互联网|网络搜索|联网搜索)"
    r"|没有联网搜索工具"
    r"|我不能检索互联网"
    r"|不支持实时(?:网络)?搜索"
    r"|之前的回复中我假装[^\n。]{0,40})"
)


def _strip_search_capability_denial(text: str, payload: dict[str, Any] | None = None) -> str:
    """去掉「我无法实时搜索」类拒答；有 citation 时整段拒答应被替换。"""
    if not text:
        return text
    payload = payload or {}
    cites = payload.get("researchCitations") if isinstance(payload.get("researchCitations"), list) else []
    has_web = any(isinstance(c, dict) and str(c.get("sourceType") or "") in ("web", "site", "") for c in cites)
    denial_markers = (
        "无法进行实时网络搜索",
        "无法实时网络搜索",
        "没有联网搜索工具",
        "不能实时检索",
        "我无法搜索",
        "假装在",
    )
    had_denial = any(m in text for m in denial_markers) or bool(_SEARCH_DENIAL_RE.search(text))
    if had_denial and cites:
        # 有真实命中却还在否认搜索能力 → 整段作废，交给后续 fallback 用 citation 重建
        return ""
    cleaned = _SEARCH_DENIAL_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if any(m in cleaned for m in denial_markers):
        cleaned = _SEARCH_DENIAL_RE.sub("", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    # 否认残留且无实质内容
    if had_denial and len(cleaned) < 40 and not has_web:
        return ""
    return cleaned


def _build_messages(
    payload: dict[str, Any],
    score_block: str | None,
    need_scores: bool,
    resource_block: str,
    brain_addendum: str = "",
    context_block: str = "",
    skills_block: str = "",
    rules_block: str = "",
) -> list[dict[str, str]]:
    memories = payload.get("memories") or []
    memory_block = ""
    teacher_mode = _is_teacher_mode(payload)
    if memories:
        if teacher_mode:
            memory_block = "\n\n## 该教师的使用偏好（仅本人可见）\n" + "\n".join(
                f"- {m}" for m in memories if m
            )
        else:
            memory_block = "\n\n## 该学生的备赛偏好（仅本人可见，请落实到回答里）\n" + "\n".join(
                f"- {m}" for m in memories if m
            )

    score_policy = (
        "\n\n当前已提供评分工具结果。"
        "若结果中含 reportMarkdown / 完整评分报告："
        "用户要求「详细报告 / Markdown / md / 评分报告全文」时，应直接输出该 Markdown 正文"
        "（可保留标题层级，禁止删减维度分、关键问题、失分明细、改进建议等关键段落，禁止改成只有总分的摘要）。"
        "用户仅问「多少分」时可先答总分，再询问是否需要完整报告。"
        if need_scores and score_block
        else "\n\n当前未提供评分数据。禁止编造具体分数、扣分项或声称已读取评分。"
    )

    base_prompt = TEACHER_SYSTEM_PROMPT if teacher_mode else SYSTEM_PROMPT
    system = base_prompt + memory_block + score_policy
    if teacher_mode:
        system += (
            "\n\n## 教师端硬规则（最高优先级）\n"
            "1. 若下文提供了「教师工作台 / 批改 / 训练进度」工具结果，必须用其中的真实数字回答待批改、未交、需关注等，"
            "禁止说「对话中没有数据 / 请提供名单 / 去学习通导出」。\n"
            "2. 工具结果为空或读取失败时，如实说明「当前账号下暂无训练营数据」或「读取失败」，并引导去教师端工作台/训练进度页查看，"
            "禁止让用户贴 Excel 或去第三方平台。\n"
            "3. 你是教师助教，不是学生备赛教练；禁止按学生视角回答「我的路演开场/讲稿」。\n"
        )
    elif _force_student_audience(payload):
        system += "\n" + HOME_STUDENT_LOCK
        home_brief = str(payload.get("homeContextBrief") or "").strip()
        if not home_brief:
            home_brief = _format_home_client_context(_client_context(payload))
        if home_brief:
            system += (
                "\n\n## 首页上下文 brief（ephemeral，学生本轮状态，必须据此定制回答）\n"
                + home_brief
                + "\n"
            )
    if brain_addendum:
        system += "\n" + brain_addendum
    if rules_block:
        system += "\n\n" + rules_block
    if skills_block:
        system += "\n\n" + skills_block
    if score_block:
        system += "\n\n## 评分工具结果\n" + score_block
    if context_block:
        if teacher_mode:
            system += (
                "\n\n## 教师端平台只读数据（工作台/批改/进度，必须据此回答）\n"
                "说明：以下来自竞赛大脑教师端 API，不是飞书、钉钉、学习通、腾讯文档。\n"
                "请直接用下列数字与名单回答用户；不要索要用户再提供数据。\n"
                + context_block
            )
        else:
            system += (
                "\n\n## 平台只读数据（学习/任务/协同工具结果，必须据此回答）\n"
                "说明：以下来自竞赛大脑站内模块（训练营/项目任务/协同），不是飞书、钉钉、企微、腾讯文档。\n"
                "若工具显示「待我处理=0」或列表为空，请直接告诉用户「当前没有待你处理的协作」，"
                "可补充「我发起的」数量；禁止反问外部平台，禁止编造待办。\n"
                + context_block
            )
    if resource_block:
        system += "\n\n" + resource_block
    research_block = _format_research_block(payload)
    if research_block:
        system += (
            "\n\n"
            + research_block
            + "\n\n引用规则：有检索结果时在文末「依据」列出标题与链接；"
            "若检索结果标题含「未找到直接相关」或写作硬约束要求未找到，"
            "必须明确写「未检索到 / 未找到」，禁止用弱相关/门户首页硬凑答案；"
            "禁止声称无法联网搜索；禁止编造名单与链接。"
        )
    mode = str(payload.get("mode") or payload.get("researchMode") or "").strip()
    if mode in ("deep_search", "think") or research_block:
        system += (
            "\n\n## 联网能力说明（硬约束）\n"
            "本平台会在后台执行联网/站内检索。你**具备**本轮检索结果（见上文「检索结果」区块，可能为空）。"
            "禁止道歉式宣称「无法实时网络搜索」。"
            "空结果或「未找到直接相关」时必须明确说「本轮未命中/未找到」，"
            "禁止用无关页面凑数。"
        )

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in payload.get("messages") or []:
        role = m.get("role")
        content = m.get("content") or ""
        if role in ("user", "assistant") and content is not None:
            messages.append({"role": role, "content": str(content)})
    return messages


def _mimo_client() -> OpenAI:
    api_key = settings.MIMO_WEB_API_KEY or settings.MIMO_API_KEY or settings.PPT_TEXT_API_KEY
    if not api_key:
        raise RuntimeError("MiMo API Key 未配置，无法使用竞赛助手")
    return OpenAI(
        api_key=api_key,
        base_url=_normalize_base_url(settings.MIMO_WEB_BASE_URL or settings.MIMO_BASE_URL),
    )


def stream_run(payload: dict[str, Any]) -> Generator[str, None, None]:
    user_text = ""
    for m in reversed(payload.get("messages") or []):
        if m.get("role") == "user":
            user_text = str(m.get("content") or "")
            break

    resource_ids = payload.get("resourceIds") or []
    resource_contexts = payload.get("resourceContexts") or []
    attachment_contexts = payload.get("attachmentContexts") or []
    options = payload.get("options") or {}
    has_materials = bool(resource_ids or resource_contexts or attachment_contexts)

    # Research Agent（可选）：Java 注入 hits 后由 AI 侧 open/装配 researchBlock
    try:
        from app.services.assistant.research_agent import apply_research_agent_to_payload

        payload = apply_research_agent_to_payload(payload)
    except Exception as e:
        logger.warning("research agent skipped: %s", e)

    # Brain：结构化理解（多轮指代 / Slot / 残句 / 产物类型）
    prior_slots = None
    if isinstance(options, dict):
        prior_slots = options.get("sessionSlots") or options.get("slots")
    if not prior_slots:
        prior_slots = payload.get("sessionSlots") or payload.get("slots")

    plan = plan_turn(
        user_text=user_text,
        messages=payload.get("messages") or [],
        has_resources=has_materials,
        options=options if isinstance(options, dict) else {},
        prior_slots=prior_slots if isinstance(prior_slots, dict) else None,
    )

    # Skills（Grok Build 思路：可复用任务说明书，非编码 Agent）
    skill_audience = "teacher" if _is_teacher_mode(payload) else "student"
    skill_matches, skills_block = resolve_skills_for_turn(
        user_text, audience=skill_audience, limit=2
    )
    skill_gate_tags = apply_skill_tool_gates(plan, skill_matches)
    if skill_gate_tags:
        plan.rationale.extend(skill_gate_tags)

    step_no = 0

    def step_start(key: str, title: str) -> str:
        nonlocal step_no
        step_no += 1
        return _sse("step_start", {"stepNo": step_no, "stepKey": key, "title": title})

    def step_end(summary: str, status: str = "completed") -> str:
        return _sse(
            "step_end",
            {"stepNo": step_no, "status": status, "outputSummary": summary},
        )

    yield step_start("intent", "理解你的问题")

    # 研究轨迹：把 Research Agent 步骤暴露为可见 step/note（Grok 式过程）
    research_steps = payload.get("researchAgentSteps")
    if isinstance(research_steps, list) and research_steps:
        yield step_end("已理解问题")
        for rs in research_steps[:8]:
            if not isinstance(rs, dict):
                continue
            tool = str(rs.get("tool") or "research")
            summary = str(rs.get("summary") or tool)
            title_map = {
                "web_search": "联网检索",
                "web_search_batch": "多假设检索",
                "open_url": "读取网页",
                "fetch_pdf": "浅读 PDF",
                "session_filter": "复用本轮证据",
                "finish": "检索收束",
            }
            yield step_start(f"research_{tool}", title_map.get(tool, f"研究·{tool}"))
            yield step_end(summary[:120])
            yield _sse(
                "agent_note",
                {
                    "agent": "小启",
                    "agentKey": "xiaoqi",
                    "text": f"研究步骤：{title_map.get(tool, tool)} · {summary[:100]}",
                },
            )
        # Agent 证据 → 前端「依据」角标（Java 已不再预搜发 citation）
        cites = payload.get("researchCitations")
        if isinstance(cites, list):
            for i, c in enumerate(cites[:10], 1):
                if not isinstance(c, dict):
                    continue
                yield _sse(
                    "citation",
                    {
                        "index": c.get("index") or i,
                        "title": c.get("title") or "来源",
                        "snippet": (c.get("snippet") or c.get("pageText") or "")[:200],
                        "url": c.get("url") or "",
                        "sourceType": c.get("sourceType") or "web",
                    },
                )

    # P2b：模糊时 soft LLM 纠偏（失败则保持规则）
    if needs_soft_intent(plan, user_text):
        try:
            client = _mimo_client()
            model_name = settings.MIMO_WEB_MODEL or settings.MIMO_MODEL or "mimo-v2.5-pro"
            _, hist = _last_user_and_history(payload.get("messages") or [])
            override = refine_intent_with_llm(
                client=client,
                model=model_name,
                user_text=user_text,
                plan_public=plan.to_public_dict(),
                slots=plan.slots,
                history_tail=_history_blob(hist, max_chars=2500),
            )
            if override:
                apply_soft_override(plan, override)
                # 纠偏后重算契约
                from app.services.assistant.brain import _build_system_addendum
                from app.services.assistant.slots import SessionSlots, slots_system_block

                plan.soft_intent = True
                plan.system_addendum = _build_system_addendum(plan) + slots_system_block(
                    SessionSlots.from_dict(plan.slots)
                )
                plan.rationale.append("soft_intent_ok")
        except Exception as e:
            logger.warning("soft intent skipped: %s", e)

    intent = plan.to_public_dict()
    if skill_matches:
        intent = {
            **intent,
            "skills": [
                {
                    "name": m.skill.name,
                    "slash": m.skill.slash,
                    "reason": m.reason,
                    "score": m.score,
                }
                for m in skill_matches
            ],
        }
    yield _sse("intent", intent)
    understand_bits = list(intent.get("labels") or ["对话"])
    if plan.project_hint:
        understand_bits.insert(0, f"项目:{plan.project_hint[:16]}")
    if plan.assumptions:
        understand_bits.append("假设：" + plan.assumptions[0][:40])
    if skill_matches:
        understand_bits.append("技能:" + "+".join(m.skill.name for m in skill_matches))
    yield step_end("、".join(understand_bits))

    if skill_matches:
        yield step_start("skills", "启用任务技能")
        yield _sse(
            "skill_match",
            {
                "skills": [
                    {
                        "name": m.skill.name,
                        "description": m.skill.description,
                        "slash": m.skill.slash,
                        "reason": m.reason,
                        "score": round(m.score, 2),
                    }
                    for m in skill_matches
                ]
            },
        )
        yield step_end(
            "、".join(
                (f"/{m.skill.slash}" if m.skill.slash else m.skill.name)
                for m in skill_matches
            )
        )

    # 赛道 RULES + 匿名规范包
    track_hint = None
    if isinstance(plan.slots, dict):
        track_hint = plan.slots.get("track")
    if not track_hint and isinstance(options, dict):
        track_hint = options.get("track") or (options.get("clientContext") or {}).get("track")
    ctx0 = _client_context(payload)
    if not track_hint and isinstance(ctx0, dict):
        track_hint = (
            (ctx0.get("camp") or {}).get("track")
            if isinstance(ctx0.get("camp"), dict)
            else None
        ) or ctx0.get("track")
    # 从评分/用户句补赛道
    if not track_hint and re.search(r"赛道|餐饮|信息|土木|机械", user_text):
        m_tr = re.search(r"(?:赛道|赛项)[：:\s]*([\u4e00-\u9fffA-Za-z]{2,20})", user_text)
        if m_tr:
            track_hint = m_tr.group(1)
        elif "餐饮" in user_text:
            track_hint = "餐饮"
        elif re.search(r"信息|人工智能|AI", user_text, re.I):
            track_hint = "新一代信息技术"
    rules_block, rules_tags = resolve_rules_block(
        track=str(track_hint) if track_hint else None,
        include_anonymity=not _is_teacher_mode(payload),
        include_common=True,
    )
    if rules_tags:
        plan.rationale.extend([f"rules:{t}" for t in rules_tags[:4]])
        yield step_start("rules", "载入赛道与赛场规范")
        yield step_end("、".join(rules_tags))

    score_block = None
    score_items: list[dict[str, Any]] = []
    if plan.need_scores:
        yield step_start("get_scores", "正在获取最近评分…")
        items = _fetch_score_summary(payload)
        score_items = items if isinstance(items, list) else []
        if score_items:
            score_block = _format_scores(score_items)
            yield step_end(f"已读取 {len(score_items)} 条评分摘要")
            for i, item in enumerate(score_items[:3], 1):
                sc = item.get("overallScore")
                if sc is None:
                    sc = item.get("overall_score")
                tr = item.get("track") or item.get("trackName") or ""
                yield _sse(
                    "citation",
                    {
                        "index": i,
                        "title": f"最近 AI 评分 · 总分 {sc if sc is not None else '—'}"
                        + (f" · {tr}" if tr else ""),
                        "snippet": str(item.get("summary") or item.get("topDeductions") or "")[:180],
                        "sourceType": "score",
                        "reportId": item.get("reportId"),
                        "sessionId": item.get("sessionId"),
                    },
                )
        else:
            score_block = "未找到可用的评分记录。"
            yield step_end("没有找到可用的评分记录")

    # 学习 / 任务 / 协同 / 教师工作台 只读工具
    # 根因：Brain 旧门闩不含「工作台/待批改」，教师问句此前从不拉工具 → 模型空聊要用户贴表
    context_blocks: list[str] = []
    teacher_mode = _is_teacher_mode(payload)
    if teacher_mode:
        plan.need_learning = True
        plan.need_tasks = True
        plan.rationale.append("teacher_mode_tools")
    if plan.need_learning or plan.need_tasks or plan.need_collab or teacher_mode:
        for title, md in _fetch_context_tools(payload, plan):
            yield step_start("context_tool", title)
            context_blocks.append(md)
            md_s = str(md or "")
            head = md_s.lstrip()[:80]
            is_tool_fail = head.startswith("（") and (
                "读取失败" in head
                or "内部错误" in head
                or "暂不可用" in head
                or "没有可见任务" in head
                or "无教师权限" in head
                or "不是教师" in head
            )
            if not md_s.strip():
                yield step_end("无数据", status="skipped")
            elif is_tool_fail:
                yield step_end("读取失败，请稍后重试", status="failed")
            else:
                yield step_end("已读取")
                # 强制依据：平台工具也发 citation
                st = "training"
                if "任务" in str(title):
                    st = "task"
                elif "协同" in str(title) or "协作" in str(title):
                    st = "collab"
                elif "教师" in str(title) or "批改" in str(title):
                    st = "teacher"
                yield _sse(
                    "citation",
                    {
                        "title": str(title or "平台数据")[:80],
                        "snippet": md_s.replace("\n", " ")[:180],
                        "sourceType": st,
                    },
                )

    # 真实资料注入（资源中心选材 + 会话附件文本）
    all_contexts: list[dict[str, Any]] = []
    if isinstance(resource_contexts, list):
        all_contexts.extend([c for c in resource_contexts if isinstance(c, dict)])
    if isinstance(attachment_contexts, list):
        all_contexts.extend([c for c in attachment_contexts if isinstance(c, dict)])

    resource_block = ""
    if plan.need_rag or all_contexts:
        yield step_start("rag_search", "正在整理参考资料…")
        if all_contexts:
            resource_block = _format_resource_block(all_contexts)
            ocr_n = 0
            cache_n = 0
            for ctx in all_contexts[:12]:
                if ctx.get("ocr") or ctx.get("extractMethod") == "ocr":
                    ocr_n += 1
                if ctx.get("fromCache"):
                    cache_n += 1
                yield _sse(
                    "citation",
                    {
                        "resourceId": ctx.get("resourceId"),
                        "fileId": ctx.get("fileId"),
                        "title": ctx.get("title") or "资料",
                        "snippet": (str(ctx.get("snippet") or "")[:180]),
                        "method": ctx.get("extractMethod") or ctx.get("method"),
                        "ocr": bool(ctx.get("ocr") or ctx.get("extractMethod") == "ocr"),
                        "fromCache": bool(ctx.get("fromCache")),
                        "sourceType": "resource",
                    },
                )
            summary = f"已载入 {len(all_contexts)} 份参考资料"
            if ocr_n:
                summary += f"（OCR {ocr_n}）"
            if cache_n:
                summary += f"（缓存 {cache_n}）"
            yield step_end(summary)
        else:
            yield step_end("未选中可解析资料，将按对话内容回答", status="skipped")

    # 按 goal 调节温度：产物/复盘更稳，闲聊略活
    temperature = 0.55
    if plan.goal in ("artifact", "score_review", "plan"):
        temperature = 0.35
    elif plan.goal == "rewrite":
        temperature = 0.45
    elif plan.goal == "clarify":
        temperature = 0.5
    if plan.need_light_confirm:
        temperature = 0.35

    context_block = "\n\n".join(context_blocks) if context_blocks else ""

    # L2 写操作：只提案不执行，前端确认卡
    action_note = ""
    proposals = _detect_and_propose_actions(payload, plan, user_text)
    for prop in proposals:
        yield _sse("action_proposal", prop)
        action_note += (
            f"\n- 已向用户发出确认卡：{prop.get('title')}（proposalId={prop.get('proposalId')}）。"
            "请用简短中文说明「请点击下方确认按钮后才会真正执行」，不要声称已完成该写操作。"
        )

    # Plan 轻确认：草案卡（前端展示按钮 → 用户再发「展开完整…」）
    if plan.need_light_confirm:
        kind = plan.light_confirm_kind or "plan"
        expand_text = "展开完整计划" if kind == "plan" else "展开完整改稿"
        title = "本周计划草案" if kind == "plan" else "改稿草案"
        summary = (
            "先确认纲要与假设，再展开完整按天计划。"
            if kind == "plan"
            else "先确认改写方向，再展开完整改后全文。"
        )
        yield _sse(
            "plan_draft",
            {
                "kind": kind,
                "title": title,
                "summary": summary,
                "confirmLabel": "展开完整版",
                "expandText": expand_text,
                "status": "pending",
            },
        )

    yield step_start("llm", "正在思考并生成回答…")
    messages = _build_messages(
        payload,
        score_block,
        plan.need_scores,
        resource_block,
        brain_addendum=plan.system_addendum + action_note,
        context_block=context_block,
        skills_block=skills_block,
        rules_block=rules_block,
    )
    model = settings.MIMO_WEB_MODEL or settings.MIMO_MODEL or "mimo-v2.5-pro"
    full_answer: list[str] = []

    try:
        client = _mimo_client()
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
        )
        thinking_done = False
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield _sse("thinking_delta", {"text": reasoning})
            content = getattr(delta, "content", None)
            if content:
                if not thinking_done:
                    yield _sse("thinking_done", {})
                    thinking_done = True
                for frame in _emit_content_with_think_tags(content):
                    # 收集正文用于可选产物
                    if '"text":' in frame and "content_delta" in frame.split("\n")[0]:
                        try:
                            line = [ln for ln in frame.split("\n") if ln.startswith("data:")][0]
                            payload_obj = json.loads(line[5:].strip())
                            if payload_obj.get("text"):
                                full_answer.append(str(payload_obj["text"]))
                        except Exception:
                            pass
                    yield frame
        if not thinking_done:
            yield _sse("thinking_done", {})
        yield step_end("回答生成完成")
    except Exception as e:
        logger.exception("assistant llm failed")
        yield step_end(f"模型调用失败：{e}", status="failed")
        yield _sse("error", {"code": "LLM_ERROR", "message": str(e), "retryable": True})
        fallback = "抱歉，模型暂时不可用。请稍后重试。"
        yield _sse("content_delta", {"text": fallback})
        full_answer = [fallback]

    # 产物通道：Brain need_doc_gen → P2 JSON 二段生成 → 渲染
    answer_text = "".join(full_answer).strip()
    # 清洗模型幻觉的 <function=search> 等伪工具调用（并尽量用修正全文覆盖前端已流式展示的脏内容）
    scrubbed = _strip_fake_tool_calls(answer_text)
    # 禁止模型把「空结果/未注入」说成「我无法搜索」
    scrubbed2 = _strip_search_capability_denial(scrubbed, payload)
    # 禁止「见附件」却无下载链
    try:
        from app.services.assistant.answer_guard import (
            guard_research_answer,
            research_has_attachment_urls,
        )

        mode_now = str(payload.get("mode") or payload.get("researchMode") or "")
        if mode_now == "deep_search" or payload.get("researchBlock") or research_has_attachment_urls(
            payload
        ):
            guarded = guard_research_answer(
                scrubbed2,
                research_block=str(payload.get("researchBlock") or ""),
                has_attachment_urls=research_has_attachment_urls(payload),
                finish_reason=str(
                    payload.get("researchAgentFinishReason")
                    or payload.get("finishReason")
                    or ""
                ),
            )
            if guarded != scrubbed2:
                scrubbed2 = guarded
    except Exception as e:
        logger.warning("answer_guard skipped: %s", e)
    if scrubbed2 != answer_text:
        if scrubbed != answer_text:
            logger.warning("stripped fake tool-call markup from assistant answer")
        if scrubbed2 != scrubbed:
            logger.warning("stripped search-capability denial from assistant answer")
        scrubbed = scrubbed2
        if len(scrubbed) < 8:
            has_research = bool(
                (isinstance(payload.get("researchBlock"), str) and payload.get("researchBlock").strip())
                or (isinstance(payload.get("researchCitations"), list) and payload.get("researchCitations"))
            )
            cites = payload.get("researchCitations") if isinstance(payload.get("researchCitations"), list) else []
            if cites:
                titles = []
                for c in cites[:5]:
                    if isinstance(c, dict) and c.get("title"):
                        titles.append(str(c.get("title")))
                scrubbed = (
                    "系统已完成联网检索。根据本轮命中摘要：\n"
                    + "\n".join(f"- {t}" for t in titles)
                    + "\n\n完整名单请以教育部/大赛官网正式公示为准。"
                )
            elif has_research:
                scrubbed = (
                    "系统已在后台完成检索，但本轮摘录不足以直接罗列完整获奖名单。"
                    "请以教育部政府门户网站、大赛官网或承办校公示为准核对。"
                )
            else:
                scrubbed = (
                    "本轮联网检索未命中足够相关公开网页。"
                    "可换关键词重试（如：2025 世界职业院校技能大赛 获奖名单 教育部），"
                    "或以 moe.gov.cn / 大赛官网公示为准。"
                )
        # 覆盖脏正文（前端/Java 均支持 content_replace）
        yield _sse("content_replace", {"text": scrubbed})
        answer_text = scrubbed
        full_answer = [scrubbed]

    # 强制依据：模型未写「依据」时，用本轮 citation 源补一节（仅文本，不重复 SSE）
    if plan.force_evidence and answer_text and not re.search(r"(?m)^##?\s*依据\b|依据[：:]", answer_text):
        evidence_lines: list[str] = []
        if score_items:
            for item in score_items[:2]:
                sc = item.get("overallScore")
                if sc is None:
                    sc = item.get("overall_score")
                evidence_lines.append(
                    f"- 依据：最近 AI 评分 · 总分 {sc if sc is not None else '—'}"
                )
        if plan.need_learning and context_block:
            evidence_lines.append("- 依据：训练营 / 今日训练（本轮工具结果）")
        if plan.need_tasks and context_block:
            evidence_lines.append("- 依据：我的任务（本轮工具结果）")
        if plan.need_collab and context_block:
            evidence_lines.append("- 依据：协同待办（本轮工具结果）")
        if resource_block and all_contexts:
            for ctx in all_contexts[:4]:
                nm = ctx.get("title") or "资料"
                evidence_lines.append(f"- 依据：资料《{nm}》")
        if not evidence_lines:
            evidence_lines.append("- 依据：本轮未读到站内评分/训练/资料（或工具为空）")
        footer = "\n\n## 依据\n" + "\n".join(evidence_lines)
        yield _sse("content_delta", {"text": footer})
        answer_text = (answer_text + footer).strip()
        full_answer.append(footer)

    if plan.need_doc_gen and answer_text and len(answer_text) > 80:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        generated_names: list[str] = []
        import base64

        from app.services.assistant.artifact_schema import (
            generate_artifact_schema,
            schema_to_markdown,
        )
        from app.services.assistant.doc_generate import (
            deck_schema_to_pptx_bytes,
            doc_schema_to_docx_bytes,
            markdown_to_docx_bytes,
            markdown_to_pptx_bytes,
            markdown_to_xlsx_bytes,
            plan_schema_to_xlsx_bytes,
        )

        art_title = default_artifact_title(plan)
        artifact = plan.artifact or "docx"
        render_text = prepare_artifact_markdown(
            answer_text, artifact=artifact, title=art_title
        )

        # Step A: 结构化
        yield step_start("doc_struct", "正在把回答整理成结构化产物…")
        schema = None
        schema_source = "none"
        try:
            client = _mimo_client()
            schema, schema_source = generate_artifact_schema(
                client=client,
                model=model,
                artifact=artifact,
                title=art_title,
                answer_text=answer_text,
                user_text=user_text,
                project_hint=plan.project_hint,
                temperature=0.2,
            )
        except Exception as e:
            logger.warning("schema generation setup failed: %s", e)
            schema, schema_source = None, "none"

        if schema:
            render_text = schema_to_markdown(schema)
            yield step_end(f"结构化完成（来源：{schema_source}）")
        else:
            yield step_end("结构化跳过，将按正文渲染", status="skipped")

        # Step B: 渲染文件
        yield step_start("doc_render", "正在渲染可下载文件…")

        md_name = f"助手文稿-{stamp}.md"
        yield _sse(
            "file",
            {
                "name": md_name,
                "mime": "text/markdown",
                "source": "generated",
                "textContent": render_text,
            },
        )
        generated_names.append(md_name)

        if schema:
            try:
                schema_name = f"助手结构-{stamp}.json"
                yield _sse(
                    "file",
                    {
                        "name": schema_name,
                        "mime": "application/json",
                        "source": "generated",
                        "textContent": json.dumps(schema, ensure_ascii=False, indent=2),
                    },
                )
                generated_names.append(schema_name)
            except Exception:
                pass

        if artifact in ("docx", "md", "pdf"):
            try:
                if schema and schema.get("type") == "doc":
                    docx_bytes = doc_schema_to_docx_bytes(schema)
                else:
                    docx_bytes = markdown_to_docx_bytes(render_text, title=art_title)
                docx_name = f"助手文稿-{stamp}.docx"
                yield _sse(
                    "file",
                    {
                        "name": docx_name,
                        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "source": "generated",
                        "contentBase64": base64.b64encode(docx_bytes).decode("ascii"),
                        "size": len(docx_bytes),
                    },
                )
                generated_names.append(docx_name)
            except Exception as e:
                logger.warning("docx render failed: %s", e)

            if artifact == "pdf":
                try:
                    from app.services.assistant.pdf_export import markdown_to_pdf_bytes

                    pdf_bytes = markdown_to_pdf_bytes(render_text, title=art_title)
                    pdf_name = f"助手文稿-{stamp}.pdf"
                    yield _sse(
                        "file",
                        {
                            "name": pdf_name,
                            "mime": "application/pdf",
                            "source": "generated",
                            "contentBase64": base64.b64encode(pdf_bytes).decode("ascii"),
                            "size": len(pdf_bytes),
                        },
                    )
                    generated_names.append(pdf_name)
                except Exception as e:
                    logger.warning("pdf render failed: %s", e)

        if artifact == "xlsx":
            try:
                if schema and schema.get("type") == "plan":
                    xlsx_bytes = plan_schema_to_xlsx_bytes(schema)
                else:
                    xlsx_bytes = markdown_to_xlsx_bytes(
                        render_text, sheet_title=art_title[:31] or "计划"
                    )
                xlsx_name = f"助手计划-{stamp}.xlsx"
                yield _sse(
                    "file",
                    {
                        "name": xlsx_name,
                        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "source": "generated",
                        "contentBase64": base64.b64encode(xlsx_bytes).decode("ascii"),
                        "size": len(xlsx_bytes),
                    },
                )
                generated_names.append(xlsx_name)
            except Exception as e:
                logger.warning("xlsx render failed: %s", e)

        if artifact == "pptx":
            try:
                if schema and schema.get("type") == "deck":
                    pptx_bytes = deck_schema_to_pptx_bytes(schema)
                else:
                    pptx_bytes = markdown_to_pptx_bytes(render_text, title=art_title)
                pptx_name = f"助手提纲-{stamp}.pptx"
                yield _sse(
                    "file",
                    {
                        "name": pptx_name,
                        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "source": "generated",
                        "contentBase64": base64.b64encode(pptx_bytes).decode("ascii"),
                        "size": len(pptx_bytes),
                    },
                )
                generated_names.append(pptx_name)
            except Exception as e:
                logger.warning("pptx render failed: %s", e)

        yield step_end(
            "已生成：" + "、".join(generated_names) if generated_names else "产物生成完成"
        )

    yield _sse("heartbeat", {"ts": time.time()})




def _emit_content_with_think_tags(text: str) -> Iterable[str]:
    if "<think>" in text.lower() or "</think>" in text.lower():
        parts = re.split(r"(?i)(</?think>)", text)
        mode = "content"
        buf_events: list[str] = []
        for part in parts:
            if not part:
                continue
            if part.lower() == "<think>":
                mode = "thinking"
                continue
            if part.lower() == "</think>":
                mode = "content"
                continue
            if mode == "thinking":
                buf_events.append(_sse("thinking_delta", {"text": part}))
            else:
                buf_events.append(_sse("content_delta", {"text": part}))
        return buf_events
    return [_sse("content_delta", {"text": text})]
