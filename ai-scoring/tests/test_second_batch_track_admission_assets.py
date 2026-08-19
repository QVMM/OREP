import json
from pathlib import Path

from app.services.track_expansion_plan_service import (
    load_track_expansion_plan,
    validate_track_expansion_candidate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RUBRIC_DIR = REPO_ROOT / "ai-scoring" / "app" / "rubrics"
EVALUATION_DIR = REPO_ROOT / "ai-scoring" / "app" / "evaluation" / "track_admission"
SECOND_BATCH_TRACKS = {
    "09": "track_09_civil_design_management_v1_2_engine_draft.json",
    "10": "track_10_civil_construction_v1_2_engine_draft.json",
    "11": "track_11_water_conservancy_v1_2_engine_draft.json",
    "07": "track_07_energy_power_v1_2_engine_draft.json",
    "08": "track_08_materials_v1_2_engine_draft.json",
    "21": "track_21_chemical_technology_v1_2_engine_draft.json",
    "18": "track_18_automotive_manufacturing_repair_v1_2_engine_draft.json",
    "15": "track_15_rail_transport_v1_2_engine_draft.json",
    "16": "track_16_air_transport_v1_2_engine_draft.json",
    "17": "track_17_ship_transport_v1_2_engine_draft.json",
    "19": "track_19_road_pipeline_transport_v1_2_engine_draft.json",
}


def load_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def test_second_batch_admission_assets_exist_and_meet_sample_mix_gate():
    for track_id in SECOND_BATCH_TRACKS:
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


def test_second_batch_admission_assets_pass_candidate_gate():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
    for track_id, rule_file in SECOND_BATCH_TRACKS.items():
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


def test_second_batch_plan_entries_reference_admission_assets_without_pilot_promotion():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
    planned_tracks = {
        track["trackId"]: track
        for batch in plan["batches"]
        for track in batch["tracks"]
        if track["trackId"] in SECOND_BATCH_TRACKS
    }

    for track_id, track in planned_tracks.items():
        assert track["status"] == "pilot_generated"
        assert track["structuredRuleStatus"] == "pilot_generated"
        assert track["pilotPromotion"]["activeAllowed"] is False
        for field in ("admissionManifest", "ruleAdmissionAudit", "qualityReport"):
            assert (REPO_ROOT / track[field]).exists(), f"{track_id} missing {field}"
