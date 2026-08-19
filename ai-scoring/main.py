"""
AI 智能评分微服务 — 入口
基于 FastAPI，提供音频上传、ASR、语音分析、大模型评分的完整 API
"""
import logging
import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.scoring_router import router as scoring_router
from app.routers.chat_router import router as chat_router
from app.routers.ppt_router import router as ppt_router
from app.routers.prep_router import router as prep_router
from app.routers.session_scoring_router import router as session_scoring_router
from app.routers.assistant_router import router as assistant_router
from app.services.ppt.agent_runtime import (
    bootstrap_ppt_agent,
    shutdown_ppt_agent_runtime,
    startup_ppt_agent_runtime,
)

bootstrap_ppt_agent()
from backend.api.websocket import router as ppt_websocket_router  # noqa: E402

# ppt_generator_router 依赖的模块不存在，暂时禁用
# from app.routers.ppt_generator_router import router as ppt_generator_router
ppt_generator_router = None

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="OREP AI 智能评分服务",
    description="在线路演评审平台 — AI 语音分析与内容评分",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 注册路由
app.include_router(scoring_router)
app.include_router(chat_router)
app.include_router(ppt_router)
app.include_router(prep_router)
app.include_router(session_scoring_router)
app.include_router(assistant_router)
app.include_router(ppt_websocket_router, prefix="/api/ppt")
if ppt_generator_router:
    app.include_router(ppt_generator_router)


@app.on_event("startup")
async def startup():
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await startup_ppt_agent_runtime()
    logger.info("=" * 50)
    logger.info("AI 智能评分服务启动")
    logger.info(f"  上传目录: {settings.UPLOAD_DIR}")
    logger.info(f"  DashScope Key: {'已配置' if settings.DASHSCOPE_API_KEY else '未配置'}")
    logger.info(f"  DeepSeek Key: {'已配置' if settings.DEEPSEEK_API_KEY else '未配置'}")
    logger.info(f"  后端回调: {settings.BACKEND_CALLBACK_URL}")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown():
    await shutdown_ppt_agent_runtime()


@app.get("/")
async def root():
    return {
        "service": "OREP AI Services",
        "version": "1.0.0",
        "endpoints": {
            "ai_scoring": {
                "upload_audio": "POST /api/ai/upload-audio",
                "trigger_score": "POST /api/ai/score",
                "get_result": "GET /api/ai/result/{meeting_id}",
                "get_status": "GET /api/ai/status/{meeting_id}",
                "health": "GET /api/ai/health"
            },
            "ai_chat": {
                "chat_create": "POST /api/ai/chat/create",
                "chat_message": "POST /api/ai/chat/{session_id}",
                "chat_health": "GET /api/ai/chat/health"
            },
            "ppt_generation": {
                "health": "GET /api/ppt/health",
                "providers": "GET /api/ppt/providers",
                "templates": "GET /api/ppt/templates",
                "upload": "POST /api/ppt/upload",
                "generate": "POST /api/ppt/generate",
                "status": "GET /api/ppt/status/{job_id}",
                "websocket": "WS /api/ppt/ws/{job_id}",
                "preview": "GET /api/ppt/preview/{job_id}",
                "critic": "GET /api/ppt/critic/{job_id}",
                "download": "GET /api/ppt/download/{job_id}",
                "reexport": "POST /api/ppt/download/{job_id}/reexport",
                "image_search": "POST /api/ppt/image-search/{job_id}"
            },
            "project_prep": {
                "topic_planning": "POST /api/prep/topic-planning/analyze",
                "health": "GET /api/prep/health"
            },
            "assistant": {
                "run": "POST /api/assistant/v1/runs",
                "health": "GET /api/assistant/health"
            },
            "docs": "GET /docs"
        }
    }


if __name__ == "__main__":
    reload_enabled = os.getenv("AI_SERVICE_RELOAD", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload_enabled,
        # Generated PPT workspaces include source-code samples such as .py
        # files. Watching the whole service directory makes those artifacts
        # look like application source changes and cancels active jobs.
        reload_dirs=[str(Path(__file__).resolve().parent / "app")] if reload_enabled else None,
    )
