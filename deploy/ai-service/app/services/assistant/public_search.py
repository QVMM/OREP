"""公开网页检索（供 Grok 式 Research Agent 作 search 工具）。

与业务词表无关：只负责「query → 标题/摘要/URL 列表」。
引擎顺序：百度（国内召回主源）→ 360 → Bing CN；合并去重后按标题相关度粗排。
"""
from __future__ import annotations

import logging
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

# 跳转解析缓存：降时延、避免重复 GET baidu link
_RESOLVE_CACHE: OrderedDict[str, tuple[float, str]] = OrderedDict()
_RESOLVE_LOCK = threading.Lock()
_RESOLVE_TTL_SEC = 3600.0
_RESOLVE_CACHE_MAX = 512
_RESOLVE_TIMEOUT = 2.2

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# 口语尾巴：进检索引擎前剥掉，避免「是什么」拖垮召回
_ORAL_TAIL = re.compile(
    r"(请基于官方来源回答.*$|若搜不到请如实说明.*$|请如实说明.*$|"
    r"是什么[？?]?$|怎么样[？?]?$|如何[？?]?$|有哪些[？?]?$|"
    r"帮我(搜|查|找).*$|谢谢[。.!！]?$)"
)
_ORAL_MID = re.compile(
    r"请基于官方来源回答|若搜不到请如实说明|请如实说明|帮我搜一搜|帮我查找|"
    r"帮我搜|搜一下|查一下|网上有没有|有没有|能不能|可不可以|请问|谢谢"
)


def normalize_search_query(query: str) -> str:
    """剥口语、压空白，保留实体与主题。"""
    q = (query or "").strip()
    if not q:
        return ""
    # 去掉 URL（URL 阅读不走关键词搜）
    q = re.sub(r"https?://\S+", " ", q)
    q = _ORAL_MID.sub(" ", q)
    q = _ORAL_TAIL.sub("", q)
    # 句中/句尾疑问尾巴
    q = re.sub(r"(是什么|怎么样|有哪些|如何)[？?！!。.\s]*", " ", q)
    q = re.sub(r"[?？!！。，,]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q[:48]


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<script[\s\S]*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style[\s\S]*?</style>", " ", s)
    s = re.sub(r"<em>|</em>", "", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _get(url: str, *, timeout: float = 12.0, referer: str | None = None) -> str:
    headers = {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        "Accept-Encoding": "identity",
        "Connection": "close",
    }
    if referer:
        headers["Referer"] = referer
    req = urlrequest.Request(url, headers=headers, method="GET")
    with urlrequest.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        for enc in ("utf-8", "gb18030", "gbk"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", "ignore")


def _cache_get(url: str) -> str | None:
    now = time.time()
    with _RESOLVE_LOCK:
        item = _RESOLVE_CACHE.get(url)
        if not item:
            return None
        ts, final = item
        if now - ts > _RESOLVE_TTL_SEC:
            _RESOLVE_CACHE.pop(url, None)
            return None
        # LRU touch
        _RESOLVE_CACHE.move_to_end(url)
        return final


def _cache_put(url: str, final: str) -> None:
    with _RESOLVE_LOCK:
        _RESOLVE_CACHE[url] = (time.time(), final)
        _RESOLVE_CACHE.move_to_end(url)
        while len(_RESOLVE_CACHE) > _RESOLVE_CACHE_MAX:
            _RESOLVE_CACHE.popitem(last=False)


def resolve_redirect_url(url: str, *, timeout: float | None = None) -> str:
    """解析百度/360 跳转链到最终 URL（带 TTL 缓存）。"""
    u = (url or "").strip()
    if not u.startswith("http"):
        return u
    if not any(x in u for x in ("baidu.com/link?", "so.com/link?", "bing.com/ck/")):
        return u
    cached = _cache_get(u)
    if cached:
        return cached
    t_out = _RESOLVE_TIMEOUT if timeout is None else float(timeout)
    final = u
    try:
        req = urlrequest.Request(
            u,
            headers={"User-Agent": _UA, "Referer": "https://www.baidu.com/"},
            method="GET",
        )
        with urlrequest.urlopen(req, timeout=t_out) as resp:
            final = resp.geturl() or u
    except urlerror.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        final = loc or u
    except Exception:
        final = u
    if final and final != u and "baidu.com/link?" not in final:
        _cache_put(u, final)
    return final


def _needs_resolve(url: str) -> bool:
    u = url or ""
    return "baidu.com/link?" in u or "so.com/link?" in u or "bing.com/ck/" in u


def _resolve_hits(
    hits: list[dict[str, Any]],
    *,
    max_resolve: int = 5,
    query: str = "",
) -> list[dict[str, Any]]:
    """并行解析跳转 URL；先粗排再只解析前 max_resolve 条，降时延。"""
    if not hits:
        return []
    # 已有真链的不解析；需要解析的按标题相关度优先
    scored = sorted(
        enumerate(hits),
        key=lambda iv: -_relevance_score(query, iv[1]),
    )
    resolve_idx: list[int] = []
    for i, h in scored:
        url = str(h.get("url") or "")
        if _needs_resolve(url):
            resolve_idx.append(i)
        if len(resolve_idx) >= max_resolve:
            break

    def _one(h: dict[str, Any]) -> dict[str, Any]:
        out = dict(h)
        url = str(out.get("url") or "")
        if _needs_resolve(url):
            out["url"] = resolve_redirect_url(url)
        return out

    out_hits = [dict(h) for h in hits]
    if not resolve_idx:
        return out_hits

    with ThreadPoolExecutor(max_workers=min(5, max(1, len(resolve_idx)))) as ex:
        futs = {ex.submit(_one, hits[i]): i for i in resolve_idx}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                out_hits[i] = fut.result()
            except Exception:
                out_hits[i] = dict(hits[i])
    return out_hits


def search_baidu(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """百度网页搜索（国内主召回）。短页/验证码时重试。"""
    q = normalize_search_query(query) or (query or "").strip()
    if not q:
        return []
    url = "https://www.baidu.com/s?wd=" + urlparse.quote(q) + "&rn=10&ie=utf-8"
    body = ""
    for attempt in range(2):  # 最多 2 次，压时延
        try:
            body = _get(url, timeout=10.0, referer="https://www.baidu.com/")
        except Exception as e:
            logger.info("baidu search fail attempt=%s: %s", attempt, e)
            body = ""
        if body.count("<h3") >= 2 or body.count("c-container") >= 3:
            break
        if attempt == 0:
            time.sleep(0.35)
    if not body or body.count("<h3") < 1:
        logger.info("baidu search empty/captcha q=%s len=%s", q[:40], len(body or ""))
        return []

    hits: list[dict[str, Any]] = []
    for m in re.finditer(
        r"<h3[^>]*>\s*<a\s+([^>]+)>([\s\S]*?)</a>\s*</h3>([\s\S]{0,700})",
        body,
        re.I,
    ):
        attrs, title_html, rest = m.group(1), m.group(2), m.group(3)
        title = _strip_html(title_html)
        if not title or len(title) < 4:
            continue
        href_m = re.search(r'href="([^"]+)"', attrs)
        href = href_m.group(1) if href_m else ""
        # 优先同窗 mu 真链
        prev = body[max(0, m.start() - 600) : m.start()]
        mu_m = re.search(r'\smu="(https?://[^"]+)"', prev)
        if mu_m:
            href = mu_m.group(1)
        if not href or "hao.360.com" in href:
            continue
        snip_m = re.search(
            r'class="[^"]*(?:c-abstract|content-right|cos-line-clamp|summary-text)[^"]*"[^>]*>([\s\S]*?)</(?:span|div)>',
            rest,
            re.I,
        )
        snip = _strip_html(snip_m.group(1)) if snip_m else ""
        hits.append(
            {
                "sourceType": "web",
                "title": title[:80],
                "url": href,
                "snippet": snip[:200],
            }
        )
        if len(hits) >= max(limit, 8):
            break

    # 只解析前 5 条高相关（缓存命中几乎零成本）
    hits = _resolve_hits(hits, max_resolve=min(5, max(limit, 3)), query=q)
    # 丢掉仍未解析的 baidu 跳转（无法 open）；真链优先
    cleaned: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for h in hits:
        u = str(h.get("url") or "")
        if not u.startswith("http"):
            continue
        if "baidu.com/s?" in u:
            continue
        if _needs_resolve(u):
            unresolved.append(h)
            continue
        cleaned.append(h)
    # 解析失败的仍可按标题保留靠后（极少用）
    return (cleaned + unresolved)[:limit]


def search_so360(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    q = normalize_search_query(query) or (query or "").strip()
    if not q:
        return []
    url = "https://www.so.com/s?q=" + urlparse.quote(q)
    try:
        body = _get(url)
    except Exception as e:
        logger.info("so360 search fail: %s", e)
        return []
    hits: list[dict[str, Any]] = []
    for block in re.finditer(
        r'<li class="res-list"[^>]*>([\s\S]*?)</li>', body, re.I
    ):
        b = block.group(1)
        md = re.search(r'data-mdurl="([^"]+)"', b, re.I)
        title_m = re.search(
            r'class="res-title"[^>]*>\s*<a[^>]*>([\s\S]*?)</a>', b, re.I
        )
        if not title_m:
            continue
        title = _strip_html(title_m.group(1))
        href = md.group(1) if md else ""
        if not href or "hao.360.com" in href:
            hm = re.search(r'href="(https?://(?!www\.so\.com)[^"]+)"', b, re.I)
            href = hm.group(1) if hm else href
        if not href or not title:
            continue
        if href.startswith("http://") and any(
            d in href for d in ("gov.cn", "edu.cn", "moe.gov")
        ):
            href = "https://" + href[len("http://") :]
        sum_m = re.search(
            r'class="res-list-summary"[^>]*>([\s\S]*?)</span>', b, re.I
        )
        snip = _strip_html(sum_m.group(1)) if sum_m else ""
        hits.append(
            {
                "sourceType": "web",
                "title": title[:80],
                "url": href,
                "snippet": snip[:200],
            }
        )
        if len(hits) >= limit:
            break
    return hits


def search_bing_cn(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    q = normalize_search_query(query) or (query or "").strip()
    if not q:
        return []
    url = (
        "https://cn.bing.com/search?q="
        + urlparse.quote(q)
        + "&setlang=zh-CN&ensearch=0"
    )
    try:
        body = _get(url)
    except Exception as e:
        logger.info("bing search fail: %s", e)
        return []
    if "b_algo" not in body:
        return []
    hits: list[dict[str, Any]] = []
    for block in re.finditer(
        r'<li class="b_algo"[^>]*>([\s\S]*?)</li>', body, re.I
    ):
        b = block.group(1)
        lm = re.search(
            r"<h2[^>]*>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>([\s\S]*?)</a>", b, re.I
        )
        if not lm:
            continue
        href, title = lm.group(1), _strip_html(lm.group(2))
        if not title:
            continue
        sm = re.search(r"<p[^>]*>([\s\S]*?)</p>", b, re.I)
        snip = _strip_html(sm.group(1)) if sm else ""
        hits.append(
            {
                "sourceType": "web",
                "title": title[:80],
                "url": href,
                "snippet": snip[:200],
            }
        )
        if len(hits) >= limit:
            break
    return hits


_PORTAL_NOISE = re.compile(
    r"百度百科|百度地图|天气预报|旅游景点|人民政府门户网站$|互动百科"
)


def _relevance_score(query: str, hit: dict[str, Any]) -> int:
    """粗相关度：标题命中查询碎片越高越好；门户噪声降权。"""
    q = normalize_search_query(query) or query or ""
    title = str(hit.get("title") or "")
    snip = str(hit.get("snippet") or "")
    blob = f"{title} {snip}"
    if _PORTAL_NOISE.search(title):
        return -50
    score = 0
    # 年份
    for y in re.findall(r"20\d{2}", q):
        if y in blob:
            score += 3
    # 2～6 字中文碎片
    parts = re.findall(r"[\u4e00-\u9fff]{2,6}", q)
    seen: set[str] = set()
    for p in parts:
        if p in seen or p in ("什么", "一下", "相关", "信息", "名单"):
            continue
        seen.add(p)
        if p in title:
            score += 4
        elif p in snip:
            score += 2
    if any(k in title for k in ("获奖", "公示", "通知", "名单", "大赛", "技能")):
        score += 2
    if ".gov.cn" in str(hit.get("url") or "") or ".edu.cn" in str(hit.get("url") or ""):
        score += 3
    return score


def _merge_hits(
    batches: list[list[dict[str, Any]]],
    *,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for batch in batches:
        for h in batch or []:
            if not isinstance(h, dict):
                continue
            url = str(h.get("url") or "").strip()
            title = str(h.get("title") or "").strip()
            key = url or title
            if not key or key in seen:
                continue
            if not title:
                continue
            seen.add(key)
            merged.append(h)
    merged.sort(key=lambda h: -_relevance_score(query, h))
    # 丢掉明显负分噪声（百科省名/地图），除非总数过少
    strong = [h for h in merged if _relevance_score(query, h) > 0]
    if len(strong) >= 2:
        merged = strong
    return merged[:limit]


# 中文政务/官方意图信号（通用词，不写省表）
_CN_OFFICIAL_SIGNAL = re.compile(
    r"通知|公示|名单|政策|办法|条例|规定|文号|公文|"
    r"教育厅|人社|人民政府|教育部|官网|官方|大赛|获奖|"
    r"技能|职教|报名|规程|意见|决定|公告|公开"
)
_CN_GEO_HINT = re.compile(r"[\u4e00-\u9fff]{2,4}(?:省|市|自治区|地区|县|区)")


def looks_cn_official_query(query: str) -> bool:
    """是否像中文政务/官方公开信息检索（用于 site:gov 扩展，非业务白名单）。"""
    q = query or ""
    if not q.strip():
        return False
    if _CN_OFFICIAL_SIGNAL.search(q):
        return True
    if _CN_GEO_HINT.search(q) and re.search(r"[\u4e00-\u9fff]{4,}", q):
        return True
    return False


def expand_cn_gov_queries(query: str, *, max_n: int = 3) -> list[str]:
    """中文政务召回扩展：site:gov.cn / site:edu.cn / 通知公示，不写死省份域名。"""
    q = normalize_search_query(query) or (query or "").strip()
    if not q:
        return []
    # 已带 site: 则只规范主句
    base = re.sub(r"\s*site:\S+", " ", q, flags=re.I)
    base = re.sub(r"\s+", " ", base).strip()[:40]
    if not base:
        return [q[:48]]
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip())[:48]
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(base)
    if not looks_cn_official_query(base) and "site:" not in q.lower():
        return out[:max_n]
    add(f"{base} site:gov.cn")
    add(f"{base} site:edu.cn")
    # 无通知/公示词时补通用官方信号（提升政务 SERP 权重）
    if not re.search(r"通知|公示|名单|公告", base):
        add(f"{base} 通知 公示")
    return out[:max_n]


def looks_time_sensitive_query(query: str) -> bool:
    """时效/近年问句：空结果时更积极换引擎。"""
    q = query or ""
    if re.search(r"最近|最新|今年|本月|本周|时效|刚刚|近日|新近", q):
        return True
    if re.search(r"20(?:2[4-9]|3\d)", q):  # 2024–203x
        return True
    return False


def looks_pdf_seeking_query(query: str) -> bool:
    """名单/附件/PDF 意图：空结果时换引擎并补 filetype 类检索。"""
    q = query or ""
    return bool(
        re.search(r"(?i)\.pdf|PDF|附件|下载|名单|公示|通知|获奖|完整名单|全文", q)
    )


def _safe_engine(fn: Any, q: str, *, limit: int) -> list[dict[str, Any]]:
    try:
        out = fn(q, limit=limit)
        return out if isinstance(out, list) else []
    except Exception as e:
        logger.info("engine %s fail q=%s: %s", getattr(fn, "__name__", "?"), q[:30], e)
        return []


def public_web_search(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Agent 用统一入口：百度主源 + 中文政务 fan-out + 空/弱结果自动换引擎。

    时效/PDF 问句在主源空或弱时强制 360/Bing 并行补齐；名单类再补 filetype:pdf 变体。
    """
    q = normalize_search_query(query) or (query or "").strip()
    if not q:
        return []

    t0 = time.time()
    batches: list[list[dict[str, Any]]] = []
    time_sens = looks_time_sensitive_query(q)
    pdf_seek = looks_pdf_seeking_query(q)

    # 百度优先（国内教育/政务召回明显更好）
    baidu_hits = _safe_engine(search_baidu, q, limit=limit)
    batches.append(baidu_hits)

    baidu_n = len(baidu_hits)
    strong = sum(1 for h in baidu_hits if _relevance_score(q, h) >= 6)
    gov_hits = sum(
        1
        for h in baidu_hits
        if ".gov.cn" in str(h.get("url") or "") or ".edu.cn" in str(h.get("url") or "")
    )
    # 中文政务 fan-out：官方意图 或 主搜弱/缺 gov 域
    need_gov = looks_cn_official_query(q) and (strong < 3 or gov_hits < 1 or baidu_n < 4)
    if need_gov:
        for gq in expand_cn_gov_queries(q, max_n=3)[1:]:  # 跳过与主 query 重复的 base
            if gq == q:
                continue
            batches.append(_safe_engine(search_baidu, gq, limit=min(limit, 6)))
            # 只补一路 site 扩展，控时延
            break

    # 空结果 / 弱结果 / 时效·PDF 意图：强制换引擎（360 + Bing 并行）
    total_n = sum(len(b) for b in batches)
    strong_all = sum(1 for b in batches for h in b if _relevance_score(q, h) >= 6)
    empty_primary = baidu_n == 0
    weak = total_n < 3 or strong_all < 2
    # 时效/PDF：主源无强命中也换（即使有几条噪声）
    force_failover = empty_primary or weak or (
        (time_sens or pdf_seek) and strong_all < 3
    )
    engine_tags: list[str] = [f"baidu:{baidu_n}"]
    if force_failover:
        alt_jobs: list[tuple[str, Any, str, int]] = [
            ("so360", search_so360, q, min(limit, 6)),
            ("bing", search_bing_cn, q, min(limit, 6)),
        ]
        # PDF/名单空结果：再 hop 一条 filetype 变体（走百度，换检索式）
        if pdf_seek and (empty_primary or strong_all < 1):
            pdf_q = re.sub(r"\s+", " ", f"{q} filetype:pdf").strip()[:48]
            if pdf_q != q:
                alt_jobs.append(("baidu_pdf", search_baidu, pdf_q, min(limit, 6)))
            att_q = re.sub(r"\s+", " ", f"{q} 附件 PDF").strip()[:48]
            if att_q != q and att_q != pdf_q:
                alt_jobs.append(("baidu_att", search_baidu, att_q, min(limit, 6)))

        with ThreadPoolExecutor(max_workers=min(4, max(1, len(alt_jobs)))) as ex:
            futs = {
                ex.submit(_safe_engine, fn, qq, limit=lim): tag
                for tag, fn, qq, lim in alt_jobs
            }
            for fut in as_completed(futs):
                tag = futs[fut]
                try:
                    part = fut.result() or []
                except Exception:
                    part = []
                batches.append(part)
                engine_tags.append(f"{tag}:{len(part)}")

    hits = _merge_hits(batches, query=q, limit=limit)
    logger.info(
        "public_web_search q=%s hits=%s engines=%s gov_fanout=%s "
        "time_sens=%s pdf_seek=%s failover=%s ms=%s",
        q[:40],
        len(hits),
        engine_tags,
        need_gov,
        time_sens,
        pdf_seek,
        force_failover,
        int((time.time() - t0) * 1000),
    )
    return hits
