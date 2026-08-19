"""LLM Research Planner：Grok 式「先想 → 多假设工具 → 观察 → 再规划」。

主决策在模型；规则只做 tool 卫生与解析护栏，不写业务 if-else。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from app.services.assistant.query_anchors import extract_query_anchors
from app.services.assistant.research_tools import normalize_tool_call

logger = logging.getLogger(__name__)

LlmFn = Callable[[str], str]

_JSON_OBJ = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        m = _JSON_OBJ.search(t)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None


def parse_planner_response(raw: str) -> dict[str, Any]:
    """解析 LLM 输出为 tool call。"""
    obj = _extract_json(raw) or {}
    name = str(obj.get("name") or obj.get("tool") or "").strip()
    args = obj.get("arguments") if isinstance(obj.get("arguments"), dict) else {}
    if not args and isinstance(obj.get("args"), dict):
        args = obj["args"]
    if not name and isinstance(obj.get("queries"), list):
        name = "web_search_batch"
        args = {"queries": obj.get("queries")}
    thought = str(obj.get("thought") or obj.get("rationale") or "").strip()
    call = normalize_tool_call({"name": name, "arguments": args})
    if thought:
        call["thought"] = thought
    if call.get("name") == "web_search_batch":
        qs = call.get("arguments", {}).get("queries") or []
        cleaned: list[str] = []
        if isinstance(qs, list):
            for q in qs:
                s = re.sub(r"\s+", " ", str(q or "").strip())
                if 1 <= len(s) <= 48 and s not in cleaned:
                    cleaned.append(s)
                if len(cleaned) >= 5:
                    break
        call["arguments"] = {"queries": cleaned}
    return call


def build_planner_prompt(
    state: Any,
    *,
    max_steps: int,
    max_open: int,
    max_pdf: int,
) -> str:
    """Grok 式规划提示：多 hop、观察后改写、拒凑数。"""
    anchors = extract_query_anchors(getattr(state, "query", "") or "")
    prior = list(getattr(state, "prior_queries", None) or [])
    hits = list(getattr(state, "hits", None) or [])
    evidence = list(getattr(state, "evidence", None) or [])
    opened = list(getattr(state, "opened_urls", None) or [])
    failed = list(getattr(state, "failed_urls", None) or [])
    step = int(getattr(state, "step_count", 0) or 0)
    search_count = int(getattr(state, "search_count", 0) or 0)

    hit_lines = []
    for h in hits[:10]:
        if not isinstance(h, dict):
            continue
        hit_lines.append(
            f"- {str(h.get('title') or '')[:70]} | {str(h.get('url') or '')[:90]}"
        )
    ev_lines = []
    for e in evidence[:8]:
        if not isinstance(e, dict):
            continue
        ev_lines.append(
            f"- {str(e.get('title') or '')[:70]} fetched={bool(e.get('fetched'))} "
            f"chars={len(str(e.get('pageText') or ''))} "
            f"url={(e.get('url') or '')[:70]}"
        )

    geo_hint = "、".join(anchors.required) if anchors.required else "（未识别）"
    topic_hint = (
        "、".join(anchors.content_phrases[:4])
        if anchors.content_phrases
        else "（从问题理解）"
    )
    year_hint = "、".join(anchors.years) if anchors.years else "（无）"
    opened_ok = [u for u in opened if u not in set(failed)]

    return f"""你是联网研究 Agent 规划器（Grok 式多跳：think → tool → 观察 → 再 think）。
只输出一个 JSON 对象，不要 Markdown 代码块，不要其它文字。
thought 字段用中文写清「当前缺什么 / 为何选这个工具」（≤80字）。

## 工具
1) web_search_batch — 首轮首选。arguments.queries：3～5 条互不相同短检索式（≤48字）
2) web_search — 单条补搜 / 第二跳改写。arguments.q
3) open_url — 细读 hits/evidence 中的 URL。arguments.url
4) fetch_pdf — 浅读 PDF。arguments.url + 可选 keywords
5) finish — arguments.reason = enough | empty | max_steps

## 多跳策略（必须遵守）
1. **理解意图**：读页 / 名单 / 政策文号 / **对比（两侧）** / 时效 / 查无 / 域名职责 / 规模数字？
2. **首轮**（无用户 URL）：web_search_batch，queries 覆盖：
   - 核心实体 + 主题 + 年份（若有）
   - 同义改写（职业院校↔高等职业教育/高职；通知↔公示）
   - 需要官方页时加通用词：教育厅/通知/公示/名单/site:gov.cn（**不要**写死省域白名单表）
   - **对比题强制拆侧**：A 侧独立 query、B 侧独立 query（勿把「比较河南省与山东省…」糊成一条）
3. **观察 hits**：标题是否同时贴近「实体+主题」。门户首页、考试院首页、旅游/百科/娱乐 → **不要 open**，改写检索再搜。
4. **open**：优先标题含「通知/公示/名单/职责/赛道」的实质页；**不要**优先人民政府/考试院**首页壳**；正文不够 → 换另一条 open 或再 search，**禁止**立刻 finish enough。
5. **第二跳/第三跳**（多 hop 核心）：
   - 已 open 仍缺关键字段（文号、规模、**另一侧对比数据**、PDF 名单）→ 必须再 search/open/fetch_pdf
   - **对比题**：若 evidence 只有 A 侧、缺 B 侧 → 用 B 侧地名+同一主题再 web_search/batch，禁止因「只有一侧」就 finish empty
   - 首轮全跑题 → 用更具体实体+「通知/公示」或 site:gov.cn 再 batch，不要 finish enough
   - 预算未尽且 evidence 无法直接回答核心问题 → **继续工具**，不要凑 enough
6. **finish enough**：
   - 普通题：≥1 条证据标题/正文含问题**核心专名+主题**（允许「数字见摘录」「名单见 PDF 链接」）
   - **对比题**：至少一侧有可引用规模/名单/通知证据即可 enough（另一侧可写「本轮未检索到」）；两侧都有更好
7. **finish empty（拒凑数）**：以下任一即 empty：
   - 只有门户/频道/考试院**首页壳**，答不了原问题
   - 证据主题与问题明显无关（跑题页）
   - **问题中的具体机构/专业/产品专名在证据中完全不出现**（查无/虚构）——不能用「区政府首页」冒充招生简章
   - **严禁**因「有几条 hit / 有 .gov.cn」就 enough
8. 禁止 open 失败列表与 baidu.com/link 未解析链；禁止重复 prior 检索词。
9. 预算：步数 {step}/{max_steps}，已成功 open 约 {len(opened_ok)}/{max_open}，search 轮次 {search_count}。
   步数尚早且证据不足时优先再 search/open，勿过早 finish。

## 弱提示（排序提示，不是硬过滤表）
- 地理：{geo_hint}
- 主题：{topic_hint}
- 年份：{year_hint}

## 状态
用户问题：{(getattr(state, "query", "") or "")[:300]}
已用检索词：{prior[:10] or "（无）"}
失败 URL：{failed[:8] or "（无）"}
已打开 URL：{opened[:8] or "（无）"}
hits：
{chr(10).join(hit_lines) if hit_lines else "（无）"}
evidence：
{chr(10).join(ev_lines) if ev_lines else "（无）"}

JSON：{{"thought":"…","name":"web_search_batch","arguments":{{"queries":["…"]}}}}
"""


def llm_finish_judge(
    query: str,
    evidence: list[dict[str, Any]] | None,
    proposed_reason: str = "",
    *,
    llm_fn: LlmFn | None = None,
) -> str:
    """LLM 判断 enough/empty：拒凑数；宁可 empty 也不用门户壳硬凑。"""
    ev = [e for e in (evidence or []) if isinstance(e, dict)][:10]
    lines = []
    for e in ev:
        atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
        att_bits = []
        for a in atts[:5]:
            if not isinstance(a, dict):
                continue
            au = str(a.get("url") or "").strip()
            at = str(a.get("title") or "附件")[:40]
            if au:
                att_bits.append(f"{at}|{au[:80]}")
        att_line = ("  attachments: " + "; ".join(att_bits)) if att_bits else ""
        lines.append(
            f"- title={(e.get('title') or '')[:90]}\n"
            f"  url={(e.get('url') or '')[:100]}\n"
            f"  fetched={bool(e.get('fetched'))} "
            f"text={(e.get('pageText') or e.get('snippet') or '')[:180]}"
            + (f"\n{att_line}" if att_line else "")
        )
    # 轻量结构提示（给裁判，不是硬编码答案表）
    notice_pdf = False
    list_sub = False
    try:
        from app.services.assistant.query_anchors import (
            comparison_sides_covered,
            evidence_has_list_notice_with_pdf,
            evidence_has_list_substance,
            extract_distinctive_entities,
            is_comparison_query,
            is_full_list_demand,
            looks_like_portal_shell,
        )

        ents = extract_distinctive_entities(query)
        ent_hint = "、".join(ents[:6]) if ents else "（未抽到专名）"
        is_cmp = is_comparison_query(query)
        covered, missing = comparison_sides_covered(query, ev)
        cmp_hint = (
            f"对比题=是；已覆盖侧={covered or '无'}；缺失侧={missing or '无'}"
            if is_cmp
            else "对比题=否"
        )
        full_list = is_full_list_demand(query)
        notice_pdf = evidence_has_list_notice_with_pdf(ev)
        list_sub = evidence_has_list_substance(ev)
        shell_n = sum(1 for e in ev if looks_like_portal_shell(e))
        list_hint = (
            f"名单通知+PDF信号={'是' if notice_pdf else '否'}；"
            f"名单实质(正文或PDF)={'是' if list_sub else '否'}；"
            f"完整名单需求={'是' if full_list else '否'}；"
            f"疑似门户壳条数={shell_n}"
        )
    except Exception:
        ent_hint = "（未抽到专名）"
        cmp_hint = "对比题=未知"
        list_hint = "名单信号=未知"

    prompt = f"""你是联网研究收尾裁判（Grok 式：诚实优先，拒绝凑数）。
只输出 JSON：{{"reason":"enough"}} 或 {{"reason":"empty"}}，可加 "why":"≤40字"。

## 先抽取用户问题的「必答核」
用一句话自问：用户到底要什么？（名单/规模/对比两侧/机构职责/URL 要点/某专名原文/完整逐条名单）
再逐条看证据能否支撑这个核。

结构提示（可参考）：
- 专名候选：{ent_hint}
- {cmp_hint}
- {list_hint}

## enough
**普通题**须同时：
1. ≥1 条证据的标题或正文与**核心专名+主题**直接相关（不是只沾边区县名或 .gov.cn 首页）；
2. 据此能写出有出处的回答（允许「数字见摘录」「完整名单见 PDF 链接」）。

**名单类问法（问「获奖名单/公示/有哪些获奖」等，非必须逐队抄全）**：
- 若证据同时有 **「公布/公示/获奖名单」类通知** + **可下载 PDF/附件链接** → **enough**；
- 回答应写清通知标题、链接，并说明完整名单见 PDF/附件（Markdown 链），**不要** empty。
- 仅有考试院/政府**首页壳**、无通知也无 PDF → empty。

**对比题（比较/对照/多省）**：
- 至少**一侧**有可引用的主题相关证据（规模/通知/名单等）→ **enough**（可注明另一侧本轮不足）；
- 不要因为「只有一侧」就 empty；两侧都无主题证据才 empty。

**完整/逐条名单需求**（用户含全部/完整/逐队/逐条等）：
- enough **仅当**：证据中有可引用的名单正文（多条姓名/队名/奖项），**或**有可下载 PDF/附件链接且标题指向名单；
- 仅有教育考试院首页、政府门户、旅游页、空通知壳 → **empty**，禁止编造队伍列表。

## empty（有一条即 empty）
- 证据全是人民政府/考试院/频道**首页壳**，答不了原问题；
- 证据主题明显跑题；
- **问题中的具体机构名/专业名/产品名在证据标题与正文中完全不出现**（查无或虚构）；
- 只有域名或导航菜单，无实质可引用内容；
- **完整名单需求**但无名单正文也无 PDF/附件 → empty。

## 严禁（拒凑数）
- 因 URL 含 .gov.cn / edu.cn 就 enough；
- 因「搜到了几条」或规划器说 enough 就 enough；
- 用跑题页/首页壳硬凑答案；
- **有名单通知+PDF 时不要 empty**（应 enough 并引导看 PDF）；
- 证据只能回答「有个网站」却答不了用户问的专名对象 → empty；
- **不得编造**完整金奖/获奖队伍列表；用户禁止「见附件」时，若无正文名单也无真实下载链 → empty。

规划器建议：{proposed_reason or "无"}（仅供参考，你可推翻）

用户问题：{(query or "")[:320]}

证据列表：
{chr(10).join(lines) if lines else "（无证据）"}
"""
    raw = ""
    try:
        if llm_fn is not None:
            raw = llm_fn(prompt) or ""
        else:
            # 收尾裁判：低温、短输出，稳定 enough/empty
            raw = _default_llm(prompt, max_tokens=160, temperature=0.0)
    except Exception as e:
        logger.info("finish judge llm fail: %s", e)
        # 解析失败：有名单通知+PDF 时偏 enough，否则 empty
        if notice_pdf or list_sub:
            return "enough"
        return (proposed_reason or "").strip() or "empty"
    obj = _extract_json(raw) or {}
    reason = str(obj.get("reason") or "").strip().lower()
    if reason in ("enough", "empty"):
        # 名单通知+PDF：LLM 误 empty 时纠正（形态信号，非业务表）
        if reason == "empty" and notice_pdf:
            return "enough"
        return reason
    low = (raw or "").lower()
    # 解析失败时：有名单通知+PDF 偏 enough；否则偏 empty（拒凑数）
    if notice_pdf or (list_sub and "empty" not in low):
        if "empty" in low and not notice_pdf:
            return "empty"
        if notice_pdf:
            return "enough"
    if "empty" in low:
        return "empty"
    if '"reason":"empty"' in low or "'reason':'empty'" in low:
        return "empty"
    if "enough" in low and "empty" not in low:
        return "enough"
    if not ev:
        return "empty"
    # 有证据但解析失败：保留规划器建议；规划器也不清时 empty
    prop = (proposed_reason or "").strip().lower()
    if prop in ("enough", "empty"):
        return prop
    return "empty"


def plan_research_step(
    state: Any,
    *,
    llm_fn: LlmFn | None = None,
    max_steps: int = 8,
    max_open: int = 2,
    max_pdf: int = 2,
) -> dict[str, Any]:
    """调用 LLM（或注入的 llm_fn）得到下一步 tool call。"""
    prompt = build_planner_prompt(
        state, max_steps=max_steps, max_open=max_open, max_pdf=max_pdf
    )
    raw = ""
    if llm_fn is not None:
        raw = llm_fn(prompt) or ""
    else:
        # 规划器：略低温、足量 token，鼓励多跳 thought + 多 query
        raw = _default_llm(prompt, max_tokens=720, temperature=0.1)
    if not raw.strip():
        raise RuntimeError("planner_llm_empty")
    call = parse_planner_response(raw)
    if not call.get("name"):
        raise RuntimeError("planner_no_tool")
    if call["name"] == "web_search_batch":
        qs = call.get("arguments", {}).get("queries") or []
        if len(qs) < 1:
            raise RuntimeError("planner_empty_queries")
    return call


def _default_llm(
    prompt: str,
    *,
    max_tokens: int = 600,
    temperature: float = 0.15,
) -> str:
    try:
        from app.services.assistant.web_research import _llm_json_chat

        content, _model = _llm_json_chat(
            prompt, max_tokens=max_tokens, temperature=temperature
        )
        return content or ""
    except Exception as e:
        logger.warning("planner llm failed: %s", e)
        return ""


def _dedupe_search_call(call: dict[str, Any], state: Any) -> dict[str, Any]:
    """禁止与 prior_queries 完全重复；重复则改写为未用假设。"""
    from app.services.assistant.query_anchors import (
        build_search_query_variants,
        next_unused_query,
    )

    name = call.get("name") or ""
    prior = list(getattr(state, "prior_queries", None) or [])
    prior_set = {re.sub(r"\s+", " ", str(p).strip()) for p in prior}

    if name == "web_search":
        q = re.sub(r"\s+", " ", str((call.get("arguments") or {}).get("q") or "").strip())
        if not q or q in prior_set:
            nxt = next_unused_query(getattr(state, "query", "") or "", prior)
            if nxt:
                return {
                    "name": "web_search",
                    "arguments": {"q": nxt},
                    "thought": call.get("thought") or "rewrite_unused_query",
                }
        return call

    if name == "web_search_batch":
        qs = list((call.get("arguments") or {}).get("queries") or [])
        cleaned: list[str] = []
        for q in qs:
            s = re.sub(r"\s+", " ", str(q or "").strip())
            if s and s not in prior_set and s not in cleaned:
                cleaned.append(s[:48])
        if len(cleaned) < 2:
            cleaned = build_search_query_variants(
                getattr(state, "query", "") or "",
                max_n=4,
                prior_queries=prior,
            )
        if cleaned:
            return {
                "name": "web_search_batch",
                "arguments": {"queries": cleaned[:5]},
                "thought": call.get("thought") or "",
            }
    if name == "open_url":
        url = str((call.get("arguments") or {}).get("url") or "")
        failed = set(getattr(state, "failed_urls", None) or [])
        opened = set(getattr(state, "opened_urls", None) or [])
        if url in failed or "baidu.com/link" in url:
            # 不在此硬判 enough：有 hit 可换链；否则 empty（拒凑数）
            hits = list(getattr(state, "hits", None) or [])
            alt = None
            for h in hits:
                if not isinstance(h, dict):
                    continue
                u2 = str(h.get("url") or "")
                if u2 and u2 not in failed and u2 not in opened and "baidu.com/link" not in u2:
                    alt = u2
                    break
            if alt:
                return {
                    "name": "open_url",
                    "arguments": {"url": alt},
                    "thought": "blocked_url_try_alt",
                }
            return {
                "name": "finish",
                "arguments": {"reason": "empty"},
                "thought": "blocked_url_fallback",
            }
        # 已 open 过的链不要再 open：优先换下一条 hit，勿直接 enough 凑数
        if url in opened:
            hits = list(getattr(state, "hits", None) or [])
            for h in hits:
                if not isinstance(h, dict):
                    continue
                u2 = str(h.get("url") or "")
                if u2 and u2 not in opened and u2 not in failed and "baidu.com/link" not in u2:
                    return {
                        "name": "open_url",
                        "arguments": {"url": u2},
                        "thought": "already_opened_try_alt",
                    }
            return {
                "name": "finish",
                "arguments": {
                    "reason": "enough"
                    if getattr(state, "evidence", None)
                    else "empty"
                },
                "thought": "already_opened",
            }
    return call


def make_llm_planner(
    *,
    llm_fn: LlmFn | None = None,
    max_steps: int = 8,
    max_open: int = 2,
    max_pdf: int = 2,
    fallback: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[Any], dict[str, Any]]:
    """返回 planner_fn(state)->tool_call；失败时走 fallback。"""

    def _run_fallback(state: Any) -> dict[str, Any]:
        if fallback is None:
            raise RuntimeError("no_fallback")
        try:
            return fallback(
                state,
                max_steps=max_steps,
                max_open=max_open,
                max_pdf=max_pdf,
            )
        except TypeError:
            return fallback(state)

    def _planner(state: Any) -> dict[str, Any]:
        try:
            call = plan_research_step(
                state,
                llm_fn=llm_fn,
                max_steps=max_steps,
                max_open=max_open,
                max_pdf=max_pdf,
            )
            call = _dedupe_search_call(call, state)
            name = call.get("name") or ""
            hits = list(getattr(state, "hits", None) or [])
            opened = list(getattr(state, "opened_urls", None) or [])
            failed = set(getattr(state, "failed_urls", None) or [])
            opened_ok = [u for u in opened if u not in failed]
            # 有 hit 却 finish 且还没成功 open → heuristic 尝试 open（多 hop）
            if name == "finish" and hits and not opened_ok and fallback is not None:
                return _run_fallback(state)
            # 对比题：过早 finish 且仍缺一侧 → 再搜缺失侧（工具路径，不硬改 enough/empty）
            if name == "finish" and int(getattr(state, "search_count", 0) or 0) < 4:
                try:
                    from app.services.assistant.query_anchors import (
                        comparison_sides_covered,
                        extract_geo_phrases,
                        extract_query_anchors,
                        is_comparison_query,
                    )
                    from app.services.assistant.research_agent import (
                        pick_open_url_for_geo,
                        side_has_substantive_open,
                    )

                    q = getattr(state, "query", "") or ""
                    if is_comparison_query(q):
                        _cov, missing = comparison_sides_covered(
                            q, getattr(state, "evidence", None) or hits
                        )
                        if missing:
                            a = extract_query_anchors(q)
                            geo = missing[0]
                            topic = (a.content_phrases or [""])[0] or ""
                            year = (a.years or [""])[0]
                            q2 = " ".join(p for p in (geo, year, topic) if p)[:48]
                            prior = {
                                re.sub(r"\s+", " ", str(p).strip())
                                for p in (getattr(state, "prior_queries", None) or [])
                            }
                            if q2 and q2 not in prior:
                                return {
                                    "name": "web_search",
                                    "arguments": {"q": q2},
                                    "thought": "compare_missing_side_continue",
                                }
                        # 两侧有 hit 但缺实质 open → 强制双侧实质页（可并行）
                        opened = list(getattr(state, "opened_urls", None) or [])
                        failed = set(getattr(state, "failed_urls", None) or [])
                        opened_ok_n = len([u for u in opened if u not in failed])
                        if opened_ok_n < max_open and hits:
                            need_urls: list[str] = []
                            for g in extract_geo_phrases(q)[:4]:
                                if side_has_substantive_open(state, g):
                                    continue
                                u = pick_open_url_for_geo(state, g)
                                if u and u not in need_urls:
                                    need_urls.append(u)
                            if need_urls:
                                return {
                                    "name": "open_url",
                                    "arguments": {
                                        "url": need_urls[0],
                                        "urls": need_urls[
                                            : max(1, min(3, max_open - opened_ok_n))
                                        ],
                                    },
                                    "thought": "compare_force_dual_open",
                                }
                except Exception:
                    pass
            # 空结果再 hop：finish empty 但预算未尽且尚可换检索式
            if name == "finish" and str((call.get("arguments") or {}).get("reason") or "") in (
                "empty",
                "",
            ):
                try:
                    from app.services.assistant.query_anchors import next_unused_query
                    from app.services.assistant.public_search import (
                        looks_pdf_seeking_query,
                        looks_time_sensitive_query,
                    )

                    q = getattr(state, "query", "") or ""
                    sc = int(getattr(state, "search_count", 0) or 0)
                    if sc < 3 and not hits:
                        q2 = next_unused_query(
                            q, list(getattr(state, "prior_queries", None) or []), max_n=8
                        )
                        if q2:
                            if looks_pdf_seeking_query(q) and "附件" not in q2:
                                q2 = (q2 + " 附件").strip()[:48]
                            elif looks_time_sensitive_query(q) and "通知" not in q2:
                                q2 = (q2 + " 通知").strip()[:48]
                            return {
                                "name": "web_search",
                                "arguments": {"q": q2[:48]},
                                "thought": "empty_engine_rehop",
                            }
                except Exception:
                    pass
            return call
        except Exception as e:
            logger.info("llm planner fallback: %s", e)
            if fallback is not None:
                return _run_fallback(state)
            raise

    return _planner
