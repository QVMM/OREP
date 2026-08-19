import hashlib
import json
from pathlib import Path

from app.services.track_expansion_plan_service import (
    load_track_expansion_plan,
    validate_track_expansion_candidate,
)


RUBRIC_DIR = Path(__file__).resolve().parents[1] / "app" / "rubrics"
THIRD_BATCH_NEW_RULES = {
    "01": "track_01_modern_agriculture_v1_2_engine_draft.json",
    "02": "track_02_forestry_v1_2_engine_draft.json",
    "03": "track_03_animal_husbandry_aquaculture_v1_2_engine_draft.json",
    "04": "track_04_geological_survey_mapping_v1_2_engine_draft.json",
    "05": "track_05_resource_mining_v1_2_engine_draft.json",
    "06": "track_06_ecological_environment_governance_v1_2_engine_draft.json",
}
REQUIRED_LEVELS = {"E0", "E1", "E2", "E3", "E4", "E5"}


def load_rule(file_name):
    with (RUBRIC_DIR / file_name).open(encoding="utf-8") as f:
        return json.load(f)


def test_third_batch_rules_are_promoted_to_pilot_but_not_active():
    for file_name in THIRD_BATCH_NEW_RULES.values():
        rule = load_rule(file_name)

        assert rule["status"] == "pilot"
        assert rule["status"] != "active"
        assert rule["pilotPromotion"]["activeAllowed"] is False
        assert rule["sourceType"] == "track_inference"
        assert rule["sourceMarkdown"].endswith(f"{rule['trackName']}.md")
        assert len(rule["dimensions"]) == 5
        assert len(rule["observations"]) == 15
        assert {level["level"] for level in rule["evidenceLevels"]} == REQUIRED_LEVELS
        assert set(rule["evidenceCaps"]) == REQUIRED_LEVELS
        assert rule["qualityGates"]["minimumAdmissionSamplesPerTrack"] == 10

        observation_codes = {observation["observationCode"] for observation in rule["observations"]}
        assert len(observation_codes) == 15
        for observation in rule["observations"]:
            assert observation["trackDefinition"]
            assert len(observation["acceptableEvidence"]) >= 3
            assert observation["deductionRules"]
            assert observation["recoveryRules"]
            assert observation["sourceType"] == "track_inference"


def test_third_batch_rule_hashes_match_canonical_payloads():
    for file_name in THIRD_BATCH_NEW_RULES.values():
        rule = load_rule(file_name)
        declared_hash = rule["ruleHash"]
        payload = dict(rule)
        payload["ruleHash"] = ""
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

        assert declared_hash == "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_third_batch_rules_pass_candidate_gate_with_ready_assets():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
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

    for file_name in THIRD_BATCH_NEW_RULES.values():
        result = validate_track_expansion_candidate(
            load_rule(file_name),
            samples=samples,
            audit_record={"status": "approved", "reviewer": "stage8-auditor", "reviewedAt": "2026-07-05"},
            quality_report={"status": "ready"},
            global_gate=plan["globalAdmissionGate"],
        )

        assert result["status"] == "ready"
        assert result["blockingReasons"] == []


def test_third_batch_plan_entries_reference_generated_draft_rules():
    plan = load_track_expansion_plan(RUBRIC_DIR / "track_expansion_plan_v1.json")
    planned_tracks = {
        track["trackId"]: track
        for batch in plan["batches"]
        for track in batch["tracks"]
        if track["trackId"] in THIRD_BATCH_NEW_RULES
    }

    assert set(planned_tracks) == set(THIRD_BATCH_NEW_RULES)
    for track_id, track in planned_tracks.items():
        assert track["status"] == "pilot_generated"
        assert track["structuredRuleStatus"] == "pilot_generated"
        assert track["pilotPromotion"]["activeAllowed"] is False
        assert track["structuredRuleFile"].endswith(THIRD_BATCH_NEW_RULES[track_id])
        assert (Path(__file__).resolve().parents[2] / track["structuredRuleFile"]).exists()
