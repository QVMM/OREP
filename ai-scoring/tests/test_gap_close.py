"""纠正后：只测 tool 卫生 / 缓存 / 非法 tool，不测业务 if。"""
from __future__ import annotations

from app.services.assistant.research_agent import (
    cache_page_evidence,
    hydrate_hit_from_cache,
    pick_open_url_from_hits,
    run_research_agent,
    AgentState,
    sanitize_evidence_url,
)
from app.services.assistant.research_tools import normalize_tool_call, ALLOWED_TOOLS


def test_illegal_tool_normalized():
    call = normalize_tool_call({"name": "tool_name", "arguments": {"q": "x"}})
    assert call.get("name") == "" or call.get("invalid_tool")
    assert "tool_name" not in ALLOWED_TOOLS
    call2 = normalize_tool_call({"name": "web_search", "arguments": {"q": "ok"}})
    assert call2["name"] == "web_search"


def test_sanitize_redirect():
    assert sanitize_evidence_url("http://www.baidu.com/link?url=abc") is None
    assert sanitize_evidence_url("https://www.gov.cn/a.html")


def test_page_cache_hydrate():
    url = "https://jyt.example.gov.cn/list.html"
    cache_page_evidence(
        url,
        {
            "title": "获奖名单通知",
            "url": url,
            "pageText": "技能大赛金奖159",
            "fetched": True,
            "attachments": [{"title": "名单", "url": "https://x.example.gov.cn/a.pdf"}],
        },
    )
    hit = hydrate_hit_from_cache(
        {"title": "获奖名单", "url": url, "snippet": "技能大赛"}
    )
    assert hit.get("fetched") is True
    assert "金奖" in (hit.get("pageText") or "")


def test_pick_open_skips_failed_url():
    st = AgentState(query="河南省技能大赛")
    st.hits = [
        {"title": "A", "url": "https://a.example.gov.cn/1", "snippet": "技能"},
        {"title": "B", "url": "https://b.example.gov.cn/2", "snippet": "技能大赛"},
    ]
    st.failed_urls = ["https://a.example.gov.cn/1"]
    st.opened_urls = ["https://a.example.gov.cn/1"]
    u = pick_open_url_from_hits(st)
    assert u == "https://b.example.gov.cn/2"


def test_seed_evidence_still_usable():
    seed = [
        {
            "title": "附件 · 名单 PDF",
            "url": "https://xcoss.example.gov.cn/a.pdf",
            "snippet": "河南省 技能大赛 获奖名单",
            "pageText": "金奖159 银奖313",
            "fetched": True,
        }
    ]
    plan = iter([{"name": "finish", "arguments": {"reason": "enough"}}])
    r = run_research_agent(
        "河南省技能大赛获奖名单 PDF",
        search_fn=lambda q: [],
        open_fn=lambda u: {"ok": False, "url": u},
        planner_fn=lambda s: next(plan),
        seed_evidence=seed,
        max_steps=3,
        use_llm_planner=False,
    )
    # 不在代码里硬判 enough；seed 应进入 evidence
    assert any("pdf" in str(e.get("url") or "").lower() for e in r.evidence) or r.evidence


def test_agent_invalid_tool_does_not_crash():
    plan = iter(
        [
            {"name": "not_a_tool", "arguments": {}},
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )
    r = run_research_agent(
        "x",
        search_fn=lambda q: [],
        open_fn=lambda u: {"ok": False, "url": u},
        planner_fn=lambda s: next(plan),
        max_steps=4,
        use_llm_planner=False,
    )
    assert r.finish_reason in ("empty", "enough", "max_steps", "done")
