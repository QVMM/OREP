import json
from pathlib import Path

from app.services.track_expansion_plan_service import (
    load_track_expansion_plan,
    summarize_stage8_final_readiness,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUBRIC_DIR = REPO_ROOT / "ai-scoring" / "app" / "rubrics"
ADMISSION_DIR = REPO_ROOT / "ai-scoring" / "app" / "evaluation" / "track_admission"
MARKDOWN_DIR = REPO_ROOT / "42赛道梯度评分规则v1.2-证据审查版"
PLAN_PATH = RUBRIC_DIR / "track_expansion_plan_v1.json"


def test_stage8_final_readiness_summarizes_all_tracks_without_allowing_active():
    plan = load_track_expansion_plan(PLAN_PATH)

    summary = summarize_stage8_final_readiness(
        plan,
        rubric_dir=RUBRIC_DIR,
        admission_dir=ADMISSION_DIR,
        markdown_dir=MARKDOWN_DIR,
    )

    assert summary["status"] == "pilot_ready_not_active"
    assert summary["trackCount"] == 42
    assert summary["structuredRuleCount"] == 42
    assert summary["pilotCompletedCount"] == 2
    assert summary["pilotGeneratedCount"] == 40
    assert summary["activeReadyCount"] == 0
    assert summary["activeBlockedCount"] == 40
    assert summary["missingStructuredRuleFiles"] == []
    assert summary["missingAdmissionAssets"] == []
    assert summary["tracksAllowedActive"] == []
    assert summary["realSampleRevalidationRequired"] is True
    assert summary["realSampleRevalidationBlockers"]


def test_stage8_final_readiness_detects_missing_generated_admission_asset():
    plan = load_track_expansion_plan(PLAN_PATH)
    broken_plan = json.loads(json.dumps(plan))
    first_generated = next(
        track
        for batch in broken_plan["batches"]
        for track in batch["tracks"]
        if track["status"] == "pilot_generated"
    )
    first_generated["admissionManifest"] = "ai-scoring/app/evaluation/track_admission/missing_manifest.json"

    summary = summarize_stage8_final_readiness(
        broken_plan,
        rubric_dir=RUBRIC_DIR,
        admission_dir=ADMISSION_DIR,
        markdown_dir=MARKDOWN_DIR,
    )

    assert summary["status"] == "not_ready"
    assert summary["missingAdmissionAssets"] == [
        {
            "trackId": first_generated["trackId"],
            "trackName": first_generated["trackName"],
            "assetType": "admissionManifest",
            "path": first_generated["admissionManifest"],
        }
    ]
