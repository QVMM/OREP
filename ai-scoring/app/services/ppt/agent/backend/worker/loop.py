"""DB-queue worker loop: claim ppt_agent_job rows and run the pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
import uuid

logger = logging.getLogger(__name__)


def _worker_id() -> str:
    return os.getenv("PPT_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


async def process_claimed_row(row: dict) -> None:
    from backend.api.endpoints.generate import _run_generation_job
    from backend.session.manager import session_manager
    from backend.store.job_store import job_store
    from backend.worker.request_codec import generation_request_from_dict

    job_id = row["id"]
    raw = row.get("request_json") or ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        session_manager.update_job(
            job_id,
            status="error",
            error="任务请求数据损坏，请重新生成",
            message="任务请求数据损坏，请重新生成",
        )
        return

    # User may have cancelled while still queued — honor before starting work.
    pre_status = job_store.get_job_status(job_id)
    if pre_status in {"cancelled", "cancelling"}:
        session_manager.mark_job_cancelled(job_id, "用户已取消生成")
        logger.info("PPT worker skip cancelled job %s", job_id)
        return

    # Ensure in-memory job exists for progress events
    if session_manager._jobs.get(job_id) is None:
        from backend.session.manager import Job

        job = Job(
            id=job_id,
            session_id=row["session_id"],
            status="pending",
            owner_key=row.get("owner_key"),
            owner_user_id=row.get("owner_user_id"),
            owner_name=row.get("owner_name"),
            owner_tenant_id=row.get("owner_tenant_id"),
            provider=row.get("provider"),
            model_name=row.get("model_name"),
            base_url=row.get("base_url"),
            canvas_format=row.get("canvas_format"),
            style=row.get("style"),
            render_engine=row.get("render_engine"),
            language=row.get("language"),
            detail_level=row.get("detail_level"),
            instruction=row.get("instruction"),
            project_dir=row.get("project_dir"),
        )
        session_manager._jobs[job_id] = job
        session_manager._write_job_sidecar(job)

    # Hydrate session for ownership consistency
    session_manager.get_session(row["session_id"])

    try:
        request = generation_request_from_dict(payload)
        request.job_id = job_id
        session_manager.update_job(job_id, status="parsing", message="Worker 开始解析资料…")

        async def _run() -> None:
            await _run_generation_job(job_id, request)

        gen_task = asyncio.create_task(_run(), name=f"ppt-job-{job_id}")

        async def _watch_cancel() -> None:
            """Cross-process cancel: API sets status=cancelling in MySQL."""
            while not gen_task.done():
                await asyncio.sleep(1.5)
                status = job_store.get_job_status(job_id)
                if status in {"cancelling", "cancelled"}:
                    logger.info("PPT worker cancelling job %s (db status=%s)", job_id, status)
                    gen_task.cancel()
                    return

        watch_task = asyncio.create_task(_watch_cancel(), name=f"ppt-cancel-{job_id}")
        try:
            await gen_task
        except asyncio.CancelledError:
            session_manager.mark_job_cancelled(job_id, "用户已取消生成")
            logger.info("PPT worker job %s cancelled by user", job_id)
        finally:
            if not watch_task.done():
                watch_task.cancel()
                try:
                    await watch_task
                except asyncio.CancelledError:
                    pass
    except asyncio.CancelledError:
        session_manager.mark_job_cancelled(job_id, "用户已取消生成")
        raise
    except Exception as exc:
        logger.exception("PPT worker failed job %s", job_id)
        # Don't overwrite an intentional cancel with a generic error.
        current = session_manager.get_job(job_id)
        if current and current.status in {"cancelled", "cancelling"}:
            session_manager.mark_job_cancelled(job_id, "用户已取消生成")
            return
        session_manager.update_job(
            job_id,
            status="error",
            error=str(exc)[:500] or "Worker 执行失败",
            message="生成失败，请重新生成",
        )


async def worker_loop(poll_seconds: float = 2.0) -> None:
    from backend.store.db import ping
    from backend.store.job_store import job_store

    worker_id = _worker_id()
    logger.info("PPT worker starting id=%s db=%s", worker_id, ping())
    # Recover jobs left mid-flight by a previous crashed worker process.
    requeued = job_store.requeue_orphaned_claimed(
        max_age_seconds=int(os.getenv("PPT_REQUEUE_AGE_SECONDS", "60"))
    )
    if requeued:
        logger.warning("PPT worker re-queued %s orphaned mid-run job(s)", requeued)
    job_store.mark_stale_running(stale_minutes=int(os.getenv("PPT_STALE_RUNNING_MINUTES", "120")))

    while True:
        try:
            # Periodically requeue stuck claims (worker crash mid-job)
            if int(time.time()) % 30 < poll_seconds:
                job_store.requeue_orphaned_claimed(
                    max_age_seconds=int(os.getenv("PPT_REQUEUE_AGE_SECONDS", "90"))
                )
            row = job_store.claim_next_job(worker_id)
            if not row:
                await asyncio.sleep(poll_seconds)
                continue
            logger.info("PPT worker claimed job %s", row.get("id"))
            await process_claimed_row(row)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("PPT worker loop iteration failed")
            await asyncio.sleep(max(poll_seconds, 3.0))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Bootstrap agent paths/env the same way as the API process.
    from app.services.ppt.agent_runtime import bootstrap_ppt_agent, startup_ppt_agent_runtime

    bootstrap_ppt_agent()

    async def _run() -> None:
        await startup_ppt_agent_runtime()
        await worker_loop()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
