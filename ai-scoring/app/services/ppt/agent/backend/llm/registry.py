"""LLM provider registry and factory."""

from __future__ import annotations

from importlib import import_module

from backend.config import settings

from .base import LLMProvider
from .types import ModelInfo, ProviderInfo

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/anthropic"

_PROVIDER_IMPORTS: dict[str, tuple[str, str]] = {
    "mimo": ("backend.llm.provider_openai", "OpenAIProvider"),
    "qwen": ("backend.llm.provider_openai", "OpenAIProvider"),
    "openai": ("backend.llm.provider_openai", "OpenAIProvider"),
    "deepseek": ("backend.llm.provider_openai", "OpenAIProvider"),
    "anthropic": ("backend.llm.provider_anthropic", "AnthropicProvider"),
    "gemini": ("backend.llm.provider_gemini", "GeminiProvider"),
}

_PROVIDER_INFO: dict[str, ProviderInfo] = {
    "mimo": ProviderInfo(
        name="mimo",
        display_name="MiMo",
        default_base_url=settings.mimo_base_url or MIMO_BASE_URL,
        models=[
            ModelInfo(
                id=settings.mimo_model or "mimo-v2.5-pro",
                display_name=settings.mimo_model or "MiMo V2.5 Pro",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
            ModelInfo(
                id="mimo-v2-omni",
                display_name="MiMo V2 Omni",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
        ],
    ),
    "openai": ProviderInfo(
        name="openai",
        display_name="OpenAI",
        models=[
            ModelInfo(
                id="gpt-5.5",
                display_name="GPT-5.5",
                supports_vision=True,
                supports_structured_output=True,
                context_window=400000,
            ),
            ModelInfo(
                id="gpt-5.4",
                display_name="GPT-5.4",
                supports_vision=True,
                supports_structured_output=True,
                context_window=400000,
            ),
        ],
    ),
    "qwen": ProviderInfo(
        name="qwen",
        display_name="Qwen / DashScope",
        default_base_url=settings.dashscope_base_url,
        models=[
            ModelInfo(
                id=settings.qwen_text_model or "qwen3.6-plus",
                display_name=settings.qwen_text_model or "Qwen Text",
                supports_vision=False,
                supports_structured_output=True,
                context_window=128000,
            ),
            ModelInfo(
                id=settings.qwen_vision_model or "qwen3-vl-flash",
                display_name=settings.qwen_vision_model or "Qwen Vision",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
            ModelInfo(
                id="qwen3-omni-flash-2025-12-01",
                display_name="Qwen3 Omni Flash",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
        ],
    ),
    "deepseek": ProviderInfo(
        name="deepseek",
        display_name="DeepSeek",
        default_base_url=DEEPSEEK_BASE_URL,
        models=[
            ModelInfo(
                id="deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
            ModelInfo(
                id="deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                supports_vision=True,
                supports_structured_output=True,
                context_window=128000,
            ),
        ],
    ),
    "anthropic": ProviderInfo(
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
    ),
    "gemini": ProviderInfo(
        name="gemini",
        display_name="Google Gemini",
        models=[
            ModelInfo(
                id="gemini-3.1-pro-preview",
                display_name="Gemini 3.1 Pro Preview",
                supports_vision=True,
                supports_structured_output=True,
                context_window=1048576,
            ),
            ModelInfo(
                id="gemini-3.1-flash-preview",
                display_name="Gemini 3.1 Flash Preview",
                supports_vision=True,
                supports_structured_output=True,
                context_window=1048576,
            ),
        ],
    ),
}


def _configured_secret(*values: str | None) -> str:
    """Return the first real secret, skipping empty values and .env placeholders."""
    for value in values:
        if not value:
            continue
        normalized = value.strip()
        if normalized.startswith("${") and normalized.endswith("}"):
            continue
        return normalized
    return ""


def _load_class(module_name: str, class_name: str) -> type[LLMProvider]:
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        missing = exc.name or module_name
        raise RuntimeError(
            f"Provider module '{module_name}' is unavailable because the optional dependency "
            f"'{missing}' is not installed."
        ) from exc
    return getattr(module, class_name)


def _load_provider_class(name: str) -> type[LLMProvider]:
    module_name, class_name = _PROVIDER_IMPORTS[name]
    return _load_class(module_name, class_name)


def _uses_anthropic_protocol(base_url: str | None) -> bool:
    return "anthropic" in (base_url or "").lower()


def create_provider(
    name: str,
    api_key: str,
    *,
    base_url: str | None = None,
    deepseek_settings: dict | None = None,
    openai_settings: dict | None = None,
) -> LLMProvider:
    """Create an LLM provider instance by name."""
    if name not in _PROVIDER_IMPORTS:
        raise ValueError(f"Unknown provider '{name}'. Available: {list(_PROVIDER_IMPORTS)}")

    cls = _load_provider_class(name)
    if name in {"mimo", "qwen", "openai", "deepseek"}:
        resolved_base_url = base_url
        if name == "deepseek" and not resolved_base_url:
            resolved_base_url = DEEPSEEK_BASE_URL
        if name == "mimo":
            # MiMo is configured server-side for this integration. Prefer the
            # local .env endpoint/key so stale browser localStorage cannot
            # override it with an old token-plan URL or invalid key.
            resolved_base_url = settings.mimo_base_url or resolved_base_url or MIMO_BASE_URL
            api_key = settings.mimo_api_key or api_key or ""
            if not api_key:
                raise ValueError(
                    "MiMo API key is not configured. Set MIMO_API_KEY in the environment or enter it in the UI."
                )
            if _uses_anthropic_protocol(resolved_base_url):
                anthropic_cls = _load_class(
                    "backend.llm.provider_anthropic",
                    "AnthropicProvider",
                )
                return anthropic_cls(
                    api_key=api_key,
                    base_url=resolved_base_url,
                    provider_name="mimo",
                )
        if name == "qwen":
            resolved_base_url = resolved_base_url or settings.dashscope_base_url
            api_key = _configured_secret(
                settings.visual_qa_api_key,
                settings.ppt_vision_api_key,
                settings.dashscope_api_key,
                api_key,
            )
            if not api_key:
                raise ValueError(
                    "Qwen API key is not configured. Set DASHSCOPE_API_KEY or PPT_VISION_API_KEY."
                )
        kwargs = {
            "api_key": api_key,
            "base_url": resolved_base_url,
            "provider_name": name,
        }
        if deepseek_settings is not None:
            kwargs["deepseek_settings"] = deepseek_settings
        if openai_settings is not None:
            kwargs["openai_settings"] = openai_settings
        return cls(**kwargs)
    return cls(api_key=api_key)


def list_providers() -> list[ProviderInfo]:
    """List configured providers without importing optional SDKs."""
    return list(_PROVIDER_INFO.values())
