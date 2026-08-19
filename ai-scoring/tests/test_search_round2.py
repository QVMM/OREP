"""Round2: 检索规范化、主题同义、禁重复检索假设。"""
from __future__ import annotations

from app.services.assistant.public_search import normalize_search_query
from app.services.assistant.query_anchors import (
    build_search_query_variants,
    extract_query_anchors,
    hit_passes_anchors,
    next_unused_query,
)
from app.services.assistant.research_agent import (
    AgentState,
    build_research_block,
    default_heuristic_planner,
)


def test_normalize_strips_oral_tail():
    q = normalize_search_query(
        "河南省2025职业院校技能大赛获奖名单是什么？请基于官方来源回答，若搜不到请如实说明。"
    )
    assert "是什么" not in q
    assert "请基于" not in q
    assert "河南" in q
    assert "技能" in q or "职业" in q


def test_variants_include_gaozhi_synonym_and_no_dup_prior():
    q = "河南省2025职业院校技能大赛获奖名单"
    vs = build_search_query_variants(q, max_n=6)
    blob = " ".join(vs)
    assert any("高等职业教育" in v or "高职" in v for v in vs), vs
    assert any("2025" in v for v in vs)
    # prior 去重
    prior = [vs[0]]
    nxt = next_unused_query(q, prior)
    assert nxt is None or nxt != vs[0]


def test_topic_synonym_matches_higher_voc_title():
    a = extract_query_anchors("河南省2025年职业院校技能大赛获奖名单")
    hit = {
        "title": "河南省教育厅办公室关于公布2025年河南省高等职业教育技能大赛获奖名单的通知",
        "snippet": "金奖银奖铜奖",
        "url": "https://jyt.example.gov.cn/x.html",
    }
    assert hit_passes_anchors(hit, a, strict=True) is True


def test_portal_tourism_still_rejected():
    a = extract_query_anchors("河南省2025年职业院校技能大赛获奖名单")
    assert (
        hit_passes_anchors(
            {
                "title": "河南旅游景点大全",
                "snippet": "河南省景点介绍",
                "url": "http://www.hnta.cn/x",
            },
            a,
            strict=True,
        )
        is False
    )
    assert (
        hit_passes_anchors(
            {
                "title": "河南省（中国华中地区省级行政区）_百度百科",
                "snippet": "省会郑州",
                "url": "https://baike.baidu.com/x",
            },
            a,
            strict=True,
        )
        is False
    )


def test_heuristic_first_step_is_batch():
    st = AgentState(query="河南省2025职业院校技能大赛获奖名单是什么")
    call = default_heuristic_planner(st, max_steps=8, max_open=3)
    assert call["name"] in ("web_search_batch", "web_search")
    if call["name"] == "web_search_batch":
        qs = call["arguments"]["queries"]
        assert len(qs) >= 2
        assert len(set(qs)) == len(qs)


def test_heuristic_never_repeats_prior_query():
    st = AgentState(query="河南省2025职业院校技能大赛获奖名单")
    st.search_count = 1
    st.prior_queries = ["河南省 2025 职业院校技能大赛"]
    st.hits = []
    call = default_heuristic_planner(st, max_steps=8, max_open=3)
    if call["name"] == "web_search":
        assert call["arguments"]["q"] not in st.prior_queries
    elif call["name"] == "web_search_batch":
        for q in call["arguments"]["queries"]:
            assert q not in st.prior_queries


def test_degraded_block_when_only_school_news():
    q = "河南省2025职业院校技能大赛获奖名单"
    # 若 strict 因某种原因空、soft 有院校喜报
    evidence = [
        {
            "title": "喜报！我校在2025年河南省高等职业教育技能大赛中获21项奖励",
            "url": "https://school.edu.cn/x",
            "snippet": "河南省高等职业教育技能大赛金奖2项",
            "sourceType": "web",
        }
    ]
    block = build_research_block(q, evidence, "enough")
    assert "河南" in block
    assert "技能大赛" in block or "职业教育" in block
    # 不得空
    assert "未命中" not in block or "次级" in block
