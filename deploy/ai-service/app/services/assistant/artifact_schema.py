"""
产物 JSON Schema（P2 双通道第二段）

聊天正文给人看；可下载文件优先吃结构化 JSON，再渲染。
失败时回退：从 Markdown 启发式抽取 schema，再不行走旧 markdown 渲染。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Schema 形态 ─────────────────────────────────────────────────────
# deck:
# {
#   "type": "deck",
#   "title": str,
#   "subtitle": str?,
#   "slides": [
#     {"layout": "cover|bullets|compare|closing",
#      "title": str,
#      "subtitle": str?,
#      "bullets": [str],
#      "rows": [[str,str,...]]?,  # compare
#      "notes": str?}
#   ]
# }
# plan:
# {
#   "type": "plan",
#   "title": str,
#   "rows": [{"item": str, "detail": str, "owner": str?, "due": str?}]
# }
# doc:
# {
#   "type": "doc",
#   "title": str,
#   "sections": [{"heading": str, "level": 1|2|3, "paras": [str], "bullets": [str]}]
# }


def _clip(s: Any, n: int) -> str:
    t = re.sub(r"\s+", " ", str(s or "")).strip()
    return t[:n] if len(t) > n else t


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", t, re.I)
    if m:
        return m.group(1).strip()
    return t


def extract_json_object(text: str) -> dict[str, Any] | None:
    """从模型输出中抠出第一个 JSON 对象。"""
    raw = _strip_fences(text)
    # 直接 parse
    for candidate in (raw, raw[raw.find("{") : raw.rfind("}") + 1] if "{" in raw else ""):
        if not candidate or not candidate.strip().startswith("{"):
            continue
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    # 宽松：找平衡大括号
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(raw)):
        ch = raw[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(raw[start : i + 1])
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    return None
    return None


def normalize_deck(data: dict[str, Any], *, fallback_title: str = "路演PPT") -> dict[str, Any]:
    title = _clip(data.get("title") or fallback_title, 80) or fallback_title
    subtitle = _clip(data.get("subtitle") or "", 120)
    slides_in = data.get("slides") or data.get("pages") or []
    slides: list[dict[str, Any]] = []
    if not isinstance(slides_in, list):
        slides_in = []

    for i, s in enumerate(slides_in[:16]):
        if not isinstance(s, dict):
            continue
        layout = str(s.get("layout") or "bullets").lower().strip()
        if layout not in ("cover", "bullets", "compare", "closing", "section"):
            layout = "bullets"
        st = _clip(s.get("title") or s.get("heading") or f"第{i+1}页", 60)
        if re.search(r"制作建议|如需我|核心建议|结构与内容", st):
            continue
        bullets_raw = s.get("bullets") or s.get("points") or s.get("items") or []
        bullets: list[str] = []
        if isinstance(bullets_raw, list):
            for b in bullets_raw:
                bb = _clip(b, 48)
                if bb and not re.match(r"^(如需我|请告知)", bb):
                    bullets.append(bb)
        bullets = bullets[:6]

        rows: list[list[str]] = []
        raw_rows = s.get("rows") or s.get("table") or []
        if isinstance(raw_rows, list):
            for row in raw_rows[:8]:
                if isinstance(row, (list, tuple)):
                    rows.append([_clip(c, 24) for c in row[:4]])
                elif isinstance(row, dict):
                    rows.append([_clip(v, 24) for v in list(row.values())[:4]])

        if layout == "compare" and not rows and bullets:
            # bullets 可能是「A | B | C」
            for b in bullets:
                if "·" in b or "|" in b or "／" in b:
                    parts = re.split(r"[·|／]", b)
                    rows.append([_clip(p, 24) for p in parts if p.strip()][:4])
            if rows:
                bullets = []

        # 标题含封面/致谢时纠正 layout
        if re.search(r"^封面|封面页", st) and layout == "bullets":
            layout = "cover"
        # 仅标题整体是致谢/收尾时改 closing，避免「农业问答」误伤
        if re.search(r"^(致谢|谢谢|结束|收尾|Q\s*&\s*A)($|[：:\s])", st, re.I) and layout == "bullets":
            layout = "closing"
        if layout == "cover" and not st:
            st = title
        if not st and not bullets and not rows:
            continue
        slides.append(
            {
                "layout": layout if layout != "section" else "bullets",
                "title": st or "内容",
                "subtitle": _clip(s.get("subtitle") or "", 80),
                "bullets": bullets,
                "rows": rows,
                "notes": _clip(s.get("notes") or "", 200),
            }
        )

    # 保证有封面（若首屏已是 cover 或标题即项目名则不重复）
    if slides and slides[0]["layout"] != "cover":
        first_title = slides[0].get("title") or ""
        if re.search(r"封面", first_title):
            slides[0]["layout"] = "cover"
            if not slides[0].get("subtitle"):
                slides[0]["subtitle"] = subtitle or "竞赛大脑 · 路演提纲"
        else:
            slides.insert(
                0,
                {
                    "layout": "cover",
                    "title": title,
                    "subtitle": subtitle or "竞赛大脑 · 路演提纲",
                    "bullets": [],
                    "rows": [],
                    "notes": "",
                },
            )
    if not slides:
        slides = [
            {
                "layout": "cover",
                "title": title,
                "subtitle": subtitle or "竞赛大脑 · 路演提纲",
                "bullets": [],
                "rows": [],
                "notes": "",
            },
            {
                "layout": "bullets",
                "title": "内容要点",
                "subtitle": "",
                "bullets": ["（结构化失败，请重试生成）"],
                "rows": [],
                "notes": "",
            },
        ]

    return {"type": "deck", "title": title, "subtitle": subtitle, "slides": slides[:15]}


def normalize_plan(data: dict[str, Any], *, fallback_title: str = "训练计划") -> dict[str, Any]:
    title = _clip(data.get("title") or fallback_title, 80) or fallback_title
    rows_in = data.get("rows") or data.get("items") or data.get("tasks") or []
    rows: list[dict[str, str]] = []
    if isinstance(rows_in, list):
        for r in rows_in[:40]:
            if isinstance(r, dict):
                item = _clip(r.get("item") or r.get("task") or r.get("name") or r.get("title"), 40)
                detail = _clip(r.get("detail") or r.get("desc") or r.get("说明") or r.get("goal"), 80)
                owner = _clip(r.get("owner") or r.get("负责人") or "", 20)
                due = _clip(r.get("due") or r.get("day") or r.get("when") or "", 20)
            elif isinstance(r, str):
                if "：" in r:
                    a, b = r.split("：", 1)
                    item, detail = _clip(a, 40), _clip(b, 80)
                elif ":" in r:
                    a, b = r.split(":", 1)
                    item, detail = _clip(a, 40), _clip(b, 80)
                else:
                    item, detail = _clip(r, 40), ""
                owner, due = "", ""
            else:
                continue
            if item:
                rows.append({"item": item, "detail": detail, "owner": owner, "due": due})
    if not rows:
        rows = [{"item": "（暂无条目）", "detail": "可根据对话继续完善", "owner": "", "due": ""}]
    return {"type": "plan", "title": title, "rows": rows}


def normalize_doc(data: dict[str, Any], *, fallback_title: str = "竞赛助手文稿") -> dict[str, Any]:
    title = _clip(data.get("title") or fallback_title, 80) or fallback_title
    secs_in = data.get("sections") or []
    sections: list[dict[str, Any]] = []
    if isinstance(secs_in, list):
        for s in secs_in[:30]:
            if not isinstance(s, dict):
                continue
            heading = _clip(s.get("heading") or s.get("title") or "", 80)
            level = int(s.get("level") or 2)
            level = 1 if level <= 1 else 2 if level == 2 else 3
            paras = []
            for p in s.get("paras") or s.get("paragraphs") or []:
                pp = _clip(p, 400)
                if pp:
                    paras.append(pp)
            bullets = []
            for b in s.get("bullets") or []:
                bb = _clip(b, 120)
                if bb:
                    bullets.append(bb)
            if heading or paras or bullets:
                sections.append(
                    {
                        "heading": heading,
                        "level": level,
                        "paras": paras[:12],
                        "bullets": bullets[:12],
                    }
                )
    if not sections:
        sections = [{"heading": title, "level": 1, "paras": ["（暂无正文）"], "bullets": []}]
    return {"type": "doc", "title": title, "sections": sections}


def normalize_artifact(
    data: dict[str, Any] | None,
    *,
    artifact: str,
    fallback_title: str,
) -> dict[str, Any] | None:
    if not data or not isinstance(data, dict):
        return None
    t = str(data.get("type") or "").lower()
    if artifact == "pptx" or t == "deck":
        return normalize_deck(data, fallback_title=fallback_title)
    if artifact == "xlsx" or t == "plan":
        return normalize_plan(data, fallback_title=fallback_title)
    if artifact in ("docx", "md", "pdf") or t == "doc":
        return normalize_doc(data, fallback_title=fallback_title)
    # 猜测
    if "slides" in data:
        return normalize_deck(data, fallback_title=fallback_title)
    if "rows" in data or "tasks" in data:
        return normalize_plan(data, fallback_title=fallback_title)
    if "sections" in data:
        return normalize_doc(data, fallback_title=fallback_title)
    return None


# ── Markdown → schema 回退 ──────────────────────────────────────────


def deck_from_markdown(text: str, *, title: str = "路演PPT") -> dict[str, Any]:
    from app.services.assistant.brain import prepare_artifact_markdown

    cleaned = prepare_artifact_markdown(text, artifact="pptx", title=title)
    slides: list[dict[str, Any]] = []
    cur_title = ""
    bullets: list[str] = []
    deck_title = title

    def flush():
        nonlocal cur_title, bullets
        if not cur_title and not bullets:
            return
        if cur_title and re.search(r"制作建议|核心建议", cur_title):
            cur_title, bullets = "", []
            return
        slides.append(
            {
                "layout": "bullets",
                "title": cur_title or "内容",
                "subtitle": "",
                "bullets": bullets[:6],
                "rows": [],
                "notes": "",
            }
        )
        cur_title, bullets = "", []

    for line in cleaned.split("\n"):
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^(#{1,3})\s+(.+)$", s)
        if m:
            level = len(m.group(1))
            h = re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(2)).strip()
            if level == 1 and not slides and not cur_title:
                deck_title = h
                continue
            flush()
            cur_title = h
            continue
        if re.match(r"^[-*]\s+|^\d+[\.、]\s*", s):
            s = re.sub(r"^[-*]\s+", "", s)
            s = re.sub(r"^\d+[\.、]\s*", "", s)
            s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
            if s:
                bullets.append(_clip(s, 48))
            continue
    flush()
    return normalize_deck(
        {"title": deck_title, "subtitle": "竞赛大脑 · 路演提纲", "slides": slides},
        fallback_title=title,
    )


def plan_from_markdown(text: str, *, title: str = "训练计划") -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for line in (text or "").split("\n"):
        s = line.strip()
        if not s or s.startswith("#"):
            if s.startswith("#"):
                title = re.sub(r"^#+\s*", "", s)[:40] or title
            continue
        s = re.sub(r"^[-*]\s+", "", s)
        s = re.sub(r"^\d+[\.、]\s*", "", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        if len(s) < 2:
            continue
        if "：" in s:
            a, b = s.split("：", 1)
            rows.append({"item": _clip(a, 40), "detail": _clip(b, 80), "owner": "", "due": ""})
        else:
            rows.append({"item": _clip(s, 40), "detail": "", "owner": "", "due": ""})
    return normalize_plan({"title": title, "rows": rows}, fallback_title=title)


def doc_from_markdown(text: str, *, title: str = "竞赛助手文稿") -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    def ensure():
        nonlocal cur
        if cur is None:
            cur = {"heading": "", "level": 2, "paras": [], "bullets": []}

    for line in (text or "").replace("\r\n", "\n").split("\n"):
        s = line.rstrip()
        st = s.strip()
        if not st:
            continue
        m = re.match(r"^(#{1,3})\s+(.+)$", st)
        if m:
            if cur and (cur["heading"] or cur["paras"] or cur["bullets"]):
                sections.append(cur)
            cur = {
                "heading": re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(2)).strip(),
                "level": len(m.group(1)),
                "paras": [],
                "bullets": [],
            }
            continue
        ensure()
        assert cur is not None
        if re.match(r"^[-*]\s+|^\d+[\.、]\s*", st):
            st2 = re.sub(r"^[-*]\s+", "", st)
            st2 = re.sub(r"^\d+[\.、]\s*", "", st2)
            cur["bullets"].append(_clip(st2, 120))
        else:
            cur["paras"].append(_clip(st, 400))
    if cur and (cur["heading"] or cur["paras"] or cur["bullets"]):
        sections.append(cur)
    if sections and not any(s.get("heading") for s in sections[:1]):
        pass
    return normalize_doc({"title": title, "sections": sections}, fallback_title=title)


def schema_from_markdown(text: str, *, artifact: str, title: str) -> dict[str, Any]:
    if artifact == "pptx":
        return deck_from_markdown(text, title=title)
    if artifact == "xlsx":
        return plan_from_markdown(text, title=title)
    return doc_from_markdown(text, title=title)


# ── 二次 LLM ────────────────────────────────────────────────────────


def build_schema_messages(
    *,
    artifact: str,
    title: str,
    answer_text: str,
    user_text: str = "",
    project_hint: str | None = None,
) -> list[dict[str, str]]:
    """构造「只输出 JSON」的二次调用 messages。"""
    project = project_hint or title
    body = (answer_text or "")[:12000]
    user_snip = (user_text or "")[:500]

    if artifact == "pptx":
        system = (
            "你是竞赛路演 PPT 结构化引擎。把输入整理为严格 JSON（不要 Markdown，不要解释）。\n"
            "Schema:\n"
            '{"type":"deck","title":"...","subtitle":"...",'
            '"slides":[{"layout":"cover|bullets|compare|closing","title":"...",'
            '"subtitle":"","bullets":["..."],"rows":[["维","A","B"]],"notes":""}]}\n'
            "规则：\n"
            "1. 12～14 页；每页 layout 正确；cover 一页开头；closing 一页结尾。\n"
            "2. bullets 每页 3～6 条，每条 ≤28 字；禁止客服句、禁止「制作建议」页。\n"
            "3. 功能演示必须拆成多页，禁止「第5-8页」合并。\n"
            "4. 对比用 layout=compare + rows。\n"
            "5. title 使用项目名，不要用「竞赛助手提纲」。\n"
            "6. 只输出一个 JSON 对象。"
        )
        user = (
            f"项目：{project}\n用户原话：{user_snip}\n\n"
            f"以下是助手已写的内容，请提炼为 deck JSON：\n\n{body}"
        )
    elif artifact == "xlsx":
        system = (
            "你是备赛计划结构化引擎。只输出 JSON，不要解释。\n"
            "Schema:\n"
            '{"type":"plan","title":"...",'
            '"rows":[{"item":"事项","detail":"说明","owner":"","due":"Day1"}]}\n'
            "规则：8～20 条可执行任务；item 短、detail 含目标/验收；只输出 JSON。"
        )
        user = f"标题偏好：{title}\n用户原话：{user_snip}\n\n内容：\n{body}"
    else:
        system = (
            "你是竞赛文稿结构化引擎。只输出 JSON。\n"
            "Schema:\n"
            '{"type":"doc","title":"...",'
            '"sections":[{"heading":"...","level":1|2|3,"paras":["..."],"bullets":["..."]}]}\n'
            "规则：保留可交付正文；去掉客服套话；level 层次清晰；只输出 JSON。"
        )
        user = f"标题偏好：{title}\n用户原话：{user_snip}\n\n内容：\n{body}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_artifact_schema(
    *,
    client: Any,
    model: str,
    artifact: str,
    title: str,
    answer_text: str,
    user_text: str = "",
    project_hint: str | None = None,
    temperature: float = 0.2,
) -> tuple[dict[str, Any] | None, str]:
    """
    二次 LLM → schema。
    返回 (schema|None, source) source=llm|markdown_fallback|none
    """
    messages = build_schema_messages(
        artifact=artifact,
        title=title,
        answer_text=answer_text,
        user_text=user_text,
        project_hint=project_hint,
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            temperature=temperature,
        )
        content = ""
        if resp.choices:
            content = resp.choices[0].message.content or ""
        raw = extract_json_object(content)
        schema = normalize_artifact(raw, artifact=artifact, fallback_title=title)
        if schema:
            # 基本质量门：deck 至少 4 页
            if artifact == "pptx" and len(schema.get("slides") or []) < 3:
                raise ValueError("deck too short")
            if artifact == "xlsx" and len(schema.get("rows") or []) < 2:
                raise ValueError("plan too short")
            return schema, "llm"
    except Exception as e:
        logger.warning("artifact schema LLM failed: %s", e)

    try:
        fb = schema_from_markdown(answer_text, artifact=artifact, title=title)
        return fb, "markdown_fallback"
    except Exception as e:
        logger.warning("artifact markdown fallback failed: %s", e)
        return None, "none"


def schema_to_markdown(schema: dict[str, Any]) -> str:
    """把 schema 转回可读 Markdown（给 .md 附件与聊天摘要）。"""
    t = schema.get("type")
    if t == "deck":
        lines = [f"# {schema.get('title') or '路演PPT'}"]
        if schema.get("subtitle"):
            lines.append(f"\n{schema['subtitle']}\n")
        for i, s in enumerate(schema.get("slides") or [], 1):
            lines.append(f"\n## {s.get('title') or f'第{i}页'}")
            if s.get("subtitle"):
                lines.append(s["subtitle"])
            for b in s.get("bullets") or []:
                lines.append(f"- {b}")
            for row in s.get("rows") or []:
                if isinstance(row, list):
                    lines.append("- " + " · ".join(str(c) for c in row))
        return "\n".join(lines).strip() + "\n"
    if t == "plan":
        lines = [f"# {schema.get('title') or '计划'}\n"]
        for i, r in enumerate(schema.get("rows") or [], 1):
            item = r.get("item") or ""
            detail = r.get("detail") or ""
            due = r.get("due") or ""
            owner = r.get("owner") or ""
            extra = " / ".join(x for x in (due, owner) if x)
            if detail:
                lines.append(f"{i}. **{item}**：{detail}" + (f"（{extra}）" if extra else ""))
            else:
                lines.append(f"{i}. **{item}**" + (f"（{extra}）" if extra else ""))
        return "\n".join(lines).strip() + "\n"
    # doc
    lines = [f"# {schema.get('title') or '文稿'}\n"]
    for s in schema.get("sections") or []:
        h = s.get("heading") or ""
        level = int(s.get("level") or 2)
        if h:
            lines.append("#" * min(level, 3) + " " + h)
        for p in s.get("paras") or []:
            lines.append(p)
            lines.append("")
        for b in s.get("bullets") or []:
            lines.append(f"- {b}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
