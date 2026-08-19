"""
AI智能评分微服务 — 配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # DashScope ASR
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "qwen3.6-plus")

    # PPT 多模型配置：文本/HTML/视觉可分别切换到 OpenAI-compatible 服务商。
    PPT_TEXT_API_KEY: str = os.getenv("PPT_TEXT_API_KEY", DASHSCOPE_API_KEY)
    PPT_TEXT_BASE_URL: str = os.getenv("PPT_TEXT_BASE_URL", DASHSCOPE_BASE_URL)
    PPT_TEXT_MODEL: str = os.getenv("PPT_TEXT_MODEL", DEFAULT_MODEL)
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", PPT_TEXT_API_KEY)
    MIMO_BASE_URL: str = os.getenv("MIMO_BASE_URL", PPT_TEXT_BASE_URL)
    MIMO_MODEL: str = os.getenv("MIMO_MODEL", PPT_TEXT_MODEL)
    MIMO_WEB_API_KEY: str = os.getenv("MIMO_WEB_API_KEY", "")
    MIMO_WEB_BASE_URL: str = os.getenv("MIMO_WEB_BASE_URL", "https://api.xiaomimimo.com/v1/chat/completions")
    MIMO_WEB_MODEL: str = os.getenv("MIMO_WEB_MODEL", MIMO_MODEL)

    PPT_HTML_API_KEY: str = os.getenv("PPT_HTML_API_KEY", PPT_TEXT_API_KEY)
    PPT_HTML_BASE_URL: str = os.getenv("PPT_HTML_BASE_URL", PPT_TEXT_BASE_URL)
    PPT_HTML_MODEL: str = os.getenv("PPT_HTML_MODEL", "qwen3-coder-plus")

    PPT_VISION_API_KEY: str = os.getenv("PPT_VISION_API_KEY", DASHSCOPE_API_KEY)
    PPT_VISION_BASE_URL: str = os.getenv("PPT_VISION_BASE_URL", DASHSCOPE_BASE_URL)
    PPT_VISION_MODEL: str = os.getenv("PPT_VISION_MODEL", DEFAULT_MODEL)
    PPT_VISION_REVIEW_ENABLED: bool = os.getenv("PPT_VISION_REVIEW_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    PPT_VISION_REVIEW_MAX_PAGES: int = int(os.getenv("PPT_VISION_REVIEW_MAX_PAGES", "8"))

    # PPT 图片素材生成：使用 DashScope MultiModalConversation / qwen-image-2.0-pro。
    PPT_IMAGE_API_KEY: str = os.getenv("PPT_IMAGE_API_KEY", DASHSCOPE_API_KEY)
    PPT_IMAGE_MODEL: str = os.getenv("PPT_IMAGE_MODEL", "qwen-image-2.0-pro")
    PPT_IMAGE_ASSETS_ENABLED: bool = os.getenv("PPT_IMAGE_ASSETS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    PPT_IMAGE_ASSET_MAX_PAGES: int = int(os.getenv("PPT_IMAGE_ASSET_MAX_PAGES", "6"))
    PPT_IMAGE_ASSET_N: int = int(os.getenv("PPT_IMAGE_ASSET_N", "1"))
    PPT_IMAGE_WATERMARK: bool = os.getenv("PPT_IMAGE_WATERMARK", "true").lower() in {"1", "true", "yes", "on"}

    # Image2 page renderer: OpenAI-compatible image generation service.
    IMAGE2_API_KEY: str = os.getenv("IMAGE2_API_KEY", "")
    IMAGE2_BASE_URL: str = os.getenv("IMAGE2_BASE_URL", "https://img.alibaba.cv")
    IMAGE2_MODEL: str = os.getenv("IMAGE2_MODEL", "gpt-image-2")
    IMAGE2_API_PROTOCOL: str = os.getenv("IMAGE2_API_PROTOCOL", "auto")
    IMAGE2_RESOLUTION: str = os.getenv("IMAGE2_RESOLUTION", "2K")
    IMAGE2_EXPORT_MODE: str = os.getenv("IMAGE2_EXPORT_MODE", "image")
    IMAGE2_RETRY_ATTEMPTS: int = int(os.getenv("IMAGE2_RETRY_ATTEMPTS", "3"))
    IMAGE2_RETRY_BASE_DELAY: float = float(os.getenv("IMAGE2_RETRY_BASE_DELAY", "1.5"))
    IMAGE2_TIMEOUT_SECONDS: int = int(os.getenv("IMAGE2_TIMEOUT_SECONDS", "300"))

    # DeepSeek LLM — API now requires deepseek-v4-pro / deepseek-v4-flash
    # (deepseek-chat is retired). Prefer pro for scoring quality.
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    # Core scoring: long roadshows need higher completion budget + segmented dims.
    LLM_CORE_MAX_TOKENS: int = max(
        2000, int(os.getenv("LLM_CORE_MAX_TOKENS", "12000"))
    )
    LLM_CORE_BATCH_MAX_TOKENS: int = max(
        1500, int(os.getenv("LLM_CORE_BATCH_MAX_TOKENS", "8000"))
    )
    # DeepSeek V4 supports up to 384K output tokens. Evidence extraction still
    # keeps a moderate single-shot budget and falls back to observation batches
    # when the response is truncated, instead of relying on unbounded growth.
    LLM_EVIDENCE_MAX_TOKENS: int = max(
        2000, int(os.getenv("LLM_EVIDENCE_MAX_TOKENS", "12000"))
    )
    LLM_EVIDENCE_BATCH_MAX_TOKENS: int = max(
        1500, int(os.getenv("LLM_EVIDENCE_BATCH_MAX_TOKENS", "6000"))
    )
    LLM_EVIDENCE_BATCH_SIZE: int = max(
        3, int(os.getenv("LLM_EVIDENCE_BATCH_SIZE", "5"))
    )
    LLM_EVIDENCE_MODEL_MAX_OUTPUT_TOKENS: int = max(
        4000, int(os.getenv("LLM_EVIDENCE_MODEL_MAX_OUTPUT_TOKENS", "384000"))
    )
    LLM_JURY_MAX_TOKENS: int = max(
        2000, int(os.getenv("LLM_JURY_MAX_TOKENS", "9000"))
    )
    LLM_SCORING_TRANSCRIPT_MAX_CHARS: int = max(
        8000, int(os.getenv("LLM_SCORING_TRANSCRIPT_MAX_CHARS", "48000"))
    )
    # Evidence extraction: never hard-cut only the head of a long roadshow.
    # Pack the full timeline into labeled parts (time buckets) under this budget.
    LLM_EVIDENCE_TRANSCRIPT_MAX_CHARS: int = max(
        8000, int(os.getenv("LLM_EVIDENCE_TRANSCRIPT_MAX_CHARS", "48000"))
    )
    LLM_EVIDENCE_TRANSCRIPT_PART_CHARS: int = max(
        2000, int(os.getenv("LLM_EVIDENCE_TRANSCRIPT_PART_CHARS", "10000"))
    )
    LLM_EVIDENCE_TRANSCRIPT_MAX_PARTS: int = max(
        1, int(os.getenv("LLM_EVIDENCE_TRANSCRIPT_MAX_PARTS", "8"))
    )
    # After rule scoring succeeds, generate coach-grade prose grounded on the ledger.
    # Free core scoring can be skipped to avoid a second conflicting score narrative.
    LLM_LEDGER_GROUNDED_REPORT_ENABLED: bool = os.getenv(
        "LLM_LEDGER_GROUNDED_REPORT_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LLM_LEDGER_GROUNDED_REPORT_MAX_TOKENS: int = max(
        4000, int(os.getenv("LLM_LEDGER_GROUNDED_REPORT_MAX_TOKENS", "14000"))
    )
    # Two-stage report (A=diagnosis/actions, B=jury/structure) keeps each call small.
    LLM_LEDGER_GROUNDED_REPORT_STAGE_MAX_TOKENS: int = max(
        1800, int(os.getenv("LLM_LEDGER_GROUNDED_REPORT_STAGE_MAX_TOKENS", "4500"))
    )
    LLM_LEDGER_GROUNDED_REPORT_STAGE_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LLM_LEDGER_GROUNDED_REPORT_STAGE_TIMEOUT_SECONDS", "150"))
    )
    LLM_SKIP_FREE_CORE_WHEN_RULE_READY: bool = os.getenv(
        "LLM_SKIP_FREE_CORE_WHEN_RULE_READY", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LLM_EVIDENCE_REQUEST_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LLM_EVIDENCE_REQUEST_TIMEOUT_SECONDS", "180"))
    )
    LLM_HTTP_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LLM_HTTP_TIMEOUT_SECONDS", "180"))
    )
    # DeepSeek V4 thinking can exhaust max_tokens and leave content empty.
    LLM_DISABLE_THINKING_FOR_JSON: bool = os.getenv(
        "LLM_DISABLE_THINKING_FOR_JSON", "true"
    ).lower() in {"1", "true", "yes", "on"}
    # Long-roadshow evidence extraction uses session memory (window scan + synthesize)
    # instead of stuffing the full transcript into one prompt.
    LLM_EVIDENCE_MEMORY_SESSION_ENABLED: bool = os.getenv(
        "LLM_EVIDENCE_MEMORY_SESSION_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LLM_EVIDENCE_MEMORY_MIN_DURATION_SEC: int = max(
        300, int(os.getenv("LLM_EVIDENCE_MEMORY_MIN_DURATION_SEC", "900"))
    )
    LLM_EVIDENCE_MEMORY_MIN_CHARS: int = max(
        2000, int(os.getenv("LLM_EVIDENCE_MEMORY_MIN_CHARS", "6000"))
    )
    LLM_EVIDENCE_MEMORY_WINDOW_SEC: int = max(
        180, int(os.getenv("LLM_EVIDENCE_MEMORY_WINDOW_SEC", "600"))
    )
    LLM_EVIDENCE_MEMORY_MAX_WINDOWS: int = max(
        3, int(os.getenv("LLM_EVIDENCE_MEMORY_MAX_WINDOWS", "8"))
    )
    LLM_EVIDENCE_MEMORY_WINDOW_CHARS: int = max(
        1500, int(os.getenv("LLM_EVIDENCE_MEMORY_WINDOW_CHARS", "3500"))
    )
    LLM_EVIDENCE_MEMORY_MAX_TOKENS: int = max(
        800, int(os.getenv("LLM_EVIDENCE_MEMORY_MAX_TOKENS", "2500"))
    )
    LLM_EVIDENCE_MEMORY_OBS_BATCH: int = max(
        1, int(os.getenv("LLM_EVIDENCE_MEMORY_OBS_BATCH", "3"))
    )

    # MiniMax LLM
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_BASE_URL: str = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_AUDIO: str = os.getenv("MINIO_BUCKET_AUDIO", "meeting-audio")
    MINIO_BUCKET_REPORTS: str = os.getenv("MINIO_BUCKET_REPORTS", "ai-reports")

    # 服务
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8090"))

    # 后端回调
    BACKEND_CALLBACK_URL: str = os.getenv("BACKEND_CALLBACK_URL", "http://127.0.0.1:8080/api/ai-score/callback")
    CHAT_CALLBACK_URL: str = os.getenv("CHAT_CALLBACK_URL", "http://127.0.0.1:8080/api/ai-chat/callback")

    # 竞赛助手
    ASSISTANT_INTERNAL_TOKEN: str = os.getenv(
        "ASSISTANT_INTERNAL_TOKEN",
        os.getenv("OREP_ASSISTANT_INTERNAL_TOKEN", "OREP_ASSISTANT_INTERNAL_DEV_TOKEN"),
    )
    ANYTHINGLLM_BASE_URL: str = os.getenv("ANYTHINGLLM_BASE_URL", "")
    ANYTHINGLLM_API_KEY: str = os.getenv("ANYTHINGLLM_API_KEY", "")
    # Docker 内默认走服务名；本地开发可覆盖为 http://127.0.0.1:8080
    BACKEND_INTERNAL_URL: str = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8080")
    # 扫描件 OCR（Tesseract）
    ASSISTANT_OCR_ENABLED: bool = os.getenv("ASSISTANT_OCR_ENABLED", "true").lower() in {
        "1", "true", "yes", "on"
    }
    ASSISTANT_OCR_LANG: str = os.getenv("ASSISTANT_OCR_LANG", "chi_sim+eng")
    ASSISTANT_OCR_MAX_PAGES: int = max(1, min(30, int(os.getenv("ASSISTANT_OCR_MAX_PAGES", "8"))))
    ASSISTANT_OCR_MIN_TEXT_CHARS: int = max(0, int(os.getenv("ASSISTANT_OCR_MIN_TEXT_CHARS", "40")))
    ASSISTANT_OCR_ZOOM: float = max(1.0, min(3.0, float(os.getenv("ASSISTANT_OCR_ZOOM", "2.0"))))
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "/opt/homebrew/bin/tesseract")

    # 文件路径
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

    # 视频分析配置
    VIDEO_MODEL: str = os.getenv("VIDEO_MODEL", "qwen3-vl-flash")
    VIDEO_FRAME_INTERVAL: int = int(os.getenv("VIDEO_FRAME_INTERVAL", "30"))  # 抽帧间隔（秒）
    VIDEO_ANALYSIS_MAX_FRAMES: int = int(os.getenv("VIDEO_ANALYSIS_MAX_FRAMES", "180"))  # 单次视觉分析最大帧数
    VIDEO_SCENE_DIFF_THRESHOLD: float = float(os.getenv("VIDEO_SCENE_DIFF_THRESHOLD", "0.12"))  # 场景变化补帧阈值
    VIDEO_BATCH_SIZE: int = int(os.getenv("VIDEO_BATCH_SIZE", "8"))  # 每批分析帧数
    VIDEO_ANALYSIS_MAX_WORKERS: int = max(1, int(os.getenv("VIDEO_ANALYSIS_MAX_WORKERS", "3")))
    VIDEO_AUDIO_WEIGHT: float = float(os.getenv("VIDEO_AUDIO_WEIGHT", "0.6"))  # 音频权重
    VIDEO_VISUAL_WEIGHT: float = float(os.getenv("VIDEO_VISUAL_WEIGHT", "0.4"))  # 视觉权重

    # 长音频分片识别并发度；只并发执行，不改变分片数量和时序合并。
    ASR_CHUNK_MAX_WORKERS: int = max(1, int(os.getenv("ASR_CHUNK_MAX_WORKERS", "3")))
    PRIMARY_EVIDENCE_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("PRIMARY_EVIDENCE_TIMEOUT_SECONDS", "900"))
    )

    # 统一媒体证据流：第一阶段只写影子快照，默认不开启。
    UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED: bool = os.getenv(
        "UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    EVIDENCE_CONTRACT_VERSION: str = os.getenv(
        "EVIDENCE_CONTRACT_VERSION", "media-evidence-v1"
    )
    UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED: bool = os.getenv(
        "UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    # LiveKit camera evidence stays an opt-in shadow channel until the
    # end-to-end accuracy and latency gates pass. It subscribes directly on the
    # private deployment network and never requires OSS/public media URLs.
    LIVE_CAMERA_SUBSCRIBER_ENABLED: bool = os.getenv(
        "LIVE_CAMERA_SUBSCRIBER_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    LIVEKIT_INTERNAL_WS_URL: str = os.getenv(
        "LIVEKIT_INTERNAL_WS_URL",
        os.getenv("LIVEKIT_URL", os.getenv("LIVEKIT_WS_URL", "ws://127.0.0.1:7880")),
    )
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")
    LIVE_CAMERA_TARGET_FPS: int = max(
        5, min(8, int(os.getenv("LIVE_CAMERA_TARGET_FPS", "6")))
    )
    LIVE_CAMERA_MAX_BACKLOG_MS: int = max(
        250, int(os.getenv("LIVE_CAMERA_MAX_BACKLOG_MS", "3000"))
    )
    LIVE_CAMERA_MAX_QUEUE_FRAMES: int = max(
        1, int(os.getenv("LIVE_CAMERA_MAX_QUEUE_FRAMES", "32"))
    )
    LIVE_CAMERA_JPEG_MAX_WIDTH: int = max(
        320, int(os.getenv("LIVE_CAMERA_JPEG_MAX_WIDTH", "960"))
    )
    LIVE_CAMERA_JPEG_QUALITY: int = max(
        40, min(90, int(os.getenv("LIVE_CAMERA_JPEG_QUALITY", "70")))
    )
    LOCAL_SPEAKER_DIARIZATION_ENABLED: bool = os.getenv(
        "LOCAL_SPEAKER_DIARIZATION_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_DIARIZATION_MODEL_DIR: str = os.getenv(
        "LOCAL_DIARIZATION_MODEL_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models",
            "speaker-diarization",
        ),
    )
    LOCAL_DIARIZATION_SEGMENTATION_MODEL: str = os.getenv(
        "LOCAL_DIARIZATION_SEGMENTATION_MODEL",
        os.path.join(
            LOCAL_DIARIZATION_MODEL_DIR,
            "sherpa-onnx-pyannote-segmentation-3-0",
            "model.int8.onnx",
        ),
    )
    LOCAL_DIARIZATION_EMBEDDING_MODEL: str = os.getenv(
        "LOCAL_DIARIZATION_EMBEDDING_MODEL",
        os.path.join(
            LOCAL_DIARIZATION_MODEL_DIR,
            "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx",
        ),
    )
    LOCAL_DIARIZATION_CLUSTER_THRESHOLD: float = float(
        os.getenv("LOCAL_DIARIZATION_CLUSTER_THRESHOLD", "1.10")
    )
    LOCAL_DIARIZATION_MIN_CLUSTER_DURATION_SECONDS: float = max(
        0.0, float(os.getenv("LOCAL_DIARIZATION_MIN_CLUSTER_DURATION_SECONDS", "5"))
    )
    LOCAL_DIARIZATION_MAX_DETECTED_SPEAKERS: int = max(
        2, int(os.getenv("LOCAL_DIARIZATION_MAX_DETECTED_SPEAKERS", "16"))
    )
    LOCAL_DIARIZATION_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LOCAL_DIARIZATION_TIMEOUT_SECONDS", "900"))
    )
    LOCAL_DIARIZATION_MAX_CONCURRENCY: int = max(
        1, int(os.getenv("LOCAL_DIARIZATION_MAX_CONCURRENCY", "1"))
    )
    # Long roadshows: windowed diarization + global embedding recluster.
    # Full single-pass stays for short files (default <= 12 min).
    LOCAL_DIARIZATION_CHUNK_SECONDS: float = max(
        60.0, float(os.getenv("LOCAL_DIARIZATION_CHUNK_SECONDS", "600"))
    )
    LOCAL_DIARIZATION_CHUNK_OVERLAP_SECONDS: float = max(
        0.0, float(os.getenv("LOCAL_DIARIZATION_CHUNK_OVERLAP_SECONDS", "15"))
    )
    LOCAL_DIARIZATION_FULL_PASS_MAX_SECONDS: float = max(
        60.0, float(os.getenv("LOCAL_DIARIZATION_FULL_PASS_MAX_SECONDS", "720"))
    )
    # Isolate native sherpa crashes from the pipeline process. Job runner already
    # isolates from uvicorn; keep this on for production.
    # Production compose sets this true. Default false so unit tests can inject
    # fakes via _build_local_speaker_diarizer without spawning subprocesses.
    LOCAL_DIARIZATION_ISOLATED_PROCESS: bool = os.getenv(
        "LOCAL_DIARIZATION_ISOLATED_PROCESS", "false"
    ).lower() in {"1", "true", "yes", "on"}

    # 场景约束型人物归属。真实长视频门禁已通过，新部署默认进入正式发布态。
    # 仍可通过环境变量一键回退到影子态，但不得在无配置时静默关闭。
    SPEAKER_ATTRIBUTION_ENABLED: bool = os.getenv(
        "SPEAKER_ATTRIBUTION_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    SPEAKER_ATTRIBUTION_SHADOW_MODE: bool = os.getenv(
        "SPEAKER_ATTRIBUTION_SHADOW_MODE", "false"
    ).lower() in {"1", "true", "yes", "on"}
    SPEAKER_ATTRIBUTION_CONFIRMED_THRESHOLD: float = float(
        os.getenv("SPEAKER_ATTRIBUTION_CONFIRMED_THRESHOLD", "0.85")
    )
    SPEAKER_ATTRIBUTION_PROVISIONAL_THRESHOLD: float = float(
        os.getenv("SPEAKER_ATTRIBUTION_PROVISIONAL_THRESHOLD", "0.70")
    )
    SPEAKER_ATTRIBUTION_MINIMUM_MARGIN: float = float(
        os.getenv("SPEAKER_ATTRIBUTION_MINIMUM_MARGIN", "0.15")
    )

    # 3D-Speaker 本地音视频联合转写归属。发布开关与执行开关分离，
    # 便于故障时只停止公开人物结果，不影响主评分流完成。
    LOCAL_3D_SPEAKER_ENABLED: bool = os.getenv(
        "LOCAL_3D_SPEAKER_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_3D_SPEAKER_REQUIRED: bool = os.getenv(
        "LOCAL_3D_SPEAKER_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    # Independent cutover gate. Installing or running the provider never makes
    # its biometric inference public by itself; production must explicitly
    # enable this only after the real-video accuracy/resource gate passes.
    LOCAL_3D_SPEAKER_PUBLICATION_ENABLED: bool = os.getenv(
        "LOCAL_3D_SPEAKER_PUBLICATION_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_3D_SPEAKER_RUNTIME_DIR: str = os.getenv(
        "LOCAL_3D_SPEAKER_RUNTIME_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models",
            "3d-speaker",
            "runtime",
        ),
    )
    LOCAL_3D_SPEAKER_PYTHON: str = os.getenv(
        "LOCAL_3D_SPEAKER_PYTHON",
        os.path.join(LOCAL_3D_SPEAKER_RUNTIME_DIR, ".venv", "bin", "python"),
    )
    LOCAL_3D_SPEAKER_WORKER: str = os.getenv(
        "LOCAL_3D_SPEAKER_WORKER",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scripts",
            "three_d_speaker_worker.py",
        ),
    )
    LOCAL_3D_SPEAKER_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LOCAL_3D_SPEAKER_TIMEOUT_SECONDS", "2400"))
    )
    LOCAL_3D_SPEAKER_MAX_CONCURRENCY: int = max(
        1, int(os.getenv("LOCAL_3D_SPEAKER_MAX_CONCURRENCY", "1"))
    )

    # 国产 LR-ASD 音视频主动说话检测使用独立 Python 3.11 运行时，
    # 不向主评分环境安装 PyTorch，也不上传视频或依赖对象存储。
    LOCAL_ACTIVE_SPEAKER_ENABLED: bool = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_ACTIVE_SPEAKER_REQUIRED: bool = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_REQUIRED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models",
            "active-speaker",
            "lr-asd-runtime",
        ),
    )
    LOCAL_ACTIVE_SPEAKER_PYTHON: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_PYTHON",
        os.path.join(LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR, ".venv", "bin", "python"),
    )
    LOCAL_ACTIVE_SPEAKER_WORKER: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_WORKER",
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scripts",
            "lr_asd_worker.py",
        ),
    )
    LOCAL_ACTIVE_SPEAKER_REPOSITORY: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_REPOSITORY",
        os.path.join(LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR, "LR-ASD"),
    )
    LOCAL_ACTIVE_SPEAKER_WEIGHT: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_WEIGHT",
        os.path.join(
            LOCAL_ACTIVE_SPEAKER_REPOSITORY, "weight", "pretrain_AVA.model"
        ),
    )
    LOCAL_ACTIVE_SPEAKER_YUNET_MODEL: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_YUNET_MODEL",
        os.path.join(
            LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR,
            "face-models",
            "face_detection_yunet_2023mar.onnx",
        ),
    )
    LOCAL_ACTIVE_SPEAKER_SFACE_MODEL: str = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_SFACE_MODEL",
        os.path.join(
            LOCAL_ACTIVE_SPEAKER_RUNTIME_DIR,
            "face-models",
            "face_recognition_sface_2021dec.onnx",
        ),
    )
    LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS: int = max(
        60, int(os.getenv("LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS", "900"))
    )
    LOCAL_ACTIVE_SPEAKER_MAX_CONCURRENCY: int = max(
        1, int(os.getenv("LOCAL_ACTIVE_SPEAKER_MAX_CONCURRENCY", "1"))
    )
    LOCAL_ACTIVE_SPEAKER_PERSISTENT_WORKERS_ENABLED: bool = os.getenv(
        "LOCAL_ACTIVE_SPEAKER_PERSISTENT_WORKERS_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    LOCAL_ACTIVE_SPEAKER_WORKER_QUEUE_SIZE: int = max(
        1, int(os.getenv("LOCAL_ACTIVE_SPEAKER_WORKER_QUEUE_SIZE", "4"))
    )
    LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_THRESHOLD: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_THRESHOLD", "0.30")
    )
    LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_STABLE_THRESHOLD: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_STABLE_THRESHOLD", "0.45")
    )
    LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_DETECTIONS: int = max(
        1,
        int(
            os.getenv(
                "LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_DETECTIONS", "3"
            )
        ),
    )
    LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_VISIBILITY: float = float(
        os.getenv(
            "LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_VISIBILITY", "0.60"
        )
    )
    LOCAL_ACTIVE_SPEAKER_MIN_ACTIVE_PROBABILITY: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_ACTIVE_PROBABILITY", "0.65")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_VISIBLE_PROBABILITY: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_VISIBLE_PROBABILITY", "0.60")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_TEMPORAL_COVERAGE: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_TEMPORAL_COVERAGE", "0.35")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_WINNER_DOMINANCE: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_WINNER_DOMINANCE", "0.70")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_IDENTITY_CONFIDENCE: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_IDENTITY_CONFIDENCE", "0.40")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_VOTE_DOMINANCE: float = float(
        os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_VOTE_DOMINANCE", "0.70")
    )
    LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS: int = max(
        1,
        int(os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS", "2")),
    )
    LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS: int = max(
        0,
        int(os.getenv("LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS", "3000")),
    )

    # AI 评审团
    AI_JURY_ENABLED: bool = os.getenv("AI_JURY_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    AI_JURY_COUNT: int = int(os.getenv("AI_JURY_COUNT", "9"))
    AI_JURY_MAX_WORKERS: int = int(os.getenv("AI_JURY_MAX_WORKERS", "9"))
    AI_JURY_MEMBER_TIMEOUT_SECONDS: int = int(os.getenv("AI_JURY_MEMBER_TIMEOUT_SECONDS", "180"))
    AI_JURY_MEMBER_RETRIES: int = int(os.getenv("AI_JURY_MEMBER_RETRIES", "1"))
    AI_JURY_PROVIDERS: str = os.getenv("AI_JURY_PROVIDERS", "")
    AI_JURY_PERSONA_API_URL: str = os.getenv("AI_JURY_PERSONA_API_URL", "http://127.0.0.1:8080/api/ai-jury/personas")


settings = Settings()
