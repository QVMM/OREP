"""Reliable, auditable execution for one structured LLM generation stage."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from typing import Callable


logger = logging.getLogger(__name__)


class StageGenerationError(RuntimeError):
    def __init__(self, stage: str, meta: dict, message: str):
        super().__init__(message)
        self.stage = stage
        self.meta = meta


def run_json_stage(
    *,
    client,
    model: str,
    stage: str,
    messages: list[dict],
    max_tokens: int,
    validator: Callable[[dict], dict],
    timeout: float | None = None,
    max_attempts: int = 2,
    temperature: float = 0.1,
) -> tuple[dict, dict]:
    """Generate and validate one complete JSON object, retrying only this stage."""
    attempt_log: list[dict] = []
    base_messages = deepcopy(messages)
    last_error = "unknown_stage_failure"

    for attempt in range(1, max_attempts + 1):
        attempt_messages = deepcopy(base_messages)
        if attempt > 1:
            attempt_messages.append({
                "role": "system",
                "content": (
                    "上一轮输出未通过完整性门禁。请从头完整重生成同一 JSON 对象；"
                    "不得删减任何数组、字段、评分理由、改进建议、评委或行动项，"
                    "不得续写残片，也不要输出 JSON 之外的文字。"
                ),
            })

        response = None
        finish_reason = None
        usage = None
        content = ""
        truncated = False
        error = None
        try:
            request = {
                "model": model,
                "messages": attempt_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if timeout is not None:
                request["timeout"] = timeout
            try:
                from app.services.llm_scoring_service import chat_completion_kwargs

                request = chat_completion_kwargs(**request)
            except Exception:
                pass
            response = client.chat.completions.create(**request)
            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None)
            content = getattr(choice.message, "content", "") or ""
            usage = getattr(response, "usage", None)
            completion_tokens = _usage_value(usage, "completion_tokens")
            reasoning_tokens = 0
            details = getattr(usage, "completion_tokens_details", None)
            if details is not None:
                reasoning_tokens = _usage_value(details, "reasoning_tokens")
            truncated = finish_reason == "length" or completion_tokens >= max(1, int(max_tokens * 0.98))
            if not content and reasoning_tokens > 0:
                raise ValueError(
                    f"empty_content_reasoning_exhausted:reasoning_tokens={reasoning_tokens}"
                )
            if truncated and not content:
                raise ValueError("response_truncated")
            if truncated:
                raise ValueError("response_truncated")
            payload = _parse_complete_json(content)
            validated = validator(payload)
        except Exception as exc:
            error = str(exc) or exc.__class__.__name__
            last_error = error
        attempt_log.append({
            "attempt": attempt,
            "finish_reason": finish_reason,
            "prompt_tokens": _usage_value(usage, "prompt_tokens"),
            "completion_tokens": _usage_value(usage, "completion_tokens"),
            "total_tokens": _usage_value(usage, "total_tokens"),
            "response_chars": len(content),
            "truncated": truncated,
            "error": error,
        })

        if error is None:
            meta = _build_meta(stage, "completed", attempt_log)
            logger.info(
                "LLM stage completed: stage=%s attempts=%s completion_tokens=%s chars=%s",
                stage,
                attempt,
                attempt_log[-1]["completion_tokens"],
                len(content),
            )
            return validated, meta

        logger.warning(
            "LLM stage attempt failed: stage=%s attempt=%s/%s error=%s finish_reason=%s",
            stage,
            attempt,
            max_attempts,
            error,
            finish_reason,
        )

    meta = _build_meta(stage, "failed", attempt_log)
    raise StageGenerationError(stage, meta, last_error)


def _parse_complete_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("stage_output_must_be_json_object")
    return payload


def _usage_value(usage, field: str) -> int:
    value = getattr(usage, field, 0) if usage is not None else 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _build_meta(stage: str, status: str, attempt_log: list[dict]) -> dict:
    return {
        "stage": stage,
        "status": status,
        "attempts": len(attempt_log),
        "prompt_tokens": sum(item["prompt_tokens"] for item in attempt_log),
        "completion_tokens": sum(item["completion_tokens"] for item in attempt_log),
        "total_tokens": sum(item["total_tokens"] for item in attempt_log),
        "attempt_log": attempt_log,
    }
