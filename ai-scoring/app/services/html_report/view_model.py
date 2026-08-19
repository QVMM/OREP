"""把评分 JSON 收成 HTML 报告用的视图，不发明分数。"""
from __future__ import annotations

import base64
import html
import os
import re
from datetime import datetime
from pathlib import Path

from app.services import report_service as rs
from app.services.html_report.bands import OFFICIAL_ITEM_NAMES, band_label

_OFFICIAL_ITEM_COUNTS = {
    "skill_level": 5,
    "professionalism": 3,
    "application_value": 3,
    "teamwork": 2,
    "innovation": 2,
}


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _pct(score, max_score) -> float:
    try:
        s = float(score or 0)
        m = float(max_score or 0)
    except (TypeError, ValueError):
        return 0.0
    if m <= 0:
        return 0.0
    return max(0.0, min(100.0, s * 100.0 / m))


def _fmt_score(value, digits=1) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(n - round(n)) < 1e-6:
        return str(int(round(n)))
    return f"{n:.{digits}f}"


def _num(value, default=0.0) -> float:
    if value is None or value == "" or value == "—":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _share_tenths(delta: float, weights: list[float]) -> list[float]:
    total_w = sum(max(0.0, w) for w in weights)
    if total_w <= 0 or delta <= 0:
        return [0.0] * len(weights)
    tenths = int(round(delta * 10))
    raw = [max(0.0, w) / total_w * tenths for w in weights]
    floors = [int(x) for x in raw]
    remain = tenths - sum(floors)
    order = sorted(
        range(len(raw)),
        key=lambda i: (raw[i] - floors[i], weights[i]),
        reverse=True,
    )
    for i in order:
        if remain <= 0:
            break
        if weights[i] <= 0:
            continue
        floors[i] += 1
        remain -= 1
    return [f / 10.0 for f in floors]


def _item_weight(name: str) -> float:
    text = str(name or "")
    if "熟练" in text:
        return 0.55
    if "规范" in text:
        return 0.35
    if "讲解" in text or "现场" in text:
        return 0.10
    return 0.0


def _distribute_skill_credit(rows: list[dict], delta: float) -> None:
    if delta <= 0.05 or not rows:
        return
    rooms = []
    weights = []
    for row in rows:
        max_s = _num(row.get("max_score"))
        cur = _num(row.get("score"))
        room = max(0.0, round(max_s - cur, 1)) if max_s else 0.0
        weight = _item_weight(row.get("name") or "") if room > 0 else 0.0
        rooms.append(room)
        weights.append(weight)
    if sum(weights) <= 0:
        return
    shares = _share_tenths(round(delta, 1), weights)
    leftover = 0.0
    for i, row in enumerate(rows):
        add = round(min(shares[i], rooms[i]), 1)
        leftover = round(leftover + shares[i] - add, 1)
        if add <= 0:
            continue
        new_s = round(_num(row.get("score")) + add, 1)
        row["score"] = _fmt_score(new_s)
        row["band"] = band_label(row.get("name") or "", new_s) or row.get("band") or ""
        rooms[i] = round(rooms[i] - add, 1)
    if leftover < 0.05:
        return
    for i, row in enumerate(rows):
        while leftover >= 0.05 and rooms[i] >= 0.05:
            new_s = round(_num(row.get("score")) + 0.1, 1)
            row["score"] = _fmt_score(new_s)
            row["band"] = band_label(row.get("name") or "", new_s) or row.get("band") or ""
            rooms[i] = round(rooms[i] - 0.1, 1)
            leftover = round(leftover - 0.1, 1)


def _reconcile_dimensions(result: dict, dimensions: list[dict]) -> list[dict]:
    visual = ((result.get("ai_score") or {}).get("_skill_visual_rescore") or {})
    for dim in dimensions:
        rows = dim.get("item_rows") or []
        if not rows:
            continue
        item_sum = round(sum(_num(row.get("score")) for row in rows), 1)
        complete = len(rows) >= _OFFICIAL_ITEM_COUNTS.get(dim["key"], 10**9)
        if dim["key"] == "skill_level" and isinstance(visual, dict) and visual.get("after") is not None:
            target = round(_num(visual.get("after")), 1)
            if target > item_sum + 0.05:
                _distribute_skill_credit(rows, target - item_sum)
                item_sum = round(sum(_num(row.get("score")) for row in rows), 1)
        if complete:
            dim["score"] = _fmt_score(item_sum)
            dim["pct"] = _pct(item_sum, _num(dim.get("max_score")))
    return dimensions


def _aligned_overall(ai_overall: float, dimensions: list[dict]) -> float:
    if not dimensions:
        return ai_overall
    for dim in dimensions:
        need = _OFFICIAL_ITEM_COUNTS.get(dim["key"])
        if not need or len(dim.get("item_rows") or []) < need:
            return ai_overall
    return round(sum(_num(dim.get("score")) for dim in dimensions), 1)


def _score_note(result: dict) -> str:
    visual = ((result.get("ai_score") or {}).get("_skill_visual_rescore") or {})
    if not isinstance(visual, dict):
        return ""
    try:
        delta = float(visual.get("delta") or 0)
    except (TypeError, ValueError):
        return ""
    if delta <= 0:
        return ""
    before = _fmt_score(visual.get("before"))
    after = _fmt_score(visual.get("after"))
    return f"现场出现开发工具界面，技能水平由 {before} 调至 {after}，15 个观测点已按同一增量对齐。"


def _item_gaps(dimensions: list[dict]) -> dict[str, float]:
    gaps = {}
    for dim in dimensions:
        for row in dim.get("item_rows") or []:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            gaps[name] = round(_num(row.get("max_score")) - _num(row.get("score")), 1)
    return gaps


def _rewrite_gap_numbers(text: str, gaps: dict[str, float]) -> str:
    out = str(text or "")
    if not out or not gaps:
        return out
    for name, gap in sorted(gaps.items(), key=lambda kv: len(kv[0]), reverse=True):
        shown = _fmt_score(gap)
        out = re.sub(
            rf"({re.escape(name)}[^（(\n]{{0,48}})[（(][-−]?\d+(?:\.\d+)?[）)]",
            rf"\g<1>（-{shown}）",
            out,
        )
        out = re.sub(
            rf"({re.escape(name)}失分)\s*\d+(?:\.\d+)?",
            rf"\g<1>{shown}",
            out,
        )
    return out


def _logo_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [
        here.parents[3] / "assets" / "brand",
        here.parents[4] / "frontend" / "user" / "public" / "brand",
        here.parents[4] / "assets",
        Path(rs._brand_logo_path() or "").parent,
    ]
    names = (
        "competition-brain-mark.svg",
        "competition-brain-mark.png",
        "competition-brain-logo.svg",
        "competition-brain-logo.png",
        "启发竞赛大脑-logo.svg",
        "qifa-jixue-logo.png",
    )
    out = []
    for root in roots:
        if not root:
            continue
        for name in names:
            path = root / name
            if path.is_file() and path not in out:
                out.append(path)
    return out


def _file_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    ext = path.suffix.lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/png"
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _logo_data_uri() -> str:
    for path in _logo_candidates():
        if path.name.startswith("competition-brain-mark") and path.suffix.lower() == ".svg":
            return _file_data_uri(path)
    for path in _logo_candidates():
        if path.suffix.lower() == ".svg":
            return _file_data_uri(path)
    for path in _logo_candidates():
        return _file_data_uri(path)
    return ""


def _publisher_logo_data_uri() -> str:
    for path in _logo_candidates():
        if path.name == "qifa-jixue-logo.png":
            return _file_data_uri(path)
    return ""


def _header_mark_data_uri() -> str:
    """页眉只用 Q 标小 PNG，四个字用网页字体画，避免 lockup 被压扁。"""
    for path in _logo_candidates():
        if path.name == "competition-brain-mark.png":
            return _file_data_uri(path)
    for path in _logo_candidates():
        if path.suffix.lower() == ".png" and "qifa-jixue" not in path.name and "logo" not in path.name:
            return _file_data_uri(path)
    return ""


def _cover_meta(result: dict) -> dict:
    project = rs._resolve_project_name(result)
    track = (
        result.get("track")
        or result.get("track_name")
        or (result.get("project_info") or {}).get("track")
        or ""
    )
    meeting_id = result.get("meeting_id", "—")
    session_no = result.get("session_no") or result.get("sessionNo") or ""
    duration_s = (result.get("asr") or {}).get("duration") or result.get("duration") or 0
    try:
        duration_s = float(duration_s)
    except (TypeError, ValueError):
        duration_s = 0
    duration_txt = f"{duration_s / 60:.1f} 分钟" if duration_s > 0 else "—"
    completed = result.get("completed_at", "")
    if completed:
        try:
            dt = datetime.fromisoformat(str(completed).replace("Z", "+00:00").split("+")[0])
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = str(completed)[:10]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    report_type = "AI 官方五维评分复盘"
    if rs._jury_enabled(result) and rs._real_jury_package(result):
        report_type = "AI 评分流 + 评审团 + 多模态复盘"
    if session_no:
        session_txt = str(session_no)
    elif str(meeting_id) not in {"", "—", "None"}:
        session_txt = f"第 {meeting_id} 场"
    else:
        session_txt = "—"
    return {
        "project": project or "—",
        "track": track or "—",
        "session": session_txt,
        "duration": duration_txt,
        "report_type": report_type,
        "date": date_str,
        "meeting_id": str(meeting_id),
    }


def _student_text(text: str) -> str:
    t = str(text or "")
    t = re.sub(r"(\d+(?:\.\d+)?)\s*wpm", r"\1字/分", t, flags=re.I)
    t = t.replace("speech_rate", "语速").replace("filler_rate", "填充词占比")
    t = t.replace("pause最长", "最长停顿")
    t = re.sub(r"\bpause\b", "停顿", t)
    t = re.sub(r"根据梯度规则扣[\d.]+分[。.]?", "", t)
    t = re.sub(r"故证据等级为E\d[。.]?", "", t)
    t = re.sub(r"证据等级为E\d[，。.]?", "", t)
    t = re.sub(r"达到substantial水平", "结构完整", t)
    t = re.sub(r"故为substantial[。.]?", "", t)
    t = t.replace("substantial。", "").replace("substantial", "")
    t = t.replace("。；", "；").replace("；。", "。")
    t = re.sub(r"[，、]\s*$", "。", t)
    t = re.sub(r"技能熟练度维度", "技能水平", t)
    return t.strip()


def _item_name(raw) -> str:
    name = str(raw or "").strip()
    if name in OFFICIAL_ITEM_NAMES:
        return name
    if name == "技能水平":
        return "技能熟练度"
    return name or "细项"


def _rule_observations(result: dict) -> list[dict]:
    shadow = result.get("rule_engine_shadow") or {}
    rows = [o for o in (shadow.get("observations") or []) if isinstance(o, dict)]
    if rows:
        return rows
    ee = result.get("evidence_extraction") or {}
    return [o for o in (ee.get("observationEvidence") or []) if isinstance(o, dict)]


def _ratio_level(score, max_score) -> str:
    ceiling = _num(max_score)
    if ceiling <= 0:
        return ""
    ratio = _num(score) / ceiling
    if ratio >= 0.65:
        return "基本站得住"
    if ratio >= 0.35:
        return "偏弱"
    return "还缺"


def _engine_level(code, score=None, max_score=None) -> str:
    by_score = _ratio_level(score, max_score) if max_score not in (None, "", "—") else ""
    if by_score:
        return by_score
    text = str(code or "").upper()
    if text in {"E0"}:
        return "还缺"
    if text in {"E1", "E2"}:
        return "偏弱"
    if text in {"E3", "E4", "E5"}:
        return "站得住"
    return _evidence_level(code)


def _obs_to_item(obs: dict) -> dict:
    name = _item_name(obs.get("observationName") or obs.get("name") or "细项")
    score = obs.get("finalScore")
    if score is None:
        score = obs.get("score", obs.get("suggestedBaseScore"))
    max_score = obs.get("maxScore", obs.get("max_score"))
    reason = obs.get("evidenceReason") or obs.get("reason") or obs.get("modelReason") or ""
    gap = ""
    tmpl = obs.get("trainingTaskTemplate") or {}
    if isinstance(tmpl, dict):
        gap = str(tmpl.get("action") or "")
    if not gap:
        miss = obs.get("missingEvidence") or obs.get("requiredInfo") or []
        if isinstance(miss, list) and miss:
            gap = "还缺：" + "、".join(str(x) for x in miss[:4])
    return {
        "name": name,
        "score": _fmt_score(score),
        "max_score": _fmt_score(max_score),
        "band": band_label(name, score),
        "evidence": _student_text(reason),
        "gap": _student_text(gap),
        "dim_key": str(obs.get("dimensionCode") or ""),
    }


def _dimensions(result: dict) -> list[dict]:
    ai = result.get("ai_score") or {}
    out = []
    for key, dim in (ai.get("dimensions") or {}).items():
        if not isinstance(dim, dict):
            continue
        name = rs._dimension_display_name(key, dim.get("name", ""))
        try:
            score = float(dim.get("score") or 0)
            max_score = float(dim.get("max_score") or 0)
        except (TypeError, ValueError):
            score, max_score = 0.0, 0.0
        items = []
        for it in dim.get("items") or []:
            if not isinstance(it, dict):
                continue
            item_name = _item_name(it.get("name") or it.get("title") or "细项")
            reason = str(it.get("reason") or it.get("comment") or "").strip()
            gap = str(it.get("gap") or it.get("improvement") or "").strip()
            band = str(it.get("band") or "").strip() or band_label(item_name, it.get("score"))
            items.append({
                "name": item_name,
                "score": _fmt_score(it.get("score")),
                "max_score": _fmt_score(it.get("max_score")),
                "band": band,
                "evidence": _student_text(reason),
                "gap": _student_text(gap),
            })
        out.append({
            "key": key,
            "name": name,
            "score": _fmt_score(score),
            "max_score": _fmt_score(max_score),
            "pct": _pct(score, max_score),
            "item_rows": items,
        })
    if any(d["item_rows"] for d in out):
        return out
    by_dim: dict[str, list] = {}
    for obs in _rule_observations(result):
        item = _obs_to_item(obs)
        by_dim.setdefault(item["dim_key"] or "other", []).append(item)
    for dim in out:
        rows = by_dim.get(dim["key"]) or []
        dim["item_rows"] = [{k: v for k, v in row.items() if k != "dim_key"} for row in rows]
    return out


def _short_tags(values, limit=3) -> list[str]:
    tags = []
    for raw in values or []:
        text = str(raw or "").strip().rstrip("。；;")
        if not text:
            continue
        if "：" in text:
            head = text.split("：", 1)[0].strip()
            if 4 <= len(head) <= 22:
                text = head
        elif ":" in text:
            head = text.split(":", 1)[0].strip()
            if 4 <= len(head) <= 22:
                text = head
        tags.append(text)
        if len(tags) >= limit:
            break
    return tags


def _student_diagnosis(result: dict, ai: dict, overall: float, dimensions: list[dict]) -> str:
    overview = ai.get("score_overview") or {}
    diagnosis = rs._humanize_dimension_tokens(
        rs._value_text(overview.get("diagnosis") or ai.get("summary") or "")
    ).replace("权威总分", "本场总分")
    leaked = any(token in diagnosis for token in ("规则引擎", "证据上限", "硬性处罚", "失分账本", "权威分"))
    if leaked or not diagnosis:
        weakest = sorted(
            [d for d in dimensions if d.get("name")],
            key=lambda d: float(d.get("pct") or 0),
        )[:2]
        names = "、".join(d["name"] for d in weakest) or "部分维度"
        return (
            f"本场总分 {_fmt_score(overall)}。"
            f"{names}的可核验证据不足，分数被压在证据档；现场演示和转写是有的，但缺仓库、测试和对照材料。"
        )
    return diagnosis


def _overview_tags(ai: dict, result: dict | None = None) -> tuple[list[str], list[str]]:
    overview = ai.get("score_overview") or {}
    highs = overview.get("highlights") or []
    issues = overview.get("key_issues") or []
    if not highs:
        highs = ai.get("highlights") or []
    if not issues:
        issues = ai.get("critical_issues") or []
    high_tags = _short_tags(highs)
    if not high_tags and result:
        ranked = []
        for obs in _rule_observations(result):
            try:
                ratio = float(obs.get("finalScore") or 0) / max(float(obs.get("maxScore") or 0), 1e-6)
            except (TypeError, ValueError):
                continue
            if ratio >= 0.65:
                ranked.append((ratio, obs.get("observationName") or ""))
        ranked.sort(reverse=True)
        high_tags = _short_tags([name for _, name in ranked], limit=3)
    return high_tags, _short_tags(issues)


def _evidence_level(raw: str) -> str:
    text = str(raw or "")
    if "矛盾" in text:
        return "对不上"
    if "缺失" in text or "还缺" in text:
        return "还缺"
    if "弱" in text:
        return "偏弱"
    if "强" in text:
        return "站得住"
    return text or "—"


def _obs_name_by_code(result: dict) -> dict[str, dict]:
    out = {}
    for obs in _rule_observations(result):
        code = str(obs.get("observationCode") or "").strip()
        if code:
            out[code] = obs
    return out


def _evidence_ledger(result: dict) -> list[dict]:
    rows = []
    by_code = _obs_name_by_code(result)
    for item in ((result.get("ai_score") or {}).get("evidence_audit") or [])[:15]:
        if not isinstance(item, dict):
            continue
        code = str(item.get("observationCode") or "").strip()
        obs = by_code.get(code) or {}
        claim = rs._value_text(
            item.get("claim")
            or item.get("conclusion")
            or obs.get("observationName")
            or code
        )
        source = rs._value_text(
            item.get("source")
            or item.get("evidence")
            or item.get("gap")
            or ""
        )
        required = rs._value_text(item.get("requiredEvidence") or "")
        if required and required not in source:
            source = f"{source} 还缺：{required}".strip()
        if not claim or not source:
            continue
        impact = rs._value_text(
            item.get("impact")
            or item.get("observation")
            or obs.get("dimensionName")
            or obs.get("dimensionCode")
            or ""
        )
        level = _evidence_level(item.get("level") or item.get("grade") or "")
        if not level or level == "—":
            level = _engine_level(
                item.get("evidenceLevel") or obs.get("evidenceLevel"),
                obs.get("finalScore"),
                obs.get("maxScore"),
            )
        rows.append({
            "level": level,
            "claim": _item_name(claim),
            "source": _student_text(source),
            "impact": rs._dimension_display_name(impact, impact) if impact else "",
        })
    if rows:
        return rows
    for obs in _rule_observations(result)[:15]:
        name = obs.get("observationName") or obs.get("observationCode") or ""
        source = _student_text(obs.get("evidenceReason") or obs.get("reason") or "")
        if not name:
            continue
        impact = obs.get("dimensionName") or obs.get("dimensionCode") or ""
        rows.append({
            "level": _engine_level(obs.get("evidenceLevel"), obs.get("finalScore"), obs.get("maxScore")),
            "claim": name,
            "source": source or "本场没有落到可核验材料上",
            "impact": rs._dimension_display_name(impact, impact) if impact else "",
        })
    return rows


def _questions(result: dict) -> list[dict]:
    rows = []
    for item in ((result.get("ai_score") or {}).get("judge_questioning") or [])[:3]:
        if not isinstance(item, dict):
            continue
        q = rs._value_text(item.get("question") or "")
        if not q:
            continue
        rows.append({
            "question": q,
            "why": _student_text(rs._value_text(item.get("why_it_matters") or item.get("focus") or "")),
            "prep": rs._value_text(item.get("prep_evidence") or ""),
        })
    return rows


def _speech(result: dict) -> dict | None:
    sq = result.get("speech_quality") or {}
    if not sq:
        return None
    sr = sq.get("speech_rate") or {}
    pauses = sq.get("pauses") or {}
    fillers = sq.get("fillers") or {}
    cpm = sr.get("global_chars_per_minute", "—")
    try:
        cpm_f = float(cpm)
        if cpm_f > 280:
            rate_label = "过快，关键句容易被冲掉"
        elif cpm_f > 250:
            rate_label = "略快"
        elif cpm_f < 180:
            rate_label = "偏慢，后段容易散"
        else:
            rate_label = "合适，评委跟得上"
        cpm_show = _fmt_score(cpm_f)
    except (TypeError, ValueError):
        rate_label = "以实测为准"
        cpm_show = str(cpm)
    filler_n = fillers.get("total_fillers", 0)
    rate = fillers.get("filler_rate_percent")
    try:
        rate_f = float(rate)
        filler_label = "少，不影响听" if rate_f < 5 else ("一般" if rate_f <= 15 else "偏多，显得没准备好")
    except (TypeError, ValueError):
        filler_label = fillers.get("rating") or "—"
    pause_n = pauses.get("total_pauses", 0)
    try:
        longest = float(pauses.get("longest_pause") or 0)
    except (TypeError, ValueError):
        longest = 0.0
    if longest >= 20:
        pause_label = f"次数含演示等待，最长约{int(round(longest))}秒"
    elif int(pause_n or 0) > 20:
        pause_label = "次数偏多，要分清是故障还是在想词"
    else:
        pause_label = "次数尚可"
    return {
        "tiles": [
            {"value": cpm_show, "unit": "字/分钟", "caption": "平均语速", "status": rate_label},
            {"value": pause_n, "unit": "次", "caption": "停顿", "status": pause_label},
            {"value": filler_n, "unit": "次", "caption": "填充词", "status": filler_label},
        ]
    }


def _actions(result: dict) -> list[dict]:
    out = []
    raw_items = [x for x in ((result.get("ai_score") or {}).get("action_plan") or []) if isinstance(x, dict)]
    order = {"P0": 0, "HIGH": 0, "P1": 1, "MEDIUM": 1, "P2": 2, "LOW": 2}
    raw_items.sort(key=lambda x: order.get(str(x.get("priority") or "").upper(), 9))
    for idx, item in enumerate(raw_items, 1):
        priority = str(item.get("priority") or "—").upper()
        if priority == "HIGH":
            priority = "P0"
        elif priority == "MEDIUM":
            priority = "P1"
        elif priority == "LOW":
            priority = "P2"
        out.append({
            "n": f"{idx:02d}",
            "title": rs._value_text(item.get("title") or "改进动作"),
            "priority": priority,
            "method": rs._value_text(item.get("method") or item.get("action")),
            "owner": rs._value_text(item.get("owner")),
            "timebox": rs._value_text(item.get("timebox")),
            "expected": rs._value_text(item.get("expected") or item.get("expected_gain") or item.get("acceptance")),
        })
        if len(out) >= 4:
            break
    return out


def _pitch(result: dict) -> list[dict]:
    rows = []
    for item in (result.get("ai_score") or {}).get("pitch_structure_benchmark") or []:
        if not isinstance(item, dict):
            continue
        stage = rs._value_text(item.get("stage") or item.get("section") or item.get("name") or "")
        if not stage:
            continue
        grade = item.get("score")
        if grade is None or grade == "":
            grade = item.get("score_or_level")
        if isinstance(grade, str) and re.search(r"[A-Fa-f]", grade) and not re.fullmatch(r"\d+(?:\.\d+)?", grade):
            score_txt = grade.strip()
        else:
            score_txt = _fmt_score(grade)
        rows.append({
            "stage": stage,
            "time": rs._value_text(item.get("time_range") or item.get("time") or "未切分"),
            "score": score_txt,
            "actual": _student_text(
                rs._value_text(item.get("actual") or item.get("comment") or item.get("performance") or "")
            ),
            "fix": _student_text(rs._value_text(item.get("fix") or item.get("improvement") or "")),
        })
    return rows


def _team(result: dict) -> list[dict]:
    rows = []
    for item in (result.get("ai_score") or {}).get("team_optimization") or []:
        if not isinstance(item, dict):
            continue
        rows.append({
            "role": rs._value_text(item.get("role") or item.get("owner") or "成员"),
            "issue": rs._value_text(
                item.get("issue") or item.get("currentIssue") or item.get("problem") or ""
            ),
            "action": rs._value_text(
                item.get("action")
                or item.get("optimization")
                or item.get("method")
                or item.get("training")
                or ""
            ),
        })
        if len(rows) >= 4:
            break
    return rows


def _first_text(value, prefer=("suggestion", "issue", "text", "title", "summary")) -> str:
    if isinstance(value, list):
        for item in value:
            text = _first_text(item, prefer)
            if text:
                return text
        return ""
    if isinstance(value, dict):
        for key in prefer:
            text = rs._value_text(value.get(key) or "")
            if text:
                return text
        return rs._value_text(value)
    return rs._value_text(value or "")


def _jury_texts(value, limit: int = 4, prefer=("suggestion", "issue", "text", "title", "summary")) -> list[str]:
    items = value if isinstance(value, list) else [value] if value else []
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _student_text(_first_text(item, prefer))
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


_JURY_THEMES = (
    ("冷场", "参数混淆", "参数混搅", "未有效应答", "联调", "演示故障", "现场改代码", "演示中断"),
    ("开发周期", "周期缩短", "效率提升", "需求响应提升", "创新成效"),
    ("节约成本", "成本构成", "每亩降低", "硬件节约", "成本对比", "投入产出"),
    ("语速", "字/分钟", "字/分", "停顿109", "讲解节奏"),
    ("标准编号", "条款对照", "合规检查", "阿里巴巴开发规约"),
    ("逐行", "代码讲解"),
    ("补台", "应急协作", "发言不均衡"),
    ("使用频次", "真实用户", "用户访谈", "小农户"),
    ("竞品", "低代码", "原创性"),
    ("共同愿景", "成长故事"),
    ("隐私", "数据合规", "脱敏"),
)


def _jury_themes(text: str) -> set[str]:
    return {group[0] for group in _JURY_THEMES if any(key in (text or "") for key in group)}


def _jury_tokens(text: str) -> set[str]:
    return set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}|\d+(?:\.\d+)?%?", text or ""))


def _jury_overlap(left: str, right: str) -> bool:
    if not left or not right:
        return False
    a, b = left.strip(), right.strip()
    if len(a) >= 12 and (a[:12] in b or b[:12] in a):
        return True
    themes_a, themes_b = _jury_themes(a), _jury_themes(b)
    if themes_a and themes_b and themes_a & themes_b:
        return True
    tokens_a, tokens_b = _jury_tokens(a), _jury_tokens(b)
    return bool(tokens_a and tokens_b and len(tokens_a & tokens_b) >= 4)


def _jury_specificity(text: str) -> float:
    score = min(len(text or ""), 80) / 20.0
    if re.search(r"\d{1,2}:\d{2}", text or ""):
        score += 20
    if re.search(r"视频帧|语音|约\d", text or ""):
        score += 8
    if re.search(r"\d+%", text or ""):
        score += 4
    return score


def _jury_pick(texts: list[str]) -> str:
    if not texts:
        return ""
    return max(texts, key=_jury_specificity)


def _matches_consensus(text: str, consensus: list[dict]) -> bool:
    return any(_jury_overlap(text, row.get("text") or "") for row in consensus)


def _first_unique(texts: list[str], consensus: list[dict]) -> str:
    for text in texts:
        if text and not _matches_consensus(text, consensus):
            return text
    return ""


def _cn_bigrams(text: str) -> set[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", text or "")
    return {"".join(chars[i:i + 2]) for i in range(max(0, len(chars) - 1))}


def _lens_ask(card: dict, consensus: list[dict]) -> str:
    unique = _first_unique(card.get("asks") or [], consensus)
    if unique:
        return unique
    if card.get("angle") and not _matches_consensus(card["angle"], consensus):
        return card["angle"]
    focus_grams = _cn_bigrams(card.get("focus") or "")
    ranked = []
    for text in card.get("asks") or []:
        ranked.append((len(_cn_bigrams(text) & focus_grams), _jury_specificity(text), text))
    if ranked:
        ranked.sort(reverse=True)
        return ranked[0][2]
    return (card.get("asks") or [""])[0] if card.get("asks") else (card.get("angle") or "")


def _advice_for(card: dict, concern: str, consensus: list[dict]) -> str:
    if card.get("angle") and concern and _jury_overlap(card["angle"], concern):
        return card["angle"]
    if concern:
        for text in card.get("advices") or []:
            if _jury_overlap(text, concern):
                return text
    if card.get("angle") and not _matches_consensus(card["angle"], consensus):
        return card["angle"]
    return _first_unique(card.get("advices") or [], consensus) or card.get("angle") or (
        (card.get("advices") or [""])[0] if card.get("advices") else ""
    )


def _jury_consensus(pkg: dict, issue_rows: list[dict]) -> list[dict]:
    buckets: list[dict] = []

    def add(text: str, role: str = "", count: int = 1) -> None:
        text = _student_text(text)
        if not text:
            return
        for bucket in buckets:
            if not _jury_overlap(text, bucket["text"]):
                continue
            if role:
                if role not in bucket["roles"]:
                    bucket["roles"].add(role)
                    bucket["n"] += 1
            else:
                bucket["n"] = max(bucket["n"], count)
            if _jury_specificity(text) > _jury_specificity(bucket["text"]):
                bucket["text"] = text
            return
        buckets.append({
            "text": text,
            "n": 1 if role else count,
            "roles": {role} if role else set(),
        })

    used_cards = False
    for row in issue_rows:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        used_cards = True
        add(text, role=str(row.get("role") or ""))
    if not used_cards:
        for item in pkg.get("consensus_issues") or []:
            if isinstance(item, dict):
                add(
                    rs._value_text(item.get("issue") or item.get("text") or ""),
                    count=int(item.get("count") or 1),
                )
            else:
                add(str(item or ""))
    buckets.sort(key=lambda item: (-item["n"], -_jury_specificity(item["text"])))
    rows = []
    for bucket in buckets:
        if bucket["n"] < 2:
            continue
        rows.append({"text": bucket["text"], "n": bucket["n"]})
        if len(rows) >= 4:
            break
    return rows


def _public_role(value) -> str:
    role = rs._value_text(value or "") or "评委"
    if re.fullmatch(r"[A-Z]{4}", role):
        return "评委"
    return role


def _jury(result: dict, dimensions: list[dict] | None = None) -> dict | None:
    if not rs._jury_enabled(result):
        return None
    pkg = rs._real_jury_package(result)
    if not pkg:
        return None
    focus_by_role = {}
    for member in pkg.get("members") or []:
        if not isinstance(member, dict):
            continue
        role = _public_role(member.get("role_label") or member.get("name") or "")
        if role and role != "评委":
            focus_by_role[role] = rs._value_text(member.get("short_label") or "") or rs._format_focus_dimensions_zh(
                member.get("focus_dimensions") or member.get("rubric_focus") or []
            )
    raw_cards = []
    for card in pkg.get("score_cards") or pkg.get("reviews") or []:
        if not isinstance(card, dict):
            continue
        role = _public_role(card.get("role_label") or card.get("persona_name") or "评委")
        view = card.get("persona_view") if isinstance(card.get("persona_view"), dict) else {}
        focus = rs._value_text(
            card.get("short_label")
            or view.get("short_label")
            or focus_by_role.get(role)
            or ""
        )
        if focus and (focus == card.get("optimization_angle") or len(focus) > 22):
            focus = rs._value_text(card.get("short_label") or focus_by_role.get(role) or "")
        raw_cards.append({
            "role": role,
            "focus": _student_text(focus),
            "score": _fmt_score(
                card.get("overall_score") if card.get("overall_score") is not None else card.get("score")
            ),
            "highlights": _jury_texts(card.get("highlights") or card.get("recognition") or "", prefer=("text", "title", "issue")),
            "issues": _jury_texts(
                card.get("critical_issues") or card.get("comment") or "",
                prefer=("issue", "text", "title"),
            ),
            "asks": _jury_texts(view.get("top_concerns") or card.get("top_concerns") or "", prefer=("text", "issue", "title")),
            "advices": _jury_texts(
                card.get("improvement_priorities") or card.get("advice") or "",
                prefer=("suggestion", "action", "improvement", "text"),
            ),
            "why": _student_text(view.get("score_reasoning_style") or card.get("score_reasoning_style") or ""),
            "angle": _student_text(view.get("optimization_angle") or card.get("optimization_angle") or ""),
        })
    issue_rows = [
        {"text": text, "role": card["role"]}
        for card in raw_cards
        for text in (card["issues"] or card["asks"])
    ]
    consensus = _jury_consensus(pkg, issue_rows)
    cards = []
    lenses = []
    for card in raw_cards:
        concern = _lens_ask(card, consensus) or _first_unique(card["issues"], consensus) or _jury_pick(card["issues"])
        advice = _advice_for(card, concern, consensus)
        ask = concern or _lens_ask(card, consensus)
        if ask:
            lenses.append({
                "role": card["role"],
                "focus": card["focus"],
                "ask": ask,
            })
        cards.append({
            "role": card["role"],
            "focus": card["focus"],
            "score": card["score"],
            "why": card["why"],
            "praise": _jury_pick(
                [text for text in card["highlights"] if not _matches_consensus(text, consensus)]
                or card["highlights"]
            ),
            "concern": concern,
            "advice": advice,
        })
    official = None
    try:
        official = float((result.get("ai_score") or {}).get("overall_score") or pkg.get("official_score"))
    except (TypeError, ValueError):
        official = _num(pkg.get("official_score"), default=None) or None
    jury_avg = pkg.get("trimmed_average_score")
    if jury_avg is None:
        jury_avg = pkg.get("raw_average_score")
    try:
        jury_avg_f = float(jury_avg) if jury_avg is not None else None
    except (TypeError, ValueError):
        jury_avg_f = None
    diff = None
    if official is not None and jury_avg_f is not None:
        diff = round(jury_avg_f - official, 1)
    if diff is None:
        try:
            diff = round(float(pkg.get("score_diff_from_official")), 1)
        except (TypeError, ValueError):
            diff = None
    if diff is None:
        diff_note = "评委分只作对照，卷面仍以官方分为准。"
    elif abs(diff) < 3:
        diff_note = "评委观感和官方分接近，方向一致。"
    elif diff > 0:
        diff_note = "评委按现场观感给得更高；官方按可核验证据压分，卷面以官方分为准。"
    else:
        diff_note = "评委对现场观感更严；卷面仍以官方 15 点分为准。"
    high = pkg.get("highest_score")
    low = pkg.get("lowest_score")
    range_note = ""
    try:
        spread = float(high) - float(low)
        count_hint = int(pkg.get("judge_count") or len(cards) or 0)
        who = f"{count_hint} 位" if count_hint else "评委"
        if spread < 4:
            range_note = f"{who}分差不大，判断方向一致；价值在各视角盯的问题不一样。"
        elif spread >= 8:
            range_note = "不同视角分差较大，下面按评委拆开看，答辩优先准备分差大的维度。"
    except (TypeError, ValueError):
        spread = None
    official_by_key = {}
    for dim in dimensions or []:
        official_by_key[dim.get("key")] = dim
        official_by_key[dim.get("name")] = dim
    dim_compare = []
    for stat in pkg.get("dimension_stats") or []:
        if not isinstance(stat, dict):
            continue
        name = rs._dimension_display_name(stat.get("key") or "", stat.get("name") or "")
        official_dim = official_by_key.get(stat.get("key")) or official_by_key.get(name) or {}
        jury_score = _fmt_score(stat.get("average_score"))
        official_score = official_dim.get("score") or "—"
        max_score = _fmt_score(stat.get("max_score") or official_dim.get("max_score") or "")
        try:
            dim_spread = float(stat.get("range"))
        except (TypeError, ValueError):
            try:
                dim_spread = float(stat.get("highest_score")) - float(stat.get("lowest_score"))
            except (TypeError, ValueError):
                dim_spread = None
        dim_compare.append({
            "name": name,
            "official": f"{official_score}/{max_score}" if max_score and max_score != "—" else str(official_score),
            "jury": f"{jury_score}/{max_score}" if max_score and max_score != "—" else jury_score,
            "spread": _fmt_score(dim_spread) if dim_spread is not None else "—",
        })
        if len(dim_compare) >= 5:
            break
    count = int(pkg.get("judge_count") or len(cards) or 0)
    intro = (
        f"{count} 位评委按不同视角独立看同一场，不是第二份官方分。"
        "官方分按赛项 15 个观测点给；这一章回答三件事：多数人卡住什么、不同视角会追问什么、每位评委认可什么和下刀改什么。"
    )
    return {
        "count": count,
        "intro": intro,
        "summary": {
            "official": _fmt_score(official) if official is not None else "—",
            "jury_avg": _fmt_score(jury_avg_f) if jury_avg_f is not None else "—",
            "diff": (f"+{_fmt_score(diff)}" if diff is not None and diff > 0 else _fmt_score(diff)) if diff is not None else "—",
            "diff_note": diff_note,
            "high": _fmt_score(high) if high is not None else "—",
            "low": _fmt_score(low) if low is not None else "—",
            "range_note": range_note,
        },
        "consensus": consensus,
        "lenses": lenses,
        "dim_compare": dim_compare,
        "cards": cards,
        "members": [],
    }


def _strip_md(text: str) -> str:
    t = rs._humanize_dimension_tokens(str(text or ""))
    t = t.replace("**", "")
    return t.strip()


def _profile(result: dict) -> dict | None:
    profile = result.get("character_profile") or {}
    if not isinstance(profile, dict) or profile.get("error"):
        return None
    raw = profile.get("profile_markdown") or profile.get("markdown") or ""
    if not raw:
        return None
    cleaned = rs._clean_profile_markdown(raw)
    if not cleaned:
        return None
    blocks: list[dict] = []
    current = {"heading": "", "paras": []}

    def flush() -> None:
        if current["heading"] or current["paras"]:
            blocks.append({"heading": current["heading"], "paras": list(current["paras"])})

    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        if line.startswith("#"):
            flush()
            heading = _strip_md(line.lstrip("#").strip())
            if heading in ("选手团队能力画像报告", "选手团队能力画像"):
                current = {"heading": "", "paras": []}
                continue
            current = {"heading": heading, "paras": []}
            continue
        if line.startswith("|"):
            current["paras"].append(_strip_md(line.replace("|", "  ")))
            continue
        if line[:1] in "-*•":
            current["paras"].append(_strip_md(line[1:].strip()))
            continue
        numbered = re.sub(r"^\d+[\.、)]\s+", "", line)
        current["paras"].append(_strip_md(numbered if numbered != line else line))
    flush()
    useful = [b for b in blocks if b["heading"] or b["paras"]]
    if not useful:
        return None
    return {"blocks": useful[:12]}


def _fusion(result: dict) -> dict | None:
    fusion = result.get("fusion") or {}
    ai_fusion = (result.get("ai_score") or {}).get("audio_visual_fusion") or {}
    if not isinstance(fusion, dict):
        fusion = {}
    if not isinstance(ai_fusion, dict):
        ai_fusion = {}
    if fusion.get("error") and not ai_fusion:
        return None
    summary = rs._humanize_dimension_tokens(
        rs._value_text(ai_fusion.get("summary") or fusion.get("summary") or "")
    )
    summary_minutes = [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*分钟", summary)]
    if len(summary_minutes) >= 2 and max(summary_minutes) - min(summary_minutes) > 2:
        summary = ""
    rows = []
    src = ai_fusion.get("contradictions") or fusion.get("contradictions") or []
    for item in src:
        if isinstance(item, str):
            desc = item.strip()
            if not desc:
                continue
            rows.append({"time": "—", "desc": _student_text(desc)})
            if len(rows) >= 3:
                break
            continue
        if not isinstance(item, dict):
            continue
        desc = rs._value_text(item.get("description") or item.get("desc") or item.get("note") or "")
        if not desc:
            continue
        minutes = [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)\s*分钟", desc)]
        time_txt = rs._value_text(item.get("time") or item.get("timestamp") or "")
        minutes += [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)", time_txt) if "分钟" in time_txt or ":" not in time_txt]
        if len(minutes) >= 2 and max(minutes) - min(minutes) > 2:
            continue
        rows.append({"time": time_txt, "desc": _student_text(desc)})
        if len(rows) >= 3:
            break
    if not summary and not rows:
        return None
    return {"summary": summary, "rows": rows}


def _verdict(result: dict, diagnosis: str = "") -> dict | None:
    verdict = (result.get("ai_score") or {}).get("final_verdict") or {}
    if not isinstance(verdict, dict) or not verdict:
        ai = result.get("ai_score") or {}
        issues = ai.get("critical_issues") or []
        actions = [a for a in (ai.get("action_plan") or []) if isinstance(a, dict)]
        highs = ai.get("highlights") or []
        rows = []
        if highs:
            rows.append({
                "label": "站得住脚的优势",
                "text": "\n".join(f"{i}. {t}" for i, t in enumerate(_short_tags(highs, 3), 1)),
            })
        if issues:
            rows.append({
                "label": "关键扣分项",
                "text": "\n".join(f"{i}. {t}" for i, t in enumerate(_short_tags(issues, 3), 1)),
            })
        titles = [a.get("title") for a in actions if a.get("title")]
        if titles:
            rows.append({
                "label": "下一轮优先补齐",
                "text": "\n".join(f"{i}. {t}" for i, t in enumerate(titles[:3], 1)),
            })
        if not rows:
            return None
        return {"title": "综合判定", "summary": diagnosis, "rows": rows}
    has_jury = bool(rs._real_jury_package(result))
    summary = rs._value_text(verdict.get("summary") or (verdict.get("jury_summary") if has_jury else ""))
    rows = []
    for label, key in (
        ("站得住脚的优势", "defensible_strengths"),
        ("关键扣分项", "critical_deductions"),
        ("下一轮优先补齐", "next_round_focus"),
    ):
        raw = verdict.get(key)
        if not raw:
            continue
        text = rs._verdict_cell_text(raw).replace("<br/>", "\n").replace("<br>", "\n")
        rows.append({"label": label, "text": text})
    return {
        "title": "评审团与系统综合判定" if has_jury else "综合判定",
        "summary": rs._humanize_dimension_tokens(summary),
        "rows": rows,
    }


def build_view_model(result: dict) -> dict:
    if not isinstance(result, dict):
        raise TypeError("result must be dict")
    result = dict(result)
    try:
        from app.services.evidence_alignment_service import sanitize_result_for_report
        result = sanitize_result_for_report(result)
    except Exception as exc:
        print(f"[HtmlReport] evidence alignment skipped: {exc}")
    if not rs._jury_enabled(result):
        ai = result.get("ai_score")
        if isinstance(ai, dict):
            ai = dict(ai)
            ai.pop("jury_review", None)
            result["ai_score"] = ai
    else:
        result = rs._attach_jury_package(result)

    ai = result.get("ai_score") or {}
    try:
        overall = float(ai.get("overall_score") or 0)
    except (TypeError, ValueError):
        overall = 0.0
    highlight_tags, issue_tags = _overview_tags(ai, result)

    sections = []
    n = 0

    def _sec() -> str:
        nonlocal n
        n += 1
        return f"{n:02d}"

    cover = _cover_meta(result)
    dimensions = _reconcile_dimensions(result, _dimensions(result))
    overall = _aligned_overall(overall, dimensions)
    score_note = _score_note(result)
    diagnosis = _student_diagnosis(result, ai, overall, dimensions)
    actions = _actions(result)
    pitch = _pitch(result)
    team = _team(result)
    speech = _speech(result)
    jury = _jury(result, dimensions)
    fusion = _fusion(result)
    questions = _questions(result)
    evidence = _evidence_ledger(result)
    verdict = _verdict(result, diagnosis)
    gaps = _item_gaps(dimensions)
    if verdict:
        verdict["summary"] = _rewrite_gap_numbers(verdict.get("summary") or "", gaps)
        for row in verdict.get("rows") or []:
            row["text"] = _rewrite_gap_numbers(row.get("text") or "", gaps)
    for item in questions:
        item["why"] = _rewrite_gap_numbers(item.get("why") or "", gaps)
    delivery = bool(speech or (fusion and fusion.get("rows")) or pitch)

    sections.append({"no": _sec(), "title": "成绩单", "key": "overview"})
    if evidence or questions:
        sections.append({"no": _sec(), "title": "证据台账", "key": "evidence"})
    if dimensions:
        sections.append({"no": _sec(), "title": "官方给分", "key": "dimensions"})
    if delivery:
        sections.append({"no": _sec(), "title": "讲述质量", "key": "delivery"})
    if jury:
        sections.append({"no": _sec(), "title": "评审团", "key": "jury"})
    if actions:
        sections.append({"no": _sec(), "title": "下一轮动作", "key": "actions"})
    if team:
        sections.append({"no": _sec(), "title": "谁来练", "key": "team"})
    if verdict:
        sections.append({"no": _sec(), "title": "判定", "key": "verdict"})

    return {
        "brand": rs.BRAND_PRODUCT,
        "company": rs.BRAND_COMPANY,
        "website": rs.BRAND_WEBSITE,
        "logo": _logo_data_uri(),
        "header_mark": _header_mark_data_uri(),
        "publisher_logo": _publisher_logo_data_uri(),
        "cover": cover,
        "overall": _fmt_score(overall),
        "score_note": score_note,
        "diagnosis": diagnosis,
        "highlight_tags": highlight_tags,
        "issue_tags": issue_tags,
        "evidence": evidence,
        "questions": questions,
        "dimensions": dimensions,
        "speech": speech,
        "jury": jury,
        "fusion": fusion,
        "pitch": pitch,
        "actions": actions,
        "team": team,
        "verdict": verdict,
        "sections": sections,
    }
