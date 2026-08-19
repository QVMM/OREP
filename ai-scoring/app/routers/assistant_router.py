"""竞赛助手 API：供 Spring Boot 编排代理调用。"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.assistant.doc_extract import extract_path
from app.services.assistant.doc_generate import markdown_to_docx_bytes, markdown_to_pptx_bytes
from app.services.assistant.orchestrator import stream_run
from app.services.assistant.skills import list_skills_public
from app.services.assistant.research_agent import run_research_from_seed_hits
from app.services.assistant.web_research import (
    enrich_hits_with_pages,
    fetch_page,
    fetch_pages,
    refine_search_queries_llm,
    rerank_hits_llm,
    rewrite_search_queries_llm,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assistant", tags=["竞赛助手"])


class RewriteSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    maxQueries: int = Field(default=3, ge=1, le=5)


class FetchPagesRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    maxPages: int = Field(default=3, ge=1, le=5)
    maxChars: int = Field(default=1600, ge=200, le=6000)


class EnrichHitsRequest(BaseModel):
    hits: list[dict[str, Any]] = Field(default_factory=list)
    maxPages: int = Field(default=3, ge=1, le=5)
    maxChars: int = Field(default=1600, ge=200, le=6000)


class RefineSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    priorQueries: list[str] = Field(default_factory=list)
    hitTitles: list[str] = Field(default_factory=list)
    badTitles: list[str] = Field(default_factory=list)
    mustKeepPhrases: list[str] = Field(default_factory=list)
    maxQueries: int = Field(default=3, ge=1, le=5)


class RerankHitsRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    hits: list[dict[str, Any]] = Field(default_factory=list)
    topK: int = Field(default=6, ge=1, le=12)


@router.post("/v1/rewrite-search")
async def rewrite_search(body: RewriteSearchRequest):
    """轻量 LLM 改写联网检索词；失败时 queries 为空，由调用方用规则兜底。"""
    result = rewrite_search_queries_llm(body.query, max_queries=body.maxQueries)
    return result


@router.post("/v1/refine-search")
async def refine_search(body: RefineSearchRequest):
    """第二轮补搜：根据首轮标题动态生成新检索词（通用）。"""
    return refine_search_queries_llm(
        body.query,
        prior_queries=body.priorQueries or [],
        hit_titles=body.hitTitles or [],
        bad_titles=body.badTitles or [],
        must_keep_phrases=body.mustKeepPhrases or [],
        max_queries=body.maxQueries,
    )


@router.post("/v1/rerank-hits")
async def rerank_hits(body: RerankHitsRequest):
    """对候选结果做 LLM 相关度重排（通用）。"""
    return rerank_hits_llm(body.query, body.hits or [], top_k=body.topK)


@router.post("/v1/fetch-pages")
async def fetch_pages_api(body: FetchPagesRequest):
    """抓取公开网页正文（截断），供联网依据加深。"""
    pages = fetch_pages(body.urls or [], max_pages=body.maxPages, max_chars=body.maxChars)
    return {"pages": pages, "count": len(pages)}


@router.post("/v1/enrich-hits")
async def enrich_hits_api(body: EnrichHitsRequest):
    """给搜索 hits 补充 pageText。"""
    hits = enrich_hits_with_pages(
        body.hits or [], max_pages=body.maxPages, max_chars=body.maxChars
    )
    return {"hits": hits, "fetched": sum(1 for h in hits if h.get("fetched"))}


class ResearchRunRequest(BaseModel):
    """Research Agent：Java 可先搜 hits 再交给 AI 做 open/多跳装配。"""

    query: str = Field(..., min_length=1, max_length=500)
    hits: list[dict[str, Any]] = Field(default_factory=list)
    maxSteps: int = Field(default=6, ge=1, le=12)
    doFetch: bool = True


@router.post("/v1/research-run")
async def research_run_api(body: ResearchRunRequest):
    """Grok 式 tool loop（引擎结果由调用方注入 hits；本服务负责 open + block 装配）。"""

    def open_fn(url: str) -> dict[str, Any]:
        if not body.doFetch:
            return {"ok": False, "url": url, "error": "fetch_disabled"}
        return fetch_page(url, max_chars=1600)

    result = run_research_from_seed_hits(
        body.query,
        body.hits or [],
        open_fn=open_fn,
        max_steps=body.maxSteps,
    )
    return {
        "researchBlock": result.research_block,
        "evidence": result.evidence,
        "finishReason": result.finish_reason,
        "steps": [
            {
                "stepNo": s.step_no,
                "tool": s.tool,
                "args": s.args,
                "summary": s.result_summary,
            }
            for s in result.steps
        ],
    }


class ExtractItem(BaseModel):
    path: str
    ext: str | None = None
    title: str | None = None
    resourceId: int | None = None
    fileId: int | None = None
    maxChars: int = Field(default=14000, ge=1000, le=50000)


class ExtractRequest(BaseModel):
    items: list[ExtractItem]


class RenderDocxRequest(BaseModel):
    content: str
    title: str | None = "竞赛助手文稿"


class RenderPdfRequest(BaseModel):
    title: str | None = "竞赛助手导出"
    subtitle: str | None = None
    content: str | None = None
    messages: list[dict] | None = None


@router.get("/v1/skills")
async def list_skills(audience: str = "any"):
    """技能目录（供前端 slash 菜单；与 catalog SKILL.md 同步）。"""
    return {"skills": list_skills_public(audience=audience or "any")}


@router.get("/health")
async def health():
    ocr = {"enabled": False, "tesseract": None, "lang": None}
    try:
        from app.config import settings
        import shutil
        from pathlib import Path

        tess = getattr(settings, "TESSERACT_CMD", "") or shutil.which("tesseract") or ""
        ocr = {
            "enabled": bool(getattr(settings, "ASSISTANT_OCR_ENABLED", True)),
            "tesseract": tess if Path(tess).exists() or shutil.which("tesseract") else None,
            "lang": getattr(settings, "ASSISTANT_OCR_LANG", "chi_sim+eng"),
            "maxPages": getattr(settings, "ASSISTANT_OCR_MAX_PAGES", 8),
        }
        if ocr["tesseract"]:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = ocr["tesseract"]
                ocr["version"] = str(pytesseract.get_tesseract_version())
            except Exception as e:
                ocr["error"] = str(e)
    except Exception as e:
        ocr["error"] = str(e)
    return {"status": "ok", "service": "assistant", "ocr": ocr}


def _item_result(item: ExtractItem, extracted: dict) -> dict:
    return {
        "path": item.path,
        "title": item.title,
        "resourceId": item.resourceId,
        "fileId": item.fileId,
        "ext": item.ext or extracted.get("ext"),
        "ok": extracted.get("ok"),
        "error": extracted.get("error"),
        "text": extracted.get("text") or "",
        "chars": extracted.get("chars") or len(extracted.get("text") or ""),
        "method": extracted.get("method"),
        "ocr": bool(extracted.get("ocr")),
    }


@router.post("/v1/extract")
async def extract_documents(body: ExtractRequest):
    """批量抽取文档正文，供后端构建 RAG 上下文。"""
    results = []
    for item in body.items:
        extracted = extract_path(item.path, ext=item.ext, max_chars=item.maxChars)
        results.append(_item_result(item, extracted))
    return {"items": results}


@router.post("/v1/extract-stream")
async def extract_documents_stream(body: ExtractRequest):
    """
    流式抽取：OCR 过程中实时推送 progress。
    事件：
      - progress: {phase,title,page,total,index,count,resourceId,fileId}
      - item: 单文件结果
      - done: {items:[...]}
    """
    import json
    import queue
    import threading

    def gen():
        results = []
        count = len(body.items or [])
        for idx, item in enumerate(body.items or [], 1):
            title = item.title or item.path
            yield (
                "event: progress\n"
                f"data: {json.dumps({'phase': 'start', 'title': title, 'index': idx, 'count': count, 'resourceId': item.resourceId, 'fileId': item.fileId, 'page': 0, 'total': 0}, ensure_ascii=False)}\n\n"
            )

            q: queue.Queue = queue.Queue()
            holder: dict[str, Any] = {}

            def worker():
                def on_progress(page: int, total: int, name: str | None = None):
                    # page==0 表示文字层解析；page>=1 表示 OCR 分页
                    phase = "ocr" if page and total else "text_layer"
                    q.put(
                        {
                            "phase": phase,
                            "title": title,
                            "page": page,
                            "total": total,
                            "index": idx,
                            "count": count,
                            "resourceId": item.resourceId,
                            "fileId": item.fileId,
                            "fileName": name,
                        }
                    )

                try:
                    extracted = extract_path(
                        item.path,
                        ext=item.ext,
                        max_chars=item.maxChars,
                        on_progress=on_progress,
                    )
                    holder["result"] = _item_result(item, extracted)
                except Exception as e:
                    logger.exception("extract-stream item failed")
                    holder["result"] = _item_result(
                        item,
                        {
                            "ok": False,
                            "error": str(e),
                            "text": f"（解析失败：{e}）",
                            "method": "error",
                            "ocr": False,
                            "chars": 0,
                            "ext": item.ext,
                        },
                    )
                finally:
                    q.put(None)

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            while True:
                ev = q.get()
                if ev is None:
                    break
                yield f"event: progress\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            t.join(timeout=1)
            result = holder.get("result") or _item_result(item, {"ok": False, "text": "", "error": "empty"})
            results.append(result)
            yield f"event: item\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"

        yield f"event: done\ndata: {json.dumps({'items': results}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v1/render-docx")
async def render_docx(body: RenderDocxRequest):
    """把 Markdown/纯文本渲染为 DOCX（base64）。"""
    import base64

    raw = markdown_to_docx_bytes(body.content or "", title=body.title)
    return {
        "name": f"{(body.title or '竞赛助手文稿').strip() or '竞赛助手文稿'}.docx",
        "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": len(raw),
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }


@router.post("/v1/render-pptx")
async def render_pptx(body: RenderDocxRequest):
    """把 Markdown 提纲渲染为简易 PPTX（base64）。"""
    import base64

    raw = markdown_to_pptx_bytes(body.content or "", title=body.title or "竞赛助手提纲")
    return {
        "name": f"{(body.title or '竞赛助手提纲').strip() or '竞赛助手提纲'}.pptx",
        "mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "size": len(raw),
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }


@router.post("/v1/render-pdf")
async def render_pdf(body: RenderPdfRequest):
    """把对话消息或 Markdown 渲染为 PDF（base64）。"""
    import base64

    from app.services.assistant.pdf_export import markdown_to_pdf_bytes, messages_to_pdf_bytes

    title = (body.title or "竞赛助手导出").strip() or "竞赛助手导出"
    if body.messages:
        raw = messages_to_pdf_bytes(
            title=title,
            subtitle=body.subtitle,
            messages=body.messages,
        )
    else:
        raw = markdown_to_pdf_bytes(body.content or "", title=title)
    return {
        "name": f"{title}.pdf",
        "mime": "application/pdf",
        "size": len(raw),
        "contentBase64": base64.b64encode(raw).decode("ascii"),
    }


@router.post("/v1/runs")
async def create_run(request: Request):
    payload: dict[str, Any] = await request.json()

    def event_generator():
        try:
            for frame in stream_run(payload):
                yield frame
        except Exception as e:
            logger.exception("assistant run failed")
            import json

            yield f"event: error\ndata: {json.dumps({'code': 'RUN_ERROR', 'message': str(e), 'retryable': True}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
