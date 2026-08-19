"""Image2-backed roadshow page renderer.

Image2 produces the visual layer.  The editable title/body layer is rebuilt
locally as SVG text and shapes so PPTX export can still emit editable objects.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import html
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from backend.config import settings

from .manuscript import extract_page_type, page_title, split_manuscript_pages
from .roadshow_asset_registry import IMAGE_ASSET_EXTENSIONS, load_asset_registry

logger = logging.getLogger(__name__)

PageStatusCallback = Callable[[int, int, str, str, dict | None], Awaitable[None]]
SvgReadyCallback = Callable[[int, str], Awaitable[None]]


def image2_configured() -> bool:
    return bool((settings.image2_api_key or "").strip())


def _image2_timeout() -> float:
    configured = float(settings.image2_timeout_seconds or 90)
    return max(15.0, min(configured, 95.0))


async def generate_image2_svg_pages(
    manuscript: str,
    design_spec: str,
    project_dir: Path,
    *,
    canvas_format: str = "ppt169",
    language: str = "zh",
    target_pages: set[int] | None = None,
    on_page_status: PageStatusCallback | None = None,
    on_svg_ready: SvgReadyCallback | None = None,
) -> list[tuple[int, str]]:
    """Generate one SVG per manuscript page with an image2 visual layer."""
    api_key = (settings.image2_api_key or "").strip()
    if not api_key:
        raise RuntimeError("Image2 API key is not configured. Set IMAGE2_API_KEY on the ai-scoring service.")

    pages = split_manuscript_pages(manuscript)
    output_dir = project_dir / "svg_output"
    image_dir = project_dir / "images" / "image2"
    debug_dir = project_dir / "debug" / "image2"
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    cards_by_page = (
        _load_image2_page_briefs(project_dir)
        or _load_image2_page_descriptions(project_dir)
        or _load_image2_page_cards(project_dir)
    )
    asset_registry = load_asset_registry(project_dir)
    manifest: list[dict[str, Any]] = []
    generated: list[tuple[int, str]] = []
    for index, page in enumerate(pages, start=1):
        if target_pages and index not in target_pages:
            continue
        card = cards_by_page.get(index)
        asset_context = _resolve_image_asset_inputs(
            project_dir,
            _card_assets(card) or _field_value(page, "required_assets"),
            asset_registry,
            page_num=index,
        )
        prompt = _build_image_prompt(
            page,
            design_spec=design_spec,
            language=language,
            canvas_format=canvas_format,
            card=card,
            asset_context=asset_context,
        )
        if on_page_status:
            await on_page_status(index, 1, "image2_prompt", f"第 {index}/{len(pages)} 页 image2 提示词已生成", None)
        image_path, failure_message, image_meta = await _generate_page_image(
            index,
            prompt,
            image_dir=image_dir,
            debug_dir=debug_dir,
            canvas_format=canvas_format,
            ref_image_paths=asset_context["image_paths"],
            asset_context=asset_context,
            on_page_status=on_page_status,
        )
        svg = _compose_editable_svg(index, page, image_path, failure_message=failure_message)
        svg_path = output_dir / f"{index:02d}_image2.svg"
        svg_path.write_text(svg, encoding="utf-8")
        manifest.append({
            "page": index,
            "svg_path": str(svg_path),
            "image_path": str(image_path) if image_path else None,
            "failure": failure_message,
            **image_meta,
        })
        if on_svg_ready:
            await on_svg_ready(index, svg)
        generated.append((index, svg))
    (debug_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return generated


async def _generate_page_image(
    page_num: int,
    prompt: str,
    *,
    image_dir: Path,
    debug_dir: Path,
    canvas_format: str,
    ref_image_paths: list[Path],
    asset_context: dict[str, Any],
    on_page_status: PageStatusCallback | None,
) -> tuple[Path | None, str | None, dict[str, Any]]:
    digest_source = prompt + "\n" + "\n".join(str(path) for path in ref_image_paths)
    digest = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:12]
    image_path = image_dir / f"page_{page_num:02d}_{digest}.png"
    prompt_path = debug_dir / f"page_{page_num:02d}_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    if image_path.exists():
        return image_path, None, {"cached": True, "prompt_path": str(prompt_path)}

    attempts = max(1, int(settings.image2_retry_attempts or 3))
    size = _image2_size(canvas_format)
    last_error: str = ""
    last_endpoint = ""
    for attempt in range(1, attempts + 1):
        try:
            if on_page_status:
                await on_page_status(
                    page_num,
                    attempt,
                    "image2_request",
                    f"第 {page_num} 页 image2 生成中，第 {attempt}/{attempts} 次尝试",
                    {"render_engine": "image2"},
                )
            payload = await _call_image2(prompt, size=size, ref_image_paths=ref_image_paths)
            last_endpoint = str(payload.get("_image2_endpoint") or "")
            (debug_dir / f"page_{page_num:02d}_attempt_{attempt}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            await _save_image_payload(payload, image_path)
            if image_path.exists():
                if on_page_status:
                    await on_page_status(
                        page_num,
                        attempt,
                        "image2_ready",
                        f"第 {page_num} 页 image2 视觉层已生成",
                        {"render_engine": "image2", "image_path": str(image_path)},
                    )
                return image_path, None, {
                    "attempts": attempt,
                    "endpoint": last_endpoint,
                    "size": size,
                    "prompt_path": str(prompt_path),
                    "asset_input_mode": payload.get("_asset_input_mode"),
                    "asset_images_used": payload.get("_asset_images_used") or [],
                    "asset_images_skipped": [
                        *(payload.get("_asset_images_skipped") or []),
                        *(asset_context.get("skipped") or []),
                    ],
                    "asset_captions_used": asset_context.get("used_asset_captions") or [],
                }
            last_error = "image2 response did not contain a usable image"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.warning("Image2 page %s attempt %s failed: %s", page_num, attempt, exc)
        if attempt < attempts:
            delay = float(settings.image2_retry_base_delay or 1.5) * (2 ** (attempt - 1))
            if on_page_status:
                await on_page_status(
                    page_num,
                    attempt,
                    "image2_retry",
                    f"第 {page_num} 页 image2 生成失败，正在重试：{_safe_error(last_error)}",
                    {"render_engine": "image2", "error": last_error},
                )
            await asyncio.sleep(delay)

    failure_message = f"第 {page_num} 页 image2 重试 {attempts} 次后仍失败：{_safe_error(last_error)}"
    if on_page_status:
        await on_page_status(
            page_num,
            attempts,
            "image2_failed",
            f"{failure_message}；已保留可编辑占位页并继续生成后续页面",
            {"render_engine": "image2", "error": last_error, "page_failed": True},
        )
    return None, failure_message, {
        "attempts": attempts,
        "endpoint": last_endpoint,
        "size": size,
        "prompt_path": str(prompt_path),
        "error": last_error,
        "asset_images_used": [str(path) for path in ref_image_paths],
        "asset_images_skipped": asset_context.get("skipped") or [],
        "asset_captions_used": asset_context.get("used_asset_captions") or [],
    }


async def _call_image2(prompt: str, *, size: str, ref_image_paths: list[Path] | None = None) -> dict[str, Any]:
    base_url = (settings.image2_base_url or "https://img.alibaba.cv").rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    timeout = _image2_timeout()
    protocol = (settings.image2_api_protocol or "auto").lower()
    ref_image_paths = ref_image_paths or []
    if protocol == "chat":
        return await _call_image2_chat(base_url, prompt, size=size, timeout=timeout, ref_image_paths=ref_image_paths)
    if protocol == "images":
        return await _call_image2_generation(base_url, prompt, size=size, timeout=timeout, ref_image_paths=ref_image_paths)

    model = (settings.image2_model or "").lower()
    prefer_images = model.startswith("gpt-image") or model.startswith("dall-e")
    if ref_image_paths:
        try:
            return await _call_image2_chat(base_url, prompt, size=size, timeout=timeout, ref_image_paths=ref_image_paths)
        except Exception as exc:
            logger.warning("Image2 chat request with material images failed, trying text-only images/generations: %s", exc)
            return await _call_image2_generation(base_url, prompt, size=size, timeout=timeout, ref_image_paths=ref_image_paths)
    try:
        if prefer_images:
            return await _call_image2_generation(base_url, prompt, size=size, timeout=timeout)
        return await _call_image2_chat(base_url, prompt, size=size, timeout=timeout)
    except Exception as exc:
        if prefer_images:
            logger.warning("Image2 images/generations request failed, trying chat/completions: %s", exc)
            return await _call_image2_chat(base_url, prompt, size=size, timeout=timeout)
        logger.warning("Image2 chat-compatible request failed, trying images/generations: %s", exc)
        return await _call_image2_generation(base_url, prompt, size=size, timeout=timeout)


async def _call_image2_chat(
    base_url: str,
    prompt: str,
    *,
    size: str,
    timeout: float,
    ref_image_paths: list[Path] | None = None,
) -> dict[str, Any]:
    url = f"{base_url}/chat/completions"
    content: str | list[dict[str, Any]]
    ref_image_paths = ref_image_paths or []
    if ref_image_paths:
        content = [{"type": "text", "text": prompt}]
        for path in ref_image_paths[:3]:
            content.append({"type": "image_url", "image_url": {"url": _image_data_url(path)}})
    else:
        content = prompt
    body = {
        "model": settings.image2_model or "gpt-image-2",
        "messages": [{"role": "user", "content": content}],
        "modalities": ["text", "image"],
        "aspect_ratio": "16:9",
        "resolution": settings.image2_resolution or "2K",
        "size": size,
        "generationConfig": {
            "imageConfig": {
                "aspectRatio": "16:9",
                "imageSize": settings.image2_resolution or "2K",
            }
        },
        "n": 1,
    }
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        http2=True,
    ) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.image2_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        payload = response.json()
        payload["_image2_endpoint"] = "chat/completions"
        payload["_asset_input_mode"] = "chat_image_inputs" if ref_image_paths else "no_asset_images"
        payload["_asset_images_used"] = [str(path) for path in ref_image_paths[:3]]
        payload["_asset_images_skipped"] = []
        return payload


async def _call_image2_generation(
    base_url: str,
    prompt: str,
    *,
    size: str,
    timeout: float,
    ref_image_paths: list[Path] | None = None,
) -> dict[str, Any]:
    url = f"{base_url}/images/generations"
    ref_image_paths = ref_image_paths or []
    body = {
        "model": settings.image2_model or "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": size,
    }
    if (settings.image2_model or "").lower().startswith("dall-e"):
        body["response_format"] = "b64_json"
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        trust_env=False,
        http2=True,
    ) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.image2_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        payload = response.json()
        payload["_image2_endpoint"] = "images/generations"
        payload["_asset_input_mode"] = "text_only_endpoint" if ref_image_paths else "no_asset_images"
        payload["_asset_images_used"] = []
        payload["_asset_images_skipped"] = [
            f"{path.name}: images/generations does not accept material image inputs"
            for path in ref_image_paths[:3]
        ]
        return payload


async def _save_image_payload(payload: dict[str, Any], image_path: Path) -> None:
    image_ref = _extract_image_reference(payload)
    if image_ref:
        await _save_image_reference(image_ref, image_path)
        return
    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("image2 response has no data array")
    first = data[0] if isinstance(data[0], dict) else {}
    b64 = first.get("b64_json")
    if isinstance(b64, str) and b64.strip():
        image_path.write_bytes(base64.b64decode(b64))
        return
    url = first.get("url") or first.get("image_url")
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        await _download_image(url, image_path)
        return
    raise ValueError("image2 response has neither b64_json nor image URL")


async def _save_image_reference(ref: str, image_path: Path) -> None:
    ref = ref.strip()
    if ref.startswith("data:image") and "," in ref:
        image_path.write_bytes(base64.b64decode(ref.split(",", 1)[1]))
        return
    if ref.startswith(("http://", "https://")):
        await _download_image(ref, image_path)
        return
    try:
        image_path.write_bytes(base64.b64decode(ref, validate=True))
        return
    except Exception as exc:  # noqa: BLE001
        raise ValueError("image2 response image reference was not a URL, data URL, or base64 image") from exc


async def _download_image(url: str, image_path: Path) -> None:
    async with httpx.AsyncClient(
        timeout=120.0,
        follow_redirects=True,
        trust_env=False,
        http2=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        image_path.write_bytes(response.content)


def _extract_image_reference(payload: dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            ref = item.get("b64_json") or item.get("url") or item.get("image_url")
            if isinstance(ref, str) and ref.strip():
                return ref.strip()

    choices = payload.get("choices")
    if not isinstance(choices, list):
        return ""
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        images = message.get("images")
        if isinstance(images, list):
            for item in images:
                ref = _extract_reference_from_image_item(item)
                if ref:
                    return ref
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                ref = _extract_reference_from_image_item(part)
                if ref:
                    return ref
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    ref = _extract_reference_from_text(part["text"])
                    if ref:
                        return ref
            continue
        if not isinstance(content, str):
            continue
        ref = _extract_reference_from_text(content)
        if ref:
            return ref
    return ""


def _extract_reference_from_image_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    if isinstance(item.get("b64_json"), str):
        return item["b64_json"].strip()
    image_url = item.get("image_url")
    if isinstance(image_url, str):
        return image_url.strip()
    if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
        return image_url["url"].strip()
    if isinstance(item.get("url"), str):
        return item["url"].strip()
    if isinstance(item.get("data"), str):
        return item["data"].strip()
    return ""


def _extract_reference_from_text(content: str) -> str:
    data_match = re.search(r"data:image/[^;\s]+;base64,[A-Za-z0-9+/=\s]+", content)
    if data_match:
        return re.sub(r"\s+", "", data_match.group(0))
    markdown_match = re.search(r"!\[[^\]]*]\((https?://[^)\s]+)\)", content)
    if markdown_match:
        return markdown_match.group(1)
    url_match = re.search(r"https?://\S+", content)
    if url_match:
        return url_match.group(0).rstrip(").,，。")
    return ""


def _build_image_prompt(
    page: str,
    *,
    design_spec: str,
    language: str,
    canvas_format: str,
    card: dict[str, Any] | None = None,
    asset_context: dict[str, Any] | None = None,
) -> str:
    title = _card_field(card, "formal_title") or _card_field(card, "title") or page_title(page)
    page_type = _card_field(card, "page_type") or extract_page_type(page)
    visual = (
        _card_visual_scene(card)
        or _field_value(page, "main_visual")
        or _field_value(page, "primary_visual")
    )
    core = _first_usable_text(
        _card_field(card, "core_sentence"),
        _card_field(card, "page_core_sentence"),
        _card_field(card, "core_message"),
        _field_value(page, "page_core_sentence"),
        _field_value(page, "core_sentence"),
    )
    visible = _first_usable_text(
        _card_field(card, "visible_content"),
        _card_field(card, "page_text"),
        _card_field(card, "visible_points"),
        _field_value(page, "visible_content"),
        _visible_fallback(page),
    )
    assets = _card_assets(card) or _field_value(page, "required_assets")
    spec_hint = _summarize_design_spec(design_spec)
    size = _image2_size(canvas_format)
    visible_text = _prompt_visible_text(title=title, core=core, visible=visible)
    layout_intent = _card_field(card, "layout_intent")
    evidence_focus = _card_field(card, "evidence_focus")
    prompt_notes = _card_field(card, "image_prompt_notes")
    asset_context = asset_context or {}
    used_assets = asset_context.get("used_asset_captions") or []
    skipped_assets = asset_context.get("skipped") or []
    asset_hint = ""
    if not _is_empty_asset_hint(assets):
        cleaned_assets = _clean_prompt_text(assets, 220)
        asset_hint = (
            "Support material visual hints: "
            f"{cleaned_assets or 'use the attached material images and their captions only'}. "
            "Do not print raw asset IDs on the slide. "
        )
    if used_assets:
        asset_hint += (
            "Attached material images are available as visual references: "
            f"{_clip('；'.join(used_assets), 320)}. "
            "Use them as real screenshots/material visuals when relevant, while keeping slide text readable. "
        )
    elif skipped_assets:
        asset_hint += (
            "Some material images could not be attached to this provider call, so treat asset references as textual hints only. "
        )
    cover_hint = (
        "Cover slide rule: generate a complete designed cover image with background, title composition, project keywords, abstract technology/agriculture visuals, lighting, lines, or geometry. No uploaded asset is required, but the cover must not be blank or text-only. "
        if page_type == "cover"
        else ""
    )
    return (
        f"Create one complete {size} 16:9 PowerPoint slide as a single finished image. "
        "The slide must already include the final layout, readable Chinese slide text, title hierarchy, bullets, visual composition, and decorative/data graphics. "
        "Do not leave a blank area for later editing. Do not rely on external SVG/text overlays. Do not output a background-only image. "
        f"{cover_hint}"
        "Use polished roadshow PPT design: clear information hierarchy, modern agriculture technology visuals, greenhouse IoT monitoring, dashboards, sensors, field operations, data flows, and refined teal/blue/green accents when relevant. "
        "Avoid raw internal tokens, markdown, [[FIG:...]] IDs, asset_status fields, watermarks, UI buttons, lorem ipsum, or placeholder text. "
        "Use the following visible slide copy as the content to typeset directly on the slide image. Keep it concise and readable; preserve Chinese meaning and key phrases. "
        f"Visible slide copy: {visible_text}. "
        f"Language context: {language}. Slide type: {_clip(page_type, 80)}. "
        f"Visual intent: {_clip(visual, 180)}. "
        f"Layout intent: {_clip(layout_intent, 220)}. "
        f"Evidence focus: {_clip(evidence_focus, 220)}. "
        f"Page-specific notes: {_clip(prompt_notes, 220)}. "
        f"{asset_hint}"
        f"Deck visual direction: {_clip(spec_hint, 260)}."
    )


def _load_image2_page_briefs(project_dir: Path) -> dict[int, dict[str, Any]]:
    path = project_dir / "image2_page_briefs.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read image2 page briefs from %s: %s", path, exc)
        return {}
    rows = payload.get("briefs")
    if not isinstance(rows, list):
        return {}
    result: dict[int, dict[str, Any]] = {}
    for fallback_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        page_num = _safe_int(item.get("page")) or fallback_index
        result[page_num] = item
    return result


def _load_image2_page_descriptions(project_dir: Path) -> dict[int, dict[str, Any]]:
    path = project_dir / "image2_page_descriptions.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read image2 page descriptions from %s: %s", path, exc)
        return {}
    rows = payload.get("descriptions")
    if not isinstance(rows, list):
        return {}
    result: dict[int, dict[str, Any]] = {}
    for fallback_index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        page_num = _safe_int(item.get("page")) or fallback_index
        result[page_num] = item
    return result


def _load_image2_page_cards(project_dir: Path) -> dict[int, dict[str, Any]]:
    for name in ("page_content_cards.confirmed.json", "page_content_cards.json"):
        path = project_dir / name
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read image2 page cards from %s: %s", path, exc)
            continue
        cards = payload.get("cards")
        if not isinstance(cards, list):
            continue
        result: dict[int, dict[str, Any]] = {}
        for fallback_index, item in enumerate(cards, start=1):
            if not isinstance(item, dict):
                continue
            page_num = _safe_int(item.get("page")) or fallback_index
            result[page_num] = item
        if result:
            return result
    return {}


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _card_field(card: dict[str, Any] | None, name: str) -> str:
    if not card:
        return ""
    value = card.get(name)
    return str(value).strip() if value not in (None, "") else ""


def _card_visual_scene(card: dict[str, Any] | None) -> str:
    if not card:
        return ""
    direct = str(card.get("visual_scene") or "").strip()
    if direct:
        return direct
    main_visual = card.get("main_visual")
    if isinstance(main_visual, dict):
        parts = [
            str(main_visual.get("visual_scene") or "").strip(),
            str(main_visual.get("purpose") or "").strip(),
            str(main_visual.get("required_elements") or "").strip(),
        ]
        text = "；".join(part for part in parts if part)
        if text:
            return text
    primary_visual = card.get("primary_visual")
    if isinstance(primary_visual, dict):
        parts = [
            str(primary_visual.get("purpose") or "").strip(),
            str(primary_visual.get("required_elements") or "").strip(),
        ]
        return "；".join(part for part in parts if part)
    return ""


def _card_assets(card: dict[str, Any] | None) -> str:
    if not card:
        return ""
    raw = card.get("required_assets") or card.get("asset_refs")
    if isinstance(raw, list):
        return "；".join(str(item).strip() for item in raw if str(item).strip())
    return str(raw or "").strip()


def _resolve_image_asset_inputs(
    project_dir: Path,
    assets_text: str,
    asset_registry: dict[str, dict[str, Any]],
    *,
    page_num: int,
) -> dict[str, Any]:
    asset_ids = _asset_ids_from_text(assets_text)
    image_paths: list[Path] = []
    used_asset_captions: list[str] = []
    skipped: list[str] = []

    if page_num == 1:
        return {
            "image_paths": [],
            "used_asset_captions": [],
            "skipped": [f"{asset_id}: cover ignores uploaded assets" for asset_id in asset_ids],
        }

    for asset_id in asset_ids[:6]:
        asset = asset_registry.get(asset_id)
        if not asset:
            skipped.append(f"{asset_id}: missing from asset_registry.json")
            continue
        filename = str(asset.get("filename") or asset.get("path") or "")
        suffix = Path(filename).suffix.lower()
        if suffix not in IMAGE_ASSET_EXTENSIONS:
            skipped.append(f"{asset_id}: not an image asset")
            continue
        path = _asset_local_path(project_dir, asset)
        if not path or not path.exists():
            skipped.append(f"{asset_id}: local image file not found")
            continue
        image_paths.append(path)
        caption = str(asset.get("caption") or asset.get("filename") or asset_id).strip()
        used_asset_captions.append(f"{asset_id} {caption}".strip())
        if len(image_paths) >= 3:
            break

    return {
        "image_paths": image_paths,
        "used_asset_captions": used_asset_captions,
        "skipped": skipped,
    }


def _asset_ids_from_text(value: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in re.finditer(r"\[\[ASSET:([A-Za-z0-9_.:-]+)\]\]", value or ""):
        asset_id = match.group(1)
        if asset_id in seen:
            continue
        seen.add(asset_id)
        result.append(asset_id)
    return result


def _asset_local_path(project_dir: Path, asset: dict[str, Any]) -> Path | None:
    candidates: list[Path] = []
    for key in ("path", "href", "original_rel"):
        value = str(asset.get(key) or "").strip()
        if not value:
            continue
        raw = Path(value)
        if raw.is_absolute():
            candidates.append(raw)
        candidates.append((project_dir / value).resolve())
        candidates.append((project_dir / "sources" / value).resolve())
        if value.startswith("sources/"):
            candidates.append((project_dir / value).resolve())
        if value.startswith("../sources/"):
            candidates.append((project_dir / value.removeprefix("../")).resolve())
        if value.startswith("../"):
            candidates.append((project_dir / value).resolve())
    filename = str(asset.get("filename") or "").strip()
    if filename:
        asset_id = str(asset.get("asset_id") or "").strip()
        if asset_id:
            candidates.append(project_dir / "sources" / "images" / "assets" / filename)
            candidates.append(project_dir / "sources" / "images" / "assets" / f"{asset_id}{Path(filename).suffix}")

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _image2_size(canvas_format: str) -> str:
    resolution = (settings.image2_resolution or "2K").upper()
    long_edge = {"1K": 1280, "2K": 2048, "4K": 3840}.get(resolution, 2048)
    width = long_edge
    height = round(width * 9 / 16)
    width = max(16, (width // 16) * 16)
    height = max(16, (height // 16) * 16)
    max_pixels = 8_294_400
    if width * height > max_pixels:
        scale = (max_pixels / (width * height)) ** 0.5
        width = max(16, (int(width * scale) // 16) * 16)
        height = max(16, (int(height * scale) // 16) * 16)
    return f"{width}x{height}"


def _compose_editable_svg(
    page_num: int,
    page: str,
    image_path: Path | None,
    *,
    failure_message: str | None = None,
) -> str:
    if image_path is not None:
        image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <image href="data:image/png;base64,{image_data}" x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid slice"/>
</svg>'''

    title = _clean_text(_field_value(page, "formal_title") or page_title(page), 42)
    core = _clean_text(_field_value(page, "page_core_sentence") or _field_value(page, "core_sentence"), 88)
    visible = _clean_text(_field_value(page, "visible_content") or _visible_fallback(page), 260)
    bullets = _wrap_lines(visible, max_lines=4, line_chars=26)
    title_lines = _wrap_lines(title, max_lines=2, line_chars=18)
    core_lines = _wrap_lines(core, max_lines=2, line_chars=30)
    title_svg = _text_block(title_lines, x=72, y=94, size=34, weight=800, fill="#f4fff9", line_gap=42)
    core_svg = _text_block(core_lines, x=76, y=190, size=18, weight=600, fill="#bfffe1", line_gap=26)
    bullet_svg = _bullet_block(bullets, x=78, y=312)
    failure_svg = _failure_notice(failure_message)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720">
  <defs>
    <linearGradient id="shade{page_num}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#07130f" stop-opacity="0.92"/>
      <stop offset="0.54" stop-color="#07130f" stop-opacity="0.54"/>
      <stop offset="1" stop-color="#07130f" stop-opacity="0.18"/>
    </linearGradient>
    <linearGradient id="panel{page_num}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0c2a21" stop-opacity="0.82"/>
      <stop offset="1" stop-color="#102032" stop-opacity="0.70"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="#07130f"/>
  <rect width="1280" height="720" fill="url(#shade{page_num})"/>
  <rect x="54" y="52" width="720" height="590" rx="0" fill="url(#panel{page_num})" stroke="#64f0a6" stroke-opacity="0.26"/>
  <line x1="76" y1="248" x2="710" y2="248" stroke="#77ffb5" stroke-opacity="0.36" stroke-width="2"/>
  {title_svg}
  {core_svg}
  {bullet_svg}
  {failure_svg}
</svg>'''


def _field_value(page: str, name: str) -> str:
    pattern = re.compile(rf"(?ims)^\s*(?:\*\*)?{re.escape(name)}(?:\*\*)?\s*[:：]\s*(.+?)(?=^\s*(?:\*\*)?[a-zA-Z_][\w_ -]{{1,48}}(?:\*\*)?\s*[:：]|\Z)")
    match = pattern.search(page)
    return match.group(1).strip() if match else ""


def _visible_fallback(page: str) -> str:
    lines = []
    for raw in page.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--") or re.match(r"^#{1,6}\s+", line):
            continue
        if re.match(r"^(?:page|section|formal_title|title|speaker_notes|main_visual|primary_visual)\s*[:：]", line, re.I):
            continue
        lines.append(line.strip("-* "))
    return "；".join(lines[:6])


def _text_block(lines: list[str], *, x: int, y: int, size: int, weight: int, fill: str, line_gap: int) -> str:
    if not lines:
        return ""
    chunks = []
    for offset, line in enumerate(lines):
        chunks.append(
            f'<text x="{x}" y="{y + offset * line_gap}" fill="{fill}" '
            f'font-family="Microsoft YaHei, PingFang SC, Arial" font-size="{size}" font-weight="{weight}">{html.escape(line)}</text>'
        )
    return "\n  ".join(chunks)


def _bullet_block(lines: list[str], *, x: int, y: int, text_fill: str = "#f4fff9", dot_fill: str = "#77ffb5") -> str:
    chunks = []
    for index, line in enumerate(lines):
        cy = y + index * 48
        chunks.append(f'<circle cx="{x + 6}" cy="{cy - 6}" r="4" fill="{dot_fill}"/>')
        chunks.append(
            f'<text x="{x + 24}" y="{cy}" fill="{text_fill}" font-family="Microsoft YaHei, PingFang SC, Arial" '
            f'font-size="21" font-weight="650">{html.escape(line)}</text>'
        )
    return "\n  ".join(chunks)


def _wrap_lines(text: str, *, max_lines: int, line_chars: int) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip(" ；;，,")
    if not text:
        return []
    parts = [part.strip() for part in re.split(r"[；;。\n]+", text) if part.strip()]
    lines: list[str] = []
    for part in parts:
        while len(part) > line_chars and len(lines) < max_lines:
            cut = part[:line_chars]
            for sep in ("，", ",", "、", " "):
                pos = cut.rfind(sep)
                if pos >= 8:
                    cut = cut[:pos]
                    break
            lines.append(cut.strip())
            part = part[len(cut):].lstrip("，,、 ")
        if part and len(lines) < max_lines:
            lines.append(part[:line_chars].strip())
        if len(lines) >= max_lines:
            break
    return lines


def _clean_text(value: str, max_chars: int) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = value.replace("**", "")
    value = re.sub(r"\s+", " ", value).strip(" `*_#：:，,。；;|")
    return value[:max_chars].strip()


def _prompt_visible_text(*, title: str, core: str, visible: str) -> str:
    parts = []
    clean_title = _clean_prompt_text(title, 80)
    clean_core = _clean_prompt_text(core, 140)
    clean_visible = _clean_prompt_text(visible, 420)
    if clean_title:
        parts.append(f"标题：{clean_title}")
    if clean_core:
        parts.append(f"副标题/核心句：{clean_core}")
    if clean_visible:
        parts.append(f"正文要点：{clean_visible}")
    return "；".join(parts) or "根据页面主题生成简洁中文标题和2到4条汇报要点"


def _first_usable_text(*values: str) -> str:
    for value in values:
        text = _clean_prompt_text(value, 500)
        if text and not _is_placeholder_text(text):
            return text
    return ""


def _clean_prompt_text(value: str, limit: int) -> str:
    text = re.sub(r"\[\[FIG:[^\]]+]]", "", value or "")
    text = re.sub(r"\[\[ASSET:[^\]]+]]", "", text)
    text = re.sub(
        r"\b(?:visible_content|page_core_sentence|asset_status|fallback_visual|export_gate|layout_hint|primary_visual|operator_action|expected_screen_state)\s*[:：]",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"asset_status\s*[:：]\s*\w+", "", text, flags=re.I)
    text = text.replace("**", "")
    text = re.sub(r"\s+", " ", text).strip(" `*_#：:，,。；;|")
    return text[:limit].strip()


def _is_placeholder_text(value: str) -> bool:
    text = re.sub(r"\s+", "", value or "")
    if not text:
        return True
    placeholders = (
        "本页围绕项目事实展开说明",
        "请补充本页可见正文",
        "本页需补充正式核心句",
        "内容待确认",
        "待补充",
        "待确认",
    )
    return any(item in text for item in placeholders)


def _is_empty_asset_hint(value: str) -> bool:
    text = (value or "").strip().lower()
    return not text or text in {"无", "none", "not_required", "asset_status: not_required", "asset_status:not_required"}


def _failure_notice(message: str | None) -> str:
    if not message:
        return ""
    safe = html.escape(_clip(message, 100))
    return (
        '<rect x="812" y="548" width="390" height="92" rx="0" fill="#3b1d12" fill-opacity="0.74" stroke="#ffb385" stroke-opacity="0.30"/>'
        '<text x="836" y="576" fill="#ffb385" font-family="Microsoft YaHei, PingFang SC, Arial" font-size="12" font-weight="800">IMAGE2 RETRY FAILED</text>'
        f'<text x="836" y="604" fill="#ffe8d8" font-family="Microsoft YaHei, PingFang SC, Arial" font-size="13" font-weight="600">{safe}</text>'
    )


def _summarize_design_spec(design_spec: str) -> str:
    lines = []
    for raw in design_spec.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if any(key in line.lower() for key in ("palette", "color", "visual", "style", "layout", "roadshow", "competition")):
            lines.append(line)
        if len(" ".join(lines)) > 900:
            break
    return " ".join(lines) or design_spec[:900]


def _clip(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def _safe_error(value: str) -> str:
    text = value or ""
    secret = settings.image2_api_key or ""
    if secret:
        text = text.replace(secret, "[redacted]")
    if "524" in text:
        return "image2 服务网关超时(524)，上游生图超过当前网关等待时间"
    if "ReadTimeout" in text or "timed out" in text.lower():
        return f"image2 服务在 {_image2_timeout():.0f}s 内未返回"
    if "RemoteProtocolError" in text or "disconnected" in text.lower():
        return "image2 服务连接中断，未返回图片结果"
    text = re.sub(r"https?://\\S+", "[url]", text)
    return _clip(text, 120)
