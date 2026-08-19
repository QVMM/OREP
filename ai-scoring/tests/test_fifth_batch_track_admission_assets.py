import json
from pathlib import Path

from app.services.track_expansion_plan_service import (
    load_track_expansion_plan,
    validate_track_expansion_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUBRIC_DIR = REPO_ROOT / "ai-scoring" / "app" / "rubrics"
EVALUATION_DIR = REPO_ROOT / "ai-scoring" / "app" / "evaluation" / "track_admission"
FIFTH_BATCH_TRACKS = {
    "32": "track_32_finance_v1_2_engine_draft.json",
    "33": "track_33_commerce_trade_v1_2_engine_draft.json",
    "34": "track_34_logistics_supply_chain_v1_2_engine_draft.json",
    "35": "track_35_tourism_v1_2_engine_draft.json",
    "36": "track_36_catering_v1_2_engine_draft.json",
    "37": "track_37_art_design_v1_2_engine_draft.json",
    "38": "track_38_performing_arts_v1_2_engine_draft.json",
    "39": "track_39_journalism_communication_v1_2_engine_draft.json",
    "40": "track_40_education_sports_v1_2_engine_draft.json",
    "41": "track_41_public_safety_management_service_v1_2_engine_draft.json",
    "22": "track_22_light_industry_v1_2_engine_draft.json",
    "23": "track_23_textile_apparel_v1_2_engine_draft.json",
    "24": "track_24_food_grain_v1_2_engine_draft.json",
}


def load_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def test_fifth_batch_admission_assets_exist_and_meet_sample_mix_gate():
    for track_id in FIFTH_BATCH_TRACKS:
        manifest = load_json(EVALUATION_DIR / f"track_{track_id}_admission_manifest.generated.json")
        audit = load_json(EVALUATION_DIR / f"track_{track_id}_rule_admission_audit.generated.json")
        quality = load_json(EVALUATION_DIR / f"track_{track_id}_quality_report.generated.json")

        samples = manifest["samples"]
        sample_types = [sample["sampleType"] for sample in samples]

        assert manifest["trackId"] == track_id
        assert manifest["sourceMode"] == "synthetic_from_local_markdown"
        assert len(samples) == 10
        assert sample_types.count("low_evidence") >= 2
        assert sample_types.count("middle_score") >= 2
        assert sample_types.count("high_score") >= 2
        assert sample_types.count("demo_failure") + sample_types.count("material_missing") >= 1
        assert all(sample["inputSnapshotHash"].startswith("sha256:") for sample in samples)
        assert all(sample["frozenInputFiles"] for sample in samples)
        assert audit["status"] == "approved"
        assert audit["reviewer"]
        assert audit["reviewedAt"]
        assert quality["status"] == "ready"
        assert quality["sampleCount"] == 10


def test_fifth_batch_admission_assets_pass_candidate_gate():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
    for track_id, rule_file in FIFTH_BATCH_TRACKS.items():
        rule = load_json(RUBRIC_DIR / rule_file)
        manifest = load_json(EVALUATION_DIR / f"track_{track_id}_admission_manifest.generated.json")
        audit = load_json(EVALUATION_DIR / f"track_{track_id}_rule_admission_audit.generated.json")
        quality = load_json(EVALUATION_DIR / f"track_{track_id}_quality_report.generated.json")

        result = validate_track_expansion_candidate(
            rule,
            samples=manifest["samples"],
            audit_record=audit,
            quality_report=quality,
            global_gate=plan["globalAdmissionGate"],
        )

        assert result["status"] == "ready"
        assert result["blockingReasons"] == []


def test_fifth_batch_plan_entries_reference_admission_assets_as_pilot_generated_only():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
    planned_tracks = {
        track["trackId"]: track
        for batch in plan["batches"]
        for track in batch["tracks"]
        if track["trackId"] in FIFTH_BATCH_TRACKS
    }

    for track_id, track in planned_tracks.items():
        assert track["status"] == "pilot_generated"
        assert track["structuredRuleStatus"] == "pilot_generated"
        assert track["pilotPromotion"]["activeAllowed"] is False
        for field in ("admissionManifest", "ruleAdmissionAudit", "qualityReport"):
            assert (REPO_ROOT / track[field]).exists(), f"{track_id} missing {field}"
