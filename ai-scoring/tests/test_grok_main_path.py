"""Grok 主路径回归：geo 误抽、多省 soft、failed url、cite 禁跳转。"""
from __future__ import annotations

from app.services.assistant.query_anchors import (
    extract_geo_phrases,
    extract_query_anchors,
    hit_passes_anchors,
    rank_hits_soft,
)
from app.services.assistant.research_agent import (
    AgentState,
    build_research_block,
    default_heuristic_planner,
    is_low_quality_page,
    is_unresolved_redirect_url,
    run_research_agent,
    sanitize_evidence_url,
)


def test_geo_not_swallow_compare_prefix():
    geos = extract_geo_phrases("比较一下河南省与山东省最近一年高等职业教育技能大赛")
    assert "河南省" in geos
    assert "山东省" in geos
    assert not any("比较" in g for g in geos)


def test_geo_not_what_district():
    a = extract_query_anchors(
        "OpenAI 官方文档里 Responses API 和 Chat Completions 有什么区别？"
    )
    assert not any("区" in r for r in a.required)
    assert a.required == []


def test_multi_geo_either_side_passes_strict():
    a = extract_query_anchors("河南省与山东省职业院校技能大赛规模对比")
    assert len(a.required) >= 2
    henan = {
        "title": "河南省高等职业教育技能大赛",
        "snippet": "42个赛道",
        "url": "https://jyt.example.gov.cn/h",
    }
    shandong = {
        "title": "山东省职业院校技能大赛高职组",
        "snippet": "41个赛道",
        "url": "https://edu.example.gov.cn/s",
    }
    assert hit_passes_anchors(henan, a, strict=True)
    assert hit_passes_anchors(shandong, a, strict=True)


def test_rank_keeps_english_docs():
    a = extract_query_anchors("OpenAI Responses API vs Chat Completions")
    hits = [
        {
            "title": "Migrate to the Responses API - OpenAI",
            "url": "https://developers.openai.com/api/docs/guides/migrate-to-responses",
            "snippet": "Responses API evolution of Chat Completions",
        },
        {
            "title": "百度百科",
            "url": "https://baike.baidu.com/x",
            "snippet": "旅游景点",
        },
    ]
    ranked = rank_hits_soft(hits, a, "OpenAI Responses API vs Chat Completions")
    assert ranked
    assert "openai.com" in ranked[0]["url"]


def test_sanitize_drops_baidu_link():
    assert sanitize_evidence_url("http://www.baidu.com/link?url=abc") is None
    assert sanitize_evidence_url("https://www.gov.cn/a.html") == "https://www.gov.cn/a.html"
    assert is_unresolved_redirect_url("https://www.baidu.com/link?url=x")


def test_maint_page_low_quality():
    assert is_low_quality_page(
        {"title": "网站维护中", "text": "维护", "ok": True},
        "https://www.mee.gov.cn/weihu/",
    )


def test_block_strips_baidu_link_cites():
    block = build_research_block(
        "河南省技能大赛",
        [
            {
                "title": "假跳转",
                "url": "http://www.baidu.com/link?url=xxx",
                "snippet": "河南省技能大赛",
            },
            {
                "title": "河南省教育厅通知",
                "url": "https://jyt.example.gov.cn/n",
                "snippet": "河南省职业院校技能大赛获奖名单",
            },
        ],
    )
    assert "baidu.com/link" not in block
    assert "jyt.example.gov.cn" in block


def test_heuristic_skips_failed_url():
    st = AgentState(query="生态环境部官网主要职责")
    st.search_count = 1
    st.hits = [
        {
            "title": "生态环境部维护",
            "url": "https://www.mee.gov.cn/weihu/",
            "snippet": "生态环境部",
        },
        {
            "title": "生态环境部职责",
            "url": "https://www.mee.gov.cn/zjhb/zyzz/x.html",
            "snippet": "主要职责 生态环境",
        },
    ]
    st.failed_urls = ["https://www.mee.gov.cn/weihu/"]
    st.opened_urls = ["https://www.mee.gov.cn/weihu/"]
    call = default_heuristic_planner(st, max_steps=8, max_open=3)
    if call["name"] == "open_url":
        assert "weihu" not in call["arguments"]["url"]


def test_agent_failed_url_not_reopened():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "生态环境部 职责"}},
            {"name": "open_url", "arguments": {"url": "https://www.mee.gov.cn/weihu/"}},
            {"name": "open_url", "arguments": {"url": "https://www.mee.gov.cn/weihu/"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://www.mee.gov.cn/zjhb/zyzz.html"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    def search_fn(q):
        return [
            {
                "title": "维护",
                "url": "https://www.mee.gov.cn/weihu/",
                "snippet": "生态环境部 官网",
            },
            {
                "title": "生态环境部主要职责",
                "url": "https://www.mee.gov.cn/zjhb/zyzz.html",
                "snippet": "主要职责 生态环境基本制度 生态环境部",
            },
        ]

    def open_fn(url):
        if "weihu" in url:
            return {
                "ok": True,
                "url": url,
                "title": "网站维护",
                "text": "维护中",
                "attachments": [],
            }
        return {
            "ok": True,
            "url": url,
            "title": "生态环境部主要职责",
            "text": "生态环境部负责建立健全生态环境基本制度，履行主要职责。" * 5,
            "attachments": [],
        }

    r = run_research_agent(
        "生态环境部官网的域名和主要职责简介是什么",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=8,
        max_open=3,
        use_llm_planner=False,
    )
    weihu_opens = sum(
        1
        for s in r.steps
        if s.tool == "open_url" and "weihu" in str(s.args.get("url") or "")
    )
    # 维护页不应被反复 open；选链应偏向职责页
    assert weihu_opens <= 1
    assert r.finish_reason == "enough"
    assert "生态环境" in r.research_block or "职责" in r.research_block
