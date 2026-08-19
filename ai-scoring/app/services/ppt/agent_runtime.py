"""Runtime adapter for the integrated paper-ppt-agent subsystem.

The original project is kept as an internal package under
``app/services/ppt/agent`` so we can preserve its full capability surface while
running it inside the ai-scoring FastAPI process.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from app.config import settings as ai_settings

PPT_SERVICE_DIR = Path(__file__).resolve().parent
AGENT_ROOT = PPT_SERVICE_DIR / "agent"
AGENT_BACKEND_ROOT = AGENT_ROOT / "backend"
AGENT_ASSETS_ROOT = AGENT_ROOT / "assets"
AGENT_WORKSPACE_ROOT = Path(ai_settings.UPLOAD_DIR) / "ppt_agent"
AI_SCORING_ROOT = PPT_SERVICE_DIR.parents[2]
AI_SCORING_ENV = AI_SCORING_ROOT / ".env"

_BOOTSTRAPPED = False
TOKEN_PLAN_HOSTS = ("token-plan-cn.xiaomimimo.com",)


def _env_value(values: dict[str, str | None], name: str, fallback: str = "") -> str:
    raw = values.get(name)
    if raw is None or raw == "":
        raw = os.getenv(name, fallback)
    return str(raw or "").strip()


def _set_env(name: str, value: str | None) -> None:
    if value:
        os.environ[name] = value


def _append_no_proxy(*hosts: str) -> None:
    """Ensure token-plan endpoints bypass local HTTP/SOCKS proxies.

    The local dev environment may export HTTP_PROXY/HTTPS_PROXY.  The MiMo
    token-plan host is reachable directly but can fail during TLS tunneling
    through the local proxy, so keep this scoped to the known token-plan host.
    """
    existing = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    parts = [part.strip() for part in existing.split(",") if part.strip()]
    seen = {part.lower() for part in parts}
    for host in hosts:
        if host.lower() not in seen:
            parts.append(host)
            seen.add(host.lower())
    merged = ",".join(parts)
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged


def _set_env_defaults() -> None:
    """Map ai-scoring env names to paper-ppt-agent env names."""
    env_values = {
        str(key): str(value) if value is not None else None
        for key, value in dotenv_values(AI_SCORING_ENV).items()
    }

    text_key = _env_value(
        env_values,
        "PPT_TEXT_API_KEY",
        _env_value(env_values, "MIMO_API_KEY", ai_settings.MIMO_API_KEY),
    )
    text_base_url = _env_value(
        env_values,
        "PPT_TEXT_BASE_URL",
        _env_value(
            env_values,
            "MIMO_BASE_URL",
            ai_settings.MIMO_BASE_URL or "https://token-plan-cn.xiaomimimo.com/anthropic",
        ),
    )
    text_model = _env_value(
        env_values,
        "PPT_TEXT_MODEL",
        _env_value(env_values, "MIMO_MODEL", ai_settings.MIMO_MODEL or "mimo-v2.5-pro"),
    )

    _set_env("MIMO_API_KEY", text_key)
    _set_env("MIMO_BASE_URL", text_base_url)
    _set_env("MIMO_MODEL", text_model)
    _set_env("DEFAULT_LLM_PROVIDER", "mimo")
    _set_env("DEFAULT_LLM_MODEL", text_model)

    web_key = _env_value(env_values, "MIMO_WEB_API_KEY", ai_settings.MIMO_WEB_API_KEY)
    web_base_url = _env_value(
        env_values,
        "MIMO_WEB_BASE_URL",
        ai_settings.MIMO_WEB_BASE_URL or "https://api.xiaomimimo.com/v1/chat/completions",
    )
    web_model = _env_value(env_values, "MIMO_WEB_MODEL", ai_settings.MIMO_WEB_MODEL or text_model)
    _set_env("MIMO_WEB_API_KEY", web_key)
    _set_env("MIMO_WEB_BASE_URL", web_base_url)
    _set_env("MIMO_WEB_MODEL", web_model)
    if "token-plan-cn.xiaomimimo.com" in text_base_url or "token-plan-cn.xiaomimimo.com" in web_base_url:
        _append_no_proxy(*TOKEN_PLAN_HOSTS)

    if ai_settings.DASHSCOPE_API_KEY:
        _set_env("DASHSCOPE_API_KEY", ai_settings.DASHSCOPE_API_KEY)
    if ai_settings.DASHSCOPE_BASE_URL:
        _set_env("DASHSCOPE_BASE_URL", ai_settings.DASHSCOPE_BASE_URL)
    if ai_settings.PPT_VISION_API_KEY:
        _set_env("PPT_VISION_API_KEY", ai_settings.PPT_VISION_API_KEY)
    if ai_settings.PPT_VISION_BASE_URL:
        _set_env("PPT_VISION_BASE_URL", ai_settings.PPT_VISION_BASE_URL)
    if ai_settings.PPT_VISION_MODEL:
        _set_env("PPT_VISION_MODEL", ai_settings.PPT_VISION_MODEL)
    if ai_settings.PPT_IMAGE_API_KEY:
        _set_env("PPT_IMAGE_API_KEY", ai_settings.PPT_IMAGE_API_KEY)
    if ai_settings.PPT_IMAGE_MODEL:
        _set_env("PPT_IMAGE_MODEL", ai_settings.PPT_IMAGE_MODEL)
    if ai_settings.IMAGE2_API_KEY:
        _set_env("IMAGE2_API_KEY", ai_settings.IMAGE2_API_KEY)
    if ai_settings.IMAGE2_BASE_URL:
        _set_env("IMAGE2_BASE_URL", ai_settings.IMAGE2_BASE_URL)
    if ai_settings.IMAGE2_MODEL:
        _set_env("IMAGE2_MODEL", ai_settings.IMAGE2_MODEL)
    _set_env("IMAGE2_API_PROTOCOL", ai_settings.IMAGE2_API_PROTOCOL)
    _set_env("IMAGE2_RESOLUTION", ai_settings.IMAGE2_RESOLUTION)
    _set_env("IMAGE2_EXPORT_MODE", ai_settings.IMAGE2_EXPORT_MODE)
    _set_env("IMAGE2_RETRY_ATTEMPTS", str(ai_settings.IMAGE2_RETRY_ATTEMPTS))
    _set_env("IMAGE2_RETRY_BASE_DELAY", str(ai_settings.IMAGE2_RETRY_BASE_DELAY))
    _set_env("IMAGE2_TIMEOUT_SECONDS", str(ai_settings.IMAGE2_TIMEOUT_SECONDS))
    os.environ.setdefault("IMAGE_BACKEND", "qwen-image")


def bootstrap_ppt_agent() -> Any:
    """Make the vendored paper-ppt-agent backend importable and configured."""
    global _BOOTSTRAPPED
    _set_env_defaults()
    agent_root_str = str(AGENT_ROOT)
    if agent_root_str not in sys.path:
        sys.path.insert(0, agent_root_str)

    from backend.config import settings as agent_settings

    agent_settings.assets_dir = AGENT_ASSETS_ROOT
    agent_settings.templates_dir = AGENT_ASSETS_ROOT / "templates"
    agent_settings.icons_dir = AGENT_ASSETS_ROOT / "icons"
    agent_settings.references_dir = AGENT_ASSETS_ROOT / "references"
    agent_settings.workspaces_dir = AGENT_WORKSPACE_ROOT / "workspaces"
    agent_settings.runtime_dir = AGENT_WORKSPACE_ROOT / ".runtime"
    agent_settings.workspaces_dir.mkdir(parents=True, exist_ok=True)
    agent_settings.runtime_dir.mkdir(parents=True, exist_ok=True)

    _BOOTSTRAPPED = True
    return agent_settings


async def startup_ppt_agent_runtime() -> None:
    """Start paper-ppt-agent runtime services inside ai-scoring."""
    settings = bootstrap_ppt_agent()
    from backend.runtime.offload import init_offload
    from backend.runtime.scheduler import get_scheduler

    init_offload(settings.io_pool_workers)
    await get_scheduler().start()


async def shutdown_ppt_agent_runtime() -> None:
    """Drain scheduler and shutdown the shared offload pool."""
    if not _BOOTSTRAPPED:
        return
    from backend.runtime.offload import shutdown_offload
    from backend.runtime.scheduler import get_scheduler

    await get_scheduler().shutdown(timeout=30.0)
    shutdown_offload()
