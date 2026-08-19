"""Session and job lifecycle management.

Persistence strategy:

    The in-memory dict is the source of truth. ``session_state.json`` is
    just a snapshot used to recover Job/Session metadata across server
    restarts. Writing the full snapshot on every event update is wasteful
    (an active job emits hundreds of progress events; each one used to
    rewrite a multi-MB JSON), so the snapshot is *debounced*:

      * ``record_event`` / ``update_job`` / ``create_*`` mark the state
        dirty in-memory, then schedule a flush via ``_request_flush``;
      * a single background task drains the dirty flag every
        ``settings.persist_debounce_ms``, writing one consolidated JSON;
      * if asyncio is not running yet (e.g. unit-test imports), we fall
        back to an immediate synchronous write so behaviour stays correct.

    Worst case on a hard crash we lose the last 200ms of *metadata*
    snapshots. Events themselves are still in memory; they would also be
    lost on a crash, which is acceptable: a fresh-restarted server marks
    in-flight jobs as errored anyway via ``_mark_orphaned_running_jobs``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


# Maximum number of recent events kept on disk per job, used for replay
# when a websocket reconnects after a transient drop.
EVENT_RING_SIZE = 256


@dataclass
class Session:
    """A user upload session."""

    id: str
    file_path: Path
    source_type: str  # "pdf" or "latex"
    file_name: str
    file_size: int
    owner_key: str | None = None
    owner_user_id: str | None = None
    owner_name: str | None = None
    owner_tenant_id: str | None = None


@dataclass
class Job:
    """A generation job."""

    id: str
    session_id: str
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    slides_completed: int = 0
    total_slides: int = 0
    output_path: str | None = None
    error: str | None = None
    project_dir: str | None = None
    # For refine jobs: reference to the parent job that produced the project
    parent_job_id: str | None = None
    # Accumulated feedback history for refine iterations (list of strings)
    feedback_history: list[str] = field(default_factory=list)
    provider: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    canvas_format: str | None = None
    style: str | None = None
    render_engine: str | None = None
    language: str | None = None
    detail_level: str | None = None
    instruction: str | None = None
    owner_key: str | None = None
    owner_user_id: str | None = None
    owner_name: str | None = None
    owner_tenant_id: str | None = None
    # Bounded ring buffer of recent events with monotonically increasing
    # ``seq`` ids. Persisted to disk so a reconnecting client can ask for
    # everything after its last seen seq.
    events: list[dict] = field(default_factory=list)
    last_seq: int = 0


class SessionManager:
    """Manages sessions and jobs in memory."""

    def __init__(self) -> None:
        self._state_file = settings.runtime_dir / "session_state.json"
        self._session_dir = settings.runtime_dir / "sessions"
        self._job_dir = settings.runtime_dir / "jobs"
        self._sessions: dict[str, Session] = {}
        self._jobs: dict[str, Job] = {}
        self._ws_queues: dict[str, list[asyncio.Queue]] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        # Debounced persistence — see module docstring.
        self._dirty: bool = False
        self._flush_task: asyncio.Task[None] | None = None
        self._flush_event: asyncio.Event | None = None
        self._load_state()
        self._hydrate_jobs_from_sidecars()
        self._mark_orphaned_running_jobs()

    def create_session(
        self,
        file_path: Path,
        source_type: str,
        file_name: str,
        file_size: int,
        session_id: str | None = None,
        owner_key: str | None = None,
        owner_user_id: str | None = None,
        owner_name: str | None = None,
        owner_tenant_id: str | None = None,
    ) -> Session:
        session_id = session_id or uuid.uuid4().hex[:12]
        session = Session(
            id=session_id,
            file_path=file_path,
            source_type=source_type,
            file_name=file_name,
            file_size=file_size,
            owner_key=owner_key,
            owner_user_id=owner_user_id,
            owner_name=owner_name,
            owner_tenant_id=owner_tenant_id,
        )
        self._sessions[session_id] = session
        # Sidecar is the cross-process source of truth for upload sessions.
        # Uvicorn multi-worker keeps separate in-memory dicts; generate may
        # land on a different worker than upload without this file.
        self._write_session_sidecar(session)
        self._db_upsert_session(session)
        self._persist_state()
        return session

    def get_session(self, session_id: str) -> Session | None:
        if not session_id:
            return None
        session = self._sessions.get(session_id)
        if session is not None:
            return session
        session = self._hydrate_session(session_id)
        if session is not None:
            return session
        return self._hydrate_session_from_db(session_id)

    def create_job(self, session_id: str) -> Job:
        job_id = uuid.uuid4().hex[:12]
        session = self.get_session(session_id)
        job = Job(
            id=job_id,
            session_id=session_id,
            owner_key=session.owner_key if session else None,
            owner_user_id=session.owner_user_id if session else None,
            owner_name=session.owner_name if session else None,
            owner_tenant_id=session.owner_tenant_id if session else None,
        )
        self._jobs[job_id] = job
        self._write_job_sidecar(job)
        self._db_upsert_job(job)
        self._persist_state()
        return job

    def create_refine_job(
        self,
        parent_job_id: str,
        feedback: str,
        project_dir: str | None = None,
    ) -> Job | None:
        """Create a refine job derived from *parent_job_id*."""
        parent = self.get_job(parent_job_id)
        if parent is None or not parent.project_dir:
            return None

        job_id = uuid.uuid4().hex[:12]
        history = list(parent.feedback_history) + [feedback]

        job = Job(
            id=job_id,
            session_id=parent.session_id,
            project_dir=project_dir or parent.project_dir,
            parent_job_id=parent_job_id,
            feedback_history=history,
            provider=parent.provider,
            model_name=parent.model_name,
            base_url=parent.base_url,
            canvas_format=parent.canvas_format,
            style=parent.style,
            render_engine=parent.render_engine,
            language=parent.language,
            detail_level=parent.detail_level,
            instruction=parent.instruction,
            owner_key=parent.owner_key,
            owner_user_id=parent.owner_user_id,
            owner_name=parent.owner_name,
            owner_tenant_id=parent.owner_tenant_id,
        )
        self._jobs[job_id] = job
        self._write_job_sidecar(job)
        self._db_upsert_job(job)
        self._persist_state()
        return job

    def get_job(self, job_id: str) -> Job | None:
        if not job_id:
            return None
        job = self._jobs.get(job_id)
        if job is not None:
            # Worker updates progress in another process + MySQL. Always merge
            # fresher DB fields so API polling does not stick on "queued".
            self._refresh_job_from_db(job)
            return job
        job = self._hydrate_job(job_id)
        if job is not None:
            self._refresh_job_from_db(job)
            return job
        return self._hydrate_job_from_db(job_id)

    def list_jobs(self) -> list[Job]:
        """Return a stable snapshot of known jobs for read-only API views."""
        # Ensure disk sidecars are visible even if the shared state snapshot
        # was truncated or written by an older process revision.
        self._hydrate_jobs_from_sidecars()
        return list(self._jobs.values())

    def list_sessions(self) -> list[Session]:
        """Return a stable snapshot of upload sessions for read-only API views."""
        return list(self._sessions.values())

    def claim_legacy_owner(
        self,
        *,
        owner_key: str,
        owner_user_id: str | None,
        owner_name: str | None,
        owner_tenant_id: str | None,
    ) -> int:
        """Attach owner metadata to jobs created before auth isolation.

        This is intentionally narrow: it only fills blank ownership fields and
        never changes a job/session that already belongs to a user.
        """
        if not owner_key:
            return 0

        changed = 0
        for session in self._sessions.values():
            if session.owner_key:
                continue
            session.owner_key = owner_key
            session.owner_user_id = owner_user_id
            session.owner_name = owner_name
            session.owner_tenant_id = owner_tenant_id
            changed += 1

        for job in self._jobs.values():
            if job.owner_key:
                continue
            job.owner_key = owner_key
            job.owner_user_id = owner_user_id
            job.owner_name = owner_name
            job.owner_tenant_id = owner_tenant_id
            changed += 1

        if changed:
            self._persist_state()
        return changed

    def is_job_running(self, job_id: str) -> bool:
        """True if there is a live asyncio task for *job_id*."""
        task = self._tasks.get(job_id)
        return bool(task and not task.done())

    def register_task(self, job_id: str, task: asyncio.Task[Any]) -> None:
        self._tasks[job_id] = task

        def _cleanup(_: asyncio.Task[Any]) -> None:
            current = self._tasks.get(job_id)
            if current is task:
                self._tasks.pop(job_id, None)

        task.add_done_callback(_cleanup)

    def cancel_job(self, job_id: str) -> bool:
        # Prefer the scheduler when it's been wired in: it knows about both
        # running tasks *and* still-queued ones (which we can't reach via
        # ``self._tasks``). Falls through to legacy task cancellation when
        # the scheduler module isn't loaded (early startup, tests).
        cancelled_locally = False
        try:
            from backend.runtime.scheduler import get_scheduler

            if get_scheduler().cancel(job_id):
                cancelled_locally = True
        except Exception:
            pass

        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
            cancelled_locally = True

        job = self.get_job(job_id)
        if job is not None and job.status in {"complete", "error", "cancelled"}:
            return True

        # Queue mode: the pipeline runs in orep-ppt-worker (another process).
        # There is no in-API asyncio.Task to cancel — write a DB cancel flag
        # that the worker watches, and update local/sidecar status for the UI.
        db_status: str | None = None
        try:
            from backend.store.job_store import job_store

            if job_store.available():
                db_status = job_store.request_cancel(job_id)
        except Exception:
            logger.exception("DB cancel request failed for job %s", job_id)

        if cancelled_locally:
            self.mark_job_cancelled(job_id, "用户已取消生成")
            return True

        if db_status in {"cancelled", "cancelling"}:
            if db_status == "cancelled":
                self.mark_job_cancelled(job_id, "用户已取消生成")
            else:
                # Cooperative cancel: worker will abort and finalize as cancelled.
                self.update_job(
                    job_id,
                    status="cancelling",
                    message="正在取消生成…",
                )
            return True

        if job is not None and job.status in {
            "queued",
            "pending",
            "running",
            "parsing",
            "research",
            "content_cards",
            "strategy",
            "generation",
            "postprocess",
            "export",
            "cancelling",
        }:
            # No live task and no DB — still mark cancelled so the UI stops spinning.
            self.mark_job_cancelled(job_id, "用户已取消生成")
            return True

        return False

    def mark_job_cancelled(self, job_id: str, message: str = "Job cancelled") -> None:
        job = self._jobs.get(job_id)
        if not job:
            return

        self._tasks.pop(job_id, None)
        event = {
            "type": "progress",
            "job_id": job_id,
            "stage": "cancelled",
            "status": "error",
            "message": message,
            "progress": job.progress,
            "slides_completed": job.slides_completed,
            "total_slides": job.total_slides,
            "data": {
                "output_path": job.output_path,
                "project_dir": job.project_dir,
            },
        }
        self.record_event(
            job_id,
            event,
            status="cancelled",
            message=message,
            error=None,
        )

    def mark_job_interrupted(self, job_id: str, message: str = "Job interrupted by server restart") -> None:
        """Mark a job that was running before the server restarted.

        The asyncio task is gone forever; surface this to the client as an
        error so the UI doesn't spin indefinitely.
        """
        job = self._jobs.get(job_id)
        if not job:
            return
        event = {
            "type": "error",
            "job_id": job_id,
            "stage": "error",
            "status": "error",
            "message": message,
            "progress": job.progress,
            "slides_completed": job.slides_completed,
            "total_slides": job.total_slides,
            "data": {"error": message},
        }
        self.record_event(
            job_id,
            event,
            status="error",
            message=message,
            error=message,
        )

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        changed = False
        for key, value in kwargs.items():
            if hasattr(job, key) and getattr(job, key) != value:
                setattr(job, key, value)
                changed = True
        if changed:
            self._write_job_sidecar(job)
            self._db_upsert_job(job)
            self._persist_state()

    def record_event(self, job_id: str, event: dict, **job_updates: Any) -> None:
        job = self.get_job(job_id)
        if not job:
            return

        if job_updates:
            for key, value in job_updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)

        # Stamp event with a monotonic sequence id and timestamp so the
        # client can ack and ask for replay starting after any seq.
        job.last_seq += 1
        event = _compact_event(dict(event))
        event["seq"] = job.last_seq
        event["ts"] = time.time()

        job.events.append(event)
        # Cap memory: keep only the most recent ``EVENT_RING_SIZE`` events.
        if len(job.events) > EVENT_RING_SIZE:
            job.events = job.events[-EVENT_RING_SIZE:]
        self._write_job_sidecar(job)
        # DB: throttle full upserts — still update on status/progress changes.
        if job_updates or event.get("status") in {
            "started",
            "complete",
            "error",
            "cancelled",
        }:
            self._db_upsert_job(job)
        self._persist_state()

    def save_job_request_payload(
        self,
        job_id: str,
        request_payload: dict[str, Any],
        *,
        deck_type: str | None = None,
        mode: str | None = None,
        status: str | None = None,
        message: str | None = None,
    ) -> None:
        """Persist GenerationRequest JSON for DB queue workers."""
        job = self.get_job(job_id)
        if not job:
            return
        if status:
            job.status = status
        if message is not None:
            job.message = message
        self._write_job_sidecar(job)
        self._db_upsert_job(
            job,
            request_json=json.dumps(request_payload, ensure_ascii=False),
            deck_type=deck_type,
            mode=mode,
        )
        self._persist_state()

    def get_events_after(self, job_id: str, since_seq: int) -> list[dict]:
        """Return all retained events with seq > *since_seq*, in order."""
        job = self.get_job(job_id)
        if not job:
            return []
        if since_seq <= 0:
            return list(job.events)
        return [ev for ev in job.events if int(ev.get("seq", 0)) > since_seq]

    def subscribe_ws(self, job_id: str) -> asyncio.Queue:
        """Subscribe to WebSocket events for a job.

        The queue is bounded by ``settings.ws_subscriber_queue_size``; when
        full, the oldest pending frame is dropped to make room for the new
        one. This protects the producer from a single slow socket without
        introducing any cross-subscriber blocking.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=settings.ws_subscriber_queue_size)
        if job_id not in self._ws_queues:
            self._ws_queues[job_id] = []
        self._ws_queues[job_id].append(queue)
        return queue

    def unsubscribe_ws(self, job_id: str, queue: asyncio.Queue) -> None:
        if job_id in self._ws_queues:
            self._ws_queues[job_id] = [
                q for q in self._ws_queues[job_id] if q is not queue
            ]
            if not self._ws_queues[job_id]:
                self._ws_queues.pop(job_id, None)

    def delete_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session and session.file_path.exists():
            upload_dir = session.file_path.parent
            if upload_dir.exists():
                shutil.rmtree(upload_dir, ignore_errors=True)
        self._persist_state()

    def delete_job(self, job_id: str, *, delete_files: bool = True) -> bool:
        """Remove a job and, by default, its generated local workspace.

        If this was the last job for the upload session, also remove the
        uploaded source file directory.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False

        self.cancel_job(job_id)
        self._jobs.pop(job_id, None)
        self._tasks.pop(job_id, None)
        self._ws_queues.pop(job_id, None)
        try:
            sidecar = self._job_sidecar_path(job_id)
            if sidecar.exists():
                sidecar.unlink()
        except OSError:
            logger.exception("failed to remove job sidecar for %s", job_id)

        if delete_files and job.project_dir:
            self._remove_workspace_dir(Path(job.project_dir))

        if not any(other.session_id == job.session_id for other in self._jobs.values()):
            self.delete_session(job.session_id)
        else:
            self._persist_state()
        return True

    def clear(self) -> None:
        self._sessions.clear()
        self._jobs.clear()
        self._ws_queues.clear()
        self._tasks.clear()
        self._persist_state()

    def _mark_orphaned_running_jobs(self) -> None:
        """After process restart, any job left in a non-terminal state
        cannot have a live asyncio task — its work was lost. Mark such
        jobs as ``error`` so the UI stops polling for progress."""
        terminal = {"complete", "error", "cancelled", "waiting_confirmation"}
        running_states = {"pending", "parsing", "research", "strategy",
                          "content_cards", "generation", "postprocess", "export", "refine"}
        changed = False
        for job in self._jobs.values():
            if job.status in terminal:
                continue
            if job.status in running_states or job.status not in terminal:
                job.status = "error"
                if not job.error:
                    job.error = (
                        "生成服务已重启，当前任务中断。"
                        "请重新点击「开始生成 / 重新生成」；已上传资料会话通常仍可用。"
                    )
                if not job.message or job.message in {
                    "Queued for generation",
                    "Parsing source materials...",
                    "任务已入队",
                }:
                    job.message = job.error
                self._write_job_sidecar(job)
                changed = True
        if changed:
            self._persist_state()

    def _persist_state(self) -> None:
        """Debounced persistence entry point.

        From an event-loop context this only marks the state dirty and asks
        the background flusher to wake up. From a non-loop context (early
        import, tests) it falls back to the synchronous write so existing
        callers keep working.
        """
        self._dirty = True
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop yet — write synchronously so module-import-time
            # mutations still hit disk.
            self._write_state_blocking()
            self._dirty = False
            return

        if self._flush_task is None or self._flush_task.done():
            self._flush_event = asyncio.Event()
            self._flush_task = asyncio.create_task(
                self._flush_loop(), name="session-state-flusher"
            )
        if self._flush_event is not None:
            self._flush_event.set()

    async def _flush_loop(self) -> None:
        """Coalesce rapid-fire dirty flags into one disk write per window."""
        debounce = max(0.05, settings.persist_debounce_ms / 1000.0)
        try:
            while True:
                ev = self._flush_event
                if ev is None:
                    return
                await ev.wait()
                ev.clear()
                if not self._dirty:
                    continue
                # Sleep to absorb any further updates within the window.
                await asyncio.sleep(debounce)
                if not self._dirty:
                    continue
                self._dirty = False
                try:
                    # Build the snapshot on the event-loop thread so the
                    # offload worker never iterates mutable SessionManager
                    # dicts while other requests are updating them.
                    payload = self._build_state_payload()
                    from backend.runtime.offload import aoffload

                    await aoffload(self._write_payload_blocking, payload)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("session state flush failed")
                    self._dirty = True
        except asyncio.CancelledError:
            # On shutdown, write one last time so we don't lose the most
            # recent metadata if the loop is cancelled before debounce.
            if self._dirty:
                try:
                    self._write_payload_blocking(self._build_state_payload())
                except Exception:
                    logger.exception("final session state flush failed")
            raise

    def _write_state_blocking(self) -> None:
        self._write_payload_blocking(self._build_state_payload())

    def _build_state_payload(self) -> dict[str, Any]:
        return {
            "sessions": [
                self._serialize_session(session) for session in list(self._sessions.values())
            ],
            "jobs": [
                self._serialize_job(job) for job in list(self._jobs.values())
            ],
        }

    def _write_payload_blocking(self, payload: dict[str, Any]) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._state_file.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._state_file)

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        for raw_session in payload.get("sessions", []):
            session = self._session_from_raw(raw_session if isinstance(raw_session, dict) else {})
            if session is None:
                continue
            self._sessions[session.id] = session
            # Seed sidecars so multi-worker (or post-restart) get_session can
            # rehydrate without scanning the large shared state file.
            if not self._session_sidecar_path(session.id).exists():
                self._write_session_sidecar(session)

        for raw_job in payload.get("jobs", []):
            try:
                events_raw = raw_job.get("events") or []
                events: list[dict] = [ev for ev in events_raw if isinstance(ev, dict)]
                last_seq = int(raw_job.get("last_seq", 0) or 0)
                if not last_seq and events:
                    last_seq = max(int(ev.get("seq", 0) or 0) for ev in events)
                job = Job(
                    id=str(raw_job["id"]),
                    session_id=str(raw_job["session_id"]),
                    status=str(raw_job.get("status", "pending")),
                    progress=float(raw_job.get("progress", 0.0)),
                    message=str(raw_job.get("message", "")),
                    slides_completed=int(raw_job.get("slides_completed", 0)),
                    total_slides=int(raw_job.get("total_slides", 0)),
                    output_path=raw_job.get("output_path"),
                    error=raw_job.get("error"),
                    project_dir=raw_job.get("project_dir"),
                    parent_job_id=raw_job.get("parent_job_id"),
                    feedback_history=list(raw_job.get("feedback_history", [])),
                    provider=raw_job.get("provider"),
                    model_name=raw_job.get("model_name"),
                    base_url=raw_job.get("base_url"),
                    canvas_format=raw_job.get("canvas_format"),
                    style=raw_job.get("style"),
                    render_engine=raw_job.get("render_engine"),
                    language=raw_job.get("language"),
                    detail_level=raw_job.get("detail_level"),
                    instruction=raw_job.get("instruction"),
                    owner_key=raw_job.get("owner_key"),
                    owner_user_id=raw_job.get("owner_user_id"),
                    owner_name=raw_job.get("owner_name"),
                    owner_tenant_id=raw_job.get("owner_tenant_id"),
                    events=events[-EVENT_RING_SIZE:],
                    last_seq=last_seq,
                )
            except (KeyError, TypeError, ValueError):
                continue
            self._jobs[job.id] = job
            if not self._job_sidecar_path(job.id).exists():
                self._write_job_sidecar(job)

    @staticmethod
    def _serialize_session(session: Session) -> dict[str, Any]:
        return {
            "id": session.id,
            "file_path": str(session.file_path),
            "source_type": session.source_type,
            "file_name": session.file_name,
            "file_size": session.file_size,
            "owner_key": session.owner_key,
            "owner_user_id": session.owner_user_id,
            "owner_name": session.owner_name,
            "owner_tenant_id": session.owner_tenant_id,
        }

    def _job_sidecar_path(self, job_id: str) -> Path:
        return self._job_dir / f"{job_id}.json"

    def _write_job_sidecar(self, job: Job) -> None:
        """Persist a compact per-job file (authoritative for cross-restart get_job)."""
        try:
            self._job_dir.mkdir(parents=True, exist_ok=True)
            path = self._job_sidecar_path(job.id)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self._serialize_job(job), ensure_ascii=False),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except OSError:
            logger.exception("failed to write job sidecar for %s", job.id)

    def _job_from_raw(self, raw_job: dict[str, Any]) -> Job | None:
        try:
            events_raw = raw_job.get("events") or []
            events: list[dict] = [
                _compact_event(ev) for ev in events_raw if isinstance(ev, dict)
            ]
            last_seq = int(raw_job.get("last_seq", 0) or 0)
            if not last_seq and events:
                last_seq = max(int(ev.get("seq", 0) or 0) for ev in events)
            return Job(
                id=str(raw_job["id"]),
                session_id=str(raw_job["session_id"]),
                status=str(raw_job.get("status", "pending")),
                progress=float(raw_job.get("progress", 0.0)),
                message=str(raw_job.get("message", "")),
                slides_completed=int(raw_job.get("slides_completed", 0)),
                total_slides=int(raw_job.get("total_slides", 0)),
                output_path=raw_job.get("output_path"),
                error=raw_job.get("error"),
                project_dir=raw_job.get("project_dir"),
                parent_job_id=raw_job.get("parent_job_id"),
                feedback_history=list(raw_job.get("feedback_history", [])),
                provider=raw_job.get("provider"),
                model_name=raw_job.get("model_name"),
                base_url=raw_job.get("base_url"),
                canvas_format=raw_job.get("canvas_format"),
                style=raw_job.get("style"),
                render_engine=raw_job.get("render_engine"),
                language=raw_job.get("language"),
                detail_level=raw_job.get("detail_level"),
                instruction=raw_job.get("instruction"),
                owner_key=raw_job.get("owner_key"),
                owner_user_id=raw_job.get("owner_user_id"),
                owner_name=raw_job.get("owner_name"),
                owner_tenant_id=raw_job.get("owner_tenant_id"),
                events=events[-EVENT_RING_SIZE:],
                last_seq=last_seq,
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _hydrate_job(self, job_id: str) -> Job | None:
        sidecar = self._job_sidecar_path(job_id)
        if not sidecar.exists():
            return None
        try:
            raw = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(raw, dict):
            return None
        job = self._job_from_raw(raw)
        if job is None:
            return None
        self._jobs[job.id] = job
        return job

    def _hydrate_jobs_from_sidecars(self) -> None:
        if not self._job_dir.exists():
            return
        try:
            paths = list(self._job_dir.glob("*.json"))
        except OSError:
            return
        for path in paths:
            job_id = path.stem
            if job_id in self._jobs:
                continue
            self._hydrate_job(job_id)

    def _db_upsert_session(self, session: Session) -> None:
        try:
            from backend.store.job_store import job_store

            job_store.upsert_session(session)
        except Exception:
            logger.exception("db upsert session failed")

    def _db_upsert_job(
        self,
        job: Job,
        *,
        request_json: str | None = None,
        deck_type: str | None = None,
        mode: str | None = None,
    ) -> None:
        try:
            from backend.store.job_store import job_store

            job_store.upsert_job(
                job,
                request_json=request_json,
                deck_type=deck_type,
                mode=mode,
            )
        except Exception:
            logger.exception("db upsert job failed")

    def _hydrate_session_from_db(self, session_id: str) -> Session | None:
        try:
            from backend.store.job_store import job_store, row_to_session_fields

            row = job_store.get_session_row(session_id)
            if not row:
                return None
            fields = row_to_session_fields(row)
            session = Session(**fields)
            if not session.file_path.exists():
                return None
            self._sessions[session.id] = session
            self._write_session_sidecar(session)
            return session
        except Exception:
            logger.exception("hydrate session from db failed")
            return None

    def _hydrate_job_from_db(self, job_id: str) -> Job | None:
        try:
            from backend.store.job_store import job_store, row_to_job_fields

            row = job_store.get_job_row(job_id)
            if not row:
                return None
            fields = row_to_job_fields(row)
            fields["status"] = self._normalize_db_status(str(fields.get("status") or "pending"))
            job = Job(**{k: v for k, v in fields.items() if k in Job.__dataclass_fields__})
            self._jobs[job.id] = job
            self._write_job_sidecar(job)
            return job
        except Exception:
            logger.exception("hydrate job from db failed")
            return None

    @staticmethod
    def _normalize_db_status(status: str) -> str:
        """Map queue-layer statuses to agent progress statuses for the UI."""
        s = (status or "").strip().lower()
        if s == "queued":
            return "pending"
        if s == "running":
            # Prefer pipeline stage if already advanced; default pending/parsing.
            return "parsing"
        return status

    def _refresh_job_from_db(self, job: Job) -> None:
        """Overlay mutable fields from MySQL (source of truth under queue mode)."""
        try:
            from backend.store.job_store import job_store

            row = job_store.get_job_row(job.id)
            if not row:
                return
            raw = str(row.get("status") or job.status or "")
            # Always trust DB for terminal / queue lifecycle
            if raw == "queued":
                job.status = "pending"
            elif raw == "running":
                # Worker claimed; show parsing unless DB message already advanced
                msg = str(row.get("message") or "")
                if job.status in {
                    "research",
                    "content_cards",
                    "waiting_confirmation",
                    "strategy",
                    "generation",
                    "postprocess",
                    "export",
                    "complete",
                }:
                    pass  # keep more specific stage already in memory if any
                elif any(k in msg for k in ("研究", "research", "卡片", "生成", "export", "Pass")):
                    job.status = "research" if "research" in msg.lower() or "Pass" in msg else "parsing"
                else:
                    job.status = "parsing"
            else:
                job.status = raw

            if row.get("message") is not None:
                job.message = str(row.get("message") or "")
            # Prefer DB error when present
            if row.get("error"):
                job.error = row.get("error")
            job.progress = float(row.get("progress") if row.get("progress") is not None else (job.progress or 0))
            job.slides_completed = int(
                row.get("slides_completed")
                if row.get("slides_completed") is not None
                else (job.slides_completed or 0)
            )
            job.total_slides = int(
                row.get("total_slides") if row.get("total_slides") is not None else (job.total_slides or 0)
            )
            if row.get("output_path"):
                job.output_path = row.get("output_path")
            if row.get("project_dir"):
                job.project_dir = row.get("project_dir")
            if row.get("render_engine"):
                job.render_engine = row.get("render_engine")
        except Exception:
            logger.debug("refresh job from db skipped for %s", job.id, exc_info=True)

    def job_recovery_flags(self, job: Job) -> dict[str, Any]:
        """Hints for the client: resume vs full retry, session still usable."""
        session = self.get_session(job.session_id) if job.session_id else None
        session_alive = bool(
            session
            and session.file_path
            and Path(session.file_path).exists()
        )
        project_exists = bool(job.project_dir and Path(job.project_dir).exists())
        slides_done = int(job.slides_completed or 0)
        total = int(job.total_slides or 0)
        terminal_error = job.status in {"error", "cancelled"}
        can_resume = bool(
            terminal_error
            and project_exists
            and (slides_done > 0 or "重启" in str(job.error or "") or "restart" in str(job.error or "").lower())
        )
        if terminal_error and project_exists and slides_done > 0 and total > slides_done:
            can_resume = True
        can_retry = bool(session_alive or project_exists)
        return {
            "session_id": job.session_id,
            "session_alive": session_alive,
            "can_resume": can_resume,
            "can_retry": can_retry,
            "project_dir_exists": project_exists,
        }

    def _session_sidecar_path(self, session_id: str) -> Path:
        return self._session_dir / f"{session_id}.json"

    def _write_session_sidecar(self, session: Session) -> None:
        try:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            path = self._session_sidecar_path(session.id)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(self._serialize_session(session), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except OSError:
            logger.exception("failed to write session sidecar for %s", session.id)

    def _session_from_raw(self, raw_session: dict[str, Any]) -> Session | None:
        try:
            return Session(
                id=str(raw_session["id"]),
                file_path=Path(raw_session["file_path"]),
                source_type=str(raw_session["source_type"]),
                file_name=str(raw_session["file_name"]),
                file_size=int(raw_session["file_size"]),
                owner_key=raw_session.get("owner_key"),
                owner_user_id=raw_session.get("owner_user_id"),
                owner_name=raw_session.get("owner_name"),
                owner_tenant_id=raw_session.get("owner_tenant_id"),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _hydrate_session(self, session_id: str) -> Session | None:
        """Reload a session created by another process / worker.

        Prefer the small per-session sidecar. Fall back to reconstructing from
        the upload directory when the sidecar is missing (legacy uploads).
        """
        sidecar = self._session_sidecar_path(session_id)
        if sidecar.exists():
            try:
                raw = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw = None
            if isinstance(raw, dict):
                session = self._session_from_raw(raw)
                if session is not None:
                    # Drop broken file pointers so generate fails clearly.
                    if session.file_path.exists():
                        self._sessions[session.id] = session
                        return session

        # Legacy / partial: rebuild metadata from the upload folder when possible.
        upload_dir = settings.workspaces_dir / "uploads" / session_id
        if not upload_dir.is_dir():
            return None
        candidates = [
            path
            for path in sorted(upload_dir.iterdir())
            if path.is_file() and path.name not in {".DS_Store"}
        ]
        if not candidates:
            # materials/prepare stores a zip next to prepared_materials/
            for path in sorted(upload_dir.rglob("*")):
                if path.is_file() and path.suffix.lower() in {".zip", ".pdf", ".tex", ".tgz", ".gz"}:
                    candidates.append(path)
                    break
        if not candidates:
            return None
        file_path = candidates[0]
        suffix = file_path.suffix.lower()
        if file_path.name.endswith(".tar.gz"):
            source_type = "latex"
        elif suffix == ".pdf":
            source_type = "pdf"
        elif suffix in {".tex", ".zip", ".tgz", ".gz"}:
            source_type = "latex"
        else:
            source_type = "pdf"
        try:
            file_size = int(file_path.stat().st_size)
        except OSError:
            file_size = 0
        session = Session(
            id=session_id,
            file_path=file_path,
            source_type=source_type,
            file_name=file_path.name,
            file_size=file_size,
        )
        self._sessions[session.id] = session
        # Persist sidecar so ownership can be attached by claim paths later.
        self._write_session_sidecar(session)
        return session

    @staticmethod
    def _serialize_job(job: Job) -> dict[str, Any]:
        payload = asdict(job)
        # Persist a bounded slice of recent events so reconnecting clients
        # can replay any frames they missed during the disconnect.
        # Always compact — a single HTML/SVG payload in events previously
        # ballooned session_state.json past 400MB and blocked multi-worker
        # startups for minutes.
        payload["events"] = [
            _compact_event(ev) for ev in list(job.events[-EVENT_RING_SIZE:])
        ]
        payload["last_seq"] = job.last_seq
        return payload

    @staticmethod
    def _remove_workspace_dir(path: Path) -> None:
        try:
            target = path.resolve()
            workspace_root = settings.workspaces_dir.resolve()
            target.relative_to(workspace_root)
        except (OSError, ValueError):
            logger.warning("refusing to delete workspace outside root: %s", path)
            return
        if target == workspace_root:
            logger.warning("refusing to delete workspace root: %s", target)
            return
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


_EVENT_KEEP_KEYS = {
    "seq",
    "stage",
    "status",
    "type",
    "message",
    "progress",
    "ts",
    "timestamp",
    "slide",
    "page",
    "slides_completed",
    "total_slides",
    "error",
}


def _compact_event(event: dict[str, Any] | Any) -> dict[str, Any]:
    """Keep only progress metadata; drop HTML/SVG/base64 payloads."""
    if not isinstance(event, dict):
        return {"message": str(event)[:500]}
    compact: dict[str, Any] = {}
    for key in _EVENT_KEEP_KEYS:
        if key not in event:
            continue
        value = event[key]
        if isinstance(value, str) and len(value) > 800:
            compact[key] = value[:800] + "…"
        else:
            compact[key] = value
    # Preserve a short stage label if the only useful field was nested.
    if not compact and event:
        compact["message"] = str(event.get("message") or event.get("type") or "event")[:500]
    return compact


def _offer_to_queue(queue: asyncio.Queue, event: dict) -> None:
    """Drop-oldest publish onto a bounded subscriber queue."""
    try:
        queue.put_nowait(event)
        return
    except asyncio.QueueFull:
        pass
    # Drop the oldest pending frame and retry. Best effort: if the queue
    # is concurrently drained by the consumer between checks, just bail.
    try:
        queue.get_nowait()
    except asyncio.QueueEmpty:
        return
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:  # pragma: no cover — extremely unlikely race
        pass


# Global singleton
session_manager = SessionManager()
