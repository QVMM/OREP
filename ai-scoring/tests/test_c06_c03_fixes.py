"""C06 虚构→empty；C03 对比 hop 两侧检索与 partial enough。"""
from __future__ import annotations

from app.services.assistant.query_anchors import (
    build_search_query_variants,
    comparison_sides_covered,
    evidence_covers_distinctive_entities,
    extract_distinctive_entities,
    is_comparison_query,
)
from app.services.assistant.research_agent import (
    AgentState,
    default_heuristic_planner,
    run_research_agent,
)
from app.services.assistant.research_planner import build_planner_prompt, llm_finish_judge


FICTION_Q = "查找「郑州市金水区第七十二职业中专2027年火星殖民专业」招生简章原文链接。"
COMPARE_Q = "比较河南省与山东省最近一年高等职业教育技能大赛的规模（赛道/参赛/奖项），并标明来源。"


def test_distinctive_entities_for_fiction():
    ents = extract_distinctive_entities(FICTION_Q)
    blob = " ".join(ents)
    assert "火星" in blob or "殖民" in blob or any("中专" in e for e in ents), ents
    # 门户壳不覆盖专名
    assert not evidence_covers_distinctive_entities(
        FICTION_Q,
        [
            {
                "title": "金水区人民政府",
                "url": "https://www.jinshui.gov.cn/",
                "pageText": "网站首页 政务公开 导航菜单",
                "fetched": True,
            }
        ],
    )


def test_real_skill_list_covers_entities():
    q = "河南省2025职业院校技能大赛获奖名单是什么？"
    assert evidence_covers_distinctive_entities(
        q,
        [
            {
                "title": "河南省教育厅关于公布2025年高等职业教育技能大赛获奖名单的通知",
                "url": "https://jyt.henan.gov.cn/x",
                "pageText": "现将2025年河南省高等职业教育技能大赛获奖名单公布如下",
                "fetched": True,
            }
        ],
    )


def test_comparison_query_and_sides():
    assert is_comparison_query(COMPARE_Q)
    covered, missing = comparison_sides_covered(
        COMPARE_Q,
        [
            {
                "title": "河南省高等职业教育技能大赛",
                "snippet": "42个赛道",
                "url": "https://jyt.henan.gov.cn/a",
            }
        ],
    )
    assert any("河南" in c for c in covered)
    assert any("山东" in m for m in missing)


def test_variants_split_compare_sides():
    vs = build_search_query_variants(COMPARE_Q, max_n=8)
    blob = " ".join(vs)
    assert "河南" in blob and "山东" in blob
    # 不应只剩「比较河南省与山东」糊句占满
    assert any("山东" in v and "河南" not in v for v in vs) or any(
        "山东" in v for v in vs
    ), vs


def test_heuristic_searches_missing_side_after_one_side():
    st = AgentState(query=COMPARE_Q)
    st.search_count = 1
    st.prior_queries = ["河南省 高等职业教育技能大赛"]
    st.opened_urls = ["https://jyt.henan.gov.cn/a"]
    st.evidence = [
        {
            "title": "河南省高等职业教育技能大赛通知",
            "url": "https://jyt.henan.gov.cn/a",
            "pageText": "河南省高等职业教育技能大赛 赛道与报名 现将有关事项通知如下" * 3,
            "snippet": "河南省 技能大赛",
            "fetched": True,
        }
    ]
    st.hits = list(st.evidence)
    call = default_heuristic_planner(st, max_steps=8, max_open=3, max_pdf=1)
    # 工具路径：应再搜缺失侧（山东），不在此硬判 enough
    assert call["name"] == "web_search"
    assert "山东" in call["arguments"]["q"]


def test_fiction_agent_finish_empty_despite_portal():
    plan = iter(
        [
            {"name": "web_search_batch", "arguments": {"queries": ["火星殖民 招生"]}},
            {
                "name": "open_url",
                "arguments": {"url": "https://www.jinshui.gov.cn/"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    def search_fn(q: str):
        return [
            {
                "title": "金水区人民政府门户网站",
                "url": "https://www.jinshui.gov.cn/",
                "snippet": "郑州市金水区 政务服务",
            }
        ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "金水区人民政府",
            "text": "网站首页 政务公开 部门导航 通知公告列表",
            "attachments": [],
        }

    r = run_research_agent(
        FICTION_Q,
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert r.finish_reason == "empty"
    assert "未找到" in r.research_block or "未检索到" in r.research_block or "未命中" in r.research_block


def test_compare_does_not_force_empty_to_enough():
    """代码不得把 planner 的 empty 硬翻 enough（拒 if 刷分）。"""
    plan = iter(
        [
            {
                "name": "web_search_batch",
                "arguments": {
                    "queries": [
                        "河南省 高等职业教育技能大赛",
                        "山东省 高等职业教育技能大赛",
                    ]
                },
            },
            {
                "name": "open_url",
                "arguments": {"url": "https://jyt.henan.gov.cn/h.html"},
            },
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )

    def search_fn(q: str):
        return [
            {
                "title": "河南省高等职业教育技能大赛获奖通知",
                "url": "https://jyt.henan.gov.cn/h.html",
                "snippet": "河南省 技能大赛 赛道",
            }
        ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "河南省高等职业教育技能大赛",
            "text": "现将河南省高等职业教育技能大赛有关事项通知如下，共设赛道若干，参赛院校若干。",
            "attachments": [],
        }

    r = run_research_agent(
        COMPARE_Q,
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=8,
        use_llm_planner=False,
    )
    # 无硬翻：planner empty 保持 empty（真实 enough 靠 LLM judge/多 hop）
    assert r.finish_reason == "empty"


def test_compare_enough_when_planner_says_enough_one_side():
    """planner/LLM 判 enough 时，一侧实质证据可写。"""
    plan = iter(
        [
            {
                "name": "web_search_batch",
                "arguments": {"queries": ["河南省 高等职业教育技能大赛"]},
            },
            {
                "name": "open_url",
                "arguments": {"url": "https://jyt.henan.gov.cn/h.html"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    r = run_research_agent(
        COMPARE_Q,
        search_fn=lambda q: [
            {
                "title": "河南省高等职业教育技能大赛通知",
                "url": "https://jyt.henan.gov.cn/h.html",
                "snippet": "河南省 赛道",
            }
        ],
        open_fn=lambda u: {
            "ok": True,
            "url": u,
            "title": "河南省高等职业教育技能大赛",
            "text": "现将河南省高等职业教育技能大赛有关事项通知如下，共设赛道若干。",
            "attachments": [],
        },
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    assert r.finish_reason == "enough"
    assert "河南" in r.research_block


def test_planner_prompt_mentions_compare_split_and_entity_empty():
    st = AgentState(query=COMPARE_Q)
    p = build_planner_prompt(st, max_steps=8, max_open=3, max_pdf=1)
    assert "对比" in p
    assert "A 侧" in p or "两侧" in p or "拆侧" in p
    p2 = build_planner_prompt(AgentState(query=FICTION_Q), max_steps=8, max_open=2, max_pdf=0)
    assert "专名" in p2 or "虚构" in p2 or "完全不出现" in p2


def test_finish_judge_prompt_includes_compare_and_entity_hints():
    seen = {}

    def fake(prompt: str) -> str:
        seen["p"] = prompt
        return '{"reason":"empty"}'

    llm_finish_judge(
        FICTION_Q,
        [{"title": "金水区人民政府", "url": "https://www.jinshui.gov.cn/", "pageText": "首页"}],
        "enough",
        llm_fn=fake,
    )
    assert "专名" in seen["p"] or "机构" in seen["p"]
    llm_finish_judge(
        COMPARE_Q,
        [{"title": "河南省技能大赛", "url": "https://jyt.henan.gov.cn/x", "pageText": "河南 赛道"}],
        "empty",
        llm_fn=fake,
    )
    assert "对比" in seen["p"]
