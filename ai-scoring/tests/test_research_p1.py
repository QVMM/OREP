"""P1 TDD: 结构化 open、并行 open、会话 evidence、答案防「见附件」无链。"""
from __future__ import annotations

from app.services.assistant.answer_guard import guard_research_answer
from app.services.assistant.research_agent import (
    filter_evidence_for_followup,
    run_research_agent,
)
from app.services.assistant.web_research import extract_page_structure


def test_extract_page_structure_docno_date_attachments():
    html = """
    <html><body>
    <p>教职成函〔2026〕1号</p>
    <p>2026年3月13日</p>
    <a href="./W01.pdf">2025年名单附件一</a>
    <a href="https://www.moe.gov.cn/x/W02.pdf">附件二 PDF</a>
    </body></html>
    """
    base = "https://www.moe.gov.cn/srcsite/A07/t.html"
    st = extract_page_structure(html, base)
    assert "2026" in (st.get("docNo") or st.get("date") or "")
    assert st.get("date") or st.get("docNo")
    assert len(st.get("attachments") or []) >= 1
    assert any("pdf" in (a.get("url") or "").lower() for a in st["attachments"])


def test_guard_strips_jian_fujian_without_url():
    text = "获奖名单见附件1—7，请下载查看。\n\n具体内容在附件中。"
    out = guard_research_answer(text, research_block="", has_attachment_urls=False)
    assert "见附件" not in out
    assert "本对话" in out or "未提供可点击" in out or "官网" in out


def test_guard_keeps_markdown_links():
    text = "名单见 [冠军总决赛](https://www.moe.gov.cn/a.pdf)。"
    out = guard_research_answer(
        text,
        research_block="可下载附件\n- [x](https://www.moe.gov.cn/a.pdf)",
        has_attachment_urls=True,
    )
    assert "https://www.moe.gov.cn/a.pdf" in out
    assert "见附件1" not in out or "[" in out


def test_followup_filters_session_evidence_without_research():
    prior = [
        {
            "title": "河南省高职组获奖名单",
            "url": "https://example.gov.cn/h.pdf",
            "snippet": "高职组 人工智能",
        },
        {
            "title": "河南省中职组获奖名单",
            "url": "https://example.gov.cn/z.pdf",
            "snippet": "中职组",
        },
    ]
    filtered = filter_evidence_for_followup(
        "只要高职组人工智能的",
        prior,
    )
    assert len(filtered) == 1
    assert "高职" in filtered[0]["title"] or "人工智能" in (filtered[0].get("snippet") or "")


def test_parallel_open_top_k_in_agent():
    opened: list[str] = []

    def search_fn(q: str):
        return [
            {
                "title": "河南省职业院校技能大赛通知A",
                "url": "https://jyt.example.gov.cn/a.html",
                "snippet": "河南省 技能大赛",
            },
            {
                "title": "河南省职业院校技能大赛通知B",
                "url": "https://jyt.example.gov.cn/b.html",
                "snippet": "河南省 名单",
            },
        ]

    def open_fn(url: str):
        opened.append(url)
        return {
            "ok": True,
            "url": url,
            "title": "河南省通知",
            "text": "河南省职业院校技能大赛详情",
            "attachments": [],
            "docNo": "豫教〔2025〕1号",
            "date": "2025-06-01",
        }

    # 使用启发式；配置 max_open=2
    result = run_research_agent(
        "河南省2025年职业院校技能大赛",
        search_fn=search_fn,
        open_fn=open_fn,
        max_steps=6,
        max_open=2,
    )
    assert len(opened) >= 1
    assert len(opened) <= 2
    assert result.evidence
