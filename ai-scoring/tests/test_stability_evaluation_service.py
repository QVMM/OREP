from app.services.stability_evaluation_service import (
    evaluate_quality_report,
    validate_expert_calibration_record,
    validate_pilot_dataset_manifest,
)


def test_pilot_dataset_manifest_requires_20_samples_per_pilot_track_and_frozen_inputs():
    manifest = {
        "tracks": {
            "track_42_ai": [
                {
                    "sampleId": "ai-low-evidence-001",
                    "sampleType": "low_evidence",
                    "inputSnapshotHash": "sha256:abc",
                    "ruleVersion": "v1.2-engine-pilot",
                    "humanReferenceScore": 72,
                    "humanDeductionNotes": ["缺少稳定演示证据"],
                    "verifiableEvidencePoints": ["frame:10"],
                }
            ],
            "track_27_it": [],
        }
    }

    result = validate_pilot_dataset_manifest(manifest)

    assert result["status"] == "not_ready"
    assert result["trackStats"]["track_42_ai"]["sampleCount"] == 1
    assert "track_42_ai needs at least 20 frozen samples" in result["blockingReasons"]
    assert "track_27_it needs at least 20 frozen samples" in result["blockingReasons"]
    assert "track_27_it must cover low_evidence" in result["blockingReasons"]


def test_quality_report_flags_unstable_rule_engine_and_e4_e5_violations():
    samples = [
        {
            "sampleId": "ai-slogan-high-score",
            "trackId": "track_42_ai",
            "sampleType": "slogan_packaging",
            "humanReferenceScore": 70,
            "expertDimensionScores": {"technical": 20, "business": 18},
            "runs": [
                {
                    "ruleEngineScore": 92,
                    "oldLlmScore": 94,
                    "jsonParsed": True,
                    "unsupportedClaims": 1,
                    "needsHumanReview": True,
                    "dimensionScores": {"technical": 28, "business": 26},
                    "observationEvidence": [
                        {"observationCode": "O01", "evidenceLevel": "E5", "anchorCount": 1, "anchorAccurate": False},
                    ],
                    "deductions": ["D-low-evidence"],
                },
                {
                    "ruleEngineScore": 90,
                    "oldLlmScore": 94,
                    "jsonParsed": True,
                    "unsupportedClaims": 0,
                    "needsHumanReview": True,
                    "dimensionScores": {"technical": 27, "business": 25},
                    "observationEvidence": [
                        {"observationCode": "O01", "evidenceLevel": "E5", "anchorCount": 1, "anchorAccurate": False},
                    ],
                    "deductions": ["D-low-evidence"],
                },
            ],
        },
        {
            "sampleId": "it-stable-mid",
            "trackId": "track_27_it",
            "sampleType": "middle_score",
            "humanReferenceScore": 80,
            "expertDimensionScores": {"technical": 24, "business": 20},
            "runs": [
                {
                    "ruleEngineScore": 82,
                    "oldLlmScore": 87,
                    "jsonParsed": False,
                    "unsupportedClaims": 0,
                    "needsHumanReview": False,
                    "dimensionScores": {"technical": 24, "business": 20},
                    "observationEvidence": [
                        {"observationCode": "O01", "evidenceLevel": "E3", "anchorCount": 2, "anchorAccurate": True},
                    ],
                    "deductions": ["D-demo"],
                }
            ],
        },
    ]

    report = evaluate_quality_report(samples)

    assert report["sampleCount"] == 2
    assert report["trackDistribution"] == {"track_42_ai": 1, "track_27_it": 1}
    assert report["metrics"]["ruleEngineScoreConsistencyRate"] == 0.5
    assert report["metrics"]["jsonParseSuccessRate"] == 2 / 3
    assert report["metrics"]["unsupportedClaimRate"] == 1 / 3
    assert report["metrics"]["e4e5HardConditionViolationRate"] == 2 / 3
    assert report["metrics"]["totalScoreMae"] == 12
    assert report["status"] == "not_ready"
    assert report["failingSamples"][0]["sampleId"] == "ai-slogan-high-score"
    assert report["remediationTasks"][0]["owner"] == "规则/证据校准负责人"


def test_expert_calibration_record_requires_reviewer_reason_scope_and_type():
    invalid = {
        "sampleId": "ai-001",
        "correctionType": "score_override",
        "reason": "分数不准",
    }

    result = validate_expert_calibration_record(invalid)

    assert result["valid"] is False
    assert "reviewer is required" in result["errors"]
    assert "correctionType must be sample_annotation or rule_change_suggestion" in result["errors"]

    valid = validate_expert_calibration_record({
        "sampleId": "ai-001",
        "reviewer": "专家A",
        "reviewedAt": "2026-07-05T14:30:00+08:00",
        "correctionType": "sample_annotation",
        "reason": "E5 证据锚点不足，应降为 E3",
        "affectedObservations": ["O01"],
        "ruleVersion": "v1.2-engine-pilot",
    })

    assert valid["valid"] is True
    assert valid["errors"] == []
