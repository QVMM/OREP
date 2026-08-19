"""TDD: research tool executor."""
from __future__ import annotations

from app.services.assistant.research_tools import execute_tool, normalize_tool_call


def test_normalize_tool_call_variants():
    assert normalize_tool_call({"name": "web_search", "arguments": {"q": "a"}})["name"] == "web_search"
    assert normalize_tool_call({"tool": "open_url", "args": {"url": "http://x"}})["arguments"]["url"] == "http://x"
    assert normalize_tool_call(None)["name"] == ""


def test_web_search_missing_query():
    r = execute_tool(
        {"name": "web_search", "arguments": {}},
        search_fn=lambda q: [{"title": "x"}],
        open_fn=lambda u: {},
    )
    assert r.ok is False
    assert r.error == "missing_query"


def test_open_url_missing_url():
    r = execute_tool(
        {"name": "open_url", "arguments": {}},
        search_fn=lambda q: [],
        open_fn=lambda u: {"ok": True},
    )
    assert r.ok is False
    assert r.error == "missing_url"


def test_unknown_tool():
    r = execute_tool(
        {"name": "hack", "arguments": {}},
        search_fn=lambda q: [],
        open_fn=lambda u: {},
    )
    assert r.ok is False
    assert r.error == "unknown_tool"
