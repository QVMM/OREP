"""Research Agent 工具协议与执行（search/open/pdf 可注入，不绑定具体搜索引擎）。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable


SearchFn = Callable[[str], list[dict[str, Any]]]
OpenFn = Callable[[str], dict[str, Any]]
FetchPdfFn = Callable[..., dict[str, Any]]

ALLOWED_TOOLS = frozenset({"web_search", "web_search_batch", "open_url", "fetch_pdf", "finish"})


@dataclass
class ToolResult:
    ok: bool
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    summary: str = ""


def normalize_tool_call(raw: Any) -> dict[str, Any]:
    """把 planner 输出规范成 {name, arguments}。

    非法 tool 名（如 tool_name）一律降级为空 name，由上层改写为 finish/跳过。
    """
    if not isinstance(raw, dict):
        return {"name": "", "arguments": {}}
    name = str(raw.get("name") or raw.get("tool") or "").strip()
    # 常见幻觉字段名
    if name in ("tool_name", "toolName", "function", "action", "…", "..."):
        name = ""
    args = raw.get("arguments") if isinstance(raw.get("arguments"), dict) else {}
    if not args and isinstance(raw.get("args"), dict):
        args = raw["args"]
    if name and name not in ALLOWED_TOOLS:
        # 保留原始以便日志，但标记非法
        return {"name": "", "arguments": args, "invalid_tool": name}
    return {"name": name, "arguments": dict(args)}


def execute_tool(
    call: dict[str, Any],
    *,
    search_fn: SearchFn,
    open_fn: OpenFn,
    fetch_pdf_fn: FetchPdfFn | None = None,
) -> ToolResult:
    name = str(call.get("name") or "").strip()
    args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
    invalid = str(call.get("invalid_tool") or "").strip()

    if invalid or (name and name not in ALLOWED_TOOLS):
        bad = invalid or name or "unknown"
        return ToolResult(
            ok=False,
            name=bad,
            error="unknown_tool",
            summary=f"error:unknown_tool:{bad}",
        )
    if not name:
        return ToolResult(
            ok=False,
            name="unknown",
            error="unknown_tool",
            summary="error:unknown_tool:empty",
        )

    if name == "web_search":
        q = str(args.get("q") or args.get("query") or "").strip()
        if not q:
            return ToolResult(
                ok=False,
                name=name,
                error="missing_query",
                summary="error:missing_query",
            )
        hits = search_fn(q) or []
        if not isinstance(hits, list):
            hits = []
        return ToolResult(
            ok=True,
            name=name,
            data={"query": q, "hits": hits},
            summary=f"search hits={len(hits)} q={q[:40]}",
        )

    if name == "web_search_batch":
        raw_qs = args.get("queries") if isinstance(args.get("queries"), list) else []
        queries: list[str] = []
        for q in raw_qs:
            s = str(q or "").strip()
            if 1 <= len(s) <= 48 and s not in queries:
                queries.append(s)
            if len(queries) >= 5:
                break
        if not queries:
            return ToolResult(
                ok=False,
                name=name,
                error="missing_queries",
                summary="error:missing_queries",
            )
        # 并行检索各假设，压串行时延
        per_q: dict[str, list[dict[str, Any]]] = {}
        workers = min(4, max(1, len(queries)))

        def _one(qq: str) -> tuple[str, list[dict[str, Any]]]:
            try:
                batch = search_fn(qq) or []
            except Exception:
                batch = []
            if not isinstance(batch, list):
                batch = []
            return qq, batch

        if len(queries) == 1:
            qq, batch = _one(queries[0])
            per_q[qq] = batch
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futs = [ex.submit(_one, qq) for qq in queries]
                for fut in as_completed(futs):
                    try:
                        qq, batch = fut.result()
                    except Exception:
                        continue
                    per_q[qq] = batch
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        # 保持 queries 顺序合并，结果可复现
        for qq in queries:
            for h in per_q.get(qq) or []:
                if not isinstance(h, dict):
                    continue
                key = str(h.get("url") or h.get("title") or "")
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(h)
        return ToolResult(
            ok=True,
            name=name,
            data={"queries": queries, "hits": merged},
            summary=f"batch n={len(queries)} hits={len(merged)} parallel=1",
        )

    if name == "open_url":
        # 单 url 或 urls[] 批量并行 open（压串行时延）
        urls: list[str] = []
        single = str(args.get("url") or "").strip()
        if single:
            urls.append(single)
        raw_urls = args.get("urls") if isinstance(args.get("urls"), list) else []
        for u in raw_urls:
            s = str(u or "").strip()
            if s.startswith("http") and s not in urls:
                urls.append(s)
            if len(urls) >= 4:
                break
        if not urls:
            return ToolResult(
                ok=False,
                name=name,
                error="missing_url",
                summary="error:missing_url",
            )

        def _open_one(u: str) -> tuple[str, dict[str, Any]]:
            try:
                page = open_fn(u) or {}
            except Exception as e:
                page = {"ok": False, "url": u, "error": str(e)[:80]}
            if not isinstance(page, dict):
                page = {"ok": False, "url": u, "error": "bad_open_result"}
            return u, page

        pages: list[dict[str, Any]] = []
        if len(urls) == 1:
            u, page = _open_one(urls[0])
            pages.append({"url": u, "page": page})
        else:
            with ThreadPoolExecutor(max_workers=min(3, len(urls))) as ex:
                futs = {ex.submit(_open_one, u): u for u in urls}
                # 按输入顺序收集
                tmp: dict[str, dict[str, Any]] = {}
                for fut in as_completed(futs):
                    try:
                        u, page = fut.result()
                    except Exception as e:
                        u = futs[fut]
                        page = {"ok": False, "url": u, "error": str(e)[:80]}
                    tmp[u] = page
                for u in urls:
                    pages.append({"url": u, "page": tmp.get(u) or {"ok": False, "url": u}})

        # 兼容单开：保留 page/url 字段
        primary = pages[0]
        page0 = primary.get("page") if isinstance(primary.get("page"), dict) else {}
        ok0 = bool(page0.get("ok", True))
        atts0 = page0.get("attachments") if isinstance(page0.get("attachments"), list) else []
        ok_n = sum(
            1
            for p in pages
            if isinstance(p.get("page"), dict) and bool(p["page"].get("ok", True))
        )
        return ToolResult(
            ok=ok0 if len(urls) == 1 else ok_n > 0,
            name=name,
            data={
                "page": page0,
                "url": primary.get("url") or urls[0],
                "pages": pages,
                "urls": urls,
            },
            summary=(
                f"open ok={ok0} atts={len(atts0)} url={(primary.get('url') or '')[:60]}"
                if len(urls) == 1
                else f"open_batch n={len(urls)} ok={ok_n} parallel=1"
            ),
            error=None
            if (ok0 if len(urls) == 1 else ok_n > 0)
            else str(page0.get("error") or "open_failed"),
        )


    if name == "fetch_pdf":
        url = str(args.get("url") or "").strip()
        if not url:
            return ToolResult(
                ok=False,
                name=name,
                error="missing_url",
                summary="error:missing_url",
            )
        if fetch_pdf_fn is None:
            return ToolResult(
                ok=False,
                name=name,
                error="pdf_unavailable",
                summary="error:pdf_unavailable",
            )
        keywords = args.get("keywords") if isinstance(args.get("keywords"), list) else []
        try:
            from app.services.assistant.pdf_research import clean_pdf_keywords

            keywords = clean_pdf_keywords(keywords)
        except Exception:
            keywords = [str(k).strip() for k in keywords if str(k).strip()][:8]
        max_pages = int(args.get("maxPages") or args.get("max_pages") or 5)
        max_pages = max(1, min(max_pages, 8))
        result = fetch_pdf_fn(url, max_pages=max_pages, keywords=keywords) or {}
        if not isinstance(result, dict):
            result = {"ok": False, "error": "bad_pdf_result"}
        ok = bool(result.get("ok"))
        hits = result.get("keywordHits") if isinstance(result.get("keywordHits"), dict) else {}
        hit_n = sum(1 for v in hits.values() if v)
        return ToolResult(
            ok=ok,
            name=name,
            data={"pdf": result, "url": url},
            summary=f"pdf ok={ok} pages={result.get('pages')} kw_hits={hit_n}",
            error=None if ok else str(result.get("error") or "pdf_failed"),
        )

    # finish
    reason = str(args.get("reason") or "done").strip() or "done"
    return ToolResult(
        ok=True,
        name="finish",
        data={"reason": reason},
        summary=f"finish:{reason}",
    )
