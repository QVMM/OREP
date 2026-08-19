"""URL 阅读意图：从用户问题抽取链接，优先直抓而非关键词检索。"""
from __future__ import annotations

import re

# 允许路径中的常见字符；去掉尾部中文标点
_URL_RE = re.compile(
    r"https?://[^\s\[\]（）()<>\"'“”‘’]+",
    re.I,
)
_TRAIL_PUNCT = re.compile(r"[。．，,、；;：:!！?？》>】\]]+$")


def extract_http_urls(text: str) -> list[str]:
    raw = text or ""
    out: list[str] = []
    for m in _URL_RE.finditer(raw):
        u = m.group(0)
        u = _TRAIL_PUNCT.sub("", u)
        u = u.rstrip(".,;:!?")
        if u.startswith("http") and u not in out:
            out.append(u)
    return out


def is_url_read_intent(text: str) -> bool:
    """问题中带 URL，且像「打开/看内容/这个网站」或仅贴链接。"""
    urls = extract_http_urls(text)
    if not urls:
        return False
    t = text or ""
    # 只要有 URL，默认按阅读意图处理（避免把「告诉」拿去搜）
    if len(urls) >= 1:
        # 若整句几乎只有 URL，必读
        stripped = _URL_RE.sub(" ", t)
        stripped = re.sub(r"\s+", "", stripped)
        if len(stripped) <= 8:
            return True
        keys = (
            "网站",
            "链接",
            "网页",
            "打开",
            "看看",
            "内容",
            "上面",
            "这篇",
            "这个",
            "访问",
            "总结",
            "摘要",
            "读一下",
            "说了什么",
            "写了什么",
            "是什么",
            "告诉我",
        )
        if any(k in t for k in keys):
            return True
        # 含 URL 即倾向直抓
        return True
    return False


def should_skip_keyword_search(text: str) -> bool:
    """有明确 URL 阅读意图时，禁止再做「告诉/词典」式关键词搜索。"""
    return is_url_read_intent(text) and bool(extract_http_urls(text))
