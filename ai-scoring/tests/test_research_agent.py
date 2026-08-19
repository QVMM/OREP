"""TDD: Research Agent tool loop (injectable search/open, no network)."""
from __future__ import annotations

import pytest

from app.services.assistant.research_agent import (
    ResearchResult,
    run_research_agent,
)


def test_run_research_agent_search_open_finish_collects_evidence():
    calls: list[str] = []

    def search_fn(q: str):
        calls.append(f"search:{q}")
        return [
            {
                "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
                "url": "https://www.moe.gov.cn/notice/1.html",
                "snippet": "见附件1—7",
                "sourceType": "web",
            }
        ]

    def open_fn(url: str):
        calls.append(f"open:{url}")
        return {
            "ok": True,
            "url": url,
            "title": "教育部通知",
            "text": "现将获奖名单予以公布",
            "attachments": [
                {
                    "title": "冠军总决赛获奖名单",
                    "url": "https://www.moe.gov.cn/a.pdf",
                }
            ],
        }

    # scripted planner: search → open → finish
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "2025 职业院校技能大赛 获奖名单"}},
            {"name": "open_url", "arguments": {"url": "https://www.moe.gov.cn/notice/1.html"}},
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    def planner_fn(state):
        return next(plan)

    result = run_research_agent(
        "搜索2025年职业院校技能大赛国赛的获奖名单",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=planner_fn,
        max_steps=6,
    )

    assert isinstance(result, ResearchResult)
    assert result.finish_reason == "enough"
    assert any(s.tool == "web_search" for s in result.steps)
    assert any(s.tool == "open_url" for s in result.steps)
    assert len(result.evidence) >= 1
    assert "moe.gov.cn" in result.research_block
    assert "https://www.moe.gov.cn/a.pdf" in result.research_block
    assert "无法实时网络搜索" not in result.research_block
    assert "无法进行实时网络搜索" not in result.research_block
    assert calls[0].startswith("search:")
    assert calls[1].startswith("open:")


def test_run_research_agent_max_steps_stops():
    def search_fn(q: str):
        return [{"title": "无关", "url": "https://example.com/x", "snippet": "2025"}]

    def open_fn(url: str):
        return {"ok": True, "url": url, "title": "x", "text": "t" * 50, "attachments": []}

    def planner_fn(state):
        # always search again — should hit max_steps
        return {"name": "web_search", "arguments": {"q": f"q{state.step_count}"}}

    result = run_research_agent(
        "test",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=planner_fn,
        max_steps=3,
    )
    assert result.finish_reason == "max_steps"
    assert len([s for s in result.steps if s.tool == "web_search"]) == 3


def test_empty_evidence_research_block_is_honest_not_denial():
    def search_fn(q: str):
        return []

    def open_fn(url: str):
        return {"ok": False, "url": url, "error": "skip"}

    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "不存在的 xyzzy 名单"}},
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )

    result = run_research_agent(
        "不存在的 xyzzy 名单",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=4,
    )
    block = result.research_block
    assert "本轮" in block or "未命中" in block or "未检索到" in block
    assert "无法实时网络搜索" not in block
    assert "无法进行实时网络搜索" not in block
    assert "没有联网搜索工具" not in block


def test_invalid_tool_is_recorded_and_loop_continues():
    """非法 tool 不得当有效动作；应改写为 finish/合法工具，不崩溃。"""
    plan = iter(
        [
            {"name": "not_a_tool", "arguments": {}},
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )

    result = run_research_agent(
        "x",
        search_fn=lambda q: [],
        open_fn=lambda u: {"ok": False, "url": u},
        planner_fn=lambda s: next(plan),
        max_steps=4,
    )
    # 不得把非法名当成功工具执行后无收尾
    assert result.finish_reason in ("empty", "enough", "max_steps", "abort", "done")
    assert len(result.steps) >= 1
