"""赛道 RULES + 赛场匿名规范包（类似 AGENTS.md 注入）。"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_CATALOG = Path(__file__).resolve().parent / "catalog"
_MAX_CHARS = 2800

# 用户口头赛道 → catalog 目录名
_TRACK_ALIASES: dict[str, str] = {
    "餐饮": "餐饮",
    "餐饮赛道": "餐饮",
    "信息技术": "新一代信息技术",
    "新一代信息技术": "新一代信息技术",
    "信技": "新一代信息技术",
    "ai": "新一代信息技术",
    "人工智能": "新一代信息技术",
}


def _norm_track(name: str | None) -> str | None:
    if not name:
        return None
    t = re.sub(r"\s+", "", str(name).strip())
    if not t:
        return None
    t = re.sub(r"(赛道|赛项)$", "", t)
    key = t.lower() if re.fullmatch(r"[a-z0-9_\-]+", t, re.I) else t
    if key in _TRACK_ALIASES:
        return _TRACK_ALIASES[key]
    if t in _TRACK_ALIASES:
        return _TRACK_ALIASES[t]
    # 模糊：目录名包含
    try:
        for p in _CATALOG.iterdir():
            if p.is_dir() and p.name.startswith("_"):
                continue
            if p.is_dir() and (t in p.name or p.name in t):
                return p.name
    except OSError:
        pass
    return t


@lru_cache(maxsize=32)
def _read_md(path_str: str) -> str:
    path = Path(path_str)
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("track rules read failed %s: %s", path, exc)
        return ""
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n…(已截断)"
    return text


def clear_tracks_cache() -> None:
    _read_md.cache_clear()


def load_anonymity_block() -> str:
    p = _CATALOG / "_common" / "ANONYMITY.md"
    body = _read_md(str(p)) if p.is_file() else ""
    if not body:
        return ""
    return "## 赛场匿名规范包（必须遵守）\n" + body


def load_common_rules() -> str:
    p = _CATALOG / "_common" / "RULES.md"
    body = _read_md(str(p)) if p.is_file() else ""
    if not body:
        return ""
    return body


def load_track_rules(track: str | None) -> str:
    name = _norm_track(track)
    if not name:
        return ""
    p = _CATALOG / name / "RULES.md"
    if not p.is_file():
        return ""
    body = _read_md(str(p))
    if not body:
        return ""
    return f"## 赛道 RULES · {name}\n{body}"


def resolve_rules_block(
    *,
    track: str | None = None,
    include_anonymity: bool = True,
    include_common: bool = True,
) -> tuple[str, list[str]]:
    """返回 (system 注入块, 已加载标签列表)。"""
    parts: list[str] = []
    tags: list[str] = []
    if include_anonymity:
        anon = load_anonymity_block()
        if anon:
            parts.append(anon)
            tags.append("anonymity")
    if include_common:
        common = load_common_rules()
        if common:
            parts.append(common)
            tags.append("common_rules")
    track_body = load_track_rules(track)
    if track_body:
        parts.append(track_body)
        tags.append(f"track:{_norm_track(track)}")
    if not parts:
        return "", tags
    header = "## 规范与赛道 RULES（类似 AGENTS，必须遵守）\n"
    return header + "\n\n".join(parts), tags
