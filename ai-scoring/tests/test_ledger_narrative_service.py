import unittest

from app.services.scoring.ledger_narrative_service import (
    apply_rule_ledger_narrative,
    apply_rule_ledger_to_pipeline_result,
)


class LedgerNarrativeServiceTest(unittest.TestCase):
    def test_rewrites_official_score_fields_from_rule_ledger(self):
        ai_score = {
            "overall_score": 88.0,
            "raw_overall_score": 90.0,
            "dimensions": {"skill": {"score": 88}},
            "highlights": ["模型夸夸其谈"],
            "critical_issues": ["模型随便扣的问题"],
            "action_plan": [{"title": "无关建议", "problem": "无关联"}],
            "jury_review": {"summary": "评委文字"},
        }
        rule_payload = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 49.5,
            "llmRawScore": 88.0,
            "ruleEngineScore": 49.5,
            "performanceGap": 40.0,
            "evidenceLimitedGap": 7.5,
            "effectiveHardPenalty": 2.0,
            "scoringFingerprint": "rule-fp",
            "ruleFingerprint": "rule-fp",
            "evidenceSnapshotHash": "ev-fp",
            "scoreInstanceId": "inst-1",
            "dimensionScores": {"skill": 31.0, "value": 18.5},
            "dimensionMaxScores": {"skill": 60.0, "value": 40.0},
            "reconciliation": {"totalLoss": 50.5},
            "observations": [
                {
                    "observationCode": "O01",
                    "observationName": "现场演示",
                    "maxScore": 20,
                    "finalScore": 18,
                    "evidenceLevel": "E4",
                },
                {
                    "observationCode": "O02",
                    "observationName": "客户验证",
                    "maxScore": 20,
                    "finalScore": 4,
                    "evidenceLevel": "E1",
                },
            ],
            "lossLedger": [
                {
                    "observationCode": "O02",
                    "observationName": "客户验证",
                    "dimensionCode": "value",
                    "lossType": "evidence_limited",
                    "points": 7.5,
                    "reason": "缺少可核验证据",
                    "causeCode": "O02:evidence_limited",
                },
                {
                    "observationCode": "O02",
                    "observationName": "客户验证",
                    "dimensionCode": "value",
                    "lossType": "performance_gap",
                    "points": 8.0,
                    "reason": "现场只讲到一半",
                    "causeCode": "O02:performance_gap",
                },
                {
                    "observationCode": "O03",
                    "observationName": "演示稳定性",
                    "dimensionCode": "skill",
                    "lossType": "hard_violation",
                    "points": 2.0,
                    "reason": "演示中断超时",
                    "causeCode": "O03:hard",
                    "penaltyRuleCode": "DEMO_FAIL",
                },
            ],
        }

        result = apply_rule_ledger_narrative(ai_score, rule_payload, evidence_extraction={
            "trackName": "商贸赛道",
        })

        self.assertEqual(result["overall_score"], 49.5)
        self.assertEqual(result["raw_overall_score"], 88.0)
        self.assertEqual(result["score_authority"], "structured_rule_engine")
        self.assertEqual(result["narrative_source"], "rule-ledger-narrative-v1")
        self.assertEqual(result["dimensions"]["skill"]["score"], 31.0)
        self.assertEqual(result["dimensions"]["skill"]["source"], "structured_rule_engine")
        self.assertTrue(any("现场演示表现较好" in item for item in result["highlights"]))
        self.assertTrue(any("演示中断超时" in item for item in result["critical_issues"]))
        self.assertEqual(result["improvement_priorities"][0]["observationCode"], "O03")
        self.assertEqual(result["action_plan"][0]["sourceKind"], "rule-ledger-narrative")
        self.assertIn("规则引擎权威分 49.5", result["score_overview"]["diagnosis"])
        self.assertEqual(result["jury_review"]["score_authority"], "diagnostic_only")

    def test_keeps_model_actions_that_already_link_observations(self):
        ai_score = {
            "overall_score": 70,
            "action_plan": [{
                "title": "模型已关联动作",
                "problem": "证据弱",
                "observationCode": "O02",
                "method": "补客户验收",
            }],
        }
        rule_payload = {
            "scoreAuthority": "structured_rule_engine",
            "finalScore": 60,
            "dimensionScores": {},
            "dimensionMaxScores": {},
            "observations": [],
            "lossLedger": [{
                "observationCode": "O02",
                "observationName": "客户验证",
                "lossType": "evidence_limited",
                "points": 5,
                "reason": "缺证据",
                "causeCode": "O02:evidence_limited",
            }],
        }
        result = apply_rule_ledger_narrative(ai_score, rule_payload)
        self.assertEqual(result["action_plan"][0]["title"], "模型已关联动作")
        self.assertEqual(result["action_plan"][0]["observationCode"], "O02")

    def test_pipeline_helper_skips_when_extraction_not_publishable(self):
        pipeline = {
            "ai_score": {"overall_score": 77},
            "evidence_extraction": {
                "status": "review_required",
                "extractionQuality": {"publicationEligible": False},
            },
        }
        updated = apply_rule_ledger_to_pipeline_result(pipeline)
        self.assertEqual(updated["ai_score"]["score_authority"], "review_required")
        self.assertEqual(updated["ai_score"]["overall_score"], 77)


if __name__ == "__main__":
    unittest.main()
