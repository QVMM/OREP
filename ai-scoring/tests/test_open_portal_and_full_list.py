"""open 选链降权门户壳 + 完整名单 finish 门。"""
from __future__ import annotations

from app.services.assistant.query_anchors import (
    evidence_has_list_notice_with_pdf,
    evidence_has_list_substance,
    extract_query_anchors,
    is_full_list_demand,
    looks_like_portal_shell,
    portal_shell_rank_penalty,
    rank_hits_soft,
)
from app.services.assistant.research_agent import (
    AgentState,
    pick_open_url_from_hits,
    run_research_agent,
)
from app.services.assistant.research_planner import llm_finish_judge


def test_looks_like_portal_shell():
    assert looks_like_portal_shell(
        {"title": "河南省教育考试院", "url": "https://www.haeea.cn/index.shtml", "snippet": "首页"}
    )
    assert looks_like_portal_shell(
        {"title": "金水区人民政府", "url": "https://www.jinshui.gov.cn/", "snippet": "政务公开"}
    )
    assert not looks_like_portal_shell(
        {
            "title": "河南省教育厅关于公布2025年高等职业教育技能大赛获奖名单的通知",
            "url": "https://jyt.henan.gov.cn/2026/01-26/3313887.html",
            "snippet": "获奖名单 公示",
        }
    )


def test_rank_prefers_notice_over_exam_portal():
    q = "河南省2025职业院校技能大赛获奖名单"
    a = extract_query_anchors(q)
    hits = [
        {
            "title": "河南省教育考试院",
            "url": "https://www.haeea.cn/index.shtml",
            "snippet": "河南省 首页",
        },
        {
            "title": "河南省教育厅关于公布2025年高等职业教育技能大赛获奖名单的通知",
            "url": "https://jyt.henan.gov.cn/2026/01-26/3313887.html",
            "snippet": "河南省 技能大赛 获奖名单",
        },
        {
            "title": "河南旅游景点大全",
            "url": "https://travel.example.com/x",
            "snippet": "景点",
        },
    ]
    ranked = rank_hits_soft(hits, a, q)
    assert ranked
    assert "jyt.henan" in (ranked[0].get("url") or "")
    assert portal_shell_rank_penalty(hits[0], q) >= 10


def test_pick_open_skips_portal_for_award_query():
    st = AgentState(query="河南省2025职业院校技能大赛获奖名单")
    st.hits = [
        {
            "title": "河南省教育考试院",
            "url": "https://www.haeea.cn/index.shtml",
            "snippet": "河南省",
        },
        {
            "title": "河南省教育厅办公室关于公布2025年技能大赛获奖名单的通知",
            "url": "https://jyt.henan.gov.cn/list.html",
            "snippet": "河南省 技能大赛 获奖名单 通知",
        },
    ]
    u = pick_open_url_from_hits(st)
    assert u and "jyt.henan" in u
    assert "haeea" not in (u or "")


def test_full_list_demand_detection():
    assert is_full_list_demand(
        "请列出2025年河南省高职技能大赛全部金奖队伍完整名单（必须逐队列出）"
    )
    assert not is_full_list_demand("河南省技能大赛有什么通知")


def test_list_substance_needs_body_or_pdf():
    assert not evidence_has_list_substance(
        [{"title": "河南省教育考试院", "url": "https://www.haeea.cn/", "snippet": "首页"}]
    )
    assert evidence_has_list_substance(
        [
            {
                "title": "获奖名单通知",
                "url": "https://jyt.example.gov.cn/a.pdf",
                "snippet": "名单",
            }
        ]
    )
    long = "金奖\n" * 5 + "某校某队\n" * 10
    assert evidence_has_list_substance(
        [
            {
                "title": "公布获奖名单",
                "url": "https://jyt.example.gov.cn/n.html",
                "pageText": long,
                "fetched": True,
            }
        ]
    )


def test_agent_full_list_empty_without_list_body():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南 技能大赛 金奖"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://www.haeea.cn/index.shtml"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )
    r = run_research_agent(
        "请列出2025年河南省高职技能大赛全部金奖队伍完整名单（必须逐队列出，不准说见附件）。",
        search_fn=lambda q: [
            {
                "title": "河南省教育考试院",
                "url": "https://www.haeea.cn/index.shtml",
                "snippet": "河南省",
            }
        ],
        open_fn=lambda u: {
            "ok": True,
            "url": u,
            "title": "河南省教育考试院",
            "text": "网站首页 导航 考试动态",
            "attachments": [],
        },
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert r.finish_reason == "empty"
    assert "未找到" in r.research_block or "未检索到" in r.research_block


def test_agent_full_list_enough_with_pdf():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南 名单"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://jyt.example.gov.cn/notice.html"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )
    r = run_research_agent(
        "请列出2025年河南省高职技能大赛全部金奖队伍完整名单",
        search_fn=lambda q: [
            {
                "title": "河南省教育厅关于公布获奖名单的通知",
                "url": "https://jyt.example.gov.cn/notice.html",
                "snippet": "河南省 技能大赛 获奖名单",
            }
        ],
        open_fn=lambda u: {
            "ok": True,
            "url": u,
            "title": "河南省教育厅关于公布获奖名单的通知",
            "text": "现将名单公布如下",
            "attachments": [
                {"title": "附件1 金奖名单", "url": "https://xcoss.example.gov.cn/a.pdf"}
            ],
        },
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert r.finish_reason == "enough"


def test_finish_judge_prompt_mentions_full_list():
    seen = {}

    def fake(prompt: str) -> str:
        seen["p"] = prompt
        return '{"reason":"empty"}'

    llm_finish_judge(
        "请列出全部金奖队伍完整名单必须逐队",
        [{"title": "考试院", "url": "https://haeea.cn/", "pageText": "首页"}],
        "enough",
        llm_fn=fake,
    )
    assert "完整" in seen["p"] or "逐" in seen["p"]


def test_notice_with_pdf_signal():
    ev = [
        {
            "title": "河南省教育厅办公室关于公布2025年高等职业教育技能大赛获奖名单的通知",
            "url": "https://jyt.example.gov.cn/n.html",
            "pageText": "现将名单公布如下",
            "fetched": True,
            "attachments": [
                {"title": "附件1 名单", "url": "https://xcoss.example.gov.cn/a.pdf"}
            ],
        }
    ]
    assert evidence_has_list_notice_with_pdf(ev)
    assert evidence_has_list_substance(ev)
    # 分拆：通知页 + 附件 PDF 行
    ev2 = [
        {
            "title": "河南省教育厅关于公布获奖名单的通知",
            "url": "https://jyt.example.gov.cn/n.html",
            "snippet": "获奖名单",
        },
        {
            "title": "附件 · 获奖名单",
            "url": "https://xcoss.example.gov.cn/a.pdf",
            "snippet": "官网附件",
        },
    ]
    assert evidence_has_list_notice_with_pdf(ev2)


def test_finish_judge_corrects_empty_when_notice_and_pdf():
    """有名单通知+PDF 时，LLM 误 empty 应纠正为 enough。"""

    def fake(prompt: str) -> str:
        assert "名单通知+PDF" in prompt or "PDF" in prompt
        return '{"reason":"empty","why":"无正文"}'

    reason = llm_finish_judge(
        "河南省2025职业院校技能大赛获奖名单是什么？",
        [
            {
                "title": "河南省教育厅办公室关于公布2025年高等职业教育技能大赛获奖名单的通知",
                "url": "https://jyt.example.gov.cn/n.html",
                "pageText": "现将有关事项通知如下",
                "fetched": True,
                "attachments": [
                    {"title": "附件1", "url": "https://x.example.gov.cn/list.pdf"}
                ],
            }
        ],
        "empty",
        llm_fn=fake,
    )
    assert reason == "enough"


def test_agent_list_notice_pdf_not_empty():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南 名单"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://jyt.example.gov.cn/notice.html"},
            },
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )
    r = run_research_agent(
        "河南省2025职业院校技能大赛获奖名单是什么？",
        search_fn=lambda q: [
            {
                "title": "河南省教育厅办公室关于公布2025年高等职业教育技能大赛获奖名单的通知",
                "url": "https://jyt.example.gov.cn/notice.html",
                "snippet": "河南省 技能大赛 获奖名单",
            }
        ],
        open_fn=lambda u: {
            "ok": True,
            "url": u,
            "title": "河南省教育厅办公室关于公布2025年高等职业教育技能大赛获奖名单的通知",
            "text": "现将2025年河南省高等职业教育技能大赛获奖名单公布如下。",
            "attachments": [
                {"title": "附件1 名单", "url": "https://xcoss.example.gov.cn/a.pdf"}
            ],
        },
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert r.finish_reason == "enough"
    assert "未找到直接相关" not in r.research_block


def test_llm_open_portal_rewritten_to_notice():
    """LLM 若 open 考试院壳，有通知 hit 时应改写。"""
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南 技能大赛"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://www.haeea.cn/index.shtml"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )
    opens: list[str] = []

    def search_fn(q: str):
        return [
            {
                "title": "河南省教育考试院",
                "url": "https://www.haeea.cn/index.shtml",
                "snippet": "河南省",
            },
            {
                "title": "河南省教育厅关于公布技能大赛获奖名单的通知",
                "url": "https://jyt.henan.gov.cn/notice.html",
                "snippet": "河南省 技能大赛 获奖名单",
            },
        ]

    def open_fn(url: str):
        opens.append(url)
        if "jyt" in url:
            return {
                "ok": True,
                "url": url,
                "title": "河南省教育厅关于公布技能大赛获奖名单的通知",
                "text": "现将2025年河南省职业院校技能大赛获奖名单公布如下。" + "金奖\n" * 3,
                "attachments": [],
            }
        return {
            "ok": True,
            "url": url,
            "title": "河南省教育考试院",
            "text": "首页导航",
            "attachments": [],
        }

    r = run_research_agent(
        "河南省2025职业院校技能大赛获奖名单",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert opens
    assert any("jyt.henan" in u for u in opens)
    assert not any("haeea.cn/index" in u for u in opens)
