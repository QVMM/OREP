"""CRUD + claim for ppt_agent_session / ppt_agent_job."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .db import db_enabled, get_connection

logger = logging.getLogger(__name__)


class JobStore:
    def available(self) -> bool:
        return db_enabled()

    def upsert_session(self, session: Any) -> None:
        if not self.available():
            return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ppt_agent_session (
                            id, owner_key, owner_user_id, owner_name, owner_tenant_id,
                            file_path, source_type, file_name, file_size
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON DUPLICATE KEY UPDATE
                            owner_key=VALUES(owner_key),
                            owner_user_id=VALUES(owner_user_id),
                            owner_name=VALUES(owner_name),
                            owner_tenant_id=VALUES(owner_tenant_id),
                            file_path=VALUES(file_path),
                            source_type=VALUES(source_type),
                            file_name=VALUES(file_name),
                            file_size=VALUES(file_size)
                        """,
                        (
                            session.id,
                            session.owner_key,
                            session.owner_user_id,
                            session.owner_name,
                            session.owner_tenant_id,
                            str(session.file_path),
                            session.source_type,
                            session.file_name,
                            int(session.file_size or 0),
                        ),
                    )
        except Exception:
            logger.exception("upsert_session failed for %s", getattr(session, "id", "?"))

    def upsert_job(self, job: Any, *, request_json: str | None = None, deck_type: str | None = None, mode: str | None = None) -> None:
        if not self.available():
            return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Preserve existing request_json / deck_type / mode if not provided
                    cur.execute(
                        "SELECT request_json, deck_type, mode FROM ppt_agent_job WHERE id=%s",
                        (job.id,),
                    )
                    prev = cur.fetchone() or {}
                    req = request_json if request_json is not None else prev.get("request_json")
                    deck = deck_type if deck_type is not None else prev.get("deck_type")
                    job_mode = mode if mode is not None else prev.get("mode")
                    cur.execute(
                        """
                        INSERT INTO ppt_agent_job (
                            id, session_id, owner_key, owner_user_id, owner_name, owner_tenant_id,
                            status, progress, message, error, slides_completed, total_slides,
                            output_path, project_dir, parent_job_id, provider, model_name, base_url,
                            canvas_format, style, render_engine, language, detail_level, instruction,
                            deck_type, mode, request_json
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,
                            %s,%s,%s
                        )
                        ON DUPLICATE KEY UPDATE
                            session_id=VALUES(session_id),
                            owner_key=VALUES(owner_key),
                            owner_user_id=VALUES(owner_user_id),
                            owner_name=VALUES(owner_name),
                            owner_tenant_id=VALUES(owner_tenant_id),
                            status=VALUES(status),
                            progress=VALUES(progress),
                            message=VALUES(message),
                            error=VALUES(error),
                            slides_completed=VALUES(slides_completed),
                            total_slides=VALUES(total_slides),
                            output_path=VALUES(output_path),
                            project_dir=VALUES(project_dir),
                            parent_job_id=VALUES(parent_job_id),
                            provider=VALUES(provider),
                            model_name=VALUES(model_name),
                            base_url=VALUES(base_url),
                            canvas_format=VALUES(canvas_format),
                            style=VALUES(style),
                            render_engine=VALUES(render_engine),
                            language=VALUES(language),
                            detail_level=VALUES(detail_level),
                            instruction=VALUES(instruction),
                            deck_type=COALESCE(VALUES(deck_type), deck_type),
                            mode=COALESCE(VALUES(mode), mode),
                            request_json=COALESCE(VALUES(request_json), request_json),
                            -- Re-queue (confirm cards / regenerate) must release the previous claim,
                            -- otherwise claim_next_job never picks the row up again.
                            worker_id=IF(
                                VALUES(status) IN ('queued', 'pending'),
                                NULL,
                                worker_id
                            ),
                            claimed_at=IF(
                                VALUES(status) IN ('queued', 'pending'),
                                NULL,
                                claimed_at
                            )
                        """,
                        (
                            job.id,
                            job.session_id,
                            job.owner_key,
                            job.owner_user_id,
                            job.owner_name,
                            job.owner_tenant_id,
                            job.status,
                            float(job.progress or 0),
                            (job.message or "")[:1024],
                            job.error,
                            int(job.slides_completed or 0),
                            int(job.total_slides or 0),
                            job.output_path,
                            job.project_dir,
                            job.parent_job_id,
                            job.provider,
                            job.model_name,
                            job.base_url,
                            job.canvas_format,
                            job.style,
                            job.render_engine,
                            job.language,
                            job.detail_level,
                            job.instruction,
                            deck,
                            job_mode,
                            req,
                        ),
                    )
        except Exception:
            logger.exception("upsert_job failed for %s", getattr(job, "id", "?"))

    def get_session_row(self, session_id: str) -> dict[str, Any] | None:
        if not self.available() or not session_id:
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM ppt_agent_session WHERE id=%s", (session_id,))
                    return cur.fetchone()
        except Exception:
            logger.exception("get_session_row failed for %s", session_id)
            return None

    def get_job_row(self, job_id: str) -> dict[str, Any] | None:
        if not self.available() or not job_id:
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM ppt_agent_job WHERE id=%s", (job_id,))
                    return cur.fetchone()
        except Exception:
            logger.exception("get_job_row failed for %s", job_id)
            return None

    def list_job_rows_for_owner(self, owner_key: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.available() or not owner_key:
            return []
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM ppt_agent_job
                        WHERE owner_key=%s
                        ORDER BY updated_at DESC
                        LIMIT %s
                        """,
                        (owner_key, int(limit)),
                    )
                    return list(cur.fetchall() or [])
        except Exception:
            logger.exception("list_job_rows_for_owner failed")
            return []

    def claim_next_job(self, worker_id: str) -> dict[str, Any] | None:
        """Atomically claim one queued job (SKIP LOCKED)."""
        if not self.available():
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Accept rows with a stale worker_id (e.g. re-queued after card
                    # confirm without clearing claim fields). Status alone is the
                    # source of truth for "ready to run".
                    cur.execute(
                        """
                        SELECT id FROM ppt_agent_job
                        WHERE status IN ('queued', 'pending')
                          AND request_json IS NOT NULL
                          AND request_json != ''
                        ORDER BY created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    job_id = row["id"]
                    cur.execute(
                        """
                        UPDATE ppt_agent_job
                        SET status='running',
                            message='Worker 已认领，开始生成',
                            worker_id=%s,
                            claimed_at=NOW()
                        WHERE id=%s AND status IN ('queued', 'pending')
                        """,
                        (worker_id, job_id),
                    )
                    if cur.rowcount != 1:
                        return None
                    cur.execute("SELECT * FROM ppt_agent_job WHERE id=%s", (job_id,))
                    return cur.fetchone()
        except Exception:
            logger.exception("claim_next_job failed")
            return None

    def mark_stale_running(self, stale_minutes: int = 120) -> int:
        """Mark long-running claimed jobs as error after worker death."""
        if not self.available():
            return 0
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE ppt_agent_job
                        SET status='error',
                            error='Worker 超时未完成，任务已中断。请重新生成。',
                            message='Worker 超时未完成，任务已中断。请重新生成。'
                        WHERE status IN (
                            'running', 'parsing', 'research', 'content_cards',
                            'strategy', 'generation', 'postprocess', 'export', 'pending'
                          )
                          AND worker_id IS NOT NULL
                          AND claimed_at IS NOT NULL
                          AND claimed_at < (NOW() - INTERVAL %s MINUTE)
                        """,
                        (int(stale_minutes),),
                    )
                    return int(cur.rowcount or 0)
        except Exception:
            logger.exception("mark_stale_running failed")
            return 0

    def requeue_orphaned_claimed(self, max_age_seconds: int = 90) -> int:
        """Re-queue jobs claimed by a dead worker (restart mid-run).

        Jobs stuck in non-terminal pipeline stages with a worker_id but no
        recent update are put back to queued so another worker can pick them up.
        """
        if not self.available():
            return 0
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE ppt_agent_job
                        SET status='queued',
                            message='Worker 异常退出，任务已重新入队',
                            error=NULL,
                            worker_id=NULL,
                            claimed_at=NULL
                        WHERE status IN (
                            'running', 'parsing', 'research', 'pending',
                            'content_cards', 'script', 'strategy', 'generation',
                            'postprocess', 'export'
                          )
                          AND worker_id IS NOT NULL
                          AND request_json IS NOT NULL
                          AND request_json != ''
                          AND updated_at < (NOW() - INTERVAL %s SECOND)
                        """,
                        (int(max_age_seconds),),
                    )
                    return int(cur.rowcount or 0)
        except Exception:
            logger.exception("requeue_orphaned_claimed failed")
            return 0

    def get_job_status(self, job_id: str) -> str | None:
        """Return current status string from MySQL (cross-process cancel checks)."""
        if not self.available() or not job_id:
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT status FROM ppt_agent_job WHERE id=%s",
                        (job_id,),
                    )
                    row = cur.fetchone() or {}
                    return str(row.get("status") or "") or None
        except Exception:
            logger.exception("get_job_status failed for %s", job_id)
            return None

    def request_cancel(self, job_id: str) -> str | None:
        """Mark a job cancelled (queued) or cancelling (running).

        Returns the resulting status, or None if the job is missing / already terminal.
        """
        if not self.available() or not job_id:
            return None
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT status FROM ppt_agent_job WHERE id=%s FOR UPDATE",
                        (job_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None
                    current = str(row.get("status") or "")
                    if current in {"complete", "error", "cancelled"}:
                        return current
                    if current in {"queued", "pending"}:
                        cur.execute(
                            """
                            UPDATE ppt_agent_job
                            SET status='cancelled',
                                message=%s,
                                error=NULL,
                                worker_id=NULL,
                                claimed_at=NULL
                            WHERE id=%s
                            """,
                            ("用户已取消生成", job_id),
                        )
                        return "cancelled"
                    # Mid-run on a worker: cooperative cancel flag.
                    cur.execute(
                        """
                        UPDATE ppt_agent_job
                        SET status='cancelling',
                            message=%s
                        WHERE id=%s
                          AND status NOT IN ('complete', 'error', 'cancelled')
                        """,
                        ("正在取消生成…", job_id),
                    )
                    return "cancelling" if cur.rowcount else current
        except Exception:
            logger.exception("request_cancel failed for %s", job_id)
            return None


job_store = JobStore()


def row_to_session_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "file_path": Path(row["file_path"]),
        "source_type": row.get("source_type") or "pdf",
        "file_name": row.get("file_name") or "",
        "file_size": int(row.get("file_size") or 0),
        "owner_key": row.get("owner_key"),
        "owner_user_id": row.get("owner_user_id"),
        "owner_name": row.get("owner_name"),
        "owner_tenant_id": row.get("owner_tenant_id"),
    }


def row_to_job_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "status": row.get("status") or "pending",
        "progress": float(row.get("progress") or 0),
        "message": row.get("message") or "",
        "error": row.get("error"),
        "slides_completed": int(row.get("slides_completed") or 0),
        "total_slides": int(row.get("total_slides") or 0),
        "output_path": row.get("output_path"),
        "project_dir": row.get("project_dir"),
        "parent_job_id": row.get("parent_job_id"),
        "provider": row.get("provider"),
        "model_name": row.get("model_name"),
        "base_url": row.get("base_url"),
        "canvas_format": row.get("canvas_format"),
        "style": row.get("style"),
        "render_engine": row.get("render_engine"),
        "language": row.get("language"),
        "detail_level": row.get("detail_level"),
        "instruction": row.get("instruction"),
        "owner_key": row.get("owner_key"),
        "owner_user_id": row.get("owner_user_id"),
        "owner_name": row.get("owner_name"),
        "owner_tenant_id": row.get("owner_tenant_id"),
        "events": [],
        "last_seq": 0,
        "feedback_history": [],
    }
