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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/assistant", tags=["竞赛助手"])


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
