"""URL 阅读意图：直抓页面，禁止把「告诉」等词当搜索关键词。"""
from __future__ import annotations

from app.services.assistant.url_intent import (
    extract_http_urls,
    is_url_read_intent,
    should_skip_keyword_search,
)
from app.services.assistant.research_agent import run_research_agent, apply_research_agent_to_payload


def test_extract_url_from_chinese_sentence():
    q = "告诉我这个网站上面是什么内容：https://www.mee.gov.cn/zcwj/zyygwj/202501/t20250120_1100948.shtml"
    urls = extract_http_urls(q)
    assert len(urls) == 1
    assert "mee.gov.cn" in urls[0]
    assert urls[0].endswith(".shtml")


def test_is_url_read_intent():
    assert is_url_read_intent(
        "告诉我这个网站上面是什么内容：https://www.mee.gov.cn/a.shtml"
    )
    assert is_url_read_intent("打开 https://example.com/x 看看")
    assert not is_url_read_intent("河南省技能大赛")


def test_should_skip_keyword_search_when_url_present():
    q = "告诉我这个网站上面是什么内容：https://www.mee.gov.cn/a.shtml"
    assert should_skip_keyword_search(q) is True


def test_agent_opens_url_instead_of_dictionary_search():
    opens: list[str] = []
    searches: list[str] = []
    target = "https://www.mee.gov.cn/zcwj/zyygwj/202501/t20250120_1100948.shtml"
    q = f"告诉我这个网站上面是什么内容：{target}"

    def search_fn(s: str):
        searches.append(s)
        return [
            {
                "title": "告诉的意思|告诉是什么意思 - 查字典",
                "url": "https://dict.example.com/tell",
                "snippet": "告诉 汉语词典",
            }
        ]

    def open_fn(url: str):
        opens.append(url)
        return {
            "ok": True,
            "url": url,
            "title": "中共中央 国务院印发《教育强国建设规划纲要（2024－2035年）》",
            "text": "近日，中共中央、国务院印发了《教育强国建设规划纲要（2024－2035年）》",
            "attachments": [],
        }

    # 启发式即可：有 URL 时首步 open
    result = run_research_agent(
        q,
        search_fn=search_fn,
        open_fn=open_fn,
        use_llm_planner=False,
        max_steps=4,
    )
    assert opens and target.rstrip("/") in opens[0].rstrip("/") or opens[0] == target
    assert "教育强国" in result.research_block or "规划纲要" in result.research_block
    # 不应把字典结果当依据
    assert "查字典" not in result.research_block
    assert "dict.example.com" not in result.research_block


def test_apply_payload_url_read_builds_block():
    target = "https://www.mee.gov.cn/page.shtml"
    payload = {
        "mode": "deep_search",
        "useLlmPlanner": False,
        "messages": [
            {
                "role": "user",
                "content": f"这个链接写了什么 {target}",
            }
        ],
        "researchCitations": [],
    }

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "测试政策文件标题",
            "text": "这是政策文件正文摘要内容足够长用于通过校验。",
            "attachments": [],
        }

    out = apply_research_agent_to_payload(
        payload, open_fn=open_fn, search_fn=lambda q: []
    )
    assert "测试政策文件标题" in (out.get("researchBlock") or "")
    assert target in (out.get("researchBlock") or "")
