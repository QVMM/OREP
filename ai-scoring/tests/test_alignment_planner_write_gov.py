"""对齐三项：planner/finish 拒凑数、写作层未找到、中文政务召回。"""
from __future__ import annotations

from app.services.assistant.answer_guard import (
    force_not_found_if_no_related_evidence,
    guard_research_answer,
    research_block_is_empty,
)
from app.services.assistant.public_search import (
    expand_cn_gov_queries,
    looks_cn_official_query,
)
from app.services.assistant.query_anchors import build_search_query_variants
from app.services.assistant.research_agent import (
    AgentState,
    build_research_block,
    run_research_agent,
)
from app.services.assistant.research_planner import (
    build_planner_prompt,
    llm_finish_judge,
    parse_planner_response,
)


def test_planner_prompt_has_multihop_and_reject_padding():
    st = AgentState(query="河南省2025职业院校技能大赛获奖名单")
    st.hits = [
        {
            "title": "河南省人民政府门户网站",
            "url": "https://www.henan.gov.cn/",
            "snippet": "首页",
        }
    ]
    p = build_planner_prompt(st, max_steps=8, max_open=2, max_pdf=1)
    assert "多 hop" in p or "第二跳" in p or "第三跳" in p
    assert "拒凑数" in p or "严禁" in p
    assert "site:gov.cn" in p
    assert "web_search_batch" in p


def test_finish_judge_empty_on_portal_shell():
    def fake_llm(prompt: str) -> str:
        assert "拒凑数" in prompt or "empty" in prompt
        return '{"reason":"empty","why":"仅门户首页"}'

    reason = llm_finish_judge(
        "河南省2025职业院校技能大赛获奖名单",
        [
            {
                "title": "河南省人民政府门户网站",
                "url": "https://www.henan.gov.cn/",
                "pageText": "政务服务 首页导航",
                "fetched": True,
            }
        ],
        "enough",
        llm_fn=fake_llm,
    )
    assert reason == "empty"


def test_finish_judge_enough_on_real_notice():
    def fake_llm(prompt: str) -> str:
        return '{"reason":"enough","why":"教育厅通知"}'

    reason = llm_finish_judge(
        "河南省2025职业院校技能大赛",
        [
            {
                "title": "河南省教育厅关于举办2025年职业院校技能大赛的通知",
                "url": "https://jyt.henan.gov.cn/a.html",
                "pageText": "现将有关事项通知如下…技能大赛…",
                "fetched": True,
            }
        ],
        "enough",
        llm_fn=fake_llm,
    )
    assert reason == "enough"


def test_build_research_block_empty_forces_not_found():
    block = build_research_block(
        "某虚构 xyzzy 名单",
        [
            {
                "title": "某市人民政府门户",
                "url": "https://www.example.gov.cn/",
                "snippet": "首页",
            }
        ],
        "empty",
    )
    assert "未找到" in block or "未检索到" in block
    assert "写作硬约束" in block
    assert research_block_is_empty(block)


def test_agent_empty_finish_not_flipped_by_soft_portal():
    """finish empty 后不得因 soft 门户证据翻回 enough。"""
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南省 技能大赛"}},
            {
                "name": "open_url",
                "arguments": {"url": "https://www.henan.gov.cn/"},
            },
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )

    def search_fn(q: str):
        return [
            {
                "title": "河南省人民政府门户网站",
                "url": "https://www.henan.gov.cn/",
                "snippet": "政务公开",
            }
        ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "河南省人民政府门户网站",
            "text": "网站首页 导航 政务服务",
            "attachments": [],
        }

    r = run_research_agent(
        "河南省2025年职业院校技能大赛获奖名单",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=6,
        use_llm_planner=False,
    )
    # 启发式可能 keep soft evidence，但 finish empty 应保留
    assert r.finish_reason == "empty"
    assert "未找到" in r.research_block or "未检索到" in r.research_block or "未命中" in r.research_block


def test_answer_guard_forces_not_found_when_research_empty():
    block = build_research_block("虚构实体", [], "empty")
    padded = (
        "根据河南省人民政府网站介绍，该省下辖多个地市，"
        "经济社会发展迅速，建议您访问官网了解更多。"
    )
    out = guard_research_answer(
        padded,
        research_block=block,
        finish_reason="empty",
    )
    assert "未找到" in out or "未检索到" in out
    # 诚实答案不重复强制
    honest = "本轮未检索到相关公开结果，建议换关键词。"
    out2 = force_not_found_if_no_related_evidence(
        honest, research_block=block, finish_reason="empty"
    )
    assert out2 == honest


def test_expand_cn_gov_queries_adds_site_gov():
    qs = expand_cn_gov_queries("河南省2025职业院校技能大赛获奖名单")
    blob = " ".join(qs)
    assert any("site:gov.cn" in q for q in qs), qs
    assert "河南" in blob or "技能" in blob
    assert looks_cn_official_query("河南省教育厅通知")


def test_variants_include_gov_site_for_official():
    vs = build_search_query_variants("河南省2025职业院校技能大赛获奖名单", max_n=8)
    blob = " ".join(vs)
    assert "site:gov.cn" in blob or "通知" in blob or "公示" in blob, vs


def test_parse_still_accepts_finish_empty():
    c = parse_planner_response(
        '{"thought":"仅门户壳","name":"finish","arguments":{"reason":"empty"}}'
    )
    assert c["name"] == "finish"
    assert c["arguments"]["reason"] == "empty"
