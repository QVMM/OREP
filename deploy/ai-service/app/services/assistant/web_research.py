"""联网研究辅助：轻量 LLM 改写检索词 + 抓取网页正文。

供 Java 后端在 deep_search 模式下调用，失败时调用方回落规则改写。
"""
from __future__ import annotations

import json
import logging
import re
from html import unescape
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_JSON_OBJ = re.compile(r"\{[\s\S]*\}")
_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"(?is)<script[\s\S]*?</script>")
_STYLE = re.compile(r"(?is)<style[\s\S]*?</style>")
_WS = re.compile(r"\s+")


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    normalized = base_url.strip().rstrip("/")
    suffix = "/chat/completions"
    if normalized.lower().endswith(suffix):
        normalized = normalized[: -len(suffix)].rstrip("/")
    return normalized or None


def _mimo_client() -> OpenAI | None:
    api_key = settings.MIMO_WEB_API_KEY or settings.MIMO_API_KEY or settings.PPT_TEXT_API_KEY
    if not api_key:
        return None
    base = _normalize_base_url(settings.MIMO_WEB_BASE_URL or settings.MIMO_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base)


def _model_name() -> str:
    return settings.MIMO_WEB_MODEL or settings.MIMO_MODEL or settings.PPT_TEXT_MODEL or "mimo-v2.5-pro"


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    # strip code fence
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        m = _JSON_OBJ.search(text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None


def _llm_json_chat(user_prompt: str, *, max_tokens: int = 400, temperature: float = 0.15) -> tuple[str, str]:
    """返回 (content, model)。"""
    client = _mimo_client()
    if client is None:
        return "", ""
    model = _model_name()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": user_prompt}],
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = ""
    if resp.choices:
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content:
            content = str(
                getattr(msg, "reasoning_content", None)
                or getattr(msg, "reasoning", None)
                or ""
            ).strip()
    return content, model


def _parse_queries_from_llm(content: str, *, max_queries: int) -> list[str]:
    obj = _extract_json(content) or {}
    raw_list = obj.get("queries") or obj.get("query") or []
    if isinstance(raw_list, str):
        raw_list = [raw_list]
    if not isinstance(raw_list, list) or not raw_list:
        lines = re.findall(r'["“]([^"”]{2,40})["”]', content or "")
        raw_list = lines if lines else []
    cleaned: list[str] = []
    for item in raw_list:
        s = _clean_query_phrase(str(item or ""))
        if not s:
            continue
        if s not in cleaned:
            cleaned.append(s)
        if len(cleaned) >= max_queries:
            break
    return cleaned


def rewrite_search_queries_llm(user_query: str, *, max_queries: int = 3) -> dict[str, Any]:
    """返回 {queries: [...], source: llm|empty, model?}。失败 queries=[]。"""
    q = (user_query or "").strip()
    if not q:
        return {"queries": [], "source": "empty"}

    if _mimo_client() is None:
        fb = _generic_fallback_queries(q, max_queries=max_queries)
        return {"queries": fb, "source": "no_key_fallback" if fb else "no_key"}

    # 通用改写：不写死任何赛道/题型。Grok 同思路——按当前问题动态改写。
    user = (
        "你是通用搜索查询改写器（不限领域）。\n"
        "把用户口语改成适合搜索引擎的检索式，1～3 条。\n"
        "只输出一行 JSON 对象，键名必须是 queries，值为字符串数组。\n"
        "例如用户问「2024 诺贝尔物理奖得主是谁」可输出："
        "{\"queries\":[\"2024 诺贝尔物理学奖 得主\",\"Nobel Prize Physics 2024 winners\"]}\n"
        "硬规则：\n"
        "1) 每条 ≤20 字/词，空格分词；不要问号、完整客服句。\n"
        "2) 去掉口语壳（网上/有没有/帮我/请/好的/一下/搜索 等），保留年份、专名、实体、意图。\n"
        "3) 多条从不同角度覆盖；**每条都应包含问题中的核心专名短语**，禁止只输出单独年份。\n"
        "4) 禁止输出「关键词1」「关键词组2」等占位符。\n"
        "5) 不要解释、不要 Markdown 代码块。\n"
        f"用户问题：{q[:240]}"
    )

    try:
        content, model = _llm_json_chat(user, max_tokens=400, temperature=0.15)
        cleaned = _parse_queries_from_llm(content, max_queries=max_queries)
        if not cleaned:
            cleaned = _generic_fallback_queries(q, max_queries=max_queries)
            return {
                "queries": cleaned,
                "source": "fallback" if cleaned else "llm_empty",
                "model": model,
                "raw": content[:120] if content else None,
            }
        return {
            "queries": cleaned[:max_queries],
            "source": "llm",
            "model": model,
        }
    except Exception as exc:
        logger.warning("rewrite_search_queries_llm failed: %s", exc)
        fb = _generic_fallback_queries(q, max_queries=max_queries)
        return {
            "queries": fb,
            "source": "error_fallback" if fb else "error",
            "error": str(exc)[:160],
        }


def refine_search_queries_llm(
    user_query: str,
    *,
    prior_queries: list[str] | None = None,
    hit_titles: list[str] | None = None,
    bad_titles: list[str] | None = None,
    must_keep_phrases: list[str] | None = None,
    max_queries: int = 3,
) -> dict[str, Any]:
    """第二轮补搜：根据首轮结果标题，动态生成更准的检索词（通用，不写死领域）。"""
    q = (user_query or "").strip()
    if not q:
        return {"queries": [], "source": "empty"}

    titles = [str(t).strip() for t in (hit_titles or []) if str(t).strip()][:8]
    bad = [str(t).strip() for t in (bad_titles or []) if str(t).strip()][:6]
    keep = [str(t).strip() for t in (must_keep_phrases or []) if str(t).strip()][:4]
    priors = [str(p).strip() for p in (prior_queries or []) if str(p).strip()][:6]
    title_blob = "；".join(titles) if titles else "（首轮几乎无相关结果）"
    bad_blob = "；".join(bad) if bad else "（无）"
    keep_blob = "；".join(keep) if keep else "（从用户问题中自抽专名）"
    prior_blob = "；".join(priors) if priors else "（无）"

    prompt = (
        "你在做「多轮搜索补搜」。不限领域。\n"
        "用户问题、首轮检索词、命中标题、跑偏标题、必须保留的实体短语已给出。\n"
        "请生成 1～3 条**新的**搜索引擎检索式。\n"
        "只输出一行 JSON：{\"queries\":[\"...\"]}\n"
        "规则：\n"
        "1) 不要重复首轮检索词；\n"
        "2) 每条必须尽量包含「必须保留的实体短语」中的核心专名（不要只搜年份）；\n"
        "3) 若跑偏标题全是无关主题，换更精确的专名组合/官方全称/同义说法；\n"
        "4) 每条≤24字，禁止占位词，不要解释。\n"
        f"用户问题：{q[:240]}\n"
        f"必须保留的实体短语：{keep_blob[:200]}\n"
        f"首轮检索词：{prior_blob[:200]}\n"
        f"首轮命中标题：{title_blob[:300]}\n"
        f"跑偏标题（应避开）：{bad_blob[:300]}\n"
    )
    try:
        if _mimo_client() is None:
            return {"queries": [], "source": "no_key"}
        content, model = _llm_json_chat(prompt, max_tokens=350, temperature=0.2)
        cleaned = _parse_queries_from_llm(content, max_queries=max_queries)
        # 去掉与 prior 重复
        prior_set = {p.lower() for p in priors}
        cleaned = [c for c in cleaned if c.lower() not in prior_set]
        return {
            "queries": cleaned[:max_queries],
            "source": "llm" if cleaned else "llm_empty",
            "model": model,
        }
    except Exception as exc:
        logger.warning("refine_search_queries_llm failed: %s", exc)
        return {"queries": [], "source": "error", "error": str(exc)[:160]}


def rerank_hits_llm(
    user_query: str,
    hits: list[dict[str, Any]],
    *,
    top_k: int = 6,
) -> dict[str, Any]:
    """用 LLM 对候选结果重排（通用）。返回 {order:[原下标...], scores?:{}}。"""
    q = (user_query or "").strip()
    if not q or not hits:
        return {"order": list(range(len(hits or []))), "source": "noop"}

    # 只送标题+短摘要，控制 token
    lines = []
    for i, h in enumerate(hits[:12]):
        if not isinstance(h, dict):
            continue
        title = str(h.get("title") or "")[:80]
        snip = str(h.get("snippet") or h.get("pageText") or "")[:120]
        lines.append(f"{i}. {title} | {snip}")
    if not lines:
        return {"order": [], "source": "empty"}

    prompt = (
        "你是通用搜索结果排序器。根据用户问题，对候选结果按相关度从高到低排序。\n"
        "只输出一行 JSON：{\"order\":[3,0,1,...]}，数字是候选编号，可省略明显无关项。\n"
        "不要解释。\n"
        f"用户问题：{q[:240]}\n"
        "候选：\n" + "\n".join(lines)
    )
    try:
        if _mimo_client() is None:
            return {"order": list(range(min(top_k, len(hits)))), "source": "no_key"}
        content, model = _llm_json_chat(prompt, max_tokens=200, temperature=0.0)
        obj = _extract_json(content) or {}
        order_raw = obj.get("order") or obj.get("ranks") or []
        order: list[int] = []
        if isinstance(order_raw, list):
            for x in order_raw:
                try:
                    idx = int(x)
                except Exception:
                    continue
                if 0 <= idx < len(hits) and idx not in order:
                    order.append(idx)
                if len(order) >= top_k:
                    break
        # 补全未出现的高分项
        for i in range(len(hits)):
            if i not in order:
                order.append(i)
            if len(order) >= top_k:
                break
        return {"order": order[:top_k], "source": "llm", "model": model}
    except Exception as exc:
        logger.warning("rerank_hits_llm failed: %s", exc)
        return {"order": list(range(min(top_k, len(hits)))), "source": "error"}

def _strip_html_to_text(html: str) -> tuple[str, str]:
    """返回 (title, text)。"""
    if not html:
        return "", ""
    title = ""
    tm = re.search(r"(?is)<title[^>]*>([\s\S]*?)</title>", html)
    if tm:
        title = _WS.sub(" ", unescape(_TAG.sub("", tm.group(1)))).strip()

    # 优先 main/article
    body = html
    for pat in (
        r"(?is)<article[^>]*>([\s\S]*?)</article>",
        r"(?is)<main[^>]*>([\s\S]*?)</main>",
        r"(?is)<div[^>]+id=[\"']content[\"'][^>]*>([\s\S]*?)</div>",
    ):
        m = re.search(pat, html)
        if m and len(m.group(1)) > 200:
            body = m.group(1)
            break

    body = _SCRIPT.sub(" ", body)
    body = _STYLE.sub(" ", body)
    # drop nav/footer lightly
    body = re.sub(r"(?is)<nav[\s\S]*?</nav>", " ", body)
    body = re.sub(r"(?is)<footer[\s\S]*?</footer>", " ", body)
    body = re.sub(r"(?is)<header[\s\S]*?</header>", " ", body)
    text = _TAG.sub(" ", body)
    text = unescape(text)
    text = _WS.sub(" ", text).strip()
    return title, text


_CHAT_SHELL = re.compile(
    r"网上有没有|有没有好的|有没有|能不能|可不可以|请给我|帮我找|帮我|请问|"
    r"真实参加|真实的|比较好|好的|一下|谢谢"
)


def _clean_query_phrase(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"[?？!！。，,、；;：:\"'“”‘’]", " ", s)
    s = _CHAT_SHELL.sub(" ", s)
    s = re.sub(r"^(搜索|搜一下|查一下|查找)\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 2:
        return ""
    if len(s) > 36:
        s = s[:36].strip()
    # 过短/只有年份不够当检索式
    if re.fullmatch(r"20\d{2}年?", s):
        return ""
    if re.search(r"办税|网上银行|学信网|政务服务|人社厅|电子银行", s):
        return ""
    # 模型占位符 / 假词
    if re.match(r"(?i)^keyword\s*\d*$", s):
        return ""
    if re.match(r"(?i)^(query|term|keyword)[\s_\-]*\d*$", s):
        return ""
    if re.match(r"^关键词\s*\d*$", s):
        return ""
    if re.match(r"^关键词组\s*\d*$", s):
        return ""
    if re.match(r"^(检索词|搜索词|词条|示例词)\s*[A-Za-z0-9]*$", s):
        return ""
    if "关键词" in s and len(s) <= 8:
        return ""
    if s in {"...", "…", "……", "xxx", "XXX", "待补充"}:
        return ""
    if re.fullmatch(r"[.\-…_]+", s):
        return ""
    if re.fullmatch(r"[A-Za-z0-9_\-\s]{1,40}", s) and not re.search(r"[\u4e00-\u9fff]", s):
        return ""
    # 单独一个过泛/口语词不要
    if s in {
        "比赛", "竞赛", "网上", "开场词", "开场", "内容", "资料",
        "搜索", "怎么", "如何", "什么", "一下", "真实", "好的",
    }:
        return ""
    # 清理异常符号串
    if s.count("/") >= 2 and len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", s)) < 6:
        return ""
    return s


def _generic_fallback_queries(user_q: str, *, max_queries: int = 3) -> list[str]:
    """通用兜底：剥口语壳，保留用户原句里的实体/时间/意图词。不写死任何业务模板。"""
    raw = (user_q or "").strip()
    if not raw:
        return []
    t = re.sub(r"[?？!！。，,、；;：:\"'“”‘’（）()\[\]【】]", " ", raw)
    t = _CHAT_SHELL.sub(" ", t)
    for stop in (
        "一个", "一些", "什么", "怎么", "如何", "可以", "需要", "给我", "找找", "看看",
        "推荐", "相关", "内容", "资料", "搜索", "搜一下", "查一下", "的", "了", "吗",
        "呢", "啊", "吧", "是", "在", "和", "与", "或", "就", "都", "很", "太", "更", "最",
        "一下", "帮我", "请问",
    ):
        t = t.replace(stop, " ")
    t = re.sub(r"\s+", " ", t).strip()
    out: list[str] = []
    if 2 <= len(t) <= 40:
        out.append(t)
    elif len(t) > 40:
        # 按空格切，取前若干有信息量的片段
        parts = [p for p in t.split(" ") if len(p) >= 2][:6]
        if parts:
            out.append(" ".join(parts[:4])[:36])
            if len(parts) > 3:
                out.append(" ".join(parts[2:6])[:36])
    # 抽出年份作第二条角度（通用，不绑赛道）
    years = re.findall(r"20\d{2}", raw)
    if years and out:
        yq = f"{years[0]} {out[0]}"
        if yq not in out:
            out.append(yq[:36])
    return out[:max_queries]


def fetch_page(url: str, *, max_chars: int = 1800, timeout: float = 8.0) -> dict[str, Any]:
    """抓取单页正文。"""
    u = (url or "").strip()
    if not u or not u.startswith("http"):
        return {"ok": False, "url": u, "error": "bad_url"}
    # 跳过明显二进制/应用商店 / 跟踪跳转难解的
    if re.search(r"\.(pdf|zip|rar|exe|dmg|apk)(\?|$)", u, re.I):
        return {"ok": False, "url": u, "error": "binary_skip"}
    try:
        req = urlrequest.Request(
            u,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
            },
            method="GET",
        )
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text" not in ctype and ctype:
                return {"ok": False, "url": u, "error": f"ctype:{ctype[:40]}"}
            raw = resp.read(400_000)  # cap ~400KB
            # charset
            charset = "utf-8"
            if "charset=" in ctype:
                charset = ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
            try:
                html = raw.decode(charset, errors="ignore")
            except Exception:
                html = raw.decode("utf-8", errors="ignore")
            final_url = resp.geturl() or u
        title, text = _strip_html_to_text(html)
        if len(text) < 40:
            return {"ok": False, "url": final_url, "title": title, "error": "too_short"}
        # 去掉开头重复标题
        if title and text.startswith(title):
            text = text[len(title) :].strip()
        text = text[:max_chars]
        if len(text) >= max_chars:
            text = text[: max_chars - 1] + "…"
        return {
            "ok": True,
            "url": final_url,
            "title": title[:120] if title else "",
            "text": text,
            "chars": len(text),
        }
    except Exception as exc:
        logger.info("fetch_page fail %s: %s", u[:80], exc)
        return {"ok": False, "url": u, "error": str(exc)[:120]}


def fetch_pages(urls: list[str], *, max_pages: int = 3, max_chars: int = 1800) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for u in urls or []:
        if len(out) >= max_pages:
            break
        key = (u or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        page = fetch_page(key, max_chars=max_chars)
        if page.get("ok"):
            out.append(page)
    return out


def enrich_hits_with_pages(
    hits: list[dict[str, Any]],
    *,
    max_pages: int = 3,
    max_chars: int = 1600,
) -> list[dict[str, Any]]:
    """给搜索 hit 补充 pageText / 加长 snippet（按命中顺序抓前 max_pages 个）。"""
    if not hits:
        return []
    urls: list[str] = []
    for h in hits:
        if not isinstance(h, dict):
            continue
        u = str(h.get("url") or "").strip()
        if u.startswith("http") and u not in urls:
            urls.append(u)

    # 顺序抓取：url -> page，同时保留原始请求 url 映射
    pages_by_req: dict[str, dict[str, Any]] = {}
    fetched = 0
    for u in urls:
        if fetched >= max_pages:
            break
        page = fetch_page(u, max_chars=max_chars)
        if page.get("ok"):
            pages_by_req[u] = page
            fetched += 1

    enriched: list[dict[str, Any]] = []
    for h in hits:
        if not isinstance(h, dict):
            continue
        item = dict(h)
        u = str(item.get("url") or "")
        page = pages_by_req.get(u)
        if page and page.get("ok"):
            text = str(page.get("text") or "")
            if page.get("title") and (
                not item.get("title") or len(str(item.get("title"))) < 4
            ):
                item["title"] = page["title"]
            item["pageText"] = text
            item["snippet"] = text[:220] + ("…" if len(text) > 220 else "")
            item["fetched"] = True
            if page.get("url") and page.get("url") != u:
                item["finalUrl"] = page["url"]
        enriched.append(item)
    return enriched
