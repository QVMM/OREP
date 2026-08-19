"""TDD: stop / re-search policy for research agent."""
from __future__ import annotations

from app.services.assistant.research_agent import (
    AgentState,
    should_search_again,
    should_stop_success,
    title_is_year_noise,
)


def test_authoritative_award_page_with_attachments_should_stop():
    state = AgentState(
        query="2025 职业院校技能大赛 获奖名单",
        evidence=[
            {
                "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
                "url": "https://www.moe.gov.cn/srcsite/xxx.html",
                "attachments": [{"title": "名单", "url": "https://www.moe.gov.cn/a.pdf"}],
            }
        ],
    )
    assert should_stop_success(state) is True
    assert should_search_again(state) is False


def test_search_hit_only_without_open_should_not_stop():
    state = AgentState(
        query="2025 职业院校技能大赛 获奖名单",
        evidence=[
            {
                "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
                "url": "https://www.moe.gov.cn/srcsite/xxx.html",
                "snippet": "见附件1—7",
            }
        ],
    )
    assert should_stop_success(state) is False


def test_year_noise_only_should_search_again():
    state = AgentState(
        query="2025年职业院校技能大赛获奖名单",
        search_count=1,
        hits=[
            {"title": "中华人民共和国2025年国民经济和社会发展统计公报", "url": "https://www.stats.gov.cn/x"},
            {"title": "2025年_百度百科", "url": "https://baike.baidu.com/x"},
        ],
        evidence=[],
    )
    assert title_is_year_noise(state.hits[0]["title"], state.query) is True
    assert should_stop_success(state) is False
    assert should_search_again(state) is True


def test_has_hits_not_opened_prefer_open_not_research():
    state = AgentState(
        query="2025 职业院校技能大赛 获奖名单",
        search_count=1,
        hits=[
            {
                "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
                "url": "https://www.moe.gov.cn/n.html",
            }
        ],
        opened_urls=[],
    )
    # 有好 hit 未 open → 不应再搜，应 open
    assert should_search_again(state) is False
