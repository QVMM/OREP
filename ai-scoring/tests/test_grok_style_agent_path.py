"""Grok 式主路径：Agent 自带 search/open，不依赖 Java 预搜噪声。"""
from __future__ import annotations

from app.services.assistant.research_agent import apply_research_agent_to_payload


def test_deep_search_agent_uses_search_tool_not_java_seed():
    searches: list[str] = []

    def search_fn(q: str):
        searches.append(q)
        return [
            {
                "title": "中共中央 国务院印发教育强国建设规划纲要",
                "url": "https://www.mee.gov.cn/doc.shtml",
                "snippet": "教育强国建设规划纲要（2024－2035年）",
            }
        ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "教育强国建设规划纲要（2024－2035年）",
            "text": "中共中央、国务院印发《教育强国建设规划纲要（2024－2035年）》，要求贯彻落实。",
            "attachments": [],
        }

    payload = {
        "mode": "deep_search",
        "researchAgentPrimary": True,
        "useLlmPlanner": False,
        "messages": [
            {
                "role": "user",
                "content": "告诉我这个网站上面是什么内容：https://www.mee.gov.cn/doc.shtml",
            }
        ],
        # 故意塞垃圾预搜，Grok 路径不应被带偏
        "researchCitations": [
            {
                "title": "告诉的意思|查字典",
                "url": "https://dict.example.com/tell",
                "snippet": "告诉 汉语",
            }
        ],
    }
    out = apply_research_agent_to_payload(
        payload, search_fn=search_fn, open_fn=open_fn
    )
    block = out.get("researchBlock") or ""
    assert "教育强国" in block or "规划纲要" in block
    assert "查字典" not in block
    # URL 阅读：可能不调用 search
    assert out.get("researchAgentSteps")
