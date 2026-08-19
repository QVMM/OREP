"""防糊弄：省级查询不得用全国/他省结果当依据。"""
from __future__ import annotations

from app.services.assistant.research_agent import run_research_agent


def test_henan_query_rejects_shandong_and_national_as_evidence():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南省 职业院校技能大赛"}},
            {"name": "finish", "arguments": {"reason": "empty"}},
        ]
    )

    def search_fn(q: str):
        return [
            {
                "title": "第十八届山东省职业院校技能大赛获奖名单",
                "url": "https://example.com/sd",
                "snippet": "山东省教育厅",
            },
            {
                "title": "全国职业院校技能大赛官网",
                "url": "http://www.nvsc.com.cn/",
                "snippet": "大赛点亮人生",
            },
            {
                "title": "教育部世界职业院校技能大赛获奖名单",
                "url": "https://www.moe.gov.cn/w",
                "snippet": "世界赛",
            },
        ]

    result = run_research_agent(
        "河南省2025年职业院校技能大赛的信息帮我搜一搜",
        search_fn=search_fn,
        open_fn=lambda u: {"ok": False, "url": u},
        planner_fn=lambda s: next(plan),
        max_steps=4,
    )
    assert result.evidence == []
    assert "山东省" not in result.research_block
    assert "nvsc.com.cn" not in result.research_block
    # 空结果诚实句，不得伪装有依据
    assert "本轮" in result.research_block or "未命中" in result.research_block
    assert "无法进行实时网络搜索" not in result.research_block


def test_henan_hit_kept():
    plan = iter(
        [
            {"name": "web_search", "arguments": {"q": "河南省"}},
            {
                "name": "open_url",
                "arguments": {"url": "http://jyt.example.gov.cn/henan.html"},
            },
            {"name": "finish", "arguments": {"reason": "enough"}},
        ]
    )

    def search_fn(q: str):
        return [
            {
                "title": "河南省教育厅关于2025年职业院校技能大赛的通知",
                "url": "http://jyt.example.gov.cn/henan.html",
                "snippet": "河南省职业院校技能大赛",
            }
        ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "河南省教育厅通知",
            "text": "现将河南省2025年职业院校技能大赛有关事项通知如下",
            "attachments": [],
        }

    result = run_research_agent(
        "河南省2025年职业院校技能大赛",
        search_fn=search_fn,
        open_fn=open_fn,
        planner_fn=lambda s: next(plan),
        max_steps=6,
    )
    assert len(result.evidence) >= 1
    assert "河南" in result.research_block
    assert "山东" not in result.research_block
