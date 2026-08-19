"""
AI 评分 API 路由
"""
import os

_cert_candidates = ["/etc/ssl/cert.pem"]
try:
    import certifi
    _cert_candidates.append(certifi.where())
except Exception:
    pass

for _cert_path in _cert_candidates:
    if _cert_path and os.path.exists(_cert_path):
        os.environ.setdefault("SSL_CERT_FILE", _cert_path)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", _cert_path)
        break

import json
import logging
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

from app.config import settings
from app.services import audio_service, coaching_service, pipeline_service, report_service
from app.services.jury.evidence_service import build_system_evidence_summary
from app.services.jury import persona_repository
from app.services.jury import report_service as jury_report_service
from app.services.jury import scoring_service as jury_scoring_service
from app.services.llm_scoring_service import _sanitize_competition_duration
from app.services.media_evidence.realtime_gateway import (
    AudioChunkRejected,
    RealtimeAudioProtocol,
    get_audio_chunk_journal,
    select_transport_mode,
)
from app.services.media_evidence.live_finalizer import finalize_live_evidence
from app.services.media_evidence.live_camera_subscriber import (
    LiveCameraSubscriberError,
    build_livekit_subscriber_token,
    live_camera_runtime_registry,
)
from app.services.media_evidence.shadow_store import save_live_evidence_package

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI评分"])
PROGRESS_STALE_SECONDS = 6 * 60 * 60


class ScoringRequest(BaseModel):
    """手动触发评分请求"""
    meeting_id: str
    project_name: str = "未命名项目"
    track: str = "未指定赛道"
    team_size: int = 4
    callback_url: Optional[str] = None
    provider: str = "deepseek"  # 评分通道固定使用 deepseek
    compare_mode: bool = False  # 兼容旧参数；MiniMax 对比通道已停用


class ScoringResponse(BaseModel):
    """评分响应"""
    meeting_id: str
    status: str
    message: str = ""
    session_id: Optional[str] = None


class ScoringSessionStartRequest(BaseModel):
    """AI 评分会话启动请求"""
    meeting_id: str
    has_audio: bool = False
    has_video: bool = False


class ScoringSessionFinishRequest(BaseModel):
    """AI 评分会话结束请求"""
    status: str = "finished"
    error_message: Optional[str] = None


class CoachingRefreshRequest(BaseModel):
    refresh: bool = False
    provider: str = "deepseek"


class JuryStartRequest(BaseModel):
    refresh: bool = True
    provider: str = "deepseek"
    ppt_recognition: bool = False
    roadshow_memory: Optional[dict] = None
    dispute_review_context: Optional[dict] = None


class JuryPersonaUpdateRequest(BaseModel):
    name: Optional[str] = None
    short_label: Optional[str] = None
    prompt_modifier: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    judge_profile: Optional[dict] = None
    rubric_focus: Optional[dict] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _is_progress_fresh(progress: dict) -> bool:
    updated_at = _parse_datetime(progress.get("updated_at") or progress.get("progress_updated_at"))
    if not updated_at:
        return False
    return (datetime.now(timezone.utc) - updated_at).total_seconds() <= PROGRESS_STALE_SECONDS


def _sanitize_result_payload(result: dict) -> dict:
    duration = (
        result.get("audio_info", {}).get("duration")
        or result.get("asr", {}).get("duration")
        or 0
    )
    if "ai_score" in result:
        result["ai_score"] = _sanitize_competition_duration(result.get("ai_score", {}), duration)
    return result


def _session_dir() -> str:
    path = os.path.join(settings.UPLOAD_DIR, "sessions")
    os.makedirs(path, exist_ok=True)
    return path


def _session_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"session_{session_id}.json")


def _transcript_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"transcript_{session_id}.jsonl")


def _visual_frames_dir(session_id: str) -> str:
    path = os.path.join(_session_dir(), f"frames_{session_id}")
    os.makedirs(path, exist_ok=True)
    return path


def _visual_frames_index_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"frames_{session_id}.jsonl")


def _live_camera_frames_index_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"live_camera_frames_{session_id}.jsonl")


def _meeting_session_index_path(meeting_id: str) -> str:
    return os.path.join(_session_dir(), f"latest_meeting_{meeting_id}.json")


def _write_session(session: dict):
    session["updated_at"] = _utc_now()
    path = _session_path(session["session_id"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)

    with open(_meeting_session_index_path(session["meeting_id"]), "w", encoding="utf-8") as f:
        json.dump({
            "meeting_id": session["meeting_id"],
            "session_id": session["session_id"],
            "updated_at": session["updated_at"]
        }, f, ensure_ascii=False, indent=2)


def _read_session(session_id: str) -> dict:
    path = _session_path(session_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"评分会话 {session_id} 不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _append_transcript_event(session_id: str, event: dict):
    event["session_id"] = session_id
    event["received_at"] = _utc_now()
    with open(_transcript_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_transcript_events(session_id: str) -> list[dict]:
    path = _transcript_path(session_id)
    if not os.path.exists(path):
        return []

    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"转写事件解析失败: {line[:120]}")
    return events


def _append_visual_frame_event(session_id: str, event: dict):
    event["session_id"] = session_id
    event["received_at"] = _utc_now()
    with open(_visual_frames_index_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_visual_frame_events(session_id: str) -> list[dict]:
    path = _visual_frames_index_path(session_id)
    if not os.path.exists(path):
        return []

    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"视频帧索引解析失败: {line[:120]}")
    return events


def _append_live_camera_frame_event(session_id: str, frame: dict) -> None:
    """Persist timing/audit metadata only; raw live frames remain in local memory."""

    observed_audio_sample = None
    sample_rate = 16_000
    try:
        clock_snapshot = get_audio_chunk_journal(
            _session_dir(), session_id
        ).media_clock_snapshot
        if (
            isinstance(clock_snapshot, dict)
            and clock_snapshot.get("clockId") == frame.get("clockId")
            and isinstance(clock_snapshot.get("nextSample"), int)
            and not isinstance(clock_snapshot.get("nextSample"), bool)
        ):
            observed_audio_sample = max(0, int(clock_snapshot["nextSample"]))
            configured_rate = clock_snapshot.get("sampleRate")
            if isinstance(configured_rate, int) and configured_rate > 0:
                sample_rate = configured_rate
    except Exception:
        # The live camera path may start before the first PCM clock handshake.
        # Raw PTS is retained and sync becomes UNAVAILABLE rather than guessed.
        pass
    fallback_timestamp = max(0.0, float(frame.get("mappedPtsMs") or 0) / 1000)
    timestamp = (
        observed_audio_sample / sample_rate
        if observed_audio_sample is not None
        else fallback_timestamp
    )
    event = {
        "session_id": session_id,
        "frame_id": uuid.uuid4().hex,
        "timestamp": timestamp,
        "frame_type": (
            "live_camera_key" if frame.get("isKeyFrame") else "live_camera_sample"
        ),
        "clock_id": frame.get("clockId"),
        "raw_pts": frame.get("rawPts"),
        "pts_timebase_num": frame.get("ptsTimebaseNum"),
        "pts_timebase_den": frame.get("ptsTimebaseDen"),
        "observed_audio_sample": observed_audio_sample,
        "track_id": frame.get("trackId"),
        "source": "livekit_camera",
        "analysis_status": "shadow_queued",
        "received_at": _utc_now(),
    }
    with open(_live_camera_frames_index_path(session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_live_camera_frame_events(session_id: str) -> list[dict]:
    path = _live_camera_frames_index_path(session_id)
    if not os.path.exists(path):
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                if line.strip():
                    events.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("实时摄像头帧索引解析失败: %s", line[:120])
    return events


async def _persist_live_camera_frame_metadata(session_id: str, frame: dict) -> None:
    await asyncio.to_thread(_append_live_camera_frame_event, session_id, frame)


def _finalize_live_evidence_if_enabled(session: dict) -> dict | None:
    """Freeze v2 live facts without changing meeting or official score terminal state."""

    if not settings.UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED:
        return None
    if session.get("transcript_protocol") != RealtimeAudioProtocol.PROTOCOL:
        return None

    session_id = str(session.get("session_id") or "")
    try:
        journal = get_audio_chunk_journal(_session_dir(), session_id)
        gateway_summary = journal.finalize()
        package = finalize_live_evidence(
            session_id=session_id,
            transcript_events=_read_transcript_events(session_id),
            visual_frames=(
                _read_visual_frame_events(session_id)
                + _read_live_camera_frame_events(session_id)
            ),
            gateway_summary=gateway_summary,
            processing_metrics={
                "provider": "dashscope",
                "model": "fun-asr-realtime-2026-02-28",
            },
        )
        path = save_live_evidence_package(settings.UPLOAD_DIR, session_id, package)
        session["evidence_status"] = "final"
        session["evidence_snapshot_hash"] = package.get("snapshotHash")
        session["evidence_snapshot_path"] = path
        session.pop("evidence_error_code", None)
        return package
    except Exception as error:
        logger.warning("[ASR:%s] 会后证据冻结失败: %s", session_id, error)
        session["evidence_status"] = "evidence_failed"
        session["evidence_error_code"] = "LIVE_EVIDENCE_FINALIZE_FAILED"
        return None


def _latest_session_for_meeting(meeting_id: str) -> Optional[dict]:
    index_path = _meeting_session_index_path(meeting_id)
    if not os.path.exists(index_path):
        return None
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    session_id = index.get("session_id")
    if not session_id:
        return None
    try:
        return _read_session(session_id)
    except HTTPException:
        return None


def _safe_frame_event(session_id: str, frame: dict) -> dict:
    return {
        "frame_id": frame.get("frame_id"),
        "timestamp": frame.get("timestamp"),
        "frame_type": frame.get("frame_type"),
        "diff_score": frame.get("diff_score"),
        "analysis_status": frame.get("analysis_status"),
        "received_at": frame.get("received_at"),
        "clock_id": frame.get("clock_id"),
        "raw_pts": frame.get("raw_pts"),
        "pts_timebase_num": frame.get("pts_timebase_num"),
        "pts_timebase_den": frame.get("pts_timebase_den"),
        "observed_audio_sample": frame.get("observed_audio_sample"),
        "image_url": f"/api/ai/session/{session_id}/visual-frame/{frame.get('frame_id')}"
    }


def _resolve_visual_frame_image_path(session_id: str, frame: dict) -> Optional[str]:
    frame_dir = os.path.abspath(_visual_frames_dir(session_id))

    file_name = os.path.basename(str(frame.get("file_name") or ""))
    if file_name:
        candidate = os.path.abspath(os.path.join(frame_dir, file_name))
        if candidate.startswith(frame_dir + os.sep) and os.path.exists(candidate):
            return candidate

    image_path = os.path.abspath(frame.get("image_path") or "")
    if image_path.startswith(frame_dir + os.sep) and os.path.exists(image_path):
        return image_path

    legacy_name = os.path.basename(image_path)
    if legacy_name:
        candidate = os.path.abspath(os.path.join(frame_dir, legacy_name))
        if candidate.startswith(frame_dir + os.sep) and os.path.exists(candidate):
            return candidate

    return None


class SessionRecognitionCallback(RecognitionCallback):
    """DashScope 实时 ASR 回调：把 final/interim 结果落到 session transcript 文件。"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.error_message = ""
        self.closed = False
        self._segment_revisions: dict[str, int] = {}
        self._finalized_segments: set[str] = set()

    def on_open(self) -> None:
        logger.info(f"[ASR:{self.session_id}] WebSocket opened")
        _append_transcript_event(self.session_id, {"type": "asr_open"})

    def on_close(self) -> None:
        logger.info(f"[ASR:{self.session_id}] WebSocket closed")
        self.closed = True
        _append_transcript_event(self.session_id, {"type": "asr_close"})

    def on_complete(self) -> None:
        logger.info(f"[ASR:{self.session_id}] Recognition completed")
        _append_transcript_event(self.session_id, {"type": "asr_complete"})

    def on_error(self, result: RecognitionResult) -> None:
        message = getattr(result, "message", "") or ""
        request_id = getattr(result, "request_id", "") or ""
        logger.error(f"[ASR:{self.session_id}] Recognition error: {message}")
        self.error_message = message
        _append_transcript_event(self.session_id, {
            "type": "asr_error",
            "request_id": request_id,
            "message": message
        })

    def on_event(self, result: RecognitionResult) -> None:
        try:
            sentence = result.get_sentence() or {}
            text = sentence.get("text", "")
            if not text:
                return

            is_final = RecognitionResult.is_sentence_end(sentence)
            request_id = str(result.get_request_id() or "unknown")
            sentence_key = sentence.get("sentence_id")
            if sentence_key is None:
                sentence_key = sentence.get("begin_time", 0)
            segment_id = f"{request_id}:{sentence_key}"
            if segment_id in self._finalized_segments:
                return
            revision = self._segment_revisions.get(segment_id, 0) + 1
            self._segment_revisions[segment_id] = revision
            if is_final:
                self._finalized_segments.add(segment_id)
            _append_transcript_event(self.session_id, {
                "type": "transcript",
                "segmentId": segment_id,
                "revision": revision,
                "state": "FINAL" if is_final else "PROVISIONAL",
                "observedAtMs": int(datetime.now(timezone.utc).timestamp() * 1000),
                "text": text,
                "is_final": is_final,
                "start": sentence.get("begin_time", 0) / 1000,
                "end": sentence.get("end_time", 0) / 1000,
                "words": sentence.get("words", []),
                "request_id": request_id,
                "usage": result.get_usage(sentence) if is_final else None,
                "source": "realtime"
            })
        except Exception as e:
            logger.warning(f"[ASR:{self.session_id}] 处理实时转写事件失败: {e}")


def _session_with_pipeline_status(session: dict) -> dict:
    """把旧评分流水线的进度叠加到 session 状态上，兼容现有报告链路。"""
    data = dict(session)
    meeting_id = data.get("meeting_id")
    session_id = data.get("session_id")

    if session_id:
        live_camera_status = live_camera_runtime_registry.status(session_id)
        if live_camera_status is not None:
            data["live_camera_subscriber"] = live_camera_status
        transcript_events = _read_transcript_events(session_id)
        final_transcripts = [
            event for event in transcript_events
            if event.get("type") == "transcript" and event.get("is_final")
        ]
        visual_frames = _read_visual_frame_events(session_id)
        live_camera_frames = _read_live_camera_frame_events(session_id)
        data["observability"] = {
            "transcript_event_count": len(transcript_events),
            "transcript_final_count": len(final_transcripts),
            "transcript_text_chars": sum(len(event.get("text", "")) for event in final_transcripts),
            "visual_frame_count": len(visual_frames),
            "live_camera_sample_count": len(live_camera_frames),
            "visual_scene_change_count": len([
                frame for frame in visual_frames
                if frame.get("frame_type") == "scene_change"
            ]),
            "asr_chunks": data.get("transcript_chunks", 0),
            "asr_bytes": data.get("transcript_bytes", 0),
        }

    if not meeting_id:
        return data

    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")
    if os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        result_status = result.get("status", "unknown")
        data["final_score_status"] = "processing" if result_status == "generating_report" else result_status
        data["current_step"] = "report" if result_status == "generating_report" else "completed"
        data["step_label"] = "生成PDF报告中..." if result_status == "generating_report" else "已完成"
        data["progress_percent"] = 92 if result_status == "generating_report" else 100
        data["report_url"] = f"/api/ai/report/{meeting_id}"
        data["completed_at"] = result.get("completed_at")
        data["elapsed_seconds"] = result.get("elapsed_seconds")
        data["total_elapsed_seconds"] = result.get("total_elapsed_seconds")
        data["asr_source"] = result.get("asr", {}).get("source")
        data["video_source"] = result.get("video_analysis", {}).get("source")
        if result_status == "failed":
            data["error_message"] = result.get("error") or data.get("error_message")
        return data

    progress_path = os.path.join(settings.UPLOAD_DIR, "results", f"progress_{meeting_id}.json")
    if os.path.exists(progress_path):
        with open(progress_path, "r", encoding="utf-8") as f:
            progress = json.load(f)
        if not _is_progress_fresh(progress):
            return data
        data["final_score_status"] = "processing"
        data["current_step"] = progress.get("step", "asr")
        data["step_label"] = progress.get("label", "")
        data["step_num"] = progress.get("step_num", 0)
        data["total_steps"] = progress.get("total_steps", 0)
        data["progress_percent"] = progress.get("progress_percent", 0)
        data["progress_updated_at"] = progress.get("updated_at")

    return data


@router.post("/session/start")
async def start_scoring_session(request: ScoringSessionStartRequest):
    """创建 AI 评分会话。后续实时转写、截图、完整录制都挂在该会话下。"""
    if not request.meeting_id:
        raise HTTPException(status_code=400, detail="meeting_id 不能为空")
    if not request.has_audio or not request.has_video:
        raise HTTPException(status_code=400, detail="开启 AI 评分前必须存在有效音频和视频")

    session_id = uuid.uuid4().hex
    media_clock_id = f"session-{session_id}-{uuid.uuid4().hex[:12]}"
    session = {
        "session_id": session_id,
        "meeting_id": str(request.meeting_id),
        "status": "recording",
        "has_audio": request.has_audio,
        "has_video": request.has_video,
        "media_clock_id": media_clock_id,
        "media_clock_master": "AUDIO_SAMPLE_CLOCK",
        "transcript_status": "pending",
        "visual_status": "pending",
        "recording_status": "recording",
        "final_score_status": "pending",
        "started_at": _utc_now(),
        "ended_at": None,
        "error_message": None,
        "live_camera_subscriber": {
            "state": "DISABLED",
            "clockId": media_clock_id,
            "audioMayContinue": True,
        },
    }
    if settings.LIVE_CAMERA_SUBSCRIBER_ENABLED:
        try:
            token = build_livekit_subscriber_token(
                api_key=settings.LIVEKIT_API_KEY,
                api_secret=settings.LIVEKIT_API_SECRET,
                room_name=str(request.meeting_id),
                session_id=session_id,
            )
            session["live_camera_subscriber"] = await live_camera_runtime_registry.start(
                session_id=session_id,
                room_name=str(request.meeting_id),
                clock_id=media_clock_id,
                url=settings.LIVEKIT_INTERNAL_WS_URL,
                token=token,
                target_fps=settings.LIVE_CAMERA_TARGET_FPS,
                max_backlog_ms=settings.LIVE_CAMERA_MAX_BACKLOG_MS,
                max_queue_frames=settings.LIVE_CAMERA_MAX_QUEUE_FRAMES,
                jpeg_max_width=settings.LIVE_CAMERA_JPEG_MAX_WIDTH,
                jpeg_quality=settings.LIVE_CAMERA_JPEG_QUALITY,
                frame_sink=lambda frame: _persist_live_camera_frame_metadata(
                    session_id, frame
                ),
            )
        except (LiveCameraSubscriberError, ValueError, OSError) as error:
            logger.warning("[CAMERA:%s] 影子订阅未启动: %s", session_id, error)
            session["live_camera_subscriber"] = {
                "state": "AUDIO_ONLY",
                "clockId": media_clock_id,
                "integrityStatus": "DEGRADED",
                "degradationReason": str(error),
                "audioMayContinue": True,
            }
    _write_session(session)
    return session


@router.post("/session/{session_id}/finish")
async def finish_scoring_session(session_id: str, request: ScoringSessionFinishRequest):
    """结束 AI 评分会话。完整文件上传和评分任务可以在结束后继续异步运行。"""
    session = _read_session(session_id)
    session["status"] = request.status
    session["recording_status"] = "finished" if request.status == "finished" else request.status
    session["ended_at"] = _utc_now()
    if request.error_message:
        session["error_message"] = request.error_message
    live_camera_summary = await live_camera_runtime_registry.stop(session_id)
    if live_camera_summary is not None:
        session["live_camera_subscriber"] = live_camera_summary
    if request.status == "finished":
        _finalize_live_evidence_if_enabled(session)
    _write_session(session)
    return session


@router.get("/session/{session_id}/status")
async def get_scoring_session_status(session_id: str):
    """查询 AI 评分会话状态。"""
    return _session_with_pipeline_status(_read_session(session_id))


@router.get("/session/{session_id}/transcript")
async def get_scoring_session_transcript(session_id: str):
    """读取 AI 评分会话的实时转写结果。"""
    _read_session(session_id)
    events = _read_transcript_events(session_id)
    final_segments = [
        {
            "text": event.get("text", ""),
            "start": event.get("start", 0),
            "end": event.get("end", 0),
            "words": event.get("words", []),
            "source": event.get("source", "realtime")
        }
        for event in events
        if event.get("type") == "transcript" and event.get("is_final")
    ]

    return {
        "session_id": session_id,
        "segments": final_segments,
        "transcript": " ".join(seg["text"] for seg in final_segments),
        "event_count": len(events)
    }


@router.post("/session/{session_id}/visual-frame")
async def upload_visual_frame(
    session_id: str,
    frame: UploadFile = File(...),
    timestamp: float = Form(0),
    frame_type: str = Form("interval"),
    diff_score: float = Form(0),
    clock_id: Optional[str] = Form(None),
    raw_pts: Optional[int] = Form(None),
    pts_timebase_num: Optional[int] = Form(None),
    pts_timebase_den: Optional[int] = Form(None),
    observed_audio_sample: Optional[int] = Form(None),
):
    """上传 AI 评分会话中的视频关键帧。"""
    _read_session(session_id)
    if not frame.filename:
        raise HTTPException(status_code=400, detail="未上传视频帧")

    ext = os.path.splitext(frame.filename)[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail=f"不支持的视频帧格式: {ext}")

    frame_id = uuid.uuid4().hex
    file_name = f"frame_{int(timestamp * 1000):012d}_{frame_type}_{frame_id}{ext}"
    frame_path = os.path.join(_visual_frames_dir(session_id), file_name)
    with open(frame_path, "wb") as f:
        f.write(await frame.read())

    event = {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "frame_type": frame_type,
        "diff_score": diff_score,
        "clock_id": clock_id,
        "raw_pts": raw_pts,
        "pts_timebase_num": pts_timebase_num,
        "pts_timebase_den": pts_timebase_den,
        "observed_audio_sample": observed_audio_sample,
        "image_path": frame_path,
        "file_name": file_name,
        "analysis_status": "pending"
    }
    _append_visual_frame_event(session_id, event)

    session = _read_session(session_id)
    session["visual_status"] = "capturing" if session.get("status") == "recording" else "captured"
    session["visual_frame_count"] = int(session.get("visual_frame_count") or 0) + 1
    _write_session(session)

    return event


@router.get("/session/{session_id}/visual-frames")
async def get_visual_frames(session_id: str):
    """读取 AI 评分会话视频关键帧索引。"""
    _read_session(session_id)
    frames = _read_visual_frame_events(session_id)
    return {
        "session_id": session_id,
        "frame_count": len(frames),
        "frames": [_safe_frame_event(session_id, frame) for frame in frames]
    }


@router.get("/meeting/{meeting_id}/visual-frames")
async def get_meeting_visual_frames(meeting_id: str):
    """读取某个会议最近一次 AI 评分会话的视频关键帧。"""
    session = _latest_session_for_meeting(meeting_id)
    if not session:
        return {
            "meeting_id": meeting_id,
            "session_id": None,
            "frame_count": 0,
            "frames": []
        }

    session_id = session["session_id"]
    frames = _read_visual_frame_events(session_id)
    return {
        "meeting_id": meeting_id,
        "session_id": session_id,
        "frame_count": len(frames),
        "frames": [_safe_frame_event(session_id, frame) for frame in frames]
    }


@router.get("/session/{session_id}/visual-frame/{frame_id}")
async def get_visual_frame_image(session_id: str, frame_id: str):
    """读取 AI 评分会话中的单张视频关键帧图片。"""
    _read_session(session_id)
    frame = next(
        (item for item in _read_visual_frame_events(session_id) if item.get("frame_id") == frame_id),
        None
    )
    if not frame:
        raise HTTPException(status_code=404, detail="视频帧不存在")

    image_path = _resolve_visual_frame_image_path(session_id, frame)
    if not image_path:
        raise HTTPException(status_code=404, detail="视频帧图片不存在")

    ext = os.path.splitext(image_path)[1].lower()
    media_type = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }.get(ext, "application/octet-stream")
    return FileResponse(image_path, media_type=media_type)


@router.websocket("/asr/stream/{session_id}")
async def realtime_asr_stream(websocket: WebSocket, session_id: str):
    """接收浏览器 PCM 音频流并转发 DashScope 实时 ASR。"""
    await websocket.accept()

    try:
        session = _read_session(session_id)
    except HTTPException:
        await websocket.send_json({"type": "error", "message": "评分会话不存在"})
        await websocket.close(code=1008)
        return

    try:
        transport_mode = select_transport_mode(
            settings.UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED,
            websocket.query_params.get("protocol"),
        )
    except AudioChunkRejected as error:
        await websocket.send_json(
            {"type": "error", "code": error.code, "message": str(error)}
        )
        await websocket.close(code=1008)
        return

    if not settings.DASHSCOPE_API_KEY:
        await websocket.send_json({"type": "error", "message": "DASHSCOPE_API_KEY 未配置"})
        session["transcript_status"] = "failed"
        session["error_message"] = "DASHSCOPE_API_KEY 未配置"
        _write_session(session)
        await websocket.close(code=1011)
        return

    dashscope.api_key = settings.DASHSCOPE_API_KEY
    dashscope.base_websocket_api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    callback = SessionRecognitionCallback(session_id)
    recognition = Recognition(
        model="fun-asr-realtime-2026-02-28",
        format="pcm",
        sample_rate=16000,
        semantic_punctuation_enabled=True,
        callback=callback
    )

    chunk_count = 0
    received_bytes = 0
    explicit_stop = False
    protocol_error = None
    v2_protocol = None
    if transport_mode == RealtimeAudioProtocol.PROTOCOL:
        journal = get_audio_chunk_journal(_session_dir(), session_id)
        v2_protocol = RealtimeAudioProtocol(journal, recognition.send_audio_frame)
    session["transcript_status"] = "streaming"
    session["transcript_protocol"] = transport_mode
    _write_session(session)

    try:
        recognition.start()
        if transport_mode == "legacy_raw":
            await websocket.send_json({"type": "ready", "session_id": session_id, "sample_rate": 16000})

        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            text = message.get("text")
            if text:
                try:
                    payload = json.loads(text)
                    if v2_protocol is not None:
                        response = v2_protocol.handle_control(payload)
                        await websocket.send_json(response)
                        if response.get("type") == "finalized":
                            explicit_stop = True
                            session["audio_gateway_summary"] = response.get("summary")
                            break
                    elif payload.get("type") == "stop":
                        explicit_stop = True
                        break
                except json.JSONDecodeError:
                    if v2_protocol is not None:
                        raise AudioChunkRejected(
                            "INVALID_CONTROL_MESSAGE", "control message is not valid JSON"
                        )
                continue

            data = message.get("bytes")
            if not data:
                continue

            if callback.error_message:
                await websocket.send_json({"type": "error", "message": callback.error_message})
                break

            if v2_protocol is not None:
                receipt = v2_protocol.handle_binary(data)
                if receipt.get("status") == "accepted":
                    chunk_count += 1
                    received_bytes += len(data)
                await websocket.send_json(receipt)
            else:
                recognition.send_audio_frame(data)
                chunk_count += 1
                received_bytes += len(data)
            if v2_protocol is None and chunk_count % 50 == 0:
                await websocket.send_json({
                    "type": "ack",
                    "chunks": chunk_count,
                    "received_bytes": received_bytes
                })

    except AudioChunkRejected as error:
        protocol_error = error.code
        logger.warning("[ASR:%s] 实时音频协议拒绝: %s %s", session_id, error.code, error)
        try:
            await websocket.send_json(
                {"type": "error", "code": error.code, "message": str(error)}
            )
        except Exception:
            pass
    except WebSocketDisconnect:
        logger.info(f"[ASR:{session_id}] 前端 WebSocket 已断开")
    except Exception as e:
        logger.exception(f"[ASR:{session_id}] 实时转写失败")
        session = _read_session(session_id)
        session["transcript_status"] = "failed"
        session["error_message"] = str(e)
        _write_session(session)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if v2_protocol is not None:
            v2_protocol.close_transport()
        try:
            recognition.stop()
        except Exception as e:
            logger.warning(f"[ASR:{session_id}] 停止 DashScope 实时识别失败: {e}")

        session = _read_session(session_id)
        if session.get("transcript_status") != "failed":
            if v2_protocol is not None and not explicit_stop:
                session["transcript_status"] = "stream_interrupted"
            else:
                session["transcript_status"] = "completed"
        if protocol_error:
            session["transcript_protocol_error"] = protocol_error
        session["transcript_chunks"] = chunk_count
        session["transcript_bytes"] = received_bytes
        _write_session(session)

        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/session/latest/{meeting_id}")
async def get_latest_scoring_session(meeting_id: str):
    """查询某个会议最近一次 AI 评分会话。"""
    session = _latest_session_for_meeting(meeting_id)
    if not session:
        return {
            "meeting_id": meeting_id,
            "session_id": None,
            "status": "empty",
            "detail": f"会议 {meeting_id} 暂无 AI 评分会话",
        }
    return _session_with_pipeline_status(session)


def _parse_team_roster(team_roster: Optional[str]) -> Optional[list]:
    if not team_roster:
        return None
    try:
        parsed = json.loads(team_roster)
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        logger.warning("team_roster JSON 无效，已忽略")
        return None


def _uploaded_media_has_video(extension: str, declared_has_video: Optional[bool]) -> bool:
    """Resolve the real browser recording shape without guessing from WebM alone.

    WebM is used by browsers for both audio-only and audio+video MediaRecorder output,
    so its extension cannot decide whether the joint speaker model receives pictures.
    The recorder already knows whether it attached a video track and sends that fact.
    """
    if declared_has_video is not None:
        return bool(declared_has_video)
    return extension.lower() in {'.mp4', '.mkv', '.avi', '.mov'}


@router.post("/upload-audio", response_model=ScoringResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    meeting_id: str = Form(...),
    project_name: str = Form("未命名项目"),
    track: str = Form("未指定赛道"),
    team_size: int = Form(4),
    auto_score: bool = Form(True),
    provider: str = Form("deepseek"),
    compare_mode: bool = Form(False),
    has_screen_share: bool = Form(False),
    has_video: Optional[bool] = Form(None),
    audio_source_count: int = Form(0),
    session_id: Optional[str] = Form(None),
    team_roster: Optional[str] = Form(None),
    clock_id: Optional[str] = Form(None),
    media_clock_master: Optional[str] = Form(None),
):
    """
    上传音频文件并自动触发 AI 评分

    - audio: 音频文件（webm/wav/mp3）
    - meeting_id: 会议 ID
    - project_name: 项目名称
    - track: 赛道
    - team_size: 团队人数
    - auto_score: 是否自动触发评分（默认 true）
    """
    # 校验文件
    if not audio.filename:
        raise HTTPException(status_code=400, detail="未上传文件")

    allowed_ext = {'.webm', '.wav', '.mp3', '.ogg', '.mp4', '.m4a', '.mkv'}
    ext = os.path.splitext(audio.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")

    # 检查是否含视频轨
    has_video = _uploaded_media_has_video(ext, has_video)
    logger.info(f"上传文件: {audio.filename}, 格式: {ext}, has_video: {has_video}")

    # 保存文件
    try:
        file_path = audio_service.save_upload_file(audio, meeting_id, settings.UPLOAD_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")

    # 清理该 meeting 之前的旧分析结果（避免 status 轮询返回旧数据）
    _clean_old_results(meeting_id)

    project_info = {
        'project_name': project_name,
        'track': track,
        'team_size': team_size,
        'has_screen_share': has_screen_share,
        'audio_source_count': audio_source_count,
        'session_id': session_id
    }
    if clock_id:
        project_info['media_clock'] = {
            'clockId': clock_id,
            'masterSource': media_clock_master or 'MEDIA_PTS',
        }
    roster = _parse_team_roster(team_roster)
    if roster:
        project_info['team_roster'] = roster

    if auto_score:
        # 清掉旧进度和结果（新上传新评分）
        results_dir = os.path.join(settings.UPLOAD_DIR, "results")
        os.makedirs(results_dir, exist_ok=True)
        for prefix in ("progress", "result"):
            old = os.path.join(results_dir, f"{prefix}_{meeting_id}.json")
            if os.path.exists(old): os.remove(old)

        # 后台线程执行评分流水线（避免阻塞事件循环）
        callback = settings.BACKEND_CALLBACK_URL
        import asyncio
        import threading

        def _run_pipeline():
            """在独立线程中运行 pipeline，不阻塞事件循环"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    pipeline_service.run_scoring_pipeline(
                        file_path, meeting_id, project_info, callback,
                        provider, compare_mode
                    )
                )
            finally:
                loop.close()

        thread = threading.Thread(target=_run_pipeline, daemon=True)
        thread.start()

        if session_id:
            try:
                session = _read_session(session_id)
                session["recording_status"] = "uploaded"
                session["final_score_status"] = "processing"
                session["uploaded_file"] = file_path
                _write_session(session)
            except HTTPException:
                logger.warning(f"上传时未找到评分会话: {session_id}")

        return ScoringResponse(
            meeting_id=meeting_id,
            status="processing",
            message="音频已上传，评分任务已在后台启动",
            session_id=session_id
        )
    else:
        if session_id:
            try:
                session = _read_session(session_id)
                session["recording_status"] = "uploaded"
                session["uploaded_file"] = file_path
                _write_session(session)
            except HTTPException:
                logger.warning(f"上传时未找到评分会话: {session_id}")

        return ScoringResponse(
            meeting_id=meeting_id,
            status="uploaded",
            message="音频已上传，等待手动触发评分",
            session_id=session_id
        )


@router.post("/score", response_model=ScoringResponse)
async def trigger_score(
    background_tasks: BackgroundTasks,
    request: ScoringRequest
):
    """
    手动触发评分（音频已上传的情况）

    查找已上传的 WAV 文件并执行评分
    """
    # 查找已有的 wav 文件
    wav_path = os.path.join(settings.UPLOAD_DIR, f"meeting_{meeting_id_to_int(request.meeting_id)}.wav")

    # 如果没有 wav，查找 webm 并转码
    if not os.path.exists(wav_path):
        webm_path = None
        for f in os.listdir(settings.UPLOAD_DIR):
            if f.startswith(f"meeting_{request.meeting_id}") and f.endswith('.webm'):
                webm_path = os.path.join(settings.UPLOAD_DIR, f)
                break

        if webm_path and os.path.exists(webm_path):
            wav_path = audio_service.convert_to_wav(webm_path)
        else:
            raise HTTPException(status_code=404, detail=f"未找到会议 {request.meeting_id} 的音频文件")

    # 清理旧分析结果
    _clean_old_results(request.meeting_id)

    project_info = {
        'project_name': request.project_name,
        'track': request.track,
        'team_size': request.team_size
    }

    callback = request.callback_url or settings.BACKEND_CALLBACK_URL

    import asyncio
    import threading

    def _run_pipeline():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                pipeline_service.run_scoring_pipeline(
                    wav_path, request.meeting_id, project_info, callback,
                    request.provider, request.compare_mode
                )
            )
        finally:
            loop.close()

    thread = threading.Thread(target=_run_pipeline, daemon=True)
    thread.start()

    return ScoringResponse(
        meeting_id=request.meeting_id,
        status="processing",
        message="评分任务已在后台启动"
    )


@router.get("/result/{meeting_id}")
async def get_result(meeting_id: str):
    """获取评分结果"""
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 的评分结果不存在")

    with open(result_path, 'r', encoding='utf-8') as f:
        return _sanitize_result_payload(json.load(f))


@router.get("/jury/personas")
async def list_jury_personas():
    """读取 AI 评审团 16 个详细评委画像。"""
    return {
        "personas": persona_repository.load_personas(),
        "source": "file_backed",
    }


@router.put("/jury/personas/{code}")
async def update_jury_persona(code: str, request: JuryPersonaUpdateRequest):
    """更新单个 AI 评委画像。"""
    try:
        patch = request.model_dump(exclude_unset=True)
    except AttributeError:
        patch = request.dict(exclude_unset=True)
    try:
        return persona_repository.save_persona(code.upper(), patch)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"AI评委画像保存失败: code={code}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI评委画像保存失败: {exc}")


@router.post("/jury/personas/reset")
async def reset_jury_personas():
    """恢复默认 16 个 AI 评委画像。"""
    return {
        "personas": persona_repository.reset_personas(),
        "source": "default_reset",
    }


@router.post("/jury/{meeting_id}/start")
async def start_jury_review(meeting_id: str, request: JuryStartRequest):
    """启动 AI 评审团争议复核。评审团围绕规则引擎结果输出复核意见，不覆盖最终分。"""
    try:
        official_result = jury_scoring_service.load_official_result(meeting_id)
        session = jury_scoring_service.start_jury_review_background(
            meeting_id=meeting_id,
            official_result=official_result,
            project_info=official_result.get("project_info", {}),
            provider=request.provider or "deepseek",
            ppt_recognition=bool(request.ppt_recognition),
            memory_summary=request.roadshow_memory,
            dispute_review_context=request.dispute_review_context,
        )
        return jury_scoring_service.public_jury_result(session)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"AI评审团启动失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI评审团启动失败: {exc}")


@router.get("/jury/{meeting_id}/status")
async def get_jury_status(meeting_id: str):
    """查询 AI 评审团复盘状态。"""
    session = jury_scoring_service.get_latest_jury_session(meeting_id)
    if not session:
        return {
            "meeting_id": meeting_id,
            "status": "empty",
            "message": "该会议暂未生成AI评审团复盘",
        }
    return {
        "meeting_id": meeting_id,
        "jury_session_id": session.get("jury_session_id"),
        "status": session.get("status"),
        "judge_count": session.get("judge_count"),
        "completed_count": len([
            report for report in session.get("judge_reports", [])
            if report.get("status") == "completed"
        ]),
        "started_at": session.get("started_at"),
        "completed_at": session.get("completed_at"),
        "error_message": session.get("error_message"),
    }


@router.get("/jury/{meeting_id}/result")
async def get_jury_result(meeting_id: str):
    """获取最新 AI 评审团复盘结果。"""
    session = jury_scoring_service.get_latest_jury_session(meeting_id)
    if not session:
        return {
            "meeting_id": meeting_id,
            "status": "empty",
            "message": "该会议暂未生成AI评审团复盘",
        }
    return jury_scoring_service.public_jury_result(session)


@router.get("/jury/{meeting_id}/report")
async def download_jury_report(meeting_id: str):
    """下载独立 AI 评审团复盘报告。"""
    session = jury_scoring_service.get_latest_jury_session(meeting_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 暂未生成 AI 评审团复盘")
    if session.get("status") not in {"completed", "partial_failed"}:
        raise HTTPException(status_code=400, detail="AI评审团复盘尚未完成，暂不能导出报告")
    report_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    try:
        if not session.get("official_evidence_summary"):
            session = dict(session)
            session["official_evidence_summary"] = build_system_evidence_summary(
                jury_scoring_service.load_official_result(meeting_id)
            )
        report_path = await asyncio.to_thread(jury_report_service.generate_jury_report, session, report_dir)
    except Exception as exc:
        logger.error(f"AI评审团报告生成失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI评审团报告生成失败: {exc}")
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"AI评审团复盘报告_{meeting_id}.pdf",
    )


@router.get("/coaching/expression/{meeting_id}")
async def get_expression_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek"):
    """获取由大模型生成的表达节奏训练建议。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_expression_coaching,
            meeting_id,
            refresh,
            provider
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"表达训练建议生成失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"表达训练建议生成失败: {exc}")


@router.post("/coaching/expression/{meeting_id}")
async def refresh_expression_coaching(meeting_id: str, request: CoachingRefreshRequest):
    """强制刷新表达节奏训练建议。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_expression_coaching,
            meeting_id,
            True if request.refresh is None else request.refresh,
            request.provider or "deepseek"
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"表达训练建议刷新失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"表达训练建议刷新失败: {exc}")


@router.get("/coaching/presentation/{meeting_id}")
async def get_presentation_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek"):
    """获取由大模型生成的现场呈现训练建议。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_presentation_coaching,
            meeting_id,
            refresh,
            provider
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"现场呈现建议生成失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"现场呈现建议生成失败: {exc}")


@router.post("/coaching/presentation/{meeting_id}")
async def refresh_presentation_coaching(meeting_id: str, request: CoachingRefreshRequest):
    """强制刷新现场呈现训练建议。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_presentation_coaching,
            meeting_id,
            True if request.refresh is None else request.refresh,
            request.provider or "deepseek"
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"现场呈现建议刷新失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"现场呈现建议刷新失败: {exc}")


@router.get("/coaching/action-plan/{meeting_id}")
async def get_action_plan_coaching(meeting_id: str, refresh: bool = False, provider: str = "deepseek"):
    """获取由大模型生成的下一轮提分方案。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_action_plan_coaching,
            meeting_id,
            refresh,
            provider
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"提分方案生成失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提分方案生成失败: {exc}")


@router.post("/coaching/action-plan/{meeting_id}")
async def refresh_action_plan_coaching(meeting_id: str, request: CoachingRefreshRequest):
    """强制刷新下一轮提分方案。"""
    try:
        return await asyncio.to_thread(
            coaching_service.get_action_plan_coaching,
            meeting_id,
            True if request.refresh is None else request.refresh,
            request.provider or "deepseek"
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"提分方案刷新失败: meeting={meeting_id}, error={exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提分方案刷新失败: {exc}")


@router.get("/status/{meeting_id}")
async def get_status(meeting_id: str):
    """查询评分状态（含当前步骤）"""
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")

    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        rs = result.get('status', 'unknown')
        if rs == 'generating_report':
            # 报告还在生成中，按 processing 返回
            return {
                'meeting_id': meeting_id,
                'status': 'processing',
                'current_step': 'report',
                'step_label': '生成PDF报告中...',
                'progress_percent': 92
            }
        return {
            'meeting_id': meeting_id,
            'status': rs,
            'current_step': 'completed',
            'step_label': '已完成',
            'progress_percent': 100 if rs == 'completed' else 0,
            'completed_at': result.get('completed_at'),
            'elapsed_seconds': result.get('elapsed_seconds'),
            'total_elapsed_seconds': result.get('total_elapsed_seconds'),
            'report_url': f'/api/ai/report/{meeting_id}'
        }

    # 检查进度文件（流水线运行时实时写入）
    progress_path = os.path.join(settings.UPLOAD_DIR, "results", f"progress_{meeting_id}.json")
    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            progress = json.load(f)
        if not _is_progress_fresh(progress):
            return {
                'meeting_id': meeting_id,
                'status': 'not_found',
                'current_step': None,
                'message': '未找到该会议的实时评分任务'
            }
        return {
            'meeting_id': meeting_id,
            'status': 'processing',
            'current_step': progress.get('step', 'asr'),
            'step_label': progress.get('label', ''),
            'step_num': progress.get('step_num', 0),
            'total_steps': progress.get('total_steps', 0),
            'progress_percent': progress.get('progress_percent', 0),
            'progress_updated_at': progress.get('updated_at')
        }

    # 检查是否有上传的文件
    meeting_prefix = f"meeting_{meeting_id}_"
    has_audio = any(
        f.startswith(meeting_prefix)
        for f in os.listdir(settings.UPLOAD_DIR)
        if os.path.isfile(os.path.join(settings.UPLOAD_DIR, f))
    )

    return {
        'meeting_id': meeting_id,
        'status': 'processing' if has_audio else 'not_found',
        'current_step': 'asr' if has_audio else None,
        'message': '评分进行中' if has_audio else '未找到该会议的音频文件'
    }


@router.get("/report/{meeting_id}")
async def download_report(meeting_id: str):
    """下载 PDF 评分报告"""
    report_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    report_path = os.path.join(report_dir, f"report_{meeting_id}.pdf")
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")

    if os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            result = _sanitize_result_payload(json.load(f))
        report_path = report_service.generate_report(result, report_dir)

    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 的评分报告不存在")

    return FileResponse(
        report_path,
        media_type='application/pdf',
        filename=f"路演评分报告_{meeting_id}.pdf"
    )


@router.get("/profile/{meeting_id}")
async def get_character_profile(meeting_id: str):
    """获取能力画像"""
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 的评分结果不存在")

    with open(result_path, 'r', encoding='utf-8') as f:
        result = json.load(f)

    profile = result.get('character_profile', {})
    if not profile or 'error' in profile:
        raise HTTPException(status_code=404, detail="能力画像未生成或生成失败")

    return {
        'meeting_id': meeting_id,
        'profile': profile.get('profile_markdown', ''),
        'sections': profile.get('sections', {}),
        'provider': profile.get('provider', '')
    }


@router.get("/fusion/{meeting_id}")
async def get_fusion_timeline(meeting_id: str):
    """获取音视频融合时间线"""
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{meeting_id}.json")

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail=f"会议 {meeting_id} 的评分结果不存在")

    with open(result_path, 'r', encoding='utf-8') as f:
        result = json.load(f)

    fusion = result.get('fusion', {})
    if not fusion or 'error' in fusion:
        raise HTTPException(status_code=404, detail="融合数据未生成")

    return {
        'meeting_id': meeting_id,
        'has_video': result.get('has_video', False),
        'timeline': fusion.get('timeline', []),
        'summary': fusion.get('summary', {}),
        'contradictions': fusion.get('contradictions', []),
        'trends': fusion.get('trends', {})
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        'status': 'ok',
        'service': 'ai-scoring',
        'providers': {
            'deepseek': {
                'configured': bool(settings.DEEPSEEK_API_KEY),
                'model': settings.DEEPSEEK_MODEL or 'deepseek-v4-pro',
                'label': 'DeepSeek V3'
            }
        },
        'upload_dir': settings.UPLOAD_DIR,
        'upload_dir_exists': os.path.exists(settings.UPLOAD_DIR)
    }


def _clean_old_results(meeting_id: str):
    """清理该会议旧的分析结果、报告和进度文件"""
    results_dir = os.path.join(settings.UPLOAD_DIR, "results")
    reports_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    files_to_remove = [
        os.path.join(results_dir, f"result_{meeting_id}.json"),
        os.path.join(results_dir, f"progress_{meeting_id}.json"),
        os.path.join(reports_dir, f"report_{meeting_id}.pdf"),
    ]
    for f in files_to_remove:
        try:
            if os.path.exists(f):
                os.remove(f)
                logger.info(f"已清理旧文件: {f}")
        except Exception as e:
            logger.warning(f"清理旧文件失败 {f}: {e}")


def meeting_id_to_int(meeting_id: str) -> str:
    """确保 meeting_id 是字符串"""
    return str(meeting_id)


# ==================== 双视频源上传端点 ====================

@router.post("/upload-dual-video", response_model=ScoringResponse)
async def upload_dual_video(
    background_tasks: BackgroundTasks,
    camera: UploadFile = File(None),
    screen: UploadFile = File(None),
    audio: UploadFile = File(...),
    meeting_id: str = Form(...),
    project_name: str = Form("未命名项目"),
    track: str = Form("未指定赛道"),
    team_size: str = Form("4"),
    auto_score: bool = Form(True),
    provider: str = Form("deepseek"),
    compare_mode: bool = Form(False),
    audio_source_count: str = Form("0"),
    has_ppt: bool = Form(False),
    team_roster: Optional[str] = Form(None),
):
    """
    上传双视频源文件（摄像头+屏幕共享）+ 音频

    录制模式判断：
    - camera + screen 同时上传 → 双源模式（启用PPT识别）
    - 只有其中一路 → 单源模式（无PPT识别）
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="未上传音频文件")

    # 解析数字参数
    team_size = int(team_size) if team_size else 4
    audio_source_count = int(audio_source_count) if audio_source_count else 0

    # 保存文件
    audio_path = audio_service.save_upload_file(audio, meeting_id, settings.UPLOAD_DIR)
    camera_path = None
    screen_path = None

    if camera and camera.filename:
        camera_path = audio_service.save_upload_file(camera, meeting_id + '_camera', settings.UPLOAD_DIR)
    if screen and screen.filename:
        screen_path = audio_service.save_upload_file(screen, meeting_id + '_screen', settings.UPLOAD_DIR)

    # 清理旧结果
    _clean_old_results(meeting_id)

    project_info = {
        'project_name': project_name,
        'track': track,
        'team_size': team_size,
        'has_screen_share': screen_path is not None,
        'audio_source_count': audio_source_count,
        'has_ppt': has_ppt
    }
    roster = _parse_team_roster(team_roster)
    if roster:
        project_info['team_roster'] = roster

    # 判断模式
    is_dual = camera_path is not None and screen_path is not None
    mode = 'dual' if is_dual else ('camera_only' if camera_path else 'screen_only')

    logger.info(f"上传录制文件: meeting={meeting_id}, mode={mode}, "
                f"camera={'✓' if camera_path else '✗'}, screen={'✓' if screen_path else '✗'}")

    if auto_score:
        # 清掉旧进度和结果（新上传新评分）
        results_dir = os.path.join(settings.UPLOAD_DIR, "results")
        os.makedirs(results_dir, exist_ok=True)
        for prefix in ("progress", "result"):
            old = os.path.join(results_dir, f"{prefix}_{meeting_id}.json")
            if os.path.exists(old): os.remove(old)

        callback = settings.BACKEND_CALLBACK_URL

        import asyncio
        import threading

        if is_dual:
            def _run_dual():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        pipeline_service.run_dual_video_scoring_pipeline(
                            camera_video_path=camera_path,
                            screen_video_path=screen_path,
                            audio_path=audio_path,
                            meeting_id=meeting_id,
                            project_info=project_info,
                            callback_url=callback,
                            provider=provider,
                            compare_mode=compare_mode,
                            ppt_recognition=has_ppt,
                        )
                    )
                finally:
                    loop.close()
            thread = threading.Thread(target=_run_dual, daemon=True)
            thread.start()
        else:
            # 单源模式：用哪路视频就传哪路
            video_path = camera_path or screen_path
            def _run_single():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        pipeline_service.run_scoring_pipeline(
                            audio_file_path=video_path or audio_path,
                            meeting_id=meeting_id,
                            project_info=project_info,
                            callback_url=callback,
                            provider=provider,
                            compare_mode=compare_mode,
                            ppt_recognition=False  # 单源不启用PPT识别
                        )
                    )
                finally:
                    loop.close()
            thread = threading.Thread(target=_run_single, daemon=True)
            thread.start()

        return ScoringResponse(
            meeting_id=meeting_id,
            status="processing",
            message=f"文件已上传（{mode}模式），评分任务已在后台启动"
        )
    else:
        return ScoringResponse(
            meeting_id=meeting_id,
            status="uploaded",
            message=f"文件已上传（{mode}模式），等待手动触发评分"
        )
