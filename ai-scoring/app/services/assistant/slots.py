"""
会话级 Slot 记忆（P3）

从多轮对话 + 可选持久化 context 中维护：
- project_name / track / team_name
- last_artifact / prefer_scores
- report_mentioned / key_facts（短）

不依赖向量库；规则抽取优先，稳定、零延迟。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SessionSlots:
    project_name: str | None = None
    track: str | None = None
    team_name: str | None = None
    last_artifact: str | None = None  # pptx|docx|xlsx|pdf|md
    prefer_scores: bool = False
    report_title: str | None = None
    domain: str | None = None  # roadshow|script|plan|score|docs
    key_facts: list[str] = field(default_factory=list)
    updated_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["key_facts"] = list(self.key_facts or [])[:8]
        d["updated_keys"] = list(self.updated_keys or [])[:12]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SessionSlots":
        if not data or not isinstance(data, dict):
            return cls()
        facts = data.get("key_facts") or []
        if not isinstance(facts, list):
            facts = []
        return cls(
            project_name=_s(data.get("project_name") or data.get("projectName"), 40),
            track=_s(data.get("track"), 40),
            team_name=_s(data.get("team_name") or data.get("teamName"), 40),
            last_artifact=_s(data.get("last_artifact") or data.get("lastArtifact"), 16),
            prefer_scores=bool(data.get("prefer_scores") or data.get("preferScores")),
            report_title=_s(data.get("report_title") or data.get("reportTitle"), 60),
            domain=_s(data.get("domain"), 20),
            key_facts=[_s(x, 80) for x in facts if _s(x, 80)][:8],
            updated_keys=[],
        )


def _s(v: Any, n: int) -> str | None:
    if v is None:
        return None
    t = re.sub(r"\s+", " ", str(v)).strip()
    if not t:
        return None
    return t[:n]


def _set(slots: SessionSlots, key: str, value: str | None, *, force: bool = False) -> None:
    if not value:
        return
    cur = getattr(slots, key, None)
    if cur and not force and key not in ("key_facts",):
        # 已有值时，仅当新值更长/更具体才覆盖
        if len(value) < len(str(cur)):
            return
    setattr(slots, key, value)
    if key not in slots.updated_keys:
        slots.updated_keys.append(key)


_PROJECT_PATTERNS = [
    re.compile(r"(?:项目(?:名称|名)?|作品(?:名称|名)?)\s*[：:]\s*[《\"'「]?([^《\"'」\n]{2,40})"),
    re.compile(
        r"(?:带来的是|项目是|我们的项目是|作品是)\s*[「\"'《]?"
        r"([\u4e00-\u9fffA-Za-z0-9]{2,20}(?:系统|平台|方案))"
    ),
    re.compile(r"《([\u4e00-\u9fffA-Za-z0-9]{2,24}(?:系统|平台|方案))》"),
    re.compile(r"(智能[\u4e00-\u9fff]{2,16}(?:系统|平台))"),
]

_TEAM_PAT = re.compile(r"(?:团队(?:名称|名)?)\s*[：:：]\s*[「\"']?([\u4e00-\u9fffA-Za-z0-9]{2,24})")
_TRACK_PAT = re.compile(r"(?:赛道|赛项)\s*[：:：]\s*([\u4e00-\u9fffA-Za-z0-9（）()]{2,30})")
_REPORT_PAT = re.compile(r"《([^》]*?报告[^》]*)》|(路演评分报告[_\-\w]*)")
_FACT_PAT = re.compile(
    r"(?:病害|成本|效率|节水|下降|提升|降低)[^\n。]{0,24}(?:\d+\s*%|[\d.]+\s*万)?"
)


def _clean_project_name(name: str) -> str | None:
    name = (name or "").strip().strip("《》\"'「」")
    if not name or re.search(r"^(项目|作品|系统)$", name):
        return None
    if re.search(r"报告|评分|依据", name):
        return None
    # 拒绝技术占位词 / 编号类噪声（避免把 requestId、团队编号 当成项目名）
    if re.search(
        r"编号|requestId|sessionId|teamId|userId|真实ID|占位|todo|id\s*=",
        name,
        re.I,
    ):
        return None
    if re.fullmatch(r"[\d\s/\-_|]+", name):
        return None
    # 去掉前缀噪声
    name = re.sub(r"^(项目是|作品是|我们的)", "", name).strip()
    if len(name) < 2:
        return None
    return name[:40]


def extract_from_text(text: str, slots: SessionSlots | None = None) -> SessionSlots:
    slots = slots or SessionSlots()
    t = text or ""
    if not t.strip():
        return slots

    # 报告优先（避免被当成项目名）
    m = _REPORT_PAT.search(t)
    if m:
        title = (m.group(1) or m.group(2) or "").strip().strip("《》\"'")
        if title and "报告" in title:
            _set(slots, "report_title", title[:60])
            slots.prefer_scores = True
            if "prefer_scores" not in slots.updated_keys:
                slots.updated_keys.append("prefer_scores")

    for pat in _PROJECT_PATTERNS:
        m = pat.search(t)
        if m:
            name = _clean_project_name(m.group(1))
            if name:
                _set(slots, "project_name", name)
                break

    m = _TEAM_PAT.search(t)
    if m:
        _set(slots, "team_name", m.group(1).strip())

    m = _TRACK_PAT.search(t)
    if m:
        _set(slots, "track", m.group(1).strip())

    if re.search(r"\bpptx?\b|幻灯片", t, re.I):
        slots.last_artifact = "pptx"
        if "last_artifact" not in slots.updated_keys:
            slots.updated_keys.append("last_artifact")
    elif re.search(r"excel|xlsx|训练计划", t, re.I):
        slots.last_artifact = "xlsx"
        if "last_artifact" not in slots.updated_keys:
            slots.updated_keys.append("last_artifact")
    elif re.search(r"docx?|\bword\b|讲稿|申报书", t, re.I):
        slots.last_artifact = "docx"
        if "last_artifact" not in slots.updated_keys:
            slots.updated_keys.append("last_artifact")

    if re.search(r"路演|答辩", t):
        slots.domain = "roadshow"
    elif re.search(r"评分|扣分", t):
        slots.domain = "score"
    elif re.search(r"训练计划|周计划", t):
        slots.domain = "plan"

    for fm in _FACT_PAT.finditer(t):
        fact = _s(fm.group(0), 80)
        if fact and fact not in slots.key_facts:
            slots.key_facts.append(fact)
            if len(slots.key_facts) >= 8:
                break

    return slots


def merge_slots(*parts: SessionSlots | dict | None) -> SessionSlots:
    """后者覆盖前者的非空字段；key_facts 去重合并。"""
    out = SessionSlots()
    for p in parts:
        if p is None:
            continue
        s = p if isinstance(p, SessionSlots) else SessionSlots.from_dict(p)
        for key in (
            "project_name",
            "track",
            "team_name",
            "last_artifact",
            "report_title",
            "domain",
        ):
            val = getattr(s, key, None)
            if val:
                setattr(out, key, val)
        if s.prefer_scores:
            out.prefer_scores = True
        for f in s.key_facts or []:
            if f and f not in out.key_facts:
                out.key_facts.append(f)
        out.key_facts = out.key_facts[:8]
        for k in s.updated_keys or []:
            if k not in out.updated_keys:
                out.updated_keys.append(k)
    return out


def extract_from_messages(
    messages: list[dict[str, Any]] | None,
    *,
    prior: SessionSlots | dict | None = None,
) -> SessionSlots:
    slots = SessionSlots.from_dict(prior.to_dict() if isinstance(prior, SessionSlots) else prior)
    for m in messages or []:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        if role not in ("user", "assistant") or not content:
            continue
        # 用户句优先 force 项目名
        before = slots.project_name
        extract_from_text(content, slots)
        if role == "user" and slots.project_name and slots.project_name != before:
            pass
    return slots


def slots_system_block(slots: SessionSlots) -> str:
    """注入 system 的会话记忆块。"""
    if not any(
        [
            slots.project_name,
            slots.track,
            slots.team_name,
            slots.report_title,
            slots.last_artifact,
            slots.key_facts,
            slots.prefer_scores,
        ]
    ):
        return ""
    lines = ["", "## 会话记忆 Slot（跨轮有效，请沿用，勿遗忘或改名）"]
    if slots.project_name:
        lines.append(f"- 项目名称：{slots.project_name}")
    if slots.team_name:
        lines.append(f"- 团队：{slots.team_name}")
    if slots.track:
        lines.append(f"- 赛道：{slots.track}")
    if slots.report_title:
        lines.append(f"- 关联报告：{slots.report_title}")
    if slots.last_artifact:
        lines.append(f"- 最近产物偏好：{slots.last_artifact}")
    if slots.prefer_scores:
        lines.append("- 用户本会话关注评分/报告，指代「报告」时优先联想到评分报告")
    if slots.domain:
        lines.append(f"- 当前领域：{slots.domain}")
    if slots.key_facts:
        lines.append("- 已锁定事实（勿篡改数字）：")
        for f in slots.key_facts[:6]:
            lines.append(f"  · {f}")
    lines.append("- 指代「这个项目 / 这份报告 / 继续」时必须使用以上 Slot。")
    return "\n".join(lines)
