import threading
import time

import pytest

from app.services.media_evidence.model_worker_pool import (
    ModelWorkerPool,
    WorkerCrashedError,
    WorkerQueueFullError,
)


def test_priority_order_is_live_then_upload_then_repair():
    gate = threading.Event()
    started = threading.Event()
    order = []
    pool = ModelWorkerPool(lambda: object(), worker_count=1, maximum_queue_size=4)
    try:
        blocker = pool.submit(
            "UPLOAD", lambda worker: (started.set(), gate.wait(2), "blocker")[-1]
        )
        assert started.wait(1)
        repair = pool.submit("REPAIR", lambda worker: order.append("repair"))
        upload = pool.submit("UPLOAD", lambda worker: order.append("upload"))
        live = pool.submit("LIVE", lambda worker: order.append("live"))
        gate.set()
        assert blocker.result(2) == "blocker"
        live.result(2)
        upload.result(2)
        repair.result(2)
        assert order == ["live", "upload", "repair"]
    finally:
        pool.close()


def test_queue_is_bounded_while_worker_is_busy():
    gate = threading.Event()
    started = threading.Event()
    pool = ModelWorkerPool(lambda: object(), worker_count=1, maximum_queue_size=1)
    try:
        running = pool.submit(
            "UPLOAD", lambda worker: (started.set(), gate.wait(2), "done")[-1]
        )
        assert started.wait(1)
        queued = pool.submit("UPLOAD", lambda worker: "queued")
        with pytest.raises(WorkerQueueFullError):
            pool.submit("UPLOAD", lambda worker: "overflow")
        gate.set()
        assert running.result(2) == "done"
        assert queued.result(2) == "queued"
    finally:
        pool.close()


def test_expired_queued_request_never_reaches_model_worker():
    gate = threading.Event()
    started = threading.Event()
    called = []
    pool = ModelWorkerPool(lambda: object(), worker_count=1, maximum_queue_size=2)
    try:
        running = pool.submit(
            "LIVE", lambda worker: (started.set(), gate.wait(2), "done")[-1]
        )
        assert started.wait(1)
        expired = pool.submit(
            "UPLOAD", lambda worker: called.append(True), timeout_seconds=0.02
        )
        time.sleep(0.04)
        gate.set()
        running.result(2)
        with pytest.raises(TimeoutError, match="worker_queue_deadline_exceeded"):
            expired.result(2)
        assert called == []
    finally:
        pool.close()


def test_crashed_worker_is_replaced_before_next_request():
    created = []

    def factory():
        worker = {"generation": len(created) + 1}
        created.append(worker)
        return worker

    pool = ModelWorkerPool(factory, worker_count=1, maximum_queue_size=2)
    try:
        crashed = pool.submit(
            "UPLOAD",
            lambda worker: (_ for _ in ()).throw(WorkerCrashedError("pipe_closed")),
        )
        with pytest.raises(WorkerCrashedError):
            crashed.result(2)
        recovered = pool.submit("UPLOAD", lambda worker: worker["generation"])
        assert recovered.result(2) == 2
        assert len(created) == 2
    finally:
        pool.close()


def test_starvation_guard_runs_waiting_upload_during_live_flood():
    gate = threading.Event()
    started = threading.Event()
    order = []
    pool = ModelWorkerPool(
        lambda: object(),
        worker_count=1,
        maximum_queue_size=8,
        maximum_consecutive_high_priority=2,
    )
    try:
        blocker = pool.submit(
            "LIVE", lambda worker: (started.set(), gate.wait(2), None)[-1]
        )
        assert started.wait(1)
        upload = pool.submit("UPLOAD", lambda worker: order.append("upload"))
        lives = [
            pool.submit("LIVE", lambda worker, i=i: order.append(f"live-{i}"))
            for i in range(4)
        ]
        gate.set()
        blocker.result(2)
        upload.result(2)
        for future in lives:
            future.result(2)
        assert order.index("upload") <= 2
    finally:
        pool.close()
