"""Reliable delivery for Java backend callbacks."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx


class CallbackDeliveryError(RuntimeError):
    """Raised when a callback is not accepted after all attempts."""


class BackendCallbackClient:
    def __init__(
        self,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        timeout_seconds: float = 30,
    ):
        self._transport = transport
        self._sleep = sleep
        self._timeout_seconds = timeout_seconds

    async def send(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 1,
        backoff_seconds: float = 1,
    ) -> dict[str, Any]:
        attempts = max(1, int(max_attempts))
        last_error = "unknown_error"
        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                    trust_env=False,
                ) as client:
                    response = await client.post(url, json=payload)
                if not 200 <= response.status_code < 300:
                    raise RuntimeError(f"http_status={response.status_code}")
                try:
                    body = response.json()
                except ValueError as exc:
                    raise RuntimeError("non_json_response") from exc
                if not isinstance(body, dict):
                    raise RuntimeError("non_object_response")
                if body.get("code") != 200:
                    raise RuntimeError(
                        f"business_code={body.get('code')} message={body.get('message') or ''}"
                    )
                return body
            except Exception as exc:
                last_error = str(exc) or exc.__class__.__name__
                if attempt < attempts:
                    await self._sleep(backoff_seconds * (2 ** (attempt - 1)))
        raise CallbackDeliveryError(f"callback_rejected attempts={attempts} last_error={last_error}")
