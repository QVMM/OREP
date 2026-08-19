"""T-P0-06: payload 接入 research agent（无外网）。"""
from __future__ import annotations

from app.services.assistant.research_agent import apply_research_agent_to_payload


def test_apply_research_agent_skipped_without_flag():
    payload = {
        "messages": [{"role": "user", "content": "搜索名单"}],
        "researchCitations": [
            {
                "title": "教育部通知",
                "url": "https://www.moe.gov.cn/n.html",
                "snippet": "获奖名单",
            }
        ],
    }
    out = apply_research_agent_to_payload(
        payload,
        open_fn=lambda u: {
            "ok": True,
            "url": u,
            "title": "t",
            "text": "公布名单",
            "attachments": [{"title": "A", "url": "https://www.moe.gov.cn/a.pdf"}],
        },
    )
    assert "researchAgentSteps" not in out


def test_apply_research_agent_enriches_block_with_attachments():
    payload = {
        "useResearchAgent": True,
        "useLlmPlanner": False,
        "messages": [{"role": "user", "content": "搜索2025职业院校技能大赛获奖名单"}],
        "researchCitations": [
            {
                "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
                "url": "https://www.moe.gov.cn/n.html",
                "snippet": "见附件",
                "sourceType": "web",
            }
        ],
    }

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "教育部通知",
            "text": "现将获奖名单予以公布",
            "attachments": [
                {"title": "冠军总决赛", "url": "https://www.moe.gov.cn/champ.pdf"},
            ],
        }

    def search_fn(q: str):
        return list(payload["researchCitations"])

    out = apply_research_agent_to_payload(
        payload, open_fn=open_fn, search_fn=search_fn, max_steps=6
    )
    assert "researchBlock" in out
    assert "champ.pdf" in out["researchBlock"]
    assert "无法进行实时网络搜索" not in out["researchBlock"]
    assert out.get("researchAgentSteps")
    assert any(s.get("tool") == "open_url" for s in out["researchAgentSteps"])
