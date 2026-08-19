import json
import unittest

from app.services.evidence_extraction_service import (
    build_extraction_prompt,
    extract_evidence_from_llm_payload,
    load_pilot_track_rule,
)


class AchievementAssessmentTest(unittest.TestCase):
    def test_normalizes_categorical_achievement_to_pre_deduction_base_score(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "claims": [],
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceType": "material",
                "sourceRef": "report.pdf#page=2",
                "text": "提供了测试数据、部署日志和运行记录",
            }],
            "observationEvidence": [{
                "observationCode": "O01",
                "evidenceIds": ["e1"],
                "evidenceLevel": "E3",
                "achievementLevel": "substantial",
                "achievementReason": "已覆盖测试、部署与运行，但安全策略未完整展示",
            }],
            "deductionCandidates": [],
            "recoveryCandidates": [],
            "riskFlags": [],
            "extractionQuality": {},
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)
        item = {row["observationCode"]: row for row in extraction["observationEvidence"]}["O01"]

        self.assertEqual(item["achievementLevel"], "substantial")
        self.assertEqual(item["achievementRatio"], 0.8)
        self.assertEqual(item["suggestedBaseScore"], 8.0)
        self.assertIn("安全策略", item["achievementReason"])

    def test_missing_model_observation_has_no_achievement(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        extraction = extract_evidence_from_llm_payload("{}", rule)
        item = extraction["observationEvidence"][0]

        self.assertEqual(item["achievementLevel"], "not_demonstrated")
        self.assertEqual(item["achievementRatio"], 0.0)
        self.assertEqual(item["suggestedBaseScore"], 0.0)

    def test_prompt_separates_achievement_from_evidence_strength(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        prompt = build_extraction_prompt(rule, {"transcript": "test"})

        self.assertIn("achievementLevel", prompt)
        self.assertIn("达成程度与证据强度必须分开判断", prompt)
        self.assertIn("sourceType", prompt)
        self.assertIn("confidence", prompt)
        self.assertIn("performanceLevel", prompt)
        self.assertIn("performanceReason 禁止使用缺少第三方证明", prompt)
        self.assertIn("证据不足不得进入 deductionCandidates", prompt)
        self.assertIn("penaltyRuleCode、triggerFact、evidenceIds", prompt)

    def test_external_evidence_absence_cannot_reduce_performance_score(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "evidenceItems": [],
            "observationEvidence": [{
                "observationCode": "O01",
                "evidenceIds": [],
                "evidenceLevel": "E0",
                "performanceLevel": "partial",
                "performanceReason": "缺少第三方验收证明和订单附件",
            }],
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)
        item = extraction["observationEvidence"][0]

        self.assertEqual(item["performanceLevel"], "not_assessed")
        self.assertEqual(item["performanceAssessmentStatus"], "review_required_evidence_contamination")
        self.assertEqual(item["suggestedBaseScore"], item["maxScore"])
        self.assertIn("第三方验收证明", item["evidenceReason"])
        self.assertNotIn("第三方", item["performanceReason"])

    def test_keyed_observation_mapping_and_short_code_are_normalized(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceType": "timeline",
                "sourceRef": "timeline@03:00",
                "text": "现场展示了核心操作流程",
            }],
            "observationEvidence": {
                "O1": {
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E2",
                    "performanceLevel": "partial",
                    "performanceReason": "核心操作已展示，但步骤不完整",
                }
            },
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)
        first = extraction["observationEvidence"][0]

        self.assertEqual(first["observationCode"], "O01")
        self.assertEqual(first["sourceType"], "llm_extraction")
        self.assertEqual(first["performanceLevel"], "partial")
        self.assertEqual(first["evidenceReason"], "已找到相关现场依据，但仍需补充更完整、可复核的证明材料")
        self.assertNotIn("E2", first["evidenceReason"])
        self.assertNotIn("上限", first["evidenceReason"])
        self.assertEqual(extraction["extractionQuality"]["modelObservationCount"], 1)
        self.assertEqual(extraction["extractionQuality"]["matchedObservationCount"], 1)
        self.assertFalse(extraction["extractionQuality"]["publicationEligible"])
        self.assertEqual(extraction["status"], "review_required")

    def test_document_only_absence_is_moved_but_missing_operation_stays_performance(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceRef": "timeline@03:00",
                "text": "现场表达与操作片段",
            }],
            "observationEvidence": {
                "O1": {
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E2",
                    "performanceLevel": "partial",
                    "performanceReason": "职业表达清晰，但未展示完整记录或文档",
                },
                "O2": {
                    "evidenceIds": ["e1"],
                    "evidenceLevel": "E2",
                    "performanceLevel": "partial",
                    "performanceReason": "未展示完整操作流程或记录",
                },
            },
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)
        by_code = {item["observationCode"]: item for item in extraction["observationEvidence"]}

        self.assertEqual(by_code["O01"]["performanceLevel"], "not_assessed")
        self.assertEqual(by_code["O02"]["performanceLevel"], "partial")

    def test_missing_model_observation_contract_is_not_publishable(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "claims": [{"claimId": "c1", "observationCode": "O01"}],
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceRef": "timeline@03:00",
                "text": "存在有效现场内容",
            }],
            "observationEvidence": {},
            "extractionQuality": {"completeness": 0.9},
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)

        self.assertEqual(extraction["status"], "review_required")
        self.assertEqual(extraction["extractionQuality"]["matchedObservationCount"], 0)
        self.assertFalse(extraction["extractionQuality"]["publicationEligible"])

    def test_missing_optional_confidence_and_source_type_get_safe_diagnostic_defaults(self):
        rule = load_pilot_track_rule("新一代信息技术赛道")
        payload = json.dumps({
            "evidenceItems": [{
                "evidenceId": "e1",
                "sourceRef": "timeline@02:10",
                "text": "展示了内部测试数据和运行记录",
            }],
            "observationEvidence": [{
                "observationCode": "O01",
                "evidenceIds": ["e1"],
                "evidenceLevel": "E3",
                "achievementLevel": "substantial",
            }],
        }, ensure_ascii=False)

        extraction = extract_evidence_from_llm_payload(payload, rule)
        observation = extraction["observationEvidence"][0]
        evidence = extraction["evidenceItems"][0]

        self.assertGreater(observation["confidence"], 0)
        self.assertEqual(evidence["sourceType"], "timeline")


if __name__ == "__main__":
    unittest.main()
