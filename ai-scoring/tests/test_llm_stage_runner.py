from types import SimpleNamespace

import pytest

from app.services.llm_stage_runner import StageGenerationError, run_json_stage


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def response(content, *, finish_reason="stop", completion_tokens=100):
    return SimpleNamespace(
        choices=[SimpleNamespace(
            finish_reason=finish_reason,
            message=SimpleNamespace(content=content),
        )],
        usage=SimpleNamespace(
            prompt_tokens=200,
            completion_tokens=completion_tokens,
            total_tokens=200 + completion_tokens,
        ),
    )


def test_length_finish_reason_retries_only_the_current_stage():
    client = FakeClient([
        response('{"value": 1}', finish_reason="length", completion_tokens=5000),
        response('{"value": 2}', completion_tokens=120),
    ])

    result, meta = run_json_stage(
        client=client,
        model="deepseek-chat",
        stage="core",
        messages=[{"role": "user", "content": "生成完整核心评分"}],
        max_tokens=5000,
        validator=lambda payload: payload,
    )

    assert result == {"value": 2}
    assert meta["status"] == "completed"
    assert meta["attempts"] == 2
    assert meta["attempt_log"][0]["truncated"] is True
    assert meta["attempt_log"][0]["finish_reason"] == "length"
    assert "不得删减" in client.chat.completions.calls[1]["messages"][-1]["content"]


def test_invalid_json_twice_raises_with_auditable_attempts():
    client = FakeClient([
        response('{"value":', completion_tokens=80),
        response('still not json', completion_tokens=30),
    ])

    with pytest.raises(StageGenerationError) as exc_info:
        run_json_stage(
            client=client,
            model="deepseek-chat",
            stage="evidence",
            messages=[{"role": "user", "content": "生成证据分析"}],
            max_tokens=4500,
            validator=lambda payload: payload,
        )

    assert exc_info.value.stage == "evidence"
    assert exc_info.value.meta["status"] == "failed"
    assert exc_info.value.meta["attempts"] == 2
    assert all(item["error"] for item in exc_info.value.meta["attempt_log"])


def test_validator_failure_retries_the_same_stage_with_full_regeneration():
    client = FakeClient([
        response('{"items": []}'),
        response('{"items": [1, 2]}'),
    ])

    def validate(payload):
        if len(payload.get("items", [])) != 2:
            raise ValueError("items_incomplete")
        return payload

    result, meta = run_json_stage(
        client=client,
        model="deepseek-chat",
        stage="jury",
        messages=[{"role": "user", "content": "生成完整评委结果"}],
        max_tokens=5500,
        validator=validate,
    )

    assert result["items"] == [1, 2]
    assert meta["attempt_log"][0]["error"] == "items_incomplete"
