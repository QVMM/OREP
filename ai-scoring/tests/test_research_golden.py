"""黄金集：mock 引擎下的 research agent 行为（无外网）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.assistant.research_agent import (
    default_heuristic_planner,
    run_research_agent,
)

FIXTURE = Path(__file__).parent / "fixtures" / "research_golden.json"


def _load_cases():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_research_golden_case(case: dict):
    rounds = list(case.get("mock_search_rounds") or [[]])
    pages = case.get("mock_pages") or {}
    search_i = {"n": 0}

    def search_fn(q: str):
        i = search_i["n"]
        search_i["n"] = i + 1
        if i < len(rounds):
            return list(rounds[i])
        return list(rounds[-1]) if rounds else []

    def open_fn(url: str):
        page = pages.get(url)
        if page:
            return dict(page)
        return {"ok": False, "url": url, "error": "not_in_fixture"}

    # 对 golden 使用启发式 planner（模拟无 LLM）
    result = run_research_agent(
        case["query"],
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: default_heuristic_planner(s, max_steps=6),
        max_steps=6,
    )

    exp = case["expect"]
    assert len(result.evidence) >= int(exp.get("min_evidence") or 0)
    block = result.research_block
    for needle in exp.get("research_block_contains") or []:
        assert needle in block, f"missing {needle!r} in block for {case['id']}"
    for bad in exp.get("research_block_forbids") or []:
        assert bad not in block, f"forbidden {bad!r} in block for {case['id']}"
    reasons = exp.get("finish_reason_in")
    if reasons:
        assert result.finish_reason in reasons, (
            f"finish_reason={result.finish_reason} not in {reasons} for {case['id']}"
        )
    min_search = exp.get("min_search_steps")
    if min_search:
        n_search = sum(1 for s in result.steps if s.tool == "web_search")
        assert n_search >= int(min_search)
