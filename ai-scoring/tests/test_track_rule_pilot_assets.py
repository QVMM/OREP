import hashlib
import json
from pathlib import Path


RUBRIC_DIR = Path(__file__).resolve().parents[1] / "app" / "rubrics"
PILOT_FILES = [
    "track_42_ai_v1_2_engine_pilot.json",
    "track_27_it_v1_2_engine_pilot.json",
]
REQUIRED_LEVELS = ["E0", "E1", "E2", "E3", "E4", "E5"]
ALLOWED_SOURCE_TYPES = {"official", "track_inference", "orep_training"}


def load_rule(file_name):
    with (RUBRIC_DIR / file_name).open(encoding="utf-8") as f:
        return json.load(f)


def test_track_rule_schema_v2_exists_with_required_top_level_fields():
    schema_path = RUBRIC_DIR / "track_rule_schema_v2.json"

    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)

    required = set(schema["required"])
    assert {
        "trackId",
        "trackName",
        "ruleVersion",
        "ruleHash",
        "dimensions",
        "observations",
        "evidenceLevels",
        "evidenceCaps",
        "deductionRules",
        "recoveryRules",
        "riskPatterns",
        "sourceType",
    }.issubset(required)


def test_pilot_track_rules_cover_15_observations_and_e0_to_e5_caps():
    for file_name in PILOT_FILES:
        rule = load_rule(file_name)
        assert rule["status"] == "pilot"
        assert rule["sourceType"] in ALLOWED_SOURCE_TYPES
        assert len(rule["dimensions"]) == 5
        assert len(rule["observations"]) == 15
        assert {level["level"] for level in rule["evidenceLevels"]} == set(REQUIRED_LEVELS)
        assert set(rule["evidenceCaps"]) == set(REQUIRED_LEVELS)
        assert rule["evidenceCaps"] == {
            "E0": 0.20,
            "E1": 0.30,
            "E2": 0.50,
            "E3": 0.70,
            "E4": 0.85,
            "E5": 1.00,
        }

        observation_codes = set()
        for observation in rule["observations"]:
            observation_codes.add(observation["observationCode"])
            assert observation["observationName"]
            assert observation["dimensionCode"]
            assert observation["maxScore"] > 0
            assert observation["trackDefinition"]
            assert observation["requiredInfo"]
            assert observation["acceptableEvidence"]
            assert set(observation["evidenceCaps"]) == set(REQUIRED_LEVELS)
            assert observation["deductionRules"]
            assert observation["recoveryRules"]
            assert observation["reviewTriggers"]
            assert all(item["sourceType"] in ALLOWED_SOURCE_TYPES for item in observation["deductionRules"])
            assert all(item["sourceType"] in ALLOWED_SOURCE_TYPES for item in observation["recoveryRules"])
        assert len(observation_codes) == 15


def test_rule_hash_matches_canonical_payload_without_rule_hash():
    for file_name in PILOT_FILES:
        path = RUBRIC_DIR / file_name
        rule = load_rule(file_name)
        declared_hash = rule["ruleHash"]
        payload = dict(rule)
        payload["ruleHash"] = ""
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

        assert declared_hash == "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
