"""Prepare SVG files/content for browser preview and PPT export.

Applies the same high-value normalization steps on a temporary copy so
preview/export do not depend on previous finalize state being perfect.
"""

from __future__ import annotations

import uuid
import re
from pathlib import Path

from backend.config import settings

from .embed_icons import embed_icons_in_file
from .embed_images import build_image_index, embed_images_in_svg
from .flatten_tspan import flatten_text_in_svg
from .merge_adjacent_text import merge_adjacent_text_in_svg
from .normalize_fonts import normalize_text_fonts_in_svg
from .repair_svg import repair_svg_file


def prepare_svg_file_for_render(
    svg_path: Path,
    image_index: dict[str, Path] | None = None,
    page_num: int | None = None,
) -> Path:
    """Return a temporary sibling SVG with assets and text normalized."""
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file does not exist: {svg_path}")
    base_name = svg_path.name
    while True:
        match = re.match(r"^\.__render_[0-9a-f]+_(.+)$", base_name)
        if not match:
            break
        base_name = match.group(1)
    temp_path = svg_path.with_name(f".__render_{uuid.uuid4().hex}_{base_name}")
    temp_path.write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8")

    _prepare_in_place(
        temp_path,
        image_index=image_index,
        strip_images=_is_cover_svg(svg_path, page_num=page_num) and not _is_image2_svg(svg_path),
    )
    return temp_path


def prepare_svg_content_for_render(
    svg_content: str,
    svg_dir: Path,
    image_index: dict[str, Path] | None = None,
    page_num: int | None = None,
) -> str:
    """Normalize raw SVG content for browser rendering without mutating source files."""
    temp_path = svg_dir / f".__preview_{uuid.uuid4().hex}.svg"
    temp_path.write_text(svg_content, encoding="utf-8")
    try:
        _prepare_in_place(
            temp_path,
            image_index=image_index,
            strip_images=page_num == 1 and not _is_image2_full_page_content(svg_content),
        )
        return temp_path.read_text(encoding="utf-8")
    finally:
        temp_path.unlink(missing_ok=True)


def _prepare_in_place(
    svg_path: Path,
    image_index: dict[str, Path] | None = None,
    *,
    strip_images: bool = False,
) -> None:
    if image_index is None:
        image_index = build_image_index(svg_path.parent.parent)
    repair_svg_file(svg_path)
    if strip_images:
        _strip_image_elements_in_file(svg_path)
    embed_icons_in_file(svg_path, settings.icons_dir)
    if not strip_images:
        embed_images_in_svg(svg_path, image_index=image_index)
    flatten_text_in_svg(svg_path)
    merge_adjacent_text_in_svg(svg_path)
    normalize_text_fonts_in_svg(svg_path)


_SVG_IMAGE_RE = re.compile(
    r"<image\b[^>]*(?:/>\s*|>\s*</image\s*>)",
    re.IGNORECASE | re.DOTALL,
)


def strip_svg_image_elements(svg_content: str) -> str:
    """Remove raster/image nodes from a SVG string."""
    return _SVG_IMAGE_RE.sub("", svg_content or "")


def _strip_image_elements_in_file(svg_path: Path) -> None:
    svg_path.write_text(
        strip_svg_image_elements(svg_path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )


def _is_cover_svg(svg_path: Path, page_num: int | None = None) -> bool:
    if page_num is not None:
        return page_num == 1
    name = svg_path.name.lower()
    if "cover" in name:
        return True
    match = re.search(r"(?:^|[_-])0*1(?:[_-]|\.)", name)
    return bool(match)


def _is_image2_svg(svg_path: Path) -> bool:
    return "image2" in svg_path.stem.lower()


def _is_image2_full_page_content(svg_content: str) -> bool:
    svg = svg_content or ""
    image_tags = _SVG_IMAGE_RE.findall(svg)
    if len(image_tags) != 1:
        return False
    if not re.search(r"href=[\"']data:image/(?:png|jpe?g|webp);base64,", image_tags[0], re.I):
        return False
    return not re.search(r"<(?:text|foreignObject|rect|path|circle|ellipse|polygon|polyline|line)\b", svg, re.I)
