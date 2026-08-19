"""Anthropic LLM provider using the native anthropic SDK."""

from __future__ import annotations

import base64
import os
import time
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from backend.usage.tracker import current_usage_context, usage_tracker

from .base import LLMProvider
from .retry import call_with_retry
from .types import (
    ContentBlock,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ModelInfo,
    ProviderInfo,
    TokenUsage,
)


class AnthropicProvider(LLMProvider):
    """Anthropic provider wrapping AsyncAnthropic."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        provider_name: str = "anthropic",
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        self._provider_name = provider_name
        self._base_url = (base_url or "").rstrip("/")

    def _split_system_and_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[dict]]:
        """Split system message from conversation messages.

        Anthropic requires system prompt as a separate top-level parameter.
        """
        system_text = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                if isinstance(msg.content, str):
                    system_text = msg.content
                continue

            if isinstance(msg.content, str):
                api_messages.append({"role": msg.role, "content": msg.content})
            else:
                parts = []
                for block in msg.content:
                    if block.type == "text" and block.text:
                        parts.append({"type": "text", "text": block.text})
                    elif block.type == "image" and block.image_data:
                        b64 = base64.b64encode(block.image_data).decode()
                        media = block.image_media_type or "image/png"
                        parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media,
                                "data": b64,
                            },
                        })
                api_messages.append({"role": msg.role, "content": parts})

        return system_text, api_messages

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: type[BaseModel] | None = None,
    ) -> LLMResponse:
        system_text, api_messages = self._split_system_and_messages(messages)

        kwargs = self._build_message_kwargs(
            api_messages,
            model,
            system_text=system_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        t0 = time.monotonic()
        resp = await call_with_retry(lambda: self._stream_message(kwargs))
        duration_ms = int((time.monotonic() - t0) * 1000)

        usage = TokenUsage(
            prompt_tokens=getattr(resp.usage, "input_tokens", 0) if resp.usage else 0,
            completion_tokens=getattr(resp.usage, "output_tokens", 0) if resp.usage else 0,
        )
        ctx = current_usage_context()
        usage_tracker.record(
            provider=self._provider_name,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            job_id=ctx.get("job_id"),
            stage=ctx.get("stage"),
            page=ctx.get("page"),
            attempt=ctx.get("attempt") or 1,
            duration_ms=duration_ms,
        )
        return LLMResponse(content=self._message_text(resp), usage=usage, raw=resp)

    def _build_message_kwargs(
        self,
        api_messages: list[dict],
        model: str,
        *,
        system_text: str | None,
        temperature: float,
        max_tokens: int | None,
    ) -> dict:
        token_limit = max_tokens or 8192
        if self._provider_name == "mimo" or "xiaomimimo.com" in self._base_url:
            limit = int(os.getenv("MIMO_MAX_TOKENS", "24000") or "24000")
            token_limit = min(token_limit, limit)
        kwargs: dict = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": token_limit,
        }
        if system_text:
            kwargs["system"] = system_text
        return kwargs

    def _message_text(self, resp) -> str:
        content = ""
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                content += block.text
        return content

    async def _stream_message(self, kwargs: dict):
        async with self._client.messages.stream(**kwargs) as stream:
            await stream.until_done()
            return await stream.get_final_message()

    async def chat_stream(
        self,
        messages: list[LLMMessage],
        model: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        system_text, api_messages = self._split_system_and_messages(messages)

        kwargs = self._build_message_kwargs(
            api_messages,
            model,
            system_text=system_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield LLMStreamChunk(delta=text)

    async def validate(self) -> bool:
        try:
            model = "mimo-v2.5-pro" if self._provider_name == "mimo" else "claude-sonnet-4.6"
            await self._client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    def get_provider_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="anthropic",
            display_name="Anthropic",
            models=[
                ModelInfo(
                    id="claude-opus-4.6",
                    display_name="Claude Opus 4.6",
                    supports_vision=True,
                    supports_structured_output=True,
                    context_window=200000,
                ),
                ModelInfo(
                    id="claude-sonnet-4.6",
                    display_name="Claude Sonnet 4.6",
                    supports_vision=True,
                    supports_structured_output=True,
                    context_window=200000,
                ),
                ModelInfo(
                    id="claude-haiku-4.6",
                    display_name="Claude Haiku 4.6",
                    supports_vision=True,
                    supports_structured_output=True,
                    context_window=200000,
                ),
            ],
        )
