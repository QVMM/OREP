import json
from pathlib import Path

from app.services.track_expansion_plan_service import (
    load_track_expansion_plan,
    validate_track_expansion_candidate,
    validate_track_expansion_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_DIR = REPO_ROOT / "42赛道梯度评分规则v1.2-证据审查版"
PLAN_PATH = REPO_ROOT / "ai-scoring" / "app" / "rubrics" / "track_expansion_plan_v1.json"


def test_stage8_plan_covers_all_42_markdown_tracks_in_batches():
    plan = load_track_expansion_plan(PLAN_PATH)

    result = validate_track_expansion_plan(plan, MARKDOWN_DIR)

    assert result["status"] == "ready"
    assert result["trackCount"] == 42
    assert result["batchCount"] == 5
    assert result["blockingReasons"] == []
    assert result["trackStatusCounts"]["pilot_completed"] == 2
    assert result["trackStatusCounts"]["pilot_generated"] == 40
    assert result["trackStatusCounts"].get("planned", 0) == 0


def test_stage8_plan_keeps_per_track_admission_gates_above_plan_minimums():
    plan = load_track_expansion_plan(PLAN_PATH)

    assert plan["globalAdmissionGate"]["minimumAdmissionSamplesPerTrack"] == 10
    assert plan["globalAdmissionGate"]["recommendedSamplesBeforeActive"] >= 30
    assert plan["globalAdmissionGate"]["minimumLowEvidenceSamples"] == 2
    assert plan["globalAdmissionGate"]["minimumMiddleSamples"] == 2
    assert plan["globalAdmissionGate"]["minimumHighEvidenceSamples"] == 2
    assert plan["globalAdmissionGate"]["requiresRuleAdmissionAudit"] is True
    assert plan["globalAdmissionGate"]["requiresHumanSpotCheck"] is True
    assert plan["globalAdmissionGate"]["requiresQualityReport"] is True

    for batch in plan["batches"]:
        assert batch["tracks"]
        for track in batch["tracks"]:
            assert track["trackId"]
            assert track["trackName"].endswith("赛道")
            assert track["status"] in {"pilot_completed", "pilot_generated", "planned"}
            assert track["sourceMarkdown"].endswith(f"{track['trackName']}.md")
            assert track["evidenceFocus"]
            assert track["admissionGate"] == plan["globalAdmissionGate"]


def test_new_track_candidate_cannot_be_admitted_with_name_only_rule():
    plan = load_track_expansion_plan(PLAN_PATH)
    name_only_rule = {
        "trackId": "26",
        "trackName": "电子电器与集成电路赛道",
        "status": "draft",
        "observations": [],
    }

    result = validate_track_expansion_candidate(
        name_only_rule,
        samples=[],
        audit_record={},
        quality_report={},
        global_gate=plan["globalAdmissionGate"],
    )

    assert result["status"] == "not_ready"
    assert "rule must contain 15 observations" in result["blockingReasons"]
    assert "track-specific acceptable evidence is required" in result["blockingReasons"]
    assert "at least 10 admission samples are required" in result["blockingReasons"]
    assert "rule admission audit is required" in result["blockingReasons"]


def test_new_track_candidate_passes_when_rule_samples_audit_and_report_are_ready():
    plan = load_track_expansion_plan(PLAN_PATH)
    pilot_rule = json.loads(
        (REPO_ROOT / "ai-scoring" / "app" / "rubrics" / "track_27_it_v1_2_engine_pilot.json").read_text(
            encoding="utf-8"
        )
    )
    samples = [
        {"sampleId": "high-1", "sampleType": "high_score"},
        {"sampleId": "high-2", "sampleType": "high_score"},
        {"sampleId": "middle-1", "sampleType": "middle_score"},
        {"sampleId": "middle-2", "sampleType": "middle_score"},
        {"sampleId": "low-evidence-1", "sampleType": "low_evidence"},
        {"sampleId": "low-evidence-2", "sampleType": "low_evidence"},
        {"sampleId": "demo-failure-1", "sampleType": "demo_failure"},
        {"sampleId": "low-1", "sampleType": "low_score"},
        {"sampleId": "material-1", "sampleType": "material_sufficient"},
        {"sampleId": "boundary-1", "sampleType": "boundary_dispute"},
    ]

    result = validate_track_expansion_candidate(
        pilot_rule,
        samples=samples,
        audit_record={"status": "approved", "reviewer": "stage8-auditor", "reviewedAt": "2026-07-05"},
        quality_report={"status": "ready"},
        global_gate=plan["globalAdmissionGate"],
    )

    assert result["status"] == "ready"
    assert result["blockingReasons"] == []
