"""Generate exportable AI jury review reports."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.config import settings
from app.services.jury.aggregate_service import aggregate_judge_reports


def build_jury_report_payload(session: dict[str, Any]) -> dict[str, Any]:
    reports = [
        report for report in session.get("judge_reports", [])
        if report.get("status", "completed") == "completed" and report.get("overall_score") is not None
    ]
    aggregate = session.get("aggregate") or aggregate_judge_reports(reports, session.get("official_score"))
    judge_count = int(session.get("judge_count") or aggregate.get("judge_count") or len(reports) or 9)
    trimmed_count = int(aggregate.get("trimmed_count") or max(judge_count - 2, 0))
    score_cards = [
        {
            "persona_code": report.get("persona_code"),
            "role_label": report.get("role_label") or report.get("persona_name"),
            "overall_score": _round2(report.get("overall_score")),
            "summary": _summary(report),
        }
        for report in reports
    ]
    deduction_details = _deduction_details(reports)
    deduction_map = _balanced_deductions(deduction_details)
    action_routes = _action_routes(reports, deduction_details)
    official_score = _round2(session.get("official_score"))
    jury_trimmed_avg = _round2(
        aggregate.get("trimmed_average_score")
        or session.get("jury_trimmed_avg")
    )
    score_diff = _round2(
        aggregate.get("score_diff_from_official")
        or session.get("score_diff_from_official")
    )
    return {
        "meeting_id": session.get("meeting_id"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "official_score": official_score,
        "jury_trimmed_avg": jury_trimmed_avg,
        "jury_trimmed_total": _round2(aggregate.get("trimmed_total_score")),
        "judge_count": judge_count,
        "trimmed_count": trimmed_count,
        "score_diff_from_official": score_diff,
        "evidence_summary": session.get("official_evidence_summary") or {},
        "coach_note": (
            "这份评审团报告不是为了再给一次分，而是帮你提前听见不同评委脑子里的疑问。"
            "分歧越大的地方，越值得提前准备；共识越强的问题，越应该优先修改。"
            "你们不是没有亮点，而是有些亮点还没有被证据托住。"
        ),
        "score_cards": score_cards,
        "dimension_stats": aggregate.get("dimension_stats", []),
        "consensus_issues": aggregate.get("consensus_issues", []),
        "deduction_map": deduction_map,
        "deduction_details": deduction_details,
        "priorities": _priorities(reports),
        "action_routes": action_routes,
        "reading_summary": _reading_summary(
            official_score,
            jury_trimmed_avg,
            score_diff,
            deduction_map,
            action_routes,
        ),
    }


def generate_jury_report(session: dict[str, Any], output_dir: str | None = None) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

    output_dir = output_dir or os.path.join(settings.UPLOAD_DIR, "reports")
    os.makedirs(output_dir, exist_ok=True)
    meeting_id = session.get("meeting_id") or "unknown"
    filepath = os.path.join(output_dir, f"jury_report_{meeting_id}.pdf")
    payload = build_jury_report_payload(session)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
    )
    story: list[Any] = []
    styles = _styles()

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("AI JURY REVIEW", styles["eyebrow"]))
    story.append(Paragraph("AI 评审团复盘作战书", styles["title"]))
    story.append(Paragraph(f"会议 #{payload['meeting_id']} · {payload['generated_at']}", styles["meta"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(payload["coach_note"], styles["lead"]))
    story.append(Spacer(1, 0.45 * cm))

    score_rows = [
        ["本场得分", _fmt(payload["official_score"]), "评审团计分总分", _fmt(payload["jury_trimmed_total"]), "去高低均分", _fmt(payload["jury_trimmed_avg"])],
        ["评委人数", str(payload["judge_count"]), "计分人数", str(payload["trimmed_count"]), "差异", _signed(payload["score_diff_from_official"])],
        ["口头证据", str(payload["evidence_summary"].get("verbal_evidence_count", "-")), "视觉证据", str(payload["evidence_summary"].get("visual_evidence_count", "-")), "交叉验证", str(payload["evidence_summary"].get("cross_validated_count", "-"))],
    ]
    story.append(_table(score_rows, widths=[2.4 * cm, 2.0 * cm, 3.0 * cm, 2.0 * cm, 1.8 * cm, 2.0 * cm]))

    story.append(Paragraph("先看结论", styles["h2"]))
    summary_labels = ["分数信号", "共识扣分", "行动顺序"]
    for label, line in zip(summary_labels, payload["reading_summary"]):
        story.append(Paragraph(f"{label}：{line}", styles["body"]))
    story.append(Spacer(1, 0.12 * cm))

    story.append(Paragraph(f"{payload['judge_count']} 位评委视角", styles["h2"]))
    card_rows = [["评委", "类型", "分数", "第一关注点"]]
    for card in payload["score_cards"]:
        card_rows.append([
            card.get("persona_code") or "-",
            card.get("role_label") or "-",
            _fmt(card.get("overall_score")),
            card.get("summary") or "-",
        ])
    story.append(_table(card_rows, widths=[1.8 * cm, 3.4 * cm, 2.0 * cm, 8.0 * cm], header=True))

    story.append(PageBreak())
    story.append(Paragraph("分歧最大的地方", styles["h2"]))
    dim_rows = [["维度", "均分", "最高", "最低", "分歧"]]
    for item in (payload["dimension_stats"] or [])[:4]:
        dim_rows.append([
            item.get("name") or item.get("key") or "-",
            _fmt(item.get("average_score")),
            _fmt(item.get("highest_score")),
            _fmt(item.get("lowest_score")),
            _fmt(item.get("range")),
        ])
    story.append(_table(dim_rows, widths=[4.0 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm], header=True))

    story.append(Paragraph("评分表扣分拆解", styles["section_title"]))
    story.append(Paragraph(f"这里不复述本场评分报告，而是把{payload['judge_count']}位评委在评分表上的扣分位置、扣分幅度和分歧拆开看。", styles["section_desc"]))
    for item in payload["deduction_details"][:8]:
        title = (
            f"{item['dimension']} · {item['item']}  "
            f"<font color='#0F766E'>均扣{_fmt(item['average_deducted'])} / {item.get('judge_count', 1)}位评委</font>"
        )
        summary_rows = [
            ["满分", _fmt(item["max_score"]), "均分", _fmt(item["average_score"]), "最高扣分", _fmt(item["max_deducted"]), "最低扣分", _fmt(item["min_deducted"])],
        ]
        judge_rows = [["评委", "扣分", "主要判断"]]
        for judge in jury_report_judges_for_item(item):
            judge_rows.append([
                f"{judge.get('persona_code')} · {judge.get('role_label')}",
                _fmt(judge.get("deducted")),
                judge.get("reason") or "-",
            ])
        story.append(Paragraph(title, styles["card_title"]))
        story.append(_table(summary_rows, widths=[1.5 * cm, 1.6 * cm, 1.5 * cm, 1.6 * cm, 2.0 * cm, 1.6 * cm, 2.0 * cm, 1.6 * cm]))
        story.append(_table(judge_rows, widths=[3.6 * cm, 1.6 * cm, 9.0 * cm], header=True))
        story.append(Spacer(1, 0.2 * cm))

    story.append(PageBreak())
    story.append(Paragraph("下一轮详细改进方案", styles["section_title"]))
    story.append(Paragraph(f"按追回分数和现场可执行性排序。这里的共识人数按评委去重，最大为{payload['judge_count']}。", styles["section_desc"]))
    for index, route in enumerate(payload["action_routes"][:4], start=1):
        related = "；".join(
            f"{item['dimension']}·{item['item']} 均扣{_fmt(item['average_deducted'])}"
            for item in route.get("score_items", [])[:3]
        ) or route["dimension_hint"]
        route_block = [
            Paragraph(f"{index}. {route['theme']}：{route['action']}", styles["h2"]),
            Paragraph(f"共识来源：{route['judge_count']}/{payload['judge_count']} 位评委 · 命中建议：{route['mention_count']}条 · 关联扣分：{related}", styles["caption"]),
            Paragraph(route["why"], styles["body"]),
        ]
        task_rows = [["动作", "具体改法"]]
        for task in route.get("tasks", []):
            task_rows.append([task["label"], task["detail"]])
        route_block.append(_table(task_rows, widths=[2.5 * cm, 11.7 * cm], header=True))
        route_block.append(Spacer(1, 0.25 * cm))
        story.append(KeepTogether(route_block))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filepath


def jury_report_judges_for_item(item: dict[str, Any]) -> list[dict[str, Any]]:
    return list(item.get("judge_breakdown") or [])


def _deduction_details(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for report in reports:
        persona = report.get("persona_code") or report.get("role_label") or "评委"
        role_label = report.get("role_label") or report.get("persona_name") or persona
        for dimension in (report.get("dimensions") or {}).values():
            dim_name = dimension.get("name") or "未知维度"
            for item in dimension.get("items") or []:
                max_score = _num(item.get("max_score") or item.get("maxScore"))
                score = _num(item.get("score"))
                deducted = max(0.0, max_score - score)
                if deducted <= 0:
                    continue
                key = (dim_name, item.get("name") or "未命名评分项")
                bucket = grouped.setdefault(key, {
                    "dimension": dim_name,
                    "item": item.get("name") or "未命名评分项",
                    "deductions": [],
                    "scores": [],
                    "reasons": [],
                    "personas": set(),
                    "judge_breakdown": [],
                    "max_score": max_score,
                })
                bucket["deductions"].append(deducted)
                bucket["scores"].append(score)
                bucket["personas"].add(persona)
                reason = item.get("reason") or item.get("improvement") or "未返回详细原因"
                improvement = item.get("improvement") or ""
                bucket["reasons"].append({"reason": reason, "deducted": deducted})
                bucket["judge_breakdown"].append({
                    "persona_code": persona,
                    "role_label": role_label,
                    "score": _round2(score),
                    "max_score": _round2(max_score),
                    "deducted": _round2(deducted),
                    "reason": _shorten(reason, 160),
                    "improvement": _shorten(improvement, 140),
                })

    merged = []
    for bucket in grouped.values():
        deductions = bucket["deductions"]
        scores = bucket["scores"]
        reasons = sorted(bucket["reasons"], key=lambda item: item["deducted"], reverse=True)
        judge_breakdown = sorted(bucket["judge_breakdown"], key=lambda item: item["deducted"], reverse=True)
        judge_count = len(bucket["personas"])
        avg_deducted = sum(deductions) / len(deductions)
        max_score = bucket["max_score"]
        merged.append({
            "dimension": bucket["dimension"],
            "item": bucket["item"],
            "judge_count": judge_count,
            "average_score": _round2(sum(scores) / len(scores)),
            "average_deducted": _round2(avg_deducted),
            "max_deducted": _round2(max(deductions)),
            "min_deducted": _round2(min(deductions)),
            "max_score": _round2(max_score),
            "deducted": _round2(sum(deductions) / len(deductions)),
            "representative_reason": _shorten(reasons[0]["reason"], 180),
            "reason": _shorten(reasons[0]["reason"], 180),
            "judge_breakdown": judge_breakdown,
            "personas": sorted(bucket["personas"]),
            "score_weight": judge_count * 10 + avg_deducted,
        })
    return sorted(merged, key=lambda item: item["score_weight"], reverse=True)


def _balanced_deductions(items: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(items, key=lambda item: item["score_weight"], reverse=True)
    selected = []
    used_keys = set()
    for dimension in _dimension_order():
        candidates = [item for item in ranked if item["dimension"] == dimension]
        if candidates:
            item = candidates[0]
            selected.append(item)
            used_keys.add((item["dimension"], item["item"]))
    for item in ranked:
        key = (item["dimension"], item["item"])
        if key in used_keys:
            continue
        selected.append(item)
        used_keys.add(key)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _dimension_order() -> list[str]:
    return ["技能水平", "创新创意", "应用价值", "团队合作", "职业素养"]


def _priorities(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for report in reports:
        for item in report.get("improvement_priorities") or []:
            key = (item.get("dimension"), item.get("issue"), item.get("suggestion"))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def _action_routes(reports: list[dict[str, Any]], deduction_details: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    buckets = {
        "演示稳定性": {
            "keywords": ("故障", "演示", "稳定", "冷场", "备用", "彩排"),
            "dimension_hint": "技能水平 · 技能熟练度",
            "action": "把AI问答和关键功能做成零故障演示链路",
            "why": "多位评委把现场故障视为技能熟练度的直接扣分点。下一轮先做全流程彩排、备用账号/离线视频、异常时的过渡话术。",
        },
        "证据补强": {
            "keywords": ("证据", "标准", "报告", "截图", "对比表", "来源", "数据来源", "成本"),
            "dimension_hint": "职业素养 / 应用价值 / 创新创意",
            "action": "把口头结论补成可看见的证据页",
            "why": "评委普遍认可项目有应用场景，但对标准依据、成本测算、数据来源和测试报告的可见证据仍不够放心。",
        },
        "表达压缩": {
            "keywords": ("讲解", "冗长", "语速", "时间", "代码", "填充词", "重点"),
            "dimension_hint": "技能水平 · 现场讲解效果",
            "action": "重写代码讲解段，只保留业务逻辑、关键算法和结果",
            "why": "技术细节讲得多，不等于评委理解得深。下一轮要把逐行解释改成结论、证据、价值三拍。",
        },
        "创新可信度": {
            "keywords": ("创新", "原创", "benchmark", "对比", "A/B", "性能", "成效"),
            "dimension_hint": "创新创意 · 创新意识/创新成效",
            "action": "给创新点补对比对象和成效来源",
            "why": "评委不是否定创新，而是需要看见相对传统方案到底新在哪里、快在哪里、准在哪里。",
        },
    }
    for bucket in buckets.values():
        bucket["mention_count"] = 0
        bucket["judge_codes"] = set()
        bucket["examples"] = []

    for report in reports:
        judge_code = report.get("persona_code") or report.get("role_label") or "评委"
        for item in report.get("improvement_priorities") or []:
            text = f"{item.get('dimension', '')} {item.get('issue', '')} {item.get('suggestion', '')}"
            matched_themes = [
                theme
                for theme, bucket in buckets.items()
                if any(keyword in text for keyword in bucket["keywords"])
            ]
            if not matched_themes:
                matched_themes = ["证据补强"]
            for theme in matched_themes:
                bucket = buckets[theme]
                bucket["mention_count"] += 1
                bucket["judge_codes"].add(judge_code)
                if len(bucket["examples"]) < 2:
                    bucket["examples"].append(item.get("suggestion") or item.get("issue") or "")

    routes = [
        {
            "theme": theme,
            **{
                key: value
                for key, value in bucket.items()
                if key not in ("keywords", "judge_codes")
            },
            "judge_count": len(bucket["judge_codes"]),
            "tasks": _action_tasks(theme, deduction_details or []),
            "score_items": _related_deductions(theme, deduction_details or []),
        }
        for theme, bucket in buckets.items()
        if bucket["mention_count"] > 0
    ]
    priority = {
        "演示稳定性": 0,
        "创新可信度": 1,
        "证据补强": 2,
        "表达压缩": 3,
    }
    return sorted(routes, key=lambda item: (priority.get(item["theme"], 99), -item["mention_count"]))


def _related_deductions(theme: str, deduction_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapping = {
        "演示稳定性": ("技能熟练度",),
        "创新可信度": ("创新意识", "创新成效", "技术先进性"),
        "证据补强": ("操作规范性", "职业道德与行为规范", "经济性", "可持续性", "创新成效"),
        "表达压缩": ("现场讲解效果",),
    }
    names = mapping.get(theme, ())
    related = [
        item for item in deduction_details
        if item.get("item") in names or any(name in item.get("item", "") for name in names)
    ]
    return sorted(related, key=lambda item: item["score_weight"], reverse=True)[:4]


def _action_tasks(theme: str, deduction_details: list[dict[str, Any]]) -> list[dict[str, str]]:
    task_map = {
        "演示稳定性": [
            ("演示脚本", "把AI问答、智能排风、后台管理拆成固定演示步骤，每一步写清输入、点击、预期输出和兜底话术。"),
            ("演示兜底", "准备一段本地录屏和一套离线截图，现场服务异常时可以立即切换，不让评委等待。"),
            ("彩排验收", "正式路演前至少完成3轮全流程彩排，记录失败点、耗时和修复人，直到关键链路连续通过。"),
            ("现场分工", "一人主讲，一人操作，一人盯异常，一人准备备用材料；故障时由主讲继续解释业务价值。"),
        ],
        "创新可信度": [
            ("对比对象", "明确传统方案、竞品方案或上一版本方案，说明本项目到底新在哪里。"),
            ("数据来源", "给开发周期缩短、效率提升、响应提速等数据补充来源、口径、样本量和统计时间。"),
            ("验证图表", "增加benchmark、A/B测试、前后对比截图或用户反馈摘要，避免只用口头数字。"),
            ("创新表达", "把创新点改写成“原问题-原方案痛点-本方案机制-验证结果”的四段式。"),
        ],
        "证据补强": [
            ("标准依据", "列出国家标准、开发规范、安全规范编号，并放一页合规对照表。"),
            ("成本测算", "补硬件成本、部署成本、维护成本和节省收益的明细表，标注计算口径。"),
            ("证明材料", "展示测试报告、软著进度、开源License清单、权限/隐私保护截图。"),
            ("证据页设计", "每个关键结论旁边放一个可视证据，不让评委只听到结论。"),
        ],
        "表达压缩": [
            ("删减代码", "代码讲解不逐行解释，只保留业务入口、关键算法、异常处理和输出结果。"),
            ("节奏重排", "把技术细节压缩为2-3分钟，把时间让给稳定演示、应用价值和创新证据。"),
            ("评委语言", "把工程术语翻译成评委能判断的价值：更稳、更快、更省、更安全。"),
            ("口播训练", "控制语速，减少填充词，每段结束用一句结论收束。"),
        ],
    }
    return [{"label": label, "detail": detail} for label, detail in task_map.get(theme, [])]


def _reading_summary(
    official_score: float,
    jury_trimmed_avg: float,
    score_diff: float,
    deduction_map: list[dict[str, Any]],
    action_routes: list[dict[str, Any]],
) -> list[str]:
    if score_diff < 0:
        diff_phrase = f"低于本场得分{_fmt(official_score)}共{abs(score_diff):.2f}分"
    elif score_diff > 0:
        diff_phrase = f"高于本场得分{_fmt(official_score)}共{abs(score_diff):.2f}分"
    else:
        diff_phrase = f"与本场得分{_fmt(official_score)}基本持平"
    score_line = (
        f"去高低后的评审团均分为{_fmt(jury_trimmed_avg)}，{diff_phrase}；"
        "这代表复盘重点不是推翻基准分，而是找出不同评委共同担心的地方。"
    )

    if deduction_map:
        top = deduction_map[0]
        consensus_line = (
            f"最强共识扣分点是“{top['dimension']} · {top['item']}”，"
            f"{top.get('judge_count', 1)}位评委都扣分，平均扣{_fmt(top.get('average_deducted', top.get('deducted')))}分。"
        )
    else:
        consensus_line = "本轮没有形成明显共识扣分点，建议优先查看分歧维度和各评委原始意见。"

    if action_routes:
        actions = "、".join(route["theme"] for route in action_routes[:3])
        action_line = f"下一轮不要平均用力，建议按“{actions}”的顺序改；先处理现场确定性，再补证据和表达。"
    else:
        action_line = "下一轮优化动作不足，建议先补充每位评委的改进建议后再生成复盘报告。"

    return [score_line, consensus_line, action_line]


def _summary(report: dict[str, Any]) -> str:
    view = report.get("persona_view") or {}
    concerns = view.get("top_concerns") or []
    if isinstance(concerns, str):
        concerns = [part.strip() for part in concerns.replace("，", "、").split("、") if part.strip()]
    if concerns:
        return str(concerns[0])
    issues = report.get("critical_issues") or []
    return str(issues[0]) if issues else ""


def _styles():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle

    try:
        from app.services import report_service as base_report
        cn_font = getattr(base_report, "_CN_FONT", "Helvetica")
        cn_font_bold = getattr(base_report, "_CN_FONT_BOLD", "Helvetica-Bold")
    except Exception:
        cn_font = "Helvetica"
        cn_font_bold = "Helvetica-Bold"

    return {
        "eyebrow": ParagraphStyle("JuryEyebrow", fontName="Courier", fontSize=8, leading=12, textColor=colors.HexColor("#0f766e"), spaceAfter=4),
        "title": ParagraphStyle("JuryTitle", fontName=cn_font_bold, fontSize=28, leading=36, textColor=colors.HexColor("#111827"), spaceAfter=2),
        "section_title": ParagraphStyle("JurySectionTitle", fontName=cn_font_bold, fontSize=18, leading=25, spaceBefore=2, spaceAfter=4, textColor=colors.HexColor("#111827")),
        "section_desc": ParagraphStyle("JurySectionDesc", fontName=cn_font, fontSize=9, leading=15, spaceAfter=12, textColor=colors.HexColor("#6b7280")),
        "h2": ParagraphStyle("JuryH2", fontName=cn_font_bold, fontSize=13, leading=19, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#0f766e")),
        "card_title": ParagraphStyle("JuryCardTitle", fontName=cn_font_bold, fontSize=10.5, leading=16, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#111827")),
        "meta": ParagraphStyle("JuryMeta", fontName=cn_font, fontSize=9, leading=14, textColor=colors.HexColor("#6b7280")),
        "lead": ParagraphStyle("JuryLead", fontName=cn_font, fontSize=10, leading=17, alignment=TA_LEFT, textColor=colors.HexColor("#374151")),
        "body": ParagraphStyle("JuryBody", fontName=cn_font, fontSize=8.8, leading=14, alignment=TA_LEFT, textColor=colors.HexColor("#374151")),
        "body_bold": ParagraphStyle("JuryBodyBold", fontName=cn_font_bold, fontSize=9, leading=15, textColor=colors.HexColor("#111827")),
        "caption": ParagraphStyle("JuryCaption", fontName=cn_font, fontSize=8, leading=12, textColor=colors.HexColor("#6b7280")),
    }


def _table(rows: list[list[Any]], widths: list[float], header: bool = False):
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle

    styles = _styles()
    safe_rows = [[Paragraph(_escape(cell), styles["body"]) for cell in row] for row in rows]
    table = Table(safe_rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0fdfa") if header else colors.HexColor("#ffffff")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]
    if header:
        style.append(("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f766e")))
    table.setStyle(TableStyle(style))
    return table


def _header_footer(canvas, doc):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm

    styles = _styles()
    cn_font = styles["meta"].fontName
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#e5e7eb"))
    canvas.setLineWidth(0.45)
    canvas.line(2.2 * cm, A4[1] - 1.45 * cm, A4[0] - 2.2 * cm, A4[1] - 1.45 * cm)
    canvas.setFont(cn_font, 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(2.2 * cm, A4[1] - 1.25 * cm, "OREP · AI评审团复盘作战书")
    canvas.drawRightString(A4[0] - 2.2 * cm, A4[1] - 1.25 * cm, "MULTI-VIEW REVIEW")
    canvas.setFont("Courier", 8)
    canvas.drawCentredString(A4[0] / 2, 1.15 * cm, f"- {doc.page} -")
    canvas.restoreState()


def _escape(value: Any) -> str:
    text = str(value if value is not None else "-")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _shorten(text: Any, limit: int) -> str:
    value = str(text or "")
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round2(value: Any) -> float:
    return round(_num(value), 2)


def _fmt(value: Any) -> str:
    return f"{_num(value):.2f}"


def _signed(value: Any) -> str:
    number = _num(value)
    return f"{number:+.2f}"
