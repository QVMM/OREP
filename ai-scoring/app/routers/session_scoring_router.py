import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.services.session_pipeline_service import run_session_pipeline
from app.services.scoring.track_binding import (
    TrackConfirmationRequired,
    validate_competition_binding,
)
from app.services.media_evidence.speaker_attribution_recompute import (
    SpeakerAttributionRecomputeError,
    recompute_final_speaker_attribution,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["session-scoring"])


class SessionScoringRequest(BaseModel):
    sessionId: int
    sessionNo: str
    teamId: Optional[int] = None
    projectId: Optional[int] = None
    trackName: Optional[str] = None
    trackId: Optional[str] = None
    competitionBinding: Optional[dict] = None
    publishOfficialScore: bool = True
    juryEnabled: bool = False
    sourceType: str = "uploaded_video"
    videoFilePath: str
    videoOriginalName: Optional[str] = None
    materials: list[dict] = []
    callbackUrl: str
    videoSha256: Optional[str] = None
    forceRetranscribe: bool = False


class SessionScoringResponse(BaseModel):
    accepted: bool
    message: str
    taskId: Optional[str] = None


class RecomputeSpeakerAttributionRequest(BaseModel):
    contestantSlots: Optional[int] = Field(
        default=None,
        description="Optional override for expected contestant count (0-4)",
    )


@router.post("/score-session", response_model=SessionScoringResponse)
async def score_session(request: SessionScoringRequest, background_tasks: BackgroundTasks):
    logger.info(f"Session scoring: sessionId={request.sessionId}, track={request.trackName}")
    binding_input = dict(request.competitionBinding or {})
    binding_input.setdefault("trackId", request.trackId)
    binding_input.setdefault("trackName", request.trackName)
    try:
        competition_binding = validate_competition_binding(
            binding_input,
            publish_official_score=request.publishOfficialScore,
        )
    except TrackConfirmationRequired:
        logger.warning(
            "Session scoring rejected: sessionId=%s reason=track_confirmation_required",
            request.sessionId,
        )
        return SessionScoringResponse(
            accepted=False,
            message="track_confirmation_required",
            taskId=None,
        )
    background_tasks.add_task(
        run_session_pipeline,
        session_id=request.sessionId,
        session_no=request.sessionNo,
        team_id=request.teamId,
        project_id=request.projectId,
        track_name=competition_binding.get("trackName") or request.trackName,
        competition_binding=competition_binding,
        publish_official_score=request.publishOfficialScore,
        jury_enabled=request.juryEnabled,
        source_type=request.sourceType,
        video_file_path=request.videoFilePath,
        video_original_name=request.videoOriginalName,
        materials=request.materials,
        callback_url=request.callbackUrl,
        video_sha256=request.videoSha256,
        force_retranscribe=bool(request.forceRetranscribe),
    )
    return SessionScoringResponse(
        accepted=True,
        message=f"Pipeline started for session {request.sessionId}",
        taskId=f"session-{request.sessionId}",
    )


@router.post("/score-session/{session_id}/recompute-speaker-attribution")
async def recompute_speaker_attribution(
    session_id: int,
    request: Optional[RecomputeSpeakerAttributionRequest] = None,
):
    """Rebuild FINAL speaker attribution from stored ASR/cluster evidence.

    Does not re-run scoring or 3D-Speaker. Returns a new revision snapshot for
    the Java backend to persist into the report transcript.
    """
    body = request or RecomputeSpeakerAttributionRequest()
    logger.info(
        "Recompute speaker attribution: sessionId=%s contestantSlots=%s",
        session_id,
        body.contestantSlots,
    )
    try:
        receipt = recompute_final_speaker_attribution(
            str(session_id),
            contestant_slots=body.contestantSlots,
        )
    except SpeakerAttributionRecomputeError as exc:
        logger.warning(
            "Recompute speaker attribution rejected: sessionId=%s code=%s msg=%s",
            session_id,
            exc.code,
            exc.message,
        )
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        logger.exception(
            "Recompute speaker attribution failed: sessionId=%s", session_id
        )
        raise HTTPException(
            status_code=500,
            detail={"code": "RECOMPUTE_FAILED", "message": str(exc)},
        ) from exc

    snapshot = receipt.get("snapshot") or {}
    return {
        "accepted": True,
        "sessionId": session_id,
        "revision": receipt.get("revision"),
        "snapshotHash": receipt.get("snapshotHash"),
        "status": snapshot.get("status") or receipt.get("status"),
        "contestantCount": receipt.get("contestantCount"),
        "personCount": receipt.get("personCount"),
        "segmentCount": receipt.get("segmentCount"),
        "evidenceSource": receipt.get("evidenceSource"),
        "turnSource": receipt.get("turnSource"),
        "speakerAttribution": snapshot,
    }
