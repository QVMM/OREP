"""Global configuration using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Canvas format definitions (adapted from ppt-master)
CANVAS_FORMATS = {
    "ppt169": {
        "name": "PPT 16:9",
        "width": 1280,
        "height": 720,
        "viewbox": "0 0 1280 720",
        "ratio": "16:9",
    },
    "ppt43": {
        "name": "PPT 4:3",
        "width": 1024,
        "height": 768,
        "viewbox": "0 0 1024 768",
        "ratio": "4:3",
    },
}

# Design color schemes
DESIGN_STYLES = {
    "academic": {
        "name": "Academic",
        "background": "#FFFFFF",
        "primary": "#1A365D",
        "accent": "#2B6CB0",
        "body_text": "#2D3748",
    },
    "consulting": {
        "name": "Consulting",
        "background": "#FFFFFF",
        "primary": "#003A70",
        "accent": "#0077B6",
        "body_text": "#1A202C",
    },
    "tech": {
        "name": "Tech",
        "background": "#0F172A",
        "primary": "#3B82F6",
        "accent": "#06B6D4",
        "body_text": "#E2E8F0",
    },
    "general": {
        "name": "General",
        "background": "#FFFFFF",
        "primary": "#4F46E5",
        "accent": "#7C3AED",
        "body_text": "#374151",
    },
    "roadshow": {
        "name": "Competition Roadshow",
        "background": "#F7FAFC",
        "primary": "#0F766E",
        "accent": "#2563EB",
        "body_text": "#1F2937",
    },
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM defaults
    default_llm_provider: Literal["mimo", "qwen", "openai", "deepseek", "anthropic", "gemini"] = "mimo"
    default_llm_model: str = "gpt-4o"
    mimo_api_key: str | None = None
    mimo_base_url: str | None = "https://token-plan-cn.xiaomimimo.com/anthropic"
    mimo_model: str = "mimo-v2.5-pro"
    mimo_web_api_key: str | None = None
    mimo_web_base_url: str | None = "https://api.xiaomimimo.com/v1/chat/completions"
    mimo_web_model: str | None = None
    dashscope_api_key: str | None = None
    dashscope_base_url: str | None = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_text_model: str = "qwen3.6-plus"
    qwen_vision_model: str = "qwen3-vl-flash"
    ppt_vision_api_key: str | None = None
    ppt_vision_base_url: str | None = None
    ppt_vision_model: str | None = None
    ppt_image_api_key: str | None = None
    ppt_image_model: str = "qwen-image-2.0-pro"
    visual_qa_provider: str = "qwen"
    visual_qa_model: str | None = None
    visual_qa_api_key: str | None = None
    visual_qa_base_url: str | None = None
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # Paper parsing
    mineru_api_key: str | None = None
    mineru_api_url: str | None = None

    # Image generation
    image_backend: str | None = None
    image2_api_key: str | None = None
    image2_base_url: str = "https://img.alibaba.cv"
    image2_model: str = "gpt-image-2"
    image2_api_protocol: Literal["auto", "chat", "images"] = "auto"
    image2_resolution: Literal["1K", "2K", "4K"] = "2K"
    image2_export_mode: Literal["svg", "editable", "image"] = "image"
    image2_retry_attempts: int = 3
    image2_retry_base_delay: float = 1.5
    image2_timeout_seconds: int = 300

    # Paths
    assets_dir: Path = PROJECT_ROOT / "assets"
    workspaces_dir: Path = PROJECT_ROOT / "workspaces"
    runtime_dir: Path = PROJECT_ROOT / ".runtime"
    templates_dir: Path = PROJECT_ROOT / "assets" / "templates"
    icons_dir: Path = PROJECT_ROOT / "assets" / "icons"
    references_dir: Path = PROJECT_ROOT / "assets" / "references"

    # Limits
    # Historical compatibility knob. Job scheduling is now immediate and
    # per-job; this no longer caps generate/refine submissions.
    max_concurrent_jobs: int = 1
    max_upload_bytes: int = 64 * 1024 * 1024  # 64 MB per uploaded paper

    # ── Async runtime ────────────────────────────────────────────────────
    # Size of the global ThreadPoolExecutor used by ``runtime.aoffload``.
    # All blocking file IO and CPU-bound library calls (fitz, python-pptx,
    # cairosvg, PIL) flow through this pool, so size it for IO concurrency
    # rather than core count.
    io_pool_workers: int = 16

    # ── Job scheduling ───────────────────────────────────────────────────
    # Backlog cap for queued jobs; a 16th queued job returns 429.
    job_queue_capacity: int = 16

    # ── External tool timeouts (seconds) ─────────────────────────────────
    pandoc_timeout: int = 60
    pdflatex_timeout: int = 90
    cairosvg_timeout: int = 30
    # Upper bound for one SVG LLM call. A single slow provider response should
    # not freeze the whole deck; the executor will retry or fall back per page.
    svg_llm_call_timeout: int = 240
    # Soft stall detector for roadshow research LLM requests. This is not a
    # hard task kill by itself: if the upstream connection stays silent for
    # this long, the same full-quality request is re-issued (limited times).
    # 300s felt "stuck" on editable plan_only; 150s balances recovery vs speed.
    roadshow_research_llm_stall_retry_seconds: int = 150
    # Max re-issues after stall (total attempts = this value). Keep small so
    # plan_only does not burn 10+ minutes on one silent Pass.
    roadshow_research_llm_stall_max_attempts: int = 2
    # Parallel page-segment workers for light SlideContentPlan tables (plan_only
    # and full SVG planning). Page count stays 35-45; only generation is sharded.
    roadshow_parallel_segments: int = 3
    # Number of parallel equation renders allowed in flight.
    equation_render_concurrency: int = 4

    # ── WebSocket ────────────────────────────────────────────────────────
    ws_subscriber_queue_size: int = 1024
    ws_heartbeat_seconds: int = 15

    # ── Persistence ──────────────────────────────────────────────────────
    # Debounce window (ms) for full session_state.json snapshots. Events
    # always go to the per-job NDJSON stream synchronously so nothing is
    # lost on a hard crash; the snapshot just rolls up indices.
    persist_debounce_ms: int = 200


settings = Settings()
