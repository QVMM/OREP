"""Soft 域名偏好：按 TLD/机构形态加权，不写死省名或站点白名单业务表。

偏好（加分）：
- .gov.cn / 政府门户
- .edu.cn / 教育机构
- 路径含公告/通知形态由调用方另判

降权：
- 百科聚合、纯营销域常见尾巴（可模式匹配）
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def _host(url: str) -> str:
    try:
        h = urlparse(url or "").netloc.lower()
        if h.startswith("www."):
            h = h[4:]
        return h
    except Exception:
        return ""


def soft_domain_boost(url: str) -> int:
    """返回 soft 加分（可为负）。不决定 hard gate，只影响排序。"""
    u = (url or "").lower()
    h = _host(url)
    score = 0
    # 权威形态
    if h.endswith(".gov.cn") or ".gov.cn" in u:
        score += 12
    if h.endswith(".edu.cn") or ".edu.cn" in u:
        score += 10
    if h.endswith(".org.cn") or h.endswith(".org"):
        score += 3
    # 教育部等部委常见短域（形态：*.moe.gov.cn 已含 gov）
    if "moe.gov" in h:
        score += 4
    # 常见噪声域降权（非业务白名单，通用噪声）
    noise = (
        "baike.baidu.",
        "zhidao.baidu.",
        "tieba.baidu.",
        "sohu.com",
        "sina.com",
        "163.com",
        "qq.com",
        "zhihu.com",
        "weixin.qq.",
        "mp.weixin.",
    )
    for n in noise:
        if n in h or n in u:
            score -= 6
            break
    if "stats.gov" in h:
        # 统计公报类常被年份带偏
        score -= 8
    return score


def sort_hits_by_soft_rank(
    hits: list[dict[str, Any]] | None,
    *,
    score_key: str = "_score",
) -> list[dict[str, Any]]:
    """在已有 _score 上叠加 soft 域名分后排序（稳定、可测）。"""
    if not hits:
        return []
    decorated: list[tuple[int, int, dict[str, Any]]] = []
    for i, h in enumerate(hits):
        if not isinstance(h, dict):
            continue
        base = 0
        try:
            base = int(h.get(score_key) or 0)
        except Exception:
            base = 0
        boost = soft_domain_boost(str(h.get("url") or ""))
        decorated.append((base + boost, -i, h))
    decorated.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [h for _, _, h in decorated]
