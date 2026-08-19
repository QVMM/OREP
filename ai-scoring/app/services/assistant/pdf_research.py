"""PDF 浅抽：前 N 页文本 + 关键词命中（尽力，不保证扫描件 OCR）。

引擎优先序：PyMuPDF(fitz) → pypdf → PyPDF2。
生产镜像常装有 PyMuPDF；pypdf 可能未打入运行层，故必须先 fitz。
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

# 口语/指令碎片：不得当 PDF 关键词
_ORAL_KW = re.compile(
    r"^(请基于|若搜不到|请如实|帮我|请问|谢谢|是什么|怎么样|有哪些|"
    r"官方来源|如实说明|回答|搜索|查找)"
)
_SOFT_KW = frozenset(
    {
        "信息",
        "相关",
        "资料",
        "内容",
        "情况",
        "结果",
        "一下",
        "什么",
        "如何",
        "回答",
        "说明",
        "来源",
        "官方",
        "基于",
    }
)


def clean_pdf_keywords(keywords: list[str] | None, *, max_n: int = 8) -> list[str]:
    """清洗 PDF 关键词：去口语、去过短、去重。"""
    out: list[str] = []
    for k in keywords or []:
        kk = re.sub(r"\s+", "", str(k or "").strip())
        if not kk or len(kk) < 2:
            continue
        if kk in _SOFT_KW:
            continue
        if _ORAL_KW.search(kk):
            continue
        if re.fullmatch(r"[?？!！。，,\s]+", kk):
            continue
        # 剥尾部口语
        kk = re.sub(r"(是什么|怎么样|有哪些|请.*)$", "", kk)
        if len(kk) < 2 or kk in _SOFT_KW:
            continue
        if kk not in out:
            out.append(kk[:24])
        if len(out) >= max_n:
            break
    return out


def keywords_in_pdf_text(text: str, keywords: list[str] | None) -> dict[str, bool]:
    blob = text or ""
    out: dict[str, bool] = {}
    for k in clean_pdf_keywords(keywords, max_n=16):
        out[k] = k in blob
    return out


def _extract_with_fitz(
    data: bytes, *, max_pages: int, max_chars: int
) -> dict[str, Any] | None:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        logger.info("fitz open fail: %s", e)
        return None
    try:
        n = min(doc.page_count, max_pages)
        parts: list[str] = []
        total = 0
        for i in range(n):
            try:
                t = doc.load_page(i).get_text("text") or ""
            except Exception:
                t = ""
            if t.strip():
                chunk = f"\n--- 第 {i + 1} 页 ---\n{t.strip()}"
                parts.append(chunk)
                total += len(chunk)
                if total >= max_chars:
                    break
        text = "\n".join(parts)[:max_chars]
        return {
            "ok": True,
            "text": text,
            "pages": n,
            "chars": len(text),
            "engine": "fitz",
            "page_count": doc.page_count,
        }
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _extract_with_pypdf_family(
    data: bytes, *, max_pages: int, max_chars: int, engine_name: str, reader_cls: Any
) -> dict[str, Any] | None:
    try:
        reader = reader_cls(io.BytesIO(data))
        pages = getattr(reader, "pages", None) or []
        n = min(len(pages), max_pages)
        parts: list[str] = []
        total = 0
        for i in range(n):
            try:
                t = pages[i].extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                chunk = f"\n--- 第 {i + 1} 页 ---\n{t.strip()}"
                parts.append(chunk)
                total += len(chunk)
                if total >= max_chars:
                    break
        text = "\n".join(parts)[:max_chars]
        return {
            "ok": True,
            "text": text,
            "pages": n,
            "chars": len(text),
            "engine": engine_name,
            "page_count": len(pages),
        }
    except Exception as e:
        logger.info("%s extract failed: %s", engine_name, e)
        return None


def extract_pdf_text_from_bytes(
    data: bytes,
    *,
    max_pages: int = 3,
    max_chars: int = 4000,
) -> dict[str, Any]:
    """从 PDF 字节提取前 max_pages 页文本。"""
    if not data or len(data) < 8:
        return {"ok": False, "error": "empty_pdf", "text": "", "pages": 0}
    if data[:4] != b"%PDF":
        # 可能下到了 HTML 错误页
        head = data[:200].decode("utf-8", "ignore")
        return {
            "ok": False,
            "error": "not_pdf",
            "text": "",
            "pages": 0,
            "note": head[:80],
        }
    max_pages = max(1, min(int(max_pages or 3), 8))
    max_chars = max(200, min(int(max_chars or 4000), 20000))

    # 1) PyMuPDF — 生产镜像通常可用，中文表格式名单更稳
    got = _extract_with_fitz(data, max_pages=max_pages, max_chars=max_chars)
    if got is not None and (got.get("text") or "").strip():
        return got

    # 2) pypdf
    try:
        from pypdf import PdfReader  # type: ignore

        got2 = _extract_with_pypdf_family(
            data, max_pages=max_pages, max_chars=max_chars, engine_name="pypdf", reader_cls=PdfReader
        )
        if got2 is not None and (got2.get("text") or "").strip():
            return got2
        if got is None and got2 is not None:
            got = got2
    except Exception as e:
        logger.info("pypdf import/extract failed: %s", e)

    # 3) PyPDF2
    try:
        from PyPDF2 import PdfReader as PdfReader2  # type: ignore

        got3 = _extract_with_pypdf_family(
            data,
            max_pages=max_pages,
            max_chars=max_chars,
            engine_name="PyPDF2",
            reader_cls=PdfReader2,
        )
        if got3 is not None and (got3.get("text") or "").strip():
            return got3
        if got is None and got3 is not None:
            got = got3
    except Exception as e:
        logger.info("PyPDF2 import/extract failed: %s", e)

    # 有页数但无文本（扫描件/字体映射）
    if got is not None:
        if not (got.get("text") or "").strip():
            got["note"] = "pdf_has_no_extractable_text"
            got["ok"] = True
        return got

    return {
        "ok": True,
        "text": "",
        "pages": 0,
        "chars": 0,
        "engine": "none",
        "note": "pdf_has_no_extractable_text",
    }


def fetch_pdf_url(
    url: str,
    *,
    max_pages: int = 3,
    max_chars: int = 4000,
    keywords: list[str] | None = None,
    timeout: float = 12.0,
    referer: str | None = None,
) -> dict[str, Any]:
    """下载 PDF 并浅抽文本 + 关键词。"""
    u = (url or "").strip()
    if not u.startswith("http"):
        return {"ok": False, "url": u, "error": "bad_url"}
    # 清洗关键词
    kws = clean_pdf_keywords(keywords)
    # 默认 max_pages 对名单 PDF 稍放宽
    max_pages = max(1, min(int(max_pages or 3), 8))
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        # 政务附件常校验 Referer
        if referer:
            headers["Referer"] = referer
        else:
            try:
                from urllib.parse import urlparse

                p = urlparse(u)
                if p.scheme and p.netloc:
                    headers["Referer"] = f"{p.scheme}://{p.netloc}/"
            except Exception:
                pass
        req = urlrequest.Request(u, headers=headers, method="GET")
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            data = resp.read(12_000_000)  # 12MB
            final = resp.geturl() or u
            ctype = (resp.headers.get("Content-Type") or "").lower()
        if data[:4] != b"%PDF" and "pdf" not in ctype and "octet" not in ctype:
            return {
                "ok": False,
                "url": final,
                "error": "not_pdf_response",
                "text": "",
                "keywordHits": {},
                "note": f"ctype={ctype} magic={data[:8]!r}",
            }
        extracted = extract_pdf_text_from_bytes(
            data, max_pages=max_pages, max_chars=max_chars
        )
        text = str(extracted.get("text") or "")
        hits = keywords_in_pdf_text(text, kws)
        return {
            "ok": bool(extracted.get("ok")),
            "url": final,
            "text": text,
            "pages": extracted.get("pages") or 0,
            "chars": extracted.get("chars") or len(text),
            "keywordHits": hits,
            "engine": extracted.get("engine"),
            "note": extracted.get("note") or extracted.get("error"),
            "error": None if extracted.get("ok") else extracted.get("error"),
            "bytes": len(data),
        }
    except Exception as e:
        logger.info("fetch_pdf_url fail %s: %s", u[:80], e)
        return {
            "ok": False,
            "url": u,
            "error": str(e)[:160],
            "text": "",
            "keywordHits": {},
        }
