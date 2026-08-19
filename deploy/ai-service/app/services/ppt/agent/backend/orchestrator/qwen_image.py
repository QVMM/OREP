"""Qwen-Image helpers for slide image assets."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

DASHSCOPE_IMAGE_API_URL = "https://dashscope.aliyuncs.com/api/v1"


def qwen_image_configured() -> bool:
    return bool(settings.ppt_image_api_key or settings.dashscope_api_key)


async def generate_qwen_image_asset(query: str, output_dir: Path) -> Path | None:
    api_key = settings.ppt_image_api_key or settings.dashscope_api_key
    if not api_key:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt = (
        "为职业院校技能大赛 PPT 生成一张 16:9 专业视觉素材。"
        f"主题：{query}。"
        "要求：真实或高质量科技感视觉，可作为幻灯片插画或背景；"
        "不要生成任何可读文字、数字、logo、水印、按钮、网页 UI 控件、水印；"
        "画面干净、有层次、有留白，方便叠加中文标题和图表。"
    )
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    target = output_dir / f"qwen_image_{digest}.png"
    if target.exists():
        return target
    try:
        import dashscope  # type: ignore[import-not-found]
        from dashscope import MultiModalConversation  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashscope unavailable for Qwen-Image: %s", exc)
        return None

    dashscope.base_http_api_url = DASHSCOPE_IMAGE_API_URL
    try:
        response = MultiModalConversation.call(
            api_key=api_key,
            model=settings.ppt_image_model or "qwen-image-2.0-pro",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            result_format="message",
            stream=False,
            n=1,
            watermark=False,
            negative_prompt="文字, 数字, logo, 水印, 网页按钮, UI控件, 卡通, 低清晰度, 变形, 密集文字",
        )
        payload = _to_plain_dict(response)
        (output_dir / f"qwen_image_{digest}.json").write_text(
            json.dumps({"prompt": prompt, "model": settings.ppt_image_model, "raw_response": payload}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        refs = _collect_image_refs(payload)
        if not refs:
            return None
        await _save_image_ref(refs[0], target)
        return target if target.exists() else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qwen-Image generation failed: %s", exc)
        return None


def _to_plain_dict(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _to_plain_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain_dict(v) for v in value]
    return value


def _collect_image_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_l = str(key).lower()
            if key_l in {"url", "image", "image_url", "orig_url"} and isinstance(item, str):
                if item.startswith(("http://", "https://", "data:image/")):
                    refs.append(item)
            else:
                refs.extend(_collect_image_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.extend(_collect_image_refs(item))
    return refs


async def _save_image_ref(ref: str, target: Path) -> None:
    if ref.startswith("data:image/"):
        _, data = ref.split(",", 1)
        target.write_bytes(base64.b64decode(data))
        return
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        response = await client.get(ref)
        response.raise_for_status()
        target.write_bytes(response.content)
