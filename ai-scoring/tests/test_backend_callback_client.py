import asyncio

import httpx
import pytest

from app.services.backend_callback_client import BackendCallbackClient, CallbackDeliveryError
from app.services.session_pipeline_service import deliver_completion_callback


def test_retries_business_error_then_accepts_code_200():
    attempts = []

    def handler(request):
        attempts.append(request)
        if len(attempts) < 3:
            return httpx.Response(200, json={"code": 500, "message": "write failed"})
        return httpx.Response(200, json={"code": 200, "message": "success"})

    client = BackendCallbackClient(
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: _completed_sleep(),
    )

    response = asyncio.run(client.send(
        "http://backend/callback",
        {"status": "completed"},
        max_attempts=3,
        backoff_seconds=0,
    ))

    assert response["code"] == 200
    assert len(attempts) == 3


def test_retries_http_failure_and_raises_after_exhaustion():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(503, json={"code": 503, "message": "unavailable"})

    client = BackendCallbackClient(
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: _completed_sleep(),
    )

    with pytest.raises(CallbackDeliveryError, match="attempts=2"):
        asyncio.run(client.send(
            "http://backend/callback",
            {"status": "completed"},
            max_attempts=2,
            backoff_seconds=0,
        ))

    assert len(attempts) == 2


def test_non_json_success_response_is_not_accepted():
    client = BackendCallbackClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, text="ok")),
        sleep=lambda _seconds: _completed_sleep(),
    )

    with pytest.raises(CallbackDeliveryError, match="non_json_response"):
        asyncio.run(client.send(
            "http://backend/callback",
            {"status": "completed"},
            max_attempts=1,
            backoff_seconds=0,
        ))


async def _completed_sleep():
    return None


def test_completion_exhaustion_marks_result_writeback_failed():
    class StubClient:
        def __init__(self):
            self.calls = []

        async def send(self, url, payload, **kwargs):
            self.calls.append((url, payload, kwargs))
            if payload["status"] == "completed":
                raise CallbackDeliveryError("callback_rejected attempts=3 last_error=bad contract")
            return {"code": 200, "message": "success"}

    client = StubClient()
    delivered = asyncio.run(deliver_completion_callback(
        client,
        "http://backend/callback",
        {
            "sessionId": 26,
            "status": "completed",
            "currentStage": "completed",
            "progressPercent": 100,
            "finalResult": {"overallScore": 49.5},
        },
    ))

    assert delivered is False
    assert len(client.calls) == 2
    failure_payload = client.calls[1][1]
    assert failure_payload["status"] == "failed"
    assert failure_payload["currentStage"] == "result_writeback_failed"
    assert failure_payload["progressPercent"] == 95
    assert "结果回写失败" in failure_payload["errorMessage"]
