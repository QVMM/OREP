"""Discover, match, and format XiaoQi skills (Grok Build–inspired).

A skill is a directory with SKILL.md:

```markdown
---
name: opening
description: 30 秒路演开场…
triggers: [开场, 30秒]
slash: 开场
audience: student   # student | teacher | any
priority: 10
need_scores: false
need_learning: false
need_tasks: false
need_collab: false
---

# body injected into system prompt
```
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CATALOG = Path(__file__).resolve().parent / "catalog"
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)
_SLASH = re.compile(r"(?:^|\s)/([A-Za-z0-9_\u4e00-\u9fff]{1,24})\b")


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: str
    triggers: tuple[str, ...] = ()
    slash: str | None = None
    audience: str = "any"  # student | teacher | any
    priority: int = 0
    need_scores: bool = False
    need_learning: bool = False
    need_tasks: bool = False
    need_collab: bool = False
    max_inject_chars: int = 3500


@dataclass(frozen=True)
class SkillMatch:
    skill: Skill
    score: float
    reason: str  # slash | trigger | description


def _parse_yamlish(block: str) -> dict[str, Any]:
    """Minimal YAML subset for skill frontmatter (no PyYAML dependency)."""
    result: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if not val:
            result[key] = ""
            continue
        # list: [a, b] or ["a", "b"]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            items: list[str] = []
            if inner:
                for part in inner.split(","):
                    p = part.strip().strip("'\"").strip()
                    if p:
                        items.append(p)
            result[key] = items
            continue
        if val.lower() in {"true", "yes"}:
            result[key] = True
            continue
        if val.lower() in {"false", "no"}:
            result[key] = False
            continue
        if re.fullmatch(r"-?\d+", val):
            result[key] = int(val)
            continue
        result[key] = val.strip("'\"").strip()
    return result


def _load_skill_file(path: Path) -> Skill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("skill read failed %s: %s", path, exc)
        return None
    match = _FRONTMATTER.match(text)
    if not match:
        logger.warning("skill missing frontmatter: %s", path)
        return None
    meta = _parse_yamlish(match.group(1))
    body = (match.group(2) or "").strip()
    name = str(meta.get("name") or path.parent.name).strip()
    if not name or not body:
        return None
    triggers_raw = meta.get("triggers") or []
    if isinstance(triggers_raw, str):
        triggers = tuple(t.strip() for t in triggers_raw.split(",") if t.strip())
    else:
        triggers = tuple(str(t).strip() for t in triggers_raw if str(t).strip())
    audience = str(meta.get("audience") or "any").strip().lower()
    if audience not in {"student", "teacher", "any"}:
        audience = "any"
    slash = meta.get("slash")
    slash_s = str(slash).strip() if slash not in (None, "") else None
    return Skill(
        name=name,
        description=str(meta.get("description") or "").strip(),
        body=body,
        path=str(path),
        triggers=triggers,
        slash=slash_s,
        audience=audience,
        priority=int(meta.get("priority") or 0),
        need_scores=bool(meta.get("need_scores")),
        need_learning=bool(meta.get("need_learning")),
        need_tasks=bool(meta.get("need_tasks")),
        need_collab=bool(meta.get("need_collab")),
        max_inject_chars=int(meta.get("max_inject_chars") or 3500),
    )


@lru_cache(maxsize=1)
def discover_skills(catalog_dir: str | None = None) -> tuple[Skill, ...]:
    root = Path(catalog_dir) if catalog_dir else _CATALOG
    if not root.is_dir():
        return ()
    skills: list[Skill] = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        skill = _load_skill_file(skill_md)
        if skill:
            skills.append(skill)
    return tuple(skills)


def clear_skills_cache() -> None:
    discover_skills.cache_clear()


def _audience_ok(skill: Skill, audience: str) -> bool:
    if skill.audience == "any":
        return True
    return skill.audience == audience


def match_skills(
    user_text: str,
    *,
    audience: str = "student",
    limit: int = 2,
    catalog_dir: str | None = None,
) -> list[SkillMatch]:
    """Return top skill matches for this user turn."""
    text = (user_text or "").strip()
    if not text:
        return []
    audience = (audience or "student").strip().lower()
    if audience not in {"student", "teacher"}:
        audience = "student"

    slashes = {m.group(1) for m in _SLASH.finditer(text)}
    # also accept full-width slash
    for m in re.finditer(r"(?:^|\s)／([A-Za-z0-9_\u4e00-\u9fff]{1,24})\b", text):
        slashes.add(m.group(1))

    scored: list[SkillMatch] = []
    for skill in discover_skills(catalog_dir):
        if not _audience_ok(skill, audience):
            continue
        score = 0.0
        reason = "trigger"
        if skill.slash and skill.slash in slashes:
            score = 100.0 + skill.priority
            reason = "slash"
        else:
            # trigger hits
            hits = 0
            for trig in skill.triggers:
                if trig and trig in text:
                    hits += 1
                    # longer triggers weight more
                    score += 8.0 + min(12.0, len(trig) * 0.4)
            if hits:
                score += skill.priority
                reason = "trigger"
            # description token soft match (weak)
            elif skill.description:
                for token in re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{4,}", skill.description):
                    if token in text:
                        score += 2.0
                        reason = "description"
            if score <= 0:
                continue
        scored.append(SkillMatch(skill=skill, score=score, reason=reason))

    scored.sort(key=lambda m: (-m.score, -m.skill.priority, m.skill.name))
    # de-dupe by name
    seen: set[str] = set()
    out: list[SkillMatch] = []
    for item in scored:
        if item.skill.name in seen:
            continue
        seen.add(item.skill.name)
        out.append(item)
        if len(out) >= max(1, min(3, int(limit))):
            break
    return out


def format_skills_block(matches: list[SkillMatch]) -> str:
    if not matches:
        return ""
    parts = [
        "## 本轮启用技能（Skills — 必须按技能说明书组织回答，可与 Brain 契约叠加）",
        "说明：技能来自竞赛大脑内置任务包，不是用户附件。优先执行技能中的产出结构与检查清单。",
    ]
    for match in matches:
        skill = match.skill
        body = skill.body
        if len(body) > skill.max_inject_chars:
            body = body[: skill.max_inject_chars] + "\n…(技能正文已截断)"
        parts.append(
            f"### 技能 `{skill.name}`"
            + (f" · /{skill.slash}" if skill.slash else "")
            + f"\n匹配：{match.reason}（score={match.score:.1f}）\n"
            f"{skill.description}\n\n{body}"
        )
    return "\n\n".join(parts)


def apply_skill_tool_gates(plan: Any, matches: list[SkillMatch]) -> list[str]:
    """OR skill tool flags onto a BrainPlan-like object. Returns rationale tags."""
    tags: list[str] = []
    if not matches or plan is None:
        return tags
    for match in matches:
        s = match.skill
        if s.need_scores and not getattr(plan, "need_scores", False):
            plan.need_scores = True
            tags.append(f"skill:{s.name}:scores")
        if s.need_learning and not getattr(plan, "need_learning", False):
            plan.need_learning = True
            tags.append(f"skill:{s.name}:learning")
        if s.need_tasks and not getattr(plan, "need_tasks", False):
            plan.need_tasks = True
            tags.append(f"skill:{s.name}:tasks")
        if s.need_collab and not getattr(plan, "need_collab", False):
            plan.need_collab = True
            tags.append(f"skill:{s.name}:collab")
    return tags


def resolve_skills_for_turn(
    user_text: str,
    *,
    audience: str = "student",
    limit: int = 2,
    catalog_dir: str | None = None,
) -> tuple[list[SkillMatch], str]:
    matches = match_skills(
        user_text, audience=audience, limit=limit, catalog_dir=catalog_dir
    )
    return matches, format_skills_block(matches)


def list_skills_public(*, audience: str = "any") -> list[dict[str, Any]]:
    """For future FE slash menu."""
    audience = (audience or "any").strip().lower()
    rows: list[dict[str, Any]] = []
    for skill in discover_skills():
        if audience != "any" and not _audience_ok(skill, audience):
            continue
        rows.append(
            {
                "name": skill.name,
                "description": skill.description,
                "slash": skill.slash,
                "triggers": list(skill.triggers),
                "audience": skill.audience,
            }
        )
    return rows
