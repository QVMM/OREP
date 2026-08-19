"""竞赛助手：对话/文稿导出 PDF（reportlab，中文字体）。"""
from __future__ import annotations

import io
import re
from pathlib import Path


def _find_cjk_font() -> str | None:
    candidates = [
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def messages_to_pdf_bytes(
    *,
    title: str,
    messages: list[dict],
    subtitle: str | None = None,
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_path = _find_cjk_font()
    font_name = "Helvetica"
    if font_path:
        try:
            # TTC 可能需要 subfontIndex
            pdfmetrics.registerFont(TTFont("OREP_CJK", font_path, subfontIndex=0))
            font_name = "OREP_CJK"
        except Exception:
            try:
                pdfmetrics.registerFont(TTFont("OREP_CJK", font_path))
                font_name = "OREP_CJK"
            except Exception:
                font_name = "Helvetica"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title or "竞赛助手导出",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCN",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=22,
        spaceAfter=8,
    )
    sub_style = ParagraphStyle(
        "SubCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor="#666666",
        spaceAfter=14,
    )
    role_style = ParagraphStyle(
        "RoleCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=11,
        leading=15,
        textColor="#C43A12",
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BodyCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10.5,
        leading=16,
        spaceAfter=6,
    )

    def esc(s: str) -> str:
        s = (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = s.replace("\n", "<br/>")
        return s

    story = []
    story.append(Paragraph(esc(title or "竞赛助手对话导出"), title_style))
    if subtitle:
        story.append(Paragraph(esc(subtitle), sub_style))
    story.append(Spacer(1, 4))

    for m in messages or []:
        role = m.get("role")
        label = "我" if role == "user" else "竞赛助手"
        content = m.get("content") or m.get("contentText") or ""
        # 去掉过重 markdown 标记，保留可读性
        content = re.sub(r"```[\s\S]*?```", "[代码块]", content)
        content = re.sub(r"[#*_`]+", "", content)
        if not str(content).strip():
            continue
        story.append(Paragraph(esc(label), role_style))
        # 过长分段
        text = str(content).strip()
        chunk_size = 1800
        for i in range(0, len(text), chunk_size):
            story.append(Paragraph(esc(text[i : i + chunk_size]), body_style))

    if len(story) <= 2:
        story.append(Paragraph(esc("（暂无对话内容）"), body_style))

    doc.build(story)
    return buf.getvalue()


def markdown_to_pdf_bytes(text: str, title: str = "竞赛助手文稿") -> bytes:
    return messages_to_pdf_bytes(
        title=title,
        subtitle="由竞赛助手导出",
        messages=[{"role": "assistant", "content": text or ""}],
    )
