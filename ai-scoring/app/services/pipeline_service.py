"""
AI 评分流水线 — 编排整个评分流程
支持两种模式：
  - 纯音频模式：音频上传 → 转码 → ASR → 语音分析 → 大模型评分 → 报告
  - 音视频模式：视频上传 → 提取音频 + 抽帧 → ASR + 视频分析 → 融合 → 五维评分 + 画像 → 报告
"""
import os
import atexit
import json
import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime

from app.config import settings
from app.services import (
    audio_service, asr_service, speech_analysis_service,
    llm_scoring_service, report_service
)
from app.services import evidence_extraction_service
from app.services.video_analysis_service import video_analysis_service
from app.services.fusion_service import fusion_service
from app.services.character_profile_service import character_profile_service
from app.services.speaker_evidence_service import build_speaker_evidence
from app.services.competition_calibration_service import apply_calibration_to_result
from app.services.jury import scoring_service as jury_scoring_service
from app.services.pipeline_payloads import (
    build_backend_callback_payload,
    persistable_fusion,
    persistable_video_analysis,
    validate_fusion_for_scoring,
    validate_video_analysis_for_scoring,
)
from app.services.visual_frame_selector import (
    select_visual_frame_events,
    visual_frame_selection_summary,
)
from app.services.media_evidence.legacy_adapter import build_legacy_evidence_package
from app.services.media_evidence.shadow_store import save_shadow_package
from app.services.media_evidence.asr_diarization_reconciler import (
    reconcile_asr_with_diarization,
)
from app.services.media_evidence.local_diarization import (
    LocalDiarizationError,
    LocalSpeakerDiarizer,
)
from app.services.media_evidence.lr_asd_client import (
    LocalLrAsdClient,
    LocalLrAsdError,
    PersistentLrAsdTransport,
)
from app.services.media_evidence.model_worker_pool import (
    ModelWorkerPool,
    WorkerCrashedError,
)
from app.services.media_evidence.active_speaker_fusion import (
    fuse_active_speaker_evidence,
)
from app.services.media_evidence.speaker_attribution_shadow import (
    build_shadow_attribution,
    save_shadow_attribution,
)
from app.services.media_evidence.final_speaker_attribution import (
    build_final_speaker_attribution,
)
from app.services.media_evidence.three_d_speaker_client import (
    LocalThreeDSpeakerClient,
    LocalThreeDSpeakerError,
)

logger = logging.getLogger(__name__)
_PROGRESS_WRITE_LOCK = threading.Lock()
_LOCAL_DIARIZATION_CAPACITY = threading.BoundedSemaphore(
    settings.LOCAL_DIARIZATION_MAX_CONCURRENCY
)
_LOCAL_ACTIVE_SPEAKER_CAPACITY = threading.BoundedSemaphore(
    settings.LOCAL_ACTIVE_SPEAKER_MAX_CONCURRENCY
)
_LOCAL_3D_SPEAKER_CAPACITY = threading.BoundedSemaphore(
    settings.LOCAL_3D_SPEAKER_MAX_CONCURRENCY
)
_LR_ASD_POOL_LOCK = threading.Lock()
_LR_ASD_POOL = None


class _PooledLrAsdTransport:
    def __init__(self, pool):
        self._pool = pool

    def analyze(self, video_path, wav_path, *, timeout_seconds):
        def operation(worker):
            try:
                return worker.analyze(
                    video_path, wav_path, timeout_seconds=timeout_seconds
                )
            except (BrokenPipeError, EOFError, OSError) as error:
                raise WorkerCrashedError("lr_asd_persistent_worker_crashed") from error

        future = self._pool.submit(
            "UPLOAD",
            operation,
            timeout_seconds=timeout_seconds,
        )
        try:
            return future.result(timeout=max(1.0, float(timeout_seconds) + 1.0))
        except WorkerCrashedError as error:
            raise BrokenPipeError("lr_asd_persistent_worker_crashed") from error


def _new_persistent_lr_asd_worker():
    return PersistentLrAsdTransport(
        python_executable=settings.LOCAL_ACTIVE_SPEAKER_PYTHON,
        worker_script=settings.LOCAL_ACTIVE_SPEAKER_WORKER,
        model_repository=settings.LOCAL_ACTIVE_SPEAKER_REPOSITORY,
        model_weight=settings.LOCAL_ACTIVE_SPEAKER_WEIGHT,
        yunet_model=settings.LOCAL_ACTIVE_SPEAKER_YUNET_MODEL,
        sface_model=settings.LOCAL_ACTIVE_SPEAKER_SFACE_MODEL,
        global_identity_threshold=settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_THRESHOLD,
        global_identity_stable_threshold=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_STABLE_THRESHOLD
        ),
        global_identity_minimum_detections=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_DETECTIONS
        ),
        global_identity_minimum_visibility=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_VISIBILITY
        ),
    )


def _persistent_lr_asd_transport():
    global _LR_ASD_POOL
    with _LR_ASD_POOL_LOCK:
        if _LR_ASD_POOL is None:
            _LR_ASD_POOL = ModelWorkerPool(
                _new_persistent_lr_asd_worker,
                worker_count=settings.LOCAL_ACTIVE_SPEAKER_MAX_CONCURRENCY,
                maximum_queue_size=settings.LOCAL_ACTIVE_SPEAKER_WORKER_QUEUE_SIZE,
            )
        return _PooledLrAsdTransport(_LR_ASD_POOL)


def _close_lr_asd_pool():
    global _LR_ASD_POOL
    with _LR_ASD_POOL_LOCK:
        pool, _LR_ASD_POOL = _LR_ASD_POOL, None
    if pool is not None:
        pool.close()


atexit.register(_close_lr_asd_pool)

DEEP_REPORT_FIELDS = (
    "score_overview",
    "evidence_summary",
    "evidence_audit",
    "jury_review",
    "audio_visual_fusion",
    "pitch_structure_benchmark",
    "judge_questioning",
    "action_plan",
    "team_optimization",
    "final_verdict",
    "status",
    "score_authority",
    "error_code",
    "error",
    "generation_meta",
)


class LLMScoringIncomplete(RuntimeError):
    """Raised when a staged LLM result cannot safely continue to report generation."""


def _write_evidence_shadow_if_enabled(
    *,
    meeting_id: str,
    asr_result: dict,
    speech_quality: dict,
    video_analysis: dict | None,
    fusion: dict | None,
) -> str | None:
    """Persist diagnostic evidence without affecting the authoritative scoring path."""

    if not settings.UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED:
        return None
    try:
        package = build_legacy_evidence_package(
            session_id=meeting_id,
            source_type="UPLOAD_VIDEO",
            asr_result=asr_result,
            speech_quality=speech_quality,
            video_analysis=video_analysis or {},
            fusion=fusion or {},
            processing_metrics={"mode": "legacy_shadow"},
        )
        path = save_shadow_package(settings.UPLOAD_DIR, meeting_id, package)
        logger.info(
            "[%s] 影子证据包已写入: hash=%s",
            meeting_id,
            package.get("snapshotHash", ""),
        )
        return path
    except Exception as error:
        # 影子路径在切换前必须与官方评分路径故障隔离。
        logger.warning("[%s] 影子证据包生成失败: %s", meeting_id, error)
        return None


def _build_ai_score_payload(llm_result: dict) -> dict:
    """Keep the report-facing payload stable while preserving deep analysis fields."""
    payload = {
        'overall_score': llm_result.get('overall_score'),
        'dimensions': llm_result.get('dimensions', {}),
        'highlights': llm_result.get('highlights', []),
        'critical_issues': llm_result.get('critical_issues', []),
        'improvement_priorities': llm_result.get('improvement_priorities', []),
        'model': llm_result.get('model', ''),
        'provider': llm_result.get('provider', ''),
        'tokens_used': llm_result.get('tokens_used', {}),
    }
    for field in DEEP_REPORT_FIELDS:
        if field in llm_result:
            payload[field] = llm_result.get(field)
    return payload


def _ensure_llm_result_complete(llm_result: dict) -> None:
    status = llm_result.get("status")
    score = llm_result.get("overall_score")
    generation_meta = llm_result.get("generation_meta") or {}
    stages_complete = all(
        isinstance(generation_meta.get(stage), dict)
        and generation_meta[stage].get("status") == "completed"
        for stage in ("core", "evidence", "jury")
    )
    if status == "completed" and score is not None and stages_complete:
        return
    error_code = llm_result.get("error_code") or "staged_scoring_incomplete"
    raise LLMScoringIncomplete(error_code)


def _apply_rule_ledger_narrative(result: dict, meeting_id: str | None = None) -> dict:
    """Rewrite official score narrative from the structured rule ledger when available."""
    try:
        from app.services.scoring.ledger_narrative_service import apply_rule_ledger_to_pipeline_result

        updated = apply_rule_ledger_to_pipeline_result(result)
        authority = (updated.get("ai_score") or {}).get("score_authority")
        if authority == "structured_rule_engine":
            logger.info(
                "[%s] 已用规则账本重写报告叙事: overall=%s source=%s",
                meeting_id or updated.get("meeting_id"),
                (updated.get("ai_score") or {}).get("overall_score"),
                (updated.get("ai_score") or {}).get("narrative_source"),
            )
        elif authority == "review_required":
            logger.info("[%s] 证据不可发布，报告保持待复核叙事", meeting_id or updated.get("meeting_id"))
        return updated
    except Exception as error:
        logger.warning("[%s] 规则账本叙事重写失败，保留原 LLM 文案: %s", meeting_id, error)
        return result


def _apply_visual_speech_alignment(result: dict, meeting_id: str | None = None) -> dict:
    """评分落库前：音画对齐文案消歧 + skill 画面局部重评（规则账本路径也要走）。"""
    if not isinstance(result, dict):
        return result
    try:
        from app.services.evidence_alignment_service import sanitize_result_for_report

        aligned = sanitize_result_for_report(result)
        meta = ((aligned.get("ai_score") or {}).get("_skill_visual_rescore") or {})
        if meta:
            logger.info(
                "[%s] skill 画面局部重评: skill %s→%s overall %s→%s (%s)",
                meeting_id or aligned.get("meeting_id"),
                meta.get("before"),
                meta.get("after"),
                meta.get("overall_before"),
                meta.get("overall_after"),
                meta.get("credit_rule"),
            )
        return aligned
    except Exception as error:
        logger.warning("[%s] 音画证据对齐跳过: %s", meeting_id, error)
        return result


def _enrich_ledger_grounded_report(
    result: dict,
    *,
    asr_result: dict,
    speech_quality: dict,
    project_info: dict,
    fusion_context: dict | None,
    provider: str,
    meeting_id: str | None = None,
) -> dict:
    """Upgrade prose quality with a ledger-grounded coach report, scores stay locked."""
    try:
        from app.services.scoring.ledger_report_service import enrich_with_ledger_grounded_report

        ai_score = result.get("ai_score") or {}
        if ai_score.get("score_authority") != "structured_rule_engine":
            return result
        shadow = result.get("rule_engine_shadow")
        if not isinstance(shadow, dict):
            from app.services.pipeline_payloads import build_rule_engine_shadow_payload

            shadow = build_rule_engine_shadow_payload(result)
            result["rule_engine_shadow"] = shadow
        enriched = enrich_with_ledger_grounded_report(
            ai_score=ai_score,
            rule_payload=shadow,
            evidence_extraction=result.get("evidence_extraction") or {},
            asr_result=asr_result,
            speech_quality=speech_quality,
            project_info=project_info,
            fusion_context=fusion_context,
            provider=provider,
            meeting_id=meeting_id,
        )
        result["ai_score"] = enriched
        logger.info(
            "[%s] 账本接地深度报告完成: source=%s overall=%s",
            meeting_id,
            enriched.get("narrative_source"),
            enriched.get("overall_score"),
        )
        return result
    except Exception as error:
        logger.warning("[%s] 账本接地深度报告失败，保留账本骨架叙事: %s", meeting_id, error)
        return result


def _score_with_rule_first(
    *,
    result: dict,
    asr_result: dict,
    speech_quality: dict,
    project_info: dict,
    fusion_context: dict | None,
    provider: str,
    meeting_id: str,
    duration_note: str | None,
    ppt_recognition: bool,
    compare_mode: bool,
) -> dict:
    """Prefer rule ledger + high-quality grounded report; fall back to free scoring."""
    # 1) Evidence extraction first — no free score contamination.
    _attach_evidence_extraction(result, asr_result, project_info, fusion_context, provider)
    if _extraction_is_incomplete(result.get("evidence_extraction")):
        logger.warning("[%s] 证据窗未建成，跳过规则入账", meeting_id)
        return result
    result = _apply_rule_ledger_narrative(result, meeting_id)
    authority = (result.get("ai_score") or {}).get("score_authority")
    skip_free_core = bool(getattr(settings, "LLM_SKIP_FREE_CORE_WHEN_RULE_READY", True))

    if authority == "structured_rule_engine" and skip_free_core and not compare_mode:
        logger.info("[%s] 规则分已就绪，跳过自由打分，生成账本接地高质量报告", meeting_id)
        _save_progress(meeting_id, "llm", "基于规则账本生成高质量报告...", 4, 8)
        result = _enrich_ledger_grounded_report(
            result,
            asr_result=asr_result,
            speech_quality=speech_quality,
            project_info=project_info,
            fusion_context=fusion_context,
            provider=provider,
            meeting_id=meeting_id,
        )
        # Ensure staged completeness markers so report generation is not blocked.
        ai_score = result.setdefault("ai_score", {})
        generation_meta = dict(ai_score.get("generation_meta") or {})
        for stage in ("core", "evidence", "jury"):
            generation_meta.setdefault(stage, {"status": "completed", "source": "ledger_grounded_path"})
        if generation_meta.get("ledger_grounded_report", {}).get("status") == "completed":
            generation_meta["core"] = {"status": "completed", "source": "ledger_grounded_path"}
            generation_meta["evidence"] = {"status": "completed", "source": "ledger_grounded_path"}
            generation_meta["jury"] = {"status": "completed", "source": "ledger_grounded_path"}
        ai_score["generation_meta"] = generation_meta
        ai_score.setdefault("status", "completed")
        return _apply_visual_speech_alignment(result, meeting_id)

    # 2) Fallback / compare mode: full free staged scoring, then re-lock to ledger.
    logger.info("[%s] 使用传统分阶段评分（fallback/compare）", meeting_id)
    if compare_mode:
        comparison = llm_scoring_service.score_with_comparison(
            asr_result,
            speech_quality,
            project_info,
            fusion_context=fusion_context,
            duration_note=duration_note,
            ppt_recognition=ppt_recognition,
        )
        llm_result = comparison.get("deepseek", {})
        result["ai_score_comparison"] = comparison
        result["ai_score"] = _build_ai_score_payload(llm_result)
        result["ai_score"]["comparison_available"] = True
    else:
        llm_result = llm_scoring_service.score_roadshow(
            asr_result,
            speech_quality,
            project_info,
            provider=provider,
            fusion_context=fusion_context,
            duration_note=duration_note,
            ppt_recognition=ppt_recognition,
        )
        result["ai_score"] = _build_ai_score_payload(llm_result)
    _ensure_llm_result_complete(llm_result)

    # Re-apply ledger authority if extraction already succeeded.
    if result.get("evidence_extraction"):
        result = _apply_rule_ledger_narrative(result, meeting_id)
        if (result.get("ai_score") or {}).get("score_authority") == "structured_rule_engine":
            result = _enrich_ledger_grounded_report(
                result,
                asr_result=asr_result,
                speech_quality=speech_quality,
                project_info=project_info,
                fusion_context=fusion_context,
                provider=provider,
                meeting_id=meeting_id,
            )
    return _apply_visual_speech_alignment(result, meeting_id)


def _extraction_is_incomplete(extraction: dict | None) -> bool:
    from app.services.scoring.evidence_memory_session import is_extraction_incomplete

    return is_extraction_incomplete(extraction)


def _fail_incomplete_extraction(meeting_id: str, result: dict) -> dict:
    from app.services.scoring.evidence_memory_session import (
        extraction_incomplete_error,
        extraction_incomplete_message,
    )

    result["status"] = "failed"
    result["error"] = extraction_incomplete_error(result.get("evidence_extraction"))
    result["error_message"] = extraction_incomplete_message(result.get("evidence_extraction"))
    logger.error("[%s] %s", meeting_id, result["error_message"])
    _save_result(meeting_id, result)
    _remove_progress(meeting_id)
    return result


def _attach_evidence_extraction(result: dict, asr_result: dict, project_info: dict, fusion_context: dict | None, provider: str):
    try:
        extraction = evidence_extraction_service.extract_evidence(
            asr_result=asr_result,
            project_info=project_info,
            fusion_context=fusion_context,
            provider=provider,
            scoring_context=result.get("ai_score") or {},
        )
        quality = extraction.get("extractionQuality") or {}
        needs_retry = (
            extraction.get("status") in {"failed", "review_required"}
            or quality.get("jsonParseable") is False
            or quality.get("publicationEligible") is False
            or quality.get("incomplete") is True
        )
        if needs_retry:
            logger.warning(
                "[%s] 证据抽取不完整/解析失败，自动重试一次: status=%s matched=%s jsonParseable=%s",
                result.get("meeting_id"),
                extraction.get("status"),
                quality.get("matchedObservationCount"),
                quality.get("jsonParseable"),
            )
            retry = evidence_extraction_service.extract_evidence(
                asr_result=asr_result,
                project_info=project_info,
                fusion_context=fusion_context,
                provider=provider,
                scoring_context=result.get("ai_score") or {},
            )
            retry_quality = retry.setdefault("extractionQuality", {})
            retry_quality["retryCount"] = max(1, int(retry_quality.get("retryCount") or 0))
            # Prefer a successful parse / publishable result; otherwise keep the better matched count.
            if (
                retry.get("status") != "failed"
                and retry_quality.get("jsonParseable") is not False
                and (
                    retry_quality.get("publicationEligible") is True
                    or extraction.get("status") == "failed"
                    or int(retry_quality.get("matchedObservationCount") or 0)
                    >= int(quality.get("matchedObservationCount") or 0)
                )
            ):
                extraction = retry
            else:
                quality["retryCount"] = max(1, int(quality.get("retryCount") or 0))
        result["evidence_extraction"] = extraction
    except Exception as e:
        logger.warning("[%s] 证据抽取未接入当前赛道或执行失败: %s", result.get("meeting_id"), e)


def determine_duration_adjustment(actual_duration: float, expected_duration: float = 3600) -> dict:
    """Return duration-based scoring adjustment for the 60-minute competition format."""
    duration_note = None
    score_cap = None
    skip_llm = False
    duration_minutes = actual_duration / 60 if actual_duration else 0
    expected_minutes = expected_duration / 60

    if actual_duration < 600:
        skip_llm = True
    elif actual_duration < 1800:
        score_cap = 20
        duration_note = (
            f"⚠ 注意：本次路演实际时长约 {duration_minutes:.0f} 分钟，"
            f"远低于比赛要求的 {expected_minutes:.0f} 分钟。"
            f"请在评分时充分考虑时长不足的影响，给出恰当评价。"
        )
    elif actual_duration < 2100:
        score_cap = 35
        duration_note = (
            f"⚠ 注意：本次路演实际时长约 {duration_minutes:.0f} 分钟，"
            f"低于比赛要求的 {expected_minutes:.0f} 分钟，评分将受限。"
        )

    return {
        "skip_llm": skip_llm,
        "score_cap": score_cap,
        "score_floor": None,
        "duration_note": duration_note,
    }


def _save_progress(
    meeting_id: str,
    step: str,
    label: str,
    step_num: int = 0,
    total: int = 0,
    progress_percent: int | None = None
):
    """保存当前进度步骤（供前端轮询）"""
    progress_dir = os.path.join(settings.UPLOAD_DIR, "results")
    os.makedirs(progress_dir, exist_ok=True)
    step_progress = {
        "converting": 8,
        "asr": 18,
        "speech": 30,
        "video_analysis": 40,
        "fusion": 60,
        "llm": 72,
        "profile": 84,
        "report": 94,
    }
    if progress_percent is None:
        progress_percent = step_progress.get(step, 0)
        if not progress_percent and total:
            progress_percent = min(96, max(3, round((float(step_num) / float(total)) * 100)))
    progress_percent = min(99, max(0, int(progress_percent)))
    progress = {
        'step': step,
        'label': label,
        'step_num': step_num,
        'total_steps': total,
        'progress_percent': progress_percent,
        'updated_at': datetime.now().isoformat()
    }
    path = os.path.join(progress_dir, f"progress_{meeting_id}.json")
    temporary_path = f"{path}.tmp-{os.getpid()}-{threading.get_ident()}"
    with _PROGRESS_WRITE_LOCK:
        try:
            with open(temporary_path, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False)
            os.replace(temporary_path, path)
        finally:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)


def _remove_progress(meeting_id: str):
    """清理进度文件"""
    path = os.path.join(settings.UPLOAD_DIR, "results", f"progress_{meeting_id}.json")
    try:
        os.remove(path)
    except:
        pass


def _is_video_file(file_path: str) -> bool:
    """判断文件是否包含视频轨"""
    video_exts = {'.mp4', '.mkv', '.avi', '.mov'}  # 排除 .webm（可能是纯音频）
    ext = os.path.splitext(file_path)[1].lower()
    if ext in video_exts:
        return True
    # 对于 webm 等可能混合格式的文件，用 ffprobe 检测
    import subprocess
    cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
           '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return 'video' in result.stdout.lower()


def _read_session(session_id: str) -> dict:
    if not session_id:
        return {}
    path = os.path.join(settings.UPLOAD_DIR, "sessions", f"session_{session_id}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"读取评分会话失败 session={session_id}: {e}")
        return {}


def _load_realtime_transcript(session_id: str, expected_duration: float = 0) -> tuple[dict | None, dict]:
    """读取实时转写稿；质量达标时返回标准 asr_result，否则返回 None。"""
    quality = {
        "source": "realtime",
        "usable": False,
        "reason": "missing_session",
        "segment_count": 0,
        "coverage": 0,
        "transcript_status": ""
    }
    if not session_id:
        return None, quality

    session = _read_session(session_id)
    quality["transcript_status"] = session.get("transcript_status", "")
    if session.get("transcript_status") == "failed":
        quality["reason"] = "transcript_failed"
        return None, quality

    transcript_path = os.path.join(settings.UPLOAD_DIR, "sessions", f"transcript_{session_id}.jsonl")
    if not os.path.exists(transcript_path):
        quality["reason"] = "missing_transcript"
        return None, quality

    segments = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("type") != "transcript" or not event.get("is_final"):
                    continue
                text = (event.get("text") or "").strip()
                if not text:
                    continue
                segments.append({
                    "text": text,
                    "start": float(event.get("start") or 0),
                    "end": float(event.get("end") or 0),
                    "confidence": 0.92,
                    "speaker": "SPEAKER_0",
                    "source": "realtime",
                    "words": event.get("words", [])
                })
    except Exception as e:
        quality["reason"] = f"read_error:{e}"
        return None, quality

    segments.sort(key=lambda item: (item.get("start", 0), item.get("end", 0)))
    if not segments:
        quality["reason"] = "empty_transcript"
        return None, quality

    duration = max(seg.get("end", 0) for seg in segments)
    quality["segment_count"] = len(segments)
    quality["duration"] = duration
    if expected_duration > 0:
        quality["coverage"] = min(1, duration / expected_duration)
    else:
        quality["coverage"] = 1

    min_segments = 3
    min_coverage = 0.8 if expected_duration >= 600 else 0.5
    if len(segments) < min_segments:
        quality["reason"] = "too_few_segments"
        return None, quality
    if expected_duration > 0 and quality["coverage"] < min_coverage:
        quality["reason"] = "low_coverage"
        return None, quality

    quality["usable"] = True
    quality["reason"] = "ok"
    speakers = sorted(list(set(seg.get("speaker", "SPEAKER_0") for seg in segments)))
    return {
        "transcript": " ".join(seg["text"] for seg in segments),
        "segments": segments,
        "duration": duration or expected_duration,
        "speakers": speakers,
        "request_id": f"realtime:{session_id}",
        "source": "realtime",
        "quality": quality
    }, quality


def _run_asr_with_realtime_preference(wav_path: str, duration: float, project_info: dict, meeting_id: str) -> dict:
    session_id = (project_info or {}).get("session_id")
    realtime_result, quality = _load_realtime_transcript(session_id, duration)
    if realtime_result:
        logger.info(
            f"[{meeting_id}] 使用实时转写稿: segments={quality['segment_count']}, "
            f"coverage={quality['coverage']:.2f}"
        )
        return realtime_result

    logger.info(
        f"[{meeting_id}] 实时转写不可用，回退完整文件 ASR: "
        f"reason={quality.get('reason')}, session={session_id or '-'}"
    )
    if duration > 300:
        asr_result = asr_service.transcribe_long_audio(wav_path)
    else:
        asr_result = asr_service.transcribe_audio(wav_path)
    asr_result["source"] = "file"
    asr_result["realtime_quality"] = quality
    return asr_result


def _run_cloud_complete_recording_asr(
    wav_path: str,
    duration: float,
    project_info: dict | None = None,
) -> dict:
    """Transcribe the complete local recording through the provider's stream API.

    The WAV bytes are sent by the provider SDK/WebSocket client. No public URL or
    object-storage hop is part of this boundary, and partial realtime text is not
    authoritative for the terminal report.
    Same video sha256 reuses the stored transcript body, not speaker labels.
    """
    from app.services.asr_transcript_cache import get_or_transcribe

    def _transcribe() -> dict:
        if duration > 300:
            result = asr_service.transcribe_long_audio(wav_path)
        else:
            result = asr_service.transcribe_audio(wav_path)
        result["source"] = "cloud_streaming_complete_recording"
        return result

    info = dict(project_info or {})
    video_path = info.get("video_path") or info.get("videoFilePath")
    result = get_or_transcribe(project_info=info, video_path=video_path, transcribe=_transcribe)
    if not result.get("source"):
        result["source"] = "cloud_streaming_complete_recording"
    return result


def _build_local_speaker_diarizer() -> LocalSpeakerDiarizer:
    return LocalSpeakerDiarizer(
        segmentation_model=settings.LOCAL_DIARIZATION_SEGMENTATION_MODEL,
        embedding_model=settings.LOCAL_DIARIZATION_EMBEDDING_MODEL,
        cluster_threshold=settings.LOCAL_DIARIZATION_CLUSTER_THRESHOLD,
        max_detected_speakers=settings.LOCAL_DIARIZATION_MAX_DETECTED_SPEAKERS,
        minimum_cluster_duration_seconds=(
            settings.LOCAL_DIARIZATION_MIN_CLUSTER_DURATION_SECONDS
        ),
        chunk_seconds=settings.LOCAL_DIARIZATION_CHUNK_SECONDS,
        chunk_overlap_seconds=settings.LOCAL_DIARIZATION_CHUNK_OVERLAP_SECONDS,
        full_pass_max_seconds=settings.LOCAL_DIARIZATION_FULL_PASS_MAX_SECONDS,
    )


def _run_local_speaker_diarization(
    wav_path: str,
    *,
    speaker_count_hint: int | None,
) -> dict:
    """Run local diarization; optionally isolate native sherpa crashes.

    Isolation protects the pipeline process. Quality is never lowered: failures
    propagate instead of returning empty speaker evidence.
    """
    import json
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    acquired = _LOCAL_DIARIZATION_CAPACITY.acquire(
        timeout=float(settings.LOCAL_DIARIZATION_TIMEOUT_SECONDS)
    )
    if not acquired:
        raise LocalDiarizationError("local_diarization_capacity_timeout")
    try:
        if not settings.LOCAL_DIARIZATION_ISOLATED_PROCESS:
            return _build_local_speaker_diarizer().diarize(
                wav_path, speaker_count_hint=speaker_count_hint
            )

        work = Path(tempfile.mkdtemp(prefix="orep-diar-"))
        out_path = work / "diar.json"
        script = f"""
import json
from app.services.media_evidence.local_diarization import LocalSpeakerDiarizer
from app.config import settings

def _progress(stage, current, total):
    print(f"diarization_progress {{stage}} {{current}}/{{total}}", flush=True)

d = LocalSpeakerDiarizer(
    segmentation_model=settings.LOCAL_DIARIZATION_SEGMENTATION_MODEL,
    embedding_model=settings.LOCAL_DIARIZATION_EMBEDDING_MODEL,
    cluster_threshold=settings.LOCAL_DIARIZATION_CLUSTER_THRESHOLD,
    max_detected_speakers=settings.LOCAL_DIARIZATION_MAX_DETECTED_SPEAKERS,
    minimum_cluster_duration_seconds=settings.LOCAL_DIARIZATION_MIN_CLUSTER_DURATION_SECONDS,
    chunk_seconds=settings.LOCAL_DIARIZATION_CHUNK_SECONDS,
    chunk_overlap_seconds=settings.LOCAL_DIARIZATION_CHUNK_OVERLAP_SECONDS,
    full_pass_max_seconds=settings.LOCAL_DIARIZATION_FULL_PASS_MAX_SECONDS,
    progress_callback=_progress,
)
hint = {speaker_count_hint!r}
result = d.diarize({str(wav_path)!r}, speaker_count_hint=hint)
open({str(out_path)!r}, "w", encoding="utf-8").write(json.dumps(result, ensure_ascii=False))
print(
    "diarization_ok",
    result.get("diarizationStatus"),
    result.get("source"),
    len(result.get("turns") or []),
    result.get("chunkCount"),
    flush=True,
)
"""
        timeout = max(60, int(settings.LOCAL_DIARIZATION_TIMEOUT_SECONDS))
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(Path(__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        if completed.stdout:
            logger.info("diarization child stdout: %s", completed.stdout.strip()[-800:])
        if completed.stderr:
            logger.warning(
                "diarization child stderr: %s", completed.stderr.strip()[-800:]
            )
        if completed.returncode != 0:
            raise LocalDiarizationError(
                f"local_diarization_process_crashed:{completed.returncode}"
            )
        if not out_path.is_file():
            raise LocalDiarizationError("local_diarization_process_no_result")
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise LocalDiarizationError("local_diarization_process_invalid_result")
        return payload
    except subprocess.TimeoutExpired as exc:
        raise LocalDiarizationError("local_diarization_timeout") from exc
    finally:
        _LOCAL_DIARIZATION_CAPACITY.release()


def _build_local_active_speaker_client() -> LocalLrAsdClient:
    client = LocalLrAsdClient(
        python_executable=settings.LOCAL_ACTIVE_SPEAKER_PYTHON,
        worker_script=settings.LOCAL_ACTIVE_SPEAKER_WORKER,
        model_repository=settings.LOCAL_ACTIVE_SPEAKER_REPOSITORY,
        model_weight=settings.LOCAL_ACTIVE_SPEAKER_WEIGHT,
        yunet_model=settings.LOCAL_ACTIVE_SPEAKER_YUNET_MODEL,
        sface_model=settings.LOCAL_ACTIVE_SPEAKER_SFACE_MODEL,
        timeout_seconds=settings.LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS,
        global_identity_threshold=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_THRESHOLD
        ),
        global_identity_stable_threshold=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_STABLE_THRESHOLD
        ),
        global_identity_minimum_detections=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_DETECTIONS
        ),
        global_identity_minimum_visibility=(
            settings.LOCAL_ACTIVE_SPEAKER_GLOBAL_IDENTITY_MINIMUM_VISIBILITY
        ),
    )
    if settings.LOCAL_ACTIVE_SPEAKER_PERSISTENT_WORKERS_ENABLED:
        client.set_persistent_transport(_persistent_lr_asd_transport())
    return client


def _run_local_active_speaker(video_path: str, wav_path: str) -> dict:
    acquired = _LOCAL_ACTIVE_SPEAKER_CAPACITY.acquire(
        timeout=float(settings.LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS)
    )
    if not acquired:
        raise LocalLrAsdError("lr_asd_capacity_timeout")
    try:
        return _build_local_active_speaker_client().analyze(video_path, wav_path)
    finally:
        _LOCAL_ACTIVE_SPEAKER_CAPACITY.release()


def _run_optional_local_active_speaker(video_path: str, wav_path: str) -> dict:
    try:
        return _run_local_active_speaker(video_path, wav_path)
    except LocalLrAsdError as exc:
        if settings.LOCAL_ACTIVE_SPEAKER_REQUIRED:
            raise
        logger.warning("LR-ASD 证据不可用，保留纯音频人物结果: %s", exc)
        return {
            "contractVersion": "lr-asd-evidence-v1",
            "status": "failed",
            "source": "local_lr_asd",
            "reason": "active_speaker_worker_failed",
            "failureCode": str(exc),
            "faceTracks": [],
            "activeIntervals": [],
        }


def _build_local_three_d_speaker_client() -> LocalThreeDSpeakerClient:
    return LocalThreeDSpeakerClient(
        python_executable=settings.LOCAL_3D_SPEAKER_PYTHON,
        worker_script=settings.LOCAL_3D_SPEAKER_WORKER,
        runtime_dir=settings.LOCAL_3D_SPEAKER_RUNTIME_DIR,
        timeout_seconds=settings.LOCAL_3D_SPEAKER_TIMEOUT_SECONDS,
    )


def _run_local_three_d_speaker(
    video_path: str,
    wav_path: str,
    duration: float,
) -> dict:
    acquired = _LOCAL_3D_SPEAKER_CAPACITY.acquire(
        timeout=float(settings.LOCAL_3D_SPEAKER_TIMEOUT_SECONDS)
    )
    if not acquired:
        raise LocalThreeDSpeakerError("3d_speaker_capacity_timeout")
    try:
        return _build_local_three_d_speaker_client().analyze(
            video_path,
            wav_path,
            duration_ms=max(1, int(round(float(duration) * 1000))),
        )
    finally:
        _LOCAL_3D_SPEAKER_CAPACITY.release()


def _run_optional_three_d_speaker(
    video_path: str,
    wav_path: str,
    duration: float,
) -> dict:
    try:
        return _run_local_three_d_speaker(video_path, wav_path, duration)
    except LocalThreeDSpeakerError as exc:
        if settings.LOCAL_3D_SPEAKER_REQUIRED:
            raise
        logger.warning("3D-Speaker 联合人物证据不可用，转写将保持待确认: %s", exc)
        return {
            "contractVersion": "3d-speaker-local-v1",
            "provider": "local_3d_speaker",
            "status": "evidence_incomplete",
            "turns": [],
            "diagnostics": {"failureCode": str(exc)},
        }


def _build_and_save_speaker_attribution_shadow(
    *,
    meeting_id: str,
    duration: float,
    project_info: dict,
    asr_result: dict,
    diarization_result: dict,
    active_speaker_result: dict | None,
) -> dict:
    configured_slots = (project_info or {}).get(
        "expected_contestant_count", (project_info or {}).get("team_size", 4)
    )
    try:
        contestant_slots = max(0, min(4, int(configured_slots)))
    except (TypeError, ValueError):
        contestant_slots = 4
    snapshot = build_shadow_attribution(
        session_id=str(meeting_id),
        duration_ms=max(0, int(round(float(duration) * 1000))),
        contestant_slots=contestant_slots,
        asr_result=asr_result,
        diarization_result=diarization_result,
        active_speaker_result=active_speaker_result,
        media_clock=(project_info or {}).get("media_clock"),
    )
    receipt = save_shadow_attribution(settings.UPLOAD_DIR, str(meeting_id), snapshot)
    return {**receipt, "snapshot": snapshot}


def _next_speaker_attribution_revision(meeting_id: str) -> int:
    result_dir = os.path.join(
        settings.UPLOAD_DIR,
        "results",
        "speaker-attribution",
        str(meeting_id),
    )
    highest = 0
    if os.path.isdir(result_dir):
        for name in os.listdir(result_dir):
            if name.startswith("revision-") and name.endswith(".json"):
                try:
                    highest = max(highest, int(name[9:-5]))
                except ValueError:
                    continue
    return highest + 1


def _build_and_save_final_speaker_attribution(
    *,
    meeting_id: str,
    duration: float,
    project_info: dict,
    asr_result: dict,
    three_d_speaker_result: dict,
) -> dict:
    configured_slots = (project_info or {}).get(
        "expected_contestant_count", (project_info or {}).get("team_size", 4)
    )
    try:
        contestant_slots = max(0, min(4, int(configured_slots)))
    except (TypeError, ValueError):
        contestant_slots = 4
    revision = _next_speaker_attribution_revision(str(meeting_id))
    snapshot = build_final_speaker_attribution(
        session_id=str(meeting_id),
        duration_ms=max(0, int(round(float(duration) * 1000))),
        revision=revision,
        asr_result=asr_result,
        three_d_speaker_result=three_d_speaker_result,
        contestant_slots=contestant_slots,
        media_clock=(project_info or {}).get("media_clock"),
    )
    receipt = save_shadow_attribution(settings.UPLOAD_DIR, str(meeting_id), snapshot)
    return {**receipt, "snapshot": snapshot}


def _run_authoritative_asr(
    wav_path: str,
    duration: float,
    project_info: dict,
    meeting_id: str,
    *,
    video_path: str | None = None,
) -> dict:
    """Build terminal text and speaker evidence without an OSS dependency."""
    if not settings.LOCAL_SPEAKER_DIARIZATION_ENABLED:
        return _run_cloud_complete_recording_asr(wav_path, duration, project_info)

    # Team size is not speaker count: judges, silent members and hand-offs make
    # forcing it harmful. Only pass a deliberately supplied acoustic hint.
    speaker_count_hint = (project_info or {}).get("speaker_count_hint")
    branches = {
        "cloud_asr": lambda: _run_cloud_complete_recording_asr(wav_path, duration, project_info),
        "local_diarization": lambda: _run_local_speaker_diarization(
            wav_path,
            speaker_count_hint=speaker_count_hint,
        ),
    }
    # Match outer primary-evidence budget so long cloud ASR is not killed first.
    timeout_seconds = max(
        float(settings.LOCAL_DIARIZATION_TIMEOUT_SECONDS),
        _primary_evidence_timeout_seconds(duration),
    )
    if video_path and settings.LOCAL_3D_SPEAKER_ENABLED:
        branches["three_d_speaker"] = lambda: _run_optional_three_d_speaker(
            video_path, wav_path, duration
        )
        timeout_seconds = max(
            timeout_seconds, settings.LOCAL_3D_SPEAKER_TIMEOUT_SECONDS
        )
    elif video_path and settings.LOCAL_ACTIVE_SPEAKER_ENABLED:
        branches["local_active_speaker"] = lambda: _run_optional_local_active_speaker(
            video_path, wav_path
        )
        timeout_seconds = max(
            timeout_seconds, settings.LOCAL_ACTIVE_SPEAKER_TIMEOUT_SECONDS
        )
    # Sequential audio evidence first: cloud ASR text is authoritative for words;
    # local diarization is required for speaker labels when enabled. Video models
    # (3D-Speaker / LR-ASD) remain optional unless *_REQUIRED is set.
    # Isolation (subprocess + job runner) contains native crashes; we never
    # silently publish pure-cloud ASR without diarization.
    outputs = {}
    for key, operation in branches.items():
        logger.info("authoritative_asr branch start: %s", key)
        try:
            outputs[key] = operation()
            logger.info("authoritative_asr branch done: %s", key)
        except Exception as exc:
            if key in {"cloud_asr", "local_diarization"}:
                raise
            logger.warning(
                "authoritative_asr optional branch failed key=%s err=%s:%s",
                key,
                type(exc).__name__,
                exc,
            )
            if key in {"three_d_speaker", "local_active_speaker"}:
                outputs[key] = None
            else:
                raise

    cloud_asr = outputs["cloud_asr"]
    raw_diarization_result = outputs["local_diarization"]
    diarization_result = raw_diarization_result
    active_speaker_result = outputs.get("local_active_speaker")
    if active_speaker_result is not None:
        try:
            diarization_result = fuse_active_speaker_evidence(
                diarization_result,
                active_speaker_result,
                minimum_active_probability=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_ACTIVE_PROBABILITY
                ),
                minimum_visible_probability=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_VISIBLE_PROBABILITY
                ),
                minimum_temporal_coverage=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_TEMPORAL_COVERAGE
                ),
                minimum_winner_dominance=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_WINNER_DOMINANCE
                ),
                minimum_identity_confidence=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_IDENTITY_CONFIDENCE
                ),
                minimum_cluster_vote_dominance=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_VOTE_DOMINANCE
                ),
                minimum_cluster_supporting_turns=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORTING_TURNS
                ),
                minimum_cluster_support_ms=(
                    settings.LOCAL_ACTIVE_SPEAKER_MIN_CLUSTER_SUPPORT_MS
                ),
            )
            if active_speaker_result.get("failureCode"):
                diarization_result["activeSpeakerFailureCode"] = active_speaker_result[
                    "failureCode"
                ]
        except Exception as exc:
            logger.warning("active_speaker fusion skipped: %s", exc)
    result = reconcile_asr_with_diarization(cloud_asr, diarization_result)
    three_d_speaker_result = outputs.get("three_d_speaker")
    if (
        settings.SPEAKER_ATTRIBUTION_ENABLED
        and three_d_speaker_result is not None
    ):
        try:
            receipt = _build_and_save_final_speaker_attribution(
                meeting_id=meeting_id,
                duration=duration,
                project_info=project_info or {},
                asr_result=outputs["cloud_asr"],
                three_d_speaker_result=three_d_speaker_result,
            )
            result["speakerAttributionStatus"] = "completed"
            result["speakerAttributionRevision"] = receipt["revision"]
            result["speakerAttributionHash"] = receipt["snapshotHash"]
            result["speakerAttributionProviderStatus"] = three_d_speaker_result[
                "status"
            ]
            if (
                settings.LOCAL_3D_SPEAKER_PUBLICATION_ENABLED
                and
                not settings.SPEAKER_ATTRIBUTION_SHADOW_MODE
                and isinstance(receipt.get("snapshot"), dict)
            ):
                result["speakerAttribution"] = receipt["snapshot"]
        except Exception as error:
            logger.exception("[%s] 3D-Speaker 最终人物归属快照失败", meeting_id)
            result["speakerAttributionStatus"] = "failed"
            result["speakerAttributionFailureCode"] = type(error).__name__
    elif (
        settings.SPEAKER_ATTRIBUTION_ENABLED
        and settings.SPEAKER_ATTRIBUTION_SHADOW_MODE
    ):
        try:
            receipt = _build_and_save_speaker_attribution_shadow(
                meeting_id=meeting_id,
                duration=duration,
                project_info=project_info or {},
                asr_result=outputs["cloud_asr"],
                diarization_result=diarization_result,
                active_speaker_result=active_speaker_result,
            )
            result["speakerAttributionShadowStatus"] = "completed"
            result["speakerAttributionShadowRevision"] = receipt["revision"]
            result["speakerAttributionShadowHash"] = receipt["snapshotHash"]
            if isinstance(receipt.get("snapshot"), dict):
                result["speakerAttribution"] = receipt["snapshot"]
        except Exception as error:
            logger.exception("[%s] 人物归属影子快照失败", meeting_id)
            result["speakerAttributionShadowStatus"] = "failed"
            result["speakerAttributionShadowFailureCode"] = type(error).__name__
    return result


def _primary_evidence_timeout_seconds(duration: float) -> float:
    """Scale the hard deadline for long recordings.

    Cloud ASR is chunked at 300s with limited concurrency; a 50+ minute roadshow
    routinely needs more than the 15-minute floor. Observed prod: ~18.5 min for
    3271s audio before timeout aborted a still-running job.
    """
    base = float(settings.PRIMARY_EVIDENCE_TIMEOUT_SECONDS)
    duration = max(0.0, float(duration or 0))
    chunks = max(1, int((duration + 299) // 300))
    workers = max(1, int(settings.ASR_CHUNK_MAX_WORKERS))
    rounds = max(1, (chunks + workers - 1) // workers)
    # ~120s wall per concurrent ASR round + local diarization/visual headroom
    scaled = rounds * 120.0 + 900.0
    return max(base, scaled)


def _run_primary_evidence_branches(
    *,
    audio_operation,
    video_operation,
    timeout_seconds: float,
) -> dict:
    return _run_terminal_media_branches(
        {"audio": audio_operation, "video": video_operation},
        max_workers=2,
        timeout_seconds=timeout_seconds,
    )


def _run_terminal_media_branches(
    branches: dict,
    *,
    max_workers: int,
    timeout_seconds: float,
) -> dict:
    """Run independent terminal media work concurrently with one hard deadline."""
    if not branches:
        raise ValueError("branches_required")
    if timeout_seconds <= 0:
        raise ValueError("positive_timeout_required")
    branch_order = list(branches)
    executor = ThreadPoolExecutor(
        max_workers=max(1, min(int(max_workers), len(branch_order))),
        thread_name_prefix="terminal-media",
    )
    futures = {key: executor.submit(branches[key]) for key in branch_order}
    try:
        _, unfinished = wait(futures.values(), timeout=float(timeout_seconds))
        if unfinished:
            keys = [key for key in branch_order if futures[key] in unfinished]
            for future in unfinished:
                future.cancel()
            raise RuntimeError(f"branch_timeout:{','.join(keys)}")
        outputs = {}
        for key in branch_order:
            try:
                outputs[key] = futures[key].result()
            except Exception as exc:
                raise RuntimeError(f"branch_failed:{key}:{type(exc).__name__}:{exc}") from exc
        return outputs
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _load_session_visual_frame_events(session_id: str) -> list[dict]:
    if not session_id:
        return []
    index_path = os.path.join(settings.UPLOAD_DIR, "sessions", f"frames_{session_id}.jsonl")
    if not os.path.exists(index_path):
        return []

    frames = []
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                image_path = item.get("image_path")
                if image_path and os.path.exists(image_path):
                    frames.append(item)
    except Exception as e:
        logger.warning(f"读取视频关键帧索引失败 session={session_id}: {e}")
        return []

    frames.sort(key=lambda item: float(item.get("timestamp") or 0))
    return frames


def _run_video_analysis_with_session_preference(
    video_path: str,
    project_info: dict,
    meeting_id: str,
    interval_sec: int
) -> dict:
    session_id = (project_info or {}).get("session_id")
    session_frames = _load_session_visual_frame_events(session_id)
    selected_frames = select_visual_frame_events(
        session_frames,
        target_interval=interval_sec,
        max_frames=settings.VIDEO_ANALYSIS_MAX_FRAMES,
        scene_diff_threshold=settings.VIDEO_SCENE_DIFF_THRESHOLD
    )

    def save_video_batch_progress(done: int, total: int):
        if not total:
            return
        percent = 40 + round((done / total) * 18)
        _save_progress(
            meeting_id,
            "video_analysis",
            f"视频分析中 {done}/{total} 帧",
            3.5,
            8,
            progress_percent=percent
        )

    if len(selected_frames) >= 3:
        logger.info(
            f"[{meeting_id}] 使用会中采集关键帧做视频分析: "
            f"selected={len(selected_frames)}, captured={len(session_frames)}"
        )
        analysis = video_analysis_service.run_analysis_on_frames(
            selected_frames,
            interval_sec,
            progress_callback=save_video_batch_progress
        )
        analysis["captured_frame_count"] = len(session_frames)
        analysis["selected_frame_count"] = len(selected_frames)
        analysis["selection_strategy"] = visual_frame_selection_summary(
            len(session_frames),
            selected_frames,
            interval_sec,
            settings.VIDEO_ANALYSIS_MAX_FRAMES,
            settings.VIDEO_SCENE_DIFF_THRESHOLD,
        )
        analysis["source"] = "session_capture"
        return analysis

    logger.info(
        f"[{meeting_id}] 会中关键帧不足，回退完整视频抽帧: "
        f"selected={len(selected_frames)}, captured={len(session_frames)}, session={session_id or '-'}"
    )
    analysis = video_analysis_service.run_analysis(
        video_path,
        interval_sec=interval_sec,
        progress_callback=save_video_batch_progress
    )
    analysis["source"] = "video_file"
    return analysis




async def run_scoring_pipeline(
    audio_file_path: str,
    meeting_id: str,
    project_info: dict,
    callback_url: str = None,
    provider: str = "deepseek",
    compare_mode: bool = False,
    ppt_recognition: bool = False,
    start_jury_review: bool = True,
) -> dict:
    """
    执行完整评分流水线（支持音频/视频输入）

    参数：
    - audio_file_path: 上传的音频/视频文件路径
    - meeting_id: 会议 ID
    - project_info: 项目信息 {project_name, track, team_size, has_screen_share, audio_source_count}
    - callback_url: 可选的结果回调 URL
    - provider: LLM 提供商 "deepseek"
    - compare_mode: 是否启用双模型对比评分
    - ppt_recognition: 是否启用PPT内容识别（双源模式才开启）
    - start_jury_review: 是否在本流水线内启动评审团；上传会话需在权威规则分生成后另行启动

    返回：评分结果字典
    """
    start_time = datetime.now()
    has_video = _is_video_file(audio_file_path)

    # 确定总步数
    total_steps = 9 if has_video else 8  # +分发言人分析；视频模式含视频分析+融合

    result = {
        'meeting_id': meeting_id,
        'status': 'processing',
        'started_at': start_time.isoformat(),
        'has_video': has_video,
        'project_info': {
            'project_name': project_info.get('project_name', '未命名项目'),
            'track': project_info.get('track', '未指定赛道'),
            'team_size': project_info.get('team_size', 4),
            'has_screen_share': project_info.get('has_screen_share', False),
            'audio_source_count': project_info.get('audio_source_count', 0),
        },
    }

    try:
        # ========== Step 1: 音频转码 ==========
        step = 1
        logger.info(f"[{meeting_id}] Step {step}/{total_steps}: 音频转码")
        _save_progress(meeting_id, 'converting', '音频转码中...', step, total_steps)
        wav_path = audio_service.convert_to_wav(audio_file_path)

        audio_info = audio_service.get_audio_info(wav_path)
        result['audio_info'] = audio_info
        logger.info(f"[{meeting_id}] 音频信息: {audio_info.get('duration', 0):.1f}s")

        duration = audio_info.get('duration', 0)
        video_analysis = None
        fused_data = None

        def run_audio_evidence():
            logger.info(f"[{meeting_id}] 音频证据分支: 终版 ASR + 语音质量")
            _save_progress(meeting_id, 'asr', '语音识别中...', 2, total_steps)
            branch_asr = _run_authoritative_asr(
                wav_path,
                duration,
                project_info,
                meeting_id,
                video_path=audio_file_path if has_video else None,
            )
            branch_speech = speech_analysis_service.analyze_speech_quality(branch_asr, wav_path)
            return {"asr": branch_asr, "speech_quality": branch_speech}

        if has_video:
            def run_video_evidence():
                logger.info(f"[{meeting_id}] 视频证据分支: 视觉分析")
                _save_progress(meeting_id, 'video_analysis', '视频分析中...', 3.5, total_steps)
                branch_video = _run_video_analysis_with_session_preference(
                    audio_file_path,
                    project_info,
                    meeting_id,
                    interval_sec=settings.VIDEO_FRAME_INTERVAL,
                )
                validate_video_analysis_for_scoring(branch_video)
                return branch_video

            # Sequential on purpose: concurrent audio+video under uvicorn --workers N
            # repeatedly kills the worker mid-ASR ("Child process died") and leaves
            # the session stuck at asr_processing ~18% with no failure callback.
            evidence_timeout = _primary_evidence_timeout_seconds(duration)
            logger.info(
                f"[{meeting_id}] 主证据顺序执行 audio→video "
                f"(budget={evidence_timeout:.0f}s, audio_duration={duration:.0f}s)"
            )
            audio_output = run_audio_evidence()
            video_analysis = run_video_evidence()
        else:
            audio_output = run_audio_evidence()

        asr_result = audio_output["asr"]
        speech_quality = audio_output["speech_quality"]
        asr_segments = asr_result.get('segments', [])
        result['asr'] = {
            'transcript': asr_result.get('transcript', ''),
            'segment_count': len(asr_segments),
            'segments': asr_segments,
            'duration': asr_result.get('duration', 0),
            'speakers': asr_result.get('speakers', []),
            'source': asr_result.get('source', 'file'),
            'quality': asr_result.get('quality') or asr_result.get('realtime_quality')
        }
        if isinstance(asr_result.get('speakerAttribution'), dict):
            result['asr']['speakerAttribution'] = asr_result['speakerAttribution']
        logger.info(f"[{meeting_id}] ASR 完成: {len(asr_segments)} 段")
        result['speech_quality'] = {
            'speech_rate': speech_quality.get('speech_rate', {}),
            'pauses': speech_quality.get('pauses', {}),
            'fillers': speech_quality.get('fillers', {}),
            'prosody': speech_quality.get('prosody', {'enabled': False}),
            'overall_rating': speech_quality.get('overall_rating', {}),
            'duration': speech_quality.get('duration', 0),
        }
        logger.info(f"[{meeting_id}] 语音分析完成")
        if has_video:
            result['video_analysis'] = persistable_video_analysis(video_analysis)
            logger.info(f"[{meeting_id}] 视频分析完成: {video_analysis['frame_count']}帧, "
                        f"来源={video_analysis.get('source', 'video_file')}, "
                        f"视觉综合={video_analysis['aggregates'].get('avg_visual_composite', 0)}")

        # ========== Step 3.6: 音视频融合（仅视频模式） ==========
        if has_video and video_analysis:
            step_f = 3.6
            logger.info(f"[{meeting_id}] Step 3.6/{total_steps}: 音视频融合")
            _save_progress(meeting_id, 'fusion', '音视频融合中...', step_f, total_steps)
            try:
                fused_data = fusion_service.run_fusion(
                    asr_segments=asr_segments,
                    video_per_frame=video_analysis['per_frame'],
                    window_sec=settings.VIDEO_FRAME_INTERVAL
                )
                validate_fusion_for_scoring(fused_data)
                result['fusion'] = persistable_fusion(fused_data)
                logger.info(f"[{meeting_id}] 融合完成: 均分={fused_data['summary']['fusion_avg']}, "
                           f"矛盾点={fused_data['summary']['contradiction_count']}")
            except Exception as e:
                logger.error(f"[{meeting_id}] 融合失败: {e}")
                result['fusion'] = {'error': str(e)}
                raise

        # 阶段 1 影子路径：只写证据快照，不向官方评分传入任何新字段。
        if has_video:
            _write_evidence_shadow_if_enabled(
                meeting_id=meeting_id,
                asr_result=asr_result,
                speech_quality=speech_quality,
                video_analysis=video_analysis,
                fusion=fused_data,
            )

        # ========== Step 4: 大模型内容评分（五维） ==========
        step = 4
        actual_duration = result.get('audio_info', {}).get('duration', 0)
        expected_duration = 3600  # 1 小时比赛

        # 时长不足处理机制（后台机制，不体现在报告中）
        duration_note = None
        score_cap = None
        score_floor = None
        skip_llm = False

        duration_adjustment = determine_duration_adjustment(actual_duration, expected_duration)
        duration_note = duration_adjustment["duration_note"]
        score_cap = duration_adjustment["score_cap"]
        score_floor = duration_adjustment["score_floor"]
        skip_llm = duration_adjustment["skip_llm"]

        if skip_llm:  # 不足 10 分钟 — 直接 0 分，跳过 LLM
            logger.info(f"[{meeting_id}] 时长严重不足 ({actual_duration:.0f}s < 600s)，跳过LLM评分，得0分")
        elif score_cap == 20:  # 10-30 分钟 — 正常评，最高 20 分封顶
            logger.info(f"[{meeting_id}] 时长不足 ({actual_duration:.0f}s)，LLM评分封顶20分")
        elif score_cap == 35:  # 30-35 分钟 — 最高 35 分封顶
            logger.info(f"[{meeting_id}] 时长不足 ({actual_duration:.0f}s)，LLM评分封顶35分")
        # 35 分钟以上 — 正常评分，无限制

        if skip_llm:
            dim_names = ['技术技能水平', '职业素养', '创新创意', '应用价值', '团队合作']
            result['ai_score'] = {
                'overall_score': 0,
                'dimensions': {name: {'name': name, 'score': 0, 'max_score': 20, 'items': []} for name in dim_names},
                'highlights': ['路演时长严重不足，无法进行有效评分'],
                'critical_issues': [f'路演实际时长 {actual_duration:.0f} 秒，远低于比赛要求的 {expected_duration} 秒'],
                'improvement_priorities': ['建议按照完整比赛流程进行路演展示，确保覆盖所有评审维度'],
                'model': 'duration_adjustment',
                'provider': 'system',
            }
        else:
            logger.info(f"[{meeting_id}] Step {step}/{total_steps}: 大模型五维评分")
            _save_progress(meeting_id, 'llm', 'AI五维评分中...', step, total_steps)

            # 将融合数据注入评分上下文（含屏幕内容识别结果）
            fusion_context = None
            if fused_data:
                fusion_context = {
                    'trends': fused_data['trends'],
                    'contradictions': fused_data['contradictions'],
                    'visual_aggregates': video_analysis['aggregates'] if video_analysis else {},
                    'audio_windows': fused_data.get('audio_windows', []),
                    'timeline': fused_data.get('timeline', []),
                    'screen_content_summary': fused_data.get('screen_content_summary', {}),
                }

            # 强制使用 DeepSeek（MiniMax 已禁用）
            provider = 'deepseek'
            result = _score_with_rule_first(
                result=result,
                asr_result=asr_result,
                speech_quality=speech_quality,
                project_info=project_info,
                fusion_context=fusion_context,
                provider=provider,
                meeting_id=meeting_id,
                duration_note=duration_note,
                ppt_recognition=ppt_recognition,
                compare_mode=compare_mode,
            )
            if _extraction_is_incomplete(result.get("evidence_extraction")):
                return _fail_incomplete_extraction(meeting_id, result)

        # 应用时长封顶/保底
        if not skip_llm:
            orig_score = result['ai_score'].get('overall_score', 0)

            # 封顶
            if score_cap and orig_score is not None and orig_score > score_cap:
                result['ai_score']['overall_score'] = score_cap
                logger.info(f"[{meeting_id}] 时长封顶: {orig_score}分 → {score_cap}分")

            # 保底
            if score_floor and orig_score is not None and orig_score < score_floor:
                result['ai_score']['overall_score'] = score_floor
                logger.info(f"[{meeting_id}] 时长保底: {orig_score}分 → {score_floor}分")

            result = apply_calibration_to_result(result)

        if _extraction_is_incomplete(result.get("evidence_extraction")):
            return _fail_incomplete_extraction(meeting_id, result)

        logger.info(f"[{meeting_id}] 五维评分完成: {result['ai_score'].get('overall_score', 0)}分")

        # ========== Step 5: 发言人证据整理（不参与评分） ==========
        step = 5
        logger.info(f"[{meeting_id}] Step {step}/{total_steps}: 发言人证据整理")
        _save_progress(meeting_id, "speakers", "整理发言人证据中...", step, total_steps)
        speaker_evidence = build_speaker_evidence(asr_result)
        result["speaker_evidence"] = speaker_evidence
        logger.info(f"[{meeting_id}] 发言人证据整理完成: {len(speaker_evidence)} 个声纹簇")

        # ========== Step 6: 能力画像生成 ==========
        step = 6
        logger.info(f"[{meeting_id}] Step {step}/{total_steps}: 能力画像生成")
        _save_progress(meeting_id, 'profile', '生成能力画像中...', step, total_steps)

        try:
            profile_data = character_profile_service.generate_profile(
                fused_timeline=fused_data['timeline'] if fused_data else [],
                asr_segments=asr_segments,
                trends=fused_data['trends'] if fused_data else {},
                contradictions=fused_data['contradictions'] if fused_data else [],
                project_info=project_info,
                five_dim_scores=result['ai_score'],
                provider=provider if provider != "minimax" else "dashscope"
            )
            result['character_profile'] = {
                'profile_markdown': profile_data['profile_markdown'],
                'provider': profile_data['provider'],
                'sections': profile_data['sections'],
            }
            logger.info(f"[{meeting_id}] 画像生成完成")
        except Exception as e:
            logger.error(f"[{meeting_id}] 画像生成失败: {e}")
            result['character_profile'] = {'error': str(e)}

        # ========== Step 6: 汇总 ==========
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        result['status'] = 'generating_report'
        result['completed_at'] = end_time.isoformat()
        result['elapsed_seconds'] = round(elapsed, 1)
        # 从 project_info 透传是否启用评审团，供 PDF 门控（默认关闭）
        if isinstance(project_info, dict):
            result['jury_enabled'] = bool(project_info.get('jury_enabled') or project_info.get('juryEnabled'))
            if project_info.get('project_name') and not result.get('project_name'):
                result['project_name'] = project_info.get('project_name')
            if project_info.get('track') and not result.get('track'):
                result['track'] = project_info.get('track')
        else:
            result['jury_enabled'] = False

        _save_result(meeting_id, result)

        # ========== Step 8: 报告生成 ==========
        step = 8
        logger.info(f"[{meeting_id}] Step {step}/{total_steps}: 生成 PDF 报告")
        _save_progress(meeting_id, 'report', '生成PDF报告中...', step, total_steps)
        _generate_report(meeting_id, result)

        # 报告生成完毕，更新状态
        final_time = datetime.now()
        result['status'] = 'completed'
        result['completed_at'] = final_time.isoformat()
        result['total_elapsed_seconds'] = round((final_time - start_time).total_seconds(), 1)
        _save_result(meeting_id, result)
        if start_jury_review:
            _maybe_start_jury_review(meeting_id, result, project_info, provider, ppt_recognition)

        logger.info(f"[{meeting_id}] 评分流水线完成! 耗时 {result['total_elapsed_seconds']:.1f}s")
        _remove_progress(meeting_id)

        if callback_url:
            await _notify_backend(callback_url, meeting_id, result)

        _cleanup(meeting_id)
        return result

    except Exception as e:
        logger.error(f"[{meeting_id}] 流水线异常: {e}")
        logger.error(traceback.format_exc())

        result['status'] = 'failed'
        result['error'] = str(e)
        result['completed_at'] = datetime.now().isoformat()
        _save_result(meeting_id, result)

        _remove_progress(meeting_id)

        if callback_url:
            await _notify_backend(callback_url, meeting_id, result)

        return result


# ==================== 双视频源评分流水线（Mode 1: 摄像头+屏幕共享） ====================

async def run_dual_video_scoring_pipeline(
    camera_video_path: str,
    screen_video_path: str,
    audio_path: str,
    meeting_id: str,
    project_info: dict,
    callback_url: str = None,
    provider: str = "deepseek",
    compare_mode: bool = False,
    ppt_recognition: bool = False
) -> dict:
    """
    执行双视频源评分流水线（摄像头全景 + 屏幕共享）

    模式判断：
    - camera + screen + has_ppt=True → ppt_recognition=True，启用PPT内容识别
    - camera + screen + has_ppt=False → 纯屏幕共享模式，仅用音频评分
    - 只有其中一路 → 视为单源，使用 run_scoring_pipeline

    参数：
    - camera_video_path: 全景摄像头视频路径
    - screen_video_path: 屏幕共享视频路径
    - audio_path: 音频文件路径
    - ppt_recognition: 是否启用PPT识别（由前端 has_ppt 参数控制）
    """
    import copy

    start_time = datetime.now()

    result = {
        'meeting_id': meeting_id,
        'status': 'processing',
        'started_at': start_time.isoformat(),
        'recording_mode': 'dual',
        'project_info': {
            'project_name': project_info.get('project_name', '未命名项目'),
            'track': project_info.get('track', '未指定赛道'),
            'team_size': project_info.get('team_size', 4),
            'audio_source_count': project_info.get('audio_source_count', 0),
            'ppt_recognition': ppt_recognition,
        },
        'sources': {
            'camera': camera_video_path,
            'screen': screen_video_path,
            'audio': audio_path,
        }
    }

    try:
        # Step 1: 音频转码
        step = 1
        logger.info(f"[{meeting_id}] Step {step}/9: 音频转码")
        _save_progress(meeting_id, 'converting', '音频转码中...', step, 9)
        wav_path = audio_service.convert_to_wav(audio_path)
        audio_info = audio_service.get_audio_info(wav_path)
        result['audio_info'] = audio_info
        logger.info(f"[{meeting_id}] 音频信息: {audio_info.get('duration', 0):.1f}s")

        duration = audio_info.get('duration', 0)

        def run_audio_evidence():
            logger.info(f"[{meeting_id}] 音频证据分支: 终版 ASR + 语音质量")
            _save_progress(meeting_id, 'asr', '语音识别中...', 2, 9)
            branch_asr = _run_authoritative_asr(
                wav_path,
                duration,
                project_info,
                meeting_id,
                video_path=camera_video_path,
            )
            branch_speech = speech_analysis_service.analyze_speech_quality(branch_asr, wav_path)
            return {"asr": branch_asr, "speech_quality": branch_speech}

        def run_camera_evidence():
            logger.info(f"[{meeting_id}] 视频证据分支: 全景摄像头")
            branch_video = video_analysis_service.run_analysis(
                camera_video_path,
                interval_sec=settings.VIDEO_FRAME_INTERVAL,
            )
            validate_video_analysis_for_scoring(branch_video)
            return branch_video

        def run_screen_evidence():
            logger.info(f"[{meeting_id}] 视频证据分支: 屏幕共享")
            branch_video = video_analysis_service.run_analysis(
                screen_video_path,
                interval_sec=settings.VIDEO_FRAME_INTERVAL,
            )
            validate_video_analysis_for_scoring(branch_video)
            return branch_video

        _save_progress(meeting_id, 'media_evidence', '并行分析音频、全景与屏幕证据...', 2, 9)
        evidence_timeout = _primary_evidence_timeout_seconds(duration)
        logger.info(
            f"[{meeting_id}] 主证据并行超时: {evidence_timeout:.0f}s "
            f"(audio_duration={duration:.0f}s)"
        )
        branch_outputs = _run_terminal_media_branches(
            {
                "audio": run_audio_evidence,
                "camera": run_camera_evidence,
                "screen": run_screen_evidence,
            },
            max_workers=3,
            timeout_seconds=evidence_timeout,
        )
        asr_result = branch_outputs["audio"]["asr"]
        speech_quality = branch_outputs["audio"]["speech_quality"]
        camera_analysis = branch_outputs["camera"]
        screen_analysis = branch_outputs["screen"]
        asr_segments = asr_result.get('segments', [])
        result['asr'] = {
            'transcript': asr_result.get('transcript', ''),
            'segment_count': len(asr_segments),
            'segments': asr_segments,
            'duration': asr_result.get('duration', 0),
            'speakers': asr_result.get('speakers', []),
            'source': asr_result.get('source', 'file'),
            'quality': asr_result.get('quality') or asr_result.get('realtime_quality'),
        }
        if isinstance(asr_result.get('speakerAttribution'), dict):
            result['asr']['speakerAttribution'] = asr_result['speakerAttribution']
        logger.info(f"[{meeting_id}] ASR 完成: {len(asr_segments)} 段")
        result['speech_quality'] = {
            'speech_rate': speech_quality.get('speech_rate', {}),
            'pauses': speech_quality.get('pauses', {}),
            'fillers': speech_quality.get('fillers', {}),
            'prosody': speech_quality.get('prosody', {'enabled': False}),
            'overall_rating': speech_quality.get('overall_rating', {}),
            'duration': speech_quality.get('duration', 0),
        }
        logger.info(f"[{meeting_id}] 语音分析完成")
        result['video_camera_analysis'] = persistable_video_analysis(camera_analysis)
        result['video_screen_analysis'] = persistable_video_analysis(screen_analysis)
        logger.info(f"[{meeting_id}] 全景分析完成: {camera_analysis['frame_count']}帧")
        logger.info(f"[{meeting_id}] 屏幕分析完成: {screen_analysis['frame_count']}帧")

        # Step 6: 双路融合 - 全景
        camera_fused = None
        screen_fused = None
        fused_data = None

        if camera_analysis:
            step_f1 = 6
            logger.info(f"[{meeting_id}] Step {step_f1}/9: 融合 - 全景")
            _save_progress(meeting_id, 'fusion_camera', '融合全景音视频...', step_f1, 9)
            try:
                camera_fused = fusion_service.run_fusion(
                    asr_segments=asr_segments,
                    video_per_frame=camera_analysis.get('per_frame', []),
                    window_sec=settings.VIDEO_FRAME_INTERVAL
                )
                validate_fusion_for_scoring(camera_fused)
                logger.info(f"[{meeting_id}] 全景融合完成")
            except Exception as e:
                logger.error(f"[{meeting_id}] 全景融合失败: {e}")
                raise

        # Step 7: 双路融合 - 屏幕共享
        if screen_analysis:
            step_f2 = 7
            logger.info(f"[{meeting_id}] Step {step_f2}/9: 融合 - 屏幕共享")
            _save_progress(meeting_id, 'fusion_screen', '融合屏幕音视频...', step_f2, 9)
            try:
                screen_fused = fusion_service.run_fusion(
                    asr_segments=asr_segments,
                    video_per_frame=screen_analysis.get('per_frame', []),
                    window_sec=settings.VIDEO_FRAME_INTERVAL
                )
                validate_fusion_for_scoring(screen_fused)
                logger.info(f"[{meeting_id}] 屏幕融合完成")
            except Exception as e:
                logger.error(f"[{meeting_id}] 屏幕融合失败: {e}")
                raise

        # 构建融合上下文（合并两路数据）
        # screen_content_summary 主要来自屏幕共享（PPT内容）
        # visual_aggregates 主要来自全景（肢体语言/表情）
        fusion_context = None
        if camera_fused or screen_fused:
            fusion_context = {
                'trends': {},
                'contradictions': [],
                'visual_aggregates': {},
                'audio_windows': [],
                'screen_content_summary': {},
            }

            if camera_fused:
                fusion_context['trends']['camera'] = camera_fused.get('trends', {})
                fusion_context['visual_aggregates'] = camera_fused.get('summary', {})
                fusion_context['audio_windows'] = camera_fused.get('audio_windows', [])
                fusion_context['timeline'] = camera_fused.get('timeline', [])
                fusion_context['timeline_camera'] = camera_fused.get('timeline', [])
                fusion_context['contradictions'].extend(camera_fused.get('contradictions', []))

            if screen_fused:
                fusion_context['trends']['screen'] = screen_fused.get('trends', {})
                # 屏幕内容的 screen_content_summary 从 screen_fused 中获取
                fusion_context['screen_content_summary'] = screen_fused.get('screen_content_summary', {})
                fusion_context['timeline_screen'] = screen_fused.get('timeline', [])

            primary_fusion = camera_fused or screen_fused
            result['fusion'] = persistable_fusion(primary_fusion)
            if camera_fused:
                result['fusion_camera'] = persistable_fusion(camera_fused)
            if screen_fused:
                result['fusion_screen'] = persistable_fusion(screen_fused)

        # Step 8: 大模型内容评分（ppt_recognition 由 has_ppt 参数控制）
        step = 8
        mode_label = "PPT识别模式" if ppt_recognition else "纯音频模式"
        logger.info(f"[{meeting_id}] Step {step}/9: 大模型五维评分 ({mode_label})")
        _save_progress(meeting_id, 'llm', 'AI五维评分中...', step, 9)

        # 时长不足处理
        actual_duration = audio_info.get('duration', 0)
        expected_duration = 3600
        duration_note = None
        score_cap = None
        score_floor = None
        skip_llm = False

        duration_adjustment = determine_duration_adjustment(actual_duration, expected_duration)
        duration_note = duration_adjustment["duration_note"]
        score_cap = duration_adjustment["score_cap"]
        score_floor = duration_adjustment["score_floor"]
        skip_llm = duration_adjustment["skip_llm"]

        if skip_llm:
            logger.info(f"[{meeting_id}] 时长严重不足 ({actual_duration:.0f}s < 600s)，跳过LLM评分，得0分")
        elif score_cap == 20:
            logger.info(f"[{meeting_id}] 时长不足 ({actual_duration:.0f}s)，LLM评分封顶20分")
        elif score_cap == 35:
            logger.info(f"[{meeting_id}] 时长不足 ({actual_duration:.0f}s)，LLM评分封顶35分")

        if skip_llm:
            dim_names = ['技术技能水平', '职业素养', '创新创意', '应用价值', '团队合作']
            result['ai_score'] = {
                'overall_score': 0,
                'dimensions': {name: {'name': name, 'score': 0, 'max_score': 20, 'items': []} for name in dim_names},
                'highlights': ['路演时长严重不足，无法进行有效评分'],
                'critical_issues': [f'实际时长 {actual_duration:.0f} 秒'],
                'improvement_priorities': ['建议按照完整比赛流程进行路演展示，确保覆盖所有评审维度'],
                'model': 'duration_adjustment', 'provider': 'system',
            }
        else:
            provider = 'deepseek'
            result = _score_with_rule_first(
                result=result,
                asr_result=asr_result,
                speech_quality=speech_quality,
                project_info=project_info,
                fusion_context=fusion_context,
                provider=provider,
                meeting_id=meeting_id,
                duration_note=duration_note,
                ppt_recognition=ppt_recognition,
                compare_mode=compare_mode,
            )
            if _extraction_is_incomplete(result.get("evidence_extraction")):
                return _fail_incomplete_extraction(meeting_id, result)

            # 应用时长封顶/保底
            if not skip_llm:
                orig_score = result['ai_score'].get('overall_score', 0)
                if score_cap and orig_score is not None and orig_score > score_cap:
                    result['ai_score']['overall_score'] = score_cap
                    logger.info(f"[{meeting_id}] 时长封顶: {orig_score}分 → {score_cap}分")
                if score_floor and orig_score is not None and orig_score < score_floor:
                    result['ai_score']['overall_score'] = score_floor
                    logger.info(f"[{meeting_id}] 时长保底: {orig_score}分 → {score_floor}分")
                result = apply_calibration_to_result(result)

        if _extraction_is_incomplete(result.get("evidence_extraction")):
            return _fail_incomplete_extraction(meeting_id, result)

        logger.info(f"[{meeting_id}] 五维评分完成: {result['ai_score'].get('overall_score', 0)}分")

        logger.info(f"[{meeting_id}] Step 8.5/9: 发言人证据整理")
        _save_progress(meeting_id, "speakers", "整理发言人证据中...", 8, 9)
        speaker_evidence = build_speaker_evidence(asr_result)
        result["speaker_evidence"] = speaker_evidence
        logger.info(f"[{meeting_id}] 发言人证据整理完成: {len(speaker_evidence)} 个声纹簇")

        # Step 9: 能力画像生成
        step = 9
        logger.info(f"[{meeting_id}] Step {step}/9: 能力画像生成")
        _save_progress(meeting_id, 'profile', '生成能力画像中...', step, 9)
        try:
            fused_timeline = (camera_fused or screen_fused or {}).get('timeline', [])
            profile_data = character_profile_service.generate_profile(
                fused_timeline=fused_timeline,
                asr_segments=asr_segments,
                trends=(camera_fused or {}).get('trends', {}),
                contradictions=(camera_fused or screen_fused or {}).get('contradictions', []),
                project_info=project_info,
                five_dim_scores=result['ai_score'],
                provider=provider
            )
            result['character_profile'] = {
                'profile_markdown': profile_data['profile_markdown'],
                'provider': profile_data['provider'],
                'sections': profile_data['sections'],
            }
        except Exception as e:
            logger.error(f"[{meeting_id}] 画像生成失败: {e}")
            result['character_profile'] = {'error': str(e)}

        # 完成
        end_time = datetime.now()
        result['status'] = 'generating_report'
        result['completed_at'] = end_time.isoformat()
        result['elapsed_seconds'] = round((end_time - start_time).total_seconds(), 1)
        _save_result(meeting_id, result)

        _generate_report(meeting_id, result)
        result['status'] = 'completed'
        _save_result(meeting_id, result)
        _maybe_start_jury_review(meeting_id, result, project_info, provider, ppt_recognition)

        logger.info(f"[{meeting_id}] 双视频评分流水线完成! 耗时 {result['elapsed_seconds']}s")
        _remove_progress(meeting_id)

        if callback_url:
            await _notify_backend(callback_url, meeting_id, result)

        _cleanup(meeting_id)
        return result

    except Exception as e:
        logger.error(f"[{meeting_id}] 流水线异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result['status'] = 'failed'
        result['error'] = str(e)
        result['completed_at'] = datetime.now().isoformat()
        _save_result(meeting_id, result)
        _remove_progress(meeting_id)
        if callback_url:
            await _notify_backend(callback_url, meeting_id, result)
        return result


def _save_result(meeting_id: str, result: dict):
    """保存评分结果到本地文件"""
    result_dir = os.path.join(settings.UPLOAD_DIR, "results")
    os.makedirs(result_dir, exist_ok=True)

    result_path = os.path.join(result_dir, f"result_{meeting_id}.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"结果已保存: {result_path}")


def _maybe_start_jury_review(
    meeting_id: str,
    result: dict,
    project_info: dict,
    provider: str,
    ppt_recognition: bool,
):
    """Optionally start independent AI jury review after the official result exists."""
    if not settings.AI_JURY_ENABLED:
        return
    try:
        jury_scoring_service.start_jury_review_background(
            meeting_id=meeting_id,
            official_result=result,
            project_info=project_info,
                provider=provider if provider == "deepseek" else "deepseek",
            ppt_recognition=ppt_recognition,
        )
        logger.info(f"[{meeting_id}] AI评审团复盘已启动")
    except Exception as e:
        logger.error(f"[{meeting_id}] AI评审团复盘启动失败: {e}")


def _generate_report(meeting_id: str, result: dict):
    """生成报告(PDF/Word)"""
    try:
        report_dir = os.path.join(settings.UPLOAD_DIR, "reports")
        report_path = report_service.generate_report(result, report_dir)
        result['report_path'] = report_path
        logger.info(f"[{meeting_id}] 报告已生成: {report_path}")
    except Exception as e:
        logger.error(f"[{meeting_id}] 报告生成失败: {e}")
        logger.error(traceback.format_exc())


async def _notify_backend(callback_url: str, meeting_id: str, result: dict):
    """回调通知 Spring Boot 后端"""
    import httpx

    try:
        payload = build_backend_callback_payload(meeting_id, result)

        if 'error' in result:
            payload['error'] = result['error']

        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(callback_url, json=payload)
            logger.info(f"后端回调: {response.status_code}")
    except Exception as e:
        logger.warning(f"后端回调失败: {e}")


def _cleanup(meeting_id: str):
    """清理临时文件"""
    upload_dir = settings.UPLOAD_DIR
    for f in os.listdir(upload_dir):
        if f.startswith(f"meeting_{meeting_id}_") and f.endswith('.webm'):
            try:
                os.remove(os.path.join(upload_dir, f))
            except:
                pass
