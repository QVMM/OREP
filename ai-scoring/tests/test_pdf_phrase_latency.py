"""PDF fitz 路径、口语 phrase 清洗、跳转缓存。"""
from __future__ import annotations

from app.services.assistant.pdf_research import (
    clean_pdf_keywords,
    extract_pdf_text_from_bytes,
    keywords_in_pdf_text,
)
from app.services.assistant.public_search import (
    _cache_put,
    resolve_redirect_url,
)
from app.services.assistant.query_anchors import (
    clean_content_phrase,
    extract_query_anchors,
)


def test_clean_pdf_keywords_drops_oral():
    kws = clean_pdf_keywords(
        [
            "职业院校技能大赛",
            "请基于官方来源回答",
            "是什么",
            "获奖名单",
            "2025",
            "若搜不到请如实说明",
        ]
    )
    assert "职业院校技能大赛" in kws
    assert "获奖名单" in kws
    assert "2025" in kws
    assert not any("请基于" in k for k in kws)
    assert not any("是什么" in k for k in kws)
    assert not any("若搜不到" in k for k in kws)


def test_extract_anchors_no_oral_phrases():
    a = extract_query_anchors(
        "河南省2025职业院校技能大赛获奖名单是什么？请基于官方来源回答，若搜不到请如实说明。"
    )
    blob = " ".join(a.content_phrases + a.content_tokens)
    assert "请基于" not in blob
    assert "是什么" not in blob
    assert "如实说明" not in blob
    assert any("技能" in p or "职业" in p for p in a.content_phrases)


def test_clean_content_phrase():
    assert clean_content_phrase("职业院校技能大赛是什么") == "职业院校技能大赛"
    assert clean_content_phrase("请基于官方来源回答") == ""


def test_keywords_in_pdf_uses_cleaned():
    text = "2025年河南省高等职业教育技能大赛 金奖159"
    r = keywords_in_pdf_text(
        text, ["请基于官方来源回答", "技能大赛", "金奖", "是什么"]
    )
    assert "请基于官方来源回答" not in r
    assert r.get("技能大赛") is True
    assert r.get("金奖") is True


def test_extract_pdf_bytes_empty_guard():
    r = extract_pdf_text_from_bytes(b"")
    assert r.get("ok") is False


def test_extract_pdf_not_pdf_magic():
    r = extract_pdf_text_from_bytes(b"<html>not pdf</html>")
    assert r.get("ok") is False
    assert r.get("error") == "not_pdf"


def test_resolve_cache_hit_skips_network(monkeypatch):
    """缓存命中不再发 HTTP。"""
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise AssertionError("should not network")

    monkeypatch.setattr(
        "app.services.assistant.public_search.urlrequest.urlopen", boom
    )
    u = "http://www.baidu.com/link?url=cached_test_xyz"
    _cache_put(u, "https://jyt.example.gov.cn/notice.html")
    out = resolve_redirect_url(u)
    assert out == "https://jyt.example.gov.cn/notice.html"
    assert calls["n"] == 0
