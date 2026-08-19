"""Jinja2 渲染 HTML，再用 Chromium 打成 A4 PDF。"""
from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.html_report.view_model import build_view_model

_DIR = Path(__file__).resolve().parent


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_html(result: dict) -> str:
    vm = build_view_model(result)
    return _env().get_template("template.html").render(**vm)


def render_html_from_view(vm: dict) -> str:
    return _env().get_template("template.html").render(**vm)


def _launch_args() -> list[str]:
    args = ["--disable-dev-shm-usage", "--font-render-hinting=none"]
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        args.append("--no-sandbox")
    return args


def _system_chrome() -> str | None:
    for key in ("OREP_CHROMIUM_PATH", "CHROME_PATH", "PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        path = (os.getenv(key) or "").strip()
        if path and os.path.isfile(path):
            return path
    candidates = (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _header_template(logo: str, brand: str) -> str:
    img = ""
    if logo.startswith("data:image/png") or logo.startswith("data:image/jpeg"):
        img = (
            f'<img src="{logo}" width="16" height="16" alt="" '
            f'style="width:16px;height:16px;vertical-align:middle;margin-right:6px;border:0;" />'
        )
    return (
        '<div style="font-size:10px;width:100%;padding:0 14mm;box-sizing:border-box;'
        "color:#151619;font-family:PingFang SC,Noto Sans CJK SC,sans-serif;\">"
        f"{img}<span style=\"color:#E84A1C;font-weight:700;font-size:12px;"
        'letter-spacing:0.06em;vertical-align:middle;">'
        f"{brand}</span>"
        '<span style="float:right;color:#44464b;">'
        '<span style="color:#e84a1c;">■</span> 路演评分报告</span></div>'
    )


def _footer_template(website: str, company: str = "") -> str:
    left = " · ".join(part for part in (company, website) if part)
    return (
        '<div style="font-size:9px;width:100%;padding:0 14mm;box-sizing:border-box;'
        "color:#7b7d82;font-family:Helvetica,Arial,sans-serif;\">"
        f"<span>{left}</span>"
        '<span style="float:right;min-width:24px;padding-top:2px;'
        'border-top:1.5px solid #e84a1c;color:#151619;text-align:right;">'
        '<span class="pageNumber"></span></span></div>'
    )


def _playwright_pdf(html_path: str, pdf_path: str, vm: dict) -> None:
    from playwright.sync_api import sync_playwright

    uri = Path(html_path).resolve().as_uri()
    last_error: Exception | None = None
    with sync_playwright() as p:
        browser = None
        for exe in (None, _system_chrome()):
            kwargs = {"headless": True, "args": _launch_args()}
            if exe:
                kwargs["executable_path"] = exe
            try:
                browser = p.chromium.launch(**kwargs)
                break
            except Exception as exc:
                last_error = exc
                browser = None
        if browser is None:
            raise RuntimeError(f"playwright chromium 启动失败: {last_error}")
        try:
            page = browser.new_page()
            page.goto(uri, wait_until="load", timeout=60_000)
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template=_header_template(
                    vm.get("header_mark") or "",
                    vm.get("brand") or "竞赛大脑",
                ),
                footer_template=_footer_template(
                    vm.get("website") or "",
                    vm.get("company") or "",
                ),
                margin={
                    "top": "20mm",
                    "bottom": "16mm",
                    "left": "14mm",
                    "right": "14mm",
                },
            )
        finally:
            browser.close()


def _chrome_pdf(html_path: str, pdf_path: str) -> None:
    import subprocess

    chrome = _system_chrome()
    if not chrome:
        raise RuntimeError("未找到 Chrome / Chromium")
    raw = Path(html_path).read_text(encoding="utf-8")
    raw = raw.replace(".sheet-head, .sheet-foot { display: none !important; }", "")
    fallback = Path(html_path).with_name(Path(html_path).stem + ".chrome.html")
    fallback.write_text(raw, encoding="utf-8")
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        fallback.resolve().as_uri(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0 or not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) < 100:
        raise RuntimeError(
            f"chrome print-to-pdf 失败 rc={proc.returncode} {proc.stderr[-400:]}"
        )


def html_to_pdf(html_path: str, pdf_path: str, vm: dict) -> str:
    errors: list[str] = []
    try:
        _playwright_pdf(html_path, pdf_path, vm)
        return "playwright"
    except Exception as exc:
        errors.append(f"playwright: {exc}")
    try:
        _chrome_pdf(html_path, pdf_path)
        return "chrome"
    except Exception as exc:
        errors.append(f"chrome: {exc}")
    raise RuntimeError("HTML→PDF 失败: " + " | ".join(errors))


def generate_html_report(result: dict, output_dir: str) -> str:
    if not isinstance(result, dict):
        raise TypeError("result must be dict")
    vm = build_view_model(result)
    meeting_id = (vm.get("cover") or {}).get("meeting_id") or result.get("meeting_id") or "unknown"
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"report_{meeting_id}.html")
    pdf_path = os.path.join(output_dir, f"report_{meeting_id}.pdf")
    html = render_html_from_view(vm)
    Path(html_path).write_text(html, encoding="utf-8")
    engine = html_to_pdf(html_path, pdf_path, vm)
    size = os.path.getsize(pdf_path)
    print(f"[HtmlReport] {engine} 已生成: {pdf_path} ({size / 1024:.1f} KB) html={html_path}")
    return pdf_path
