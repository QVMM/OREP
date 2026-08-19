import asyncio
import copy
import difflib
import hashlib
import json
import logging
import os
import re
import subprocess
import traceback
from datetime import datetime, timezone

import httpx

from app.services.pipeline_service import run_scoring_pipeline
from app.services.competition_calibration_service import apply_calibration_to_result
from app.services.pipeline_payloads import build_rule_engine_shadow_payload
from app.services.jury import scoring_service as jury_scoring_service
from app.services.scoring.coverage_validator import validate_remediation_coverage
from app.services.scoring.loss_ledger_service import normalize_loss_ledger
from app.services.scoring.remediation_planner import build_complete_remediation_map
from app.services.scoring.score_impact_service import build_score_impact_projection
from app.config import settings
from app.services.backend_callback_client import BackendCallbackClient, CallbackDeliveryError

logger = logging.getLogger(__name__)


def _session_dir() -> str:
    path = os.path.join(settings.UPLOAD_DIR, "sessions")
    os.makedirs(path, exist_ok=True)
    return path


def _visual_frames_dir(session_id: str) -> str:
    path = os.path.join(_session_dir(), f"frames_{session_id}")
    os.makedirs(path, exist_ok=True)
    return path


def _frame_index_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"frames_{session_id}.jsonl")


def _session_path(session_id: str) -> str:
    return os.path.join(_session_dir(), f"session_{session_id}.json")


def _ffprobe_duration(video_path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return max(0.0, float(result.stdout.strip() or 0))
    except Exception as exc:
        logger.warning("读取上传视频时长失败: %s", exc)
        return 0.0


def _has_reusable_frames(session_id: str) -> bool:
    return _count_reusable_frames(session_id) >= 3


def _count_reusable_frames(session_id: str) -> int:
    index_path = _frame_index_path(session_id)
    if not os.path.exists(index_path):
        return 0
    count = 0
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                if item.get("image_path") and os.path.exists(item["image_path"]):
                    count += 1
    except Exception:
        return 0
    return count


def _write_visual_session_file(session_id: str, session_no: str, video_path: str, frame_count: int):
    now = datetime.now(timezone.utc).isoformat()
    session_payload = {
        "session_id": session_id,
        "meeting_id": session_id,
        "status": "finished",
        "has_audio": True,
        "has_video": True,
        "transcript_status": "completed",
        "visual_status": "captured" if frame_count else "missing",
        "recording_status": "uploaded",
        "final_score_status": "processing",
        "started_at": now,
        "ended_at": now,
        "error_message": None,
        "updated_at": now,
        "visual_frame_count": frame_count,
        "uploaded_file": video_path,
        "session_no": session_no,
    }
    with open(_session_path(session_id), "w", encoding="utf-8") as f:
        json.dump(session_payload, f, ensure_ascii=False, indent=2)


def prepare_uploaded_video_visual_session(session_id: int, session_no: str, video_path: str) -> int:
    """Generate a Python visual-frame session keyed by the Java ai_scoring_session id."""
    sid = str(session_id)
    if _has_reusable_frames(sid):
        count = _count_reusable_frames(sid)
        _write_visual_session_file(sid, session_no, video_path, count)
        return count

    duration = _ffprobe_duration(video_path)
    interval = max(1, int(settings.VIDEO_FRAME_INTERVAL or 30))
    max_frames = max(1, int(settings.VIDEO_ANALYSIS_MAX_FRAMES or 180))
    if duration <= 0:
        timestamps = [0.0]
    else:
        timestamps = [float(value) for value in range(0, int(duration) + 1, interval)]
        if duration not in timestamps:
            timestamps.append(duration)
        timestamps = timestamps[:max_frames]

    frame_dir = _visual_frames_dir(sid)
    index_path = _frame_index_path(sid)
    tmp_index = index_path + ".tmp"
    count = 0
    with open(tmp_index, "w", encoding="utf-8") as f:
        for timestamp in timestamps:
            frame_hash = hashlib.sha1(f"{sid}:{timestamp:.3f}:{video_path}".encode("utf-8")).hexdigest()[:32]
            frame_type = "start" if count == 0 else "interval"
            file_name = f"frame_{int(timestamp * 1000):012d}_{frame_type}_{frame_hash}.jpg"
            frame_path = os.path.join(frame_dir, file_name)
            if not os.path.exists(frame_path):
                try:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-hide_banner",
                            "-loglevel",
                            "error",
                            "-ss",
                            f"{timestamp:.3f}",
                            "-i",
                            video_path,
                            "-frames:v",
                            "1",
                            "-q:v",
                            "3",
                            "-y",
                            frame_path,
                        ],
                        check=True,
                        timeout=45,
                    )
                except Exception as exc:
                    logger.warning("上传视频关键帧抽取失败 session=%s timestamp=%.3f: %s", sid, timestamp, exc)
                    continue
            event = {
                "frame_id": frame_hash,
                "timestamp": round(timestamp, 3),
                "frame_type": frame_type,
                "diff_score": 0,
                "image_path": frame_path,
                "file_name": file_name,
                "analysis_status": "ready",
                "session_id": sid,
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            count += 1
    os.replace(tmp_index, index_path)
    _write_visual_session_file(sid, session_no, video_path, count)
    return count


def _normalize_action_plan_for_callback(ai_score: dict, evidence_extraction: dict) -> list[dict]:
    """Preserve the full coaching plan while adding stable linkage metadata."""
    raw_items = ai_score.get("action_plan") or []
    if not isinstance(raw_items, list):
        return []

    candidates = evidence_extraction.get("deductionCandidates") or []
    candidates = [item for item in candidates if isinstance(item, dict)]
    normalized: list[dict] = []
    forbidden_recovery_fields = {
        "expectedRecoverPoints",
        "expected_recover_points",
        "recoverableScore",
        "recoverable_score",
        "expectedGain",
        "expected_gain",
    }

    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item = copy.deepcopy(raw_item)
        for field in forbidden_recovery_fields:
            item.pop(field, None)

        observation_code = item.pop("observation_code", None) or item.get("observationCode")
        source_issue_key = item.pop("source_issue_key", None) or item.get("sourceIssueKey")
        evidence_anchor_ids = item.pop("evidence_anchor_ids", None) or item.get("evidenceAnchorIds")
        item["priority"] = str(item.get("priority") or "P1").upper()
        item["title"] = str(item.get("title") or "").strip()
        item["problem"] = str(item.get("problem") or item.get("issue") or "").strip()
        item["method"] = str(item.get("method") or item.get("action") or item.get("suggestion") or "").strip()
        item["owner"] = str(item.get("owner") or item.get("ownerRole") or "").strip()
        item["timebox"] = str(item.get("timebox") or item.get("timeSuggestion") or "").strip()
        item["acceptance"] = str(item.get("acceptance") or item.get("acceptanceCriteria") or "").strip()

        if not observation_code:
            matched = _best_action_plan_candidate(item, candidates)
            if matched:
                observation_code = matched.get("observationCode") or matched.get("observation_code")
                source_issue_key = source_issue_key or matched.get("penaltyRuleCode") or matched.get("sourceIssueKey")

        if observation_code:
            item["observationCode"] = str(observation_code)
        else:
            item.pop("observationCode", None)
        if source_issue_key:
            item["sourceIssueKey"] = str(source_issue_key)
        else:
            item.pop("sourceIssueKey", None)
        if evidence_anchor_ids is not None:
            item["evidenceAnchorIds"] = evidence_anchor_ids if isinstance(evidence_anchor_ids, list) else [evidence_anchor_ids]

        if not item.get("id"):
            seed = "|".join((item["priority"], item["title"], item["problem"]))
            item["id"] = f"action-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"
        normalized.append(item)
    return normalized


def _best_action_plan_candidate(item: dict, candidates: list[dict]) -> dict | None:
    plan_text = _comparison_text(" ".join((item.get("title", ""), item.get("problem", ""))))
    if len(plan_text) < 6:
        return None
    best_candidate = None
    best_ratio = 0.0
    for candidate in candidates:
        candidate_text = _comparison_text(" ".join((
            str(candidate.get("triggerFact") or candidate.get("reason") or ""),
            str(candidate.get("penaltyRuleCode") or ""),
        )))
        if len(candidate_text) < 6:
            continue
        ratio = difflib.SequenceMatcher(None, plan_text, candidate_text).ratio()
        if ratio > best_ratio:
            best_candidate = candidate
            best_ratio = ratio
    return best_candidate if best_ratio >= 0.38 else None


def _comparison_text(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def _build_final_result(pipeline_result: dict) -> dict:
    """Build the Java callback contract with an explicit score authority.

    Official published scores only come from the structured rule engine.
    LLM totals stay in llmRawScore / rawOverallScore for diagnosis.
    """
    ai_score = pipeline_result.get("ai_score", {})
    calibration = pipeline_result.get("score_calibration", {})
    speech_quality = pipeline_result.get("speech_quality", {})
    asr = pipeline_result.get("asr", {})
    dimensions = ai_score.get("dimensions", {})
    shadow_payload = {}
    evidence_extraction = pipeline_result.get("evidence_extraction") or {}
    extraction_quality = evidence_extraction.get("extractionQuality") or {}
    has_extraction_attempt = bool(evidence_extraction)
    extraction_not_publishable = has_extraction_attempt and (
        evidence_extraction.get("status") in {"failed", "review_required"}
        or extraction_quality.get("publicationEligible") is False
    )

    if has_extraction_attempt and not extraction_not_publishable:
        shadow_payload = build_rule_engine_shadow_payload(pipeline_result)

    publish_official_score = bool(pipeline_result.get("publish_official_score", True))
    has_structured_score = shadow_payload.get("scoreAuthority") == "structured_rule_engine"
    llm_score = ai_score.get("overall_score")
    review_reason = None

    if extraction_not_publishable:
        # Evidence extraction ran but is not safe to publish.
        score_authority = "review_required"
        authoritative_score = None
        review_reason = "evidence_extraction_not_publishable"
    elif has_structured_score:
        score_authority = (
            "structured_rule_engine"
            if publish_official_score
            else "diagnostic_rule_engine"
        )
        authoritative_score = shadow_payload.get("finalScore")
    elif has_extraction_attempt:
        # Extraction attempted without a rule score: never promote LLM to official.
        if publish_official_score:
            score_authority = "review_required"
            authoritative_score = None
            review_reason = "rule_engine_score_unavailable"
        else:
            score_authority = "diagnostic_llm"
            authoritative_score = llm_score
    else:
        # Pure legacy path without evidence extraction (old reports / non-rule tracks).
        score_authority = "legacy_llm" if publish_official_score else "diagnostic_llm"
        authoritative_score = llm_score
    observations = shadow_payload.get("observations", [])
    deductions = [
        _normalize_callback_deduction(item)
        for item in shadow_payload.get("deductions", [])
    ]
    rule_hash = shadow_payload.get("ruleHash") or evidence_extraction.get("ruleHash")
    scoring_fingerprint = shadow_payload.get("scoringFingerprint")
    use_v3_contract = has_structured_score and isinstance(shadow_payload.get("lossLedger"), list)
    action_plan = _normalize_action_plan_for_callback(ai_score, evidence_extraction)
    if use_v3_contract:
        loss_ledger = normalize_loss_ledger(
            rule_result=shadow_payload,
            rule_hash=rule_hash,
            scoring_fingerprint=scoring_fingerprint,
        )
        action_plan = build_complete_remediation_map(
            action_plan=action_plan,
            loss_ledger=loss_ledger,
        )
        action_plan, score_projection = build_score_impact_projection(
            action_plan,
            observations,
            deductions,
            loss_ledger=loss_ledger,
            rule_hash=rule_hash,
            scoring_fingerprint=scoring_fingerprint,
        )
        coverage_summary = validate_remediation_coverage(
            current_score=authoritative_score,
            loss_ledger=loss_ledger,
            tasks=action_plan,
            rule_hash=rule_hash,
            scoring_fingerprint=scoring_fingerprint,
        )
    else:
        loss_ledger = list(shadow_payload.get("lossLedger") or [])
        action_plan, score_projection = build_score_impact_projection(
            action_plan,
            observations,
            deductions,
            rule_hash=rule_hash,
            scoring_fingerprint=scoring_fingerprint,
        )
        coverage_summary = {
            "currentScore": authoritative_score,
            "fullGap": round(100.0 - float(authoritative_score), 1) if authoritative_score is not None else None,
            "ledgerPoints": None,
            "lossItemCount": len(loss_ledger),
            "remediationTaskCount": len(action_plan),
            "coveredLossItemCount": 0,
            "coveredGapPoints": 0.0,
            "coverageRate": 0.0,
            "uncoveredLossIds": [],
            "unresolvedDuplicateBudgetKeys": [],
            "reconciliationError": None,
            "status": "incomplete",
            "calculationVersion": "legacy-coverage-unavailable",
            "ruleHash": rule_hash,
            "scoringFingerprint": scoring_fingerprint,
        }
    todo_portfolio_status = "complete" if coverage_summary.get("status") == "complete" else "incomplete"
    if extraction_not_publishable:
        dimensions = {}
    elif has_structured_score:
        dimensions = {
            code: {
                "score": score,
                "max_score": (shadow_payload.get("dimensionMaxScores") or {}).get(code),
                "source": "structured_rule_engine",
            }
            for code, score in (shadow_payload.get("dimensionScores") or {}).items()
        }

    final_result = {
        "transcript": asr.get("transcript", ""),
        "asrSegments": asr.get("segments", []),
        "speakerEvidence": pipeline_result.get("speaker_evidence", []),
        "speakerAttribution": asr.get("speakerAttribution"),
        "overallScore": authoritative_score,
        "rawOverallScore": ai_score.get("raw_overall_score", ai_score.get("overall_score")),
        "llmRawScore": shadow_payload.get(
            "llmRawScore",
            ai_score.get("raw_overall_score", ai_score.get("overall_score")),
        ),
        "scoreAuthority": score_authority,
        "reviewReason": review_reason,
        "scorePolicyVersion": shadow_payload.get("scorePolicyVersion"),
        "publishOfficialScore": publish_official_score,
        "competitionBinding": pipeline_result.get("competition_binding"),
        "dimensionsJson": json.dumps(dimensions, ensure_ascii=False) if dimensions else None,
        "highlightsJson": json.dumps(ai_score.get("highlights", []), ensure_ascii=False),
        "criticalIssuesJson": json.dumps(ai_score.get("critical_issues", []), ensure_ascii=False),
        "improvementPrioritiesJson": json.dumps(ai_score.get("improvement_priorities", []), ensure_ascii=False),
        "actionPlanJson": json.dumps(action_plan, ensure_ascii=False),
        "lossLedgerJson": json.dumps(loss_ledger, ensure_ascii=False),
        "coverageSummaryJson": json.dumps(coverage_summary, ensure_ascii=False),
        "scoreProjectionJson": json.dumps(score_projection, ensure_ascii=False),
        "contractVersion": "ai-score-report-v3" if use_v3_contract else "ai-score-report-v2",
        "todoPortfolioStatus": todo_portfolio_status,
        "publishCompleteTodoPortfolio": todo_portfolio_status == "complete",
        "speechQualityJson": json.dumps(speech_quality, ensure_ascii=False) if speech_quality else None,
        "scoreCalibrationJson": json.dumps(calibration, ensure_ascii=False) if calibration else None,
        "model": ai_score.get("model", settings.DEEPSEEK_MODEL or "deepseek-v4-pro"),
        "observations": observations,
        "deductions": deductions,
        "diagnosticDeductions": shadow_payload.get("diagnosticDeductions", []),
        "lossLedger": loss_ledger,
        "evidenceAnchors": shadow_payload.get("evidenceAnchors", []),
        "ruleEngineVersion": shadow_payload.get("ruleEngineVersion", "pipeline-v1"),
        "ruleEngineScore": shadow_payload.get("ruleEngineScore"),
        "modelReviewScore": shadow_payload.get("modelReviewScore"),
        "tapeGrounded": shadow_payload.get("tapeGrounded"),
        "scoreDiff": shadow_payload.get("scoreDiff"),
        "diffReasons": shadow_payload.get("diffReasons", []),
        "scoringFingerprint": shadow_payload.get("scoringFingerprint"),
        "ruleFingerprint": shadow_payload.get("ruleFingerprint") or shadow_payload.get("scoringFingerprint"),
        "evidenceSnapshotHash": shadow_payload.get("evidenceSnapshotHash"),
        "scoreInstanceId": shadow_payload.get("scoreInstanceId"),
        "reconciliation": shadow_payload.get("reconciliation"),
        "dimensionScores": shadow_payload.get("dimensionScores", {}),
        "dimensionMaxScores": shadow_payload.get("dimensionMaxScores", {}),
        "baseScore": shadow_payload.get("baseScore"),
        "performanceGap": shadow_payload.get("performanceGap"),
        "evidenceLimitedGap": shadow_payload.get("evidenceLimitedGap"),
        "deductedScore": shadow_payload.get("deductedScore"),
        "recoveredScore": shadow_payload.get("recoveredScore"),
        "effectiveHardPenalty": shadow_payload.get("effectiveHardPenalty"),
        "currentScoreCap": shadow_payload.get("currentScoreCap"),
    }
    return final_result


def _normalize_callback_deduction(value: dict) -> dict:
    deduction = dict(value or {})
    deduction["requiredFix"] = _callback_text(deduction.get("requiredFix"))
    deduction["acceptanceCriteria"] = _callback_text(deduction.get("acceptanceCriteria"))
    return deduction


def _callback_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        ordered_keys = ("title", "action", "acceptanceCriteria")
        parts = [_callback_text(value.get(key)) for key in ordered_keys if value.get(key) is not None]
        remaining = [
            _callback_text(item)
            for key, item in value.items()
            if key not in ordered_keys and item is not None
        ]
        return "\n".join(part for part in parts + remaining if part)
    if isinstance(value, (list, tuple, set)):
        return "\n".join(part for item in value if (part := _callback_text(item)))
    return str(value)


async def deliver_completion_callback(
    callback_client: BackendCallbackClient,
    callback_url: str,
    completed_payload: dict,
) -> bool:
    """Deliver a completed result or explicitly mark result writeback failure."""
    try:
        await callback_client.send(
            callback_url,
            completed_payload,
            max_attempts=3,
        )
        return True
    except CallbackDeliveryError as exc:
        failure_payload = {
            "sessionId": completed_payload.get("sessionId"),
            "status": "failed",
            "currentStage": "result_writeback_failed",
            "progressPercent": 95,
            "errorMessage": f"结果回写失败：{exc}",
        }
        try:
            await callback_client.send(
                callback_url,
                failure_payload,
                max_attempts=3,
            )
        except CallbackDeliveryError:
            logger.error("[%s] 结果回写失败状态也无法送达", completed_payload.get("sessionId"))
        return False


def _build_authoritative_jury_result(pipeline_result: dict, final_result: dict) -> dict:
    """Give the independent jury the same official score contract shown to the user."""
    result = copy.deepcopy(pipeline_result)
    ai_score = result.setdefault("ai_score", {})
    previous_score = ai_score.get("overall_score")
    ai_score.setdefault("raw_overall_score", previous_score)
    ai_score["overall_score"] = final_result.get("overallScore", previous_score)
    dimensions_json = final_result.get("dimensionsJson")
    if dimensions_json:
        try:
            ai_score["dimensions"] = json.loads(dimensions_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("评审团权威维度解析失败，保留流水线原维度")
    result["score_authority"] = final_result.get("scoreAuthority", "legacy_llm")
    return result


async def run_session_pipeline(
    session_id: int,
    session_no: str,
    team_id: int,
    project_id: int,
    track_name: str,
    competition_binding: dict,
    publish_official_score: bool,
    jury_enabled: bool,
    source_type: str,
    video_file_path: str,
    video_original_name: str,
    materials: list[dict],
    callback_url: str,
    video_sha256: str | None = None,
    force_retranscribe: bool = False,
):
    callback_client = BackendCallbackClient()

    async def notify(
        status,
        stage,
        progress,
        message="",
        error_message=None,
        final_result=None,
        max_attempts=1,
    ):
        payload = {
            "sessionId": session_id,
            "status": status,
            "currentStage": stage,
            "progressPercent": progress,
            "message": message,
        }
        if error_message:
            payload["errorMessage"] = error_message
        if final_result:
            payload["finalResult"] = final_result
        try:
            response = await callback_client.send(
                callback_url,
                payload,
                max_attempts=max_attempts,
            )
            logger.info("Callback accepted: business_code=%s stage=%s", response.get("code"), stage)
            return True
        except CallbackDeliveryError as exc:
            logger.error("Callback rejected: stage=%s error=%s", stage, exc)
            if max_attempts > 1:
                raise
            return False

    async def forward_pipeline_progress(task: asyncio.Task):
        progress_path = os.path.join(settings.UPLOAD_DIR, "results", f"progress_{session_id}.json")
        last_signature = None
        step_map = {
            "converting": ("audio_extracting", "正在提取音频..."),
            "asr": ("asr_processing", "正在语音识别..."),
            "speech": ("speech_analysis", "正在分析语音质量..."),
            "video_analysis": ("frame_extracting", "正在抽帧与识别画面..."),
            "fusion": ("ocr_processing", "正在融合音视频证据..."),
            "llm": ("model_scoring", "正在 AI 评分..."),
            "profile": ("rule_calibrating", "正在生成能力画像与校准..."),
            "report": ("report_generating", "正在生成报告..."),
        }
        while not task.done():
            try:
                if os.path.exists(progress_path):
                    with open(progress_path, "r", encoding="utf-8") as f:
                        progress = json.load(f)
                    step = progress.get("step")
                    mapped_stage, default_label = step_map.get(step, (step or "scoring", "正在分析..."))
                    percent = int(progress.get("progress_percent") or 0)
                    label = progress.get("label") or default_label
                    signature = (mapped_stage, percent, label)
                    if signature != last_signature:
                        await notify("scoring", mapped_stage, percent, label)
                        last_signature = signature
            except Exception as e:
                logger.warning(f"Forward progress failed: {e}")
            await asyncio.sleep(1.5)

    def run_pipeline_in_isolated_process():
        """Run scoring in a child process so native crashes cannot kill uvicorn."""
        import json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        work = Path(tempfile.mkdtemp(prefix=f"orep-pipeline-{session_id}-"))
        config_path = work / "job.json"
        result_path = work / "result.json"
        config = {
            "audio_file_path": abs_video_path,
            "meeting_id": str(session_id),
            "project_info": project_info,
            "provider": "deepseek",
            "compare_mode": False,
            "ppt_recognition": True,
            "start_jury_review": False,
            "result_path": str(result_path),
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        # Long roadshows need multi-hour budget (ASR alone ~15-25min for 54min video).
        timeout_seconds = max(7200, int(getattr(settings, "PRIMARY_EVIDENCE_TIMEOUT_SECONDS", 3600) or 3600) * 2)
        cmd = [
            sys.executable,
            "-m",
            "app.services.pipeline_job_runner",
            "--config",
            str(config_path),
        ]
        log_path = work / "pipeline.log"
        logger.info(
            "Starting isolated pipeline process: session=%s timeout=%ss log=%s cmd=%s",
            session_id,
            timeout_seconds,
            log_path,
            cmd,
        )
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                completed = subprocess.run(
                    cmd,
                    cwd=str(Path(__file__).resolve().parents[2]),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
        except subprocess.TimeoutExpired as exc:
            logger.error("Isolated pipeline timeout: session=%s", session_id)
            return {
                "status": "failed",
                "error": f"pipeline_process_timeout:{timeout_seconds}s",
                "meeting_id": str(session_id),
            }
        try:
            if log_path.is_file():
                tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
                for line in tail:
                    logger.info("[pipeline-child] %s", line)
        except Exception:
            pass
        if result_path.is_file():
            try:
                payload = json.loads(result_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    if completed.returncode != 0 and not payload.get("error"):
                        payload.setdefault(
                            "error",
                            f"pipeline_process_exit:{completed.returncode}",
                        )
                        payload.setdefault("status", "failed")
                    return payload
            except Exception as exc:
                logger.error("Failed reading isolated pipeline result: %s", exc)
        return {
            "status": "failed",
            "error": (
                f"pipeline_process_exit:{completed.returncode}:"
                f"{(completed.stderr or completed.stdout or '')[-500:]}"
            ),
            "meeting_id": str(session_id),
        }

    try:
        abs_video_path = video_file_path
        if not os.path.isabs(abs_video_path):
            abs_video_path = os.path.join(settings.UPLOAD_DIR, abs_video_path)
        if not os.path.exists(abs_video_path):
            await notify("failed", "failed", 0, error_message=f"Video not found: {abs_video_path}")
            return

        await notify("scoring", "frame_extracting", 12, "正在提取视频关键帧...")
        frame_count = await asyncio.to_thread(
            prepare_uploaded_video_visual_session,
            session_id,
            session_no,
            abs_video_path,
        )
        logger.info("Prepared uploaded-video visual frames: session=%s count=%s", session_id, frame_count)

        project_info = {
            "team_size": 4,
            "track": track_name,
            "project_name": f"Session {session_no}",
            "competition_binding": competition_binding,
            "publish_official_score": publish_official_score,
            # 报告渲染门控：未开启时绝不写入/展示假评委
            "jury_enabled": bool(jury_enabled),
            "video_path": abs_video_path,
            "videoSha256": video_sha256,
            "forceRetranscribe": bool(force_retranscribe),
        }

        project_info["session_id"] = str(session_id)

        await notify("scoring", "queued", 5, "AI评分流水线已启动，等待任务执行...")
        # Isolate heavy native work so uvicorn workers cannot be killed mid-job.
        pipeline_task = asyncio.create_task(asyncio.to_thread(run_pipeline_in_isolated_process))
        progress_task = asyncio.create_task(forward_pipeline_progress(pipeline_task))
        try:
            pipeline_result = await pipeline_task
        finally:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
        if not isinstance(pipeline_result, dict):
            await notify("failed", "failed", 0, error_message="评分流水线返回无效结果")
            return
        if pipeline_result.get("status") == "failed" or pipeline_result.get("error"):
            error = pipeline_result.get("error") or "评分流水线执行失败"
            stage = (
                "extraction_incomplete"
                if str(error).startswith("extraction_incomplete")
                else "failed"
            )
            message = pipeline_result.get("error_message") or error
            await notify("failed", stage, 0, error_message=message)
            return

        pipeline_result["competition_binding"] = competition_binding
        pipeline_result["publish_official_score"] = publish_official_score

        await notify("scoring", "rule_calibrating", 85, "正在校准评分...")
        if "ai_score" in pipeline_result:
            pipeline_result = apply_calibration_to_result(pipeline_result)

        await notify("scoring", "report_generating", 95, "正在生成报告...")

        pipeline_result["jury_enabled"] = bool(jury_enabled)
        final_result = _build_final_result(pipeline_result)

        if settings.AI_JURY_ENABLED and jury_enabled:
            try:
                await notify("scoring", "jury_reviewing", 96, "正在进行评审团复核，完成后会写入报告...")
                jury_scoring_service.run_jury_review(
                    meeting_id=str(session_id),
                    official_result=_build_authoritative_jury_result(pipeline_result, final_result),
                    project_info=project_info,
                    provider="deepseek",
                    ppt_recognition=True,
                )
                pipeline_result["jury_enabled"] = True
                final_result = _build_final_result(pipeline_result)
                logger.info("[%s] AI评审团已完成并写入报告", session_id)
            except Exception as exc:
                logger.error("[%s] AI评审团复核失败: %s", session_id, exc)

        completed_payload = {
            "sessionId": session_id,
            "status": "completed",
            "currentStage": "completed",
            "progressPercent": 100,
            "message": "评分完成",
            "finalResult": final_result,
        }
        if not await deliver_completion_callback(callback_client, callback_url, completed_payload):
            return
        logger.info("Callback accepted: business_code=200 stage=completed")

    except Exception as e:
        logger.error(f"Pipeline failed: {traceback.format_exc()}")
        try:
            await notify("failed", "failed", 0, error_message=str(e), max_attempts=3)
        except CallbackDeliveryError:
            logger.error("[%s] 流水线失败状态无法送达", session_id)
