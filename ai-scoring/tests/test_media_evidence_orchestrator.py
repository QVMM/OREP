import threading
import time

import pytest

from app.services.media_evidence.orchestrator import (
    EvidenceStageError,
    run_evidence_branches,
)


def test_branches_overlap_and_return_in_configured_order():
    barrier = threading.Barrier(2)

    def branch(value):
        barrier.wait(timeout=1)
        time.sleep(0.03)
        return value

    started = time.monotonic()
    result = run_evidence_branches(
        {
            "visual": lambda: branch({"visualEvidence": []}),
            "audio": lambda: branch({"transcriptSegments": []}),
        },
        max_workers=2,
        timeout_seconds=1,
    )
    elapsed = time.monotonic() - started

    assert elapsed < 0.12
    assert result["branchOrder"] == ["visual", "audio"]
    assert list(result["outputs"]) == ["visual", "audio"]
    assert set(result["metrics"]) == {"visual", "audio"}
    assert all(item["durationMs"] >= 25 for item in result["metrics"].values())


def test_branch_score_field_is_rejected_with_named_stage():
    with pytest.raises(EvidenceStageError) as exc_info:
        run_evidence_branches(
            {"visual": lambda: {"visualEvidence": [{"overallScore": 90}]}},
            max_workers=1,
            timeout_seconds=1,
        )

    assert exc_info.value.stage_key == "visual"
    assert exc_info.value.code == "contract_violation"
    assert "forbidden_score_field" in str(exc_info.value)


def test_branch_exception_is_wrapped_without_losing_stage():
    def fail():
        raise RuntimeError("provider exploded")

    with pytest.raises(EvidenceStageError) as exc_info:
        run_evidence_branches(
            {"audio": fail},
            max_workers=1,
            timeout_seconds=1,
        )

    assert exc_info.value.stage_key == "audio"
    assert exc_info.value.code == "branch_failed"
    assert "provider exploded" in str(exc_info.value)


def test_timeout_reports_the_unfinished_stage():
    def slow():
        time.sleep(0.12)
        return {"contentEvidence": []}

    with pytest.raises(EvidenceStageError) as exc_info:
        run_evidence_branches(
            {
                "quick": lambda: {"deliverySignals": []},
                "slow": slow,
            },
            max_workers=2,
            timeout_seconds=0.02,
        )

    assert exc_info.value.stage_key == "slow"
    assert exc_info.value.code == "branch_timeout"


def test_branch_outputs_are_copied_before_returning():
    original = {"transcriptSegments": []}

    result = run_evidence_branches(
        {"audio": lambda: original},
        max_workers=1,
        timeout_seconds=1,
    )
    result["outputs"]["audio"]["transcriptSegments"].append({"text": "changed"})

    assert original == {"transcriptSegments": []}
