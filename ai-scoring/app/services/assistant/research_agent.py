"""Grok-style Research Agent：可注入 search/open 的多步 tool loop。

不绑定具体搜索引擎；生产侧注入 360/Bing 等现有实现。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from app.services.assistant.domain_rank import sort_hits_by_soft_rank
from app.services.assistant.query_anchors import (
    extract_query_anchors,
    filter_hits_by_anchors,
    hit_passes_anchors,
    rank_hits_soft,
)
from app.services.assistant.research_metrics import log_research_metrics, summarize_research_metrics
from app.services.assistant.research_tools import (
    FetchPdfFn,
    OpenFn,
    SearchFn,
    execute_tool,
    normalize_tool_call,
)

PlannerFn = Callable[["AgentState"], dict[str, Any]]

AUTHORITATIVE_HOST_MARKERS = (
    "moe.gov.cn",
    ".gov.cn",
    ".edu.cn",
    "chinazy.org",
    "eol.cn",
)


@dataclass
class ResearchBudget:
    """研究预算：限制步数/打开页/PDF，控制延迟。"""

    max_steps: int = 8
    max_open: int = 2
    max_pdf: int = 2
    timeout_sec: float = 35.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ResearchBudget":
        p = payload if isinstance(payload, dict) else {}
        opt = p.get("options") if isinstance(p.get("options"), dict) else {}
        rb = p.get("researchBudget") if isinstance(p.get("researchBudget"), dict) else {}
        src = {**opt, **rb}

        def _i(key: str, default: int) -> int:
            try:
                return int(src.get(key, default))
            except Exception:
                return default

        def _f(key: str, default: float) -> float:
            try:
                return float(src.get(key, default))
            except Exception:
                return default

        return cls(
            max_steps=max(1, min(_i("maxSteps", _i("max_steps", 8)), 12)),
            max_open=max(1, min(_i("maxOpen", _i("max_open", 2)), 5)),
            max_pdf=max(0, min(_i("maxPdf", _i("max_pdf", 2)), 4)),
            timeout_sec=max(5.0, min(_f("timeoutSec", _f("timeout_sec", 35.0)), 90.0)),
        )


@dataclass
class ResearchStep:
    step_no: int
    tool: str
    args: dict[str, Any]
    result_summary: str


@dataclass
class AgentState:
    query: str
    step_count: int = 0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    steps: list[ResearchStep] = field(default_factory=list)
    hits: list[dict[str, Any]] = field(default_factory=list)
    opened_urls: list[str] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)  # open 失败/维护页，禁止再开
    prior_queries: list[str] = field(default_factory=list)
    search_count: int = 0
    pdf_count: int = 0
    last_thought: str = ""
    finish_reason: str | None = None


_UNRESOLVED_LINK_RE = re.compile(
    r"baidu\.com/link\?|so\.com/link\?|bing\.com/ck/", re.I
)
_MAINT_PAGE_RE = re.compile(r"维护|weihu|under.?construction|系统维护|网站改版", re.I)


def is_unresolved_redirect_url(url: str) -> bool:
    return bool(_UNRESOLVED_LINK_RE.search(url or ""))


def is_low_quality_page(page: dict[str, Any] | None, url: str = "") -> bool:
    """维护页/空页：记 failed，换下一条。"""
    p = page if isinstance(page, dict) else {}
    u = (url or str(p.get("url") or "")).lower()
    title = str(p.get("title") or "")
    text = str(p.get("text") or "")
    if "/weihu" in u or _MAINT_PAGE_RE.search(title) or _MAINT_PAGE_RE.search(u):
        return True
    atts = p.get("attachments") if isinstance(p.get("attachments"), list) else []
    if len(text.strip()) < 40 and not atts:
        # 明确失败标记
        if p.get("ok") is False:
            return True
        if "抱歉" in text or "不存在" in title:
            return True
    return False


def sanitize_evidence_url(url: str) -> str | None:
    """证据层禁止未解析跳转链。"""
    u = (url or "").strip()
    if not u.startswith("http"):
        return None
    if is_unresolved_redirect_url(u):
        return None
    return u


# 进程内页缓存：同 URL 正文/附件可复用（缓存层，不做业务裁判）
_PAGE_CACHE: dict[str, dict[str, Any]] = {}
_PAGE_CACHE_MAX = 64


def cache_page_evidence(url: str, row: dict[str, Any]) -> None:
    u = sanitize_evidence_url(url) or (url or "").strip()
    if not u or not isinstance(row, dict):
        return
    if not (row.get("pageText") or row.get("attachments") or row.get("fetched")):
        return
    _PAGE_CACHE[u] = {
        "title": row.get("title"),
        "url": u,
        "pageText": row.get("pageText"),
        "snippet": row.get("snippet"),
        "attachments": row.get("attachments"),
        "fetched": row.get("fetched"),
        "docNo": row.get("docNo"),
        "date": row.get("date"),
        "sourceType": row.get("sourceType") or "web",
    }
    while len(_PAGE_CACHE) > _PAGE_CACHE_MAX:
        _PAGE_CACHE.pop(next(iter(_PAGE_CACHE)), None)


def hydrate_hit_from_cache(hit: dict[str, Any]) -> dict[str, Any]:
    """搜索命中若缓存已有正文/附件，合并进来。"""
    if not isinstance(hit, dict):
        return hit
    u = sanitize_evidence_url(str(hit.get("url") or ""))
    if not u or u not in _PAGE_CACHE:
        return hit
    cached = _PAGE_CACHE[u]
    out = dict(hit)
    for k in ("pageText", "attachments", "fetched", "docNo", "date"):
        if cached.get(k) and not out.get(k):
            out[k] = cached[k]
    if cached.get("title") and (
        not out.get("title")
        or len(str(cached.get("title"))) > len(str(out.get("title") or ""))
    ):
        out["title"] = cached["title"]
    if cached.get("snippet") and not out.get("snippet"):
        out["snippet"] = cached["snippet"]
    return out


def pick_open_urls_from_hits(state: "AgentState", *, limit: int = 3) -> list[str]:
    """启发式多链选开：soft rank 后优先非壳页；对比题尽量两侧各一。"""
    from app.services.assistant.query_anchors import (
        extract_geo_phrases,
        is_comparison_query,
        looks_like_portal_shell,
    )

    lim = max(1, min(int(limit or 1), 4))
    anchors = extract_query_anchors(state.query)
    pool = rank_hits_soft(state.hits, anchors, state.query) or list(state.hits or [])
    candidates: list[dict[str, Any]] = []
    for h in pool:
        if not isinstance(h, dict):
            continue
        url = str(h.get("url") or "").strip()
        if not url.startswith("http"):
            continue
        if _url_blocked(state, url):
            continue
        if ".pdf" in url.lower():
            continue
        candidates.append(h)
    if not candidates:
        return []
    non_shell = [h for h in candidates if not looks_like_portal_shell(h)]
    ordered = non_shell + [h for h in candidates if looks_like_portal_shell(h)]

    # 对比题：两侧各挑一条实质页（强制双侧 open 的原料）
    if is_comparison_query(state.query):
        geos = extract_geo_phrases(state.query)
        if len(geos) >= 2:
            picked: list[str] = []
            used: set[str] = set()
            for g in geos[:4]:
                stem = g.replace("省", "").replace("市", "").replace("区", "")[:2]
                for h in ordered:
                    url = str(h.get("url") or "").strip()
                    if not url or url in used:
                        continue
                    blob = f"{h.get('title') or ''} {h.get('snippet') or ''} {h.get('pageText') or ''}"
                    if g in blob or (stem and stem in blob):
                        if looks_like_portal_shell(h) and any(
                            not looks_like_portal_shell(x) for x in ordered
                        ):
                            continue
                        picked.append(url)
                        used.add(url)
                        break
            for h in ordered:
                if len(picked) >= lim:
                    break
                url = str(h.get("url") or "").strip()
                if url and url not in used:
                    picked.append(url)
                    used.add(url)
            return picked[:lim]

    out: list[str] = []
    for h in ordered:
        url = str(h.get("url") or "").strip()
        if url and url not in out:
            out.append(url)
        if len(out) >= lim:
            break
    return out


def pick_open_url_from_hits(state: "AgentState") -> str | None:
    """启发式兜底选链：soft rank（已含门户壳降权）后优先非壳页。

    形态降权，不写死业务域名表；LLM planner 仍可自己选 url。
    """
    urls = pick_open_urls_from_hits(state, limit=1)
    return urls[0] if urls else None


def pick_open_url_for_geo(state: "AgentState", geo: str) -> str | None:
    """为对比题某一侧选一条实质页 URL。"""
    from app.services.assistant.query_anchors import looks_like_portal_shell

    g = (geo or "").strip()
    if not g:
        return None
    stem = g.replace("省", "").replace("市", "").replace("区", "").replace("县", "")
    stem = stem[:2] if len(stem) >= 2 else stem
    anchors = extract_query_anchors(state.query)
    pool = rank_hits_soft(state.hits, anchors, state.query) or list(state.hits or [])
    candidates: list[dict[str, Any]] = []
    for h in pool:
        if not isinstance(h, dict):
            continue
        url = str(h.get("url") or "").strip()
        if not url.startswith("http") or _url_blocked(state, url):
            continue
        if ".pdf" in url.lower():
            continue
        blob = f"{h.get('title') or ''} {h.get('snippet') or ''} {h.get('pageText') or ''}"
        if g not in blob and not (stem and stem in blob):
            continue
        candidates.append(h)
    if not candidates:
        return None
    non_shell = [h for h in candidates if not looks_like_portal_shell(h)]
    ordered = non_shell + [h for h in candidates if looks_like_portal_shell(h)]
    return str(ordered[0].get("url") or "").strip() or None


def side_has_substantive_open(state: "AgentState", geo: str) -> bool:
    """该侧是否已有非门户壳且已 fetched 的实质页。"""
    from app.services.assistant.query_anchors import looks_like_portal_shell

    g = (geo or "").strip()
    stem = g.replace("省", "").replace("市", "").replace("区", "").replace("县", "")
    stem = stem[:2] if len(stem) >= 2 else stem
    for e in state.evidence or []:
        if not isinstance(e, dict):
            continue
        if not (e.get("fetched") or e.get("pageText")):
            continue
        url = str(e.get("url") or "")
        if url in (state.failed_urls or []):
            continue
        if looks_like_portal_shell(e):
            continue
        blob = f"{e.get('title') or ''} {e.get('snippet') or ''} {e.get('pageText') or ''}"
        if g in blob or (stem and stem in blob):
            text = str(e.get("pageText") or "")
            if len(text) >= 40 or e.get("attachments"):
                return True
    return False


def filter_answer_cites(
    evidence: list[dict[str, Any]] | None,
    query: str = "",
    *,
    finish_reason: str = "",
) -> list[dict[str, Any]]:
    """enough 时再滤门户壳 / 知乎等噪声 cite；无更好证据时保留以免空引用。"""
    from app.services.assistant.domain_rank import soft_domain_boost
    from app.services.assistant.query_anchors import looks_like_portal_shell

    fr = (finish_reason or "").strip().lower()
    pool = [e for e in (evidence or []) if isinstance(e, dict)]
    if not pool:
        return []
    # 非 enough 也做轻卫生：未解析链已在上游去掉
    noise_hosts = (
        "zhihu.com",
        "zhidao.baidu.",
        "baike.baidu.",
        "tieba.baidu.",
        "sohu.com",
        "sina.com.cn",
        "weixin.qq.",
        "mp.weixin.",
    )

    def _is_noise_host(e: dict[str, Any]) -> bool:
        u = str(e.get("url") or "").lower()
        return any(n in u for n in noise_hosts)

    def _is_shell(e: dict[str, Any]) -> bool:
        return looks_like_portal_shell(e)

    good: list[dict[str, Any]] = []
    weak: list[dict[str, Any]] = []
    for e in pool:
        if _is_noise_host(e) or _is_shell(e):
            weak.append(e)
        else:
            good.append(e)

    # enough：优先只出 good；若 good 空再放回 weak 里域名分最高的少量
    if fr in ("enough", "done", "session_reuse", "max_steps"):
        if good:
            # soft 排序：权威域优先
            good.sort(
                key=lambda e: (
                    soft_domain_boost(str(e.get("url") or "")),
                    1 if e.get("fetched") else 0,
                    1 if e.get("attachments") else 0,
                ),
                reverse=True,
            )
            return good[:10]
        # 全是噪声：仍保留最多 2 条，避免完全无依据
        weak.sort(
            key=lambda e: soft_domain_boost(str(e.get("url") or "")),
            reverse=True,
        )
        return weak[:2]
    # empty：保留原序少量（写作层会诚实未找到）
    return pool[:8]


@dataclass
class ResearchResult:
    evidence: list[dict[str, Any]]
    steps: list[ResearchStep]
    finish_reason: str
    research_block: str


def _url_host_blob(url: str) -> str:
    return (url or "").lower()


def is_authoritative_url(url: str) -> bool:
    u = _url_host_blob(url)
    return any(m in u for m in AUTHORITATIVE_HOST_MARKERS)


def title_looks_like_award_list(title: str) -> bool:
    t = title or ""
    return any(k in t for k in ("获奖名单", "名单公示", "公布", "附件"))


def title_is_year_noise(title: str, query: str) -> bool:
    """只有年份相关、缺核心实体的噪声标题。"""
    t = title or ""
    if any(k in t for k in ("统计公报", "国民经济", "居民收入", "百度百科", "Year in Review", "Wikipedia")):
        return True
    anchors = extract_query_anchors(query)
    # 缺必选实体 → 噪声
    if anchors.required and not hit_passes_anchors(
        {"title": t, "snippet": ""}, anchors, strict=True
    ):
        return True
    phrases = re.findall(r"[\u4e00-\u9fff]{4,}", query or "")
    phrases = [p for p in phrases if p not in ("搜索一下", "帮我查找")]
    if not phrases:
        return False
    return not any(p in t for p in phrases[:4])


def _relevant_evidence(state: AgentState) -> list[dict[str, Any]]:
    """可用证据：soft 排序后过 soft 门槛；拒绝未解析跳转链。"""
    anchors = extract_query_anchors(state.query)
    pool = []
    for e in state.evidence:
        if not isinstance(e, dict):
            continue
        u = sanitize_evidence_url(str(e.get("url") or ""))
        if not u and e.get("pageText"):
            # 允许无 url 但有正文的极少情况
            pool.append(e)
            continue
        if not u:
            continue
        row = dict(e)
        row["url"] = u
        pool.append(row)
    ranked = rank_hits_soft(pool, anchors, state.query)
    if ranked:
        return ranked
    return filter_hits_by_anchors(pool, anchors, strict=False)


def should_stop_success(state: AgentState) -> bool:
    """启发式：是否已有可写的细读证据（供兜底 planner，非业务裁判）。

    真正 enough/empty 优先由 LLM planner / finish judge 决定。
    """
    for e in _relevant_evidence(state):
        url = str(e.get("url") or "")
        title = str(e.get("title") or "")
        text = str(e.get("pageText") or "")
        atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
        if atts and (
            is_authoritative_url(url)
            or title_looks_like_award_list(title)
            or title.startswith("附件")
        ):
            return True
        if e.get("fetched") and atts:
            return True
        if e.get("fetched") and len(text) >= 80:
            return True
    return False


def should_search_again(state: AgentState) -> bool:
    if state.search_count >= 4:
        return False
    if should_stop_success(state):
        return False
    anchors = extract_query_anchors(state.query)
    relevant_hits = rank_hits_soft(state.hits, anchors, state.query)
    if not relevant_hits:
        from app.services.assistant.query_anchors import next_unused_query

        return next_unused_query(state.query, state.prior_queries) is not None
    # 有相关 hit 但从未成功 open
    opened_ok = [u for u in state.opened_urls if u not in state.failed_urls]
    if relevant_hits and not opened_ok:
        return False
    return False


def _soft_relevant_evidence(state: AgentState) -> list[dict[str, Any]]:
    return _relevant_evidence(state)


def _url_blocked(state: AgentState, url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return True
    if u in state.opened_urls or u in state.failed_urls:
        return True
    if is_unresolved_redirect_url(u):
        return True
    return False


def filter_evidence_for_followup(
    followup_query: str,
    prior_evidence: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """会话证据复用：soft rank 相关条目（含 PDF 正文缓存），不写死赛项。"""
    if not prior_evidence:
        return []
    q = (followup_query or "").strip()
    anchors = extract_query_anchors(q)
    pool = [hydrate_hit_from_cache(e) for e in prior_evidence if isinstance(e, dict)]
    # 丢掉未解析跳转
    cleaned = []
    for e in pool:
        u = sanitize_evidence_url(str(e.get("url") or ""))
        if not u and not e.get("pageText"):
            continue
        row = dict(e)
        if u:
            row["url"] = u
        cleaned.append(row)
    ranked = rank_hits_soft(cleaned, anchors, q)
    if ranked:
        ranked.sort(
            key=lambda e: (
                2 if ".pdf" in str(e.get("url") or "").lower() else 0
            )
            + (1 if e.get("attachments") else 0)
            + (1 if e.get("fetched") else 0),
            reverse=True,
        )
        return ranked[:10]
    return filter_hits_by_anchors(cleaned, anchors, strict=False)[:10]


def default_heuristic_planner(
    state: AgentState,
    *,
    max_steps: int,
    max_open: int = 2,
    max_pdf: int = 2,
) -> dict[str, Any]:
    """无 LLM 时的启发式 planner（可测、可作生产兜底）。"""
    from app.services.assistant.url_intent import extract_http_urls, should_skip_keyword_search

    anchors = extract_query_anchors(state.query)
    if state.step_count >= max_steps:
        return {"name": "finish", "arguments": {"reason": "max_steps"}}

    # URL 阅读意图：禁止词典式关键词搜，优先 open 用户给出的链接
    user_urls = extract_http_urls(state.query)
    if user_urls:
        for u in user_urls:
            if u not in state.opened_urls and len(state.opened_urls) < max_open:
                return {"name": "open_url", "arguments": {"url": u}}
        # 已尝试 open：有正文则 enough，否则 empty（不要去搜「告诉」）
        if any(e.get("fetched") for e in state.evidence):
            return {"name": "finish", "arguments": {"reason": "enough"}}
        if should_skip_keyword_search(state.query):
            return {"name": "finish", "arguments": {"reason": "empty"}}

    if should_stop_success(state) and len(state.opened_urls) >= 1:
        # 对比题：一侧够用但另一侧缺失 → 继续搜缺失侧（多 hop 合成）
        from app.services.assistant.query_anchors import (
            comparison_sides_covered,
            extract_geo_phrases,
            is_comparison_query,
            next_unused_query,
        )

        if is_comparison_query(state.query) and state.search_count < 4:
            _cov, missing = comparison_sides_covered(state.query, state.evidence)
            if missing:
                geo = missing[0]
                topic = (anchors.content_phrases or ["技能大赛"])[0]
                year = (anchors.years or [""])[0]
                q2 = " ".join(p for p in (geo, year, topic, "规模", "通知") if p)[:48]
                if q2 and q2 not in state.prior_queries:
                    return {"name": "web_search", "arguments": {"q": q2}}
            # 两侧有 hit 但缺实质 open → 强制双侧实质页 open（可并行）
            opened_ok_n = len([u for u in state.opened_urls if u not in state.failed_urls])
            if opened_ok_n < max_open:
                need_urls: list[str] = []
                for g in extract_geo_phrases(state.query)[:4]:
                    if side_has_substantive_open(state, g):
                        continue
                    u = pick_open_url_for_geo(state, g)
                    if u and u not in need_urls:
                        need_urls.append(u)
                if need_urls:
                    if len(need_urls) == 1:
                        return {"name": "open_url", "arguments": {"url": need_urls[0]}}
                    return {
                        "name": "open_url",
                        "arguments": {"url": need_urls[0], "urls": need_urls[:3]},
                    }
        # 名单类：若有 PDF 附件且未抽过，尝试 fetch_pdf
        if max_pdf > 0 and state.pdf_count < max_pdf:
            for e in _relevant_evidence(state):
                atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
                for a in atts:
                    if not isinstance(a, dict):
                        continue
                    au = str(a.get("url") or "")
                    if ".pdf" in au.lower() and au not in state.opened_urls:
                        from app.services.assistant.pdf_research import clean_pdf_keywords

                        kws = clean_pdf_keywords(
                            list(anchors.content_phrases or [])
                            + list(anchors.content_tokens or [])[:6]
                            + list(anchors.years or [])
                        )
                        return {
                            "name": "fetch_pdf",
                            "arguments": {
                                "url": au,
                                "keywords": kws[:6],
                                "maxPages": 5,
                            },
                        }
        return {"name": "finish", "arguments": {"reason": "enough"}}
    if state.search_count == 0:
        from app.services.assistant.query_anchors import build_search_query_variants
        from app.services.assistant.url_intent import should_skip_keyword_search

        if should_skip_keyword_search(state.query):
            return {"name": "finish", "arguments": {"reason": "empty"}}
        # 首轮多假设并行，避免单句糊搜
        variants = build_search_query_variants(
            state.query, max_n=4, prior_queries=state.prior_queries
        )
        if len(variants) >= 2:
            return {"name": "web_search_batch", "arguments": {"queries": variants[:4]}}
        q = variants[0] if variants else state.query
        return {"name": "web_search", "arguments": {"q": (q[:48] if q else state.query[:48])}}
    relevant = rank_hits_soft(state.hits, anchors, state.query)
    soft = filter_hits_by_anchors(state.hits, anchors, strict=False)
    # 直接 PDF 链接
    if max_pdf > 0 and state.pdf_count < max_pdf:
        for h in relevant or soft:
            url = str(h.get("url") or "")
            if ".pdf" in url.lower() and url not in state.opened_urls:
                from app.services.assistant.pdf_research import clean_pdf_keywords

                kws = clean_pdf_keywords(
                    list(anchors.content_phrases or [])
                    + list(anchors.content_tokens or [])[:6]
                    + list(anchors.years or [])
                )
                return {
                    "name": "fetch_pdf",
                    "arguments": {
                        "url": url,
                        "keywords": kws[:6],
                        "maxPages": 5,
                    },
                }
    # 有 hit 未 open → 启发式选下一批（可并行多开压时延）
    opened_ok_n = len([u for u in state.opened_urls if u not in state.failed_urls])
    if opened_ok_n < max_open:
        from app.services.assistant.query_anchors import (
            extract_geo_phrases,
            is_comparison_query,
        )

        room = max_open - opened_ok_n
        # 对比题强制两侧实质页
        if is_comparison_query(state.query):
            need_urls: list[str] = []
            for g in extract_geo_phrases(state.query)[:4]:
                if side_has_substantive_open(state, g):
                    continue
                u = pick_open_url_for_geo(state, g)
                if u and u not in need_urls:
                    need_urls.append(u)
                if len(need_urls) >= room:
                    break
            if need_urls:
                if len(need_urls) == 1:
                    return {"name": "open_url", "arguments": {"url": need_urls[0]}}
                return {
                    "name": "open_url",
                    "arguments": {"url": need_urls[0], "urls": need_urls[:room]},
                }
        batch_n = min(room, 3 if room >= 2 else 1)
        urls = pick_open_urls_from_hits(state, limit=batch_n)
        if urls:
            if len(urls) == 1:
                return {"name": "open_url", "arguments": {"url": urls[0]}}
            return {"name": "open_url", "arguments": {"url": urls[0], "urls": urls}}
    # 空结果再 hop：换检索式（引擎 failover 在 public_web_search 内完成）
    if should_search_again(state) and opened_ok_n == 0:
        from app.services.assistant.query_anchors import next_unused_query
        from app.services.assistant.public_search import (
            looks_pdf_seeking_query,
            looks_time_sensitive_query,
        )

        q2 = next_unused_query(state.query, state.prior_queries, max_n=8)
        if q2:
            # 时效/PDF 空池：变体上补通知/附件信号
            if looks_pdf_seeking_query(state.query) and "附件" not in q2:
                q2 = (q2 + " 附件").strip()[:48]
            elif looks_time_sensitive_query(state.query) and "通知" not in q2:
                q2 = (q2 + " 通知").strip()[:48]
            return {"name": "web_search", "arguments": {"q": q2[:48]}}
    # 对比题：有证据但缺另一侧 → 再搜
    from app.services.assistant.query_anchors import (
        comparison_sides_covered,
        evidence_covers_distinctive_entities,
        evidence_has_list_substance,
        is_comparison_query,
        is_full_list_demand,
    )

    if is_comparison_query(state.query) and state.search_count < 4:
        _cov, missing = comparison_sides_covered(state.query, state.evidence or state.hits)
        if missing:
            geo = missing[0]
            topic = (anchors.content_phrases or [""])[0] or "技能大赛"
            year = (anchors.years or [""])[0]
            q2 = " ".join(p for p in (geo, year, topic) if p)[:48]
            if q2 and q2 not in (state.prior_queries or []):
                return {"name": "web_search", "arguments": {"q": q2}}
        # 有两侧 hit 但未实质 open → 强制 open
        if opened_ok_n < max_open:
            need_urls = []
            from app.services.assistant.query_anchors import extract_geo_phrases

            for g in extract_geo_phrases(state.query)[:4]:
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
                        "urls": need_urls[: max(1, max_open - opened_ok_n)],
                    },
                }

    def _can_finish_enough() -> bool:
        if not evidence_covers_distinctive_entities(state.query, state.evidence):
            return False
        if is_full_list_demand(state.query) and not evidence_has_list_substance(
            state.evidence, require_enumerable=True
        ):
            return False
        return True

    if should_stop_success(state):
        return {
            "name": "finish",
            "arguments": {"reason": "enough" if _can_finish_enough() else "empty"},
        }
    # 宽松证据够用：院校喜报/转载也可 enough（写作层会标明次级）
    if _soft_relevant_evidence(state) and (
        state.opened_urls or any(e.get("snippet") for e in state.evidence)
    ):
        return {
            "name": "finish",
            "arguments": {"reason": "enough" if _can_finish_enough() else "empty"},
        }
    has_rel = bool(_relevant_evidence(state) or _soft_relevant_evidence(state))
    return {
        "name": "finish",
        "arguments": {
            "reason": "enough" if has_rel and _can_finish_enough() else "empty"
        },
    }


def _host_of(url: str) -> str:
    try:
        from urllib.parse import urlparse

        h = urlparse(url or "").netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def build_url_read_research_block(query: str, evidence: list[dict[str, Any]]) -> str:
    """用户指定 URL 阅读：直接给出抓取正文，禁止用搜索噪声冒充。"""
    lines = [
        "## 检索结果（用户指定链接，已直抓正文）",
        f"用户问题：{(query or '')[:200]}",
        "",
    ]
    for i, e in enumerate(evidence[:5], 1):
        title = str(e.get("title") or "网页")
        url = str(e.get("url") or "")
        lines.append(f"{i}. [web] {title}")
        if url:
            lines.append(f"   链接：{url}")
        body = str(e.get("pageText") or e.get("snippet") or "").strip()
        if body:
            if len(body) > 1600:
                body = body[:1599] + "…"
            lines.append(f"   正文摘录：{body}")
        lines.append("")
    lines.append(
        "写作要求：根据正文摘录准确说明页面讲什么；不要猜测无关政策；"
        "若摘录不足请说明局限；禁止引用未抓取到的内容。\n"
    )
    return "\n".join(lines)


def build_multi_source_notes(evidence: list[dict[str, Any]] | None) -> str:
    """多源对照提示：列出不同域名，冲突时并列表述。"""
    if not evidence:
        return ""
    hosts: list[str] = []
    for e in evidence:
        if not isinstance(e, dict):
            continue
        h = _host_of(str(e.get("url") or ""))
        if h and h not in hosts:
            hosts.append(h)
    if len(hosts) < 2:
        return ""
    return (
        "多源对照：本轮命中域名包括 "
        + "、".join(hosts[:6])
        + "。若二手转载与官方表述不一致，以政府/教育主管部门域名（如 .gov.cn）为准，并列表说明差异，勿只采信单一媒体。"
    )


def _honest_empty_research_block(
    query: str,
    *,
    weak_hits: list[dict[str, Any]] | None = None,
) -> str:
    """无相关证据：强制写作层输出「未找到」，可附带弱命中供说明但不许凑数。"""
    lines = [
        "## 检索结果（本轮判定：未找到直接相关公开结果）",
        f"用户问题：{(query or '')[:200]}",
        "",
        "（本轮联网检索未命中与用户问题核心实体+主题足够相关的公开网页。）",
        "",
        "写作硬约束（必须遵守）：",
        "1) 必须明确写「未检索到直接相关公开结果」或「未找到」；",
        "2) 禁止用门户首页、考试院首页、跑题页硬凑答案或编造名单/数字；",
        "3) 可建议换关键词或到主管部门官网核验；",
        "4) 系统已执行联网检索，禁止声称没有联网能力。",
    ]
    weak = [e for e in (weak_hits or []) if isinstance(e, dict)][:5]
    if weak:
        lines.append("")
        lines.append("以下为弱相关/不采用命中（仅供说明边界，**不得**当作答案依据）：")
        for i, e in enumerate(weak, 1):
            title = str(e.get("title") or "来源")[:70]
            url = str(e.get("url") or "")[:100]
            lines.append(f"{i}. {title}" + (f" — {url}" if url else ""))
    lines.append("")
    return "\n".join(lines)


def build_research_block(query: str, evidence: list[dict[str, Any]], finish_reason: str = "") -> str:
    """装配供模型引用的 researchBlock。

    Grok 主路径：soft 相关排序 + offtopic 护栏；禁止未解析跳转链。
    finish_reason=empty → 强制「未找到」写作块（拒凑数）。
    """
    fr = (finish_reason or "").strip().lower()
    anchors = extract_query_anchors(query)
    cleaned: list[dict[str, Any]] = []
    for e in evidence or []:
        if not isinstance(e, dict):
            continue
        u = sanitize_evidence_url(str(e.get("url") or ""))
        if not u:
            # 无合法 url 的丢弃（除非纯正文且已 fetch）
            if not (e.get("fetched") and e.get("pageText")):
                continue
            u = ""
        row = dict(e)
        if u:
            row["url"] = u
        cleaned.append(row)
    ranked = rank_hits_soft(cleaned, anchors, query)
    strict_ev = filter_hits_by_anchors(cleaned, anchors, strict=True)
    soft_ev = filter_hits_by_anchors(cleaned, anchors, strict=False)
    degraded = False
    if strict_ev:
        evidence = rank_hits_soft(strict_ev, anchors, query) or strict_ev
    elif ranked:
        evidence = ranked
        degraded = not any(is_authoritative_url(str(e.get("url") or "")) for e in ranked[:3])
    elif soft_ev:
        evidence = soft_ev
        degraded = True
    else:
        evidence = []

    # 收尾 empty：即使有弱命中，也强制「未找到」（拒凑数）
    if fr == "empty":
        return _honest_empty_research_block(query, weak_hits=cleaned[:5] or evidence)

    if not evidence:
        return _honest_empty_research_block(query)

    if degraded:
        lines = [
            "## 检索结果（联网·次级/非权威优先源，请标明边界）",
            f"用户问题：{query[:200]}",
            "",
            "说明：以下来源相关度尚可，但未必是主管部门完整原文；"
            "写作时标明来源层级，勿把次级来源写成唯一权威结论。",
            "",
        ]
    else:
        lines = [
            "## 检索结果（联网，请优先引用，勿编造链接）",
            f"用户问题：{query[:200]}",
            "",
        ]
    multi = build_multi_source_notes(evidence)
    if multi:
        lines.append(multi)
        lines.append("")
    for i, e in enumerate(evidence[:10], 1):
        st = str(e.get("sourceType") or "web")
        title = str(e.get("title") or "来源")
        url = str(e.get("url") or "").strip()
        lines.append(f"{i}. [{st}] {title}")
        if url:
            lines.append(f"   链接：{url}")
        if e.get("docNo"):
            lines.append(f"   文号：{e.get('docNo')}")
        if e.get("date"):
            lines.append(f"   日期：{e.get('date')}")
        body = str(e.get("pageText") or e.get("snippet") or "").strip()
        if body:
            if len(body) > 900:
                body = body[:899] + "…"
            lines.append(f"   摘录：{body}")
        kh = e.get("keywordHits") if isinstance(e.get("keywordHits"), dict) else None
        if kh:
            hit_keys = [k for k, v in kh.items() if v]
            miss_keys = [k for k, v in kh.items() if not v]
            if hit_keys:
                lines.append(f"   PDF关键词命中：{', '.join(hit_keys[:8])}")
            if miss_keys:
                lines.append(f"   PDF关键词未命中：{', '.join(miss_keys[:8])}")
        atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
        if atts:
            lines.append("   可下载附件（完整 URL，须用 Markdown 链接写出，禁止只说「见附件」）：")
            for a in atts[:10]:
                if not isinstance(a, dict):
                    continue
                at = str(a.get("title") or "附件")
                au = str(a.get("url") or "").strip()
                if not au:
                    continue
                lines.append(f"   - [{at}]({au})")
        lines.append("")

    lines.append(
        "写作要求（诚实优先）："
        "1) 只依据上方摘录与链接作答；摘录未覆盖的内容不要编。"
        "2) 若证据与用户问题核心实体/主题明显无关（门户首页、跑题页），"
        "必须明确说明「未检索到直接相关公开结果 / 未找到」，禁止用无关页面硬凑答案。"
        "3) 有附件则给出可点击 Markdown 链接，并说明本对话不上传文件。"
        "4) 多源冲突时并列表述并标明更权威来源。"
        "5) 系统已执行联网检索，禁止声称没有联网能力。\n"
    )
    return "\n".join(lines)


def run_research_from_seed_hits(
    query: str,
    hits: list[dict[str, Any]] | None,
    *,
    open_fn: OpenFn | None = None,
    planner_fn: PlannerFn | None = None,
    max_steps: int = 6,
    max_open: int = 2,
) -> ResearchResult:
    """用 Java 首轮检索 hits 作为 seed，再 open 加深（AI 侧无搜索引擎时）。"""
    seed = [h for h in (hits or []) if isinstance(h, dict)]
    used = {"seed": False}

    def search_fn(q: str) -> list[dict[str, Any]]:
        if not used["seed"] and seed:
            used["seed"] = True
            return list(seed)
        return []

    if open_fn is None:
        from app.services.assistant.web_research import fetch_page

        def open_fn(url: str) -> dict[str, Any]:  # type: ignore[no-redef]
            return fetch_page(url, max_chars=1600)

    return run_research_agent(
        query,
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=planner_fn,
        max_steps=max_steps,
        max_open=max_open,
        budget=ResearchBudget(max_steps=max_steps, max_open=max_open),
        use_llm_planner=planner_fn is None,
    )


def apply_research_agent_to_payload(
    payload: dict[str, Any],
    *,
    open_fn: OpenFn | None = None,
    search_fn: SearchFn | None = None,
    max_steps: int = 8,
    max_open: int = 2,
) -> dict[str, Any]:
    """Grok 式主路径：模型 tool loop 完成联网研究，再写回 researchBlock。

    deep_search / useResearchAgent 时启用。Java 不再前置关键词流水线。
    """
    if not isinstance(payload, dict):
        return payload
    flag = payload.get("useResearchAgent")
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    mode = str(payload.get("mode") or payload.get("researchMode") or "").strip()
    if flag is False or options.get("useResearchAgent") is False:
        return payload
    # agent 主路径：deep_search / 显式开启 / researchAgentPrimary
    enabled = bool(
        flag
        or options.get("useResearchAgent")
        or payload.get("researchAgentPrimary")
        or mode == "deep_search"
    )
    if not enabled:
        return payload

    query = ""
    for m in reversed(payload.get("messages") or []):
        if isinstance(m, dict) and m.get("role") == "user":
            query = str(m.get("content") or "")
            break
    if not query:
        query = str(payload.get("query") or "检索")

    # 会话证据复用：相关则直接用；或注入 agent 作 seed（PDF/名单一致性）
    session_ev = options.get("sessionResearchEvidence") or payload.get("sessionResearchEvidence")
    seed_ev: list[dict[str, Any]] | None = None
    if isinstance(session_ev, list) and session_ev:
        from app.services.assistant.url_intent import extract_http_urls

        if not extract_http_urls(query):
            filtered = filter_evidence_for_followup(query, session_ev)
            # 短追问且证据够 → 直接复用
            if filtered and len(query) < 100 and should_stop_success(
                AgentState(query=query, evidence=list(filtered), hits=list(filtered))
            ):
                out = dict(payload)
                out["researchBlock"] = build_research_block(query, filtered, "session_reuse")
                out["researchCitations"] = filtered
                out["researchAgentFinishReason"] = "session_reuse"
                out["researchAgentSteps"] = [
                    {
                        "stepNo": 1,
                        "tool": "session_filter",
                        "summary": f"reuse evidence n={len(filtered)}",
                        "args": {},
                    }
                ]
                out["sessionResearchEvidence"] = filtered
                return out
            if filtered:
                seed_ev = filtered
            else:
                seed_ev = [e for e in session_ev if isinstance(e, dict)][:12]

    budget = ResearchBudget.from_payload(payload)
    budget.max_steps = max(budget.max_steps, max_steps or 8)
    budget.max_open = max_open or budget.max_open
    # 对比题略放宽 open 预算（路径能力，不改判定逻辑）
    try:
        from app.services.assistant.query_anchors import is_comparison_query

        if is_comparison_query(query):
            budget.max_open = max(budget.max_open, 3)
            budget.max_steps = max(budget.max_steps, 10)
    except Exception:
        pass
    use_llm = options.get("useLlmPlanner")
    if use_llm is None:
        use_llm = payload.get("useLlmPlanner")
    if use_llm is None:
        use_llm = True
    use_llm = bool(use_llm)

    # 默认工具：真实公网检索 + 抓页（Grok 同构）
    if search_fn is None:
        from app.services.assistant.public_search import public_web_search

        search_fn = public_web_search
    if open_fn is None:
        from app.services.assistant.web_research import fetch_page

        def open_fn(url: str) -> dict[str, Any]:  # type: ignore[no-redef]
            return fetch_page(url, max_chars=2400)

    result = run_research_agent(
        query,
        search_fn=search_fn,
        open_fn=open_fn,
        max_steps=budget.max_steps,
        max_open=budget.max_open,
        budget=budget,
        use_llm_planner=use_llm,
        seed_evidence=seed_ev,
    )

    out = dict(payload)
    out["researchBlock"] = result.research_block
    out["researchCitations"] = result.evidence
    out["researchAgentSteps"] = [
        {
            "stepNo": s.step_no,
            "tool": s.tool,
            "summary": s.result_summary,
            "args": s.args,
            "thought": (s.result_summary.split("|", 1)[0].replace("think:", "").strip()
                        if s.result_summary.startswith("think:") else ""),
        }
        for s in result.steps
    ]
    out["researchAgentFinishReason"] = result.finish_reason
    out["sessionResearchEvidence"] = result.evidence
    try:
        out["researchMetrics"] = summarize_research_metrics(
            query=query,
            evidence=result.evidence,
            finish_reason=result.finish_reason,
            steps=result.steps,
        )
    except Exception:
        pass
    return out


def run_research_agent(
    query: str,
    *,
    search_fn: SearchFn,
    open_fn: OpenFn,
    fetch_pdf_fn: FetchPdfFn | None = None,
    planner_fn: PlannerFn | None = None,
    max_steps: int = 8,
    max_open: int = 2,
    budget: ResearchBudget | None = None,
    use_llm_planner: bool = False,
    seed_evidence: list[dict[str, Any]] | None = None,
) -> ResearchResult:
    """执行 tool loop。

    use_llm_planner=True：LLM 先 thought + web_search_batch 多假设再迭代（失败回落启发式）。
    seed_evidence：会话/缓存注入的已抓证据（PDF/名单可复用）。
    单测默认 False；生产 apply_research_agent_to_payload 会打开。
    """
    q = (query or "").strip() or "检索"
    b = budget or ResearchBudget(max_steps=max_steps, max_open=max_open)
    max_steps = max(1, min(int(b.max_steps or max_steps or 8), 12))
    max_open = max(1, min(int(b.max_open or max_open or 2), 5))
    max_pdf = max(0, min(int(b.max_pdf if b.max_pdf is not None else 2), 4))
    state = AgentState(query=q)
    # 注入会话/缓存证据
    if seed_evidence:
        for e in seed_evidence:
            if not isinstance(e, dict):
                continue
            row = hydrate_hit_from_cache(dict(e))
            u = sanitize_evidence_url(str(row.get("url") or ""))
            if u:
                row["url"] = u
                state.hits.append(row)
                state.evidence.append(row)
                if row.get("fetched") or row.get("pageText") or row.get("attachments"):
                    cache_page_evidence(u, row)

    if fetch_pdf_fn is None and max_pdf > 0:
        from app.services.assistant.pdf_research import fetch_pdf_url

        def fetch_pdf_fn(url: str, **kwargs: Any) -> dict[str, Any]:  # type: ignore[no-redef]
            return fetch_pdf_url(url, timeout=min(12.0, b.timeout_sec), **kwargs)

    def _heuristic(s: AgentState) -> dict[str, Any]:
        return default_heuristic_planner(
            s, max_steps=max_steps, max_open=max_open, max_pdf=max_pdf
        )

    def _planner(s: AgentState) -> dict[str, Any]:
        if planner_fn is not None:
            return planner_fn(s)
        if use_llm_planner:
            try:
                from app.services.assistant.research_planner import make_llm_planner

                return make_llm_planner(
                    max_steps=max_steps,
                    max_open=max_open,
                    max_pdf=max_pdf,
                    fallback=_heuristic,
                )(s)
            except Exception:
                return _heuristic(s)
        return _heuristic(s)

    for _ in range(max_steps + 1):
        if state.finish_reason:
            break
        if state.step_count >= max_steps:
            state.finish_reason = "max_steps"
            break

        raw_plan = _planner(state)
        if isinstance(raw_plan, dict) and raw_plan.get("thought"):
            state.last_thought = str(raw_plan.get("thought") or "")
        call = normalize_tool_call(raw_plan)
        name = call.get("name") or ""
        args = call.get("arguments") or {}

        # 非法 tool：协议层拒绝，改写为 open/finish（判断交给启发式/后续 LLM）
        if not name or call.get("invalid_tool"):
            if should_stop_success(state):
                name, args = "finish", {"reason": "enough"}
            else:
                alt = pick_open_url_from_hits(state)
                if alt:
                    name, args = "open_url", {"url": alt}
                else:
                    name, args = "finish", {
                        "reason": "enough" if _relevant_evidence(state) else "empty"
                    }
            call = {"name": name, "arguments": args}

        # tool 卫生：失败/未解析 URL；门户壳若有更优 hit 则改写 open
        # 并行 open：预算允许时扩成 urls[] 一批打开（压串行时延）
        if name == "open_url":
            from app.services.assistant.query_anchors import (
                extract_geo_phrases,
                is_comparison_query,
                looks_like_portal_shell,
            )

            url = str(args.get("url") or "").strip()
            if _url_blocked(state, url):
                alt = pick_open_url_from_hits(state)
                if alt:
                    args = {**args, "url": alt}
                    call = {**call, "arguments": args}
                    url = alt
                else:
                    name = "finish"
                    args = {
                        "reason": "enough" if should_stop_success(state) else "empty"
                    }
                    call = {"name": "finish", "arguments": args}
            if name == "open_url":
                chosen = next(
                    (
                        h
                        for h in (state.hits or [])
                        if isinstance(h, dict) and str(h.get("url") or "").strip() == url
                    ),
                    {"title": "", "url": url, "snippet": ""},
                )
                if looks_like_portal_shell(chosen):
                    alt = pick_open_url_from_hits(state)
                    if alt and alt != url:
                        alt_hit = next(
                            (
                                h
                                for h in (state.hits or [])
                                if isinstance(h, dict)
                                and str(h.get("url") or "").strip() == alt
                            ),
                            None,
                        )
                        if alt_hit is None or not looks_like_portal_shell(alt_hit):
                            args = {**args, "url": alt}
                            call = {**call, "name": "open_url", "arguments": args}
                            url = alt
                # 扩并行 open：对比双侧 / 预算剩余
                opened_ok_n = len(
                    [u for u in state.opened_urls if u not in state.failed_urls]
                )
                room = max(0, max_open - opened_ok_n)
                if room >= 2:
                    batch_urls: list[str] = []
                    if url and not _url_blocked(state, url):
                        batch_urls.append(url)
                    if is_comparison_query(state.query):
                        for g in extract_geo_phrases(state.query)[:4]:
                            if side_has_substantive_open(state, g):
                                continue
                            u = pick_open_url_for_geo(state, g)
                            if u and u not in batch_urls and not _url_blocked(state, u):
                                batch_urls.append(u)
                            if len(batch_urls) >= room:
                                break
                    if len(batch_urls) < 2:
                        for u in pick_open_urls_from_hits(state, limit=room):
                            if u not in batch_urls and not _url_blocked(state, u):
                                batch_urls.append(u)
                            if len(batch_urls) >= room:
                                break
                    if len(batch_urls) >= 2:
                        args = {
                            **args,
                            "url": batch_urls[0],
                            "urls": batch_urls[: min(3, room)],
                        }
                        call = {**call, "name": "open_url", "arguments": args}

        # 若 planner 在 max_steps 边界仍不 finish，强制收尾
        if state.step_count >= max_steps and name != "finish":
            state.finish_reason = "max_steps"
            break

        tr = execute_tool(
            call,
            search_fn=search_fn,
            open_fn=open_fn,
            fetch_pdf_fn=fetch_pdf_fn,
        )
        # 非法 tool 不推进状态机（已改写则 ok）
        if tr.error == "unknown_tool":
            state.step_count += 1
            state.steps.append(
                ResearchStep(
                    step_no=state.step_count,
                    tool=tr.name,
                    args=dict(args),
                    result_summary=tr.summary,
                )
            )
            continue

        state.step_count += 1
        summary = tr.summary
        if state.last_thought:
            summary = f"think:{state.last_thought[:60]} | {summary}"
        state.steps.append(
            ResearchStep(
                step_no=state.step_count,
                tool=name or tr.name,
                args=dict(args),
                result_summary=summary,
            )
        )

        if tr.name == "finish" and tr.ok:
            state.finish_reason = str(tr.data.get("reason") or "done")
            break

        if name == "fetch_pdf":
            state.pdf_count += 1
            pdf = tr.data.get("pdf") if tr.ok else {}
            if isinstance(pdf, dict) and tr.ok:
                url = str(tr.data.get("url") or pdf.get("url") or "")
                if url:
                    state.opened_urls.append(url)
                # 继承同 URL 搜索标题，避免 PDF 条被锚点滤掉
                parent_title = ""
                for e in state.evidence:
                    if str(e.get("url") or "") == url:
                        parent_title = str(e.get("title") or "")
                        e["pageText"] = str(pdf.get("text") or e.get("pageText") or "")[:1200]
                        e["fetched"] = True
                        e["keywordHits"] = pdf.get("keywordHits") or {}
                        e["snippet"] = (
                            f"{parent_title} PDF浅抽 pages={pdf.get('pages')} "
                            f"kw={pdf.get('keywordHits')}"
                        )[:220]
                        break
                if not parent_title:
                    state.evidence.append(
                        {
                            "sourceType": "web",
                            "title": f"PDF · {url.rsplit('/', 1)[-1] if url else 'document'}",
                            "url": url,
                            "pageText": str(pdf.get("text") or "")[:1200],
                            "snippet": (
                                f"{state.query[:40]} PDF浅抽 pages={pdf.get('pages')} "
                                f"engine={pdf.get('engine')} kw={pdf.get('keywordHits')}"
                            )[:220],
                            "fetched": True,
                            "keywordHits": pdf.get("keywordHits") or {},
                        }
                    )
                # 有 PDF 正文时扩展 pageText 上限，方便名单摘录
                if pdf.get("text"):
                    for e in state.evidence:
                        if str(e.get("url") or "") == url:
                            e["pageText"] = str(pdf.get("text") or "")[:3500]
                            e["snippet"] = (
                                f"{e.get('title') or ''} PDF浅抽 pages={pdf.get('pages')} "
                                f"chars={pdf.get('chars')} engine={pdf.get('engine')}"
                            )[:220]
                            cache_page_evidence(url, e)
                            break
                elif url:
                    for e in state.evidence:
                        if str(e.get("url") or "") == url:
                            cache_page_evidence(url, e)
                            break

        if name in ("web_search", "web_search_batch") and tr.ok:
            state.search_count += 1
            if name == "web_search":
                qq = str(tr.data.get("query") or "")
                if qq and qq not in state.prior_queries:
                    state.prior_queries.append(qq)
            else:
                for qq in tr.data.get("queries") or []:
                    s = str(qq or "")
                    if s and s not in state.prior_queries:
                        state.prior_queries.append(s)
            raw_hits = [h for h in (tr.data.get("hits") or []) if isinstance(h, dict)]
            # 丢掉未解析跳转链；合并进程缓存正文/附件
            raw_hits = [
                hydrate_hit_from_cache(h)
                for h in raw_hits
                if sanitize_evidence_url(str(h.get("url") or ""))
            ]
            anchors = extract_query_anchors(state.query)
            # Grok 主路径：soft rank；单地理仍挡错省（rank 内）
            hits = rank_hits_soft(raw_hits, anchors, state.query)
            if not hits and len(anchors.required) != 1:
                hits = filter_hits_by_anchors(raw_hits, anchors, strict=False)
            # 单地理主题问：soft 空时再用 strict 兜底
            if not hits and len(anchors.required) == 1:
                hits = filter_hits_by_anchors(raw_hits, anchors, strict=True)
            hits = sort_hits_by_soft_rank(hits)
            # batch/多轮与已有 hits 合并去重
            if state.hits:
                seen = {str(h.get("url") or h.get("title") or "") for h in state.hits}
                merged = list(state.hits)
                for h in hits:
                    key = str(h.get("url") or h.get("title") or "")
                    if key and key not in seen:
                        seen.add(key)
                        merged.append(h)
                hits = rank_hits_soft(merged, anchors, state.query) or sort_hits_by_soft_rank(merged)
            state.hits = list(hits)
            for h in hits:
                item = dict(h)
                item.setdefault("sourceType", "web")
                url_k = sanitize_evidence_url(str(item.get("url") or ""))
                if not url_k:
                    continue
                item["url"] = url_k
                if any(str(e.get("url") or "") == url_k for e in state.evidence):
                    continue
                state.evidence.append(item)
            # 空结果 → 标记，下一轮启发式会换检索式再 hop（引擎 failover 已在 search 内）
            if not hits and state.search_count < 3:
                state.last_thought = (state.last_thought or "") + "|empty_search_rehop"

        if name == "open_url":
            # 兼容单开 + 并行 batch（pages[]）
            page_items: list[tuple[str, dict[str, Any], bool]] = []
            multi = tr.data.get("pages") if isinstance(tr.data.get("pages"), list) else None
            if multi and len(multi) > 1:
                for item in multi:
                    if not isinstance(item, dict):
                        continue
                    u = str(item.get("url") or "").strip()
                    p = item.get("page") if isinstance(item.get("page"), dict) else {}
                    ok_i = bool(p.get("ok", True)) and not is_low_quality_page(p, u)
                    page_items.append((u, p, ok_i))
            else:
                page = tr.data.get("page") or {} if tr.ok else {}
                url = str(
                    tr.data.get("url")
                    or (page.get("url") if isinstance(page, dict) else "")
                    or args.get("url")
                    or ""
                )
                ok_i = bool(tr.ok) and isinstance(page, dict) and not is_low_quality_page(
                    page if isinstance(page, dict) else {}, url
                )
                page_items.append((url, page if isinstance(page, dict) else {}, ok_i))

            for url, page, ok_i in page_items:
                if not url:
                    continue
                if url not in state.opened_urls:
                    state.opened_urls.append(url)
                if not ok_i:
                    if url not in state.failed_urls:
                        state.failed_urls.append(url)
                    continue
                atts = page.get("attachments") if isinstance(page.get("attachments"), list) else []
                updated = False
                parent_keep_title = ""
                for e in state.evidence:
                    if str(e.get("url") or "") == url:
                        e["pageText"] = page.get("text") or e.get("pageText")
                        e["fetched"] = True
                        old_title = str(e.get("title") or "")
                        new_title = str(page.get("title") or "")
                        if new_title and len(new_title) > len(old_title):
                            e["title"] = new_title
                        parent_keep_title = str(e.get("title") or new_title or old_title)
                        if old_title and old_title not in str(e.get("snippet") or ""):
                            e["snippet"] = (str(e.get("snippet") or "") + " " + old_title).strip()
                        if atts:
                            e["attachments"] = atts
                        if page.get("docNo"):
                            e["docNo"] = page.get("docNo")
                        if page.get("date"):
                            e["date"] = page.get("date")
                        updated = True
                        break
                if not updated:
                    parent_keep_title = str(page.get("title") or url)
                    row = {
                        "sourceType": "web",
                        "title": parent_keep_title,
                        "url": url,
                        "pageText": page.get("text") or "",
                        "snippet": (page.get("text") or "")[:220],
                        "fetched": True,
                        "attachments": atts,
                    }
                    if page.get("docNo"):
                        row["docNo"] = page.get("docNo")
                    if page.get("date"):
                        row["date"] = page.get("date")
                    state.evidence.append(row)
                for e in state.evidence:
                    if str(e.get("url") or "") == url:
                        cache_page_evidence(url, e)
                        break
                for a in atts:
                    if not isinstance(a, dict):
                        continue
                    au = str(a.get("url") or "").strip()
                    if not au or is_unresolved_redirect_url(au):
                        continue
                    if any(str(e.get("url") or "") == au for e in state.evidence):
                        continue
                    state.evidence.append(
                        {
                            "sourceType": "web",
                            "title": f"附件 · {a.get('title') or '下载'}",
                            "url": au,
                            "snippet": f"官网附件（本对话不上传文件）；来源页：{parent_keep_title}",
                        }
                    )

    if not state.finish_reason:
        state.finish_reason = "max_steps" if state.step_count >= max_steps else "done"

    # 出口再滤一遍：绝不把错省/全国噪声交给模型当依据
    # URL 阅读意图：只保留用户链接的抓取结果，不做主题锚点误杀
    from app.services.assistant.url_intent import extract_http_urls, should_skip_keyword_search

    # LLM finish judge：enough/empty 由模型观察证据决定（失败则保留 planner 原判定）
    if (
        not should_skip_keyword_search(q)
        and use_llm_planner
        and state.finish_reason in ("enough", "empty", "done", "max_steps")
    ):
        try:
            from app.services.assistant.research_planner import llm_finish_judge

            judged = llm_finish_judge(q, state.evidence, state.finish_reason or "")
            if judged in ("enough", "empty"):
                state.finish_reason = judged
        except Exception:
            pass

    # 薄卫生（形态级，非业务白名单 / 非答案硬编码）：
    # 1) 名单通知+PDF 且问名单 → empty 纠为 enough（与 judge 提示一致）
    # 2) 专名 0 命中 → 不得 enough
    # 3) 「全部/逐队名单」需求但无名单正文/PDF → 不得 enough（C19）
    if not should_skip_keyword_search(q):
        try:
            from app.services.assistant.query_anchors import (
                evidence_covers_distinctive_entities,
                evidence_has_list_notice_with_pdf,
                evidence_has_list_substance,
                is_full_list_demand,
            )

            fr = (state.finish_reason or "").strip().lower()
            list_q = bool(re.search(r"名单|获奖|公示|金奖|银奖", q))
            if (
                fr in ("empty", "done", "max_steps")
                and list_q
                and evidence_has_list_notice_with_pdf(state.evidence)
            ):
                state.finish_reason = "enough"
                fr = "enough"
            if fr in ("enough", "done", "max_steps"):
                if not evidence_covers_distinctive_entities(q, state.evidence):
                    state.finish_reason = "empty"
                elif is_full_list_demand(q) and not evidence_has_list_substance(
                    state.evidence, require_enumerable=True
                ):
                    state.finish_reason = "empty"
        except Exception:
            pass

    # 证据只做 URL 消毒 + soft rank，不做业务硬杀
    clean_pool = []
    for e in state.evidence:
        if not isinstance(e, dict):
            continue
        u = sanitize_evidence_url(str(e.get("url") or ""))
        if not u and not e.get("pageText"):
            continue
        row = dict(e)
        if u:
            row["url"] = u
        clean_pool.append(row)
    state.evidence = clean_pool

    if should_skip_keyword_search(q):
        urls = extract_http_urls(q)
        clean_evidence = []
        for e in state.evidence:
            if not isinstance(e, dict):
                continue
            eu = str(e.get("url") or "")
            if any(u in eu or eu in u for u in urls) or (
                e.get("fetched") and eu.startswith("http")
            ):
                clean_evidence.append(e)
        if not clean_evidence and state.finish_reason == "enough":
            state.finish_reason = "empty"
        # URL 专用 block：不过滤主题短语
        if clean_evidence:
            block = build_url_read_research_block(q, clean_evidence)
        else:
            block = (
                "## 检索结果\n"
                "（本轮未能抓取用户给出的网页正文。可能原因：站点反爬、需登录、或网络不可达。）\n"
                "写作要求：如实说明未读到正文；可建议用户直接打开链接；禁止编造页面内容；"
                "禁止用无关词典/百科结果冒充该链接内容。\n"
            )
    else:
        clean_evidence = _relevant_evidence(state)
        clean_evidence = sort_hits_by_soft_rank(clean_evidence)
        if not clean_evidence and state.finish_reason == "enough":
            # 规划器误标 enough 但无可用证据 → empty（拒凑数）
            # max_steps/done 保留原因，写作块仍走无证据诚实模板
            state.finish_reason = "empty"
        # enough 时再滤门户壳/知乎等 cite 噪声
        if (state.finish_reason or "").lower() in ("enough", "done", "max_steps"):
            clean_evidence = filter_answer_cites(
                clean_evidence, q, finish_reason=state.finish_reason or "enough"
            )
        # 对比题写作：有证据时不要因 finish empty 误杀（上方已尽量纠偏）
        # 注意：finish_reason=empty 时不再因 soft 证据翻回 enough（LLM 裁判优先；对比例外已处理）
        block = build_research_block(q, clean_evidence, state.finish_reason or "")
    try:
        metrics = summarize_research_metrics(
            query=q,
            evidence=clean_evidence,
            finish_reason=state.finish_reason or "",
            steps=state.steps,
        )
        log_research_metrics(metrics)
    except Exception:
        pass
    return ResearchResult(
        evidence=list(clean_evidence),
        steps=list(state.steps),
        finish_reason=state.finish_reason,
        research_block=block,
    )
