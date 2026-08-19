from app.services.pipeline_payloads import build_rule_engine_shadow_payload


def test_rule_engine_shadow_scales_evidence_ratio_by_observation_max_score():
    result = {
        "ai_score": {"overall_score": 63.25},
        "evidence_extraction": {
            "trackName": "商贸赛道",
            "ruleVersion": "v1.2-engine-draft",
            "ruleHash": "commerce-rule-hash",
            "evidenceItems": [
                {
                    "evidenceId": "E01",
                    "sourceType": "transcript",
                    "sourceRef": "timeline@00:30",
                    "text": "团队展示了客户证据收集和渠道运营过程。",
                    "confidence": 0.82,
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": "O01",
                    "evidenceIds": ["E01"],
                    "evidenceLevel": "E3",
                    "confidence": 0.82,
                    "supportSummary": "有流程和运营过程证据。",
                    "suggestedScoreCap": 0.7,
                },
                {
                    "observationCode": "O04",
                    "evidenceIds": [],
                    "evidenceLevel": "E0",
                    "confidence": 0.2,
                    "supportSummary": "质量控制证据缺失。",
                    "suggestedScoreCap": 0.2,
                },
            ],
            "deductionCandidates": [
                {
                    "deductionId": "D01",
                    "observationCode": "O01",
                    "deductedPoints": 2,
                    "reason": "缺少独立验真记录。",
                    "evidenceIds": ["E01"],
                }
            ],
        },
    }

    payload = build_rule_engine_shadow_payload(result)

    assert payload["ruleEngineScore"] == 9.6
    assert payload["scoreDiff"] == -53.65
    assert len(payload["evidenceAnchors"]) == 1
    assert payload["evidenceAnchors"][0]["id"] == 1
    assert payload["evidenceAnchors"][0]["startMs"] == 30000

    by_code = {item["observationCode"]: item for item in payload["observations"]}
    assert by_code["O01"]["maxScore"] == 10.0
    assert by_code["O01"]["dimensionCode"] == "skill_level"
    assert by_code["O01"]["scoreCap"] == 7.0
    assert by_code["O01"]["rawScore"] == 7.0
    assert by_code["O01"]["finalScore"] == 7.0
    assert by_code["O01"]["evidenceAnchorIds"] == [1]
    assert by_code["O04"]["maxScore"] == 13.0
    assert by_code["O04"]["scoreCap"] == 2.6
    assert by_code["O04"]["finalScore"] == 2.6

    assert payload["deductions"] == []
    assert payload["diagnosticDeductions"][0]["deductedPoints"] == 2.0
    assert payload["diagnosticDeductions"][0]["dimensionCode"] == "skill_level"
    assert payload["diagnosticDeductions"][0]["evidenceAnchorIds"] == [1]


def test_rule_engine_shadow_uses_track_rule_deduction_score_when_llm_omits_points():
    result = {
        "ai_score": {"overall_score": 70},
        "evidence_extraction": {
            "trackName": "商贸赛道",
            "ruleVersion": "v1.2-engine-draft",
            "ruleHash": "commerce-rule-hash",
            "evidenceItems": [
                {
                    "evidenceId": "E04",
                    "sourceType": "transcript",
                    "sourceRef": "timeline@04:00",
                    "text": "团队只口头提到质量控制，但没有展示质量记录。",
                }
            ],
            "observationEvidence": [
                {
                    "observationCode": "O04",
                    "evidenceIds": ["E04"],
                    "evidenceLevel": "E3",
                    "suggestedScoreCap": 0.7,
                    "supportSummary": "有质量控制口头说明。",
                }
            ],
            "deductionCandidates": [
                {
                    "deductionId": "D-missing-quality-record",
                    "observationCode": "O04",
                    "reason": "质量控制证据不足，仅有口头说明。",
                    "evidenceIds": ["E04"],
                }
            ],
        },
    }

    payload = build_rule_engine_shadow_payload(result)

    assert payload["deductions"] == []
    assert payload["diagnosticDeductions"][0]["deductedPoints"] == 2.0
    assert payload["diagnosticDeductions"][0]["maxRecoverablePoints"] == 1.5
    assert payload["observations"][0]["scoreCap"] == 9.1
    assert payload["observations"][0]["finalScore"] == 9.1
    assert payload["ruleEngineScore"] == 9.1
