"""四项优化：空结果换引擎再 hop / 对比双侧实质 open / enough 滤 cite / 并行 open+batch。"""
from __future__ import annotations

import time
from unittest.mock import patch

from app.services.assistant.public_search import (
    looks_pdf_seeking_query,
    looks_time_sensitive_query,
    public_web_search,
)
from app.services.assistant.research_agent import (
    AgentState,
    default_heuristic_planner,
    filter_answer_cites,
    pick_open_url_for_geo,
    pick_open_urls_from_hits,
    run_research_agent,
    side_has_substantive_open,
)
from app.services.assistant.research_tools import execute_tool


COMPARE_Q = "比较河南省与山东省2025年高等职业教育技能大赛规模"


def test_time_sensitive_and_pdf_detectors():
    assert looks_time_sensitive_query("2025年最新名单")
    assert looks_time_sensitive_query("最近一年政策")
    assert not looks_time_sensitive_query("辛亥革命历史")
    assert looks_pdf_seeking_query("获奖名单附件 PDF")
    assert looks_pdf_seeking_query("通知公示下载")
    assert not looks_pdf_seeking_query("今天天气")


def test_public_web_search_failover_on_empty_baidu():
    """百度空 → 自动并行换 360/Bing。"""
    calls: list[str] = []

    def fake_baidu(q, limit=8):
        calls.append(f"baidu:{q[:20]}")
        return []

    def fake_360(q, limit=8):
        calls.append(f"so360:{q[:20]}")
        return [
            {
                "title": "教育部关于公布2025年技能大赛名单的通知",
                "url": "https://www.moe.gov.cn/a.html",
                "snippet": "2025 技能大赛 名单",
            }
        ]

    def fake_bing(q, limit=8):
        calls.append(f"bing:{q[:20]}")
        return []

    with (
        patch("app.services.assistant.public_search.search_baidu", side_effect=fake_baidu),
        patch("app.services.assistant.public_search.search_so360", side_effect=fake_360),
        patch("app.services.assistant.public_search.search_bing_cn", side_effect=fake_bing),
    ):
        hits = public_web_search("2025年职业院校技能大赛获奖名单", limit=6)
    assert hits
    assert any("moe.gov" in str(h.get("url") or "") for h in hits)
    assert any(c.startswith("so360:") for c in calls)
    assert any(c.startswith("bing:") for c in calls)


def test_public_web_search_pdf_variant_on_empty():
    """PDF 意图 + 主源空 → 补 filetype/附件 hop。"""
    qs: list[str] = []

    def fake_baidu(q, limit=8):
        qs.append(q)
        # 仅变体命中；主句空，触发 failover + pdf hop
        if "filetype:pdf" in q or "附件 PDF" in q:
            return [
                {
                    "title": "名单附件",
                    "url": "https://jyt.example.gov.cn/list.pdf",
                    "snippet": "获奖名单 PDF",
                }
            ]
        return []

    with (
        patch("app.services.assistant.public_search.search_baidu", side_effect=fake_baidu),
        patch("app.services.assistant.public_search.search_so360", return_value=[]),
        patch("app.services.assistant.public_search.search_bing_cn", return_value=[]),
    ):
        hits = public_web_search("河南省技能大赛获奖名单 附件", limit=6)
    assert hits
    assert any("filetype:pdf" in q or "附件 PDF" in q for q in qs)


def test_filter_answer_cites_drops_portal_and_zhihu():
    ev = [
        {
            "title": "知乎：如何看待大赛",
            "url": "https://www.zhihu.com/question/1",
            "snippet": "讨论",
        },
        {
            "title": "河南省教育考试院",
            "url": "https://www.haeea.cn/index.shtml",
            "snippet": "首页",
        },
        {
            "title": "河南省教育厅关于公布技能大赛名单的通知",
            "url": "https://jyt.henan.gov.cn/list.html",
            "snippet": "获奖名单 通知",
            "fetched": True,
        },
    ]
    out = filter_answer_cites(ev, "河南省技能大赛名单", finish_reason="enough")
    urls = " ".join(str(e.get("url") or "") for e in out)
    assert "jyt.henan" in urls
    assert "zhihu.com" not in urls
    assert "haeea" not in urls


def test_pick_open_urls_comparison_both_sides():
    st = AgentState(query=COMPARE_Q)
    st.hits = [
        {
            "title": "河南省高等职业教育技能大赛通知",
            "url": "https://jyt.henan.gov.cn/a.html",
            "snippet": "河南省 技能大赛 规模",
        },
        {
            "title": "山东省职业院校技能大赛通知",
            "url": "https://edu.shandong.gov.cn/b.html",
            "snippet": "山东省 技能大赛 赛道",
        },
        {
            "title": "河南省教育考试院",
            "url": "https://www.haeea.cn/",
            "snippet": "首页",
        },
    ]
    urls = pick_open_urls_from_hits(st, limit=2)
    assert len(urls) >= 2
    blob = " ".join(urls)
    assert "henan" in blob and "shandong" in blob
    # 门户壳不应优先
    assert "haeea" not in blob


def test_heuristic_forces_dual_side_open():
    st = AgentState(query=COMPARE_Q)
    st.search_count = 2
    st.prior_queries = ["河南省 技能大赛", "山东省 技能大赛"]
    st.hits = [
        {
            "title": "河南省高等职业教育技能大赛通知",
            "url": "https://jyt.henan.gov.cn/a.html",
            "snippet": "河南省 技能大赛 规模 通知",
        },
        {
            "title": "山东省职业院校技能大赛通知",
            "url": "https://edu.shandong.gov.cn/b.html",
            "snippet": "山东省 技能大赛 赛道 通知",
        },
    ]
    st.evidence = list(st.hits)
    st.opened_urls = []
    call = default_heuristic_planner(st, max_steps=10, max_open=3, max_pdf=1)
    assert call["name"] == "open_url"
    args = call["arguments"]
    # 应带 urls 并行双侧，或至少一侧
    urls = [args.get("url")] + list(args.get("urls") or [])
    urls = [u for u in urls if u]
    assert urls
    if len(urls) >= 2:
        blob = " ".join(urls)
        assert "henan" in blob and "shandong" in blob


def test_side_has_substantive_open():
    st = AgentState(query=COMPARE_Q)
    st.evidence = [
        {
            "title": "河南省技能大赛通知",
            "url": "https://jyt.henan.gov.cn/a.html",
            "pageText": "河南省高等职业教育技能大赛 现将有关事项通知如下，共设若干赛道" * 2,
            "fetched": True,
        }
    ]
    assert side_has_substantive_open(st, "河南省")
    assert not side_has_substantive_open(st, "山东省")
    u = pick_open_url_for_geo(
        AgentState(
            query=COMPARE_Q,
            hits=[
                {
                    "title": "山东省技能大赛通知",
                    "url": "https://edu.shandong.gov.cn/b.html",
                    "snippet": "山东省 技能大赛",
                }
            ],
        ),
        "山东省",
    )
    assert u and "shandong" in u


def test_web_search_batch_parallel():
    """batch 查询应并行，总耗时接近单次而非累加。"""
    started: list[float] = []

    def slow_search(q: str):
        started.append(time.time())
        time.sleep(0.15)
        # URL 必须互异，否则 batch 合并会去重
        return [{"title": q, "url": f"https://example.com/{q}", "snippet": q}]

    t0 = time.time()
    tr = execute_tool(
        {
            "name": "web_search_batch",
            "arguments": {"queries": ["河南技能", "山东技能", "教育部名单"]},
        },
        search_fn=slow_search,
        open_fn=lambda u: {"ok": True, "url": u, "text": "x" * 50},
    )
    elapsed = time.time() - t0
    assert tr.ok
    assert len(tr.data.get("hits") or []) >= 3
    # 串行约 0.45s+；并行应 < 0.40s（留余量）
    assert elapsed < 0.40, f"batch not parallel? elapsed={elapsed:.3f}s"
    assert "parallel=1" in tr.summary


def test_open_url_batch_parallel():
    opened: list[str] = []

    def open_fn(url: str):
        opened.append(url)
        time.sleep(0.12)
        return {
            "ok": True,
            "url": url,
            "title": "通知",
            "text": "河南省 山东省 技能大赛 详情正文内容足够长" * 3,
            "attachments": [],
        }

    t0 = time.time()
    tr = execute_tool(
        {
            "name": "open_url",
            "arguments": {
                "url": "https://jyt.henan.gov.cn/a.html",
                "urls": [
                    "https://jyt.henan.gov.cn/a.html",
                    "https://edu.shandong.gov.cn/b.html",
                ],
            },
        },
        search_fn=lambda q: [],
        open_fn=open_fn,
    )
    elapsed = time.time() - t0
    assert tr.ok
    assert len(tr.data.get("pages") or []) == 2
    assert elapsed < 0.30, f"open batch not parallel? elapsed={elapsed:.3f}s"
    assert set(opened) == {
        "https://jyt.henan.gov.cn/a.html",
        "https://edu.shandong.gov.cn/b.html",
    }


def test_agent_parallel_open_and_cite_filter():
    opened: list[str] = []

    def search_fn(q: str):
        return [
            {
                "title": "河南省高等职业教育技能大赛通知",
                "url": "https://jyt.henan.gov.cn/a.html",
                "snippet": "河南省 技能大赛 规模",
            },
            {
                "title": "山东省职业院校技能大赛通知",
                "url": "https://edu.shandong.gov.cn/b.html",
                "snippet": "山东省 技能大赛 规模",
            },
            {
                "title": "知乎讨论",
                "url": "https://www.zhihu.com/q/1",
                "snippet": "闲聊",
            },
        ]

    def open_fn(url: str):
        opened.append(url)
        geo = "河南" if "henan" in url else "山东"
        return {
            "ok": True,
            "url": url,
            "title": f"{geo}省技能大赛通知",
            "text": f"{geo}省高等职业教育技能大赛 规模与赛道 现将有关事项通知如下" * 4,
            "attachments": [],
        }

    result = run_research_agent(
        COMPARE_Q,
        search_fn=search_fn,
        open_fn=open_fn,
        max_steps=8,
        max_open=3,
        use_llm_planner=False,
    )
    assert len(opened) >= 1
    # 若并行扩开，同一步可开两侧
    assert result.evidence
    cites_blob = " ".join(str(e.get("url") or "") for e in result.evidence)
    # enough 时 cite 应尽量无知乎
    if (result.finish_reason or "") == "enough":
        assert "zhihu.com" not in cites_blob
