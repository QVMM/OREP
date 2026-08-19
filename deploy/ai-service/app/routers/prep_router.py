"""
Project preparation topic planning API.
"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.prep_topic_planning_service import PrepTopicPlanningService

router = APIRouter(prefix="/api/prep", tags=["项目准备"])
prep_service = PrepTopicPlanningService()


class TopicPlanningRequest(BaseModel):
    sessionId: int | None = None
    teamId: int | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    latestUserMessage: str = ""


@router.post("/topic-planning/analyze")
async def analyze_topic_planning(req: TopicPlanningRequest):
    return prep_service.analyze(req.model_dump())


@router.get("/health")
async def health():
    return prep_service.health()
