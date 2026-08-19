"""
路演复盘问答 API 路由
"""
import json
import logging
import os
import tempfile
import subprocess
import uuid
from fastapi import APIRouter, HTTPException

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/chat", tags=["路演复盘问答"])

# 全局服务实例
chat_service = ChatService()

class CreateSessionRequest(BaseModel):
    meeting_id: str
    project_name: str = ""
    track: str = ""
    team_size: int = 4

class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class CreateSessionResponse(BaseModel):
    session_id: str
    welcome_message: str
    suggestions: list[str]

class ChatResponse(BaseModel):
    response: str
    model: str
    suggestions: list[str]
    remaining: int

@router.post("/create", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    """创建复盘问答会话"""
    try:
        result = chat_service.create_session(
            meeting_id=req.meeting_id,
            project_name=req.project_name,
            track=req.track,
            team_size=req.team_size,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}")
async def chat(session_id: str, req: ChatRequest):
    """发送消息（支持 SSE 流式）"""
    try:
        if req.stream:
            # SSE 流式响应
            generator = chat_service.chat(session_id, req.message, stream=True)
            return StreamingResponse(
                generator,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                }
            )
        else:
            result = chat_service.chat(session_id, req.message, stream=False)
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if chat_service.delete_session(session_id):
        return {"status": "ok", "message": "会话已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")

@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "chat"}
