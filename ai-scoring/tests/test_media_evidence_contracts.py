import copy

import pytest

from app.services.media_evidence.contracts import (
    EvidenceContractError,
    finalize_evidence_package,
)


def minimal_package(**overrides):
    package = {
        "sessionId": "26",
        "sourceType": "UPLOAD_VIDEO",
        "transcriptSegments": [
            {
                "segmentNo": 1,
                "startMs": 1000,
                "endMs": 2000,
                "text": "原始证据",
                "rawSpeakerId": None,
            }
        ],
        "speakerTurns": [],
        "speakerIdentities": [],
        "visualEvidence": [],
        "deliverySignals": [],
        "contentEvidence": [],
        "integrity": {
            "audioCoverage": 0.8,
            "timestampMonotonic": True,
            "diarizationStatus": "unavailable",
        },
        "processingMetrics": {},
    }
    package.update(overrides)
    return package


def test_finalize_package_rejects_nested_official_score_fields():
    package = minimal_package()
    package["visualEvidence"] = [{"text": "画面", "deductedPoints": 2}]

    with pytest.raises(EvidenceContractError, match="forbidden_score_field"):
        finalize_evidence_package(package)


def test_finalize_package_rejects_generic_internal_score_fields():
    package = minimal_package()
    package["deliverySignals"] = [{"type": "gesture", "score": 7}]

    with pytest.raises(EvidenceContractError, match="forbidden_score_field"):
        finalize_evidence_package(package)


def test_snapshot_hash_ignores_runtime_metrics_but_changes_with_evidence():
    first = finalize_evidence_package(
        minimal_package(processingMetrics={"durationMs": 10, "requestId": "a"})
    )
    second = finalize_evidence_package(
        minimal_package(processingMetrics={"durationMs": 999, "requestId": "b"})
    )
    changed = minimal_package()
    changed["transcriptSegments"][0]["text"] = "不同证据"
    third = finalize_evidence_package(changed)

    assert first["snapshotHash"] == second["snapshotHash"]
    assert first["snapshotHash"] != third["snapshotHash"]


def test_snapshot_hash_is_stable_without_mutating_input():
    package = minimal_package()
    original = copy.deepcopy(package)

    first = finalize_evidence_package(package)
    second = finalize_evidence_package(package)

    assert first["snapshotHash"] == second["snapshotHash"]
    assert package == original
    assert "snapshotHash" not in package


def test_final_package_requires_valid_time_ranges():
    package = minimal_package()
    package["transcriptSegments"][0]["startMs"] = 2000
    package["transcriptSegments"][0]["endMs"] = 1000

    with pytest.raises(EvidenceContractError, match="invalid_time_range"):
        finalize_evidence_package(package)


def test_final_package_requires_evidence_collections_to_be_lists():
    package = minimal_package(visualEvidence={"text": "not-a-list"})

    with pytest.raises(EvidenceContractError, match="invalid_collection"):
        finalize_evidence_package(package)


def test_final_package_sets_version_and_final_status():
    result = finalize_evidence_package(minimal_package())

    assert result["contractVersion"] == "media-evidence-v1"
    assert result["status"] == "FINAL"
    assert result["snapshotHash"].startswith("sha256:")
