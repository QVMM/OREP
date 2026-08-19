"""TDD: LLM planner — 先列多条搜索假设，再按结果迭代工具。"""
from __future__ import annotations

from app.services.assistant.research_agent import (
    AgentState,
    run_research_agent,
)
from app.services.assistant.research_planner import (
    build_planner_prompt,
    parse_planner_response,
    plan_research_step,
)


def test_parse_planner_batch_hypotheses():
    raw = """
    {"thought":"需要同时覆盖教育厅、赛项通知、获奖名单","name":"web_search_batch","arguments":{"queries":[
      "河南省 2025 职业院校技能大赛",
      "河南省教育厅 技能大赛 2025 通知",
      "河南 职教 技能大赛 2025 公示",
      "河南省 职业院校技能大赛 获奖名单",
      "jyt.henan 技能大赛 2025"
    ]}}
    """
    call = parse_planner_response(raw)
    assert call["name"] == "web_search_batch"
    assert len(call["arguments"]["queries"]) == 5
    assert "教育厅" in call["arguments"]["queries"][1]


def test_parse_planner_open_and_finish():
    c1 = parse_planner_response(
        '{"thought":"标题含技能大赛","name":"open_url","arguments":{"url":"https://jyt.example.gov.cn/a.html"}}'
    )
    assert c1["name"] == "open_url"
    c2 = parse_planner_response(
        '{"name":"finish","arguments":{"reason":"empty","rationale":"无相关官方页"}}'
    )
    assert c2["name"] == "finish"
    assert c2["arguments"]["reason"] == "empty"


def test_plan_research_step_uses_injected_llm():
    state = AgentState(query="河南省2025年职业院校技能大赛")

    def fake_llm(prompt: str) -> str:
        assert "河南省" in prompt or "用户问题" in prompt
        return (
            '{"thought":"先铺5路假设","name":"web_search_batch","arguments":{"queries":'
            '["河南省 2025 职业院校技能大赛","河南省教育厅 技能大赛 2025",'
            '"河南 职教 大赛 公示 2025","河南省 技能大赛 获奖名单",'
            '"河南省 职业院校技能大赛 通知"]}}'
        )

    call = plan_research_step(state, llm_fn=fake_llm, max_steps=8, max_open=2, max_pdf=1)
    assert call["name"] == "web_search_batch"
    assert 3 <= len(call["arguments"]["queries"]) <= 5


def test_agent_runs_batch_then_open_with_scripted_llm_planner():
    """模拟：第1步5假设搜索 → 第2步 open 相关页 → finish。"""
    searches: list[str] = []
    opens: list[str] = []
    phase = {"n": 0}

    def llm_fn(prompt: str) -> str:
        phase["n"] += 1
        if phase["n"] == 1:
            return (
                '{"thought":"多假设覆盖教育厅与名单","name":"web_search_batch","arguments":{"queries":'
                '["河南省 2025 职业院校技能大赛","河南省教育厅 技能大赛",'
                '"河南 技能大赛 公示","河南省 职业院校技能大赛 通知",'
                '"河南省 技能大赛 获奖"]}}'
            )
        if phase["n"] == 2:
            return (
                '{"thought":"命中教育厅通知，打开细读","name":"open_url",'
                '"arguments":{"url":"https://jyt.example.gov.cn/skill2025.html"}}'
            )
        return '{"thought":"已有相关页","name":"finish","arguments":{"reason":"enough"}}'

    def search_fn(q: str):
        searches.append(q)
        if "技能大赛" in q or "技能" in q:
            return [
                {
                    "title": "河南省教育厅关于举办2025年职业院校技能大赛的通知",
                    "url": "https://jyt.example.gov.cn/skill2025.html",
                    "snippet": "职业院校技能大赛 赛项与报名",
                }
            ]
        return [{"title": "无关", "url": "https://example.com/x", "snippet": "其他"}]

    def open_fn(url: str):
        opens.append(url)
        return {
            "ok": True,
            "url": url,
            "title": "河南省教育厅职业院校技能大赛通知",
            "text": "现将2025年河南省职业院校技能大赛有关事项通知如下",
            "attachments": [],
        }

    def planner_fn(state: AgentState):
        return plan_research_step(
            state, llm_fn=llm_fn, max_steps=8, max_open=2, max_pdf=0
        )

    result = run_research_agent(
        "河南省2025年职业院校技能大赛信息帮我搜索一下",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=planner_fn,
        max_steps=8,
        max_open=2,
    )
    # 批量假设应触发多次 search_fn（或一次 batch 内多次）
    assert len(searches) >= 3
    assert any(s.tool == "web_search_batch" for s in result.steps) or len(searches) >= 5
    assert opens
    assert result.evidence
    assert "技能大赛" in result.research_block or "河南" in result.research_block
    assert "旅游" not in result.research_block


def test_planner_prompt_includes_must_keep_and_history():
    state = AgentState(query="河南省职业院校技能大赛")
    state.search_count = 1
    state.prior_queries = ["河南省 技能大赛"]
    state.hits = [{"title": "河南省旅游局", "url": "https://t.cn", "snippet": "景点"}]
    prompt = build_planner_prompt(state, max_steps=6, max_open=2, max_pdf=1)
    assert "用户问题" in prompt
    assert "必选" in prompt or "河南" in prompt
    assert "已用检索" in prompt or "prior" in prompt.lower() or "检索词" in prompt
    assert "web_search_batch" in prompt
