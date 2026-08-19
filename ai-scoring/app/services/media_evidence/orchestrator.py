"""Bounded parallel execution for independent evidence extraction branches."""

from __future__ import annotations

import copy
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Callable

from .contracts import EvidenceContractError, assert_no_score_fields


@dataclass
class EvidenceStageError(RuntimeError):
    stage_key: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}:{self.stage_key}:{self.message}"


def _run_branch(operation: Callable[[], dict]) -> tuple[dict, int]:
    started = time.monotonic()
    result = operation()
    duration_ms = max(0, int(round((time.monotonic() - started) * 1000)))
    return result, duration_ms


def run_evidence_branches(
    branches: dict[str, Callable[[], dict]],
    *,
    max_workers: int,
    timeout_seconds: float,
) -> dict:
    """Run independent branches concurrently and merge in declaration order."""

    if not isinstance(branches, dict) or not branches:
        raise ValueError("branches_required")
    if timeout_seconds <= 0:
        raise ValueError("positive_timeout_required")

    branch_order = list(branches)
    worker_count = max(1, min(int(max_workers), len(branch_order)))
    executor = ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="media-evidence",
    )
    futures: dict[str, Future] = {
        key: executor.submit(_run_branch, branches[key]) for key in branch_order
    }

    try:
        _, unfinished = wait(futures.values(), timeout=float(timeout_seconds))
        if unfinished:
            unfinished_keys = [key for key in branch_order if futures[key] in unfinished]
            for future in unfinished:
                future.cancel()
            stage_key = unfinished_keys[0]
            raise EvidenceStageError(stage_key, "branch_timeout", "stage deadline exceeded")

        outputs: dict[str, dict] = {}
        metrics: dict[str, dict] = {}
        for key in branch_order:
            try:
                branch_output, duration_ms = futures[key].result()
            except EvidenceStageError:
                raise
            except Exception as exc:
                raise EvidenceStageError(key, "branch_failed", str(exc)) from exc

            if not isinstance(branch_output, dict):
                raise EvidenceStageError(key, "invalid_output", "branch output must be an object")
            try:
                assert_no_score_fields(branch_output)
            except EvidenceContractError as exc:
                raise EvidenceStageError(key, "contract_violation", str(exc)) from exc

            outputs[key] = copy.deepcopy(branch_output)
            metrics[key] = {"durationMs": duration_ms}

        return {
            "branchOrder": branch_order,
            "outputs": outputs,
            "metrics": metrics,
        }
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
