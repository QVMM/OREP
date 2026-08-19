"""Bounded priority scheduling for expensive local model workers."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
import threading
import time
from typing import Callable, Generic, TypeVar


WorkerT = TypeVar("WorkerT")
ResultT = TypeVar("ResultT")
_PRIORITIES = {"LIVE": 0, "UPLOAD": 1, "REPAIR": 2}


class WorkerQueueFullError(RuntimeError):
    pass


class WorkerCrashedError(RuntimeError):
    pass


@dataclass
class _Task(Generic[WorkerT, ResultT]):
    priority: int
    sequence: int
    deadline: float | None
    operation: Callable[[WorkerT], ResultT]
    future: Future


class ModelWorkerPool(Generic[WorkerT]):
    """Run model operations on reusable workers with bounded waiting memory."""

    def __init__(
        self,
        worker_factory: Callable[[], WorkerT],
        *,
        worker_count: int,
        maximum_queue_size: int,
        maximum_consecutive_high_priority: int = 8,
    ) -> None:
        self._factory = worker_factory
        self._maximum_queue_size = max(0, int(maximum_queue_size))
        self._maximum_consecutive_high_priority = max(
            1, int(maximum_consecutive_high_priority)
        )
        self._condition = threading.Condition()
        self._tasks: list[_Task] = []
        self._sequence = 0
        self._closed = False
        self._high_priority_streak = 0
        self._threads = [
            threading.Thread(
                target=self._worker_loop,
                name=f"model-worker-{index + 1}",
                daemon=True,
            )
            for index in range(max(1, int(worker_count)))
        ]
        for thread in self._threads:
            thread.start()

    def submit(
        self,
        priority: str,
        operation: Callable[[WorkerT], ResultT],
        *,
        timeout_seconds: float | None = None,
    ) -> Future[ResultT]:
        priority_name = str(priority).upper()
        if priority_name not in _PRIORITIES:
            raise ValueError(f"invalid_worker_priority:{priority_name}")
        if not callable(operation):
            raise TypeError("worker_operation_must_be_callable")
        deadline = None
        if timeout_seconds is not None:
            deadline = time.monotonic() + max(0.0, float(timeout_seconds))
        future: Future[ResultT] = Future()
        with self._condition:
            if self._closed:
                raise RuntimeError("model_worker_pool_closed")
            if len(self._tasks) >= self._maximum_queue_size:
                raise WorkerQueueFullError("model_worker_queue_full")
            self._sequence += 1
            self._tasks.append(
                _Task(
                    priority=_PRIORITIES[priority_name],
                    sequence=self._sequence,
                    deadline=deadline,
                    operation=operation,
                    future=future,
                )
            )
            self._condition.notify()
        return future

    def _take_task(self) -> _Task | None:
        with self._condition:
            while not self._tasks and not self._closed:
                self._condition.wait()
            if not self._tasks:
                return None
            lower_priority = [task for task in self._tasks if task.priority > 0]
            if (
                self._high_priority_streak
                >= self._maximum_consecutive_high_priority
                and lower_priority
            ):
                selected = min(lower_priority, key=lambda item: item.sequence)
            else:
                selected = min(
                    self._tasks, key=lambda item: (item.priority, item.sequence)
                )
            self._tasks.remove(selected)
            if selected.priority == 0:
                self._high_priority_streak += 1
            else:
                self._high_priority_streak = 0
            return selected

    def _worker_loop(self) -> None:
        worker = self._factory()
        while True:
            task = self._take_task()
            if task is None:
                close = getattr(worker, "close", None)
                if callable(close):
                    close()
                return
            if task.future.cancelled():
                continue
            if task.deadline is not None and time.monotonic() > task.deadline:
                task.future.set_exception(
                    TimeoutError("worker_queue_deadline_exceeded")
                )
                continue
            try:
                result = task.operation(worker)
            except WorkerCrashedError as error:
                task.future.set_exception(error)
                close = getattr(worker, "close", None)
                if callable(close):
                    close()
                worker = self._factory()
            except BaseException as error:
                task.future.set_exception(error)
            else:
                task.future.set_result(result)

    def close(self, *, wait: bool = True) -> None:
        with self._condition:
            if self._closed:
                return
            self._closed = True
            for task in self._tasks:
                if not task.future.done():
                    task.future.set_exception(RuntimeError("model_worker_pool_closed"))
            self._tasks.clear()
            self._condition.notify_all()
        if wait:
            for thread in self._threads:
                thread.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
