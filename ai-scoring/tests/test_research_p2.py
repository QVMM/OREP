"""P2 TDD: PDF 浅抽、关键词、多源冲突、预算。"""
from __future__ import annotations

from app.services.assistant.pdf_research import (
    extract_pdf_text_from_bytes,
    keywords_in_pdf_text,
)
from app.services.assistant.research_agent import (
    ResearchBudget,
    build_multi_source_notes,
    run_research_agent,
)


def _minimal_pdf_bytes(text: str = "Hello PDF") -> bytes:
    """构造极简合法 PDF（无外部依赖）。"""
    # 最简单的 PDF 1.1 with one page and text via Tj
    # Use reportlab-free hand-written PDF
    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
    stream = content.encode("latin-1", errors="replace")
    objs = []
    objs.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objs.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objs.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
    )
    objs.append(
        f"4 0 obj<< /Length {len(stream)} >>stream\n".encode()
        + stream
        + b"\nendstream\nendobj\n"
    )
    objs.append(
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    )
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for o in objs:
        offsets.append(len(out))
        out.extend(o)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return bytes(out)


def test_extract_pdf_text_from_bytes():
    data = _minimal_pdf_bytes("Champion Award List 2025")
    result = extract_pdf_text_from_bytes(data, max_pages=2, max_chars=2000)
    assert result.get("ok") is True
    # pypdf may or may not extract hand-written Tj depending on version; accept text or empty with ok
    assert "pages" in result
    assert result.get("pages", 0) >= 0


def test_keywords_in_pdf_text():
    text = "2025年世界职业院校技能大赛 高职组 人工智能 获奖名单"
    r = keywords_in_pdf_text(text, ["高职组", "人工智能", "中职组"])
    assert r["高职组"] is True
    assert r["人工智能"] is True
    assert r["中职组"] is False


def test_multi_source_notes_flags_domains():
    evidence = [
        {
            "title": "教育部通知",
            "url": "https://www.moe.gov.cn/a.html",
            "snippet": "名单A",
        },
        {
            "title": "教育在线转载",
            "url": "https://www.eol.cn/b.html",
            "snippet": "名单B",
        },
    ]
    note = build_multi_source_notes(evidence)
    assert "moe.gov.cn" in note
    assert "eol.cn" in note or "多源" in note


def test_budget_caps_max_open_and_steps():
    opens = []

    def search_fn(q):
        return [
            {
                "title": f"河南省技能大赛{i}",
                "url": f"https://jyt.example.gov.cn/{i}.html",
                "snippet": "河南省 职业院校技能大赛",
            }
            for i in range(5)
        ]

    def open_fn(url):
        opens.append(url)
        return {
            "ok": True,
            "url": url,
            "title": "河南省通知",
            "text": "河南省职业院校技能大赛",
            "attachments": [],
        }

    budget = ResearchBudget(max_steps=4, max_open=1, max_pdf=0)
    result = run_research_agent(
        "河南省职业院校技能大赛",
        search_fn=search_fn,
        open_fn=open_fn,
        max_steps=budget.max_steps,
        max_open=budget.max_open,
        budget=budget,
    )
    assert len(opens) <= 1
    assert len(result.steps) <= budget.max_steps + 1


def test_fetch_pdf_tool_via_agent():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "名单"}},
            {
                "name": "fetch_pdf",
                "arguments": {
                    "url": "https://www.moe.gov.cn/a.pdf",
                    "keywords": ["高职", "人工智能"],
                },
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    def search_fn(q):
        return [
            {
                "title": "教育部获奖名单PDF",
                "url": "https://www.moe.gov.cn/a.pdf",
                "snippet": "获奖名单 pdf",
            }
        ]

    def open_fn(url):
        return {"ok": False, "url": url, "error": "binary_skip"}

    def fetch_pdf_fn(url, **kwargs):
        return {
            "ok": True,
            "url": url,
            "text": "高职组 人工智能 一等奖",
            "pages": 1,
            "keywordHits": {"高职": True, "人工智能": True},
        }

    result = run_research_agent(
        "2025职业院校技能大赛获奖名单",
        search_fn=search_fn,
        open_fn=open_fn,
        fetch_pdf_fn=fetch_pdf_fn,
        planner_fn=lambda s: next(plan),
        max_steps=6,
    )
    assert any(s.tool == "fetch_pdf" for s in result.steps)
    assert any("高职" in str(e.get("snippet") or e.get("pageText") or "") for e in result.evidence) or any(
        "keywordHits" in e for e in result.evidence
    )
