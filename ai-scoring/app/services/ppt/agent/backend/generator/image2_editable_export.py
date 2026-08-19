"""Image2-aware editable PPTX export adapter.

The image2 renderer already emits SVG pages where the generated image is the
visual layer and the known OREP slide text remains native SVG text.  This
adapter keeps that deterministic text layer editable in PowerPoint while also
persisting an image2-specific export report for retries and future OCR/inpaint
enhancements.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from backend.config import settings
from backend.generator.svg_to_pptx import create_pptx


def create_image2_editable_pptx(
    svg_files: list[Path],
    project_dir: Path,
    output_path: Path,
    *,
    canvas_format: str = "ppt169",
    notes: dict[str, str] | None = None,
) -> tuple[Path, list[str]]:
    """Create an editable PPTX for an image2 roadshow job.

    This first implementation deliberately avoids OCR dependency risk: the
    background is the image2 visual layer, and all known slide copy from OREP is
    converted from SVG into native DrawingML text boxes by the existing exporter.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = create_pptx(svg_files, output_path, canvas_format=canvas_format, notes=notes)
    report = _build_image2_export_report(project_dir, output_path)
    warnings = _report_warnings(report)
    report_path = output_path.with_suffix(".image2_export_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, warnings


def create_image2_image_pptx(
    project_dir: Path,
    output_path: Path,
    *,
    aspect_ratio: str = "16:9",
) -> tuple[Path, list[str]]:
    """Create a PPTX from pure image2 full-slide images.

    In this mode image2 is responsible for the complete slide: text, layout,
    hierarchy, and visuals.  PowerPoint receives one full-slide image per page.
    """
    image_rows = _image_rows(project_dir)
    image_paths = [Path(row["image_path"]) for row in image_rows if row.get("image_path")]
    if not image_paths:
        raise ValueError("No image2 page images found for image-only PPTX export.")

    prs = Presentation()
    width_in, height_in = _slide_size_inches(aspect_ratio)
    prs.slide_width = Inches(width_in)
    prs.slide_height = Inches(height_in)
    blank = prs.slide_layouts[6]

    for image_path in image_paths:
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(str(image_path), 0, 0, width=prs.slide_width, height=prs.slide_height)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    report = _build_image2_image_report(project_dir, output_path, image_rows)
    output_path.with_suffix(".image2_export_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path, _report_warnings(report)


def _build_image2_export_report(project_dir: Path, output_path: Path) -> dict[str, Any]:
    manifest = _read_manifest(project_dir)
    conversion_report = _read_json(output_path.with_suffix(".conversion_report.json"), default=[])
    image_pages = [row for row in manifest if row.get("image_path")]
    failed_pages = [row for row in manifest if row.get("failure")]
    fallback_slides = [
        row.get("slide")
        for row in conversion_report
        if isinstance(row, dict) and row.get("mode") == "fallback_image" and isinstance(row.get("slide"), int)
    ]
    return {
        "mode": "image2_editable",
        "export_strategy": "image2_background_plus_native_svg_text",
        "ocr_background_repair": "not_required_for_text_overlay",
        "future_ocr_inpaint_hook": {
            "enabled": False,
            "reason": "OREP already keeps exact slide copy as editable SVG text; OCR can be added as an optional enhancement for text embedded inside generated images.",
        },
        "image2": {
            "model": settings.image2_model,
            "base_url": _redact_url(settings.image2_base_url),
            "api_protocol": settings.image2_api_protocol,
            "resolution": settings.image2_resolution,
            "pages_with_images": len(image_pages),
            "failed_pages": [row.get("page") for row in failed_pages],
            "manifest": manifest,
        },
        "pptx": {
            "output_path": str(output_path),
            "fallback_slides": fallback_slides,
        },
    }


def _build_image2_image_report(project_dir: Path, output_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    failed_pages = [row.get("page") for row in rows if row.get("failure")]
    image_pages = [row for row in rows if row.get("image_path")]
    return {
        "mode": "image2_image",
        "export_strategy": "full_slide_image2_pages",
        "image2": {
            "model": settings.image2_model,
            "base_url": _redact_url(settings.image2_base_url),
            "api_protocol": settings.image2_api_protocol,
            "resolution": settings.image2_resolution,
            "pages_with_images": len(image_pages),
            "failed_pages": failed_pages,
            "manifest": rows,
        },
        "pptx": {
            "output_path": str(output_path),
            "fallback_slides": [],
        },
    }


def _read_manifest(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "debug" / "image2" / "manifest.json"
    rows = _read_json(path, default=[])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _image_rows(project_dir: Path) -> list[dict[str, Any]]:
    rows = _read_manifest(project_dir)
    if rows:
        return _normalize_image_rows(rows)
    image_dir = project_dir / "images" / "image2"
    fallback_rows = []
    for path in sorted(image_dir.glob("page_*.png")):
        page = _page_from_image_name(path.name)
        fallback_rows.append({
            "page": page,
            "image_path": str(path),
            "failure": None,
        })
    return _normalize_image_rows(fallback_rows)


def _normalize_image_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        page = item.get("page")
        if not isinstance(page, int):
            page = index
        item["page"] = page
        image_path = item.get("image_path")
        if image_path:
            resolved = Path(str(image_path))
            if resolved.exists():
                item["image_path"] = str(resolved)
            else:
                item["image_path"] = None
        normalized.append(item)
    return sorted(normalized, key=lambda row: int(row.get("page") or 0))


def _page_from_image_name(name: str) -> int:
    import re

    match = re.search(r"page_(\d+)_", name)
    return int(match.group(1)) if match else 0


def _slide_size_inches(aspect_ratio: str) -> tuple[float, float]:
    if aspect_ratio == "4:3":
        return 10.0, 7.5
    return 13.333333, 7.5


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _report_warnings(report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    failed_pages = report.get("image2", {}).get("failed_pages") or []
    if failed_pages:
        pages = ", ".join(str(page) for page in failed_pages)
        warnings.append(f"Image2 failed on page(s) {pages}; exported editable placeholder pages without SVG fallback.")
    fallback_slides = report.get("pptx", {}).get("fallback_slides") or []
    if fallback_slides:
        slides = ", ".join(str(slide) for slide in fallback_slides)
        warnings.append(f"PowerPoint conversion used raster fallback on slide(s) {slides}.")
    return warnings


def _redact_url(value: str | None) -> str | None:
    if not value:
        return value
    return value.split("?", 1)[0]
