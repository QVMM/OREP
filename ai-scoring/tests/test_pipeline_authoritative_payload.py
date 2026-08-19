import unittest
import copy
from unittest.mock import patch

from app.services.pipeline_payloads import build_rule_engine_shadow_payload


class PipelineAuthoritativePayloadTest(unittest.TestCase):
    @patch("app.services.pipeline_payloads.load_pilot_track_rule")
    def test_builds_authoritative_result_with_distinct_base_and_cap(self, load_rule):
        load_rule.return_value = {
            "observations": [{
                "observationCode": "O1",
                "observationName": "客户验证",
                "dimensionCode": "market",
                "dimensionName": "市场",
                "maxScore": 20,
                "trackDefinition": "完整说明客户验证过程并形成可复核证据闭环。",
                "requiredInfo": ["客户对象", "验证方法", "验证结果"],
                "acceptableEvidence": ["访谈原始记录", "签字验收单"],
                "trainingTaskTemplate": "补齐客户验证过程与原始材料。",
                "deductionRules": [{"ruleCode": "missing-proof", "deductionScore": 3}],
                "recoveryRules": [{"recoverableScore": 2}],
            }]
        }
        result = {
            "ai_score": {"overall_score": 88, "raw_overall_score": 90},
            "evidence_extraction": {
                "trackName": "test-track",
                "ruleVersion": "v1",
                "ruleHash": "rule-hash",
                "evidenceItems": [],
                "observationEvidence": [{
                    "observationCode": "O1",
                    "suggestedBaseScore": 16,
                    "suggestedScoreCap": 0.7,
                    "evidenceLevel": "E2",
                }],
                "deductionCandidates": [{
                    "observationCode": "O1",
                    "deductionRuleCode": "missing-proof",
                    "ruleDescription": "缺少可复核客户材料",
                }],
                "recoveryCandidates": [{
                    "observationCode": "O1",
                    "suggestion": "补充客户访谈原始记录和签字验收单",
                }],
            },
        }

        payload = build_rule_engine_shadow_payload(result)

        self.assertEqual(payload["scoreAuthority"], "structured_rule_engine")
        self.assertEqual(payload["finalScore"], 14.0)
        self.assertEqual(payload["ruleEngineScore"], 14.0)
        self.assertEqual(payload["observations"][0]["baseScore"], 16.0)
        self.assertEqual(payload["observations"][0]["scoreCap"], 14.0)
        self.assertEqual(
            payload["observations"][0]["trackDefinition"],
            "完整说明客户验证过程并形成可复核证据闭环。",
        )
        self.assertEqual(
            payload["observations"][0]["requiredInfo"],
            ["客户对象", "验证方法", "验证结果"],
        )
        self.assertEqual(
            payload["observations"][0]["acceptableEvidence"],
            ["访谈原始记录", "签字验收单"],
        )
        self.assertEqual(
            payload["observations"][0]["trainingTaskTemplate"],
            "补齐客户验证过程与原始材料。",
        )
        self.assertEqual(payload["deductions"], [])
        self.assertEqual(payload["diagnosticDeductions"][0]["deductionId"], "O1:missing-proof")
        self.assertEqual(payload["diagnosticDeductions"][0]["reason"], "缺少可复核客户材料")
        self.assertEqual(
            payload["diagnosticDeductions"][0]["requiredFix"],
            "补充客户访谈原始记录和签字验收单",
        )
        self.assertEqual(payload["reconciliation"]["dimensionScoreTotal"], 14.0)
        self.assertEqual(payload["reconciliation"]["totalLoss"], 6.0)

    @patch("app.services.pipeline_payloads.load_pilot_track_rule")
    def test_only_explicit_event_backed_hard_violation_is_subtractive(self, load_rule):
        load_rule.return_value = {
            "observations": [{
                "observationCode": "O1",
                "observationName": "现场规范",
                "dimensionCode": "delivery",
                "maxScore": 20,
                "deductionRules": [],
                "recoveryRules": [],
            }]
        }
        result = {
            "ai_score": {"overall_score": 18},
            "evidence_extraction": {
                "trackName": "test-track",
                "ruleVersion": "v2",
                "ruleHash": "rule-hash",
                "evidenceItems": [{
                    "evidenceId": "e1",
                    "sourceType": "system",
                    "sourceRef": "system@duration",
                    "text": "路演超过赛事规定时长60秒",
                }],
                "observationEvidence": [{
                    "observationCode": "O1",
                    "suggestedBaseScore": 18,
                    "suggestedScoreCap": 1,
                    "evidenceLevel": "E5",
                }],
                "deductionCandidates": [{
                    "deductionId": "EVENT-TIMEOUT",
                    "observationCode": "O1",
                    "penaltyType": "hard_violation",
                    "penaltyRuleCode": "COMP-TIME-01",
                    "causeCode": "O1:COMP-TIME-01:timeout",
                    "triggerFact": "路演超过赛事规定时长60秒",
                    "deductedPoints": 3,
                    "evidenceIds": ["e1"],
                }],
            },
        }

        payload = build_rule_engine_shadow_payload(result)

        self.assertEqual(payload["finalScore"], 15.0)
        self.assertEqual(payload["deductions"][0]["scoreEffect"], "subtractive")
        self.assertEqual(payload["diagnosticDeductions"], [])
        self.assertEqual(payload["lossLedger"][-1]["lossType"], "hard_violation")

    @patch("app.services.pipeline_payloads.load_pilot_track_rule")
    def test_scoring_fingerprint_includes_competition_binding(self, load_rule):
        load_rule.return_value = {
            "observations": [{
                "observationCode": "O1",
                "dimensionCode": "D1",
                "maxScore": 10,
                "deductionRules": [],
                "recoveryRules": [],
            }]
        }
        result = {
            "ai_score": {"overall_score": 8},
            "competition_binding": {
                "competitionName": "赛事A",
                "trackName": "商贸赛道",
                "groupName": "高职组",
                "ruleVersion": "v2",
                "ruleHash": "rule-hash",
            },
            "evidence_extraction": {
                "trackName": "商贸赛道",
                "ruleVersion": "v2",
                "ruleHash": "rule-hash",
                "observationEvidence": [{
                    "observationCode": "O1",
                    "suggestedBaseScore": 8,
                    "suggestedScoreCap": 1,
                }],
            },
        }

        first = build_rule_engine_shadow_payload(result)
        changed = copy.deepcopy(result)
        changed["competition_binding"]["groupName"] = "中职组"
        second = build_rule_engine_shadow_payload(changed)

        self.assertEqual(len(first["scoringFingerprint"]), 64)
        self.assertEqual(first["scoringFingerprint"], first["ruleFingerprint"])
        self.assertEqual(len(first["evidenceSnapshotHash"]), 64)
        self.assertEqual(len(first["scoreInstanceId"]), 64)
        self.assertNotEqual(first["scoringFingerprint"], second["scoringFingerprint"])
        self.assertNotEqual(first["scoreInstanceId"], second["scoreInstanceId"])

    @patch("app.services.pipeline_payloads.load_pilot_track_rule")
    def test_evidence_snapshot_changes_with_evidence_but_rule_fingerprint_stable(self, load_rule):
        load_rule.return_value = {
            "observations": [{
                "observationCode": "O1",
                "dimensionCode": "D1",
                "maxScore": 10,
                "deductionRules": [],
                "recoveryRules": [],
            }]
        }
        base = {
            "ai_score": {"overall_score": 8},
            "competition_binding": {
                "competitionName": "赛事A",
                "trackName": "商贸赛道",
                "groupName": "高职组",
                "ruleVersion": "v2",
                "ruleHash": "rule-hash",
            },
            "evidence_extraction": {
                "trackName": "商贸赛道",
                "ruleVersion": "v2",
                "ruleHash": "rule-hash",
                "status": "completed",
                "extractionQuality": {"publicationEligible": True},
                "evidenceItems": [{
                    "evidenceId": "e1",
                    "sourceType": "transcript",
                    "sourceRef": "transcript@01:00",
                    "text": "开场介绍",
                }],
                "observationEvidence": [{
                    "observationCode": "O1",
                    "evidenceLevel": "E2",
                    "performanceLevel": "partial",
                    "evidenceIds": ["e1"],
                    "suggestedBaseScore": 5,
                    "suggestedScoreCap": 5,
                }],
            },
        }
        first = build_rule_engine_shadow_payload(base)
        changed = copy.deepcopy(base)
        changed["evidence_extraction"]["evidenceItems"][0]["text"] = "结尾总结与数据复盘，转化率提升 12%"
        changed["evidence_extraction"]["observationEvidence"][0]["evidenceLevel"] = "E3"
        second = build_rule_engine_shadow_payload(changed)

        self.assertEqual(first["ruleFingerprint"], second["ruleFingerprint"])
        self.assertEqual(first["scoringFingerprint"], second["scoringFingerprint"])
        self.assertNotEqual(first["evidenceSnapshotHash"], second["evidenceSnapshotHash"])
        self.assertNotEqual(first["scoreInstanceId"], second["scoreInstanceId"])


if __name__ == "__main__":
    unittest.main()
